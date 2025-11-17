"""
Structured logging configuration for EnMS OVOS Skill
Uses structlog for JSON-formatted, context-rich logging
"""
import sys
import structlog
from structlog.processors import TimeStamper, StackInfoRenderer, format_exc_info
from structlog.stdlib import add_log_level, add_logger_name


def configure_logging(log_level: str = "INFO"):
    """
    Configure structured logging for the skill
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    structlog.configure(
        processors=[
            add_log_level,
            add_logger_name,
            TimeStamper(fmt="iso"),
            StackInfoRenderer(),
            format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog.stdlib.logging, log_level)
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
