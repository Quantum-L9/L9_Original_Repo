"""
L9 World Model - Engine
=======================

Core engine for the World Model runtime.

Specification Sources:
- WorldModelOS.yaml → world_model_engine
- world_model_layer.yaml → engine_layer
- reasoning kernel 01-05 (integration points)

The engine is the main entry point for World Model operations:
- Load specifications from YAML
- Initialize and manage state (async)
- Process incoming memory packets (async)
- Answer queries against current state (async)
- Run simulations (async, future)

Integration:
- Memory Substrate: receives PacketEnvelope updates
- IR Engine: accepts ir_graph and execution_plan packets
- LangGraph: exposed via update_world_model_node
- Reasoning Kernel: provides world context
- L9 Core: accessed via singleton

Version: 1.2.0 (async interface)
"""

from __future__ import annotations

from core.singleton_auto_registry import register_singleton

# ============================================================================
__dora_meta__ = {
    "component_name": "Engine",
    "module_version": "1.2.0 (async interface)",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:57Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "engine",
    "type": "engine",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "core.singleton_registry",
            "world_model.__init__",
            "world_model.nodes.update_world_model_node",
            "world_model.runtime",
            "world_model.world_model_service",
        ],
    },
}
# ============================================================================

import asyncio
from datetime import UTC, datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog

from world_model.causal_graph import CausalGraph
from world_model.loader import WorldModelLoader
from world_model.registry import WorldModelRegistry
from world_model.state import WorldModelState
from world_model.updater import WorldModelUpdater

if TYPE_CHECKING:
    from world_model.causal_mapper import CausalMapper
    from world_model.knowledge_ingestor import KnowledgeIngestor
    from world_model.reflection_memory import ReflectionMemory
    from world_model.service import WorldModelService

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# Packet Type Constants (from Memory Substrate)
# =============================================================================

PACKET_TYPE_IR_GRAPH = "ir_graph"
PACKET_TYPE_EXECUTION_PLAN = "execution_plan"
PACKET_TYPE_REFLECTION = "reflection"
PACKET_TYPE_INSIGHT = "insight"
PACKET_TYPE_EVENT = "event"
PACKET_TYPE_MEMORY_WRITE = "memory_write"
PACKET_TYPE_REASONING_TRACE = "reasoning_trace"


