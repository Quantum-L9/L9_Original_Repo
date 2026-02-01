"""
L9 L Agent Runtime - Agent State Manager
=========================================
Manages persistent state for autonomous agents following I-AGENT_STATE-001.

State includes:
- Confidence threshold (dynamic)
- Action history
- Trust index
- Proactivity level
- Performance metrics

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Agent State Manager",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T17:47:23Z",
    "updated_at": "2026-01-31T22:21:48Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "agent_state",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


class ProactivityLevel(Enum):
    """Agent proactivity levels."""

    PASSIVE = "passive"  # 0.90 threshold - only suggest
    BALANCED = "balanced"  # 0.80 threshold - suggest + moderate execution
    PROACTIVE = "proactive"  # 0.60 threshold - auto-execute many tasks
    AUTONOMOUS = "autonomous"  # 0.30 threshold - acts independently


@dataclass
class AgentState:
    """Canonical agent state structure (I-AGENT_STATE-001)."""

    # Identity
    agent_id: str = "l"

    # Confidence and autonomy
    confidence_threshold: float = 0.80
    proactivity_level: str = "balanced"
    trust_index: float = 0.5

    # History and learning
    action_history: list[dict] = field(default_factory=list)
    last_reflection_timestamp: str | None = None

    # Performance tracking
    performance_metrics: dict = field(default_factory=dict)

    # Value alignment
    value_alignment_vector: dict = field(default_factory=dict)
    bias_vectors: dict = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default values."""
        if not self.performance_metrics:
            self.performance_metrics = {
                "success_rate_last_20": 0.5,
                "prediction_accuracy": 0.5,
                "surprise_rate": 0.5,
                "threshold_adjustments": 0,
            }

        if not self.value_alignment_vector:
            self.value_alignment_vector = {
                "reciprocity": 0.5,
                "trust": 0.5,
                "exploration": 0.5,
            }


class AgentStateManager:
    """Manages agent state with persistence."""

    def __init__(self, agent_id: str = "l", state_dir: Path | None = None):
        """
        Initialize state manager.

        Args:
            agent_id: Unique identifier for the agent
            state_dir: Directory to store state (defaults to ~/.l9/agents/)
        """
        self.agent_id = agent_id
        self.state_dir = state_dir or Path.home() / ".l9" / "agents" / agent_id
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.state_dir / "state.json"

        # Load or initialize state
        self.state = self.load_state()

    def load_state(self) -> AgentState:
        """
        Load state from disk or create new.

        Returns:
            AgentState object
        """
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                logger.info(f"Loaded state for agent {self.agent_id}")
                return AgentState(**data)
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
                return AgentState(agent_id=self.agent_id)
        else:
            logger.info(f"Creating new state for agent {self.agent_id}")
            return AgentState(agent_id=self.agent_id)

    def save_state(self):
        """Save state to disk."""
        try:
            data = asdict(self.state)
            self.state_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Saved state for agent {self.agent_id}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def record_action_outcome(self, action_record: dict):
        """
        Record action with outcome for reflection.

        Args:
            action_record: Dict with action, expectation, outcome
        """
        self.state.action_history.append(action_record)

        # Keep only last 100 actions (rolling window)
        if len(self.state.action_history) > 100:
            self.state.action_history = self.state.action_history[-100:]

        # Save after each action
        self.save_state()

    @property
    def confidence_threshold(self) -> float:
        """Get current confidence threshold."""
        return self.state.confidence_threshold

    @confidence_threshold.setter
    def confidence_threshold(self, value: float):
        """Set confidence threshold with bounds checking."""
        # Enforce bounds (0.30 - 0.95)
        value = max(0.30, min(0.95, value))
        self.state.confidence_threshold = value

        # Track adjustment
        self.state.performance_metrics["threshold_adjustments"] = (
            self.state.performance_metrics.get("threshold_adjustments", 0) + 1
        )

        self.save_state()

    @property
    def action_history(self) -> list[dict]:
        """Get action history."""
        return self.state.action_history

    @property
    def trust_index(self) -> float:
        """Get trust index."""
        return self.state.trust_index

    @trust_index.setter
    def trust_index(self, value: float):
        """Set trust index with bounds checking."""
        self.state.trust_index = max(0.0, min(1.0, value))
        self.save_state()

    @property
    def performance_metrics(self) -> dict:
        """Get performance metrics."""
        return self.state.performance_metrics

    @property
    def last_reflection_timestamp(self) -> str | None:
        """Get last reflection timestamp."""
        return self.state.last_reflection_timestamp

    @last_reflection_timestamp.setter
    def last_reflection_timestamp(self, value: str):
        """Set last reflection timestamp."""
        self.state.last_reflection_timestamp = value
        self.save_state()

    @property
    def value_alignment_vector(self) -> dict:
        """Get value alignment vector."""
        return self.state.value_alignment_vector

    def get_state_summary(self) -> dict:
        """
        Get a summary of current state.

        Returns:
            Dict with key state metrics
        """
        return {
            "agent_id": self.state.agent_id,
            "confidence_threshold": self.state.confidence_threshold,
            "proactivity_level": self.state.proactivity_level,
            "trust_index": self.state.trust_index,
            "action_count": len(self.state.action_history),
            "success_rate": self.state.performance_metrics.get(
                "success_rate_last_20", 0.0
            ),
            "prediction_accuracy": self.state.performance_metrics.get(
                "prediction_accuracy", 0.0
            ),
            "last_reflection": self.state.last_reflection_timestamp,
        }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-221",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "auth",
        "data-models",
        "dataclass",
        "debugging",
        "filesystem",
        "foundation",
        "logging",
        "metrics",
        "serialization",
    ],
    "keywords": [
        "action",
        "agent",
        "alignment",
        "confidence",
        "history",
        "index",
        "last",
        "load",
    ],
    "business_value": "Provides agent state components including ProactivityLevel, AgentState, AgentStateManager",
    "last_modified": "2026-01-31T22:21:48Z",
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
