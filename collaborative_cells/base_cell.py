"""
L9 Collaborative Cells - Base Cell
==================================

Abstract base class for all collaborative cells.

A cell coordinates 2+ agents in a consensus-seeking loop:
1. Primary agent produces output
2. Secondary agent critiques
3. Iterate until consensus or max rounds
"""

from __future__ import annotations

import structlog
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID, uuid4
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


class ConsensusStrategy(str, Enum):
    """Strategy for reaching consensus."""

    UNANIMOUS = "unanimous"  # All agents must agree
    MAJORITY = "majority"  # Majority vote
    THRESHOLD = "threshold"  # Score threshold met
    LEADER = "leader"  # Primary agent decides after feedback


@dataclass
class CellConfig:
    """Configuration for a cell."""

    max_rounds: int = 5
    consensus_threshold: float = 0.85
    consensus_strategy: ConsensusStrategy = ConsensusStrategy.THRESHOLD
    timeout_ms: int = 120000
    require_validation: bool = True
    store_packets: bool = True
    api_key: Optional[str] = None
    model: str = "gpt-4o"


@dataclass
class AgentMessage:
    """Message exchanged between agents in a cell."""

    agent_id: str
    role: str  # "producer", "critic", "validator"
    content: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    round_number: int = 0


@dataclass
class CellRound:
    """Record of a single cell round."""

    round_number: int
    messages: list[AgentMessage] = field(default_factory=list)
    consensus_score: float = 0.0
    consensus_reached: bool = False
    revisions: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


T = TypeVar("T")


@dataclass
class CellResult(Generic[T]):
    """Result of cell execution."""

    cell_id: UUID
    cell_type: str
    success: bool
    output: Optional[T]
    rounds: list[CellRound]
    consensus_reached: bool
    final_score: float
    total_rounds: int
    duration_ms: int
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_id": str(self.cell_id),
            "cell_type": self.cell_type,
            "success": self.success,
            "consensus_reached": self.consensus_reached,
            "final_score": self.final_score,
            "total_rounds": self.total_rounds,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
        }


