"""
L9 Memory Substrate - Batch Query Helpers

Helper methods for efficient batch database operations.
These methods prevent N+1 query patterns by batching operations.

Usage:
    from memory.substrate_repository_batch_helpers import BatchQueryHelpers
    
    helpers = BatchQueryHelpers(substrate_repo)
    packets_with_metadata = await helpers.get_packets_with_metadata_batch(packet_ids)
"""

import json
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


class BatchQueryHelpers:
    """
    Helper class for batch database operations.
    
    Prevents N+1 query patterns by fetching related data in batch queries.
    """

    def __init__(self, repository):
        """
        Initialize batch helpers with a SubstrateRepository instance.
        
        Args:
            repository: SubstrateRepository instance
        """
        self.repo = repository

    async def get_packets_with_metadata_batch(
        self,
        packet_ids: List[UUID],
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch packets with metadata in 2 queries (not N+1).
        
        This method demonstrates the correct pattern for fetching
        related data without N+1 queries.
        
        Args:
            packet_ids: List of packet IDs to fetch
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            List of packets with metadata attached
            
        Example:
            >>> helpers = BatchQueryHelpers(repo)
            >>> packets = await helpers.get_packets_with_metadata_batch(
            ...     [uuid1, uuid2, uuid3],
            ...     tenant_id="l-cto"
            ... )
            >>> print(packets[0]["metadata"])
        """
        if not packet_ids:
            return []
        
        async with self.repo.acquire() as conn:
            # Query 1: Fetch packets
            packet_query = """
                SELECT 
                    packet_id, packet_type, envelope, timestamp,
                    routing, provenance, thread_id, parent_ids,
                    tags, ttl, scope, importance_score,
                    tenant_id, org_id, user_id
                FROM packets
                WHERE packet_id = ANY($1)
            """
            
            params = [packet_ids]
            if tenant_id:
                packet_query += " AND tenant_id = $2"
                params.append(tenant_id)
            
            packets = await conn.fetch(packet_query, *params)
            
            if not packets:
                return []
            
            # Query 2: Fetch all metadata in one query
            metadata_query = """
                SELECT packet_id, metadata, created_at, updated_at
                FROM packet_metadata
                WHERE packet_id = ANY($1)
            """
            
            metadata_rows = await conn.fetch(metadata_query, packet_ids)
            
            # Build lookup dictionary (in-memory, fast)
            metadata_map = {
                row["packet_id"]: {
                    "metadata": row["metadata"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
                for row in metadata_rows
            }
            
            # Attach metadata to packets
            result = []
            for packet in packets:
                packet_dict = dict(packet)
                packet_dict["metadata"] = metadata_map.get(packet["packet_id"])
                result.append(packet_dict)
            
            logger.debug(
                f"Fetched {len(result)} packets with metadata in 2 queries",
                packet_count=len(result),
                metadata_count=len(metadata_map)
            )
            
            return result

    async def get_packets_with_children_batch(
        self,
        parent_ids: List[UUID],
        tenant_id: Optional[str] = None
    ) -> Dict[UUID, List[Dict[str, Any]]]:
        """
        Fetch packets and their children in 2 queries.
        
        Args:
            parent_ids: List of parent packet IDs
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            Dict mapping parent_id to list of child packets
            
        Example:
            >>> children_by_parent = await helpers.get_packets_with_children_batch(
            ...     [parent_uuid1, parent_uuid2]
            ... )
            >>> print(children_by_parent[parent_uuid1])
        """
        if not parent_ids:
            return {}
        
        async with self.repo.acquire() as conn:
            # Query 1: Fetch parent packets
            parent_query = """
                SELECT * FROM packets
                WHERE packet_id = ANY($1)
            """
            
            params = [parent_ids]
            if tenant_id:
                parent_query += " AND tenant_id = $2"
                params.append(tenant_id)
            
            parents = await conn.fetch(parent_query, *params)
            
            if not parents:
                return {}
            
            # Query 2: Fetch all children in one query
            # Children have parent_id in their parent_ids array
            children_query = """
                SELECT * FROM packets
                WHERE parent_ids && $1
            """
            
            child_params = [parent_ids]
            if tenant_id:
                children_query += " AND tenant_id = $2"
                child_params.append(tenant_id)
            
            children = await conn.fetch(children_query, *child_params)
            
            # Group children by parent (in-memory)
            children_by_parent = {parent_id: [] for parent_id in parent_ids}
            
            for child in children:
                child_dict = dict(child)
                # A child can have multiple parents
                for parent_id in child["parent_ids"]:
                    if parent_id in children_by_parent:
                        children_by_parent[parent_id].append(child_dict)
            
            logger.debug(
                f"Fetched children for {len(parent_ids)} parents in 2 queries",
                parent_count=len(parent_ids),
                child_count=len(children)
            )
            
            return children_by_parent

    async def update_packets_status_batch(
        self,
        packet_ids: List[UUID],
        status: str,
        tenant_id: Optional[str] = None
    ) -> int:
        """
        Update status for multiple packets in one query.
        
        Args:
            packet_ids: List of packet IDs to update
            status: New status value
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            Number of packets updated
            
        Example:
            >>> updated = await helpers.update_packets_status_batch(
            ...     [uuid1, uuid2, uuid3],
            ...     "completed",
            ...     tenant_id="l-cto"
            ... )
            >>> print(f"Updated {updated} packets")
        """
        if not packet_ids:
            return 0
        
        async with self.repo.acquire() as conn:
            query = """
                UPDATE packets
                SET 
                    envelope = jsonb_set(
                        envelope,
                        '{status}',
                        to_jsonb($2::text)
                    ),
                    timestamp = NOW()
                WHERE packet_id = ANY($1)
            """
            
            params = [packet_ids, status]
            if tenant_id:
                query += " AND tenant_id = $3"
                params.append(tenant_id)
            
            result = await conn.execute(query, *params)
            
            # Parse "UPDATE N" to get count
            updated_count = int(result.split()[-1])
            
            logger.info(
                f"Updated status for {updated_count} packets",
                packet_count=updated_count,
                status=status
            )
            
            return updated_count

    async def add_tags_batch(
        self,
        packet_ids: List[UUID],
        tags: List[str],
        tenant_id: Optional[str] = None
    ) -> int:
        """
        Add tags to multiple packets in one query.
        
        Args:
            packet_ids: List of packet IDs
            tags: List of tags to add
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            Number of packets updated
        """
        if not packet_ids or not tags:
            return 0
        
        async with self.repo.acquire() as conn:
            query = """
                UPDATE packets
                SET tags = array_cat(tags, $2)
                WHERE packet_id = ANY($1)
            """
            
            params = [packet_ids, tags]
            if tenant_id:
                query += " AND tenant_id = $3"
                params.append(tenant_id)
            
            result = await conn.execute(query, *params)
            updated_count = int(result.split()[-1])
            
            logger.info(
                f"Added tags to {updated_count} packets",
                packet_count=updated_count,
                tags=tags
            )
            
            return updated_count

    async def remove_tags_batch(
        self,
        packet_ids: List[UUID],
        tags: List[str],
        tenant_id: Optional[str] = None
    ) -> int:
        """
        Remove tags from multiple packets in one query.
        
        Args:
            packet_ids: List of packet IDs
            tags: List of tags to remove
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            Number of packets updated
        """
        if not packet_ids or not tags:
            return 0
        
        async with self.repo.acquire() as conn:
            # Remove each tag using array_remove
            query = """
                UPDATE packets
                SET tags = (
                    SELECT array_agg(tag)
                    FROM unnest(tags) AS tag
                    WHERE tag <> ALL($2)
                )
                WHERE packet_id = ANY($1)
            """
            
            params = [packet_ids, tags]
            if tenant_id:
                query += " AND tenant_id = $3"
                params.append(tenant_id)
            
            result = await conn.execute(query, *params)
            updated_count = int(result.split()[-1])
            
            logger.info(
                f"Removed tags from {updated_count} packets",
                packet_count=updated_count,
                tags=tags
            )
            
            return updated_count

    async def get_packets_by_thread_batch(
        self,
        thread_ids: List[str],
        tenant_id: Optional[str] = None,
        limit: int = 1000
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch packets for multiple threads in one query.
        
        Args:
            thread_ids: List of thread IDs
            tenant_id: Optional tenant ID for filtering
            limit: Maximum packets per thread
            
        Returns:
            Dict mapping thread_id to list of packets
        """
        if not thread_ids:
            return {}
        
        async with self.repo.acquire() as conn:
            query = """
                SELECT * FROM packets
                WHERE thread_id = ANY($1)
            """
            
            params = [thread_ids]
            if tenant_id:
                query += " AND tenant_id = $2"
                params.append(tenant_id)
            
            query += f" ORDER BY timestamp DESC LIMIT {limit}"
            
            packets = await conn.fetch(query, *params)
            
            # Group by thread_id
            packets_by_thread = {thread_id: [] for thread_id in thread_ids}
            
            for packet in packets:
                thread_id = packet["thread_id"]
                if thread_id in packets_by_thread:
                    packets_by_thread[thread_id].append(dict(packet))
            
            logger.debug(
                f"Fetched packets for {len(thread_ids)} threads",
                thread_count=len(thread_ids),
                packet_count=len(packets)
            )
            
            return packets_by_thread

    async def archive_packets_batch(
        self,
        packet_ids: List[UUID],
        tenant_id: Optional[str] = None
    ) -> int:
        """
        Archive multiple packets in one query.
        
        Args:
            packet_ids: List of packet IDs to archive
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            Number of packets archived
        """
        if not packet_ids:
            return 0
        
        async with self.repo.acquire() as conn:
            query = """
                UPDATE packets
                SET 
                    tags = array_append(tags, 'archived'),
                    envelope = jsonb_set(envelope, '{archived}', 'true'),
                    timestamp = NOW()
                WHERE packet_id = ANY($1)
                AND NOT ('archived' = ANY(tags))
            """
            
            params = [packet_ids]
            if tenant_id:
                query += " AND tenant_id = $2"
                params.append(tenant_id)
            
            result = await conn.execute(query, *params)
            archived_count = int(result.split()[-1])
            
            logger.info(
                f"Archived {archived_count} packets",
                packet_count=archived_count
            )
            
            return archived_count


# Convenience function for direct import
async def get_packets_with_metadata(
    repository,
    packet_ids: List[UUID],
    tenant_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to fetch packets with metadata.
    
    This is a shortcut for:
        helpers = BatchQueryHelpers(repository)
        return await helpers.get_packets_with_metadata_batch(packet_ids, tenant_id)
    
    Args:
        repository: SubstrateRepository instance
        packet_ids: List of packet IDs
        tenant_id: Optional tenant ID
        
    Returns:
        List of packets with metadata
    """
    helpers = BatchQueryHelpers(repository)
    return await helpers.get_packets_with_metadata_batch(packet_ids, tenant_id)
