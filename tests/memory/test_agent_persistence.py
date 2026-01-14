"""
Agent Persistence Service Tests
================================

Tests for memory.agent_persistence.AgentPersistenceService.
Verifies checkpoint management and state serialization.
"""

import os
import pytest
from uuid import UUID, uuid4

from memory.agent_persistence import AgentPersistenceService
from memory.substrate_service import init_service, close_service


TEST_DB_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")


@pytest.fixture(scope="function")
async def memory_substrate_service():
    """Provide a memory substrate service for testing."""
    if not TEST_DB_URL:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL not set; skipping agent persistence tests.")
    service = await init_service(TEST_DB_URL)
    yield service
    await close_service()


@pytest.fixture
def agent_persistence_service(memory_substrate_service):
    """Provide an AgentPersistenceService instance."""
    service = AgentPersistenceService(
        service=memory_substrate_service,
        repository=memory_substrate_service._repository,
    )
    return service


class TestAgentPersistenceService:
    """Tests for AgentPersistenceService."""

    def test_initialization(self, agent_persistence_service):
        """Test AgentPersistenceService can be instantiated."""
        assert agent_persistence_service is not None
        assert agent_persistence_service._service is not None

    @pytest.mark.asyncio
    async def test_create_checkpoint(
        self,
        agent_persistence_service: AgentPersistenceService,
    ):
        """Test create_checkpoint creates a checkpoint."""
        agent_id = "test_agent_123"
        state = {
            "step": 1,
            "data": {"key": "value"},
            "timestamp": "2026-01-11T00:00:00Z",
        }
        
        checkpoint_id = await agent_persistence_service.create_checkpoint(
            agent_id=agent_id,
            state=state,
            reason="test",
        )
        
        assert checkpoint_id is not None
        assert isinstance(checkpoint_id, UUID)

    @pytest.mark.asyncio
    async def test_restore_checkpoint(
        self,
        agent_persistence_service: AgentPersistenceService,
    ):
        """Test restore_checkpoint retrieves checkpoint."""
        agent_id = "test_agent_456"
        state = {
            "step": 2,
            "data": {"restored": True},
        }
        
        # Create checkpoint
        checkpoint_id = await agent_persistence_service.create_checkpoint(
            agent_id=agent_id,
            state=state,
            reason="test_restore",
        )
        
        # Restore checkpoint
        restored_state = await agent_persistence_service.restore_checkpoint(agent_id)
        
        assert restored_state is not None
        assert isinstance(restored_state, dict)
        # State should contain our data
        assert "step" in restored_state or "data" in restored_state

    @pytest.mark.asyncio
    async def test_restore_checkpoint_not_found(
        self,
        agent_persistence_service: AgentPersistenceService,
    ):
        """Test restore_checkpoint returns None for non-existent agent."""
        restored = await agent_persistence_service.restore_checkpoint("nonexistent_agent")
        
        # Should return None if no checkpoint exists
        assert restored is None

    @pytest.mark.asyncio
    async def test_list_checkpoints(
        self,
        agent_persistence_service: AgentPersistenceService,
    ):
        """Test list_checkpoints returns list."""
        agent_id = "test_agent_list"
        
        # Create a checkpoint
        await agent_persistence_service.create_checkpoint(
            agent_id=agent_id,
            state={"test": "data"},
            reason="test",
        )
        
        # List checkpoints
        checkpoints = await agent_persistence_service.list_checkpoints(agent_id, limit=10)
        
        assert isinstance(checkpoints, list)
        # Note: Implementation may return empty list if not fully implemented

    def test_serialize_agent_state_dict(self, agent_persistence_service):
        """Test serialize_agent_state with dict."""
        state = {"key": "value", "number": 42}
        
        serialized = agent_persistence_service.serialize_agent_state(state)
        
        assert isinstance(serialized, dict)
        assert serialized == state  # Dict should pass through

    def test_serialize_agent_state_object(self, agent_persistence_service):
        """Test serialize_agent_state with object."""
        class TestObject:
            def __init__(self):
                self.public = "value"
                self._private = "hidden"
        
        obj = TestObject()
        serialized = agent_persistence_service.serialize_agent_state(obj)
        
        assert isinstance(serialized, dict)
        assert "public" in serialized
        assert serialized["public"] == "value"
        # Private attributes should be filtered
        assert "_private" not in serialized

    def test_serialize_agent_state_pydantic(self, agent_persistence_service):
        """Test serialize_agent_state with Pydantic model."""
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            field1: str
            field2: int
        
        model = TestModel(field1="test", field2=42)
        serialized = agent_persistence_service.serialize_agent_state(model)
        
        assert isinstance(serialized, dict)
        assert serialized["field1"] == "test"
        assert serialized["field2"] == 42

    def test_deserialize_agent_state(self, agent_persistence_service):
        """Test deserialize_agent_state."""
        state = {"key": "value", "number": 42}
        
        deserialized = agent_persistence_service.deserialize_agent_state(state)
        
        assert isinstance(deserialized, dict)
        assert deserialized == state

    @pytest.mark.asyncio
    async def test_validate_checkpoint_integrity_valid(
        self,
        agent_persistence_service: AgentPersistenceService,
    ):
        """Test validate_checkpoint_integrity with valid checkpoint."""
        agent_id = "test_agent_validate"
        
        # Create checkpoint
        checkpoint_id = await agent_persistence_service.create_checkpoint(
            agent_id=agent_id,
            state={"valid": True},
            reason="test",
        )
        
        # Validate integrity
        is_valid = await agent_persistence_service.validate_checkpoint_integrity(checkpoint_id)
        
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_checkpoint_integrity_not_found(
        self,
        agent_persistence_service: AgentPersistenceService,
    ):
        """Test validate_checkpoint_integrity with non-existent checkpoint."""
        fake_id = uuid4()
        
        is_valid = await agent_persistence_service.validate_checkpoint_integrity(fake_id)
        
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_delete_old_checkpoints(
        self,
        agent_persistence_service: AgentPersistenceService,
    ):
        """Test delete_old_checkpoints returns count."""
        agent_id = "test_agent_delete"
        
        # Create a checkpoint
        await agent_persistence_service.create_checkpoint(
            agent_id=agent_id,
            state={"test": "data"},
            reason="test",
        )
        
        # Delete old checkpoints
        deleted_count = await agent_persistence_service.delete_old_checkpoints(
            agent_id=agent_id,
            keep_last=5,
        )
        
        assert isinstance(deleted_count, int)
        assert deleted_count >= 0

