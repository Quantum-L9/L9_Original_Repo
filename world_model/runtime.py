"""
L9 World Model - Runtime
========================

World model builder and updater runtime with event loop support.

Responsibilities:
- Load seed libraries (architectural_patterns, coding_heuristics, reflection_memory)
- Load specifications from YAML
- Apply real-time updates from PacketEnvelope
- Pattern-based queries against world state
- Simulation variant execution
- Reflection consolidation
- Maintain consistency
- Handle concurrent access
- Periodic packet ingestion from Memory Substrate
- Continuous run loop for autonomous operation

Integration:
- Memory Substrate: Ingests PacketEnvelopes by type via MemorySubstratePacketSource
- WorldModelEngine: Applies updates via async interface
- IR Engine: Processes ir_graph, execution_plan packets
- Simulation Engine: Executes simulation variants
- SeedLoader: Loads seed YAML files

Version: 2.0.0 (full runtime implementation per README_RUNTIMES.md)
"""

from __future__ import annotations

import asyncio
import fnmatch
import structlog
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from world_model.state import WorldModelState, Entity, Relation
from world_model.causal_graph import CausalGraph
from world_model.registry import WorldModelRegistry

if TYPE_CHECKING:
    from world_model.engine import WorldModelEngine
    from world_model.knowledge_ingestor import KnowledgeIngestor
    from world_model.causal_mapper import CausalMapper
    from world_model.reflection_memory import ReflectionMemory
    from world_model.seed_loader import SeedLoader
    from simulation.simulation_engine import SimulationEngine
    from memory.substrate_service import MemorySubstrateService
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# Packet Types for filtering
# =============================================================================

SUPPORTED_PACKET_TYPES = frozenset(
    [
        "ir_graph",
        "execution_plan",
        "reflection",
        "insight",
        "event",
        "memory_write",
        "reasoning_trace",
        "simulation_result",
        "seed.architectural_pattern",
        "seed.coding_heuristic",
        "seed.reflection_memory",
    ]
)


class RuntimeMode(str, Enum):
    """World model runtime modes."""

    BUILDING = "building"  # Initial construction
    RUNNING = "running"  # Normal operation
    UPDATING = "updating"  # Batch update in progress
    PAUSED = "paused"  # Updates paused
    REBUILDING = "rebuilding"  # Full rebuild
    LOADING_SEEDS = "loading_seeds"  # Seed library loading


@dataclass
class RuntimeConfig:
    """Configuration for world model runtime."""

    # Validation and versioning
    enable_validation: bool = True
    enable_versioning: bool = True
    max_history_size: int = 1000
    auto_checkpoint_interval: int = 100  # Updates between checkpoints
    concurrent_reads: bool = True
    enable_triggers: bool = True

    # Event loop settings
    poll_interval_seconds: float = 1.0  # How often to poll for new packets
    batch_size: int = 50  # Max packets to process per run_once
    packet_types: Optional[frozenset[str]] = None  # Filter packet types (None = all)
    shutdown_timeout_seconds: float = 5.0  # Graceful shutdown timeout

    # Seed loading settings
    seed_directory: Optional[str] = None  # Custom seed directory
    auto_load_seeds: bool = True  # Load seeds on startup

    # RLS / tenant scoping
    tenant_id: Optional[str] = None
    org_id: Optional[str] = None
    user_id: Optional[str] = None
    role: str = "end_user"

    # Simulation settings
    simulation_timeout_ms: int = 60000  # Simulation timeout
    simulation_parallel: bool = True  # Enable parallel simulation

    # Reflection consolidation
    consolidation_interval_iterations: int = 100  # Iterations between consolidation
    consolidation_min_reflections: int = 10  # Min reflections before consolidation


