"""
L9 World Model - Knowledge Ingestor
===================================

Ingests knowledge from various sources into the world model.

Sources:
- Memory packets (PacketEnvelope format)
- IR graphs (from ir_generator.to_packet_payload())
- Execution plans (from ir_to_plan_adapter.to_memory_packet())
- Simulation results (from SimulationEngine)
- Seed YAML files (architectural_patterns, coding_heuristics)
- External documents
- API responses
- User inputs

Capabilities:
- ingest_seed_yaml(): Direct YAML ingestion
- ingest_packet(): PacketEnvelope processing
- ingest_simulation_result(): Simulation outcome processing
- normalize_architectural_patterns(): Pattern normalization
- normalize_coding_heuristics(): Heuristic normalization

Integration:
- Memory Substrate: Receives PacketEnvelopes
- IR Engine: Processes ir_graph, execution_plan packets
- Simulation Engine: Ingests simulation results
- Seed Loader: Loads YAML seed files

Version: 2.0.0 (full ingestor implementation per README_RUNTIMES.md)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Knowledge Ingestor",
    "module_version": "2.0.0 (full ingestor implementation per README_RUNTIMES.md)",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "knowledge_ingestor",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "world_model.__init__",
            "world_model.engine",
            "world_model.runtime",
            "world_model.seed_loader",
            "world_model.world_model_service",
        ],
    },
}
# ============================================================================

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import structlog

from world_model.state import Entity, Relation, WorldModelState

if TYPE_CHECKING:
    from world_model.service import WorldModelService

logger = structlog.get_logger(__name__)


class SourceType(str, Enum):
    """Types of knowledge sources."""

    MEMORY_PACKET = "memory_packet"
    DOCUMENT = "document"
    API = "api"
    USER_INPUT = "user_input"
    SYSTEM = "system"
    IR_GRAPH = "ir_graph"
    REFLECTION = "reflection"
    SIMULATION_RESULT = "simulation_result"
    SEED_YAML = "seed_yaml"


@dataclass
class IngestResult:
    """Result of knowledge ingestion."""

    ingest_id: UUID = field(default_factory=uuid4)
    source_type: SourceType = SourceType.SYSTEM
    success: bool = False
    entities_added: int = 0
    entities_updated: int = 0
    relations_added: int = 0
    facts_extracted: int = 0
    patterns_normalized: int = 0
    heuristics_normalized: int = 0
    errors: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ingest_id": str(self.ingest_id),
            "source_type": self.source_type.value,
            "success": self.success,
            "entities_added": self.entities_added,
            "entities_updated": self.entities_updated,
            "relations_added": self.relations_added,
            "facts_extracted": self.facts_extracted,
            "patterns_normalized": self.patterns_normalized,
            "heuristics_normalized": self.heuristics_normalized,
            "errors": self.errors,
        }


@dataclass
class ExtractedFact:
    """A fact extracted from source."""

    fact_id: UUID = field(default_factory=uuid4)
    fact_type: str = ""  # entity, relation, attribute
    subject: str = ""
    predicate: str = ""
    object: str = ""
    confidence: float = 1.0
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedPattern:
    """A normalized architectural pattern."""

    pattern_id: str
    name: str
    category: str
    description: str
    applicable_when: list[str] = field(default_factory=list)
    anti_applicable_when: list[str] = field(default_factory=list)
    tradeoffs: dict[str, list[str]] = field(default_factory=dict)
    related_patterns: list[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_entity_dict(self) -> dict[str, Any]:
        """Convert to entity dict for world model."""
        return {
            "id": self.pattern_id,
            "type": "architectural_pattern",
            "attributes": {
                "name": self.name,
                "category": self.category,
                "description": self.description,
                "applicable_when": self.applicable_when,
                "anti_applicable_when": self.anti_applicable_when,
                "tradeoffs": self.tradeoffs,
                "related_patterns": self.related_patterns,
                "confidence": self.confidence,
            },
        }


@dataclass
class NormalizedHeuristic:
    """A normalized coding heuristic."""

    heuristic_id: str
    rule: str
    category: str
    severity: str = "medium"
    description: str = ""
    example_good: str = ""
    example_bad: str = ""
    auto_fix_strategy: list[str] = field(default_factory=list)
    related_patterns: list[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_entity_dict(self) -> dict[str, Any]:
        """Convert to entity dict for world model."""
        return {
            "id": self.heuristic_id,
            "type": "coding_heuristic",
            "attributes": {
                "rule": self.rule,
                "category": self.category,
                "severity": self.severity,
                "description": self.description,
                "example_good": self.example_good,
                "example_bad": self.example_bad,
                "auto_fix_strategy": self.auto_fix_strategy,
                "related_patterns": self.related_patterns,
                "confidence": self.confidence,
            },
        }


@dataclass
class IngestorConfig:
    """Configuration for knowledge ingestor."""

    min_confidence: float = 0.5
    deduplicate: bool = True
    validate_entities: bool = True
    extract_relations: bool = True
    max_batch_size: int = 1000
    normalize_patterns: bool = True
    normalize_heuristics: bool = True
    auto_create_relations: bool = True


class KnowledgeIngestor:
    """
    Ingests knowledge into the world model.

    Processes:
    - Memory packets (IR graphs, execution results)
    - Seed YAML files (patterns, heuristics)
    - Simulation results
    - Documents (structured data)
    - API responses
    - User inputs

    Extracts:
    - Entities with attributes
    - Relations between entities
    - Facts and assertions

    Normalizes:
    - Architectural patterns to standard format
    - Coding heuristics to standard format

    Usage:
        ingestor = KnowledgeIngestor(state)

        # Ingest from YAML
        result = ingestor.ingest_seed_yaml(
            path="/path/to/patterns.yaml",
            seed_type="architectural_pattern_library"
        )

        # Ingest from packet
        result = ingestor.ingest_packet(packet_envelope)

        # Ingest simulation result
        result = ingestor.ingest_simulation_result(simulation_run)
    """

    def __init__(
        self,
        state: WorldModelState | None = None,
        config: IngestorConfig | None = None,
    ):
        """
        Initialize the ingestor.

        Args:
            state: World model state to update
            config: Ingestor configuration
        """
        self._state = state or WorldModelState()
        self._config = config or IngestorConfig()
        self._ingest_history: list[IngestResult] = []
        self._seen_hashes: set[str] = set()  # For deduplication

        # Normalization caches
        self._pattern_cache: dict[str, NormalizedPattern] = {}
        self._heuristic_cache: dict[str, NormalizedHeuristic] = {}

        # DB persistence (wired via set_world_model_service)
        self._world_model_service: WorldModelService | None = None
        self._pending_entities: list[Entity] = []

        logger.info("KnowledgeIngestor initialized (v2.1.0 with DB sync)")

    def set_state(self, state: WorldModelState) -> None:
        """Set the world model state."""
        self._state = state

    def set_world_model_service(self, service: WorldModelService) -> None:
        """
        Set the WorldModelService for DB persistence.

        When set, entities added via ingest() are queued for DB sync.
        Call sync_to_db() after ingest() to persist to PostgreSQL.

        Args:
            service: WorldModelService instance (DB-backed)
        """
        self._world_model_service = service
        logger.info("WorldModelService attached to KnowledgeIngestor for DB sync")

    async def sync_to_db(
        self,
        tenant_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        role: str = "end_user",
    ) -> dict[str, Any]:
        """
        Sync pending entities to PostgreSQL via WorldModelService.

        Called after ingest() to persist in-memory entities to the DB.
        This bridges the in-memory KnowledgeIngestor to the DB-backed
        primary memory pipeline.

        Args:
            tenant_id: Tenant UUID for RLS isolation
            org_id: Organization UUID for RLS isolation
            user_id: User UUID for RLS isolation
            role: User role for RLS policy enforcement

        Returns:
            Dict with sync results: entities_synced, errors
        """
        if not self._world_model_service:
            logger.debug("sync_to_db: No WorldModelService attached, skipping")
            return {"entities_synced": 0, "skipped": True, "errors": []}

        if not self._pending_entities:
            return {"entities_synced": 0, "skipped": False, "errors": []}

        synced = 0
        errors: list[str] = []

        for entity in self._pending_entities:
            try:
                await self._world_model_service.upsert_entity(
                    entity_id=entity.entity_id,
                    attributes=entity.attributes,
                    entity_type=entity.entity_type,
                    confidence=entity.attributes.get("confidence", 1.0),
                    tenant_id=tenant_id,
                    org_id=org_id,
                    user_id=user_id,
                    role=role,
                )
                synced += 1
            except Exception as e:
                logger.warning(
                    f"sync_to_db: Failed to sync entity {entity.entity_id}: {e}"
                )
                errors.append(f"{entity.entity_id}: {e!s}")

        # Clear pending after sync
        self._pending_entities.clear()

        logger.info(f"sync_to_db: Synced {synced} entities to DB, {len(errors)} errors")
        return {"entities_synced": synced, "skipped": False, "errors": errors}

    def _track_entity_for_sync(self, entity: Entity) -> None:
        """Track entity for later DB sync."""
        if self._world_model_service is not None:
            self._pending_entities.append(entity)

    # ==========================================================================
    # Seed YAML Ingestion
    # ==========================================================================

    def ingest_seed_yaml(
        self,
        path: str | Path,
        seed_type: str | None = None,
    ) -> IngestResult:
        """
        Ingest knowledge from a seed YAML file.

        Supported seed types:
        - architectural_pattern_library: Design patterns
        - coding_heuristics_library: Code quality rules
        - reflection_memory: Prior lessons learned
        - cross_task_graph: Cross-task insights

        Args:
            path: Path to YAML file
            seed_type: Optional explicit seed type (auto-detected if not provided)

        Returns:
            IngestResult with ingestion statistics
        """
        import yaml

        result = IngestResult(source_type=SourceType.SEED_YAML)
        path = Path(path)

        if not path.exists():
            result.errors.append(f"Seed file not found: {path}")
            return result

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                result.errors.append(f"Empty YAML file: {path}")
                return result

            # Auto-detect seed type if not provided
            detected_type = seed_type or data.get("type", "unknown")

            if detected_type == "architectural_pattern_library":
                self._ingest_pattern_library(data, result)
            elif detected_type == "coding_heuristics_library":
                self._ingest_heuristics_library(data, result)
            elif detected_type == "reflection_memory":
                self._ingest_reflection_memory(data, result)
            elif detected_type == "cross_task_graph":
                self._ingest_cross_task_graph(data, result)
            else:
                # Generic YAML ingestion
                self._ingest_generic_yaml(data, result)

            result.success = len(result.errors) == 0

        except Exception as e:
            logger.error(f"YAML ingestion failed: {e}")
            result.errors.append(str(e))

        self._ingest_history.append(result)

        logger.info(
            f"Seed YAML ingested: {path.name}, "
            f"entities={result.entities_added}, patterns={result.patterns_normalized}"
        )

        return result

    def _ingest_pattern_library(
        self,
        data: dict[str, Any],
        result: IngestResult,
    ) -> None:
        """Ingest architectural pattern library."""
        patterns = data.get("patterns", [])

        for pattern_data in patterns:
            # Normalize the pattern
            normalized = self.normalize_architectural_pattern(pattern_data)

            # Add to world model
            entity_dict = normalized.to_entity_dict()
            self._add_entity(entity_dict, result)

            result.patterns_normalized += 1

            # Create relations to related patterns
            for related_id in normalized.related_patterns:
                if self._config.auto_create_relations:
                    self._add_relation(
                        {
                            "type": "relates_to",
                            "source": normalized.pattern_id,
                            "target": related_id,
                        },
                        result,
                    )

    def _ingest_heuristics_library(
        self,
        data: dict[str, Any],
        result: IngestResult,
    ) -> None:
        """Ingest coding heuristics library."""
        heuristics = data.get("heuristics", [])

        for heuristic_data in heuristics:
            # Normalize the heuristic
            normalized = self.normalize_coding_heuristic(heuristic_data)

            # Add to world model
            entity_dict = normalized.to_entity_dict()
            self._add_entity(entity_dict, result)

            result.heuristics_normalized += 1

            # Create relations to related patterns
            for related_id in normalized.related_patterns:
                if self._config.auto_create_relations:
                    self._add_relation(
                        {
                            "type": "applies_pattern",
                            "source": normalized.heuristic_id,
                            "target": related_id,
                        },
                        result,
                    )

    def _ingest_reflection_memory(
        self,
        data: dict[str, Any],
        result: IngestResult,
    ) -> None:
        """Ingest reflection memory seeds."""
        # Ingest reflections
        for reflection_data in data.get("reflections", []):
            entity = Entity(
                entity_id=reflection_data.get("id", str(uuid4())),
                entity_type="reflection",
                attributes={
                    "content": reflection_data.get("content", ""),
                    "context": reflection_data.get("context", ""),
                    "priority": reflection_data.get("priority", "medium"),
                    "confidence": reflection_data.get("confidence", 0.8),
                    "tags": reflection_data.get("tags", []),
                    "source": "seed_file",
                },
            )
            self._state.add_entity(entity)
            self._track_entity_for_sync(entity)
            result.entities_added += 1

        # Ingest patterns
        for pattern_data in data.get("patterns", []):
            entity = Entity(
                entity_id=pattern_data.get("id", str(uuid4())),
                entity_type="reflection_pattern",
                attributes={
                    "name": pattern_data.get("name", ""),
                    "description": pattern_data.get("description", ""),
                    "impact": pattern_data.get("impact", "neutral"),
                    "triggers": pattern_data.get("triggers", []),
                    "outcomes": pattern_data.get("outcomes", []),
                },
            )
            self._state.add_entity(entity)
            self._track_entity_for_sync(entity)
            result.entities_added += 1

    def _ingest_cross_task_graph(
        self,
        data: dict[str, Any],
        result: IngestResult,
    ) -> None:
        """Ingest cross-task graph seeds."""
        # Ingest nodes (tasks/insights)
        for node_data in data.get("nodes", []):
            entity = Entity(
                entity_id=node_data.get("id", str(uuid4())),
                entity_type=node_data.get("type", "task_insight"),
                attributes=node_data.get("attributes", {}),
            )
            self._state.add_entity(entity)
            self._track_entity_for_sync(entity)
            result.entities_added += 1

        # Ingest edges (relationships)
        for edge_data in data.get("edges", []):
            relation = Relation(
                relation_id=edge_data.get("id", str(uuid4())),
                relation_type=edge_data.get("type", "relates_to"),
                source_id=edge_data.get("source", ""),
                target_id=edge_data.get("target", ""),
                attributes=edge_data.get("attributes", {}),
            )
            self._state.add_relation(relation)
            result.relations_added += 1

    def _ingest_generic_yaml(
        self,
        data: dict[str, Any],
        result: IngestResult,
    ) -> None:
        """Generic YAML ingestion."""
        # Try to extract entities
        if "entities" in data:
            for entity_data in data["entities"]:
                self._add_entity(entity_data, result)

        # Try to extract relations
        if "relations" in data:
            for relation_data in data["relations"]:
                self._add_relation(relation_data, result)

    # ==========================================================================
    # Pattern and Heuristic Normalization
    # ==========================================================================

    def normalize_architectural_pattern(
        self,
        raw_pattern: dict[str, Any],
    ) -> NormalizedPattern:
        """
        Normalize an architectural pattern to standard format.

        Ensures consistent structure for:
        - Pattern identification
        - Applicability conditions
        - Tradeoffs
        - Related patterns

        Args:
            raw_pattern: Raw pattern data from YAML or other source

        Returns:
            NormalizedPattern instance
        """
        pattern_id = raw_pattern.get("id", str(uuid4()))

        # Check cache
        if pattern_id in self._pattern_cache:
            return self._pattern_cache[pattern_id]

        # Extract and normalize fields
        name = raw_pattern.get("name", "Unknown Pattern")
        category = raw_pattern.get("category", "unknown")
        description = raw_pattern.get("description", "")

        # Normalize applicability
        applicable_when = raw_pattern.get("applicable_when", [])
        if isinstance(applicable_when, str):
            applicable_when = [applicable_when]

        anti_applicable_when = raw_pattern.get("anti_applicable_when", [])
        if isinstance(anti_applicable_when, str):
            anti_applicable_when = [anti_applicable_when]

        # Normalize tradeoffs
        tradeoffs = raw_pattern.get("tradeoffs", {})
        if not isinstance(tradeoffs, dict):
            tradeoffs = {"pros": [], "cons": []}

        # Ensure pros and cons are lists
        if "pros" not in tradeoffs:
            tradeoffs["pros"] = []
        if "cons" not in tradeoffs:
            tradeoffs["cons"] = []

        # Related patterns
        related = raw_pattern.get("related_patterns", [])
        if isinstance(related, str):
            related = [related]

        normalized = NormalizedPattern(
            pattern_id=pattern_id,
            name=name,
            category=self._normalize_category(category),
            description=description,
            applicable_when=applicable_when,
            anti_applicable_when=anti_applicable_when,
            tradeoffs=tradeoffs,
            related_patterns=related,
            confidence=raw_pattern.get("confidence", 1.0),
        )

        # Cache
        self._pattern_cache[pattern_id] = normalized

        return normalized

    def normalize_coding_heuristic(
        self,
        raw_heuristic: dict[str, Any],
    ) -> NormalizedHeuristic:
        """
        Normalize a coding heuristic to standard format.

        Ensures consistent structure for:
        - Rule definition
        - Severity classification
        - Examples
        - Auto-fix strategies

        Args:
            raw_heuristic: Raw heuristic data from YAML or other source

        Returns:
            NormalizedHeuristic instance
        """
        heuristic_id = raw_heuristic.get("id", str(uuid4()))

        # Check cache
        if heuristic_id in self._heuristic_cache:
            return self._heuristic_cache[heuristic_id]

        # Extract and normalize fields
        rule = raw_heuristic.get("rule", "")
        category = raw_heuristic.get("category", "unknown")

        # Normalize severity
        severity = raw_heuristic.get("severity", "medium")
        valid_severities = {"critical", "high", "medium", "low", "info"}
        if severity.lower() not in valid_severities:
            severity = "medium"

        # Auto-fix strategies
        auto_fix = raw_heuristic.get("auto_fix_strategy", [])
        if isinstance(auto_fix, str):
            auto_fix = [auto_fix]

        # Related patterns
        related = raw_heuristic.get("related_patterns", [])
        if isinstance(related, str):
            related = [related]

        normalized = NormalizedHeuristic(
            heuristic_id=heuristic_id,
            rule=rule,
            category=self._normalize_category(category),
            severity=severity.lower(),
            description=raw_heuristic.get("description", ""),
            example_good=raw_heuristic.get("example_good", ""),
            example_bad=raw_heuristic.get("example_bad", ""),
            auto_fix_strategy=auto_fix,
            related_patterns=related,
            confidence=raw_heuristic.get("confidence", 1.0),
        )

        # Cache
        self._heuristic_cache[heuristic_id] = normalized

        return normalized

    def _normalize_category(self, category: str) -> str:
        """Normalize category string."""
        # Standardize category names
        category_map = {
            "struct": "structural",
            "structure": "structural",
            "behavior": "behavioral",
            "behav": "behavioral",
            "create": "creational",
            "creation": "creational",
            "l9": "l9_native",
            "native": "l9_native",
            "code": "code_quality",
            "quality": "code_quality",
            "perf": "performance",
            "performance": "performance",
            "sec": "security",
            "security": "security",
            "doc": "documentation",
            "documentation": "documentation",
        }

        normalized = category.lower().strip()
        return category_map.get(normalized, normalized)

    # ==========================================================================
    # Packet Ingestion
    # ==========================================================================

    def ingest_packet(
        self,
        packet: dict[str, Any],
    ) -> IngestResult:
        """
        Ingest knowledge from a PacketEnvelope.

        Alias for ingest() with MEMORY_PACKET source type.

        Args:
            packet: PacketEnvelope dict with packet_type and payload

        Returns:
            IngestResult
        """
        return self.ingest(packet, SourceType.MEMORY_PACKET)

    def ingest(
        self,
        data: dict[str, Any],
        source_type: SourceType,
        source_id: str = "",
    ) -> IngestResult:
        """
        Ingest knowledge from data.

        Args:
            data: Data to ingest
            source_type: Type of source
            source_id: Source identifier

        Returns:
            IngestResult
        """
        result = IngestResult(source_type=source_type)

        try:
            # Deduplication check
            if self._config.deduplicate:
                data_hash = self._compute_hash(data)
                if data_hash in self._seen_hashes:
                    result.success = True
                    return result
                self._seen_hashes.add(data_hash)

            # Route to specific handler
            if source_type == SourceType.MEMORY_PACKET:
                self._ingest_memory_packet(data, result)
            elif source_type == SourceType.IR_GRAPH:
                self._ingest_ir_graph(data, result)
            elif source_type == SourceType.DOCUMENT:
                self._ingest_document(data, result)
            elif source_type == SourceType.REFLECTION:
                self._ingest_reflection(data, result)
            elif source_type == SourceType.SIMULATION_RESULT:
                self._ingest_simulation_result_data(data, result)
            else:
                self._ingest_generic(data, result)

            result.success = len(result.errors) == 0

        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            result.errors.append(str(e))

        self._ingest_history.append(result)

        return result

    # ==========================================================================
    # Simulation Result Ingestion
    # ==========================================================================

    def ingest_simulation_result(
        self,
        simulation_run: Any,  # SimulationRun type
    ) -> IngestResult:
        """
        Ingest a simulation result.

        Extracts from SimulationRun:
        - Run metadata as entity
        - Step outcomes as entities
        - Failure modes as entities
        - Metrics as attributes
        - Causal links between steps

        Args:
            simulation_run: SimulationRun instance

        Returns:
            IngestResult
        """
        result = IngestResult(source_type=SourceType.SIMULATION_RESULT)

        try:
            # Convert to dict if not already
            if hasattr(simulation_run, "to_dict"):
                run_data = simulation_run.to_dict()
            else:
                run_data = dict(simulation_run)

            self._ingest_simulation_result_data(run_data, result)
            result.success = len(result.errors) == 0

        except Exception as e:
            logger.error(f"Simulation result ingestion failed: {e}")
            result.errors.append(str(e))

        self._ingest_history.append(result)

        return result

    def _ingest_simulation_result_data(
        self,
        run_data: dict[str, Any],
        result: IngestResult,
    ) -> None:
        """Ingest simulation result data."""
        run_id = run_data.get("run_id", str(uuid4()))
        graph_id = run_data.get("graph_id", "")

        # Create simulation run entity
        run_entity = Entity(
            entity_id=f"sim_run:{run_id}",
            entity_type="simulation_run",
            attributes={
                "status": run_data.get("status", "unknown"),
                "score": run_data.get("score", 0.0),
                "total_steps": run_data.get("total_steps", 0),
                "successful_steps": run_data.get("successful_steps", 0),
                "failed_steps": run_data.get("failed_steps", 0),
                "failure_modes": run_data.get("failure_modes", []),
                "duration_ms": run_data.get("duration_ms", 0),
                "graph_id": graph_id,
            },
        )
        self._state.add_entity(run_entity)
        self._track_entity_for_sync(run_entity)
        result.entities_added += 1

        # Link to graph if exists
        if graph_id:
            relation = Relation(
                relation_id=str(uuid4()),
                relation_type="simulates",
                source_id=f"sim_run:{run_id}",
                target_id=graph_id,
            )
            self._state.add_relation(relation)
            result.relations_added += 1

        # Create entities for failure modes
        for idx, failure_mode in enumerate(run_data.get("failure_modes", [])):
            failure_entity = Entity(
                entity_id=f"failure:{run_id}:{idx}",
                entity_type="simulation_failure",
                attributes={
                    "description": failure_mode,
                    "run_id": run_id,
                    "index": idx,
                },
            )
            self._state.add_entity(failure_entity)
            self._track_entity_for_sync(failure_entity)
            result.entities_added += 1

            # Link to run
            relation = Relation(
                relation_id=str(uuid4()),
                relation_type="failed_with",
                source_id=f"sim_run:{run_id}",
                target_id=f"failure:{run_id}:{idx}",
            )
            self._state.add_relation(relation)
            result.relations_added += 1

        # Extract metrics as facts
        metrics = run_data.get("metrics", {})
        for _metric_name, _metric_value in metrics.items():
            result.facts_extracted += 1

    # ==========================================================================
    # Memory Packet Processing
    # ==========================================================================

    def _ingest_memory_packet(
        self,
        data: dict[str, Any],
        result: IngestResult,
    ) -> None:
        """Ingest from memory packet."""
        packet_type = data.get("packet_type", data.get("kind", ""))
        payload = data.get("payload", data)

        # Extract entities from packet
        if "entities" in payload:
            for entity_data in payload["entities"]:
                self._add_entity(entity_data, result)

        # Extract from common packet types
        if packet_type == "ir_graph":
            self._ingest_ir_graph(payload, result)

        elif packet_type == "execution_result":
            self._ingest_execution_result(payload, result)

        elif packet_type == "insight":
            self._ingest_insight(payload, result)

        elif packet_type == "simulation_result":
            self._ingest_simulation_result_data(payload, result)

        elif packet_type.startswith("seed."):
            # Seed packet - route to appropriate handler
            seed_type = packet_type.replace("seed.", "")
            if seed_type == "architectural_pattern":
                content = payload.get("content", payload)
                if "patterns" in content:
                    self._ingest_pattern_library(content, result)
            elif seed_type == "coding_heuristic":
                content = payload.get("content", payload)
                if "heuristics" in content:
                    self._ingest_heuristics_library(content, result)

        # Extract metadata as attributes
        if "metadata" in data:
            self._extract_metadata_facts(data["metadata"], result)

    def _ingest_ir_graph(
        self,
        data: dict[str, Any],
        result: IngestResult,
    ) -> None:
        """Ingest from IR graph."""
        graph_id = data.get("graph_id", str(uuid4()))

        # Create graph entity
        graph_entity = Entity(
            entity_id=graph_id,
            entity_type="ir_graph",
            attributes={
                "status": data.get("status", "unknown"),
                "intent_count": len(data.get("intents", [])),
                "action_count": len(data.get("actions", [])),
                "constraint_count": len(
                    data.get("constraints", data.get("active_constraints", []))
                ),
                "summary": data.get("summary", ""),
            },
        )
        self._state.add_entity(graph_entity)
        self._track_entity_for_sync(graph_entity)
        result.entities_added += 1

        # Extract intents as entities
        for intent in data.get("intents", []):
            intent_entity = Entity(
                entity_id=intent.get("id", str(uuid4())),
                entity_type="intent",
                attributes={
                    "intent_type": intent.get("type", intent.get("intent_type", "")),
                    "description": intent.get("description", ""),
                    "target": intent.get("target", ""),
                    "confidence": intent.get("confidence", 1.0),
                },
            )
            self._state.add_entity(intent_entity)
            self._track_entity_for_sync(intent_entity)
            result.entities_added += 1

            # Relation to graph
            relation = Relation(
                relation_id=str(uuid4()),
                relation_type="belongs_to",
                source_id=intent_entity.entity_id,
                target_id=graph_id,
            )
            self._state.add_relation(relation)
            result.relations_added += 1

        # Extract constraints as entities
        for constraint in data.get("constraints", data.get("active_constraints", [])):
            constraint_entity = Entity(
                entity_id=constraint.get("id", str(uuid4())),
                entity_type="constraint",
                attributes={
                    "constraint_type": constraint.get(
                        "type", constraint.get("constraint_type", "")
                    ),
                    "description": constraint.get("description", ""),
                    "status": constraint.get("status", "active"),
                },
            )
            self._state.add_entity(constraint_entity)
            self._track_entity_for_sync(constraint_entity)
            result.entities_added += 1

            # Relation to graph
            relation = Relation(
                relation_id=str(uuid4()),
                relation_type="constrains",
                source_id=constraint_entity.entity_id,
                target_id=graph_id,
            )
            self._state.add_relation(relation)
            result.relations_added += 1

        # Extract actions as entities
        for action in data.get("actions", []):
            action_entity = Entity(
                entity_id=action.get("id", action.get("node_id", str(uuid4()))),
                entity_type="action",
                attributes={
                    "action_type": action.get("type", action.get("action_type", "")),
                    "description": action.get("description", ""),
                    "target": action.get("target", ""),
                    "depends_on": action.get("depends_on", []),
                    "risk_level": action.get("risk_level", "low"),
                },
            )
            self._state.add_entity(action_entity)
            self._track_entity_for_sync(action_entity)
            result.entities_added += 1

    def _ingest_execution_result(
        self,
        data: dict[str, Any],
        result: IngestResult,
    ) -> None:
        """Ingest from execution result."""
        execution_id = data.get("execution_id", str(uuid4()))

        entity = Entity(
            entity_id=execution_id,
            entity_type="execution_result",
            attributes={
                "status": data.get("status", ""),
                "success": data.get("success", False),
                "duration_ms": data.get("duration_ms", 0),
                "steps_completed": data.get("completed_steps", 0),
                "errors": data.get("errors", []),
            },
        )
        self._state.add_entity(entity)
        self._track_entity_for_sync(entity)
        result.entities_added += 1

    def _ingest_insight(
        self,
        data: dict[str, Any],
        result: IngestResult,
    ) -> None:
        """Ingest from insight."""
        insight_id = data.get("insight_id", str(uuid4()))

        entity = Entity(
            entity_id=insight_id,
            entity_type="insight",
            attributes={
                "insight_type": data.get("type", data.get("insight_type", "")),
                "content": data.get("content", ""),
                "confidence": data.get("confidence", 1.0),
                "source": data.get("source", ""),
                "entities": data.get("entities", []),
            },
        )
        self._state.add_entity(entity)
        self._track_entity_for_sync(entity)
        result.entities_added += 1
        result.facts_extracted += 1

    def _ingest_document(
        self,
        data: dict[str, Any],
        result: IngestResult,
    ) -> None:
        """Ingest from document."""
        doc_id = data.get("document_id", str(uuid4()))

        # Create document entity
        doc_entity = Entity(
            entity_id=doc_id,
            entity_type="document",
            attributes={
                "title": data.get("title", ""),
                "content_type": data.get("content_type", ""),
                "source": data.get("source", ""),
            },
        )
        self._state.add_entity(doc_entity)
        self._track_entity_for_sync(doc_entity)
        result.entities_added += 1

        # Extract sections
        for section in data.get("sections", []):
            section_entity = Entity(
                entity_id=section.get("id", str(uuid4())),
                entity_type="document_section",
                attributes={
                    "title": section.get("title", ""),
                    "content": section.get("content", "")[:500],  # Truncate
                },
            )
            self._state.add_entity(section_entity)
            self._track_entity_for_sync(section_entity)
            result.entities_added += 1

            # Relation to document
            relation = Relation(
                relation_id=str(uuid4()),
                relation_type="part_of",
                source_id=section_entity.entity_id,
                target_id=doc_id,
            )
            self._state.add_relation(relation)
            result.relations_added += 1

    def _ingest_reflection(
        self,
        data: dict[str, Any],
        result: IngestResult,
    ) -> None:
        """Ingest from reflection."""
        # Extract lessons
        for lesson in data.get("lessons", []):
            lesson_entity = Entity(
                entity_id=str(uuid4()),
                entity_type="lesson_learned",
                attributes={
                    "lesson": lesson.get("lesson", ""),
                    "context": lesson.get("context", ""),
                    "confidence": lesson.get("confidence", 0.5),
                },
            )
            self._state.add_entity(lesson_entity)
            self._track_entity_for_sync(lesson_entity)
            result.entities_added += 1
            result.facts_extracted += 1

        # Extract improvements
        for improvement in data.get("improvements", []):
            imp_entity = Entity(
                entity_id=str(uuid4()),
                entity_type="improvement",
                attributes={
                    "area": improvement.get("area", ""),
                    "action": improvement.get("action_required", ""),
                    "priority": improvement.get("priority", "medium"),
                },
            )
            self._state.add_entity(imp_entity)
            self._track_entity_for_sync(imp_entity)
            result.entities_added += 1

    def _ingest_generic(
        self,
        data: dict[str, Any],
        result: IngestResult,
    ) -> None:
        """Generic ingestion for unstructured data."""
        # Try to extract any entities
        if "entities" in data:
            for entity_data in data["entities"]:
                self._add_entity(entity_data, result)

        # Try to extract any relations
        if "relations" in data:
            for relation_data in data["relations"]:
                self._add_relation(relation_data, result)

    # ==========================================================================
    # Helper Methods
    # ==========================================================================

    def _add_entity(
        self,
        data: dict[str, Any],
        result: IngestResult,
    ) -> Entity | None:
        """Add entity from data."""
        entity = Entity(
            entity_id=data.get("id", str(uuid4())),
            entity_type=data.get("type", "unknown"),
            attributes=data.get("attributes", {}),
        )

        existing = self._state.get_entity(entity.entity_id)
        if existing:
            # Update existing
            existing.attributes.update(entity.attributes)
            result.entities_updated += 1
            self._track_entity_for_sync(existing)  # Track for DB sync
            return existing
        self._state.add_entity(entity)
        self._track_entity_for_sync(entity)  # Track for DB sync
        result.entities_added += 1
        return entity

    def _add_relation(
        self,
        data: dict[str, Any],
        result: IngestResult,
    ) -> Relation | None:
        """Add relation from data."""
        relation = Relation(
            relation_id=data.get("id", str(uuid4())),
            relation_type=data.get("type", "related_to"),
            source_id=data.get("source", ""),
            target_id=data.get("target", ""),
            attributes=data.get("attributes", {}),
        )

        if not relation.source_id or not relation.target_id:
            return None

        self._state.add_relation(relation)
        result.relations_added += 1
        return relation

    def _extract_metadata_facts(
        self,
        metadata: dict[str, Any],
        result: IngestResult,
    ) -> None:
        """Extract facts from metadata."""
        for _key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                result.facts_extracted += 1

    def _compute_hash(self, data: dict[str, Any]) -> str:
        """Compute hash for deduplication."""
        json_str = json.dumps(data, sort_keys=True, default=str)
        # Use SHA256 instead of MD5 for better security
        return hashlib.sha256(json_str.encode()).hexdigest()

    # ==========================================================================
    # Batch Operations
    # ==========================================================================

    def ingest_batch(
        self,
        items: list[dict[str, Any]],
        source_type: SourceType,
    ) -> list[IngestResult]:
        """
        Ingest a batch of items.

        Args:
            items: List of items to ingest
            source_type: Source type for all items

        Returns:
            List of IngestResults
        """
        results = []

        for i, item in enumerate(items):
            if i >= self._config.max_batch_size:
                logger.warning(
                    f"Batch size limit reached ({self._config.max_batch_size})"
                )
                break

            result = self.ingest(item, source_type)
            results.append(result)

        return results

    # ==========================================================================
    # Status
    # ==========================================================================

    def get_history(self, limit: int = 100) -> list[IngestResult]:
        """Get ingestion history."""
        return self._ingest_history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get ingestion statistics."""
        total_entities = sum(r.entities_added for r in self._ingest_history)
        total_relations = sum(r.relations_added for r in self._ingest_history)
        total_facts = sum(r.facts_extracted for r in self._ingest_history)
        total_patterns = sum(r.patterns_normalized for r in self._ingest_history)
        total_heuristics = sum(r.heuristics_normalized for r in self._ingest_history)

        return {
            "total_ingestions": len(self._ingest_history),
            "total_entities_added": total_entities,
            "total_relations_added": total_relations,
            "total_facts_extracted": total_facts,
            "total_patterns_normalized": total_patterns,
            "total_heuristics_normalized": total_heuristics,
            "seen_hashes": len(self._seen_hashes),
            "cached_patterns": len(self._pattern_cache),
            "cached_heuristics": len(self._heuristic_cache),
        }

    def clear_cache(self) -> None:
        """Clear normalization caches."""
        self._pattern_cache.clear()
        self._heuristic_cache.clear()
        logger.info("Normalization caches cleared")

    # ==========================================================================
    # Helper Methods for Packet/IR Conversion
    # ==========================================================================

    @staticmethod
    def build_update_from_packet(packet: dict[str, Any]) -> dict[str, Any]:
        """
        Build a structured world model update from a PacketEnvelope.

        Transforms raw packet data into normalized update format
        suitable for WorldModelEngine.update_from_packet().

        Args:
            packet: PacketEnvelope dict or raw packet payload with:
                - packet_type: str (ir_graph, execution_plan, reflection, etc.)
                - payload: dict
                - metadata: dict (optional)
                - provenance: dict (optional)

        Returns:
            Normalized update dict with:
                - update_type: str (entity_add, relation_add, attribute_update)
                - entities: list[dict] - entities to add/update
                - relations: list[dict] - relations to add
                - facts: list[dict] - extracted facts
                - source: str - packet source identifier
        """
        packet_type = packet.get("packet_type", packet.get("kind", "unknown"))
        payload = packet.get("payload", packet)
        packet.get("metadata", {})
        provenance = packet.get("provenance", {})

        update: dict[str, Any] = {
            "update_type": f"packet_{packet_type}",
            "entities": [],
            "relations": [],
            "facts": [],
            "source": provenance.get("source", "packet_ingest"),
            "packet_type": packet_type,
            "timestamp": packet.get("timestamp"),
        }

        # Route by packet type
        if packet_type == "ir_graph":
            update["entities"], update["relations"] = (
                KnowledgeIngestor._extract_from_ir_graph(payload)
            )
        elif packet_type == "execution_plan":
            update["entities"] = KnowledgeIngestor._extract_from_execution_plan(payload)
        elif packet_type == "reflection":
            update["entities"] = KnowledgeIngestor._extract_from_reflection(payload)
        elif packet_type == "insight":
            update["entities"], update["facts"] = (
                KnowledgeIngestor._extract_from_insight(payload)
            )
        elif packet_type == "simulation_result":
            update["entities"], update["relations"] = (
                KnowledgeIngestor._extract_from_simulation_result(payload)
            )
        else:
            # Generic extraction
            update["entities"] = KnowledgeIngestor._extract_generic_entities(payload)

        return update

    @staticmethod
    def _extract_from_ir_graph(
        payload: dict[str, Any],
    ) -> tuple[list[dict], list[dict]]:
        """Extract entities and relations from IR graph payload."""
        entities: list[dict] = []
        relations: list[dict] = []

        graph_id = payload.get("graph_id", str(uuid4()))

        # Graph entity
        entities.append(
            {
                "id": graph_id,
                "type": "ir_graph",
                "attributes": {
                    "status": payload.get("status", "unknown"),
                    "intent_count": len(payload.get("intents", [])),
                    "constraint_count": len(
                        payload.get(
                            "constraints", payload.get("active_constraints", [])
                        )
                    ),
                    "action_count": len(payload.get("actions", [])),
                    "summary": payload.get("summary", ""),
                },
            }
        )

        # Intent entities
        for intent in payload.get("intents", []):
            intent_id = intent.get("id", str(uuid4()))
            entities.append(
                {
                    "id": intent_id,
                    "type": "intent",
                    "attributes": {
                        "intent_type": intent.get("type", ""),
                        "description": intent.get("description", ""),
                        "target": intent.get("target", ""),
                    },
                }
            )
            relations.append(
                {
                    "id": str(uuid4()),
                    "type": "belongs_to",
                    "source": intent_id,
                    "target": graph_id,
                }
            )

        # Constraint entities (from active_constraints)
        for constraint in payload.get(
            "active_constraints", payload.get("constraints", [])
        ):
            constraint_id = constraint.get("id", str(uuid4()))
            entities.append(
                {
                    "id": constraint_id,
                    "type": "constraint",
                    "attributes": {
                        "constraint_type": constraint.get("type", ""),
                        "description": constraint.get("description", ""),
                    },
                }
            )
            relations.append(
                {
                    "id": str(uuid4()),
                    "type": "constrains",
                    "source": constraint_id,
                    "target": graph_id,
                }
            )

        return entities, relations

    @staticmethod
    def _extract_from_execution_plan(payload: dict[str, Any]) -> list[dict]:
        """Extract entities from execution plan payload."""
        entities: list[dict] = []

        plan_id = payload.get("plan_id", str(uuid4()))

        # Plan entity
        entities.append(
            {
                "id": plan_id,
                "type": "execution_plan",
                "attributes": {
                    "total_steps": payload.get("total_steps", 0),
                    "estimated_duration_ms": payload.get("estimated_duration_ms", 0),
                    "created_at": payload.get("created_at", ""),
                },
            }
        )

        # Step entities
        for step in payload.get("steps", []):
            step_id = step.get("action_id", str(uuid4()))
            entities.append(
                {
                    "id": step_id,
                    "type": "plan_step",
                    "attributes": {
                        "step_number": step.get("step_number", 0),
                        "action_type": step.get("action_type", ""),
                        "description": step.get("description", ""),
                        "target": step.get("target", ""),
                        "risk_level": step.get("risk_level", "low"),
                    },
                }
            )

        return entities

    @staticmethod
    def _extract_from_reflection(payload: dict[str, Any]) -> list[dict]:
        """Extract entities from reflection payload."""
        entities: list[dict] = []

        # Lessons
        for lesson in payload.get("lessons", []):
            entities.append(
                {
                    "id": str(uuid4()),
                    "type": "lesson_learned",
                    "attributes": {
                        "lesson": lesson.get("lesson", ""),
                        "context": lesson.get("context", ""),
                        "confidence": lesson.get("confidence", 0.5),
                    },
                }
            )

        # Improvements
        for improvement in payload.get("improvements", []):
            entities.append(
                {
                    "id": str(uuid4()),
                    "type": "improvement",
                    "attributes": {
                        "area": improvement.get("area", ""),
                        "action": improvement.get("action_required", ""),
                        "priority": improvement.get("priority", "medium"),
                    },
                }
            )

        return entities

    @staticmethod
    def _extract_from_insight(payload: dict[str, Any]) -> tuple[list[dict], list[dict]]:
        """Extract entities and facts from insight payload."""
        entities: list[dict] = []
        facts: list[dict] = []

        insight_id = payload.get("insight_id", str(uuid4()))

        entities.append(
            {
                "id": insight_id,
                "type": "insight",
                "attributes": {
                    "insight_type": payload.get(
                        "type", payload.get("insight_type", "")
                    ),
                    "content": payload.get("content", ""),
                    "confidence": payload.get("confidence", 0.7),
                    "entities": payload.get("entities", []),
                },
            }
        )

        # Extract facts if present
        for fact_data in payload.get("facts", []):
            facts.append(
                {
                    "subject": fact_data.get("subject", ""),
                    "predicate": fact_data.get("predicate", ""),
                    "object": fact_data.get("object", ""),
                    "confidence": fact_data.get("confidence", 0.8),
                }
            )

        return entities, facts

    @staticmethod
    def _extract_from_simulation_result(
        payload: dict[str, Any],
    ) -> tuple[list[dict], list[dict]]:
        """Extract entities and relations from simulation result payload."""
        entities: list[dict] = []
        relations: list[dict] = []

        run_id = payload.get("run_id", str(uuid4()))
        graph_id = payload.get("graph_id", "")

        # Simulation run entity
        entities.append(
            {
                "id": f"sim_run:{run_id}",
                "type": "simulation_run",
                "attributes": {
                    "status": payload.get("status", "unknown"),
                    "score": payload.get("score", 0.0),
                    "total_steps": payload.get("total_steps", 0),
                    "successful_steps": payload.get("successful_steps", 0),
                    "failed_steps": payload.get("failed_steps", 0),
                    "duration_ms": payload.get("duration_ms", 0),
                },
            }
        )

        # Link to graph
        if graph_id:
            relations.append(
                {
                    "id": str(uuid4()),
                    "type": "simulates",
                    "source": f"sim_run:{run_id}",
                    "target": graph_id,
                }
            )

        # Failure mode entities
        for idx, failure in enumerate(payload.get("failure_modes", [])):
            failure_id = f"failure:{run_id}:{idx}"
            entities.append(
                {
                    "id": failure_id,
                    "type": "simulation_failure",
                    "attributes": {
                        "description": failure,
                        "run_id": run_id,
                    },
                }
            )
            relations.append(
                {
                    "id": str(uuid4()),
                    "type": "failed_with",
                    "source": f"sim_run:{run_id}",
                    "target": failure_id,
                }
            )

        return entities, relations

    @staticmethod
    def _extract_generic_entities(payload: dict[str, Any]) -> list[dict]:
        """Extract entities from generic payload."""
        entities: list[dict] = []

        # If payload has explicit entities
        if "entities" in payload:
            for entity in payload["entities"]:
                entities.append(
                    {
                        "id": entity.get("id", str(uuid4())),
                        "type": entity.get("type", "unknown"),
                        "attributes": entity.get("attributes", {}),
                    }
                )

        return entities

    @staticmethod
    def extract_entities_from_ir(ir_payload: dict[str, Any]) -> dict[str, Any]:
        """
        Extract structured entities from IR graph/plan payload.

        Designed for integration with IR Engine outputs:
        - ir_generator.to_packet_payload()
        - ir_generator.to_execution_plan()

        Args:
            ir_payload: IR graph or execution plan dict with:
                - graph_id or plan_id
                - intents, constraints, actions (for graphs)
                - steps, active_constraints (for plans)

        Returns:
            Extracted data dict with:
                - graph_id: str (if IR graph)
                - plan_id: str (if execution plan)
                - intents: list[dict] - intent entities
                - constraints: list[dict] - constraint entities
                - actions: list[dict] - action entities
                - steps: list[dict] - plan step entities
                - relations: list[dict] - relationships between entities
        """
        result: dict[str, Any] = {
            "graph_id": ir_payload.get("graph_id"),
            "plan_id": ir_payload.get("plan_id"),
            "intents": [],
            "constraints": [],
            "actions": [],
            "steps": [],
            "relations": [],
        }

        # Detect type by fields present
        is_graph = "intents" in ir_payload or "graph_id" in ir_payload
        is_plan = "steps" in ir_payload or "plan_id" in ir_payload

        if is_graph:
            # Extract intents
            for intent in ir_payload.get("intents", []):
                result["intents"].append(
                    {
                        "id": intent.get("id", intent.get("node_id")),
                        "type": intent.get("type", intent.get("intent_type")),
                        "description": intent.get("description", ""),
                        "target": intent.get("target", ""),
                        "confidence": intent.get("confidence", 1.0),
                    }
                )

            # Extract constraints
            for constraint in ir_payload.get(
                "constraints", ir_payload.get("active_constraints", [])
            ):
                result["constraints"].append(
                    {
                        "id": constraint.get("id", constraint.get("node_id")),
                        "type": constraint.get(
                            "type", constraint.get("constraint_type")
                        ),
                        "description": constraint.get("description", ""),
                        "status": constraint.get("status", "active"),
                    }
                )

            # Extract actions
            for action in ir_payload.get("actions", []):
                result["actions"].append(
                    {
                        "id": action.get("id", action.get("node_id")),
                        "type": action.get("type", action.get("action_type")),
                        "description": action.get("description", ""),
                        "target": action.get("target", ""),
                        "depends_on": action.get("depends_on", []),
                    }
                )

        if is_plan:
            # Extract steps
            for step in ir_payload.get("steps", []):
                result["steps"].append(
                    {
                        "step_number": step.get("step_number", 0),
                        "action_id": step.get("action_id"),
                        "action_type": step.get("action_type", ""),
                        "description": step.get("description", ""),
                        "target": step.get("target", ""),
                        "dependencies": step.get("dependencies", []),
                        "risk_level": step.get("risk_level", "low"),
                    }
                )

        # Build relations
        graph_id = result["graph_id"]
        if graph_id:
            for intent in result["intents"]:
                result["relations"].append(
                    {
                        "type": "intent_of",
                        "source": intent["id"],
                        "target": graph_id,
                    }
                )

            for constraint in result["constraints"]:
                result["relations"].append(
                    {
                        "type": "constrains",
                        "source": constraint["id"],
                        "target": graph_id,
                    }
                )

        return result


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-004",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "batch-processing",
        "caching",
        "code-quality",
        "config",
        "data-models",
        "dataclass",
        "filesystem",
        "learning",
        "logging",
    ],
    "keywords": [
        "architectural",
        "batch",
        "build",
        "cache",
        "clear",
        "coding",
        "engine",
        "entities",
    ],
    "business_value": "Provides knowledge ingestor components including SourceType, IngestResult, ExtractedFact",
    "last_modified": "2026-01-07T13:35:58Z",
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
