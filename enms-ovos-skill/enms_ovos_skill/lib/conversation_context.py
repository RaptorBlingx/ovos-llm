"""
Conversation Context Manager
Week 5 Days 31-32: Multi-Turn Conversation Support

Features:
- Session state management
- Follow-up question handling
- Context carryover ("What about Boiler-1?")
- Clarification dialogs
- Multi-turn conversation support
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import structlog
import re
from difflib import SequenceMatcher

from .models import Intent, IntentType

logger = structlog.get_logger(__name__)


@dataclass
class ConversationTurn:
    """Single turn in conversation history"""
    timestamp: datetime
    query: str
    intent: Intent
    response: str
    api_data: Optional[Dict[str, Any]] = None


@dataclass
class ConversationSession:
    """
    Manages conversation state across multiple turns
    
    Tracks:
    - Last mentioned machines
    - Last queried metrics
    - Recent intents
    - Conversation history (last N turns)
    """
    session_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    history: List[ConversationTurn] = field(default_factory=list)
    max_history: int = 10
    session_timeout_minutes: int = 30
    
    # Context state
    last_machine: Optional[str] = None
    last_machines: Optional[List[str]] = None  # For comparisons
    last_metric: Optional[str] = None
    last_intent: Optional[IntentType] = None
    last_time_range: Optional[str] = None
    pending_clarification: Optional[Dict[str, Any]] = None  # Awaiting user response
    
    def add_turn(self, query: str, intent: Intent, response: str, 
                 api_data: Optional[Dict[str, Any]] = None):
        """
        Add a conversation turn and update context
        
        Args:
            query: User's query
            intent: Parsed intent
            response: System response
            api_data: Optional API response data
        """
        turn = ConversationTurn(
            timestamp=datetime.utcnow(),
            query=query,
            intent=intent,
            response=response,
            api_data=api_data
        )
        
        self.history.append(turn)
        
        # Trim history if too long
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        # Update context state
        self.last_activity = datetime.utcnow()
        self.last_intent = intent.intent
        
        if intent.machine:
            self.last_machine = intent.machine
        
        if intent.machines:
            self.last_machines = intent.machines
        
        if intent.metric:
            self.last_metric = intent.metric
        
        if intent.time_range:
            self.last_time_range = str(intent.time_range)
        
        logger.info("conversation_turn_added",
                   session_id=self.session_id,
                   turn_count=len(self.history),
                   last_machine=self.last_machine,
                   last_intent=self.last_intent.value if self.last_intent else None)
    
    def is_expired(self) -> bool:
        """Check if session has timed out"""
        elapsed = datetime.utcnow() - self.last_activity
        return elapsed > timedelta(minutes=self.session_timeout_minutes)
    
    def get_last_turn(self) -> Optional[ConversationTurn]:
        """Get most recent conversation turn"""
        return self.history[-1] if self.history else None
    
    def get_last_machine(self) -> Optional[str]:
        """Get last mentioned machine name"""
        return self.last_machine
    
    def update_machine(self, machine: str):
        """Update last machine context"""
        self.last_machine = machine
        self.last_activity = datetime.utcnow()
        logger.info("context_machine_updated", 
                   session_id=self.session_id, 
                   machine=machine)
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get current context state for display/debugging"""
        return {
            'session_id': self.session_id,
            'turn_count': len(self.history),
            'last_machine': self.last_machine,
            'last_machines': self.last_machines,
            'last_metric': self.last_metric,
            'last_intent': self.last_intent.value if self.last_intent else None,
            'last_time_range': self.last_time_range,
            'session_age_minutes': (datetime.utcnow() - self.started_at).total_seconds() / 60,
            'is_expired': self.is_expired()
        }


