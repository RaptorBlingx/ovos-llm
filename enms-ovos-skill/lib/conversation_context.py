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
                intent.machine = session.last_machine
        
        # If no intent type but query looks like follow-up
        if intent.intent == IntentType.UNKNOWN and is_followup:
            if session.last_intent:
                logger.info("resolving_intent_context",
                           query=query,
                           resolved_intent=session.last_intent.value)
                intent.intent = session.last_intent
        
        # If no metric but we have context
        if not intent.metric and session.last_metric:
            # Only infer metric if query doesn't specify different one
            if not any(word in query_lower for word in ['energy', 'power', 'cost', 'status']):
                logger.info("resolving_metric_context",
                           query=query,
                           resolved_metric=session.last_metric)
                intent.metric = session.last_metric
        
        return intent
    
    def needs_clarification(self, intent: Intent) -> Optional[str]:
        """
        Determine if query needs clarification
        
        Args:
            intent: Parsed intent
            
        Returns:
            Clarification message or None
        """
        # Unknown intent
        if intent.intent == IntentType.UNKNOWN:
            return "I'm not sure what you're asking. Could you rephrase that?"
        
        # Missing machine for machine-specific queries
        if intent.intent in [IntentType.MACHINE_STATUS, IntentType.POWER_QUERY, 
                             IntentType.ENERGY_QUERY, IntentType.ANOMALY_DETECTION]:
            if not intent.machine:
                return "Which machine would you like to know about?"
        
        # Missing machines for comparison
        if intent.intent == IntentType.COMPARISON:
            if not intent.machines or len(intent.machines) < 2:
                return "Which machines would you like to compare?"
        
        # Ambiguous time range
        if intent.time_range and hasattr(intent.time_range, 'relative'):
            if intent.time_range.relative == 'ambiguous':
                return "What time period are you interested in?"
        
        return None
    
    def generate_clarification_response(self, intent: Intent, 
                                       session: ConversationSession,
                                       validation_suggestions: Optional[List[str]] = None) -> str:
        """
        Generate helpful clarification message
        
        Args:
            intent: Parsed intent (possibly incomplete)
            session: Current session (for context)
            validation_suggestions: Optional suggestions from validator
            
        Returns:
            Clarification message
        """
        # Check for standard clarifications
        clarification = self.needs_clarification(intent)
        if clarification:
            # Add suggestions if available
            if validation_suggestions:
                clarification += f" {validation_suggestions[0]}"
            return clarification
        
        # Validator provided suggestions
        if validation_suggestions:
            return validation_suggestions[0]
        
        # Generic fallback
        return "I didn't quite understand that. Could you try rephrasing?"
    
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
