"""
GMP State — State definition for GMP execution
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class GMPPhase(str, Enum):
    """GMP execution phases."""

    START = "start"
    MEMORY_READ = "memory_read"
    SCOPE_LOCK = "scope_lock"
    BASELINE = "baseline"
    IMPLEMENT = "implement"
    VALIDATE = "validate"
    MEMORY_WRITE = "memory_write"
    FINALIZE = "finalize"
    END = "end"
    ABORTED = "aborted"


@dataclass
class GMPState:
    """
    State object for GMP execution.

    Passed through all nodes and accumulates results.
    Autonomous agents (L, Emma) provide todo_plan and file_budget_may
    at invocation time — no interactive prompts.
    """

    # Agent identity (auto-injected by SDK)
    agent_id: str = ""
    tenant_id: str = ""

    # Task info
    task: str = ""
    tier: str = "RUNTIME"
    gmp_id: str = ""

    # Current phase
    phase: GMPPhase = GMPPhase.START

    # Memory context
    memory_context: dict[str, Any] = field(default_factory=dict)
    memory_read_done: bool = False

    # Scope definition (provided by caller or built by scope_lock)
    todo_plan: list[dict[str, str]] = field(default_factory=list)
    file_budget_may: list[str] = field(default_factory=list)
    file_budget_may_not: list[str] = field(default_factory=list)

    # Baseline
    baseline_passed: bool = False
    baseline_errors: list[str] = field(default_factory=list)

    # Implementation
    changes_made: list[dict[str, Any]] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)

    # Validation
    validation_passed: bool = False
    validation_results: dict[str, str] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3

    # Memory write
    memory_write_done: bool = False
    lessons_saved: int = 0

    # Finalize
    report_path: str = ""
    report_generated: bool = False

    # Errors
    errors: list[str] = field(default_factory=list)

    # Messages for display / audit trail
    messages: list[str] = field(default_factory=list)

    def add_message(self, msg: str):
        """Add a timestamped message to the log."""
        self.messages.append(f"[{datetime.now(tz=UTC).strftime('%H:%M:%S')}] {msg}")