class BaseCell(ABC):
    """
    Abstract base class for collaborative cells.

    Subclasses must implement:
    - _run_producer(): Primary agent produces output
    - _run_critic(): Secondary agent critiques
    - _apply_revisions(): Apply critique to output
    - _validate_output(): Final validation
    """

    cell_type: str = "base"

    def __init__(self, config: Optional[CellConfig] = None):
        """
        Initialize the cell.

        Args:
            config: Cell configuration
        """
        self._config = config or CellConfig()
        self._cell_id = uuid4()
        self._initialized = False
        self._agents: dict[str, Any] = {}

        logger.info(f"{self.cell_type}Cell initialized with id={self._cell_id}")

    @property
    def cell_id(self) -> UUID:
        """Get cell ID."""
        return self._cell_id

    @property
    def config(self) -> CellConfig:
        """Get cell configuration."""
        return self._config

    # ==========================================================================
    # Abstract Methods
    # ==========================================================================

    @abstractmethod
    @must_stay_async("callers use await")
    async def _run_producer(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
        previous_critique: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Run the producer agent.

        Args:
            task: Task specification
            context: Execution context
            previous_critique: Critique from previous round

        Returns:
            Producer output
        """
        pass

    @abstractmethod
    @must_stay_async("callers use await")
    async def _run_critic(
        self,
        output: dict[str, Any],
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Run the critic agent.

        Args:
            output: Producer output to critique
            task: Original task
            context: Execution context

        Returns:
            Critique with score and suggestions
        """
        pass

    @abstractmethod
    def _apply_revisions(
        self,
        output: dict[str, Any],
        critique: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        """
        Apply critique revisions to output.

        Args:
            output: Current output
            critique: Critique to apply

        Returns:
            Tuple of (revised_output, list_of_revisions_made)
        """
        pass

    @abstractmethod
    @must_stay_async("callers use await")
    async def _validate_output(
        self,
        output: dict[str, Any],
        task: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """
        Validate final output.

        Args:
            output: Output to validate
            task: Original task

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        pass

    # ==========================================================================
    # Main Execution
    # ==========================================================================

    async def execute(
        self,
        task: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> CellResult:
        """
        Execute the cell on a task.

        Args:
            task: Task specification
            context: Optional execution context

        Returns:
            CellResult with output and metadata
        """
        start_time = datetime.utcnow()
        context = context or {}
        rounds: list[CellRound] = []
        current_output: Optional[dict[str, Any]] = None
        last_score = 0.0
        consensus_reached = False
        errors: list[str] = []

        logger.info(f"Cell {self._cell_id} executing task")

        try:
            # Initial production
            current_output = await self._run_producer(task, context, None)

            for round_num in range(1, self._config.max_rounds + 1):
                logger.debug(f"Cell round {round_num}/{self._config.max_rounds}")

                round_messages: list[AgentMessage] = []

                # Producer message
                round_messages.append(
                    AgentMessage(
                        agent_id="producer",
                        role="producer",
                        content=current_output,
                        round_number=round_num,
                    )
                )

                # Get critique
                critique = await self._run_critic(current_output, task, context)
                last_score = critique.get("score", 0.0)

                round_messages.append(
                    AgentMessage(
                        agent_id="critic",
                        role="critic",
                        content=critique,
                        round_number=round_num,
                    )
                )

                # Check for consensus
                consensus_reached = self._check_consensus(critique, last_score)

                cell_round = CellRound(
                    round_number=round_num,
                    messages=round_messages,
                    consensus_score=last_score,
                    consensus_reached=consensus_reached,
                )

                if consensus_reached:
                    rounds.append(cell_round)
                    logger.info(f"Consensus reached at round {round_num}")
                    break

                # Apply revisions
                current_output, revisions = self._apply_revisions(
                    current_output, critique
                )
                cell_round.revisions = revisions
                rounds.append(cell_round)

                # Re-produce with critique context
                if round_num < self._config.max_rounds:
                    current_output = await self._run_producer(task, context, critique)

            # Final validation
            if self._config.require_validation and current_output:
                is_valid, validation_errors = await self._validate_output(
                    current_output, task
                )
                if not is_valid:
                    errors.extend(validation_errors)

        except Exception as e:
            logger.error(f"Cell execution failed: {e}")
            errors.append(str(e))

        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return CellResult(
            cell_id=self._cell_id,
            cell_type=self.cell_type,
            success=len(errors) == 0,
            output=current_output,
            rounds=rounds,
            consensus_reached=consensus_reached,
            final_score=last_score,
            total_rounds=len(rounds),
            duration_ms=duration_ms,
            errors=errors,
        )

    def _check_consensus(
        self,
        critique: dict[str, Any],
        score: float,
    ) -> bool:
        """Check if consensus is reached based on strategy."""
        if self._config.consensus_strategy == ConsensusStrategy.THRESHOLD:
            return score >= self._config.consensus_threshold

        elif self._config.consensus_strategy == ConsensusStrategy.UNANIMOUS:
            return critique.get("consensus", False)

        elif self._config.consensus_strategy == ConsensusStrategy.LEADER:
            # Leader decides - always accept if score is reasonable
            return score >= 0.7

        else:
            # Default to threshold
            return score >= self._config.consensus_threshold

    # ==========================================================================
    # Memory Integration
    # ==========================================================================

    def to_packet_payload(self, result: CellResult) -> dict[str, Any]:
        """
        Convert result to memory packet payload.

        Args:
            result: Cell result

        Returns:
            Payload for PacketEnvelopeIn
        """
        return {
            "kind": "cell_execution",
            "cell_id": str(result.cell_id),
            "cell_type": result.cell_type,
            "success": result.success,
            "consensus_reached": result.consensus_reached,
            "final_score": result.final_score,
            "total_rounds": result.total_rounds,
            "duration_ms": result.duration_ms,
            "error_count": len(result.errors),
        }

    # ==========================================================================
    # Utility Methods
    # ==========================================================================

    def get_agent(self, agent_id: str) -> Optional[Any]:
        """Get a registered agent by ID."""
        return self._agents.get(agent_id)

    def register_agent(self, agent_id: str, agent: Any) -> None:
        """Register an agent with the cell."""
        self._agents[agent_id] = agent
        logger.debug(f"Registered agent {agent_id} with cell {self._cell_id}")
