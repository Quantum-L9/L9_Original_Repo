"""
L9 World Model - Seed Loader
============================

Loads seed YAML files into the memory substrate and world model.

Responsibilities:
- Load YAML seed files
- Create PacketEnvelopes
- Write to memory substrate
- Ingest into world model via KnowledgeIngestor
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Seed Loader",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-14T15:02:46Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "seed_loader",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["world_model.runtime"],
    },
}
# ============================================================================

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog
import yaml

from core.schemas import (
    PacketEnvelope,
    PacketEnvelopeIn,
    PacketMetadata,
    PacketProvenance,
)
from memory.substrate_service import MemorySubstrateService
from world_model.knowledge_ingestor import IngestResult, KnowledgeIngestor, SourceType
from world_model.state import WorldModelState

logger = structlog.get_logger(__name__)


# =============================================================================
# Seed Data Types
# =============================================================================

SEED_TYPE_MAPPING = {
    "architectural_pattern_library": "architectural_pattern",
    "coding_heuristics_library": "coding_heuristic",
    "reflection_memory": "reflection_memory",
    "cross_task_graph": "cross_task_graph",
}


# =============================================================================
# Seed Loader
# =============================================================================


class SeedLoader:
    """
    Loads seed YAML files into the L9 memory substrate and world model.

    Workflow:
    1. Load YAML file
    2. Create PacketEnvelope for the seed data
    3. Write to memory substrate
    4. Ingest into world model via KnowledgeIngestor

    Usage:
        substrate = MemorySubstrateService(repository)
        ingestor = KnowledgeIngestor(state)
        loader = SeedLoader(substrate, ingestor)
        await loader.run()
    """

    def __init__(
        self,
        substrate: MemorySubstrateService,
        ingestor: KnowledgeIngestor,
        seed_dir: str | None = None,
    ):
        """
        Initialize the seed loader.

        Args:
            substrate: Memory substrate service instance
            ingestor: Knowledge ingestor instance
            seed_dir: Directory containing seed YAML files
        """
        self.substrate = substrate
        self.ingestor = ingestor

        # Default seed directory
        if seed_dir is None:
            # Relative to L9 root
            self.seed_dir = Path(__file__).parent.parent / "seed"
        else:
            self.seed_dir = Path(seed_dir)

        self._loaded_packets: list[PacketEnvelope] = []
        self._ingest_results: list[IngestResult] = []
        self._thread_id = str(uuid4())

        logger.info(f"SeedLoader initialized, seed_dir={self.seed_dir}")

    # =========================================================================
    # YAML Loading
    # =========================================================================

    def load_yaml(self, path: str | Path) -> dict[str, Any]:
        """
        Load and parse a YAML file.

        Args:
            path: Path to YAML file

        Returns:
            Parsed YAML data
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Seed file not found: {path}")

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        logger.info(f"Loaded YAML: {path.name}, type={data.get('type', 'unknown')}")

        return data

    def load_yaml_as_packet(
        self,
        path: str | Path,
        packet_type: str = "world_model_seed",
    ) -> PacketEnvelope:
        """
        Load a YAML file and wrap it in a PacketEnvelope.

        Args:
            path: Path to YAML file
            packet_type: Type for the packet

        Returns:
            PacketEnvelope containing the seed data
        """
        data = self.load_yaml(path)
        path = Path(path)

        # Determine specific packet type from data
        data_type = data.get("type", "unknown")
        specific_type = SEED_TYPE_MAPPING.get(data_type, packet_type)

        packet = PacketEnvelope(
            packet_id=uuid4(),
            packet_type=f"seed.{specific_type}",
            payload={
                "source_file": str(path.name),
                "version": data.get("version", "1.0"),
                "data_type": data_type,
                "content": data,
            },
            timestamp=datetime.now(timezone.utc),
            metadata=PacketMetadata(
                schema_version="1.0.1",
                agent="seed_loader",
                domain="world_model",
            ),
            provenance=PacketProvenance(
                source_agent="seed_loader",
            ),
        )

        self._loaded_packets.append(packet)

        logger.debug(f"Created packet {packet.packet_id} for {path.name}")

        return packet

    # =========================================================================
    # Memory Substrate Integration
    # =========================================================================

    async def write_packet_to_substrate(
        self,
        packet: PacketEnvelope,
    ) -> bool:
        """
        Write a packet to the memory substrate.

        Args:
            packet: PacketEnvelope to write

        Returns:
            True if successful
        """
        try:
            packet_in = PacketEnvelopeIn(
                packet_type=packet.packet_type,
                payload=packet.payload,
                metadata=packet.metadata.model_dump() if packet.metadata else None,
                provenance=(
                    packet.provenance.model_dump() if packet.provenance else None
                ),
            )

            result = await self.substrate.write_packet(packet_in)

            if result.status == "ok":
                logger.info(f"Wrote packet {packet.packet_id} to substrate")
                return True
            logger.error(f"Failed to write packet: {result.error_message}")
            return False

        except Exception as e:
            logger.error(f"Substrate write failed: {e}")
            return False

    # =========================================================================
    # World Model Ingestion
    # =========================================================================

    def ingest_packet(self, packet: PacketEnvelope) -> IngestResult:
        """
        Ingest a packet into the world model.

        Args:
            packet: PacketEnvelope to ingest

        Returns:
            IngestResult
        """
        # Extract the content for ingestion
        content = packet.payload.get("content", packet.payload)
        data_type = packet.payload.get("data_type", "unknown")

        # Transform seed data for world model ingestion
        transformed = self._transform_seed_for_ingestion(content, data_type)

        result = self.ingestor.ingest(
            data=transformed,
            source_type=SourceType.DOCUMENT,
            source_id=str(packet.packet_id),
        )

        self._ingest_results.append(result)

        logger.info(
            f"Ingested packet {packet.packet_id}: "
            f"entities={result.entities_added}, relations={result.relations_added}"
        )

        return result

    def _transform_seed_for_ingestion(
        self,
        content: dict[str, Any],
        data_type: str,
    ) -> dict[str, Any]:
        """
        Transform seed data into format suitable for world model ingestion.

        Args:
            content: Raw seed content
            data_type: Type of seed data

        Returns:
            Transformed data with entities and relations
        """
        entities = []
        relations = []

        if data_type == "architectural_pattern_library":
            # Transform patterns to entities
            for pattern in content.get("patterns", []):
                entity = {
                    "id": pattern.get("id", str(uuid4())),
                    "type": "architectural_pattern",
                    "attributes": {
                        "name": pattern.get("name", ""),
                        "category": pattern.get("category", ""),
                        "description": pattern.get("description", ""),
                        "applicable_when": pattern.get("applicable_when", []),
                        "anti_applicable_when": pattern.get("anti_applicable_when", []),
                        "tradeoffs": pattern.get("tradeoffs", {}),
                        "example_files": pattern.get("example_files", []),
                    },
                }
                entities.append(entity)

                # Create relations to related patterns
                for related in pattern.get("related_patterns", []):
                    relations.append(
                        {
                            "type": "relates_to",
                            "source": pattern.get("id"),
                            "target": related,
                        }
                    )

        elif data_type == "coding_heuristics_library":
            # Transform heuristics to entities
            for heuristic in content.get("heuristics", []):
                entity = {
                    "id": heuristic.get("id", str(uuid4())),
                    "type": "coding_heuristic",
                    "attributes": {
                        "rule": heuristic.get("rule", ""),
                        "severity": heuristic.get("severity", "medium"),
                        "category": heuristic.get("category", ""),
                        "description": heuristic.get("description", ""),
                        "example_good": heuristic.get("example_good", ""),
                        "example_bad": heuristic.get("example_bad", ""),
                        "auto_fix_strategy": heuristic.get("auto_fix_strategy", []),
                    },
                }
                entities.append(entity)

                # Create relations to related patterns
                for related in heuristic.get("related_patterns", []):
                    relations.append(
                        {
                            "type": "applies_pattern",
                            "source": heuristic.get("id"),
                            "target": related,
                        }
                    )

        return {
            "entities": entities,
            "relations": relations,
            "metadata": content.get("metadata", {}),
        }

    # =========================================================================
    # Main Entry Points
    # =========================================================================

    async def load_file(
        self,
        path: str | Path,
        write_to_substrate: bool = True,
        ingest_to_world_model: bool = True,
    ) -> dict[str, Any]:
        """
        Load a single seed file.

        Args:
            path: Path to YAML file
            write_to_substrate: Whether to write to memory substrate
            ingest_to_world_model: Whether to ingest to world model

        Returns:
            Result dict
        """
        packet = self.load_yaml_as_packet(path)

        substrate_success = True
        if write_to_substrate:
            substrate_success = await self.write_packet_to_substrate(packet)

        ingest_result = None
        if ingest_to_world_model:
            ingest_result = self.ingest_packet(packet)

        return {
            "packet_id": str(packet.packet_id),
            "file": str(path),
            "substrate_write": substrate_success,
            "ingest_result": ingest_result.to_dict() if ingest_result else None,
        }

    async def run(
        self,
        write_to_substrate: bool = True,
        ingest_to_world_model: bool = True,
    ) -> dict[str, Any]:
        """
        Load all seed files from the seed directory.

        Loads in order:
        1. architectural_patterns.yaml
        2. coding_heuristics.yaml
        3. reflection_memory.yaml (if exists)
        4. cross_task_graph.yaml (if exists)
        5. Any additional YAML files

        Args:
            write_to_substrate: Whether to write to memory substrate
            ingest_to_world_model: Whether to ingest to world model

        Returns:
            Summary of loading results
        """
        logger.info(f"Starting seed loading from {self.seed_dir}")

        results = []
        reflections_loaded = 0

        # Priority order files
        priority_files = [
            "architectural_patterns.yaml",
            "coding_heuristics.yaml",
            "reflection_memory.yaml",
            "cross_task_graph.yaml",
        ]

        # Load architectural patterns
        patterns_path = self.seed_dir / "architectural_patterns.yaml"
        if patterns_path.exists():
            result = await self.load_file(
                patterns_path,
                write_to_substrate=write_to_substrate,
                ingest_to_world_model=ingest_to_world_model,
            )
            results.append(result)
        else:
            logger.warning(f"Patterns file not found: {patterns_path}")

        # Load coding heuristics
        heuristics_path = self.seed_dir / "coding_heuristics.yaml"
        if heuristics_path.exists():
            result = await self.load_file(
                heuristics_path,
                write_to_substrate=write_to_substrate,
                ingest_to_world_model=ingest_to_world_model,
            )
            results.append(result)
        else:
            logger.warning(f"Heuristics file not found: {heuristics_path}")

        # Load reflection memory (v2.0.0)
        reflection_path = self.seed_dir / "reflection_memory.yaml"
        if reflection_path.exists():
            result = await self.load_reflection_memory_yaml(
                reflection_path,
                write_to_substrate=write_to_substrate,
            )
            results.append(result)
            reflections_loaded = result.get("reflections_loaded", 0)
        else:
            logger.debug(
                f"Reflection memory file not found (optional): {reflection_path}"
            )

        # Load cross-task graph (v2.0.0)
        cross_task_path = self.seed_dir / "cross_task_graph.yaml"
        if cross_task_path.exists():
            result = await self.load_file(
                cross_task_path,
                write_to_substrate=write_to_substrate,
                ingest_to_world_model=ingest_to_world_model,
            )
            results.append(result)
        else:
            logger.debug(
                f"Cross-task graph file not found (optional): {cross_task_path}"
            )

        # Load any additional YAML files in seed directory
        for yaml_file in self.seed_dir.glob("*.yaml"):
            if yaml_file.name not in priority_files:
                result = await self.load_file(
                    yaml_file,
                    write_to_substrate=write_to_substrate,
                    ingest_to_world_model=ingest_to_world_model,
                )
                results.append(result)

        # Calculate totals
        total_entities = sum(
            r.get("ingest_result", {}).get("entities_added", 0) or 0 for r in results
        )
        total_relations = sum(
            r.get("ingest_result", {}).get("relations_added", 0) or 0 for r in results
        )

        # Sync all pending entities to DB (GMP-WIRE: Pipeline unification)
        db_synced = 0
        if hasattr(self.ingestor, "sync_to_db"):
            sync_result = await self.ingestor.sync_to_db()
            db_synced = sync_result.get("entities_synced", 0)
            if sync_result.get("errors"):
                logger.warning(f"DB sync partial: {sync_result['errors']}")

        summary = {
            "files_loaded": len(results),
            "total_entities": total_entities,
            "total_relations": total_relations,
            "reflections_loaded": reflections_loaded,
            "entities_synced_to_db": db_synced,
            "results": results,
        }

        logger.info(
            f"Seed loading complete: {len(results)} files, "
            f"{total_entities} entities, {total_relations} relations, "
            f"{reflections_loaded} reflections, {db_synced} synced to DB"
        )

        return summary

    # =========================================================================
    # Reflection Memory Loading (v2.0.0)
    # =========================================================================

    async def load_reflection_memory_yaml(
        self,
        path: str | Path,
        write_to_substrate: bool = True,
    ) -> dict[str, Any]:
        """
        Load reflection memory YAML into both memory substrate and reflection memory.

        Loads:
        - reflections: Lessons learned
        - patterns: Recognized patterns
        - improvements: Proposed improvements
        - task_reflections: Task-specific reflections

        Args:
            path: Path to reflection_memory.yaml
            write_to_substrate: Whether to write to memory substrate

        Returns:
            Loading result dict
        """
        path = Path(path)

        if not path.exists():
            return {
                "file": str(path),
                "success": False,
                "error": f"File not found: {path}",
                "reflections_loaded": 0,
            }

        try:
            data = self.load_yaml(path)

            if not data:
                return {
                    "file": str(path),
                    "success": False,
                    "error": "Empty YAML file",
                    "reflections_loaded": 0,
                }

            reflections_loaded = 0
            patterns_loaded = 0
            improvements_loaded = 0

            # Create packet for substrate
            packet = self.load_yaml_as_packet(path, "seed.reflection_memory")

            if write_to_substrate:
                await self.write_packet_to_substrate(packet)

            # Load into reflection memory directly
            from world_model.reflection_memory import (
                ReflectionMemory,
                ReflectionPriority,
                ReflectionType,
            )

            # Get or create reflection memory instance
            reflection_memory = None
            if hasattr(self, "_reflection_memory"):
                reflection_memory = self._reflection_memory
            else:
                # Try to get from ingestor's state
                reflection_memory = ReflectionMemory()
                self._reflection_memory = reflection_memory

            # Load reflections
            for reflection_data in data.get("reflections", []):
                reflection_type_str = reflection_data.get("type", "lesson")
                try:
                    reflection_type = ReflectionType(reflection_type_str)
                except ValueError:
                    reflection_type = ReflectionType.LESSON

                priority_str = reflection_data.get("priority", "medium")
                try:
                    priority = ReflectionPriority(priority_str)
                except ValueError:
                    priority = ReflectionPriority.MEDIUM

                reflection_memory.add_reflection(
                    content=reflection_data.get("content", ""),
                    reflection_type=reflection_type,
                    context=reflection_data.get("context", ""),
                    priority=priority,
                    confidence=reflection_data.get("confidence", 0.8),
                    source="seed_file",
                    tags=reflection_data.get("tags", []),
                    metadata=reflection_data.get("metadata", {}),
                )
                reflections_loaded += 1

            # Load patterns
            for pattern_data in data.get("patterns", []):
                reflection_memory.add_pattern(
                    name=pattern_data.get("name", ""),
                    description=pattern_data.get("description", ""),
                    impact=pattern_data.get("impact", "neutral"),
                    triggers=pattern_data.get("triggers", []),
                    outcomes=pattern_data.get("outcomes", []),
                )
                patterns_loaded += 1

            # Load improvements
            for improvement_data in data.get("improvements", []):
                priority_str = improvement_data.get("priority", "medium")
                try:
                    priority = ReflectionPriority(priority_str)
                except ValueError:
                    priority = ReflectionPriority.MEDIUM

                reflection_memory.add_improvement(
                    area=improvement_data.get("area", ""),
                    description=improvement_data.get("description", ""),
                    action_required=improvement_data.get("action_required", ""),
                    priority=priority,
                    expected_impact=improvement_data.get("expected_impact", ""),
                )
                improvements_loaded += 1

            # Load task reflections
            for task_data in data.get("task_reflections", []):
                task_id = task_data.get("task_id", str(uuid4()))
                reflection_memory.record_reflection(
                    task_id=task_id,
                    data=task_data,
                )

            logger.info(
                f"Reflection memory loaded: {reflections_loaded} reflections, "
                f"{patterns_loaded} patterns, {improvements_loaded} improvements"
            )

            return {
                "file": str(path),
                "success": True,
                "reflections_loaded": reflections_loaded,
                "patterns_loaded": patterns_loaded,
                "improvements_loaded": improvements_loaded,
                "packet_id": str(packet.packet_id),
            }

        except Exception as e:
            logger.error(f"Failed to load reflection memory: {e}")
            return {
                "file": str(path),
                "success": False,
                "error": str(e),
                "reflections_loaded": 0,
            }

    # =========================================================================
    # Status
    # =========================================================================

    def get_loaded_packets(self) -> list[PacketEnvelope]:
        """Get all loaded packets."""
        return self._loaded_packets

    def get_ingest_results(self) -> list[IngestResult]:
        """Get all ingestion results."""
        return self._ingest_results


