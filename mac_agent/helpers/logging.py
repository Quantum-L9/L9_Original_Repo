"""
Mac Agent Logging Helpers
==========================

Structured logging utilities for Mac Agent execution.
"""


from datetime import UTC, datetime
from typing import Any


def ts() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(UTC).isoformat()


def log_step(
    log_list: list[dict[str, Any]],
    step_num: int,
    action: str,
    status: str,
    details: str = "",
) -> None:
    """
    Append a structured log entry for a step.

    Args:
        log_list: List to append log entry to
        step_num: Step number (1-indexed)
        action: Action name
        status: "success" or "error"
        details: Optional details string
    """
    log_list.append(
        {
            "step": step_num,
            "action": action,
            "status": status,
            "details": details,
            "timestamp": ts(),
        }
    )


# Runtime execution trace - updated automatically on every execution