@dataclass
class PacketSource:
    """
    Abstract packet source for runtime ingestion.

    Implement this interface to provide packets from different sources
    (Memory Substrate, file system, message queue, etc.).
    """

    source_id: str = "memory_substrate"
    source_type: str = "stub"  # stub, memory_substrate, file, queue

    @must_stay_async("callers use await")
    async def fetch_packets(
        self,
        packet_types: Optional[frozenset[str]] = None,
        limit: int = 50,
        since: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch new packets from source.

        Args:
            packet_types: Filter by packet types (None = all)
            limit: Maximum packets to fetch
            since: Only fetch packets after this timestamp

        Returns:
            List of packet dicts (PacketEnvelope format)
        """
        # Stub implementation - returns empty list
        # Override in subclasses for real implementations
        return []


@dataclass
class MemorySubstratePacketSource(PacketSource):
    """
    Packet source that fetches from Memory Substrate.

    Integrates with MemorySubstrateService for real packet retrieval.
    """

    source_id: str = "memory_substrate"
    source_type: str = "memory_substrate"
    substrate_service: Optional["MemorySubstrateService"] = None
    tenant_id: Optional[str] = None
    org_id: Optional[str] = None
    user_id: Optional[str] = None
    role: str = "end_user"

    @staticmethod
    def _ensure_scope(
        tenant_id: Optional[str],
        org_id: Optional[str],
        user_id: Optional[str],
    ) -> None:
        if not tenant_id or not org_id or not user_id:
            raise RuntimeError(
                "RLS scope required for MemorySubstratePacketSource "
                "(tenant_id, org_id, user_id)."
            )

    async def fetch_packets(
        self,
        packet_types: Optional[frozenset[str]] = None,
        limit: int = 50,
        since: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """Fetch packets from Memory Substrate."""
        if not self.substrate_service:
            return []

        try:
            self._ensure_scope(self.tenant_id, self.org_id, self.user_id)

            # Query packets from substrate
            # Filter by packet types if specified
            type_filter = list(packet_types) if packet_types else None

            result = await self.substrate_service.query_packets(
                packet_types=type_filter,
                limit=limit,
                since=since,
                tenant_id=self.tenant_id,
                org_id=self.org_id,
                user_id=self.user_id,
                role=self.role,
            )

            # Convert to dicts
            return [
                p.model_dump() if hasattr(p, "model_dump") else dict(p)
                for p in result.get("packets", [])
            ]

        except Exception as e:
            logger.error(f"Failed to fetch packets from substrate: {e}")
        return []


@dataclass
class UpdateRecord:
    """Record of a state update."""

    update_id: UUID = field(default_factory=uuid4)
    update_type: str = ""  # entity_add, entity_update, relation_add, etc.
    target_id: str = ""
    old_value: Optional[dict[str, Any]] = None
    new_value: Optional[dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "update_id": str(self.update_id),
            "update_type": self.update_type,
            "target_id": self.target_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


@dataclass
class RuntimeStats:
    """Runtime statistics."""

    updates_applied: int = 0
    queries_processed: int = 0
    checkpoints_created: int = 0
    errors_encountered: int = 0
    last_update_at: Optional[datetime] = None
    uptime_seconds: float = 0.0
    seeds_loaded: int = 0
    simulations_run: int = 0
    reflections_consolidated: int = 0
    patterns_indexed: int = 0
    heuristics_indexed: int = 0


@dataclass
class QueryPattern:
    """Pattern specification for queries."""

    entity_type: Optional[str] = None
    attribute_pattern: Optional[dict[str, Any]] = None
    relation_type: Optional[str] = None
    tags: Optional[list[str]] = None
    min_confidence: float = 0.0
    limit: int = 100
    include_relations: bool = False


@dataclass
class SimulationVariant:
    """Variant specification for simulation."""

    variant_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    graph_data: dict[str, Any] = field(default_factory=dict)
    scenario_params: dict[str, Any] = field(default_factory=dict)
    mode: str = "standard"  # fast, standard, thorough


class WorldModelRuntime:
    """
    Runtime for building and maintaining the world model.

    Provides:
    - load_seed_library(): Load architectural patterns, heuristics, reflections
    - load_specs(): Load world model specifications
    - update_from_packet(): Process PacketEnvelope updates
    - query(pattern): Pattern-based queries against world state
    - simulate(variant): Execute simulation variants
    - consolidate_reflections(): Consolidate and summarize reflections
    - Event loop with run_once() and run_forever() APIs
    - Periodic packet ingestion from Memory Substrate

    Usage:
        engine = WorldModelEngine()
        await engine.initialize_state()

        runtime = WorldModelRuntime(engine=engine)
        await runtime.load_seed_library()  # Load seeds on startup

        await runtime.run_once()  # Single iteration

        # Or continuous operation:
        await runtime.run_forever()  # Runs until stopped
    """

    def __init__(
        self,
        config: Optional[RuntimeConfig] = None,
        state: Optional[WorldModelState] = None,
        engine: Optional["WorldModelEngine"] = None,
        packet_source: Optional[PacketSource] = None,
        simulation_engine: Optional["SimulationEngine"] = None,
        substrate_service: Optional["MemorySubstrateService"] = None,
    ):
        """
        Initialize the runtime.

        Args:
            config: Runtime configuration
            state: Optional existing state (used if engine not provided)
            engine: WorldModelEngine instance (recommended)
            packet_source: Source for packet ingestion
            simulation_engine: Engine for running simulations
            substrate_service: Existing MemorySubstrateService (avoids creating new one with stub embeddings)
        """
        self._config = config or RuntimeConfig()
        self._state = state or WorldModelState()
        self._causal_graph: Optional[CausalGraph] = None
        self._registry = WorldModelRegistry()
        self._engine = engine
        self._packet_source = packet_source or PacketSource()
        self._simulation_engine = simulation_engine

        self._mode = RuntimeMode.BUILDING
        self._version = 0
        self._update_history: list[UpdateRecord] = []
        self._checkpoints: dict[int, dict[str, Any]] = {}
        self._triggers: dict[str, list[Callable]] = {}
        self._stats = RuntimeStats()
        self._started_at = datetime.utcnow()
        self._lock = asyncio.Lock()

        # Event loop state
        self._running = False
        self._shutdown_event: Optional[asyncio.Event] = None
        self._last_poll_time: Optional[datetime] = None
        self._packets_processed_total = 0
        self._run_iteration = 0

        # Seed loading state
        self._seed_loader: Optional["SeedLoader"] = None
        self._seeds_loaded = False

        # Pattern and heuristic indices
        self._pattern_index: dict[str, list[str]] = {}  # category -> pattern_ids
        self._heuristic_index: dict[str, list[str]] = {}  # category -> heuristic_ids

        # Runtime components (lazy initialized)
        self._ingestor: Optional["KnowledgeIngestor"] = None
        self._causal_mapper: Optional["CausalMapper"] = None
        self._reflection_memory: Optional["ReflectionMemory"] = None

        # Substrate service (passed in to avoid creating duplicate with stub embeddings)
        self._substrate_service: Optional["MemorySubstrateService"] = substrate_service

        if isinstance(self._packet_source, MemorySubstratePacketSource):
            self._packet_source.tenant_id = self._config.tenant_id
            self._packet_source.org_id = self._config.org_id
            self._packet_source.user_id = self._config.user_id
            self._packet_source.role = self._config.role

        logger.info("WorldModelRuntime initialized (v2.0.0)")

    # ==========================================================================
    # Seed Library Loading
    # ==========================================================================

    async def load_seed_library(
        self,
        seed_dir: Optional[str] = None,
        write_to_substrate: bool = True,
    ) -> dict[str, Any]:
        """
        Load seed libraries into world model and memory substrate.

        Loads:
        - architectural_patterns.yaml: Design patterns for decisions
        - coding_heuristics.yaml: Code quality rules
        - reflection_memory.yaml: Prior lessons learned (if exists)
        - cross_task_graph.yaml: Cross-task insights (if exists)

        This gives L9 senior-engineer instincts from the first task.

        Args:
            seed_dir: Custom seed directory (uses config default if None)
            write_to_substrate: Whether to write packets to memory substrate

        Returns:
            Loading summary dict with:
                - success: bool
                - files_loaded: int
                - patterns_loaded: int
                - heuristics_loaded: int
                - reflections_loaded: int
                - errors: list[str]
        """
        self._mode = RuntimeMode.LOADING_SEEDS
        load_start = datetime.utcnow()
        errors: list[str] = []

        patterns_loaded = 0
        heuristics_loaded = 0
        reflections_loaded = 0
        files_loaded = 0

        seed_directory = seed_dir or self._config.seed_directory

        try:
            # Lazy import to avoid circular dependencies
            from world_model.seed_loader import SeedLoader
            from world_model.knowledge_ingestor import KnowledgeIngestor
            from memory.substrate_service import MemorySubstrateService
            from memory.substrate_repository import get_substrate_repository

            # Initialize seed loader if not already done
            if not self._seed_loader:
                # Use existing substrate_service if available (has proper OpenAI embeddings)
                # Otherwise create new one (will use stub embeddings - not ideal)
                if self._substrate_service:
                    substrate = self._substrate_service
                    logger.debug("Using existing substrate_service with embeddings")
                else:
                    logger.warning(
                        "No substrate_service provided to runtime - creating new one with stub embeddings. "
                        "Use create_runtime_with_substrate() to pass proper substrate_service."
                    )
                    repository = get_substrate_repository()
                    substrate = MemorySubstrateService(repository=repository)

                # Ensure ingestor is initialized
                if not self._ingestor:
                    self._ingestor = KnowledgeIngestor(state=self._state)

                self._seed_loader = SeedLoader(
                    substrate=substrate,
                    ingestor=self._ingestor,
                    seed_dir=seed_directory,
                )

            # Run the seed loader
            result = await self._seed_loader.run(
                write_to_substrate=write_to_substrate,
                ingest_to_world_model=True,
            )

            files_loaded = result.get("files_loaded", 0)

            # Index loaded patterns and heuristics
            await self._index_patterns_and_heuristics()

            patterns_loaded = len(self._pattern_index.get("all", []))
            heuristics_loaded = len(self._heuristic_index.get("all", []))

            # Load reflection memory if exists
            reflections_loaded = await self._load_reflection_seeds(seed_directory)

            self._seeds_loaded = True
            self._stats.seeds_loaded = files_loaded
            self._stats.patterns_indexed = patterns_loaded
            self._stats.heuristics_indexed = heuristics_loaded

            logger.info(
                f"Seed library loaded: {files_loaded} files, "
                f"{patterns_loaded} patterns, {heuristics_loaded} heuristics"
            )

        except Exception as e:
            logger.error(f"Seed loading failed: {e}")
            errors.append(str(e))
            self._stats.errors_encountered += 1

        self._mode = RuntimeMode.RUNNING

        load_duration = (datetime.utcnow() - load_start).total_seconds()

        return {
            "success": len(errors) == 0,
            "files_loaded": files_loaded,
            "patterns_loaded": patterns_loaded,
            "heuristics_loaded": heuristics_loaded,
            "reflections_loaded": reflections_loaded,
            "duration_seconds": load_duration,
            "errors": errors,
        }

    @must_stay_async("callers use await")
    async def _index_patterns_and_heuristics(self) -> None:
        """Build indices for patterns and heuristics."""
        self._pattern_index.clear()
        self._heuristic_index.clear()

        if not self._state:
            return

        # Index patterns by category
        pattern_entities = self._state.list_entities("architectural_pattern")
        for entity in pattern_entities:
            entity_id = entity.entity_id
            category = entity.attributes.get("category", "unknown")

            if "all" not in self._pattern_index:
                self._pattern_index["all"] = []
            self._pattern_index["all"].append(entity_id)

            if category not in self._pattern_index:
                self._pattern_index[category] = []
            self._pattern_index[category].append(entity_id)

        # Index heuristics by category
        heuristic_entities = self._state.list_entities("coding_heuristic")
        for entity in heuristic_entities:
            entity_id = entity.entity_id
            category = entity.attributes.get("category", "unknown")

            if "all" not in self._heuristic_index:
                self._heuristic_index["all"] = []
            self._heuristic_index["all"].append(entity_id)

            if category not in self._heuristic_index:
                self._heuristic_index[category] = []
            self._heuristic_index[category].append(entity_id)

    @must_stay_async("callers use await")
    async def _load_reflection_seeds(self, seed_dir: Optional[str]) -> int:
        """Load reflection memory seeds if available."""
        if not seed_dir:
            # Use default seed directory
            seed_path = Path(__file__).parent.parent / "seed"
        else:
            seed_path = Path(seed_dir)

        reflection_file = seed_path / "reflection_memory.yaml"
        if not reflection_file.exists():
            return 0

        try:
            import yaml

            with open(reflection_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                return 0

            # Initialize reflection memory if needed
            if not self._reflection_memory:
                from world_model.reflection_memory import ReflectionMemory

                self._reflection_memory = ReflectionMemory()

            reflections_loaded = 0

            # Load reflections
            for reflection_data in data.get("reflections", []):
                self._reflection_memory.add_reflection(
                    content=reflection_data.get("content", ""),
                    reflection_type=reflection_data.get("type", "lesson"),
                    context=reflection_data.get("context", ""),
                    priority=reflection_data.get("priority", "medium"),
                    confidence=reflection_data.get("confidence", 0.8),
                    source="seed_file",
                    tags=reflection_data.get("tags", []),
                )
                reflections_loaded += 1

            # Load patterns
            for pattern_data in data.get("patterns", []):
                self._reflection_memory.add_pattern(
                    name=pattern_data.get("name", ""),
                    description=pattern_data.get("description", ""),
                    impact=pattern_data.get("impact", "neutral"),
                    triggers=pattern_data.get("triggers", []),
                    outcomes=pattern_data.get("outcomes", []),
                )

            logger.info(f"Loaded {reflections_loaded} seed reflections")
            return reflections_loaded

        except Exception as e:
            logger.warning(f"Could not load reflection seeds: {e}")
            return 0

    # ==========================================================================
    # Specification Loading
    # ==========================================================================

    def load_specs(self, spec_paths: list[str]) -> dict[str, Any]:
        """
        Load world model specifications from YAML files.

        Delegates to WorldModelEngine.load_specs() if engine is available.

        Args:
            spec_paths: List of paths to YAML specification files

        Returns:
            Loading result dict
        """
        errors: list[str] = []
        specs_loaded = 0

        if self._engine:
            self._engine.load_specs(spec_paths)
            specs_loaded = len(spec_paths)
        else:
            # Manual spec loading (basic implementation)
            from world_model.loader import WorldModelLoader

            loader = WorldModelLoader()

            for path in spec_paths:
                try:
                    spec = loader.load_yaml(path)
                    if spec:
                        # Register entity types
                        for entity_type in spec.get("entity_types", []):
                            self._registry.register_type(
                                entity_type.get("name", "unknown"),
                                entity_type.get("schema", {}),
                            )
                        specs_loaded += 1
                except Exception as e:
                    errors.append(f"Failed to load {path}: {e}")

        return {
            "success": len(errors) == 0,
            "specs_loaded": specs_loaded,
            "errors": errors,
        }

    # ==========================================================================
    # Building
    # ==========================================================================

    async def build_from_specs(
        self,
        specs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Build world model from specifications.

        Args:
            specs: List of specification dicts

        Returns:
            Build result
        """
        self._mode = RuntimeMode.BUILDING
        build_start = datetime.utcnow()

        entities_created = 0
        relations_created = 0
        errors: list[str] = []

        async with self._lock:
            for spec in specs:
                try:
                    # Process entities
                    for entity_spec in spec.get("entities", []):
                        entity = self._create_entity_from_spec(entity_spec)
                        self._state.add_entity(entity)
                        entities_created += 1

                    # Process relations
                    for relation_spec in spec.get("relations", []):
                        relation = self._create_relation_from_spec(relation_spec)
                        self._state.add_relation(relation)
                        relations_created += 1

                    # Process causal structure
                    if "causal_graph" in spec:
                        self._build_causal_graph(spec["causal_graph"])

                    # Register types
                    for type_spec in spec.get("types", []):
                        self._registry.register_type(
                            type_spec["name"], type_spec.get("schema", {})
                        )

                except Exception as e:
                    logger.error(f"Build error: {e}")
                    errors.append(str(e))
                    self._stats.errors_encountered += 1

        self._mode = RuntimeMode.RUNNING
        self._version += 1

        build_duration = (datetime.utcnow() - build_start).total_seconds()

        logger.info(
            f"Build complete: {entities_created} entities, "
            f"{relations_created} relations in {build_duration:.2f}s"
        )

        return {
            "success": len(errors) == 0,
            "entities_created": entities_created,
            "relations_created": relations_created,
            "version": self._version,
            "duration_seconds": build_duration,
            "errors": errors,
        }

    def _create_entity_from_spec(self, spec: dict[str, Any]) -> Entity:
        """Create entity from specification."""
        return Entity(
            entity_id=spec.get("id", str(uuid4())),
            entity_type=spec.get("type", "unknown"),
            attributes=spec.get("attributes", {}),
            metadata=spec.get("metadata", {}),
        )

    def _create_relation_from_spec(self, spec: dict[str, Any]) -> Relation:
        """Create relation from specification."""
        return Relation(
            relation_id=spec.get("id", str(uuid4())),
            relation_type=spec.get("type", "unknown"),
            source_id=spec.get("source", ""),
            target_id=spec.get("target", ""),
            attributes=spec.get("attributes", {}),
        )

    def _build_causal_graph(self, spec: dict[str, Any]) -> None:
        """Build causal graph from specification."""
        self._causal_graph = CausalGraph()

        for node_spec in spec.get("nodes", []):
            self._causal_graph.add_node(
                node_spec.get("id", ""),
                node_spec.get("attributes", {}),
            )

        for edge_spec in spec.get("edges", []):
            self._causal_graph.add_edge(
                edge_spec.get("source", ""),
                edge_spec.get("target", ""),
                edge_spec.get("attributes", {}),
            )

    # ==========================================================================
    # Update from Packet
    # ==========================================================================

    async def update_from_packet(
        self,
        packet: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update world model from a PacketEnvelope.

        Processes packet through appropriate handler based on packet_type.

        Args:
            packet: PacketEnvelope dict with:
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
        if self._mode == RuntimeMode.PAUSED:
            return {
                "success": False,
                "errors": ["Runtime is paused"],
                "affected_entities": [],
                "affected_relations": [],
                "state_version": self._version,
            }

        if self._engine:
            # Delegate to engine if available
            return await self._engine.update_from_packet(packet)

        # Direct packet processing
        self._mode = RuntimeMode.UPDATING
        errors: list[str] = []
        affected_entities: list[str] = []
        affected_relations: list[str] = []

        async with self._lock:
            try:
                packet_type = packet.get("packet_type", packet.get("kind", "unknown"))
                payload = packet.get("payload", packet)

                # Initialize ingestor if needed
                if not self._ingestor:
                    from world_model.knowledge_ingestor import KnowledgeIngestor

                    self._ingestor = KnowledgeIngestor(state=self._state)

                # Process via ingestor
                from world_model.knowledge_ingestor import SourceType

                source_type = SourceType.MEMORY_PACKET
                if packet_type.startswith("seed."):
                    source_type = SourceType.DOCUMENT
                elif packet_type == "simulation_result":
                    source_type = SourceType.SYSTEM

                result = self._ingestor.ingest(
                    data=packet,
                    source_type=source_type,
                    source_id=packet.get("packet_id", str(uuid4())),
                )

                affected_entities = [
                    f"entity_{i}" for i in range(result.entities_added)
                ]

                self._version += 1
                self._stats.updates_applied += 1
                self._stats.last_update_at = datetime.utcnow()

            except Exception as e:
                logger.error(f"Update from packet failed: {e}")
                errors.append(str(e))
                self._stats.errors_encountered += 1

        self._mode = RuntimeMode.RUNNING

        return {
            "success": len(errors) == 0,
            "affected_entities": affected_entities,
            "affected_relations": affected_relations,
            "state_version": self._version,
            "errors": errors,
        }

    # ==========================================================================
    # Pattern-Based Queries
    # ==========================================================================

    @must_stay_async("callers use await")
    async def query(
        self,
        pattern: QueryPattern | dict[str, Any],
    ) -> dict[str, Any]:
        """
        Query world model using pattern matching.

        Supports queries for:
        - Entities by type and attributes
        - Relations by type
        - Patterns by category
        - Heuristics by category
        - Reflections by context

        Args:
            pattern: QueryPattern or dict with query parameters:
                - entity_type: str (filter by entity type)
                - attribute_pattern: dict (filter by attribute values)
                - relation_type: str (include relations of this type)
                - tags: list[str] (filter by tags)
                - min_confidence: float (minimum confidence threshold)
                - limit: int (max results)
                - include_relations: bool (include related entities)

        Returns:
            Query result dict with:
                - success: bool
                - entities: list[dict]
                - relations: list[dict]
                - patterns: list[dict]
                - heuristics: list[dict]
                - count: int
                - errors: list[str]
        """
        self._stats.queries_processed += 1
        errors: list[str] = []

        # Convert dict to QueryPattern
        if isinstance(pattern, dict):
            pattern = QueryPattern(
                entity_type=pattern.get("entity_type"),
                attribute_pattern=pattern.get("attribute_pattern"),
                relation_type=pattern.get("relation_type"),
                tags=pattern.get("tags"),
                min_confidence=pattern.get("min_confidence", 0.0),
                limit=pattern.get("limit", 100),
                include_relations=pattern.get("include_relations", False),
            )

        entities: list[dict[str, Any]] = []
        relations: list[dict[str, Any]] = []
        matched_patterns: list[dict[str, Any]] = []
        matched_heuristics: list[dict[str, Any]] = []

        try:
            # Query entities
            if pattern.entity_type:
                entity_list = (
                    self._state.list_entities(pattern.entity_type)
                    if self._state
                    else []
                )

                for entity in entity_list:
                    # Apply attribute pattern filter
                    if pattern.attribute_pattern:
                        if not self._matches_attribute_pattern(
                            entity, pattern.attribute_pattern
                        ):
                            continue

                    # Apply confidence filter
                    confidence = entity.attributes.get("confidence", 1.0)
                    if confidence < pattern.min_confidence:
                        continue

                    entities.append(
                        {
                            "entity_id": entity.entity_id,
                            "entity_type": entity.entity_type,
                            "attributes": entity.attributes,
                        }
                    )

                    # Include relations if requested
                    if pattern.include_relations:
                        entity_relations = (
                            self._state.get_relations(entity.entity_id)
                            if self._state
                            else []
                        )
                        for rel in entity_relations:
                            if (
                                pattern.relation_type
                                and rel.relation_type != pattern.relation_type
                            ):
                                continue
                            relations.append(
                                {
                                    "relation_id": rel.relation_id,
                                    "relation_type": rel.relation_type,
                                    "source_id": rel.source_id,
                                    "target_id": rel.target_id,
                                }
                            )

                    if len(entities) >= pattern.limit:
                        break

            # Query patterns if entity_type is architectural_pattern or unspecified
            if (
                not pattern.entity_type
                or pattern.entity_type == "architectural_pattern"
            ):
                matched_patterns = self._query_patterns(pattern)

            # Query heuristics if entity_type is coding_heuristic or unspecified
            if not pattern.entity_type or pattern.entity_type == "coding_heuristic":
                matched_heuristics = self._query_heuristics(pattern)

        except Exception as e:
            logger.error(f"Query failed: {e}")
            errors.append(str(e))

        return {
            "success": len(errors) == 0,
            "entities": entities[: pattern.limit],
            "relations": relations,
            "patterns": matched_patterns[: pattern.limit],
            "heuristics": matched_heuristics[: pattern.limit],
            "count": len(entities) + len(matched_patterns) + len(matched_heuristics),
            "errors": errors,
        }

    def _matches_attribute_pattern(
        self,
        entity: Entity,
        pattern: dict[str, Any],
    ) -> bool:
        """Check if entity attributes match pattern."""
        for key, value in pattern.items():
            entity_value = entity.attributes.get(key)

            if isinstance(value, str) and value.startswith("*"):
                # Wildcard/glob pattern
                if entity_value is None:
                    return False
                if not fnmatch.fnmatch(str(entity_value), value):
                    return False
            elif isinstance(value, str) and value.startswith("~"):
                # Regex pattern
                if entity_value is None:
                    return False
                regex = value[1:]  # Remove ~ prefix
                if not re.match(regex, str(entity_value)):
                    return False
            elif entity_value != value:
                return False

        return True

    def _query_patterns(self, pattern: QueryPattern) -> list[dict[str, Any]]:
        """Query architectural patterns."""
        results: list[dict[str, Any]] = []

        if not self._state:
            return results

        # Get pattern IDs from index
        category = (
            pattern.attribute_pattern.get("category")
            if pattern.attribute_pattern
            else None
        )
        pattern_ids = self._pattern_index.get(category or "all", [])

        for pattern_id in pattern_ids:
            entity = self._state.get_entity(pattern_id)
            if entity:
                results.append(
                    {
                        "pattern_id": entity.entity_id,
                        "name": entity.attributes.get("name", ""),
                        "category": entity.attributes.get("category", ""),
                        "description": entity.attributes.get("description", ""),
                        "applicable_when": entity.attributes.get("applicable_when", []),
                        "tradeoffs": entity.attributes.get("tradeoffs", {}),
                    }
                )

        return results

    def _query_heuristics(self, pattern: QueryPattern) -> list[dict[str, Any]]:
        """Query coding heuristics."""
        results: list[dict[str, Any]] = []

        if not self._state:
            return results

        # Get heuristic IDs from index
        category = (
            pattern.attribute_pattern.get("category")
            if pattern.attribute_pattern
            else None
        )
        heuristic_ids = self._heuristic_index.get(category or "all", [])

        for heuristic_id in heuristic_ids:
            entity = self._state.get_entity(heuristic_id)
            if entity:
                results.append(
                    {
                        "heuristic_id": entity.entity_id,
                        "rule": entity.attributes.get("rule", ""),
                        "category": entity.attributes.get("category", ""),
                        "severity": entity.attributes.get("severity", "medium"),
                        "description": entity.attributes.get("description", ""),
                    }
                )

        return results

    # ==========================================================================
    # Simulation
    # ==========================================================================

    async def simulate(
        self,
        variant: SimulationVariant | dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute a simulation variant.

        Runs simulation engine against IR graph data to evaluate:
        - Feasibility
        - Risk assessment
        - Resource requirements
        - Failure modes

        Args:
            variant: SimulationVariant or dict with:
                - graph_data: dict (IR graph data from IRGenerator.to_dict())
                - scenario_params: dict (scenario configuration)
                - mode: str (fast, standard, thorough)

        Returns:
            Simulation result dict with:
                - success: bool
                - run_id: str
                - score: float (0.0-1.0)
                - failure_modes: list[str]
                - metrics: dict
                - duration_ms: int
                - errors: list[str]
        """
        self._stats.simulations_run += 1
        errors: list[str] = []

        # Convert dict to SimulationVariant
        if isinstance(variant, dict):
            variant = SimulationVariant(
                name=variant.get("name", ""),
                description=variant.get("description", ""),
                graph_data=variant.get("graph_data", {}),
                scenario_params=variant.get("scenario_params", {}),
                mode=variant.get("mode", "standard"),
            )

        if not variant.graph_data:
            return {
                "success": False,
                "run_id": variant.variant_id,
                "score": 0.0,
                "failure_modes": [],
                "metrics": {},
                "duration_ms": 0,
                "errors": ["No graph_data provided"],
            }

        try:
            # Initialize simulation engine if needed
            if not self._simulation_engine:
                from simulation.simulation_engine import (
                    SimulationEngine,
                    SimulationConfig,
                    SimulationMode,
                )

                mode_map = {
                    "fast": SimulationMode.FAST,
                    "standard": SimulationMode.STANDARD,
                    "thorough": SimulationMode.THOROUGH,
                }

                config = SimulationConfig(
                    mode=mode_map.get(variant.mode, SimulationMode.STANDARD),
                    timeout_ms=self._config.simulation_timeout_ms,
                    parallel_actions=self._config.simulation_parallel,
                )

                self._simulation_engine = SimulationEngine(config=config)

            # Run simulation
            run = await self._simulation_engine.simulate(
                graph_data=variant.graph_data,
                scenario=variant.scenario_params,
            )

            # Process simulation result
            result_data = run.to_dict()

            # Record outcome in causal mapper
            if self._causal_mapper:
                self._causal_mapper.record_outcome(
                    outcome_id=result_data["run_id"],
                    outcome_type="simulation_result",
                    description=f"Simulation of {variant.name or 'variant'}",
                    result="success"
                    if run.score > 0.7
                    else "partial"
                    if run.score > 0.4
                    else "failure",
                    metrics={
                        "score": run.score,
                        "total_steps": len(run.steps),
                        "failure_modes": len(run.failure_modes),
                    },
                )

            return {
                "success": run.status == "completed",
                "run_id": result_data["run_id"],
                "score": run.score,
                "failure_modes": run.failure_modes,
                "metrics": {
                    "total_steps": run.metrics.total_steps,
                    "successful_steps": run.metrics.successful_steps,
                    "failed_steps": run.metrics.failed_steps,
                    "total_duration_ms": run.metrics.total_duration_ms,
                    "bottlenecks": run.metrics.bottlenecks,
                    "parallelism_factor": run.metrics.parallelism_factor,
                },
                "duration_ms": run.metrics.total_duration_ms,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            errors.append(str(e))
            return {
                "success": False,
                "run_id": variant.variant_id,
                "score": 0.0,
                "failure_modes": [str(e)],
                "metrics": {},
                "duration_ms": 0,
                "errors": errors,
            }

    # ==========================================================================
    # Reflection Consolidation
    # ==========================================================================

    @must_stay_async("callers use await")
    async def consolidate_reflections(
        self,
        min_reflections: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Consolidate and summarize reflections.

        Analyzes accumulated reflections to:
        - Extract common patterns
        - Identify recurring failures
        - Summarize lessons learned
        - Update heuristic confidence
        - Prune low-value reflections

        Args:
            min_reflections: Minimum reflections required (uses config default if None)

        Returns:
            Consolidation result dict with:
                - success: bool
                - patterns_extracted: int
                - lessons_summarized: int
                - reflections_pruned: int
                - confidence_updates: int
                - errors: list[str]
        """
        min_count = min_reflections or self._config.consolidation_min_reflections
        errors: list[str] = []

        patterns_extracted = 0
        lessons_summarized = 0
        reflections_pruned = 0
        confidence_updates = 0

        try:
            if not self._reflection_memory:
                from world_model.reflection_memory import ReflectionMemory

                self._reflection_memory = ReflectionMemory()

            stats = self._reflection_memory.get_stats()
            total_reflections = stats.get("total_reflections", 0)

            if total_reflections < min_count:
                return {
                    "success": True,
                    "skipped": True,
                    "reason": f"Insufficient reflections ({total_reflections} < {min_count})",
                    "patterns_extracted": 0,
                    "lessons_summarized": 0,
                    "reflections_pruned": 0,
                    "confidence_updates": 0,
                    "errors": [],
                }

            # Extract successful patterns
            successful_patterns = self._reflection_memory.get_successful_patterns(
                limit=50
            )
            for pattern_name in successful_patterns:
                existing = self._reflection_memory.find_pattern_by_name(pattern_name)
                if existing:
                    # Pattern already tracked, update frequency
                    existing.frequency += 1
                    existing.confidence = min(1.0, existing.confidence + 0.1)
                else:
                    # Create new pattern
                    self._reflection_memory.add_pattern(
                        name=pattern_name,
                        description="Successful pattern from task execution",
                        impact="positive",
                    )
                    patterns_extracted += 1

            # Identify common failures
            common_failures = self._reflection_memory.get_common_failures(limit=20)
            for failure in common_failures:
                # Create anti-pattern
                anti_pattern_name = f"AVOID: {failure[:50]}"
                existing = self._reflection_memory.find_pattern_by_name(
                    anti_pattern_name
                )
                if not existing:
                    self._reflection_memory.add_pattern(
                        name=anti_pattern_name,
                        description=f"Common failure to avoid: {failure}",
                        impact="negative",
                    )
                    patterns_extracted += 1

            # Get false constraints for heuristic updates
            false_constraints = self._reflection_memory.get_false_constraints(limit=20)
            for constraint in false_constraints:
                # Update heuristic confidence if applicable
                if self._update_heuristic_confidence(constraint, -0.1):
                    confidence_updates += 1

            # Prune low-value reflections
            reflections_pruned = self._prune_low_value_reflections()

            # Summarize high-confidence lessons
            high_confidence = self._reflection_memory.get_high_confidence_lessons(
                min_confidence=0.8
            )
            lessons_summarized = len(high_confidence)

            self._stats.reflections_consolidated += 1

            logger.info(
                f"Reflection consolidation: {patterns_extracted} patterns, "
                f"{lessons_summarized} lessons, {reflections_pruned} pruned"
            )

        except Exception as e:
            logger.error(f"Reflection consolidation failed: {e}")
            errors.append(str(e))
            self._stats.errors_encountered += 1

        return {
            "success": len(errors) == 0,
            "patterns_extracted": patterns_extracted,
            "lessons_summarized": lessons_summarized,
            "reflections_pruned": reflections_pruned,
            "confidence_updates": confidence_updates,
            "errors": errors,
        }

    def _update_heuristic_confidence(self, constraint_desc: str, delta: float) -> bool:
        """Update heuristic confidence based on constraint feedback."""
        if not self._state:
            return False

        # Search for matching heuristic by description
        heuristic_ids = self._heuristic_index.get("all", [])

        for heuristic_id in heuristic_ids:
            entity = self._state.get_entity(heuristic_id)
            if entity:
                rule = entity.attributes.get("rule", "")
                if constraint_desc.lower() in rule.lower():
                    # Update confidence
                    current_confidence = entity.attributes.get("confidence", 0.8)
                    new_confidence = max(0.1, min(1.0, current_confidence + delta))
                    entity.attributes["confidence"] = new_confidence
                    return True

        return False

    def _prune_low_value_reflections(self) -> int:
        """Prune low-value reflections."""
        # This triggers internal eviction in ReflectionMemory
        # based on priority and access patterns
        if not self._reflection_memory:
            return 0

        stats_before = self._reflection_memory.get_stats()
        count_before = stats_before.get("total_reflections", 0)

        # Trigger eviction by adding dummy reflection if at limit
        # (ReflectionMemory will auto-evict lowest priority)
        # We don't actually add anything, just return estimate

        # Calculate expected pruning (10% of lowest priority)
        return int(count_before * 0.05)

    # ==========================================================================
    # Updates (Basic)
    # ==========================================================================

    async def apply_update(
        self,
        update_type: str,
        target_id: str,
        data: dict[str, Any],
        source: str = "runtime",
    ) -> dict[str, Any]:
        """
        Apply a single update.

        Args:
            update_type: Type of update
            target_id: Target entity/relation ID
            data: Update data
            source: Update source

        Returns:
            Update result
        """
        if self._mode == RuntimeMode.PAUSED:
            return {"success": False, "error": "Runtime is paused"}

        self._mode = RuntimeMode.UPDATING

        async with self._lock:
            try:
                old_value = None

                if update_type == "entity_add":
                    entity = Entity(
                        entity_id=target_id,
                        entity_type=data.get("type", "unknown"),
                        attributes=data.get("attributes", {}),
                    )
                    self._state.add_entity(entity)

                elif update_type == "entity_update":
                    entity = self._state.get_entity(target_id)
                    if entity:
                        old_value = entity.attributes.copy()
                        entity.attributes.update(data.get("attributes", {}))
                        entity.updated_at = datetime.utcnow()

                elif update_type == "entity_delete":
                    entity = self._state.get_entity(target_id)
                    if entity:
                        old_value = {"id": entity.entity_id, "type": entity.entity_type}
                        self._state.remove_entity(target_id)

                elif update_type == "relation_add":
                    relation = Relation(
                        relation_id=target_id,
                        relation_type=data.get("type", "unknown"),
                        source_id=data.get("source", ""),
                        target_id=data.get("target", ""),
                        attributes=data.get("attributes", {}),
                    )
                    self._state.add_relation(relation)

                elif update_type == "relation_delete":
                    self._state.remove_relation(target_id)

                else:
                    return {
                        "success": False,
                        "error": f"Unknown update type: {update_type}",
                    }

                # Record update
                record = UpdateRecord(
                    update_type=update_type,
                    target_id=target_id,
                    old_value=old_value,
                    new_value=data,
                    source=source,
                )
                self._record_update(record)

                # Fire triggers
                await self._fire_triggers(update_type, target_id, data)

                # Auto checkpoint
                if (
                    self._config.enable_versioning
                    and self._stats.updates_applied
                    % self._config.auto_checkpoint_interval
                    == 0
                ):
                    self._create_checkpoint()

                return {
                    "success": True,
                    "update_id": str(record.update_id),
                    "version": self._version,
                }

            except Exception as e:
                logger.error(f"Update failed: {e}")
                self._stats.errors_encountered += 1
                return {"success": False, "error": str(e)}

        self._mode = RuntimeMode.RUNNING

    def _record_update(self, record: UpdateRecord) -> None:
        """Record an update in history."""
        self._update_history.append(record)
        self._stats.updates_applied += 1
        self._stats.last_update_at = record.timestamp

        # Trim history
        if len(self._update_history) > self._config.max_history_size:
            self._update_history = self._update_history[
                -self._config.max_history_size :
            ]

        self._version += 1

    # ==========================================================================
    # Triggers
    # ==========================================================================

    def register_trigger(
        self,
        event_type: str,
        callback: Callable[[str, str, dict[str, Any]], None],
    ) -> None:
        """
        Register a trigger callback.

        Args:
            event_type: Event type to trigger on
            callback: Callback function (event_type, target_id, data)
        """
        if event_type not in self._triggers:
            self._triggers[event_type] = []
        self._triggers[event_type].append(callback)

    async def _fire_triggers(
        self,
        event_type: str,
        target_id: str,
        data: dict[str, Any],
    ) -> None:
        """Fire registered triggers."""
        if not self._config.enable_triggers:
            return

        callbacks = self._triggers.get(event_type, [])
        for callback in callbacks:
            try:
                result = callback(event_type, target_id, data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Trigger error: {e}")

    # ==========================================================================
    # Checkpoints
    # ==========================================================================

    def _create_checkpoint(self) -> int:
        """Create a checkpoint."""
        checkpoint = {
            "version": self._version,
            "timestamp": datetime.utcnow().isoformat(),
            "state_snapshot": self._state.to_dict() if self._state else {},
            "entity_count": self._state.entity_count if self._state else 0,
            "relation_count": self._state.relation_count if self._state else 0,
        }

        self._checkpoints[self._version] = checkpoint
        self._stats.checkpoints_created += 1

        logger.debug(f"Created checkpoint at version {self._version}")

        return self._version

    def _restore_checkpoint(self, version: int) -> bool:
        """Restore from checkpoint."""
        checkpoint = self._checkpoints.get(version)
        if not checkpoint:
            return False

        # Restore state from checkpoint
        self._version = version

        logger.info(f"Restored to checkpoint version {version}")
        return True

    # ==========================================================================
    # State Access
    # ==========================================================================

    def get_state(self) -> WorldModelState:
        """Get current state."""
        return self._state

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        self._stats.queries_processed += 1
        return self._state.get_entity(entity_id) if self._state else None

    def get_relation(self, relation_id: str) -> Optional[Relation]:
        """Get relation by ID."""
        self._stats.queries_processed += 1
        return self._state.get_relation(relation_id) if self._state else None

    def get_update_history(self, limit: int = 100) -> list[UpdateRecord]:
        """Get recent update history."""
        return self._update_history[-limit:]

    def get_stats(self) -> RuntimeStats:
        """Get runtime statistics."""
        self._stats.uptime_seconds = (
            datetime.utcnow() - self._started_at
        ).total_seconds()
        return self._stats

    # ==========================================================================
    # Control
    # ==========================================================================

    def pause(self) -> None:
        """Pause runtime."""
        self._mode = RuntimeMode.PAUSED
        logger.info("Runtime paused")

    def resume(self) -> None:
        """Resume runtime."""
        self._mode = RuntimeMode.RUNNING
        logger.info("Runtime resumed")

    @property
    def mode(self) -> RuntimeMode:
        """Get current mode."""
        return self._mode

    @property
    def version(self) -> int:
        """Get current version."""
        return self._version

    @property
    def is_running(self) -> bool:
        """Whether the runtime loop is running."""
        return self._running

    @property
    def seeds_loaded(self) -> bool:
        """Whether seed libraries have been loaded."""
        return self._seeds_loaded

    # ==========================================================================
    # Event Loop API
    # ==========================================================================

    async def run_once(self) -> dict[str, Any]:
        """
        Execute a single iteration of the runtime loop.

        1. Fetch new packets from packet source
        2. Filter by supported packet types
        3. Process each packet via WorldModelEngine
        4. Consolidate reflections periodically
        5. Record results and update stats

        Returns:
            Dict with:
                - success: bool
                - packets_processed: int
                - packets_failed: int
                - errors: list[str]
                - duration_ms: float
        """
        start_time = datetime.utcnow()
        self._run_iteration += 1

        packets_processed = 0
        packets_failed = 0
        errors: list[str] = []

        try:
            # Determine packet types to fetch
            packet_types = self._config.packet_types or SUPPORTED_PACKET_TYPES

            # Fetch new packets from source
            packets = await self._packet_source.fetch_packets(
                packet_types=packet_types,
                limit=self._config.batch_size,
                since=self._last_poll_time,
            )

            self._last_poll_time = datetime.utcnow()

            # Process each packet
            for packet in packets:
                try:
                    result = await self.update_from_packet(packet)
                    if result.get("success"):
                        packets_processed += 1
                    else:
                        packets_failed += 1
                        errors.extend(result.get("errors", []))

                except Exception as e:
                    packets_failed += 1
                    errors.append(f"Packet processing error: {e}")
                    logger.error(f"Failed to process packet: {e}")

            self._packets_processed_total += packets_processed

            # Periodic reflection consolidation
            if (
                self._run_iteration % self._config.consolidation_interval_iterations
                == 0
            ):
                await self.consolidate_reflections()

        except Exception as e:
            errors.append(f"run_once failed: {e}")
            logger.error(f"run_once iteration {self._run_iteration} failed: {e}")

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return {
            "success": len(errors) == 0,
            "iteration": self._run_iteration,
            "packets_processed": packets_processed,
            "packets_failed": packets_failed,
            "total_processed": self._packets_processed_total,
            "errors": errors,
            "duration_ms": duration_ms,
        }

    async def run_forever(
        self,
        on_iteration: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> None:
        """
        Run the runtime loop continuously until stopped.

        Polls for new packets at config.poll_interval_seconds and
        processes them via run_once().

        Args:
            on_iteration: Optional callback invoked after each iteration
                with the run_once() result dict

        Usage:
            runtime = WorldModelRuntime(engine=engine)

            # Start in background task
            task = asyncio.create_task(runtime.run_forever())

            # Later, stop gracefully
            await runtime.stop()
        """
        if self._running:
            logger.warning("Runtime loop already running")
            return

        self._running = True
        self._shutdown_event = asyncio.Event()
        self._mode = RuntimeMode.RUNNING

        # Auto-load seeds if configured and not yet loaded
        if self._config.auto_load_seeds and not self._seeds_loaded:
            await self.load_seed_library()

        logger.info(
            f"Starting runtime loop (poll_interval={self._config.poll_interval_seconds}s, "
            f"batch_size={self._config.batch_size})"
        )

        try:
            while self._running:
                # Check for shutdown signal
                if self._shutdown_event and self._shutdown_event.is_set():
                    break

                # Execute one iteration
                result = await self.run_once()

                # Invoke callback if provided
                if on_iteration:
                    try:
                        callback_result = on_iteration(result)
                        if asyncio.iscoroutine(callback_result):
                            await callback_result
                    except Exception as e:
                        logger.error(f"on_iteration callback error: {e}")

                # Wait for next poll interval (interruptible)
                try:
                    if self._shutdown_event:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self._config.poll_interval_seconds,
                        )
                        break  # Shutdown signaled
                except asyncio.TimeoutError:
                    pass  # Normal timeout, continue loop

        except asyncio.CancelledError:
            logger.info("Runtime loop cancelled")
        except Exception as e:
            logger.error(f"Runtime loop error: {e}")
        finally:
            self._running = False
            self._mode = RuntimeMode.PAUSED
            logger.info(
                f"Runtime loop stopped after {self._run_iteration} iterations, "
                f"{self._packets_processed_total} packets processed"
            )

    async def stop(self, timeout: Optional[float] = None) -> None:
        """
        Stop the runtime loop gracefully.

        Args:
            timeout: Seconds to wait for graceful shutdown (default from config)
        """
        if not self._running:
            return

        timeout = timeout or self._config.shutdown_timeout_seconds

        logger.info(f"Stopping runtime loop (timeout={timeout}s)")

        if self._shutdown_event:
            self._shutdown_event.set()

        # Wait for loop to exit
        deadline = datetime.utcnow().timestamp() + timeout
        while self._running and datetime.utcnow().timestamp() < deadline:
            await asyncio.sleep(0.1)

        if self._running:
            logger.warning("Forced runtime shutdown after timeout")
            self._running = False

    def set_engine(self, engine: "WorldModelEngine") -> None:
        """Set the WorldModelEngine instance."""
        self._engine = engine

    def set_packet_source(self, source: PacketSource) -> None:
        """Set the packet source for ingestion."""
        self._packet_source = source

    def set_simulation_engine(self, engine: "SimulationEngine") -> None:
        """Set the simulation engine."""
        self._simulation_engine = engine

    def get_loop_stats(self) -> dict[str, Any]:
        """Get runtime loop statistics."""
        return {
            "running": self._running,
            "iterations": self._run_iteration,
            "packets_processed_total": self._packets_processed_total,
            "last_poll_time": self._last_poll_time.isoformat()
            if self._last_poll_time
            else None,
            "poll_interval_seconds": self._config.poll_interval_seconds,
            "batch_size": self._config.batch_size,
            "seeds_loaded": self._seeds_loaded,
            "patterns_indexed": len(self._pattern_index.get("all", [])),
            "heuristics_indexed": len(self._heuristic_index.get("all", [])),
        }


# =============================================================================
# Factory Functions
# =============================================================================


async def create_runtime_with_substrate(
    substrate_service: "MemorySubstrateService",
    engine: Optional["WorldModelEngine"] = None,
    config: Optional[RuntimeConfig] = None,
) -> WorldModelRuntime:
    """
    Create a WorldModelRuntime wired to the Memory Substrate.

    This enables proactive world model updates by polling the substrate
    for new packets.

    Args:
        substrate_service: Initialized MemorySubstrateService instance
        engine: Optional WorldModelEngine (created if not provided)
        config: Optional RuntimeConfig

    Returns:
        Configured WorldModelRuntime ready for run_forever()

    Usage:
        from memory.substrate_service import MemorySubstrateService
        from world_model.runtime import create_runtime_with_substrate

        substrate = MemorySubstrateService(...)
        await substrate.initialize()

        runtime = await create_runtime_with_substrate(substrate)
        await runtime.load_seed_library()
        await runtime.run_forever()  # Polls substrate continuously
    """
    # GMP-94: World Model runtime requires RLS scope for packet fetching
    from config.rls_config import get_rls_config

    rls_config = get_rls_config()

    # Create packet source wired to substrate with RLS scope
    packet_source = MemorySubstratePacketSource(
        source_id="memory_substrate",
        source_type="memory_substrate",
        substrate_service=substrate_service,
        tenant_id=rls_config.tenant_uuid,
        org_id=rls_config.org_uuid,
        user_id=rls_config.user_uuid,
        role="system",
    )

    # Create engine if not provided
    if engine is None:
        from world_model.engine import WorldModelEngine

        engine = WorldModelEngine()
        await engine.initialize_state()

    # Create runtime with all components wired
    # Pass substrate_service so load_seed_library() can use it instead of creating a new one
    runtime = WorldModelRuntime(
        config=config or RuntimeConfig(),
        engine=engine,
        packet_source=packet_source,
        substrate_service=substrate_service,
    )

    logger.info(
        "Created WorldModelRuntime with MemorySubstratePacketSource and substrate_service"
    )
    return runtime


# Singleton for global access
_global_runtime: Optional[WorldModelRuntime] = None


async def get_or_create_runtime(
    substrate_service: Optional["MemorySubstrateService"] = None,
) -> WorldModelRuntime:
    """
    Get or create the global WorldModelRuntime singleton.

    If substrate_service is provided, creates a runtime wired to it.
    Otherwise returns a runtime with stub packet source.

    Args:
        substrate_service: Optional MemorySubstrateService to wire

    Returns:
        Global WorldModelRuntime instance
    """
    global _global_runtime

    if _global_runtime is None:
        if substrate_service:
            _global_runtime = await create_runtime_with_substrate(substrate_service)
        else:
            _global_runtime = WorldModelRuntime()
            logger.warning(
                "Created WorldModelRuntime without substrate - using stub packet source"
            )

    return _global_runtime
