"""
L9 Bootstrap Models - View Pattern Dataclasses
===============================================

Contains the core dataclasses for the 7-phase bootstrap pipeline:
- PhaseResult: Unified output from each bootstrap phase
- AgentBootstrapContext: In-memory context accumulating across phases
- IdentityView: Agent identity persona (view, not entity)
- AgentBootstrapError: Unified error type for bootstrap failures

These models implement the "view pattern" where phases compute views
without side effects, and the orchestrator accumulates context.

Version: 1.0.0
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# =============================================================================
# Identity View (Phase 4 Output)
# =============================================================================


@dataclass
class IdentityView:
    """
    Agent identity persona (view, not entity).

    Computed from 02-identity kernel YAML at bootstrap time.
    This is a pure view - it does not write to Neo4j or any database.
    """

    agent_id: str
    display_name: str
    short_name: str
    description: str
    capabilities: list[str]
    default_tone: str
    tags: list[str]


# =============================================================================
# Phase Result View Pattern
# =============================================================================


@dataclass
class PhaseResult:
    """
    Immutable result from each bootstrap phase.

    Carries phase outcome + incremental context updates.
    Allows orchestrator to build a unified AgentBootstrapContext without
    side effects in individual phases.
    """

    phase: int
    name: str
    success: bool
    context_delta: dict[str, Any] = field(default_factory=dict)
    error: Exception | None = None
    error_code: str | None = None
    duration_ms: float = 0.0

    def __post_init__(self) -> None:
        """
        Performs post-initialization checks and auto-generates an error code if the bootstrap phase failed without an error code.

        Args:
            self: The PhaseResult instance being initialized.


        Raises:
            AttributeError: If required attributes are missing during post-initialization.
        """
        if (
            not self.success
            and isinstance(self.error, Exception)
            and not self.error_code
        ):
            # Auto-generate error code if missing
            self.error_code = f"BOOTSTRAP_PHASE{self.phase}_{self.name.upper()}_FAILED"


# =============================================================================
# Bootstrap Context (Accumulated State)
# =============================================================================


@dataclass
class AgentBootstrapContext:
    """
    In-memory context accumulating across all 7 phases.

    NOT persisted to substrate; purely local orchestration state.
    Phases update this context via PhaseResult.context_delta.
    """

    agent_id: str
    config: Any  # AgentConfig - use Any to avoid circular import
    phase_results: list[PhaseResult] = field(default_factory=list)
    kernels: dict[str, dict[str, Any]] = field(default_factory=dict)
    identity_view: IdentityView | None = None
    tools: list[str] = field(default_factory=list)
    governance_gates: dict[str, Any] = field(default_factory=dict)
    init_signature: str | None = None
    status: str = "INITIALIZING"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def add_phase_result(self, result: PhaseResult) -> None:
        """Record phase result and merge context_delta."""
        self.phase_results.append(result)
        if result.success:
            for key, value in result.context_delta.items():
                setattr(self, key, value)

    def to_canonical_json(self) -> str:
        """
        Serialize context to deterministic JSON for init_signature computation.

        Sorted keys, no whitespace, consistent ordering.
        """
        # Safe serialization that handles non-serializable config
        config_dict = {}
        if hasattr(self.config, "__dict__"):
            config_dict = {
                k: v
                for k, v in self.config.__dict__.items()
                if not k.startswith("_")
                and isinstance(v, (str, int, float, bool, list, dict, type(None)))
            }
        elif isinstance(self.config, dict):
            config_dict = self.config

        data = {
            "agent_id": self.agent_id,
            "config": config_dict,
            "kernels": self.kernels,
            "identity_view": (
                asdict(self.identity_view) if self.identity_view else None
            ),
            "tools": sorted(self.tools),
            "governance_gates": self.governance_gates,
            "status": self.status,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)

    def compute_init_signature(self) -> str:
        """Compute deterministic SHA-256 signature of this context."""
        canonical = self.to_canonical_json()
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# =============================================================================
# Bootstrap Error Type
# =============================================================================


class AgentBootstrapError(Exception):
    """
    Single error type raised by orchestrator on any phase failure.

    Wraps root cause + context for structured error handling.
    """

    def __init__(
        self,
        phase: int,
        phase_name: str,
        agent_id: str | None,
        root_cause: Exception,
        init_signature: str | None = None,
    ) -> None:
        """Initialize bootstrap error with phase context."""
        self.phase = phase
        self.phase_name = phase_name
        self.agent_id = agent_id
        self.root_cause = root_cause
        self.init_signature = init_signature
        self.error_code = f"BOOTSTRAP_PHASE{phase}_{phase_name.upper()}_FAILED"

        msg = (
            f"Agent bootstrap failed at phase {phase} ({phase_name}), "
            f"agent_id={agent_id}, code={self.error_code}: {root_cause}"
        )
        super().__init__(msg)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "AgentBootstrapContext",
    "AgentBootstrapError",
    "IdentityView",
    "PhaseResult",
]
