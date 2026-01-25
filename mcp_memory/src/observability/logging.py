"""Structured Logging Interface.

Provides correlation ID injection and structured logging exports.
All modules use get_logger() to retrieve logger instance.
"""

import structlog
from typing import Any, Dict, Optional
from contextvars import ContextVar


# Correlation ID context variable
_correlation_id: ContextVar[Optional[str]] = ContextVar(
    'correlation_id', default=None
)
_trace_id: ContextVar[Optional[str]] = ContextVar(
    'trace_id', default=None
)


def set_correlation_context(
    correlation_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> None:
    """Set correlation IDs for current request context."""
    if correlation_id:
        _correlation_id.set(correlation_id)
    if trace_id:
        _trace_id.set(trace_id)


def get_correlation_context() -> Dict[str, Optional[str]]:
    """Get current correlation context."""
    return {
        'correlation_id': _correlation_id.get(),
        'trace_id': _trace_id.get(),
    }


def get_logger(name: str) -> structlog.BoundLogger:
    """Get logger instance with correlation context injected.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        structlog.BoundLogger with correlation IDs bound
    """
    logger = structlog.get_logger(name)
    
    # Inject correlation IDs
    ctx = get_correlation_context()
    if ctx['correlation_id']:
        logger = logger.bind(correlation_id=ctx['correlation_id'])
    if ctx['trace_id']:
        logger = logger.bind(trace_id=ctx['trace_id'])
    
    return logger


def setup_logging(log_level: str = "INFO") -> None:
    """Initialize structured logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    import logging
    import sys
    
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level_map.get(log_level.upper(), logging.INFO),
    )
    
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            level_map.get(log_level.upper(), logging.INFO)
        ),
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


__all__ = [
    "get_logger",
    "set_correlation_context",
    "get_correlation_context",
    "setup_logging",
]
