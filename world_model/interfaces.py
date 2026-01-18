"""
L9 World Model - Interfaces
===========================

Abstract base classes and protocols for World Model components.

Specification Sources:
- WorldModelOS.yaml (world_model_engine interface)
- world_model_layer.yaml (layer architecture)
- reasoning kernel 01–05 (integration points)

These interfaces define the contract between:
- World Model Engine and L9 core
- World Model State and Memory Substrate
- World Model Updater and LangGraph nodes
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Interfaces",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "interfaces",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["world_model.__init__", "world_model._pack_staging.loader", "world_model._pack_staging.neo4j_substrate", "world_model._pack_staging.orchestrator", "world_model._pack_staging.postgres_substrate", "world_model._pack_staging.query_engine", "world_model._pack_staging.redis_substrate", "world_model._pack_staging.registry", "world_model._pack_staging.state", "world_model._pack_staging.test_integration"],
    },
}
# ============================================================================

from typing import Any, Optional, Protocol


class IWorldModelState(Protocol):
    """
    Interface for World Model State management.

    Specification: WorldModelOS.yaml → state_management

    Responsibilities:
    - Store entity graph
    - Store relation graph
    - Hold reference to causal graph
    - Provide snapshot/restore capabilities

    Integration:
    - Memory Substrate: state persisted via PacketEnvelope
    - Reasoning Kernel 03: state accessed during inference
    """

    def get_entity(self, entity_id: str) -> Optional[dict[str, Any]]:
        """Retrieve entity by ID."""
        ...

    def get_relations(self, entity_id: str) -> list[dict[str, Any]]:
        """Retrieve relations for an entity."""
        ...

    def snapshot(self) -> dict[str, Any]:
        """Create serializable snapshot of current state."""
        ...

    def restore(self, snapshot: dict[str, Any]) -> None:
        """Restore state from snapshot."""
        ...


class IWorldModelEngine(Protocol):
    """
    Interface for World Model Engine.

    Specification: WorldModelOS.yaml → world_model_engine
    Specification: world_model_layer.yaml → engine_layer

    Responsibilities:
    - Initialize world model from specifications
    - Process incoming packets to update state
    - Answer queries against current state
    - Run simulations (future: Bayesian inference)

    Integration:
    - Memory Substrate: receives PacketEnvelope updates
    - LangGraph: exposed as node via update_world_model_node
    - Reasoning Kernel 01-05: provides world context
    """

    def load_specs(self, spec_paths: list[str]) -> None:
        """Load world model specifications from YAML files."""
        ...

    def initialize_state(self) -> None:
        """Initialize world model state from loaded specs."""
        ...

    def update_from_packet(self, packet: dict[str, Any]) -> dict[str, Any]:
        """
        Update world model from a memory packet.

        Args:
            packet: PacketEnvelope payload

        Returns:
            Update result with affected entities/relations
        """
        ...

    def query(self, query: dict[str, Any]) -> dict[str, Any]:
        """
        Query the world model.

        Args:
            query: Query specification

        Returns:
            Query result
        """
        ...

    def simulate(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """
        Run a simulation scenario.

        Args:
            scenario: Simulation parameters

        Returns:
            Simulation results
        """
        ...


class IWorldModelUpdater(Protocol):
    """
    Interface for World Model Updater.

    Specification: WorldModelOS.yaml → update_protocol
    Specification: world_model_layer.yaml → updater_component

    Responsibilities:
    - Parse incoming packets
    - Validate updates against schema
    - Apply updates to state
    - Trigger causal graph recalculation

    Integration:
    - Memory Substrate: consumes PacketEnvelope
    - Reasoning Kernel 04: update validation
    """

    def validate_update(self, update: dict[str, Any]) -> bool:
        """Validate an update against schema."""
        ...

    def apply_update(
        self,
        state: IWorldModelState,
        update: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Apply update to state.

        Args:
            state: Current world model state
            update: Update to apply

        Returns:
            Result with changes applied
        """
        ...


class ICausalGraph(Protocol):
    """
    Interface for Causal Graph operations.

    Specification: world_model_layer.yaml → causal_graph
    Specification: bayesian_causal_graph_engine.yaml

    Responsibilities:
    - Store causal structure
    - Support inference queries
    - Support counterfactual reasoning

    Integration:
    - Reasoning Kernel 05: causal inference
    - Future: Bayesian network engine
    - Future: Random forest approximation
    """

    def get_causes(self, node_id: str) -> list[str]:
        """Get direct causes of a node."""
        ...

    def get_effects(self, node_id: str) -> list[str]:
        """Get direct effects of a node."""
        ...

    def query_path(self, from_node: str, to_node: str) -> list[str]:
        """Find causal path between nodes."""
        ...


class IWorldModelLoader(Protocol):
    """
    Interface for World Model Loader.

    Specification: world_model_layer.yaml → loader_component

    Responsibilities:
    - Load YAML specifications
    - Parse entity schemas
    - Parse relation schemas
    - Parse causal structure

    Integration:
    - WorldModelOS.yaml format
    - world_graph_schema.yaml format
    """

    def load_yaml(self, path: str) -> dict[str, Any]:
        """Load and parse a YAML file."""
        ...

    def load_entity_schemas(self, spec: dict[str, Any]) -> dict[str, Any]:
        """Extract entity schemas from specification."""
        ...

    def load_relation_schemas(self, spec: dict[str, Any]) -> dict[str, Any]:
        """Extract relation schemas from specification."""
        ...

    def load_causal_structure(self, spec: dict[str, Any]) -> dict[str, Any]:
        """Extract causal structure from specification."""
        ...

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-001",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["config", "engine", "learning", "loader", "rest-api", "utility", "world-model"],
    "keywords": ["apply", "causal", "causes", "effects", "engine", "entity", "graph", "initialize"],
    "business_value": "World Model Engine and L9 core World Model State and Memory Substrate World Model Updater and LangGraph nodes",
    "last_modified": "2026-01-07T13:35:58Z",
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
