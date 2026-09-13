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


from typing import Any, Protocol


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

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
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


# Runtime execution trace - updated automatically on every execution
