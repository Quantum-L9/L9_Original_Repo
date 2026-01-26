"""World Model Pipeline Integration Tests.

Verification of complete pipeline:
- YAML loading → Registry + State
- State updates → PacketEnvelope → UpdateOperation
- Query execution → Path/Filter/Join queries
- Multi-substrate persistence → Orchestrator
- End-to-end integration

Tests Tiers 1-3 (NIST AI RMF Measure-1).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Test Integration",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T23:45:01Z",
    "updated_at": "2026-01-17T23:47:57Z",
    "layer": "learning",
    "domain": "testing",
    "module_name": "test_integration",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import unittest

import pytest

from world_model.interfaces import Entity, Relation
from world_model.loader import WorldModelLoader
from world_model.orchestrator import ConsistencyMode, SubstrateOrchestrator
from world_model.query_engine import QueryEngine
from world_model.state import WorldModelState
from world_model.updater import UpdateOperation, WorldModelUpdater


class TestYAMLLoading(unittest.TestCase):
    """Test YAML specification loading."""

    def test_load_entity_schemas(self):
        """Verify entity schema registration."""
        data = {
            "entity_types": {
                "Person": {
                    "description": "A person",
                    "properties": {"name": "string", "age": "integer"},
                },
                "Company": {
                    "description": "A company",
                    "properties": {"name": "string", "industry": "string"},
                },
            },
        }

        registry = WorldModelLoader.load_entity_schemas(data)

        assert registry.get_entity_type("Person") is not None
        assert registry.get_entity_type("Company") is not None

    def test_load_initial_state(self):
        """Verify initial state (seed data) loading."""
        data = {
            "entities": {
                "person_1": {
                    "type": "Person",
                    "attributes": {"name": "Alice", "age": 30},
                },
                "person_2": {
                    "type": "Person",
                    "attributes": {"name": "Bob", "age": 25},
                },
            },
            "relations": {
                "knows_1": {
                    "type": "knows",
                    "source_entity_id": "person_1",
                    "target_entity_id": "person_2",
                    "attributes": {},
                },
            },
        }

        state = WorldModelLoader.load_initial_state(data)

        assert len(list(state.get_all_entities())) == 2
        assert len(list(state.get_all_relations())) == 1

    def test_validate_spec(self):
        """Verify spec validation."""
        valid_spec = {
            "entity_types": {},
            "relation_types": {},
            "entities": {},
            "relations": {},
            "causal_structure": {},
        }

        assert WorldModelLoader.validate_spec(valid_spec)

    def test_validate_spec_invalid(self):
        """Verify invalid spec rejection."""
        invalid_spec = {
            "entity_types": "not a dict",  # Should be dict
        }

        with pytest.raises(ValueError):
            WorldModelLoader.validate_spec(invalid_spec)


class TestStateUpdates(unittest.TestCase):
    """Test state mutation via updates."""

    def setUp(self):
        """Initialize test state."""
        self.state = WorldModelState()
        self.updater = WorldModelUpdater(self.state)

    def test_create_entity_operation(self):
        """Verify entity creation operation."""
        op = UpdateOperation(
            op_type="create_entity",
            data={"id": "e1", "type": "Person", "attributes": {"name": "Alice"}},
        )

        self.updater.apply_operation(op)

        entity = self.state.get_entity("e1")
        assert entity is not None
        assert entity.attributes["name"] == "Alice"

    def test_update_entity_operation(self):
        """Verify entity update operation."""
        # Create initial entity
        entity = Entity(id="e1", type="Person", attributes={"name": "Alice", "age": 30})
        self.state.add_entity(entity)

        # Update operation
        op = UpdateOperation(
            op_type="update_entity",
            data={"entity_id": "e1", "updates": {"age": 31}},
        )

        self.updater.apply_operation(op)

        updated = self.state.get_entity("e1")
        assert updated.attributes["age"] == 31

    def test_create_relation_operation(self):
        """Verify relation creation operation."""
        # Create entities first
        self.state.add_entity(Entity(id="e1", type="Person", attributes={}))
        self.state.add_entity(Entity(id="e2", type="Person", attributes={}))

        # Create relation
        op = UpdateOperation(
            op_type="create_relation",
            data={
                "id": "r1",
                "type": "knows",
                "source_entity_id": "e1",
                "target_entity_id": "e2",
                "attributes": {},
            },
        )

        self.updater.apply_operation(op)

        relations = list(self.state.get_all_relations())
        assert len(relations) == 1
        assert relations[0].type == "knows"

    def test_batch_operations(self):
        """Verify batch operation execution."""
        ops = [
            UpdateOperation(
                op_type="create_entity",
                data={"id": "e1", "type": "Person", "attributes": {}},
            ),
            UpdateOperation(
                op_type="create_entity",
                data={"id": "e2", "type": "Person", "attributes": {}},
            ),
            UpdateOperation(
                op_type="create_relation",
                data={
                    "id": "r1",
                    "type": "knows",
                    "source_entity_id": "e1",
                    "target_entity_id": "e2",
                    "attributes": {},
                },
            ),
        ]

        results = self.updater.apply_batch(ops)

        assert len(results) == 3
        assert all(r.success for r in results)


class TestQueries(unittest.TestCase):
    """Test query execution."""

    def setUp(self):
        """Initialize test data."""
        self.state = WorldModelState()
        self.query = QueryEngine(self.state)

        # Create test entities
        self.state.add_entity(
            Entity(id="alice", type="Person", attributes={"name": "Alice", "age": 30})
        )
        self.state.add_entity(
            Entity(id="bob", type="Person", attributes={"name": "Bob", "age": 25})
        )
        self.state.add_entity(
            Entity(id="acme", type="Company", attributes={"name": "ACME Corp"})
        )

        # Create test relations
        self.state.add_relation(
            Relation(
                id="r1",
                type="knows",
                source_entity_id="alice",
                target_entity_id="bob",
                attributes={},
            )
        )
        self.state.add_relation(
            Relation(
                id="r2",
                type="works_at",
                source_entity_id="alice",
                target_entity_id="acme",
                attributes={},
            )
        )

    def test_get_entity_query(self):
        """Verify entity retrieval."""
        entity = self.query.get_entity("alice")
        assert entity is not None
        assert entity.attributes["name"] == "Alice"

    def test_filter_by_type_query(self):
        """Verify type-based filtering."""
        persons = self.query.get_entities_by_type("Person")
        assert len(persons) == 2

    def test_filter_by_attribute_query(self):
        """Verify attribute-based filtering."""
        results = self.query.filter_by_attribute(
            entity_type="Person",
            attribute="age",
            value=30,
            comparator="eq",
        )
        assert len(results) == 1
        assert results[0].id == "alice"

    def test_traverse_relation_query(self):
        """Verify relationship traversal."""
        # Alice knows Bob
        targets = self.query.traverse_relation("alice", "knows")
        assert len(targets) == 1
        assert targets[0].id == "bob"

    def test_path_query(self):
        """Verify multi-hop path traversal."""
        # Alice -> works_at -> ACME
        path_results = self.query.path_query("alice", ["works_at"])
        assert len(path_results) == 1
        assert path_results[0].id == "acme"

    def test_count_query(self):
        """Verify count aggregation."""
        total = self.query.count_entities()
        persons = self.query.count_entities("Person")

        assert total == 3
        assert persons == 2

    def test_group_by_query(self):
        """Verify group by aggregation."""
        groups = self.query.group_by_attribute("Person", "age")

        assert 30 in groups
        assert 25 in groups
        assert len(groups[30]) == 1

    def test_join_query(self):
        """Verify join operation."""
        pairs = self.query.join_entities("Person", "Company", "works_at")

        assert len(pairs) == 1
        person, company = pairs[0]
        assert person.id == "alice"
        assert company.id == "acme"


class TestOrchestration(unittest.TestCase):
    """Test multi-substrate orchestration (mock only)."""

    def test_orchestrator_init(self):
        """Verify orchestrator initialization."""
        orch = SubstrateOrchestrator(
            consistency=ConsistencyMode.EVENTUAL,
        )

        assert orch.consistency == ConsistencyMode.EVENTUAL

    def test_consistency_modes(self):
        """Verify consistency mode enum."""
        modes = [
            ConsistencyMode.STRONG,
            ConsistencyMode.EVENTUAL,
            ConsistencyMode.CACHE_ONLY,
        ]

        assert len(modes) == 3


class TestIntegration(unittest.TestCase):
    """End-to-end integration tests."""

    def test_full_pipeline(self):
        """Verify complete YAML → Update → Query pipeline."""
        # 1. Load spec
        spec_data = {
            "entity_types": {
                "Person": {"description": "A person", "properties": {}},
            },
            "entities": {
                "alice": {
                    "id": "alice",
                    "type": "Person",
                    "attributes": {"name": "Alice"},
                },
            },
            "relations": {},
        }

        registry = WorldModelLoader.load_entity_schemas(spec_data)
        state = WorldModelLoader.load_initial_state(spec_data)

        # 2. Apply update
        updater = WorldModelUpdater(state, registry)
        op = UpdateOperation(
            op_type="update_entity",
            data={"entity_id": "alice", "updates": {"name": "Alice Updated"}},
        )
        result = updater.apply_update(op)

        assert result.success

        # 3. Query result
        query = QueryEngine(state, registry)
        entity = query.get_entity("alice")

        assert entity.attributes["name"] == "Alice Updated"


if __name__ == "__main__":
    unittest.main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-026",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "batch-processing",
        "caching",
        "event-driven",
        "learning",
        "mocking",
        "test",
        "testing",
    ],
    "keywords": [
        "attribute",
        "batch",
        "consistency",
        "count",
        "create",
        "entity",
        "filter",
        "full",
    ],
    "business_value": "Provides test integration components including TestYAMLLoading, TestStateUpdates, TestQueries",
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
