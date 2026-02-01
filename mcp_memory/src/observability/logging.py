"""Structured Logging Interface.

Provides correlation ID injection and structured logging exports.
All modules use get_logger() to retrieve logger instance.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Logging",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-25T06:01:10Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "integration",
    "domain": "mcp_integration",
    "module_name": "logging",
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

from contextvars import ContextVar

import structlog

# Correlation ID context variable
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


def set_correlation_context(
    correlation_id: str | None = None,
    trace_id: str | None = None,
) -> None:
    """Set correlation IDs for current request context."""
    if correlation_id:
        _correlation_id.set(correlation_id)
    if trace_id:
        _trace_id.set(trace_id)


def get_correlation_context() -> dict[str, str | None]:
    """Get current correlation context."""
    return {
        "correlation_id": _correlation_id.get(),
        "trace_id": _trace_id.get(),
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
    if ctx["correlation_id"]:
        logger = logger.bind(correlation_id=ctx["correlation_id"])
    if ctx["trace_id"]:
        logger = logger.bind(trace_id=ctx["trace_id"])

    return logger


def setup_logging(log_level: str = "INFO") -> None:
    """Initialize structured logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    import logging  # noqa: ADR-0019
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
    "get_correlation_context",
    "get_logger",
    "set_correlation_context",
    "setup_logging",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-012",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "caching",
        "debugging",
        "integration",
        "logging",
        "mcp-integration",
        "messaging",
        "streaming",
        "tracing",
        "utility",
    ],
    "keywords": ["correlation", "logger", "logging", "setup", "structured"],
    "business_value": "Provides correlation ID injection and structured logging exports. All modules use get_logger() to retrieve logger instance.",
    "last_modified": "2026-01-31T22:27:11Z",
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
