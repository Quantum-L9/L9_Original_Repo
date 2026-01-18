"""
L9 Schema Registry
==================

Centralized schema version management with automatic upcasting.
Provides transparent migration of old packet versions to the latest schema.

Features:
- Version detection from raw packet dicts
- Decorator-based upcaster registration
- Chained migration (v1.0.0 → v1.0.1 → v1.1.0 → v2.0.0)
- LRU cache for upcaster lookups
- Batch upcasting for bulk reads

Usage:
    from core.schemas.schema_registry import SchemaRegistry

    # Read a packet (auto-upcasts to latest version)
    packet = SchemaRegistry.read_packet(raw_dict)

    # Register custom upcaster
    @SchemaRegistry.register("1.0.0", "1.0.1")
    def upcast_1_0_0_to_1_0_1(packet: dict) -> dict:
        packet["new_field"] = "default_value"
        return packet
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Schema Registry",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "error_handling",
    "module_name": "schema_registry",
    "type": "exception",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "ci.check_schema_deprecation",
            "core.schemas.schema_registry",
            "tests.core.schemas.test_content_hash_integrity",
            "tests.core.schemas.test_schema_registry",
        ],
    },
}
# ============================================================================

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from functools import lru_cache
from typing import Callable
from uuid import UUID

import structlog

from core.schemas import (
    PacketEnvelope,
    PacketMetadata,
    PacketLineage,
    PacketProvenance,
    PacketConfidence,
    SCHEMA_VERSION,
    SUPPORTED_VERSIONS,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class UpcasterNotFoundError(Exception):
    """Raised when no upcaster path exists between versions."""

    pass


class InvalidSchemaVersionError(Exception):
    """Raised when a schema version is malformed or unsupported."""

    pass


# =============================================================================
# Schema Registry (Singleton)
# =============================================================================


class _SchemaRegistry:
    """
    Central registry for PacketEnvelope schema versions and upcasters.

    Provides:
    - Version detection from raw dicts
    - Automatic upcasting to latest version
    - Decorator-based upcaster registration
    - Chained migration paths
    """

    def __init__(self):
        self._upcasters: dict[str, Callable[[dict], dict]] = {}
        self._migration_graph: dict[str, list[str]] = {}
        self._register_builtin_upcasters()

    def _register_builtin_upcasters(self):
        """Register built-in upcasters for known version transitions."""

        # v1.0.0 → v1.0.1 (no changes, just version bump)
        @self.register("1.0.0", "1.0.1")
        def upcast_1_0_0_to_1_0_1(packet: dict) -> dict:
            if "metadata" not in packet or packet["metadata"] is None:
                packet["metadata"] = {}
            packet["metadata"]["schema_version"] = "1.0.1"
            return packet

        # v1.0.1 → v1.1.0 (add thread_id, lineage, tags, ttl)
        @self.register("1.0.1", "1.1.0")
        def upcast_1_0_1_to_1_1_0(packet: dict) -> dict:
            # Add new v1.1.0 fields with defaults
            packet.setdefault("thread_id", None)
            packet.setdefault("lineage", None)
            packet.setdefault("tags", [])
            packet.setdefault("ttl", None)

            if "metadata" not in packet or packet["metadata"] is None:
                packet["metadata"] = {}
            packet["metadata"]["schema_version"] = "1.1.0"

            return packet

        # v1.1.0 → v1.1.1 (add model_config immutability - no data change)
        @self.register("1.1.0", "1.1.1")
        def upcast_1_1_0_to_1_1_1(packet: dict) -> dict:
            if "metadata" not in packet or packet["metadata"] is None:
                packet["metadata"] = {}
            packet["metadata"]["schema_version"] = "1.1.1"
            return packet

        # v1.1.1 → v2.0.0 (add content_hash field)
        @self.register("1.1.1", "2.0.0")
        def upcast_1_1_1_to_2_0_0(packet: dict) -> dict:
            if "metadata" not in packet or packet["metadata"] is None:
                packet["metadata"] = {}
            packet["metadata"]["schema_version"] = "2.0.0"

            # Ensure domain is set
            packet["metadata"].setdefault("domain", "l9")

            # Compute content hash for integrity verification (GMP #3)
            content = {
                "payload": packet.get("payload", {}),
                "metadata": packet["metadata"],
                "timestamp": packet.get("timestamp"),
            }
            content_bytes = json.dumps(content, sort_keys=True, default=str).encode(
                "utf-8"
            )
            packet["content_hash"] = hashlib.sha256(content_bytes).hexdigest()

            return packet

    def register(
        self, from_version: str, to_version: str
    ) -> Callable[[Callable[[dict], dict]], Callable[[dict], dict]]:
        """
        Decorator to register an upcaster function.

        Args:
            from_version: Source schema version (e.g., "1.0.0")
            to_version: Target schema version (e.g., "1.0.1")

        Returns:
            Decorator function

        Raises:
            ValueError: If an upcaster already exists for this version pair

        Usage:
            @SchemaRegistry.register("1.0.0", "1.0.1")
            def upcast_1_0_0_to_1_0_1(packet: dict) -> dict:
                packet["new_field"] = "default"
                return packet
        """
        key = f"{from_version}->{to_version}"

        def decorator(func: Callable[[dict], dict]) -> Callable[[dict], dict]:
            if key in self._upcasters:
                raise ValueError(
                    f"Upcaster already registered for {key}. "
                    f"Existing: {self._upcasters[key].__name__}"
                )

            self._upcasters[key] = func

            # Update migration graph
            if from_version not in self._migration_graph:
                self._migration_graph[from_version] = []
            self._migration_graph[from_version].append(to_version)

            logger.debug(
                "registered_upcaster",
                from_version=from_version,
                to_version=to_version,
                func=func.__name__,
            )

            return func

        return decorator

    def detect_version(self, raw: dict) -> str:
        """
        Detect the schema version of a raw packet dict.

        Args:
            raw: Raw packet dictionary

        Returns:
            Schema version string (e.g., "1.0.0", "1.1.0", "2.0.0")
        """
        # Check metadata.schema_version first
        metadata = raw.get("metadata")
        if metadata and isinstance(metadata, dict):
            version = metadata.get("schema_version")
            if version and isinstance(version, str):
                return version

        # Infer version from field presence
        if "content_hash" in raw:
            return "2.0.0"
        elif "thread_id" in raw or "lineage" in raw or "tags" in raw or "ttl" in raw:
            return "1.1.0"
        elif "provenance" in raw and raw.get("provenance"):
            prov = raw["provenance"]
            if isinstance(prov, dict) and "source_agent" in prov:
                return "1.0.1"

        # Default to oldest version
        return "1.0.0"

    @lru_cache(maxsize=128)
    def _compute_migration_path(
        self, from_version: str, to_version: str
    ) -> tuple[str, ...]:
        """
        Compute the shortest migration path between versions using BFS.

        Args:
            from_version: Starting version
            to_version: Target version

        Returns:
            Tuple of version strings representing the path

        Raises:
            UpcasterNotFoundError: If no path exists
        """
        if from_version == to_version:
            return (from_version,)

        # BFS for shortest path
        from collections import deque

        queue = deque([(from_version, [from_version])])
        visited = {from_version}

        while queue:
            current, path = queue.popleft()

            for next_version in self._migration_graph.get(current, []):
                if next_version == to_version:
                    return tuple(path + [next_version])

                if next_version not in visited:
                    visited.add(next_version)
                    queue.append((next_version, path + [next_version]))

        raise UpcasterNotFoundError(
            f"No migration path found from {from_version} to {to_version}. "
            f"Known versions: {list(self._migration_graph.keys())}"
        )

    def upcast(self, raw: dict, target_version: str = SCHEMA_VERSION) -> dict:
        """
        Upcast a raw packet dict to the target schema version.

        Args:
            raw: Raw packet dictionary (will NOT be mutated)
            target_version: Target schema version (default: latest)

        Returns:
            New dict upcasted to target version

        Raises:
            UpcasterNotFoundError: If no migration path exists
        """
        # Detect current version
        current_version = self.detect_version(raw)

        if current_version == target_version:
            return raw

        # Get migration path
        path = self._compute_migration_path(current_version, target_version)

        # Copy to avoid mutation
        result = deepcopy(raw)

        # Apply upcasters along path
        for i in range(len(path) - 1):
            from_v = path[i]
            to_v = path[i + 1]
            key = f"{from_v}->{to_v}"

            upcaster = self._upcasters.get(key)
            if not upcaster:
                raise UpcasterNotFoundError(f"Missing upcaster for {key}. Path: {path}")

            result = upcaster(result)

            logger.debug(
                "applied_upcaster",
                from_version=from_v,
                to_version=to_v,
            )

        return result

    def read_packet(self, raw: dict) -> PacketEnvelope:
        """
        Read a raw packet dict and return a PacketEnvelope.

        Automatically upcasts to the latest schema version.

        Args:
            raw: Raw packet dictionary

        Returns:
            PacketEnvelope instance (latest version)
        """
        # Upcast to latest version
        upcasted = self.upcast(raw, SCHEMA_VERSION)

        # Handle nested model conversion
        if "metadata" in upcasted and upcasted["metadata"] is not None:
            if isinstance(upcasted["metadata"], dict):
                upcasted["metadata"] = PacketMetadata(**upcasted["metadata"])

        if "provenance" in upcasted and upcasted["provenance"] is not None:
            if isinstance(upcasted["provenance"], dict):
                upcasted["provenance"] = PacketProvenance(**upcasted["provenance"])

        if "confidence" in upcasted and upcasted["confidence"] is not None:
            if isinstance(upcasted["confidence"], dict):
                upcasted["confidence"] = PacketConfidence(**upcasted["confidence"])

        if "lineage" in upcasted and upcasted["lineage"] is not None:
            if isinstance(upcasted["lineage"], dict):
                upcasted["lineage"] = PacketLineage(**upcasted["lineage"])

        # Handle UUID conversion
        if "packet_id" in upcasted and isinstance(upcasted["packet_id"], str):
            upcasted["packet_id"] = UUID(upcasted["packet_id"])

        if "thread_id" in upcasted and isinstance(upcasted["thread_id"], str):
            upcasted["thread_id"] = UUID(upcasted["thread_id"])

        # Handle datetime conversion
        if "timestamp" in upcasted and isinstance(upcasted["timestamp"], str):
            upcasted["timestamp"] = datetime.fromisoformat(
                upcasted["timestamp"].replace("Z", "+00:00")
            )

        if "ttl" in upcasted and isinstance(upcasted["ttl"], str):
            upcasted["ttl"] = datetime.fromisoformat(
                upcasted["ttl"].replace("Z", "+00:00")
            )

        return PacketEnvelope(**upcasted)

    def read_packets(self, raws: list[dict]) -> list[PacketEnvelope]:
        """
        Batch read multiple raw packet dicts.

        More efficient than calling read_packet() in a loop due to
        migration path caching.

        Args:
            raws: List of raw packet dictionaries

        Returns:
            List of PacketEnvelope instances
        """
        return [self.read_packet(raw) for raw in raws]

    def write_packet(self, packet: PacketEnvelope) -> dict:
        """
        Serialize a PacketEnvelope to a dict for storage.

        Args:
            packet: PacketEnvelope instance

        Returns:
            Dictionary suitable for JSON serialization
        """
        return packet.model_dump(mode="json")

    @property
    def current_version(self) -> str:
        """Get the current (latest) schema version."""
        return SCHEMA_VERSION

    @property
    def supported_versions(self) -> list[str]:
        """Get list of all supported schema versions."""
        return SUPPORTED_VERSIONS.copy()


# =============================================================================
# Singleton Instance
# =============================================================================

SchemaRegistry = _SchemaRegistry()


# =============================================================================
# Convenience Functions
# =============================================================================


def read_packet(raw: dict) -> PacketEnvelope:
    """Convenience function to read a packet via SchemaRegistry."""
    return SchemaRegistry.read_packet(raw)


def read_packets(raws: list[dict]) -> list[PacketEnvelope]:
    """Convenience function to batch read packets via SchemaRegistry."""
    return SchemaRegistry.read_packets(raws)


def write_packet(packet: PacketEnvelope) -> dict:
    """Convenience function to serialize a packet via SchemaRegistry."""
    return SchemaRegistry.write_packet(packet)


def detect_version(raw: dict) -> str:
    """Convenience function to detect packet version."""
    return SchemaRegistry.detect_version(raw)


def upcast(raw: dict, target_version: str = SCHEMA_VERSION) -> dict:
    """Convenience function to upcast a packet dict."""
    return SchemaRegistry.upcast(raw, target_version)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-072",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas"],
    "tags": [
        "batch-processing",
        "debugging",
        "error-handling",
        "exception",
        "foundation",
        "logging",
        "queue",
        "security",
        "serialization",
    ],
    "keywords": [
        "cache",
        "current",
        "decorator",
        "detect",
        "detection",
        "found",
        "invalid",
        "latest",
    ],
    "business_value": "Provides transparent migration of old packet versions to the latest schema. Version detection from raw packet dicts Decorator-based upcaster registration Chained migration (v1.0.0 → v1.0.1 → v1.1.0 → ",
    "last_modified": "2026-01-14T15:03:00Z",
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