class WorldModelEngine:
    """
    Core engine for World Model operations.

    Specification Sources:
    - WorldModelOS.yaml → world_model_engine
    - world_model_layer.yaml → engine_layer
    - reasoning kernel 01-05 (integration)

    Responsibilities:
    - Load world model specifications
    - Initialize and maintain state (async)
    - Process updates from memory packets (async)
    - Answer queries about world state (async)
    - Run simulations (async, future)

    Components:
    - state: WorldModelState (entities, relations)
    - causal_graph: CausalGraph (causal structure)
    - registry: WorldModelRegistry (type schemas)
    - loader: WorldModelLoader (spec parsing)
    - updater: WorldModelUpdater (apply changes)
    - ingestor: KnowledgeIngestor (packet processing)
    - causal_mapper: CausalMapper (decision-outcome mapping)
    - reflection_memory: ReflectionMemory (lessons learned)

    Usage (async):
        engine = WorldModelEngine()
        engine.load_specs(["WorldModelOS.yaml"])
        await engine.initialize_state()

        result = await engine.update_from_packet(packet_payload)
        answer = await engine.query({"type": "entity", "id": "some_id"})

    Integration:
    - Memory Substrate: update_from_packet() receives PacketEnvelope payloads
    - IR Engine: accepts ir_graph, execution_plan packet types
    - LangGraph: exposed via nodes/update_world_model_node
    - Reasoning Kernel 01-05: provides world context
    """

    def __init__(self) -> None:
        """Initialize World Model Engine."""
        self._state: WorldModelState | None = None
        self._causal_graph: CausalGraph | None = None
        self._registry: WorldModelRegistry = WorldModelRegistry()
        self._loader: WorldModelLoader = WorldModelLoader()
        self._updater: WorldModelUpdater = WorldModelUpdater(self._registry)
        self._initialized: bool = False
        self._spec_paths: list[str] = []
        self._created_at: datetime = datetime.now(UTC)
        self._version: int = 0
        self._lock: asyncio.Lock = asyncio.Lock()

        # Runtime components (lazy initialized)
        self._ingestor: KnowledgeIngestor | None = None
        self._causal_mapper: CausalMapper | None = None
        self._reflection_memory: ReflectionMemory | None = None

        # World Model Service for DB-backed entity persistence
        self._world_model_service: WorldModelService | None = None

        logger.info("WorldModelEngine initialized (v1.3.0 async with DB sync)")

    def set_world_model_service(self, service: WorldModelService) -> None:
        """
        Set WorldModelService for DB-backed entity persistence.

        When set, entities ingested via update_from_packet() are
        automatically synced to PostgreSQL after in-memory ingestion.

        Args:
            service: WorldModelService instance
        """
        self._world_model_service = service
        # Wire to ingestor if already initialized
        if self._ingestor:
            self._ingestor.set_world_model_service(service)
        logger.info("WorldModelService attached to engine for DB sync")

    # =========================================================================
    # Initialization
    # =========================================================================

    def load_specs(self, spec_paths: list[str]) -> None:
        """
        Load world model specifications from YAML files.

        Specification: WorldModelOS.yaml → load_specs
        Specification: world_model_layer.yaml → initialization

        Args:
            spec_paths: List of paths to YAML specification files
                Expected files:
                - WorldModelOS.yaml
                - world_model_layer.yaml
                - world_graph_schema.yaml
                - bayesian_causal_graph_engine.yaml
        """
        self._spec_paths = spec_paths
        for path in spec_paths:
            try:
                spec = self._loader.load_yaml(path)
                if spec:
                    # Register entity types
                    for entity_type in spec.get("entity_types", []):
                        self._registry.register_type(
                            entity_type.get("name", "unknown"),
                            entity_type.get("schema", {}),
                        )
                    logger.debug(f"Loaded spec: {path}")
            except Exception as e:
                logger.warning(f"Could not load spec {path}: {e}")

    async def initialize_state(
        self,
        initial_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Initialize world model state from loaded specifications.

        Specification: WorldModelOS.yaml → state_init
        Specification: reasoning kernel 01 (initial state)

        Args:
            initial_state: Optional initial state to restore from

        Creates:
        - WorldModelState with entity/relation containers
        - CausalGraph with loaded structure
        - Populates WorldModelRegistry with type schemas
        - Initializes runtime components (ingestor, mapper, reflection)

        Returns:
            Initialization result with entity/relation counts
        """
        async with self._lock:
            # Initialize state container
            self._state = WorldModelState()
            self._causal_graph = CausalGraph()

            # Restore from initial state if provided
            if initial_state:
                self._state.restore(initial_state.get("state", {}))
                if "causal_graph" in initial_state:
                    self._causal_graph.from_dict(initial_state["causal_graph"])

            # Lazy import to avoid circular dependencies
            from world_model.causal_mapper import CausalMapper
            from world_model.knowledge_ingestor import KnowledgeIngestor
            from world_model.reflection_memory import ReflectionMemory

            # Initialize runtime components
            self._ingestor = KnowledgeIngestor(state=self._state)
            # Wire DB sync if service available
            if self._world_model_service:
                self._ingestor.set_world_model_service(self._world_model_service)
            self._causal_mapper = CausalMapper()
            self._reflection_memory = ReflectionMemory()

            self._initialized = True
            self._version = 1

            logger.info(
                f"WorldModelEngine initialized: "
                f"{self._state.entity_count} entities, "
                f"{self._state.relation_count} relations"
            )

            return {
                "success": True,
                "initialized": True,
                "entity_count": self._state.entity_count,
                "relation_count": self._state.relation_count,
                "version": self._version,
            }

    # =========================================================================
    # Core Operations (Async)
    # =========================================================================

    async def update_from_packet(self, packet: dict[str, Any]) -> dict[str, Any]:
        """
        Update world model from a memory packet.

        Specification: WorldModelOS.yaml → update_protocol
        Specification: world_model_layer.yaml → packet_processing
        Specification: reasoning kernel 04 (update reasoning)

        This is the primary entry point for memory substrate integration.
        Receives PacketEnvelope payloads and applies updates to state.

        Supported packet_types:
        - ir_graph: IR graph from ir_generator.to_packet_payload()
        - execution_plan: Plan from ir_to_plan_adapter.to_memory_packet()
        - reflection: Lessons learned / outcomes
        - insight: Extracted insights
        - event: Generic events

        Args:
            packet: PacketEnvelope payload dict with:
                - packet_type: str
                - payload: dict
                - metadata: dict (optional)
                - provenance: dict (optional)

        Returns:
            Update result dict with:
                - success: bool
                - affected_entities: list[str]
                - affected_relations: list[str]
                - state_version: int
                - errors: list[str]
        """
        if not self._initialized:
            return {
                "success": False,
                "errors": ["Engine not initialized. Call initialize_state() first."],
                "affected_entities": [],
                "affected_relations": [],
                "state_version": 0,
            }

        async with self._lock:
            errors: list[str] = []
            affected_entities: list[str] = []
            affected_relations: list[str] = []

            try:
                packet_type = packet.get("packet_type", packet.get("kind", "unknown"))
                payload = packet.get("payload", packet)

                # Route to appropriate handler based on packet_type
                if packet_type == PACKET_TYPE_IR_GRAPH:
                    result = self._process_ir_graph_packet(payload)
                elif packet_type == PACKET_TYPE_EXECUTION_PLAN:
                    result = self._process_execution_plan_packet(payload)
                elif packet_type == PACKET_TYPE_REFLECTION:
                    result = self._process_reflection_packet(payload)
                elif packet_type == PACKET_TYPE_INSIGHT:
                    result = self._process_insight_packet(payload)
                else:
                    # Generic packet processing via ingestor
                    result = self._process_generic_packet(packet)

                affected_entities = result.get("entities", [])
                affected_relations = result.get("relations", [])
                errors = result.get("errors", [])

                # Sync entities to DB if service available (GMP-WIRE: Pipeline unification)
                if self._world_model_service and self._ingestor:
                    sync_result = await self._ingestor.sync_to_db()
                    if sync_result.get("errors"):
                        logger.warning(f"DB sync partial: {sync_result['errors']}")

                self._version += 1

            except Exception as e:
                logger.error(f"update_from_packet failed: {e}")
                errors.append(str(e))

            return {
                "success": len(errors) == 0,
                "affected_entities": affected_entities,
                "affected_relations": affected_relations,
                "state_version": self._version,
                "errors": errors,
            }

    def _process_ir_graph_packet(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process IR graph packet from ir_generator.to_packet_payload()."""
        entities: list[str] = []
        relations: list[str] = []

        if self._ingestor:
            from world_model.knowledge_ingestor import SourceType

            result = self._ingestor.ingest(payload, SourceType.IR_GRAPH)
            entities = [f"entity_{i}" for i in range(result.entities_added)]
            relations = [f"relation_{i}" for i in range(result.relations_added)]

        # Record decision in causal mapper
        if self._causal_mapper:
            graph_id = payload.get("graph_id", str(uuid4()))
            self._causal_mapper.record_decision(
                decision_id=graph_id,
                description=payload.get("summary", "IR graph generated"),
                decision_type="ir_generation",
                context={"intents": payload.get("intents", [])},
            )

        return {"entities": entities, "relations": relations, "errors": []}

    def _process_execution_plan_packet(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process execution plan packet from ir_to_plan_adapter.to_memory_packet()."""
        entities: list[str] = []

        payload.get("plan_id", str(uuid4()))

        if self._ingestor:
            from world_model.knowledge_ingestor import SourceType

            result = self._ingestor.ingest(payload, SourceType.MEMORY_PACKET)
            entities = [f"entity_{i}" for i in range(result.entities_added)]

        return {"entities": entities, "relations": [], "errors": []}

    def _process_reflection_packet(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process reflection packet containing lessons learned."""
        entities: list[str] = []

        if self._reflection_memory:
            task_id = payload.get("task_id", str(uuid4()))
            self._reflection_memory.record_reflection(
                task_id=task_id,
                data=payload,
            )
            entities.append(f"reflection_{task_id}")

        return {"entities": entities, "relations": [], "errors": []}

    def _process_insight_packet(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process insight packet."""
        entities: list[str] = []

        if self._ingestor:
            from world_model.knowledge_ingestor import SourceType

            result = self._ingestor.ingest(payload, SourceType.MEMORY_PACKET)
            entities = [f"entity_{i}" for i in range(result.entities_added)]

        return {"entities": entities, "relations": [], "errors": []}

    def _process_generic_packet(self, packet: dict[str, Any]) -> dict[str, Any]:
        """Process generic packet via ingestor."""
        entities: list[str] = []
        relations: list[str] = []

        if self._ingestor:
            from world_model.knowledge_ingestor import SourceType

            result = self._ingestor.ingest(packet, SourceType.MEMORY_PACKET)
            entities = [f"entity_{i}" for i in range(result.entities_added)]
            relations = [f"relation_{i}" for i in range(result.relations_added)]

        return {"entities": entities, "relations": relations, "errors": []}

    @must_stay_async("callers use await")
    async def query(self, query: dict[str, Any]) -> dict[str, Any]:
        """
        Query the world model.

        Specification: WorldModelOS.yaml → query_protocol
        Specification: reasoning kernel 03 (query reasoning)

        Query types:
        - entity: Get entity by ID or filter
        - relation: Get relations by ID or filter
        - path: Find path between entities
        - causal: Query causal relationships
        - reflection: Query lessons learned
        - stats: Get world model statistics

        Args:
            query: Query specification dict with:
                - type: str ("entity", "relation", "path", "causal", "reflection", "stats")
                - params: dict (type-specific parameters)

        Returns:
            Query result dict with:
                - success: bool
                - data: Any (query results)
                - errors: list[str]
        """
        if not self._initialized:
            return {
                "success": False,
                "data": None,
                "errors": ["Engine not initialized"],
            }

        query_type = query.get("type", "entity")
        params = query.get("params", {})
        errors: list[str] = []
        data: Any = None

        try:
            if query_type == "entity":
                entity_id = params.get("id")
                if entity_id and self._state:
                    entity = self._state.get_entity(entity_id)
                    data = entity.__dict__ if entity else None
                elif self._state:
                    entities = self._state.list_entities(params.get("entity_type"))
                    data = [e.__dict__ for e in entities] if entities else []

            elif query_type == "relation":
                entity_id = params.get("entity_id")
                if entity_id and self._state:
                    relations = self._state.get_relations(entity_id)
                    data = [r.__dict__ for r in relations] if relations else []

            elif query_type == "causal":
                if self._causal_mapper:
                    from world_model.causal_mapper import CausalQuery

                    causal_query = CausalQuery(
                        query_type=params.get("causal_type", "effect"),
                        source=params.get("source"),
                        target=params.get("target"),
                        intervention=params.get("intervention"),
                    )
                    result = self._causal_mapper.query(causal_query)
                    data = {
                        "result": result.result,
                        "confidence": result.confidence,
                        "explanation": result.explanation,
                    }

            elif query_type == "reflection":
                if self._reflection_memory:
                    reflections = self._reflection_memory.query_reflections(
                        task_id=params.get("task_id"),
                        filters=params.get("filters", {}),
                    )
                    data = [r.to_dict() for r in reflections]

            elif query_type == "stats":
                data = self._get_stats()

            else:
                errors.append(f"Unknown query type: {query_type}")

        except Exception as e:
            logger.error(f"Query failed: {e}")
            errors.append(str(e))

        return {
            "success": len(errors) == 0,
            "data": data,
            "errors": errors,
        }

    def _get_stats(self) -> dict[str, Any]:
        """Get world model statistics."""
        stats: dict[str, Any] = {
            "version": self._version,
            "initialized": self._initialized,
            "created_at": self._created_at.isoformat(),
        }

        if self._state:
            stats["entity_count"] = self._state.entity_count
            stats["relation_count"] = self._state.relation_count

        if self._causal_mapper:
            stats["causal_mapper"] = self._causal_mapper.get_stats()

        if self._reflection_memory:
            stats["reflection_memory"] = self._reflection_memory.get_stats()

        if self._ingestor:
            stats["ingestor"] = self._ingestor.get_stats()

        return stats

    @must_stay_async("callers use await")
    async def simulate(self, change_request: dict[str, Any]) -> dict[str, Any]:
        """
        Run a simulation scenario (what-if analysis).

        Specification: WorldModelOS.yaml → simulation
        Specification: bayesian_causal_graph_engine.yaml → inference
        Specification: reasoning kernel 05 (simulation reasoning)

        Supports:
        - Counterfactual reasoning via causal mapper
        - What-if scenario analysis
        - Impact prediction

        Args:
            change_request: Simulation specification dict with:
                - type: str ("counterfactual", "impact", "propagation")
                - intervention: dict (hypothetical changes)
                - target: str (variable to predict)
                - evidence: dict (observed values, optional)

        Returns:
            Simulation result dict with:
                - success: bool
                - predictions: dict
                - affected_nodes: list[str]
                - confidence: float
                - errors: list[str]
        """
        if not self._initialized:
            return {
                "success": False,
                "predictions": {},
                "affected_nodes": [],
                "confidence": 0.0,
                "errors": ["Engine not initialized"],
            }

        change_request.get("type", "counterfactual")
        intervention = change_request.get("intervention", {})
        target = change_request.get("target")
        errors: list[str] = []
        predictions: dict[str, Any] = {}
        affected_nodes: list[str] = []
        confidence = 0.0

        try:
            if self._causal_mapper:
                from world_model.causal_mapper import CausalQuery

                # Run counterfactual query
                query = CausalQuery(
                    query_type="counterfactual",
                    intervention=intervention,
                    target=target,
                )
                result = self._causal_mapper.query(query)

                predictions = (
                    result.result
                    if isinstance(result.result, dict)
                    else {"outcome": result.result}
                )
                affected_nodes = predictions.get("affected_variables", [])
                confidence = result.confidence
            else:
                errors.append("Causal mapper not initialized")

        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            errors.append(str(e))

        return {
            "success": len(errors) == 0,
            "predictions": predictions,
            "affected_nodes": affected_nodes,
            "confidence": confidence,
            "errors": errors,
        }

    # =========================================================================
    # State Access
    # =========================================================================

    def get_state(self) -> WorldModelState | None:
        """
        Get current world model state.

        Returns:
            WorldModelState if initialized, None otherwise
        """
        return self._state

    def get_causal_graph(self) -> CausalGraph | None:
        """
        Get causal graph.

        Returns:
            CausalGraph if initialized, None otherwise
        """
        return self._causal_graph

    def get_registry(self) -> WorldModelRegistry:
        """
        Get type registry.

        Returns:
            WorldModelRegistry instance
        """
        return self._registry

    # =========================================================================
    # Component Access
    # =========================================================================

    def get_ingestor(self) -> KnowledgeIngestor | None:
        """Get knowledge ingestor instance."""
        return self._ingestor

    def get_causal_mapper(self) -> CausalMapper | None:
        """Get causal mapper instance."""
        return self._causal_mapper

    def get_reflection_memory(self) -> ReflectionMemory | None:
        """Get reflection memory instance."""
        return self._reflection_memory

    # =========================================================================
    # Snapshot / Restore
    # =========================================================================

    def snapshot(self) -> dict[str, Any]:
        """
        Create snapshot of entire world model.

        Specification: WorldModelOS.yaml → checkpoint

        Returns:
            Dict containing:
                - state: WorldModelState snapshot
                - causal_graph: CausalGraph serialization
                - causal_mapper: CausalMapper serialization
                - reflection_memory: ReflectionMemory serialization
                - registry: WorldModelRegistry serialization
                - version: int
                - timestamp: str
        """
        snapshot_data: dict[str, Any] = {
            "version": self._version,
            "timestamp": datetime.now(UTC).isoformat(),
            "initialized": self._initialized,
        }

        if self._state:
            snapshot_data["state"] = self._state.snapshot()

        if self._causal_graph:
            snapshot_data["causal_graph"] = self._causal_graph.to_dict()

        if self._causal_mapper:
            snapshot_data["causal_mapper"] = self._causal_mapper.to_dict()

        if self._reflection_memory:
            snapshot_data["reflection_memory"] = self._reflection_memory.to_dict()

        return snapshot_data

    def restore(self, snapshot: dict[str, Any]) -> None:
        """
        Restore world model from snapshot.

        Args:
            snapshot: Previously created snapshot
        """
        self._version = snapshot.get("version", 0)
        self._initialized = snapshot.get("initialized", False)

        if "state" in snapshot and self._state:
            self._state.restore(snapshot["state"])

        if "causal_graph" in snapshot and self._causal_graph:
            self._causal_graph.from_dict(snapshot["causal_graph"])

        if "causal_mapper" in snapshot and self._causal_mapper:
            self._causal_mapper.from_dict(snapshot["causal_mapper"])

        if "reflection_memory" in snapshot and self._reflection_memory:
            self._reflection_memory.from_dict(snapshot["reflection_memory"])

        logger.info(f"Restored to version {self._version}")

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def is_initialized(self) -> bool:
        """Whether engine is initialized with state."""
        return self._initialized

    @property
    def entity_count(self) -> int:
        """Number of entities in state."""
        if self._state is None:
            return 0
        return self._state.entity_count

    @property
    def relation_count(self) -> int:
        """Number of relations in state."""
        if self._state is None:
            return 0
        return self._state.relation_count


# =============================================================================
# Singleton Access
# =============================================================================

_engine: WorldModelEngine | None = None


@register_singleton(
    name="world_model_engine",
    lifecycle="lazy",
    description="World model reasoning engine",
)
def get_world_model_engine() -> WorldModelEngine:
    """
    Get or create singleton WorldModelEngine.

    Returns:
        WorldModelEngine instance (may need async initialization)
    """
    global _engine
    if _engine is None:
        _engine = WorldModelEngine()
    return _engine


async def init_world_model_engine(
    spec_paths: list[str] | None = None,
    initial_state: dict[str, Any] | None = None,
) -> WorldModelEngine:
    """
    Initialize singleton engine with specifications (async).

    Args:
        spec_paths: Paths to specification files
        initial_state: Optional initial state to restore from

    Returns:
        Initialized WorldModelEngine
    """
    global _engine
    _engine = WorldModelEngine()

    if spec_paths:
        _engine.load_specs(spec_paths)

    await _engine.initialize_state(initial_state)
    return _engine


def reset_world_model_engine() -> None:
    """Reset the singleton engine (for testing)."""
    global _engine
    _engine = None


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-012",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "async",
        "config",
        "debugging",
        "engine",
        "event-driven",
        "learning",
        "logging",
        "rest-api",
        "testing",
        "tracing",
    ],
    "keywords": [
        "async",
        "causal",
        "core",
        "count",
        "engine",
        "entity",
        "graph",
        "ingestor",
    ],
    "business_value": "Load specifications from YAML Initialize and manage state (async) Process incoming memory packets (async) Answer queries against current state (async) Run simulations (async, future) Memory Substrate:",
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
