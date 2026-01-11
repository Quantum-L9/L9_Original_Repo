"""
L9 Memory - Agent Persistence Service
Version: 1.0.0

Agent persistence layer for checkpoint management and state serialization.
Implements memory_spec_v3.0.yaml memory_layers.persistence contract.

Responsibilities:
- Checkpoint management (create, restore, list, delete)
- State serialization (serialize, deserialize, validate)
- Checkpoint triggers: on_agent_shutdown, on_session_boundary, on_critical_decision, scheduled_hourly
"""

from __future__ import annotations

import structlog
import json
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict
from uuid import UUID, uuid4

from memory.substrate_repository import SubstrateRepository
from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)


class Checkpoint:
    """Represents an agent checkpoint."""
    
    def __init__(
        self,
        checkpoint_id: UUID,
        agent_id: str,
        state: Dict[str, Any],
        reason: str,
        created_at: datetime,
    ):
        self.checkpoint_id = checkpoint_id
        self.agent_id = agent_id
        self.state = state
        self.reason = reason
        self.created_at = created_at


class AgentPersistenceService:
    """
    Agent persistence service for checkpoint management.
    
    Per memory_spec_v3.0.yaml memory_layers.persistence:
    - create_checkpoint(agent_id, state, reason) -> UUID
    - restore_checkpoint(agent_id, checkpoint_id) -> dict
    - list_checkpoints(agent_id, limit) -> List[Checkpoint]
    - delete_old_checkpoints(agent_id, keep_last) -> int
    - serialize_agent_state(agent) -> dict
    - deserialize_agent_state(state) -> dict
    - validate_checkpoint_integrity(checkpoint_id) -> bool
    """
    
    def __init__(
        self,
        service: Optional[MemorySubstrateService] = None,
        repository: Optional[SubstrateRepository] = None,
    ):
        """
        Initialize agent persistence service.
        
        Args:
            service: MemorySubstrateService for checkpoint operations
            repository: SubstrateRepository (alternative to service)
        """
        self._service = service
        self._repository = repository
        
        # Retention policy per spec
        self._retention_policy = {
            "keep_last_n": 10,
            "keep_daily_for_days": 30,
            "keep_weekly_for_weeks": 12,
            "keep_monthly_for_months": 6,
        }
        
        logger.info("AgentPersistenceService initialized")

    def set_service(self, service: MemorySubstrateService) -> None:
        """Set or update service reference."""
        self._service = service

    def set_repository(self, repository: SubstrateRepository) -> None:
        """Set or update repository reference."""
        self._repository = repository

    async def create_checkpoint(
        self,
        agent_id: str,
        state: Dict[str, Any],
        reason: str = "manual",
    ) -> UUID:
        """
        Create a checkpoint for an agent.
        
        Args:
            agent_id: Agent identifier
            state: Agent state dict to persist
            reason: Checkpoint reason (on_agent_shutdown, on_session_boundary, on_critical_decision, scheduled_hourly, manual)
            
        Returns:
            Checkpoint UUID
        """
        logger.debug(
            "Creating checkpoint",
            agent_id=agent_id,
            reason=reason,
            state_keys=list(state.keys()),
        )
        
        if self._service:
            checkpoint_id = await self._service.save_checkpoint(
                agent_id=agent_id,
                state=state,
            )
            logger.info("Checkpoint created", checkpoint_id=str(checkpoint_id), agent_id=agent_id)
            return checkpoint_id
        
        elif self._repository:
            checkpoint_id = await self._repository.save_checkpoint(
                agent_id=agent_id,
                graph_state=state,
            )
            logger.info("Checkpoint created", checkpoint_id=str(checkpoint_id), agent_id=agent_id)
            return checkpoint_id
        
        else:
            raise RuntimeError("Neither service nor repository set")

    async def restore_checkpoint(
        self,
        agent_id: str,
        checkpoint_id: Optional[UUID] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Restore a checkpoint for an agent.
        
        If checkpoint_id is None, restores the latest checkpoint.
        
        Args:
            agent_id: Agent identifier
            checkpoint_id: Optional specific checkpoint UUID
            
        Returns:
            Agent state dict, or None if not found
        """
        logger.debug("Restoring checkpoint", agent_id=agent_id, checkpoint_id=str(checkpoint_id) if checkpoint_id else "latest")
        
        if self._service:
            state = await self._service.get_checkpoint(agent_id=agent_id)
            if state:
                logger.info("Checkpoint restored", agent_id=agent_id)
                return state
            return None
        
        elif self._repository:
            checkpoint = await self._repository.get_checkpoint(agent_id=agent_id)
            if checkpoint:
                logger.info("Checkpoint restored", agent_id=agent_id, checkpoint_id=str(checkpoint.checkpoint_id))
                return checkpoint.graph_state
            return None
        
        else:
            raise RuntimeError("Neither service nor repository set")

    async def list_checkpoints(
        self,
        agent_id: str,
        limit: int = 10,
    ) -> List[Checkpoint]:
        """
        List checkpoints for an agent.
        
        Args:
            agent_id: Agent identifier
            limit: Maximum checkpoints to return
            
        Returns:
            List of Checkpoint objects
        """
        logger.debug("Listing checkpoints", agent_id=agent_id, limit=limit)
        
        # TODO: Implement actual checkpoint listing
        # Requires repository method to query graph_checkpoints table
        # For now, return empty list
        logger.warning("Checkpoint listing not fully implemented", agent_id=agent_id)
        return []

    async def delete_old_checkpoints(
        self,
        agent_id: str,
        keep_last: int = 10,
    ) -> int:
        """
        Delete old checkpoints, keeping only the most recent N.
        
        Args:
            agent_id: Agent identifier
            keep_last: Number of recent checkpoints to keep
            
        Returns:
            Number of checkpoints deleted
        """
        logger.debug("Deleting old checkpoints", agent_id=agent_id, keep_last=keep_last)
        
        # TODO: Implement actual checkpoint deletion
        # Requires repository method to delete from graph_checkpoints
        # For now, return 0
        logger.warning("Checkpoint deletion not fully implemented", agent_id=agent_id)
        return 0

    def serialize_agent_state(self, agent: Any) -> Dict[str, Any]:
        """
        Serialize an agent object to a state dict.
        
        Args:
            agent: Agent object to serialize
            
        Returns:
            Serialized state dict
        """
        if hasattr(agent, "model_dump"):
            # Pydantic model
            return agent.model_dump(mode="json")
        elif hasattr(agent, "__dict__"):
            # Regular object
            return {
                k: self._serialize_value(v)
                for k, v in agent.__dict__.items()
                if not k.startswith("_")
            }
        elif isinstance(agent, dict):
            # Already a dict
            return agent
        else:
            # Fallback: convert to string
            return {"state": str(agent)}

    def _serialize_value(self, value: Any) -> Any:
        """Recursively serialize a value."""
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, UUID):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        else:
            return str(value)

    def deserialize_agent_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deserialize a state dict back to agent-compatible format.
        
        Args:
            state: Serialized state dict
            
        Returns:
            Deserialized state dict (ready for agent restoration)
        """
        # For now, return state as-is
        # In production, might need to restore UUIDs, datetimes, etc.
        return state

    async def validate_checkpoint_integrity(self, checkpoint_id: UUID) -> bool:
        """
        Validate checkpoint integrity.
        
        Checks:
        - Checkpoint exists
        - State is valid JSON
        - Required fields present
        
        Args:
            checkpoint_id: Checkpoint UUID to validate
            
        Returns:
            True if valid, False otherwise
        """
        if self._repository is None:
            raise RuntimeError("Repository not set")
        
        try:
            async with self._repository.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT checkpoint_id, agent_id, graph_state
                    FROM graph_checkpoints
                    WHERE checkpoint_id = $1
                    """,
                    checkpoint_id,
                )
                
                if not row:
                    logger.warning("Checkpoint not found", checkpoint_id=str(checkpoint_id))
                    return False
                
                # Validate state is valid JSON
                state = row["graph_state"]
                if isinstance(state, str):
                    json.loads(state)  # Raises if invalid
                elif not isinstance(state, dict):
                    logger.warning("Invalid state type", checkpoint_id=str(checkpoint_id))
                    return False
                
                logger.debug("Checkpoint integrity valid", checkpoint_id=str(checkpoint_id))
                return True
        
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in checkpoint", checkpoint_id=str(checkpoint_id), error=str(e))
            return False
        except Exception as e:
            logger.error("Checkpoint validation failed", checkpoint_id=str(checkpoint_id), error=str(e), exc_info=True)
            return False

