"""
L9 Governance Integration
==========================
Unified loader for both governance layers (DevLayer + ArchitectMentor).

Integrates:
- DevLayer (CA governance): diffs, reports, constraints
- ArchitectMentor (L agent): foresight, reflection, memory

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Governance Integration",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-20T18:07:27Z",
    "updated_at": "2026-01-20T23:43:16Z",
    "layer": "operations",
    "domain": "current_work",
    "module_name": "governance_integration",
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

import structlog
from pathlib import Path

# Import CA governance
from core.ca_governance import (
    CACodeChange,
)

# Import L agent runtime
from core.l_agent_runtime import (
    AgentStateManager,
    ForesightEngine,
    MemoryAdapter,
    ReflectionEngine,
    registry,
)

logger = structlog.get_logger(__name__)


class GovernanceIntegration:
    """Unified governance integration for L9."""

    def __init__(
        self, repo_root: Path | None = None, agent_id: str = "l", memory_manager=None
    ):
        """
        Initialize governance integration.

        Args:
            repo_root: Repository root directory
            agent_id: Agent identifier
            memory_manager: Optional existing memory manager
        """
        self.repo_root = repo_root or Path.cwd()
        self.agent_id = agent_id

        # Initialize CA governance (DevLayer)
        self.ca_governance = CACodeChange(
            repo_root=self.repo_root,
            governance_loader=None,  # Can be connected to existing loader
        )

        # Initialize L agent runtime (ArchitectMentor)
        self.state_manager = AgentStateManager(agent_id=agent_id)
        self.memory_adapter = MemoryAdapter(memory_manager=memory_manager)
        self.action_registry = registry

        self.foresight_engine = ForesightEngine(
            state_manager=self.state_manager,
            memory_manager=self.memory_adapter,
            action_registry=self.action_registry,
        )

        self.reflection_engine = ReflectionEngine(
            state_manager=self.state_manager, memory_manager=self.memory_adapter
        )

        logger.info(f"Initialized governance integration for agent {agent_id}")

    # =========================================================================
    # CA Governance (DevLayer) Methods
    # =========================================================================

    def propose_code_change(
        self, task: str, changes: list, rationale: str, confidence: float
    ):
        """
        Propose a code change with full CA governance.

        Args:
            task: Task description
            changes: List of file changes
            rationale: Explanation
            confidence: Confidence score

        Returns:
            ChangeProposal object
        """
        return self.ca_governance.propose_change(
            task=task, changes=changes, rationale=rationale, confidence=confidence
        )

    def apply_code_change(self, proposal):
        """
        Apply an approved code change.

        Args:
            proposal: ChangeProposal object

        Returns:
            Application result
        """
        return self.ca_governance.apply_change(proposal)

    # =========================================================================
    # L Agent Runtime (ArchitectMentor) Methods
    # =========================================================================

    def decide_and_act(self, context: dict):
        """
        Execute foresight loop: decide and act.

        Args:
            context: Current context

        Returns:
            ForesightDecision object
        """
        return self.foresight_engine.decide_and_act(context)

    def reflect_on_actions(self, window: int = 20):
        """
        Perform reflection on recent actions.

        Args:
            window: Number of recent actions to reflect on

        Returns:
            Reflection summary
        """
        return self.reflection_engine.reflect_on_recent_actions(window=window)

    def get_agent_state(self):
        """
        Get current agent state summary.

        Returns:
            State summary dict
        """
        return self.state_manager.get_state_summary()

    def register_action(self, action_type: str, description: str = ""):
        """
        Decorator to register an action.

        Args:
            action_type: Action type identifier
            description: Description of the action

        Returns:
            Decorator function
        """
        return self.action_registry.register(action_type, description=description)

    # =========================================================================
    # Unified Methods
    # =========================================================================

    def get_full_status(self):
        """
        Get complete status of both governance layers.

        Returns:
            Dict with CA and L agent status
        """
        return {
            "ca_governance": {
                "confidence_threshold": self.ca_governance.confidence_threshold,
                "repo_root": str(self.ca_governance.repo_root),
            },
            "l_agent": self.get_agent_state(),
            "actions_registered": len(self.action_registry.list_actions()),
        }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-034",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.ca_governance", "core.l_agent_runtime"],
    "tags": ["auth", "current-work", "filesystem", "operations", "utility"],
    "keywords": [
        "act",
        "action",
        "actions",
        "agent",
        "apply",
        "architectmentor",
        "change",
        "decide",
    ],
    "business_value": "Implements GovernanceIntegration for governance integration functionality",
    "last_modified": "2026-01-20T23:43:16Z",
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