class ConversationContextManager:
    """
    Manages multiple conversation sessions
    
    Features:
    - Session lifecycle (create, get, expire)
    - Context-aware query resolution
    - Follow-up question handling
    - Clarification support
    """
    
    def __init__(self, session_timeout_minutes: int = 30):
        """
        Initialize conversation manager
        
        Args:
            session_timeout_minutes: Session expiration time
        """
        self.sessions: Dict[str, ConversationSession] = {}
        self.session_timeout_minutes = session_timeout_minutes
        
        logger.info("conversation_manager_initialized",
                   session_timeout_minutes=session_timeout_minutes)
    
    def get_or_create_session(self, session_id: str) -> ConversationSession:
        """
        Get existing session or create new one
        
        Args:
            session_id: Unique session identifier (e.g., user_id)
            
        Returns:
            ConversationSession
        """
        # Check if session exists and is not expired
        if session_id in self.sessions:
            session = self.sessions[session_id]
            if not session.is_expired():
                return session
            else:
                logger.info("session_expired", session_id=session_id)
                del self.sessions[session_id]
        
        # Create new session
        session = ConversationSession(
            session_id=session_id,
            session_timeout_minutes=self.session_timeout_minutes
        )
        self.sessions[session_id] = session
        
        logger.info("session_created", session_id=session_id)
        return session
    
    def resolve_context_references(self, query: str, intent: Intent, 
                                   session: ConversationSession) -> Intent:
        """
        Resolve pronoun and context references in query
        
        Examples:
        - "What about Boiler-1?" -> Uses previous intent type
        - "And the other one?" -> Uses last_machines list
        - "What about it?" -> Uses last_machine
        
        Args:
            query: User's query
            intent: Parsed intent (may be incomplete)
            session: Current conversation session
            
        Returns:
            Intent with resolved context
        """
        query_lower = query.lower()
        
        # PRIORITY: Check if resolving pending clarification
        if session.pending_clarification:
            # Parse clarification response (machine name, number, or reference)
            resolved_machine = self._parse_clarification_response(
                query, 
                session.pending_clarification.get('options', [])
            )
            
            # If query resolved to a machine, update pending intent
            if resolved_machine:
                logger.info("resolving_pending_clarification",
                           machine=resolved_machine,
                           pending_intent=session.pending_clarification.get('intent'))
                
                # Restore pending intent with machine filled in
                resolved_intent = intent.model_copy(update={
                    'intent': session.pending_clarification['intent'],
                    'machine': resolved_machine,
                    'metric': session.pending_clarification.get('metric'),
                    'time_range': session.pending_clarification.get('time_range')
                })
                
                # Clear pending clarification
                session.pending_clarification = None
                
                return resolved_intent
        
        # Detect follow-up patterns
        is_followup = any(pattern in query_lower for pattern in [
            'what about', 'how about', 'and the', 'what\'s the', 
            'check', 'show me', 'tell me about'
        ])
        
        # Detect pronoun references
        has_pronoun = any(pronoun in query_lower for pronoun in [
            'it', 'that one', 'the other', 'this one'
        ])
        
        # If no machine specified but we have context
        if not intent.machine and not intent.machines and is_followup:
            if session.last_machine:
                logger.info("resolving_machine_context",
                           query=query,
                           resolved_machine=session.last_machine)
                intent = intent.model_copy(update={'machine': session.last_machine})
        
        # If no intent type but query looks like follow-up
        if intent.intent == IntentType.UNKNOWN and is_followup:
            if session.last_intent:
                logger.info("resolving_intent_context",
                           query=query,
                           resolved_intent=session.last_intent.value)
                intent = intent.model_copy(update={'intent': session.last_intent})
        
        # If no metric but we have context
        if not intent.metric and session.last_metric:
            # Only infer metric if query doesn't specify different one
            if not any(word in query_lower for word in ['energy', 'power', 'cost', 'status']):
                logger.info("resolving_metric_context",
                           query=query,
                           resolved_metric=session.last_metric)
                intent = intent.model_copy(update={'metric': session.last_metric})
        
        return intent
    
    def needs_clarification(self, intent: Intent, 
                            ambiguous_machines: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Determine if query needs clarification
        
        Args:
            intent: Parsed intent
            ambiguous_machines: List of machines that match ambiguous query
            
        Returns:
            Dict with clarification info or None:
            {
                'type': 'machine_ambiguous' | 'machine_missing' | 'machines_missing' | 'intent_unknown',
                'message': str,
                'options': List[str]  # Optional: choices for user
            }
        """
        # Ambiguous machine selection (HIGHEST PRIORITY)
        if ambiguous_machines and len(ambiguous_machines) > 1:
            return {
                'type': 'machine_ambiguous',
                'message': self._generate_machine_choice_prompt(ambiguous_machines),
                'options': ambiguous_machines
            }
        
        # Unknown intent
        if intent.intent == IntentType.UNKNOWN:
            return {
                'type': 'intent_unknown',
                'message': "I'm not sure what you're asking. Could you rephrase that?",
                'options': None
            }
        
        # Missing machine for STRICTLY machine-specific queries
        # Note: energy_query, power_query, anomaly_detection can work factory-wide
        if intent.intent in [IntentType.MACHINE_STATUS, IntentType.KPI]:
            if not intent.machine:
                return {
                    'type': 'machine_missing',
                    'message': "Which machine would you like to know about?",
                    'options': None
                }
        
        # Missing machines for comparison
        if intent.intent == IntentType.COMPARISON:
            if not intent.machines or len(intent.machines) < 2:
                return {
                    'type': 'machines_missing',
                    'message': "Which machines would you like to compare?",
                    'options': None
                }
        
        # Ambiguous time range
        if intent.time_range and hasattr(intent.time_range, 'relative'):
            if intent.time_range.relative == 'ambiguous':
                return {
                    'type': 'time_ambiguous',
                    'message': "What time period are you interested in?",
                    'options': None
                }
        
        return None
    
    def _generate_machine_choice_prompt(self, machines: List[str]) -> str:
        """Generate natural clarification prompt for machine selection"""
        if len(machines) == 2:
            return f"Did you mean {machines[0]} or {machines[1]}?"
        elif len(machines) == 3:
            return f"Did you mean {machines[0]}, {machines[1]}, or {machines[2]}?"
        else:
            # More than 3: use numbered list
            numbered = "\n".join([f"{i+1}. {m}" for i, m in enumerate(machines)])
            return f"Which machine did you mean?\n{numbered}"
    
    def generate_clarification_response(self, intent: Intent, 
                                       session: ConversationSession,
                                       validation_suggestions: Optional[List[str]] = None,
                                       ambiguous_machines: Optional[List[str]] = None) -> str:
        """
        Generate helpful clarification message
        
        Args:
            intent: Parsed intent (possibly incomplete)
            session: Current session (for context)
            validation_suggestions: Optional suggestions from validator
            ambiguous_machines: List of machines that match ambiguous query
            
        Returns:
            Clarification message
        """
        # Check for standard clarifications
        clarification = self.needs_clarification(intent, ambiguous_machines)
        if clarification:
            message = clarification['message']
            # Add suggestions if available and not already included
            if validation_suggestions and clarification['type'] != 'machine_ambiguous':
                message += f" {validation_suggestions[0]}"
            return message
        
        # Validator provided suggestions
        if validation_suggestions:
            return validation_suggestions[0]
        
        # Generic fallback
        return "I didn't quite understand that. Could you try rephrasing?"
    
    def _parse_clarification_response(self, query: str, options: List[str]) -> Optional[str]:
        """
        Parse user's clarification response to machine name
        
        Handles:
        - Direct machine name: "Compressor-1"
        - Number choice: "1", "the first one", "number 2"
        - Ordinal choice: "first", "second", "the third one"
        - Reference: "the first", "second one"
        
        Args:
            query: User's response
            options: List of machine options presented
            
        Returns:
            Resolved machine name or None
        """
        if not options:
            return None
        
        query_lower = query.lower().strip()
        
        # Check for direct machine name match
        from .validator import ENMSValidator
        validator = ENMSValidator()
        for valid_machine in validator.machine_whitelist:
            if query_lower == valid_machine.lower():
                # Verify it's in the options
                if valid_machine in options:
                    return valid_machine
        
        # Check for number/ordinal patterns
        number_patterns = [
            (r'^(\d+)$', 'direct'),  # "1", "2"
            (r'(?:number|option)\s+(\d+)', 'number'),  # "number 1", "option 2"
            (r'the\s+(\d+)(?:st|nd|rd|th)?(?:\s+one)?', 'the_num'),  # "the 1st", "the 2nd one"
            (r'^(first|second|third|fourth|fifth)(?:\s+one)?', 'ordinal'),  # "first", "second one"
            (r'the\s+(first|second|third|fourth|fifth)(?:\s+one)?', 'the_ordinal'),  # "the first one"
        ]
        
        ordinal_to_num = {
            'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5
        }
        
        for pattern, pattern_type in number_patterns:
            match = re.search(pattern, query_lower)
            if match:
                captured = match.group(1)
                
                # Convert ordinal to number
                if captured in ordinal_to_num:
                    index = ordinal_to_num[captured] - 1
                else:
                    index = int(captured) - 1
                
                # Validate index
                if 0 <= index < len(options):
                    logger.info("clarification_response_parsed",
                               query=query,
                               pattern_type=pattern_type,
                               index=index,
                               resolved=options[index])
                    return options[index]
        
        logger.warning("clarification_response_not_parsed",
                      query=query,
                      options=options)
        return None
    
    def fuzzy_match_machines(self, query: str, 
                            available_machines: List[str],
                            threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Find machines with similar names using fuzzy matching
        
        Handles variations like:
        - "compressor one" → "Compressor-1"
        - "hvac main" → "HVAC-Main"
        - "boiler 1" → "Boiler-1"
        - Typos and phonetic similarities
        
        Args:
            query: User's query text
            available_machines: List of valid machine names
            threshold: Similarity threshold (0.0-1.0), default 0.7
            
        Returns:
            List of matches sorted by similarity score:
            [
                {"name": "Compressor-1", "similarity": 0.95},
                {"name": "Compressor-EU-1", "similarity": 0.85}
            ]
        """
        query_lower = query.lower()
        matches = []
        
        # Number words to digits for spoken queries
        number_words = {
            'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
            'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10'
        }
        
        # Normalize query: convert number words to digits, remove punctuation
        query_normalized = query_lower
        for word, digit in number_words.items():
            query_normalized = re.sub(rf'{word}', digit, query_normalized)
        
        for machine in available_machines:
            # Normalize machine name for comparison
            machine_norm = machine.lower().replace('-', ' ')
            query_norm = query_normalized.replace('-', ' ')
            
            # Calculate similarity ratio
            ratio = SequenceMatcher(None, machine_norm, query_norm).ratio()
            
            # Also check if query is substring of machine name (boost score)
            if query_norm in machine_norm or machine_norm in query_norm:
                ratio = max(ratio, 0.8)  # Boost substring matches
            
            # Check word-level matching (for multi-word machines)
            machine_words = set(machine_norm.split())
            query_words = set(query_norm.split())
            word_overlap = len(machine_words & query_words) / max(len(machine_words), len(query_words))
            ratio = max(ratio, word_overlap)  # Use best score
            
            if ratio >= threshold:
                matches.append({
                    "name": machine,
                    "similarity": round(ratio, 2)
                })
        
        # Sort by similarity score (descending)
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        logger.info("fuzzy_matching_completed",
                   query=query,
                   matches_count=len(matches),
                   top_match=matches[0]['name'] if matches else None)
        
        return matches


    def cleanup_expired_sessions(self):
        """Remove expired sessions to free memory"""
        expired = [sid for sid, session in self.sessions.items() 
                  if session.is_expired()]
        
        for sid in expired:
            del self.sessions[sid]
            logger.info("session_cleaned_up", session_id=sid)
        
        if expired:
            logger.info("sessions_cleanup_complete", 
                       expired_count=len(expired),
                       active_count=len(self.sessions))
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions"""
        return {
            'total_sessions': len(self.sessions),
            'active_sessions': sum(1 for s in self.sessions.values() if not s.is_expired()),
            'total_turns': sum(len(s.history) for s in self.sessions.values()),
            'avg_turns_per_session': (
                sum(len(s.history) for s in self.sessions.values()) / len(self.sessions)
                if self.sessions else 0
            )
        }
