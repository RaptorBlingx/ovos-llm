#!/usr/bin/env python3
"""
Voice Feedback Manager for ENMS OVOS Skill

Provides natural voice feedback during query processing:
- Initial acknowledgment ("Let me check...")
- Progress indicators for slow queries
- Friendly error messages
- Confirmation flows for critical actions
- Help system responses
"""

import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger()


class FeedbackType(Enum):
    """Types of voice feedback"""
    ACKNOWLEDGMENT = "acknowledgment"  # Initial query received
    CHECKING = "checking"              # Processing query
    FETCHING = "fetching"              # Fetching data from API
    THINKING = "thinking"              # LLM processing
    ERROR = "error"                    # Error occurred
    CONFIRMATION = "confirmation"      # Confirm action
    HELP = "help"                      # Help response
    EXAMPLE = "example"                # Example queries


@dataclass
class FeedbackMessage:
    """Structured voice feedback message"""
    type: FeedbackType
    message: str
    should_speak: bool = True
    delay_ms: int = 0
    priority: int = 1  # 1=high, 2=medium, 3=low


class VoiceFeedbackManager:
    """
    Manages natural voice feedback during query processing
    
    Features:
    - Adaptive acknowledgments based on query type
    - Progress indicators for long operations
    - Friendly error messages with suggestions
    - Confirmation flows for critical actions
    - Help system with examples
    """
    
    def __init__(self, enable_progress: bool = True, progress_threshold_ms: int = 500):
        """
        Initialize voice feedback manager
        
        Args:
            enable_progress: Enable progress indicators for slow queries
            progress_threshold_ms: Threshold for showing progress (default 500ms)
        """
        self.enable_progress = enable_progress
        self.progress_threshold_ms = progress_threshold_ms
        
        # Acknowledgment variations
        self.acknowledgments = {
            'factory_overview': [
                "Let me get the factory overview",
                "Checking the factory status",
                "Getting the latest factory data"
            ],
            'machine_status': [
                "Let me check that machine",
                "Looking up the machine status",
                "Getting the machine information"
            ],
            'power_query': [
                "Let me check the power consumption",
                "Looking up power usage",
                "Getting power data"
            ],
            'energy_query': [
                "Let me check energy consumption",
                "Getting energy usage data",
                "Looking up energy metrics"
            ],
            'comparison': [
                "Let me compare those machines",
                "Comparing the machines",
                "Getting comparison data"
            ],
            'ranking': [
                "Let me rank the machines",
                "Getting the top machines",
                "Ranking by performance"
            ],
            'anomaly_detection': [
                "Let me check for anomalies",
                "Scanning for unusual patterns",
                "Looking for issues"
            ],
            'cost_query': [
                "Let me calculate the cost",
                "Getting cost information",
                "Looking up cost data"
            ]
        }
        
        # Progress messages
        self.progress_messages = [
            "Still working on it",
            "Just a moment",
            "Almost there",
            "Processing the data"
        ]
        
        # Error messages with suggestions
        self.error_messages = {
            'api_timeout': "Sorry, the server is taking too long to respond. Please try again.",
            'api_error': "I'm having trouble connecting to the system. Please check the connection.",
            'unknown_machine': "I don't recognize that machine name. Could you try again?",
            'invalid_query': "I didn't quite understand that. Could you rephrase it?",
            'no_data': "I couldn't find any data for that request.",
            'validation_error': "There's something wrong with that query. Please check and try again.",
            'permission_denied': "Sorry, you don't have permission for that action.",
            'rate_limit': "Too many requests. Please wait a moment and try again."
        }
        
        # Help messages
        self.help_messages = {
            'general': """
I can help you monitor factory energy consumption. Try asking:
- "What's the factory overview?"
- "Check Compressor-1 status"
- "How much power is Boiler-1 using?"
- "Which machines use the most energy?"
- "Compare Pump-1 and Pump-2"
            """,
            'examples': [
                "What's the factory status?",
                "Check Compressor-1",
                "How much power is Boiler-1 using?",
                "Show me energy for HVAC-Main today",
                "Which machines use the most power?",
                "Compare Pump-1 and Pump-2",
                "Top 5 energy consumers",
                "Any anomalies detected?"
            ]
        }
        
        logger.info("voice_feedback_manager_initialized",
                   enable_progress=enable_progress,
                   progress_threshold_ms=progress_threshold_ms)
    
    def get_acknowledgment(self, intent_type: str, variation: int = 0) -> FeedbackMessage:
        """
        Get acknowledgment message for query
        
        Args:
            intent_type: Type of intent (factory_overview, machine_status, etc.)
            variation: Which variation to use (0-2)
        
        Returns:
            FeedbackMessage with acknowledgment
        """
        messages = self.acknowledgments.get(intent_type, [
            "Let me check that",
            "Looking that up",
            "Getting the information"
        ])
        
        # Cycle through variations
        idx = variation % len(messages)
        message = messages[idx]
        
        logger.debug("acknowledgment_generated",
                    intent_type=intent_type,
                    variation=idx,
                    message=message)
        
        return FeedbackMessage(
            type=FeedbackType.ACKNOWLEDGMENT,
            message=message,
            should_speak=True,
            delay_ms=0,
            priority=1
        )
    
    def get_progress_indicator(self, elapsed_ms: int, stage: str = "processing") -> Optional[FeedbackMessage]:
        """
        Get progress indicator if query is taking too long
        
        Args:
            elapsed_ms: Time elapsed since query started
            stage: Current processing stage (fetching, thinking, processing)
        
        Returns:
            FeedbackMessage if progress should be shown, None otherwise
        """
        if not self.enable_progress:
            return None
        
        if elapsed_ms < self.progress_threshold_ms:
            return None
        
        # Show progress every 2 seconds after threshold
        if (elapsed_ms - self.progress_threshold_ms) % 2000 < 100:
            # Cycle through progress messages
            idx = (elapsed_ms // 2000) % len(self.progress_messages)
            message = self.progress_messages[idx]
            
            logger.debug("progress_indicator_shown",
                        elapsed_ms=elapsed_ms,
                        stage=stage,
                        message=message)
            
            return FeedbackMessage(
                type=FeedbackType.CHECKING,
                message=message,
                should_speak=True,
                delay_ms=0,
                priority=2
            )
        
        return None
    
    def get_error_message(self, error_type: str, context: Optional[Dict[str, Any]] = None) -> FeedbackMessage:
        """
        Get friendly error message with suggestions
        
        Args:
            error_type: Type of error (api_timeout, unknown_machine, etc.)
            context: Additional context for error message
        
        Returns:
            FeedbackMessage with error explanation
        """
        message = self.error_messages.get(error_type, 
                                         "Sorry, something went wrong. Please try again.")
        
        # Add context if available
        if context:
            if 'machine' in context:
                message = message.replace("that machine", f"the machine {context['machine']}")
            if 'suggestion' in context:
                message += f" {context['suggestion']}"
        
        logger.warning("error_feedback_generated",
                      error_type=error_type,
                      context=context,
                      message=message)
        
        return FeedbackMessage(
            type=FeedbackType.ERROR,
            message=message,
            should_speak=True,
            delay_ms=0,
            priority=1
        )
    
    def get_confirmation_request(self, action: str, details: Dict[str, Any]) -> FeedbackMessage:
        """
        Get confirmation request for critical actions
        
        Args:
            action: Action to confirm (shutdown, restart, etc.)
            details: Details about the action
        
        Returns:
            FeedbackMessage requesting confirmation
        """
        machine = details.get('machine', 'the machine')
        
        confirmations = {
            'shutdown': f"Are you sure you want to shut down {machine}?",
            'restart': f"Are you sure you want to restart {machine}?",
            'reset': f"Are you sure you want to reset {machine}?",
            'delete': f"Are you sure you want to delete {machine}?"
        }
        
        message = confirmations.get(action, f"Are you sure you want to {action} {machine}?")
        
        logger.info("confirmation_requested",
                   action=action,
                   details=details,
                   message=message)
        
        return FeedbackMessage(
            type=FeedbackType.CONFIRMATION,
            message=message,
            should_speak=True,
            delay_ms=0,
            priority=1
        )
    
    def get_help_response(self, help_type: str = "general") -> FeedbackMessage:
        """
        Get help system response
        
        Args:
            help_type: Type of help (general, examples, etc.)
        
        Returns:
            FeedbackMessage with help information
        """
        if help_type == "general":
            message = self.help_messages['general']
        elif help_type == "examples":
            examples = self.help_messages['examples']
            message = "Here are some things you can ask:\n" + "\n".join(f"- {ex}" for ex in examples)
        else:
            message = self.help_messages.get(help_type, self.help_messages['general'])
        
        logger.info("help_response_generated",
                   help_type=help_type)
        
        return FeedbackMessage(
            type=FeedbackType.HELP,
            message=message,
            should_speak=True,
            delay_ms=0,
            priority=1
        )
    
    def get_stage_feedback(self, stage: str, details: Optional[Dict[str, Any]] = None) -> FeedbackMessage:
        """
        Get feedback for processing stage
        
        Args:
            stage: Processing stage (fetching, thinking, formatting)
            details: Additional details
        
        Returns:
            FeedbackMessage for the stage
        """
        stage_messages = {
            'fetching': "Getting the data from the system",
            'thinking': "Processing your request",
            'formatting': "Preparing the response",
            'validating': "Validating the data"
        }
        
        message = stage_messages.get(stage, f"Processing: {stage}")
        
        # Add details if available
        if details:
            if 'count' in details:
                message += f" ({details['count']} items)"
            if 'machine' in details:
                message += f" for {details['machine']}"
        
        logger.debug("stage_feedback_generated",
                    stage=stage,
                    details=details,
                    message=message)
        
        return FeedbackMessage(
            type=FeedbackType.CHECKING,
            message=message,
            should_speak=self.enable_progress,
            delay_ms=0,
            priority=2
        )
    
    def format_for_speech(self, message: str) -> str:
        """
        Format message for natural speech
        
        Args:
            message: Raw message text
        
        Returns:
            Speech-optimized message
        """
        # Replace technical terms with voice-friendly versions
        # Order matters - replace longer patterns first
        replacements = [
            ('kWh', 'kilowatt hours'),
            ('kW', 'kilowatts'),
            ('MWh', 'megawatt hours'),
            ('MW', 'megawatts'),
            ('°C', 'degrees celsius'),
            ('°F', 'degrees fahrenheit'),
            ('API', 'A P I'),
            ('HVAC', 'H VAC'),
        ]
        
        result = message
        for old, new in replacements:
            result = result.replace(old, new)
        
        return result


# Global instance
_voice_feedback_manager: Optional[VoiceFeedbackManager] = None


def get_voice_feedback_manager() -> VoiceFeedbackManager:
    """Get or create global voice feedback manager"""
    global _voice_feedback_manager
    if _voice_feedback_manager is None:
        _voice_feedback_manager = VoiceFeedbackManager()
    return _voice_feedback_manager
