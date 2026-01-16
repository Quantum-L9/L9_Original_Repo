"""
Structured logging configuration for symbolic computation module.
"""

import logging
from typing import Any, Dict
from pythonjsonlogger import jsonlogger


class StructuredLogger(logging.Logger):
    """Custom logger with structured JSON output."""

    def __init__(self, name: str):
        """Initialize structured logger."""
        super().__init__(name)
        self._configure_handler()

    def _configure_handler(self):
        """Configure JSON log handler."""
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s", timestamp=True
        )
        handler.setFormatter(formatter)
        self.addHandler(handler)
        self.setLevel(logging.INFO)

    def log_structured(self, level: int, message: str, extra: Dict[str, Any] = None):
        """
        Log structured message.

        Args:
            level: Log level
            message: Log message
            extra: Additional structured data
        """
        self.log(level, message, extra=extra or {})


def get_logger(name: str) -> logging.Logger:
    """
    Get or create logger instance.

    Args:
        name: Logger name

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger
