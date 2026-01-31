"""
Phase 4: Load Identity Persona

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Parse identity.yaml, hydrate agent's self-awareness (designation, role, mission, constraints).
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Phase 4 Load Identity",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "phase_4_load_identity",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": ["working_memory"],
        "imported_by": ["tests.core.bootstrap.test_bootstrap_phases"],
    },
}
# ============================================================================

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles
import structlog
import yaml

if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService

    from .phase_2_instantiate import BootstrapInstanceData

logger = structlog.get_logger(__name__)


async def load_identity_persona(
    instance: BootstrapInstanceData,
    substrate_service: MemorySubstrateService,
    identity_yaml_path: str | None = None,
) -> None:
    """
    Load identity persona from YAML and hydrate memory.
    """
    # Default identity path based on agent_id
    if identity_yaml_path is None:
        identity_yaml_path = (
            f"private/agents/identity/{instance.agent_id}_identity.yaml"
        )

    identity_path = Path(identity_yaml_path)

    # Try fallback paths
    if not identity_path.exists():
        fallback_paths = [
            Path(f"private/agents/{instance.agent_id}/identity.yaml"),
            Path(f"config/agents/{instance.agent_id}_identity.yaml"),
            Path("private/agents/identity/L_identity.yaml"),  # Default L identity
        ]
        for fallback in fallback_paths:
            if fallback.exists():
                identity_path = fallback
                break

    if not identity_path.exists():
        logger.warning(
            "Identity YAML not found, using defaults",
            agent_id=instance.agent_id,
            tried_path=identity_yaml_path,
        )
        # Set minimal identity
        instance.designation = instance.agent_id
        instance.role = "Agent"
        instance.mission = "Execute tasks"
        return

    try:
        async with aiofiles.open(identity_path) as f:
            identity_data = yaml.safe_load(await f.read())

        # Create identity memory chunk
        identity_chunk = {
            "designation": identity_data.get("designation", instance.agent_id),
            "role": identity_data.get("role", "Agent"),
            "mission": identity_data.get("mission", ""),
            "constraints": identity_data.get("constraints", []),
            "personality_traits": identity_data.get("traits", []),
            "authority_level": identity_data.get("authority", ""),
            "allegiance": identity_data.get("allegiance", ""),
        }

        # Update instance with identity
        instance.designation = identity_chunk["designation"]
        instance.role = identity_chunk["role"]
        instance.mission = identity_chunk["mission"]
        instance.authority = identity_chunk["authority_level"]

        # Write to memory substrate if available
        if hasattr(substrate_service, "write_packet"):
            try:
                from core.schemas import PacketEnvelopeIn

                packet = PacketEnvelopeIn(
                    packet_type="memory_write",
                    payload={
                        "chunk_type": "identity",
                        "designation": identity_chunk["designation"],
                        "role": identity_chunk["role"],
                        "mission": identity_chunk["mission"],
                        "constraints": identity_chunk["constraints"],
                        "traits": identity_chunk["personality_traits"],
                        "authority": identity_chunk["authority_level"],
                        "allegiance": identity_chunk["allegiance"],
                        "agent_id": instance.agent_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    metadata={"agent": instance.agent_id, "schema_version": "1.0.0"},
                )
                await substrate_service.write_packet(packet)
            except ImportError:
                logger.debug("PacketEnvelopeIn not available, skipping memory write")

        logger.info(
            "Loaded identity",
            agent_id=instance.agent_id,
            designation=identity_chunk["designation"],
            role=identity_chunk["role"],
        )

        # Update Neo4j if available (lazy import to avoid test collection issues)
        from memory.graph_client import get_neo4j_client

        neo4j_client = await get_neo4j_client()
        if neo4j_client:
            try:
                async with neo4j_client.session() as session:
                    await session.run(
                        """
                        MATCH (a:Agent {instance_id: $instance_id})
                        SET a.designation = $designation,
                            a.role = $role,
                            a.mission = $mission,
                            a.authority = $authority,
                            a.identity_loaded_at = $loaded_at
                    """,
                        {
                            "instance_id": instance.instance_id,
                            "designation": identity_chunk["designation"],
                            "role": identity_chunk["role"],
                            "mission": identity_chunk["mission"],
                            "authority": identity_chunk["authority_level"],
                            "loaded_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
            except Exception as e:
                logger.warning("Failed to update identity in Neo4j", error=str(e))

    except Exception as e:
        logger.error("Failed to load identity", error=str(e))
        # Set minimal identity on failure
        instance.designation = instance.agent_id
        instance.role = "Agent"


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas", "memory.graph_client", "memory.substrate_service"],
    "tags": [
        "agent-execution",
        "api",
        "async",
        "auth",
        "config",
        "debugging",
        "filesystem",
        "foundation",
        "logging",
        "service",
    ],
    "keywords": ["agent", "identity", "load", "persona", "phase"],
    "business_value": "Utility module for phase 4 load identity",
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
