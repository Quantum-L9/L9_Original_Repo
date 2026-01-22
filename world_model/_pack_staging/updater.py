"""World Model Updater - State Mutation Pipeline.

Applies mutations to WorldModelState through:
- PacketEnvelope parsing → UpdateOperation extraction
- Operation validation against registry schemas
- Atomic application to state
- Transaction support (future)

Follows NIST AI RMF Govern-3 (state mutation governance).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "State Mutation Pipeline.",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T23:45:01Z",
    "updated_at": "2026-01-17T23:47:57Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "updater",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from world_model.interfaces import (Entity, IWorldModelUpdater, Relation,
                                    UpdateOperation, UpdateResult)
from world_model.registry import WorldModelRegistry
from world_model.state import WorldModelState


@dataclass
class UpdateOperation:
    """Single update operation extracted from packet."""

    op_type: str  # "create_entity", "update_entity", "delete_entity", etc.
    data: Dict[str, Any]


@dataclass
class UpdateResult:
    """Result of applying updates."""

    success: bool
    operations_applied: int = 0
    error: Optional[str] = None
    error_op: Optional[UpdateOperation] = None


class WorldModelUpdater(IWorldModelUpdater):
    """Applies updates to World Model state."""

    def __init__(
        self, state: WorldModelState, registry: Optional[WorldModelRegistry] = None
    ):
        """Initialize updater.

        Args:
            state: WorldModelState to update
            registry: Optional WorldModelRegistry for validation
        """
        self._state = state
        self._registry = registry

    # ========== UPDATE ENTRY POINT ==========

    def apply_update(self, update: Any) -> UpdateResult:
        """Apply PacketEnvelope to state.

        Args:
            update: PacketEnvelope instance

        Returns:
            UpdateResult with success status
        """
        try:
            # 1. Parse packet → operations
            operations = self.parse_packet(update)

            # 2. Validate all operations
            for op in operations:
                if not self.validate_operation(op):
                    return UpdateResult(
                        success=False,
                        error=f"Validation failed for operation: {op.op_type}",
                        error_op=op,
                    )

            # 3. Apply operations in order
            applied_count = 0
            for op in operations:
                self.apply_operation(op)
                applied_count += 1

            return UpdateResult(success=True, operations_applied=applied_count)

        except Exception as e:
            return UpdateResult(success=False, error=str(e))

    # ========== PACKET PARSING ==========

    def parse_packet(self, packet: Any) -> List[UpdateOperation]:
        """Extract update operations from PacketEnvelope.

        Args:
            packet: PacketEnvelope instance

        Returns:
            List of UpdateOperation instances

        Raises:
            ValueError: If packet structure invalid
        """
        operations = []

        # Extract payload
        payload = getattr(packet, "payload", {}) or {}
        if isinstance(payload, str):
            import json

            payload = json.loads(payload)

        # Map payload keys to operation types
        op_mapping = {
            "create_entity": "create_entity",
            "update_entity": "update_entity",
            "delete_entity": "delete_entity",
            "add_entity": "create_entity",  # alias
            "remove_entity": "delete_entity",  # alias
            "create_relation": "create_relation",
            "add_relation": "create_relation",  # alias
            "remove_relation": "delete_relation",  # alias
            "delete_relation": "delete_relation",
        }

        for key, op_type in op_mapping.items():
            if key in payload:
                data = payload[key]
                if isinstance(data, list):
                    # Multiple operations of same type
                    for item in data:
                        operations.append(UpdateOperation(op_type=op_type, data=item))
                elif isinstance(data, dict):
                    operations.append(UpdateOperation(op_type=op_type, data=data))

        return operations

    # ========== VALIDATION ==========

    def validate_update(self, update: Any) -> bool:
        """Validate entire PacketEnvelope.

        Args:
            update: PacketEnvelope instance

        Returns:
            True if valid
        """
        try:
            operations = self.parse_packet(update)
            for op in operations:
                if not self.validate_operation(op):
                    return False
            return True
        except Exception:
            return False

    def validate_operation(self, operation: UpdateOperation) -> bool:
        """Validate single operation against registry.

        Args:
            operation: UpdateOperation instance

        Returns:
            True if valid, False if invalid
        """
        if not self._registry:
            # No validation if registry not set
            return True

        if operation.op_type == "create_entity":
            # Construct entity to validate schema
            try:
                entity = Entity(**operation.data)
                return self._registry.validate_entity(entity)
            except Exception:
                return False

        elif operation.op_type == "create_relation":
            try:
                relation = Relation(**operation.data)
                return self._registry.validate_relation(relation)
            except Exception:
                return False

        elif operation.op_type in ("update_entity", "delete_entity"):
            # Just check that entity exists
            entity_id = operation.data.get("entity_id")
            return self._state.get_entity(entity_id) is not None

        elif operation.op_type == "delete_relation":
            # Check that relation exists
            operation.data.get("relation_id")
            # TODO: add get_relation to state
            return True

        return True

    # ========== OPERATION APPLICATION ==========

    def apply_update(self, operation: UpdateOperation) -> None:
        """Apply single operation to state.

        Args:
            operation: UpdateOperation to apply

        Raises:
            ValueError: If operation fails
        """
        if operation.op_type == "create_entity":
            entity = self.create_entity(operation.data)
            self._state.add_entity(entity)

        elif operation.op_type == "update_entity":
            self.update_entity(
                operation.data["entity_id"], operation.data.get("updates", {})
            )

        elif operation.op_type == "delete_entity":
            self.delete_entity(operation.data["entity_id"])

        elif operation.op_type == "create_relation":
            relation = self.create_relation(operation.data)
            self._state.add_relation(relation)

        elif operation.op_type == "delete_relation":
            self.delete_relation(operation.data["relation_id"])

    def apply_operation(self, operation: UpdateOperation) -> None:
        """Apply single operation to state (wrapper).

        Args:
            operation: UpdateOperation to apply
        """
        self.apply_update(operation)

    # ========== BATCH OPERATIONS ==========

    def apply_batch(self, operations: List[UpdateOperation]) -> List[UpdateResult]:
        """Apply multiple operations in order.

        Args:
            operations: List of UpdateOperation instances

        Returns:
            List of UpdateResult for each operation
        """
        results = []
        for op in operations:
            try:
                self.apply_operation(op)
                results.append(UpdateResult(success=True, operations_applied=1))
            except Exception as e:
                results.append(
                    UpdateResult(
                        success=False,
                        error=str(e),
                        error_op=op,
                    )
                )

        return results

    # ========== ENTITY OPERATIONS ==========

    def create_entity(self, entity_data: Dict[str, Any]) -> Entity:
        """Create Entity instance from data dict.

        Args:
            entity_data: Entity data

        Returns:
            Entity instance

        Raises:
            ValueError: If data invalid
        """
        if not entity_data.get("id"):
            raise ValueError("Entity must have 'id' field")

        try:
            return Entity(**entity_data)
        except Exception as e:
            raise ValueError(f"Failed to create entity: {e}")

    def update_entity(self, entity_id: str, updates: Dict[str, Any]) -> Entity:
        """Update existing entity.

        Args:
            entity_id: ID of entity to update
            updates: Updates to apply

        Returns:
            Updated Entity instance

        Raises:
            KeyError: If entity not found
        """
        self._state.update_entity(entity_id, updates)
        return self._state.get_entity(entity_id)

    def delete_entity(self, entity_id: str) -> None:
        """Delete entity from state.

        Args:
            entity_id: ID of entity to delete

        Raises:
            KeyError: If entity not found
        """
        self._state.remove_entity(entity_id)

    # ========== RELATION OPERATIONS ==========

    def create_relation(self, relation_data: Dict[str, Any]) -> Relation:
        """Create Relation instance from data dict.

        Args:
            relation_data: Relation data

        Returns:
            Relation instance

        Raises:
            ValueError: If data invalid
        """
        if not relation_data.get("id"):
            raise ValueError("Relation must have 'id' field")

        try:
            return Relation(**relation_data)
        except Exception as e:
            raise ValueError(f"Failed to create relation: {e}")

    def delete_relation(self, relation_id: str) -> None:
        """Delete relation from state.

        Args:
            relation_id: ID of relation to delete

        Raises:
            KeyError: If relation not found
        """
        self._state.remove_relation(relation_id)

    # ========== REGISTRY MANAGEMENT ==========

    def set_registry(self, registry: WorldModelRegistry) -> None:
        """Set registry for validation.

        Args:
            registry: WorldModelRegistry instance
        """
        self._registry = registry


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-022",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "batch-processing",
        "dataclass",
        "learning",
        "serialization",
        "world-model",
    ],
    "keywords": [
        "apply",
        "batch",
        "create",
        "delete",
        "entity",
        "governance",
        "model",
        "mutation",
    ],
    "business_value": "Provides updater components including UpdateOperation, UpdateResult, WorldModelUpdater",
    "last_modified": "2026-01-17T23:47:57Z",
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
