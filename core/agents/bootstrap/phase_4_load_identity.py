"""
Phase 4: Load Identity Persona

Harvested from: L9-Agent-Bootstrap-Architecture.md
Purpose: Parse identity.yaml, hydrate agent's self-awareness (designation, role, mission, constraints).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from pathlib import Path
from datetime import datetime

import yaml
import structlog

from memory.graph_client import get_neo4j_client

if TYPE_CHECKING:
    from .phase_2_instantiate import BootstrapInstanceData
    from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)


async def load_identity_persona(
    instance: "BootstrapInstanceData",
    substrate_service: "MemorySubstrateService",
    identity_yaml_path: Optional[str] = None,
) -> None:
    """
    Load identity persona from YAML and hydrate memory.
    """
    # Default identity path based on agent_id
    if identity_yaml_path is None:
        identity_yaml_path = f"private/agents/identity/{instance.agent_id}_identity.yaml"
    
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
        with open(identity_path, 'r') as f:
            identity_data = yaml.safe_load(f)
        
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
        if hasattr(substrate_service, 'write_packet'):
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
                        "timestamp": datetime.utcnow().isoformat(),
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
        
        # Update Neo4j if available
        neo4j_client = await get_neo4j_client()
        if neo4j_client:
            try:
                async with neo4j_client.session() as session:
                    await session.run("""
                        MATCH (a:Agent {instance_id: $instance_id})
                        SET a.designation = $designation,
                            a.role = $role,
                            a.mission = $mission,
                            a.authority = $authority,
                            a.identity_loaded_at = $loaded_at
                    """, {
                        "instance_id": instance.instance_id,
                        "designation": identity_chunk["designation"],
                        "role": identity_chunk["role"],
                        "mission": identity_chunk["mission"],
                        "authority": identity_chunk["authority_level"],
                        "loaded_at": datetime.utcnow().isoformat(),
                    })
            except Exception as e:
                logger.warning("Failed to update identity in Neo4j", error=str(e))
    
    except Exception as e:
        logger.error("Failed to load identity", error=str(e))
        # Set minimal identity on failure
        instance.designation = instance.agent_id
        instance.role = "Agent"

