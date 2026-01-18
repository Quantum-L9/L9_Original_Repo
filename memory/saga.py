"""
L9 Memory - Cross-DB Saga Pattern
=================================

Multi-stage execution framework for chaining Postgres→Neo4j queries.

The Saga Pattern reduces LLM reasoning steps by bundling related
database operations into atomic, pre-defined workflows.

Example Saga Flow:
  1. Vector search in Postgres (find similar documents)
  2. Extract entity IDs from results
  3. Neo4j graph enrichment (find related entities)
  4. Return combined result

Benefits:
- Reduces LLM reasoning steps (1 tool call vs 3-4)
- Ensures consistent cross-DB operations
- Provides rollback semantics for failures
- Enables transaction-like behavior across DBs

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Cross-DB Saga Pattern",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-13T18:30:12Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "saga",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL", "Redis"],
        "memory_layers": ["semantic_memory"],
        "imported_by": ["api.memory.router", "memory.__init__", "memory.saga_patterns", "memory.substrate_service", "tests.memory.test_saga"],
    },
}
# ============================================================================

import structlog
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, TypeVar
from uuid import UUID, uuid4
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums and Types
# =============================================================================


class SagaStepStatus(str, Enum):
    """Status of a saga step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"
    SKIPPED = "skipped"


class SagaStatus(str, Enum):
    """Overall saga status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


class DatabaseType(str, Enum):
    """Database types for saga steps."""

    POSTGRES = "postgres"
    NEO4J = "neo4j"
    REDIS = "redis"
    MEMORY = "memory"  # In-memory operations


T = TypeVar("T")
R = TypeVar("R")


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SagaStepResult:
    """Result from executing a single saga step."""

    step_id: str
    step_name: str
    status: SagaStepStatus
    database: DatabaseType

    # Results
    data: Any = None
    error: Optional[str] = None

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0

    # Metadata
    records_processed: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == SagaStepStatus.COMPLETED


@dataclass
class SagaResult:
    """Complete result from saga execution."""

    saga_id: UUID
    saga_name: str
    status: SagaStatus

    # Step results
    step_results: list[SagaStepResult] = field(default_factory=list)

    # Final output (combined from all steps)
    output: Any = None

    # Error info
    error: Optional[str] = None
    failed_step: Optional[str] = None

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_ms: float = 0.0

    # Statistics
    steps_completed: int = 0
    steps_failed: int = 0
    steps_skipped: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "saga_id": str(self.saga_id),
            "saga_name": self.saga_name,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "failed_step": self.failed_step,
            "total_duration_ms": self.total_duration_ms,
            "steps_completed": self.steps_completed,
            "steps_failed": self.steps_failed,
            "steps_skipped": self.steps_skipped,
            "step_results": [
                {
                    "step_id": s.step_id,
                    "step_name": s.step_name,
                    "status": s.status.value,
                    "database": s.database.value,
                    "duration_ms": s.duration_ms,
                    "records_processed": s.records_processed,
                }
                for s in self.step_results
            ],
        }


@dataclass
class SagaContext:
    """
    Context passed through saga steps.

    Each step can read from and write to context to pass data downstream.
    """

    saga_id: UUID

    # Input from caller
    input_data: dict[str, Any] = field(default_factory=dict)

    # Accumulated results from steps
    step_outputs: dict[str, Any] = field(default_factory=dict)

    # Extracted entities (accumulated across steps)
    entities: list[dict[str, Any]] = field(default_factory=list)

    # Graph relationships found
    relationships: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_step_output(self, step_name: str) -> Any:
        """Get output from a previous step."""
        return self.step_outputs.get(step_name)

    def set_step_output(self, step_name: str, output: Any) -> None:
        """Set output for current step."""
        self.step_outputs[step_name] = output

    def add_entities(self, entities: list[dict[str, Any]]) -> None:
        """Add extracted entities to context."""
        self.entities.extend(entities)

    def add_relationships(self, relationships: list[dict[str, Any]]) -> None:
        """Add relationships to context."""
        self.relationships.extend(relationships)


# =============================================================================
# Saga Step Definition
# =============================================================================


@dataclass
class SagaStep:
    """
    Definition of a single step in a saga.

    Each step specifies:
    - What database it operates on
    - How to execute (async function)
    - How to compensate on failure (optional)
    - Conditions for execution
    """

    name: str
    database: DatabaseType
    description: str

    # Execution function: (context, clients) -> result data
    execute_fn: Callable[..., Any]

    # Compensation function (optional): (context, clients) -> None
    compensate_fn: Optional[Callable[..., Any]] = None

    # Condition function (optional): (context) -> bool
    # If returns False, step is skipped
    condition_fn: Optional[Callable[[SagaContext], bool]] = None

    # Whether this step is required (failure stops saga)
    required: bool = True

    # Retry configuration
    max_retries: int = 0
    retry_delay_ms: int = 100


# =============================================================================
# Saga Executor
# =============================================================================


class SagaExecutor:
    """
    Executes multi-step sagas across databases.

    Handles:
    - Step sequencing
    - Context propagation
    - Error handling and compensation
    - Result aggregation

    Usage:
        executor = SagaExecutor(
            postgres_pool=pool,
            neo4j_client=neo4j,
        )

        saga = Saga(
            name="vector_to_graph",
            steps=[
                SagaStep(
                    name="vector_search",
                    database=DatabaseType.POSTGRES,
                    execute_fn=vector_search_step,
                ),
                SagaStep(
                    name="extract_entities",
                    database=DatabaseType.MEMORY,
                    execute_fn=extract_entities_step,
                ),
                SagaStep(
                    name="graph_enrich",
                    database=DatabaseType.NEO4J,
                    execute_fn=graph_enrich_step,
                ),
            ],
        )

        result = await executor.execute(saga, input_data={"query": "..."})
    """

    def __init__(
        self,
        postgres_pool: Optional[Any] = None,
        neo4j_client: Optional[Any] = None,
        redis_client: Optional[Any] = None,
        semantic_service: Optional[Any] = None,
    ):
        """
        Initialize saga executor with database clients.

        Args:
            postgres_pool: asyncpg connection pool
            neo4j_client: Neo4jClient instance
            redis_client: Redis client (optional)
            semantic_service: SemanticService for vector search
        """
        self._postgres = postgres_pool
        self._neo4j = neo4j_client
        self._redis = redis_client
        self._semantic = semantic_service

        logger.info("SagaExecutor initialized")

    async def execute(
        self,
        saga: "Saga",
        input_data: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> SagaResult:
        """
        Execute a saga with all its steps.

        Args:
            saga: Saga definition
            input_data: Input data for the saga
            metadata: Additional metadata

        Returns:
            SagaResult with all step results and final output
        """
        import time

        saga_id = uuid4()
        start_time = time.time()

        # Initialize context
        context = SagaContext(
            saga_id=saga_id,
            input_data=input_data or {},
            metadata=metadata or {},
        )

        # Initialize result
        result = SagaResult(
            saga_id=saga_id,
            saga_name=saga.name,
            status=SagaStatus.RUNNING,
            started_at=datetime.utcnow(),
        )

        logger.info(f"Starting saga: {saga.name}", saga_id=str(saga_id))

        completed_steps: list[SagaStep] = []

        try:
            for step in saga.steps:
                step_result = await self._execute_step(step, context)
                result.step_results.append(step_result)

                if step_result.is_success:
                    result.steps_completed += 1
                    completed_steps.append(step)
                elif step_result.status == SagaStepStatus.SKIPPED:
                    result.steps_skipped += 1
                else:
                    result.steps_failed += 1

                    if step.required:
                        # Required step failed - stop and compensate
                        result.status = SagaStatus.FAILED
                        result.error = step_result.error
                        result.failed_step = step.name

                        logger.error(
                            f"Saga step failed: {step.name}",
                            saga_id=str(saga_id),
                            error=step_result.error,
                        )

                        # Run compensation for completed steps
                        await self._compensate(completed_steps, context)
                        result.status = SagaStatus.COMPENSATED
                        break

            if result.status == SagaStatus.RUNNING:
                # All steps completed
                if result.steps_failed > 0:
                    result.status = SagaStatus.PARTIALLY_COMPLETED
                else:
                    result.status = SagaStatus.COMPLETED

                # Build final output
                result.output = saga.build_output(context)

        except Exception as e:
            logger.exception(f"Saga execution failed: {saga.name}")
            result.status = SagaStatus.FAILED
            result.error = str(e)

            # Attempt compensation
            try:
                await self._compensate(completed_steps, context)
                result.status = SagaStatus.COMPENSATED
            except Exception as comp_error:
                logger.error(f"Compensation failed: {comp_error}")

        finally:
            result.completed_at = datetime.utcnow()
            result.total_duration_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Saga completed: {saga.name}",
                saga_id=str(saga_id),
                status=result.status.value,
                duration_ms=result.total_duration_ms,
            )

        return result

    async def _execute_step(
        self,
        step: SagaStep,
        context: SagaContext,
    ) -> SagaStepResult:
        """Execute a single saga step."""
        import time

        step_id = str(uuid4())[:8]
        start_time = time.time()

        result = SagaStepResult(
            step_id=step_id,
            step_name=step.name,
            status=SagaStepStatus.PENDING,
            database=step.database,
            started_at=datetime.utcnow(),
        )

        # Check condition
        if step.condition_fn and not step.condition_fn(context):
            result.status = SagaStepStatus.SKIPPED
            result.completed_at = datetime.utcnow()
            result.duration_ms = (time.time() - start_time) * 1000
            logger.debug(f"Step skipped (condition not met): {step.name}")
            return result

        result.status = SagaStepStatus.RUNNING

        # Get appropriate client
        clients = self._get_clients_for_step(step)

        # Execute with retries
        last_error = None
        for attempt in range(step.max_retries + 1):
            try:
                data = await step.execute_fn(context, **clients)

                # Store output in context
                context.set_step_output(step.name, data)

                result.status = SagaStepStatus.COMPLETED
                result.data = data

                # Count records if data is list-like
                if isinstance(data, (list, tuple)):
                    result.records_processed = len(data)
                elif isinstance(data, dict) and "results" in data:
                    result.records_processed = len(data["results"])

                break

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Step attempt failed: {step.name}",
                    attempt=attempt + 1,
                    error=last_error,
                )

                if attempt < step.max_retries:
                    import asyncio

                    await asyncio.sleep(step.retry_delay_ms / 1000)

        if result.status != SagaStepStatus.COMPLETED:
            result.status = SagaStepStatus.FAILED
            result.error = last_error

        result.completed_at = datetime.utcnow()
        result.duration_ms = (time.time() - start_time) * 1000

        return result

    async def _compensate(
        self,
        completed_steps: list[SagaStep],
        context: SagaContext,
    ) -> None:
        """Run compensation for completed steps in reverse order."""
        logger.info(f"Running compensation for {len(completed_steps)} steps")

        for step in reversed(completed_steps):
            if step.compensate_fn:
                try:
                    clients = self._get_clients_for_step(step)
                    await step.compensate_fn(context, **clients)
                    logger.debug(f"Compensated step: {step.name}")
                except Exception as e:
                    logger.error(f"Compensation failed for {step.name}: {e}")

    def _get_clients_for_step(self, step: SagaStep) -> dict[str, Any]:
        """Get appropriate database clients for a step."""
        clients = {}

        if step.database == DatabaseType.POSTGRES:
            clients["postgres"] = self._postgres
            clients["semantic"] = self._semantic
        elif step.database == DatabaseType.NEO4J:
            clients["neo4j"] = self._neo4j
        elif step.database == DatabaseType.REDIS:
            clients["redis"] = self._redis

        # Always provide all clients for flexibility
        clients["all_clients"] = {
            "postgres": self._postgres,
            "neo4j": self._neo4j,
            "redis": self._redis,
            "semantic": self._semantic,
        }

        return clients


# =============================================================================
# Saga Definition
# =============================================================================


class Saga:
    """
    Definition of a complete saga (multi-step workflow).

    A Saga consists of:
    - Name and description
    - Ordered list of steps
    - Output builder function

    Usage:
        saga = Saga(
            name="vector_to_graph_enrichment",
            description="Search vectors, extract entities, enrich from graph",
            steps=[step1, step2, step3],
            output_builder=lambda ctx: {"results": ctx.entities, ...},
        )
    """

    def __init__(
        self,
        name: str,
        steps: list[SagaStep],
        description: str = "",
        output_builder: Optional[Callable[[SagaContext], Any]] = None,
    ):
        """
        Initialize saga definition.

        Args:
            name: Saga identifier
            steps: Ordered list of saga steps
            description: Human-readable description
            output_builder: Function to build final output from context
        """
        self.name = name
        self.steps = steps
        self.description = description
        self._output_builder = output_builder

    def build_output(self, context: SagaContext) -> Any:
        """Build final output from context."""
        if self._output_builder:
            return self._output_builder(context)

        # Default output builder
        return {
            "entities": context.entities,
            "relationships": context.relationships,
            "step_outputs": context.step_outputs,
            "metadata": context.metadata,
        }


# =============================================================================
# Saga Builder (Fluent API)
# =============================================================================


class SagaBuilder:
    """
    Fluent builder for creating sagas.

    Usage:
        saga = (
            SagaBuilder("my_saga")
            .add_step(
                name="step1",
                database=DatabaseType.POSTGRES,
                execute_fn=step1_fn,
            )
            .add_step(
                name="step2",
                database=DatabaseType.NEO4J,
                execute_fn=step2_fn,
                required=False,
            )
            .with_output_builder(build_output_fn)
            .build()
        )
    """

    def __init__(self, name: str, description: str = ""):
        self._name = name
        self._description = description
        self._steps: list[SagaStep] = []
        self._output_builder: Optional[Callable[[SagaContext], Any]] = None

    def add_step(
        self,
        name: str,
        database: DatabaseType,
        execute_fn: Callable[..., Any],
        description: str = "",
        compensate_fn: Optional[Callable[..., Any]] = None,
        condition_fn: Optional[Callable[[SagaContext], bool]] = None,
        required: bool = True,
        max_retries: int = 0,
    ) -> "SagaBuilder":
        """Add a step to the saga."""
        self._steps.append(
            SagaStep(
                name=name,
                database=database,
                description=description,
                execute_fn=execute_fn,
                compensate_fn=compensate_fn,
                condition_fn=condition_fn,
                required=required,
                max_retries=max_retries,
            )
        )
        return self

    def with_output_builder(
        self,
        builder: Callable[[SagaContext], Any],
    ) -> "SagaBuilder":
        """Set custom output builder."""
        self._output_builder = builder
        return self

    def build(self) -> Saga:
        """Build the saga."""
        return Saga(
            name=self._name,
            steps=self._steps,
            description=self._description,
            output_builder=self._output_builder,
        )


# =============================================================================
# Convenience Functions
# =============================================================================


_executor: Optional[SagaExecutor] = None


@must_stay_async("callers use await")
async def get_saga_executor(
    postgres_pool: Optional[Any] = None,
    neo4j_client: Optional[Any] = None,
    redis_client: Optional[Any] = None,
    semantic_service: Optional[Any] = None,
) -> SagaExecutor:
    """Get or create singleton saga executor."""
    global _executor

    if _executor is None:
        _executor = SagaExecutor(
            postgres_pool=postgres_pool,
            neo4j_client=neo4j_client,
            redis_client=redis_client,
            semantic_service=semantic_service,
        )

    return _executor


__all__ = [
    # Enums
    "SagaStepStatus",
    "SagaStatus",
    "DatabaseType",
    # Data classes
    "SagaStepResult",
    "SagaResult",
    "SagaContext",
    "SagaStep",
    # Core classes
    "Saga",
    "SagaExecutor",
    "SagaBuilder",
    # Convenience
    "get_saga_executor",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-011",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["api", "async", "builder-pattern", "data-models", "dataclass", "debugging", "executor", "learning", "logging", "streaming"],
    "keywords": ["build", "builder", "cross", "database", "entities", "execute", "executor", "find"],
    "business_value": "The Saga Pattern reduces LLM reasoning steps by bundling related database operations into atomic, pre-defined workflows. 1. Vector search in Postgres (find similar documents) 2. Extract entity IDs fro",
    "last_modified": "2026-01-17T23:47:56Z",
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