# =============================================================================
# Standalone Runner
# =============================================================================


async def run_seed_loader(
    seed_dir: str | None = None,
    db_url: str | None = None,
) -> dict[str, Any]:
    """
    Run the seed loader as standalone process.

    Args:
        seed_dir: Path to seed directory
        db_url: Database connection URL

    Returns:
        Loading summary
    """
    from memory.substrate_repository import get_substrate_repository

    # Initialize components
    repository = get_substrate_repository(db_url)
    substrate = MemorySubstrateService(repository=repository)

    state = WorldModelState()
    ingestor = KnowledgeIngestor(state=state)

    loader = SeedLoader(
        substrate=substrate,
        ingestor=ingestor,
        seed_dir=seed_dir,
    )

    return await loader.run()


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="L9 World Model Seed Loader")
    parser.add_argument(
        "--seed-dir",
        type=str,
        default=None,
        help="Path to seed directory",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database connection URL",
    )
    parser.add_argument(
        "--no-substrate",
        action="store_true",
        help="Skip writing to memory substrate",
    )
    parser.add_argument(
        "--no-ingest",
        action="store_true",
        help="Skip world model ingestion",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run loader
    async def main():
        from memory.substrate_repository import get_substrate_repository
        from world_model.state import WorldModelState

        # Initialize components
        repository = get_substrate_repository(args.db_url)
        substrate = MemorySubstrateService(repository=repository)

        state = WorldModelState()
        ingestor = KnowledgeIngestor(state=state)

        loader = SeedLoader(
            substrate=substrate,
            ingestor=ingestor,
            seed_dir=args.seed_dir,
        )

        summary = await loader.run(
            write_to_substrate=not args.no_substrate,
            ingest_to_world_model=not args.no_ingest,
        )

        logger.info("\n=== Seed Loading Summary ===")
        logger.info(f"Files loaded: {summary['files_loaded']}")
        logger.info(f"Entities created: {summary['total_entities']}")
        logger.info(f"Relations created: {summary['total_relations']}")

        for result in summary["results"]:
            logger.info(f"\n  - {result['file']}")
            if result.get("ingest_result"):
                ir = result["ingest_result"]
                logger.info(f"    Entities: {ir.get('entities_added', 0)}")
                logger.info(f"    Relations: {ir.get('relations_added', 0)}")

    asyncio.run(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-015",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.schemas",
        "memory.substrate_repository",
        "memory.substrate_service",
    ],
    "tags": [
        "async",
        "cli",
        "config",
        "debugging",
        "filesystem",
        "learning",
        "loader",
        "logging",
        "messaging",
        "service",
    ],
    "keywords": [
        "files",
        "ingest",
        "into",
        "load",
        "loaded",
        "loader",
        "memory",
        "model",
    ],
    "business_value": "Implements SeedLoader for seed loader functionality",
    "last_modified": "2026-01-14T15:02:46Z",
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
