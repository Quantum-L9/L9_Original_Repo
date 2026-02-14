"""
GMP Routing — Conditional routing functions for GMP DAG

Autonomous agent routing — no interactive user gates.
Agents get authorization BEFORE invoking the DAG.
"""

from __future__ import annotations

from typing import Literal

from workflows.dags.gmp.state import GMPState


def route_after_scope_lock(
    state: GMPState,
) -> Literal["baseline", "aborted"]:
    """Route after scope lock.

    For autonomous agents, scope is provided at invocation.
    If scope_lock found errors, abort. Otherwise proceed.
    """
    if state.errors:
        return "aborted"
    if not state.todo_plan:
        return "aborted"
    return "baseline"


def route_after_validation(
    state: GMPState,
) -> Literal["memory_write", "implement", "aborted"]:
    """Route after validation.

    - validation_passed → proceed to memory_write
    - validation failed + retries left → retry implement
    - validation failed + no retries → abort
    """
    if state.validation_passed:
        return "memory_write"
    if state.retry_count < state.max_retries:
        return "implement"
    return "aborted"
