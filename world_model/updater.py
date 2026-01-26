"""
L9 World Model - Updater
========================

Applies updates to World Model state from memory packets.

Specification Sources:
- WorldModelOS.yaml → update_protocol
- world_model_layer.yaml → updater_component
- reasoning kernel 04 (update validation)

The updater is responsible for:
- Parsing incoming PacketEnvelope payloads
- Validating updates against registry schemas
- Applying entity/relation changes to state
- Triggering causal graph recalculation (future)
- Logging update operations

Integration:
- Memory Substrate: receives PacketEnvelope via engine
- WorldModelState: applies validated updates
- WorldModelRegistry: validates against schemas
- Reasoning Kernel 04: update reasoning
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Updater",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
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
        "imported_by": [
            "world_model.__init__",
            "world_model._pack_staging.test_integration",
            "world_model.engine",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from world_model.registry import WorldModelRegistry
    from world_model.state import WorldModelState


@dataclass
class UpdateOperation:
    """
    Single update operation to apply.

    Specification: WorldModelOS.yaml → update_operation
    """

    operation: str  # "create", "update", "delete"
    target_type: str  # "entity" or "relation"
    target_id: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UpdateResult:
    """
    Result of applying an update.

    Specification: WorldModelOS.yaml → update_result
    """

    success: bool
    operation: UpdateOperation
    affected_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class WorldModelUpdater:
    """
    Applies updates to World Model state.

    Specification Sources:
    - WorldModelOS.yaml → update_protocol
    - world_model_layer.yaml → updater_component
    - reasoning kernel 04 (update validation)

    Responsibilities:
    - Parse PacketEnvelope payloads into UpdateOperations
    - Validate operations against registry schemas
    - Apply operations to state (create/update/delete)
    - Track affected entities/relations
    - (Future) Trigger causal graph updates

    Update Types:
    - entity_create: Add new entity
    - entity_update: Modify entity attributes
    - entity_delete: Remove entity
    - relation_create: Add new relation
    - relation_update: Modify relation attributes
    - relation_delete: Remove relation
    - bulk_update: Multiple operations in transaction

    Integration:
    - WorldModelEngine: delegates updates to updater
    - WorldModelState: receives validated updates
    - WorldModelRegistry: validates schemas
    - Memory Substrate: source of update packets
    """

    def __init__(
        self,
        registry: WorldModelRegistry | None = None,
    ) -> None:
        """
        Initialize updater.

        Args:
            registry: Optional registry for validation
        """
        self._registry = registry
        self._update_log: list[UpdateResult] = []

    # =========================================================================
    # Validation
    # =========================================================================

    def validate_update(self, update: dict[str, Any]) -> bool:
        """
        Validate an update against schema.

        Specification: reasoning kernel 04 → update_validation

        Args:
            update: Update payload from packet

        Returns:
            True if valid
        """
        if not isinstance(update, dict):
            return False

        # Required fields for any update
        if "operation" not in update:
            return False

        operation = update["operation"]
        if operation not in {"create", "update", "delete"}:
            return False

        # Target type validation
        if "target_type" not in update:
            return False

        target_type = update["target_type"]
        if target_type not in {"entity", "relation"}:
            return False

        # Target ID required
        if "target_id" not in update:
            return False

        # For create operations, validate data against registry if available
        if operation == "create" and self._registry:
            data = update.get("data", {})
            if target_type == "entity":
                entity_type = data.get("entity_type", "")
                if entity_type and not self._registry.validate_entity(
                    entity_type, data.get("attributes", {})
                ):
                    return False

        return True

    def validate_operation(self, operation: UpdateOperation) -> list[str]:
        """
        Validate a single operation.

        Args:
            operation: Operation to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors: list[str] = []

        # Validate operation type
        if operation.operation not in {"create", "update", "delete"}:
            errors.append(f"Invalid operation: {operation.operation}")

        # Validate target type
        if operation.target_type not in {"entity", "relation"}:
            errors.append(f"Invalid target_type: {operation.target_type}")

        # Validate target_id
        if not operation.target_id:
            errors.append("target_id is required")

        # For create operations, validate required data
        if operation.operation == "create":
            if operation.target_type == "entity":
                if "entity_type" not in operation.data:
                    errors.append("entity_type required for entity create")
            elif operation.target_type == "relation":
                if "relation_type" not in operation.data:
                    errors.append("relation_type required for relation create")
                if "source_id" not in operation.data:
                    errors.append("source_id required for relation create")
                if "target_id" not in operation.data:
                    errors.append("target_id required for relation create")

        return errors

    # =========================================================================
    # Parsing
    # =========================================================================

    def parse_packet(self, packet: dict[str, Any]) -> list[UpdateOperation]:
        """
        Parse PacketEnvelope payload into operations.

        Specification: WorldModelOS.yaml → packet_parsing

        Args:
            packet: PacketEnvelope payload

        Returns:
            List of UpdateOperations to apply
        """
        operations: list[UpdateOperation] = []

        # Handle single operation format
        if "operation" in packet:
            op = UpdateOperation(
                operation=packet.get("operation", "update"),
                target_type=packet.get("target_type", "entity"),
                target_id=packet.get("target_id", ""),
                data=packet.get("data", {}),
            )
            operations.append(op)

        # Handle batch operations format
        if "operations" in packet:
            for op_data in packet["operations"]:
                op = UpdateOperation(
                    operation=op_data.get("operation", "update"),
                    target_type=op_data.get("target_type", "entity"),
                    target_id=op_data.get("target_id", ""),
                    data=op_data.get("data", {}),
                )
                operations.append(op)

        # Handle entity-specific format
        if "entity" in packet:
            entity_data = packet["entity"]
            op = UpdateOperation(
                operation=packet.get("operation", "create"),
                target_type="entity",
                target_id=entity_data.get("entity_id", entity_data.get("id", "")),
                data=entity_data,
            )
            operations.append(op)

        # Handle relation-specific format
        if "relation" in packet:
            relation_data = packet["relation"]
            op = UpdateOperation(
                operation=packet.get("operation", "create"),
                target_type="relation",
                target_id=relation_data.get("relation_id", relation_data.get("id", "")),
                data=relation_data,
            )
            operations.append(op)

        return operations

    # =========================================================================
    # Apply Updates
    # =========================================================================

    def apply_update(
        self,
        state: WorldModelState,
        update: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Apply update to state.

        Specification: WorldModelOS.yaml → apply_update
        Specification: reasoning kernel 04 → state_mutation

        Args:
            state: Current world model state
            update: Update payload to apply

        Returns:
            Result dict with:
            - success: bool
            - affected_entities: list[str]
            - affected_relations: list[str]
            - errors: list[str]
        """
        result: dict[str, Any] = {
            "success": False,
            "affected_entities": [],
            "affected_relations": [],
            "errors": [],
        }

        # Validate update first
        if not self.validate_update(update):
            result["errors"].append("Update validation failed")
            return result

        # Parse into operations
        operations = self.parse_packet(update)
        if not operations:
            result["errors"].append("No operations parsed from update")
            return result

        # Apply operations
        results = self.apply_batch(state, operations)

        # Aggregate results
        all_success = True
        for op_result in results:
            if not op_result.success:
                all_success = False
                result["errors"].extend(op_result.errors)
            else:
                for affected_id in op_result.affected_ids:
                    if op_result.operation.target_type == "entity":
                        result["affected_entities"].append(affected_id)
                    else:
                        result["affected_relations"].append(affected_id)

        result["success"] = all_success
        return result

    def apply_operation(
        self,
        state: WorldModelState,
        operation: UpdateOperation,
    ) -> UpdateResult:
        """
        Apply single operation to state.

        Args:
            state: World model state
            operation: Operation to apply

        Returns:
            UpdateResult
        """
        # Validate operation
        errors = self.validate_operation(operation)
        if errors:
            return UpdateResult(
                success=False,
                operation=operation,
                errors=errors,
            )

        # Dispatch to appropriate handler
        try:
            if operation.target_type == "entity":
                if operation.operation == "create":
                    return self.create_entity(
                        state,
                        operation.data.get("entity_type", ""),
                        operation.target_id,
                        operation.data.get("attributes", {}),
                    )
                if operation.operation == "update":
                    return self.update_entity(
                        state,
                        operation.target_id,
                        operation.data,
                    )
                if operation.operation == "delete":
                    return self.delete_entity(state, operation.target_id)

            elif operation.target_type == "relation":
                if operation.operation == "create":
                    return self.create_relation(
                        state,
                        operation.data.get("relation_type", ""),
                        operation.data.get("source_id", ""),
                        operation.data.get("target_id", ""),
                        operation.data.get("attributes", {}),
                    )
                if operation.operation == "delete":
                    return self.delete_relation(state, operation.target_id)

            return UpdateResult(
                success=False,
                operation=operation,
                errors=[
                    f"Unhandled operation: {operation.operation} on {operation.target_type}"
                ],
            )

        except Exception as e:
            return UpdateResult(
                success=False,
                operation=operation,
                errors=[str(e)],
            )

    def apply_batch(
        self,
        state: WorldModelState,
        operations: list[UpdateOperation],
    ) -> list[UpdateResult]:
        """
        Apply batch of operations atomically.

        Args:
            state: World model state
            operations: Operations to apply

        Returns:
            List of UpdateResults
        """
        results: list[UpdateResult] = []

        # Take snapshot for rollback
        snapshot = state.snapshot()

        try:
            for operation in operations:
                result = self.apply_operation(state, operation)
                results.append(result)
                self._update_log.append(result)

                # On failure, rollback and stop
                if not result.success:
                    state.restore(snapshot)
                    # Mark remaining operations as not attempted
                    remaining_idx = operations.index(operation) + 1
                    for remaining_op in operations[remaining_idx:]:
                        results.append(
                            UpdateResult(
                                success=False,
                                operation=remaining_op,
                                errors=["Batch aborted due to previous failure"],
                            )
                        )
                    break

        except Exception as e:
            # Rollback on any exception
            state.restore(snapshot)
            # Mark all remaining as failed
            for op in operations[len(results) :]:
                results.append(
                    UpdateResult(
                        success=False,
                        operation=op,
                        errors=[f"Batch exception: {e!s}"],
                    )
                )

        return results

    # =========================================================================
    # Entity Operations
    # =========================================================================

    def create_entity(
        self,
        state: WorldModelState,
        entity_type: str,
        entity_id: str,
        attributes: dict[str, Any],
    ) -> UpdateResult:
        """
        Create new entity in state.

        Args:
            state: World model state
            entity_type: Type of entity
            entity_id: Unique identifier
            attributes: Entity attributes

        Returns:
            UpdateResult
        """
        from world_model.state import Entity

        operation = UpdateOperation(
            operation="create",
            target_type="entity",
            target_id=entity_id,
            data={"entity_type": entity_type, "attributes": attributes},
        )

        # Validate against registry if available
        if self._registry:
            try:
                if not self._registry.validate_entity(entity_type, attributes):
                    return UpdateResult(
                        success=False,
                        operation=operation,
                        errors=[f"Entity validation failed for type: {entity_type}"],
                    )
            except ValueError as e:
                return UpdateResult(
                    success=False,
                    operation=operation,
                    errors=[str(e)],
                )

        try:
            entity = Entity(
                entity_id=entity_id,
                entity_type=entity_type,
                attributes=attributes,
            )
            state.add_entity(entity)

            return UpdateResult(
                success=True,
                operation=operation,
                affected_ids=[entity_id],
            )
        except ValueError as e:
            return UpdateResult(
                success=False,
                operation=operation,
                errors=[str(e)],
            )

    def update_entity(
        self,
        state: WorldModelState,
        entity_id: str,
        updates: dict[str, Any],
    ) -> UpdateResult:
        """
        Update existing entity.

        Args:
            state: World model state
            entity_id: Entity to update
            updates: Attribute updates

        Returns:
            UpdateResult
        """
        operation = UpdateOperation(
            operation="update",
            target_type="entity",
            target_id=entity_id,
            data=updates,
        )

        try:
            state.update_entity(entity_id, updates)

            return UpdateResult(
                success=True,
                operation=operation,
                affected_ids=[entity_id],
            )
        except KeyError as e:
            return UpdateResult(
                success=False,
                operation=operation,
                errors=[str(e)],
            )

    def delete_entity(
        self,
        state: WorldModelState,
        entity_id: str,
    ) -> UpdateResult:
        """
        Delete entity from state.

        Args:
            state: World model state
            entity_id: Entity to delete

        Returns:
            UpdateResult
        """
        operation = UpdateOperation(
            operation="delete",
            target_type="entity",
            target_id=entity_id,
        )

        try:
            state.remove_entity(entity_id)

            return UpdateResult(
                success=True,
                operation=operation,
                affected_ids=[entity_id],
            )
        except KeyError as e:
            return UpdateResult(
                success=False,
                operation=operation,
                errors=[str(e)],
            )

    # =========================================================================
    # Relation Operations
    # =========================================================================

    def create_relation(
        self,
        state: WorldModelState,
        relation_type: str,
        source_id: str,
        target_id: str,
        attributes: dict[str, Any],
    ) -> UpdateResult:
        """
        Create new relation in state.

        Args:
            state: World model state
            relation_type: Type of relation
            source_id: Source entity
            target_id: Target entity
            attributes: Relation attributes

        Returns:
            UpdateResult
        """
        import uuid

        from world_model.state import Relation

        # Generate relation_id if not in attributes
        relation_id = attributes.pop("relation_id", None) or str(uuid.uuid4())

        operation = UpdateOperation(
            operation="create",
            target_type="relation",
            target_id=relation_id,
            data={
                "relation_type": relation_type,
                "source_id": source_id,
                "target_id": target_id,
                "attributes": attributes,
            },
        )

        # Validate against registry if available
        if self._registry:
            source_entity = state.get_entity(source_id)
            target_entity = state.get_entity(target_id)
            if source_entity and target_entity:
                try:
                    if not self._registry.validate_relation(
                        relation_type,
                        source_entity.entity_type,
                        target_entity.entity_type,
                        attributes,
                    ):
                        return UpdateResult(
                            success=False,
                            operation=operation,
                            errors=[
                                f"Relation validation failed for type: {relation_type}"
                            ],
                        )
                except ValueError as e:
                    return UpdateResult(
                        success=False,
                        operation=operation,
                        errors=[str(e)],
                    )

        try:
            relation = Relation(
                relation_id=relation_id,
                relation_type=relation_type,
                source_id=source_id,
                target_id=target_id,
                attributes=attributes,
            )
            state.add_relation(relation)

            return UpdateResult(
                success=True,
                operation=operation,
                affected_ids=[relation_id],
            )
        except ValueError as e:
            return UpdateResult(
                success=False,
                operation=operation,
                errors=[str(e)],
            )

    def delete_relation(
        self,
        state: WorldModelState,
        relation_id: str,
    ) -> UpdateResult:
        """
        Delete relation from state.

        Args:
            state: World model state
            relation_id: Relation to delete

        Returns:
            UpdateResult
        """
        operation = UpdateOperation(
            operation="delete",
            target_type="relation",
            target_id=relation_id,
        )

        try:
            state.remove_relation(relation_id)

            return UpdateResult(
                success=True,
                operation=operation,
                affected_ids=[relation_id],
            )
        except KeyError as e:
            return UpdateResult(
                success=False,
                operation=operation,
                errors=[str(e)],
            )

    # =========================================================================
    # Registry
    # =========================================================================

    def set_registry(self, registry: WorldModelRegistry) -> None:
        """
        Set registry for validation.

        Args:
            registry: WorldModelRegistry instance
        """
        self._registry = registry

    # =========================================================================
    # Logging
    # =========================================================================

    def get_update_log(self) -> list[UpdateResult]:
        """
        Get log of applied updates.

        Returns:
            List of UpdateResults
        """
        return self._update_log.copy()

    def clear_update_log(self) -> None:
        """Clear the update log."""
        self._update_log.clear()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-011",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["batch-processing", "dataclass", "learning", "rest-api", "world-model"],
    "keywords": [
        "against",
        "applies",
        "apply",
        "batch",
        "clear",
        "create",
        "delete",
        "entity",
    ],
    "business_value": "Parsing incoming PacketEnvelope payloads Validating updates against registry schemas Applying entity/relation changes to state Triggering causal graph recalculation (future) Logging update operations ",
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
