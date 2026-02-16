"""
Structured logging configuration for symbolic computation module.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Symbolic Computation Logger",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-01T13:15:19Z",
    "updated_at": "2026-01-15T15:48:34Z",
    "layer": "operations",
    "domain": "current_work",
    "module_name": "symbolic_computation_logger",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import logging  # noqa: ADR-0019
import json
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
            '%(asctime)s %(name)s %(levelname)s %(message)s',
            timestamp=True
        )
        handler.setFormatter(formatter)
        self.addHandler(handler)
        self.setLevel(logging.INFO)

    def log_structured(
        self,
        level: int,
        message: str,
        extra: Dict[str, Any] = None
    ):
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
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-034",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["current-work", "messaging", "operations", "serialization", "streaming", "utility"],
    "keywords": ["computation", "log", "logger", "module", "structured", "symbolic"],
    "business_value": "Implements StructuredLogger for symbolic computation logger functionality",
    "last_modified": "2026-01-15T15:48:34Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
