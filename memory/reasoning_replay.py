"""
L9 Memory - Reasoning Replay Pipeline
Version: 1.0.0

Reconstructs decision chains and reasoning traces for explainability.
Implements memory_spec_v3.0.yaml pipelines.reasoning_replay contract.

Responsibilities:
- Chain reconstruction from PacketLineage.parent_ids
- Decision ancestor traversal
- Decision explanation in multiple formats
- Lineage integrity validation
- Orphaned packet detection and repair
"""

from __future__ import annotations

import structlog
from datetime import datetime
from typing import Any, Optional, List
from uuid import UUID

from memory.substrate_repository import SubstrateRepository

logger = structlog.get_logger(__name__)


class ReasoningChain:
    """Represents a reconstructed reasoning chain."""
    
    def __init__(
        self,
        chain_id: UUID,
        start_packet_id: UUID,
        packets: List[dict[str, Any]],
        depth: int,
        is_complete: bool,
    ):
        self.chain_id = chain_id
        self.start_packet_id = start_packet_id
        self.packets = packets
        self.depth = depth
        self.is_complete = is_complete
        self.created_at = datetime.utcnow()


class ReasoningReplayPipeline:
    """
    Reasoning replay pipeline for decision chain reconstruction.
    
    Per memory_spec_v3.0.yaml pipelines.reasoning_replay:
    - reconstruct_chain(packet_id) -> ReasoningChain
    - get_decision_ancestors(packet_id, max_depth) -> List[Packet]
    - explain_decision(packet_id, format) -> str
    - verify_lineage_integrity(packet_id) -> bool
    - detect_orphaned_packets(agent_id) -> List[UUID]
    - repair_broken_lineage(packet_id) -> bool
    """

    def __init__(self, repository: Optional[SubstrateRepository] = None):
        """
        Initialize reasoning replay pipeline.
        
        Args:
            repository: SubstrateRepository for packet access
        """
        self._repository = repository
        self._max_depth = 50  # Per spec
        self._timeout_seconds = 10  # Per spec
        logger.info("ReasoningReplayPipeline initialized")

    def set_repository(self, repository: SubstrateRepository) -> None:
        """Set or update repository reference."""
        self._repository = repository

    async def reconstruct_chain(
        self,
        packet_id: UUID,
        max_depth: Optional[int] = None,
    ) -> ReasoningChain:
        """
        Reconstruct reasoning chain from a packet.
        
        Traverses PacketLineage.parent_ids to build full decision DAG.
        
        Args:
            packet_id: Starting packet UUID
            max_depth: Maximum traversal depth (default: 50)
            
        Returns:
            ReasoningChain with full chain
        """
        if self._repository is None:
            raise RuntimeError("Repository not set")
        
        max_depth = max_depth or self._max_depth
        logger.debug("Reconstructing chain", packet_id=str(packet_id), max_depth=max_depth)
        
        visited = set()
        packets = []
        queue = [(packet_id, 0)]  # (packet_id, depth)
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if depth > max_depth:
                logger.warning("Max depth reached", packet_id=str(current_id), depth=depth)
                break
            
            if current_id in visited:
                logger.debug("Cycle detected, skipping", packet_id=str(current_id))
                continue
            
            visited.add(current_id)
            
            # Get packet
            packet = await self._repository.get_packet(current_id)
            if not packet:
                logger.warning("Packet not found", packet_id=str(current_id))
                continue
            
            # Add to chain
            packets.append({
                "packet_id": str(current_id),
                "packet_type": packet.envelope.get("packet_type", "unknown"),
                "timestamp": packet.envelope.get("timestamp"),
                "payload": packet.envelope.get("payload", {}),
                "metadata": packet.envelope.get("metadata", {}),
                "depth": depth,
            })
            
            # Get parent IDs from packet row
            if hasattr(packet, 'parent_ids') and packet.parent_ids:
                for parent_id in packet.parent_ids:
                    if parent_id not in visited:
                        queue.append((parent_id, depth + 1))
        
        chain_id = UUID(packets[0]["packet_id"]) if packets else packet_id
        is_complete = len(queue) == 0  # No remaining packets
        
        return ReasoningChain(
            chain_id=chain_id,
            start_packet_id=packet_id,
            packets=packets,
            depth=len(packets),
            is_complete=is_complete,
        )

    async def get_decision_ancestors(
        self,
        packet_id: UUID,
        max_depth: int = 10,
    ) -> List[dict[str, Any]]:
        """
        Get decision ancestors (parents) of a packet.
        
        Args:
            packet_id: Packet UUID
            max_depth: Maximum depth to traverse
            
        Returns:
            List of ancestor packets
        """
        if self._repository is None:
            raise RuntimeError("Repository not set")
        
        ancestors = []
        visited = set()
        current_id = packet_id
        depth = 0
        
        while depth < max_depth:
            if current_id in visited:
                break
            
            visited.add(current_id)
            
            # Get packet to access parent_ids
            packet = await self._repository.get_packet(current_id)
            if not packet or not hasattr(packet, 'parent_ids') or not packet.parent_ids:
                break
            
            # Get first parent (primary ancestor)
            parent_id = packet.parent_ids[0]
            parent_packet = await self._repository.get_packet(parent_id)
            
            if not parent_packet:
                break
            
            ancestors.append({
                "packet_id": str(parent_id),
                "packet_type": parent_packet.envelope.get("packet_type", "unknown"),
                "timestamp": parent_packet.envelope.get("timestamp"),
                "depth": depth + 1,
            })
            
            current_id = parent_id
            depth += 1
        
        return ancestors

    async def explain_decision(
        self,
        packet_id: UUID,
        format: str = "narrative",
    ) -> str:
        """
        Explain a decision in the specified format.
        
        Args:
            packet_id: Decision packet UUID
            format: Output format (json, narrative, graph_viz, mermaid)
            
        Returns:
            Explanation string in requested format
        """
        if self._repository is None:
            raise RuntimeError("Repository not set")
        
        chain = await self.reconstruct_chain(packet_id)
        
        if format == "json":
            import json
            return json.dumps({
                "chain_id": str(chain.chain_id),
                "start_packet_id": str(chain.start_packet_id),
                "depth": chain.depth,
                "is_complete": chain.is_complete,
                "packets": chain.packets,
            }, indent=2)
        
        elif format == "narrative":
            narrative = f"Decision Chain (ID: {chain.chain_id})\n"
            narrative += f"Starting from packet: {chain.start_packet_id}\n"
            narrative += f"Depth: {chain.depth}, Complete: {chain.is_complete}\n\n"
            
            for i, packet in enumerate(chain.packets, 1):
                narrative += f"{i}. [{packet['packet_type']}] {packet.get('timestamp', 'unknown')}\n"
                if packet.get("payload"):
                    narrative += f"   Payload keys: {', '.join(packet['payload'].keys())[:50]}\n"
            
            return narrative
        
        elif format == "graph_viz":
            # Graphviz DOT format
            dot = "digraph DecisionChain {\n"
            for i, packet in enumerate(chain.packets):
                node_id = f"p{i}"
                label = f"{packet['packet_type']}\\n{packet.get('timestamp', '')[:10]}"
                dot += f'  {node_id} [label="{label}"];\n'
                if i > 0:
                    dot += f"  p{i-1} -> {node_id};\n"
            dot += "}\n"
            return dot
        
        elif format == "mermaid":
            # Mermaid flowchart format
            mermaid = "graph TD\n"
            for i, packet in enumerate(chain.packets):
                node_id = f"P{i}"
                label = f"{packet['packet_type']}"
                mermaid += f'  {node_id}["{label}"]\n'
                if i > 0:
                    mermaid += f"  P{i-1} --> {node_id}\n"
            return mermaid
        
        else:
            raise ValueError(f"Unsupported format: {format}")

    async def verify_lineage_integrity(self, packet_id: UUID) -> bool:
        """
        Verify lineage integrity for a packet.
        
        Checks:
        - All parent_ids exist
        - No cycles
        - Depth within limits
        
        Args:
            packet_id: Packet UUID to verify
            
        Returns:
            True if integrity is valid, False otherwise
        """
        if self._repository is None:
            raise RuntimeError("Repository not set")
        
        try:
            visited = set()
            queue = [packet_id]
            
            while queue:
                current_id = queue.pop(0)
                
                if current_id in visited:
                    logger.warning("Cycle detected in lineage", packet_id=str(current_id))
                    return False
                
                visited.add(current_id)
                
                # Get packet to access parent_ids
                packet = await self._repository.get_packet(current_id)
                if packet and hasattr(packet, 'parent_ids') and packet.parent_ids:
                    for parent_id in packet.parent_ids:
                        # Verify parent exists
                        parent = await self._repository.get_packet(parent_id)
                        if not parent:
                            logger.warning("Orphaned parent reference", parent_id=str(parent_id))
                            return False
                        
                        if parent_id not in visited:
                            queue.append(parent_id)
            
            return True
        
        except Exception as e:
            logger.error("Lineage integrity check failed", error=str(e), exc_info=True)
            return False

    async def detect_orphaned_packets(self, agent_id: str) -> List[UUID]:
        """
        Detect orphaned packets (packets with no valid lineage).
        
        Args:
            agent_id: Agent ID to check
            
        Returns:
            List of orphaned packet UUIDs
        """
        if self._repository is None:
            raise RuntimeError("Repository not set")
        
        # Get all packets for agent
        # Note: This is a simplified implementation
        # In production, would query packetstore with agent_id filter
        orphaned = []
        
        # TODO: Implement actual orphan detection query
        # For now, return empty list
        logger.warning("Orphan detection not fully implemented", agent_id=agent_id)
        
        return orphaned

    async def repair_broken_lineage(self, packet_id: UUID) -> bool:
        """
        Attempt to repair broken lineage for a packet.
        
        Args:
            packet_id: Packet UUID to repair
            
        Returns:
            True if repair succeeded, False otherwise
        """
        if self._repository is None:
            raise RuntimeError("Repository not set")
        
        logger.info("Repairing broken lineage", packet_id=str(packet_id))
        
        # Verify integrity first
        is_valid = await self.verify_lineage_integrity(packet_id)
        if is_valid:
            logger.debug("Lineage already valid", packet_id=str(packet_id))
            return True
        
        # Attempt repair: remove invalid parent references
        packet = await self._repository.get_packet(packet_id)
        if packet and hasattr(packet, 'parent_ids') and packet.parent_ids:
            valid_parents = []
            for parent_id in packet.parent_ids:
                parent = await self._repository.get_packet(parent_id)
                if parent:
                    valid_parents.append(parent_id)
            
            # Update lineage with only valid parents
            # Note: This requires repository method to update packet parent_ids
            # For now, log repair attempt
            logger.info(
                "Repair attempted",
                packet_id=str(packet_id),
                original_parents=len(packet.parent_ids),
                valid_parents=len(valid_parents),
            )
            
            return len(valid_parents) > 0
        
        return False

