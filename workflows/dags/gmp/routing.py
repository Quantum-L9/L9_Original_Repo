"""
GMP Routing — Conditional routing functions for GMP DAG
"""

from __future__ import annotations

from typing import Literal

from workflows.dags.gmp.state import GMPState


def route_after_scope_confirm(
    state: GMPState,
) -> Literal["baseline", "aborted"]:
    """Route after scope confirmation."""
    if state.scope_confirmed:
        return "baseline"
    return "aborted"


def route_after_validation_confirm(
    state: GMPState,
) -> Literal["memory_write", "implement", "aborted"]:
    """Route after validation confirmation."""
    if state.validation_confirmed and state.validation_passed:
        return "memory_write"
    if not state.validation_confirmed:
        return "aborted"
    return "implement"  # Fix and retry
