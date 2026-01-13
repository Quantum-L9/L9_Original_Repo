"""
L9 Memory - Neo4j Graph Client
===============================

Production Neo4j client for L9 knowledge graph operations.

Provides:
- Entity graph storage and traversal
- Relationship management
- Event timeline queries
- Knowledge fact storage

Version: 1.0.0
"""

from __future__ import annotations

import structlog
import os
from typing import Any, Optional

logger = structlog.get_logger(__name__)

# Try to import Neo4j driver
try:
    from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession, basic_auth
    from neo4j.exceptions import ServiceUnavailable, AuthError

    _has_neo4j = True
except ImportError:
    _has_neo4j = False
    logger.warning(
        "Neo4j driver not available - install with: pip install neo4j>=5.0.0"
    )


class Neo4jClient:
    """
    Production Neo4j client with connection management.

    Provides async graph database operations for the L9 memory layer.
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: str = "neo4j",
    ):
        """
        Initialize Neo4j client.

        Args:
            uri: Neo4j URI (default: NEO4J_URI env or 'bolt://localhost:7687')
            user: Neo4j username (default: NEO4J_USER env or 'neo4j')
            password: Neo4j password (default: NEO4J_PASSWORD env)
            database: Database name (default: 'neo4j')
        """
        if not _has_neo4j:
            self._driver = None
            self._available = False
            logger.warning(
                "Neo4j driver not available - operations will fail gracefully"
            )
            return

        self._uri = uri or os.getenv("NEO4J_URL") or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self._user = user or os.getenv("NEO4J_USER", "neo4j")
        self._password = password or os.getenv("NEO4J_PASSWORD")
        self._database = database
        self._driver: Optional[AsyncDriver] = None
        self._available = False

    async def connect(self) -> bool:
        """
        Connect to Neo4j server.

        Returns:
            True if connected, False if unavailable
        """
        if not _has_neo4j:
            return False

        if self._driver is not None:
            return self._available

        if not self._password:
            logger.warning("NEO4J_PASSWORD not set - cannot connect to Neo4j")
            return False

        try:
            self._driver = AsyncGraphDatabase.driver(
                self._uri,
                auth=basic_auth(self._user, self._password),
            )

            # Test connection
            async with self._driver.session(database=self._database) as session:
                await session.run("RETURN 1")

            self._available = True
            logger.info(f"Neo4j connected: {self._uri}/{self._database}")
            return True
        except (ServiceUnavailable, AuthError) as e:
            logger.warning(f"Neo4j connection failed: {e}")
            self._driver = None
            self._available = False
            return False
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e}")
            self._driver = None
            self._available = False
            return False

    async def disconnect(self) -> None:
        """Close Neo4j connection."""
        if self._driver:
            try:
                await self._driver.close()
                logger.info("Neo4j disconnected")
            except Exception as e:
                logger.warning(f"Error disconnecting Neo4j: {e}")
            finally:
                self._driver = None
                self._available = False

    def is_available(self) -> bool:
        """Check if Neo4j is available."""
        return self._available and self._driver is not None

    @property
    def driver(self) -> Optional[AsyncDriver]:
        """Expose the raw AsyncDriver for components that need it (e.g., AgentGraphLoader)."""
        return self._driver

    def session(self, database: Optional[str] = None) -> AsyncSession:
        """Create a session (AsyncDriver-compatible interface).
        
        This allows Neo4jClient to be used where an AsyncDriver is expected.
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver not initialized")
        db = database or self._database
        return self._driver.session(database=db)

    async def _get_session(self) -> Optional[AsyncSession]:
        """Get a session for database operations."""
        if not self.is_available():
            return None
        return self._driver.session(database=self._database)

    # =========================================================================
    # Entity Operations
    # =========================================================================

    async def create_entity(
        self,
        entity_type: str,
        entity_id: str,
        properties: dict[str, Any],
    ) -> Optional[str]:
        """
        Create or merge an entity node.

        Args:
            entity_type: Node label (e.g., 'User', 'Agent', 'Event')
            entity_id: Unique entity identifier
            properties: Node properties

        Returns:
            Entity ID or None if failed
        """
        if not self.is_available():
            return None

        try:
            async with self._driver.session(database=self._database) as session:
                query = f"""
                MERGE (n:{entity_type} {{id: $entity_id}})
                SET n += $properties
                RETURN n.id as id
                """
                result = await session.run(
                    query,
                    entity_id=entity_id,
                    properties=properties,
                )
                record = await result.single()
                logger.debug(f"Created/updated entity: {entity_type}:{entity_id}")
                return record["id"] if record else None
        except Exception as e:
            logger.error(f"Neo4j create_entity failed: {e}")
            return None

    async def get_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Get an entity by type and ID.

        Args:
            entity_type: Node label
            entity_id: Entity identifier

        Returns:
            Entity properties or None
        """
        if not self.is_available():
            return None

        try:
            async with self._driver.session(database=self._database) as session:
                query = f"""
                MATCH (n:{entity_type} {{id: $entity_id}})
                RETURN n
                """
                result = await session.run(query, entity_id=entity_id)
                record = await result.single()
                if record:
                    return dict(record["n"])
                return None
        except Exception as e:
            logger.error(f"Neo4j get_entity failed: {e}")
            return None

    async def delete_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> bool:
        """
        Delete an entity and its relationships.

        Args:
            entity_type: Node label
            entity_id: Entity identifier

        Returns:
            True if deleted
        """
        if not self.is_available():
            return False

        try:
            async with self._driver.session(database=self._database) as session:
                query = f"""
                MATCH (n:{entity_type} {{id: $entity_id}})
                DETACH DELETE n
                """
                await session.run(query, entity_id=entity_id)
                logger.debug(f"Deleted entity: {entity_type}:{entity_id}")
                return True
        except Exception as e:
            logger.error(f"Neo4j delete_entity failed: {e}")
            return False

    # =========================================================================
    # Spec v3.0 Required Methods - Entity Operations
    # =========================================================================

    async def upsert_entity(
        self,
        name: str,
        entity_type: str,
        attrs: dict[str, Any],
        workspace_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Upsert (create or update) an entity node.

        Spec: structural.entity_graph.upsert_entity

        Args:
            name: Entity name/identifier
            entity_type: Node label (e.g., 'User', 'Agent', 'Entity')
            attrs: Entity attributes to set
            workspace_id: Optional workspace for isolation

        Returns:
            Entity ID or None if failed
        """
        properties = {**attrs, "name": name}
        if workspace_id:
            properties["workspace_id"] = workspace_id

        return await self.create_entity(
            entity_type=entity_type,
            entity_id=name,
            properties=properties,
        )

    async def update_entity_attributes(
        self,
        name: str,
        entity_type: str,
        attrs: dict[str, Any],
    ) -> bool:
        """
        Update specific attributes on an existing entity (partial update).

        Spec: structural.entity_graph.update_entity_attributes

        Args:
            name: Entity name/identifier
            entity_type: Node label
            attrs: Attributes to update (merged with existing)

        Returns:
            True if updated, False if entity not found or failed
        """
        if not self.is_available():
            return False

        try:
            async with self._driver.session(database=self._database) as session:
                query = f"""
                MATCH (n:{entity_type} {{id: $entity_id}})
                SET n += $attrs
                RETURN n.id as id
                """
                result = await session.run(query, entity_id=name, attrs=attrs)
                record = await result.single()
                if record:
                    logger.debug(f"Updated entity attributes: {entity_type}:{name}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Neo4j update_entity_attributes failed: {e}")
            return False

    # =========================================================================
    # Relationship Operations
    # =========================================================================

    async def create_relationship(
        self,
        from_type: str,
        from_id: str,
        to_type: str,
        to_id: str,
        rel_type: str,
        properties: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Create a relationship between two entities.

        Args:
            from_type: Source node label
            from_id: Source entity ID
            to_type: Target node label
            to_id: Target entity ID
            rel_type: Relationship type (e.g., 'KNOWS', 'TRIGGERED', 'PART_OF')
            properties: Optional relationship properties

        Returns:
            True if created
        """
        if not self.is_available():
            return False

        try:
            async with self._driver.session(database=self._database) as session:
                props = properties or {}
                query = f"""
                MATCH (a:{from_type} {{id: $from_id}})
                MATCH (b:{to_type} {{id: $to_id}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += $properties
                RETURN type(r) as rel
                """
                result = await session.run(
                    query,
                    from_id=from_id,
                    to_id=to_id,
                    properties=props,
                )
                record = await result.single()
                if record:
                    logger.debug(
                        f"Created relationship: {from_type}:{from_id} -[{rel_type}]-> {to_type}:{to_id}"
                    )
                    return True
                return False
        except Exception as e:
            logger.error(f"Neo4j create_relationship failed: {e}")
            return False

    async def get_relationships(
        self,
        entity_type: str,
        entity_id: str,
        rel_type: Optional[str] = None,
        direction: str = "both",
    ) -> list[dict[str, Any]]:
        """
        Get relationships for an entity.

        Args:
            entity_type: Node label
            entity_id: Entity identifier
            rel_type: Optional filter by relationship type
            direction: 'outgoing', 'incoming', or 'both'

        Returns:
            List of relationships with connected nodes
        """
        if not self.is_available():
            return []

        try:
            async with self._driver.session(database=self._database) as session:
                rel_pattern = f":{rel_type}" if rel_type else ""

                if direction == "outgoing":
                    query = f"""
                    MATCH (n:{entity_type} {{id: $entity_id}})-[r{rel_pattern}]->(m)
                    RETURN type(r) as rel_type, properties(r) as rel_props, labels(m) as target_labels, m.id as target_id, properties(m) as target_props
                    """
                elif direction == "incoming":
                    query = f"""
                    MATCH (n:{entity_type} {{id: $entity_id}})<-[r{rel_pattern}]-(m)
                    RETURN type(r) as rel_type, properties(r) as rel_props, labels(m) as source_labels, m.id as source_id, properties(m) as source_props
                    """
                else:  # both
                    query = f"""
                    MATCH (n:{entity_type} {{id: $entity_id}})-[r{rel_pattern}]-(m)
                    RETURN type(r) as rel_type, properties(r) as rel_props, labels(m) as connected_labels, m.id as connected_id, properties(m) as connected_props
                    """

                result = await session.run(query, entity_id=entity_id)
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"Neo4j get_relationships failed: {e}")
            return []

    # =========================================================================
    # Spec v3.0 Required Methods - Relationship & Traversal
    # =========================================================================

    async def upsert_relationship(
        self,
        src: str,
        rel: str,
        tgt: str,
        confidence: float = 1.0,
        source_packet: Optional[str] = None,
    ) -> Optional[str]:
        """
        Upsert a relationship between two entities.

        Spec: structural.entity_graph.upsert_relationship

        Args:
            src: Source entity ID
            rel: Relationship type
            tgt: Target entity ID
            confidence: Confidence score for the relationship
            source_packet: Optional source packet UUID

        Returns:
            Relationship type if created, None if failed
        """
        properties = {"confidence": confidence}
        if source_packet:
            properties["source_packet"] = source_packet

        # Use create_relationship which already uses MERGE
        success = await self.create_relationship(
            from_type="Entity",
            from_id=src,
            to_type="Entity",
            to_id=tgt,
            rel_type=rel,
            properties=properties,
        )
        return rel if success else None

    async def traverse(
        self,
        source: str,
        depth: int = 2,
        relationship_types: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        Traverse graph from source entity to specified depth.

        Spec: structural.relationship_traversal.traverse

        Args:
            source: Starting entity ID
            depth: Maximum traversal depth (default 2)
            relationship_types: Optional filter by relationship types

        Returns:
            List of edges (source, rel_type, target, depth)
        """
        if not self.is_available():
            return []

        try:
            async with self._driver.session(database=self._database) as session:
                rel_filter = ""
                if relationship_types:
                    rel_filter = ":" + "|".join(relationship_types)

                query = f"""
                MATCH path = (start {{id: $source}})-[r{rel_filter}*1..{depth}]-(end)
                UNWIND relationships(path) as rel
                WITH startNode(rel) as src, rel, endNode(rel) as tgt, length(path) as d
                RETURN DISTINCT src.id as source_id, type(rel) as rel_type, 
                       tgt.id as target_id, properties(rel) as rel_props, d as depth
                ORDER BY d
                """
                result = await session.run(query, source=source)
                records = await result.data()
                logger.debug(f"Traversed {len(records)} edges from {source}")
                return records
        except Exception as e:
            logger.error(f"Neo4j traverse failed: {e}")
            return []

    async def find_path(
        self,
        source: str,
        target: str,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find shortest path between two entities.

        Spec: structural.relationship_traversal.find_path

        Args:
            source: Source entity ID
            target: Target entity ID
            max_depth: Maximum path length

        Returns:
            List of path segments [{source, rel_type, target}, ...]
        """
        if not self.is_available():
            return []

        try:
            async with self._driver.session(database=self._database) as session:
                query = f"""
                MATCH path = shortestPath((start {{id: $source}})-[*1..{max_depth}]-(end {{id: $target}}))
                UNWIND relationships(path) as rel
                RETURN startNode(rel).id as source_id, type(rel) as rel_type, 
                       endNode(rel).id as target_id, properties(rel) as rel_props
                """
                result = await session.run(query, source=source, target=target)
                records = await result.data()
                logger.debug(f"Found path with {len(records)} segments from {source} to {target}")
                return records
        except Exception as e:
            logger.error(f"Neo4j find_path failed: {e}")
            return []

    async def get_neighbors(
        self,
        entity: str,
        direction: str = "both",
    ) -> list[dict[str, Any]]:
        """
        Get immediate neighbors (adjacent nodes) of an entity.

        Spec: structural.relationship_traversal.get_neighbors

        Args:
            entity: Entity ID
            direction: 'outgoing', 'incoming', or 'both'

        Returns:
            List of neighbor entities with relationship info
        """
        if not self.is_available():
            return []

        try:
            async with self._driver.session(database=self._database) as session:
                if direction == "outgoing":
                    pattern = "(n {id: $entity})-[r]->(m)"
                elif direction == "incoming":
                    pattern = "(n {id: $entity})<-[r]-(m)"
                else:
                    pattern = "(n {id: $entity})-[r]-(m)"

                query = f"""
                MATCH {pattern}
                RETURN m.id as neighbor_id, labels(m) as labels, 
                       type(r) as rel_type, properties(m) as props
                """
                result = await session.run(query, entity=entity)
                records = await result.data()
                logger.debug(f"Found {len(records)} neighbors for {entity}")
                return records
        except Exception as e:
            logger.error(f"Neo4j get_neighbors failed: {e}")
            return []

    # =========================================================================
    # Event Timeline Operations
    # =========================================================================

    async def create_event(
        self,
        event_id: str,
        event_type: str,
        timestamp: str,
        properties: dict[str, Any],
        parent_event_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create an event in the timeline.

        Args:
            event_id: Unique event identifier
            event_type: Event type (e.g., 'user_action', 'agent_response')
            timestamp: ISO timestamp
            properties: Event properties
            parent_event_id: Optional parent event for causality chain

        Returns:
            Event ID or None
        """
        if not self.is_available():
            return None

        try:
            async with self._driver.session(database=self._database) as session:
                # Create the event
                props = {**properties, "event_type": event_type, "timestamp": timestamp}
                query = """
                MERGE (e:Event {id: $event_id})
                SET e += $properties
                RETURN e.id as id
                """
                result = await session.run(query, event_id=event_id, properties=props)
                await result.single()

                # Link to parent if provided
                if parent_event_id:
                    link_query = """
                    MATCH (parent:Event {id: $parent_id})
                    MATCH (child:Event {id: $child_id})
                    MERGE (parent)-[:TRIGGERED]->(child)
                    """
                    await session.run(
                        link_query,
                        parent_id=parent_event_id,
                        child_id=event_id,
                    )

                logger.debug(f"Created event: {event_type}:{event_id}")
                return event_id
        except Exception as e:
            logger.error(f"Neo4j create_event failed: {e}")
            return None

    async def get_event_timeline(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get events in time range.

        Args:
            start_time: ISO timestamp start (optional)
            end_time: ISO timestamp end (optional)
            event_type: Filter by event type (optional)
            limit: Maximum events to return

        Returns:
            List of events ordered by timestamp
        """
        if not self.is_available():
            return []

        try:
            async with self._driver.session(database=self._database) as session:
                conditions = []
                params: dict[str, Any] = {"limit": limit}

                if start_time:
                    conditions.append("e.timestamp >= $start_time")
                    params["start_time"] = start_time
                if end_time:
                    conditions.append("e.timestamp <= $end_time")
                    params["end_time"] = end_time
                if event_type:
                    conditions.append("e.event_type = $event_type")
                    params["event_type"] = event_type

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                query = f"""
                MATCH (e:Event)
                {where_clause}
                RETURN e
                ORDER BY e.timestamp DESC
                LIMIT $limit
                """

                result = await session.run(query, **params)
                records = await result.data()
                return [dict(r["e"]) for r in records]
        except Exception as e:
            logger.error(f"Neo4j get_event_timeline failed: {e}")
            return []

    # =========================================================================
    # Spec v3.0 Required Methods - Event Timeline
    # =========================================================================

    async def get_temporal_events(
        self,
        entity: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Get events related to an entity within a time range.

        Spec: structural.event_timeline.get_temporal_events

        Args:
            entity: Entity ID to get events for
            start: ISO timestamp start (optional)
            end: ISO timestamp end (optional)

        Returns:
            List of events related to the entity
        """
        if not self.is_available():
            return []

        try:
            async with self._driver.session(database=self._database) as session:
                conditions = ["(e)-[]-(n {id: $entity})"]
                params: dict[str, Any] = {"entity": entity}

                if start:
                    conditions.append("e.timestamp >= $start")
                    params["start"] = start
                if end:
                    conditions.append("e.timestamp <= $end")
                    params["end"] = end

                where_clause = "WHERE " + " AND ".join(conditions)

                query = f"""
                MATCH (e:Event), (n)
                {where_clause}
                RETURN e
                ORDER BY e.timestamp ASC
                """
                result = await session.run(query, **params)
                records = await result.data()
                logger.debug(f"Found {len(records)} temporal events for {entity}")
                return [dict(r["e"]) for r in records]
        except Exception as e:
            logger.error(f"Neo4j get_temporal_events failed: {e}")
            return []

    async def get_event_sequence(
        self,
        entity: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get ordered sequence of events for an entity.

        Spec: structural.event_timeline.get_event_sequence

        Args:
            entity: Entity ID
            limit: Maximum events to return

        Returns:
            List of events ordered by timestamp (oldest first)
        """
        if not self.is_available():
            return []

        try:
            async with self._driver.session(database=self._database) as session:
                query = """
                MATCH (e:Event)-[]-(n {id: $entity})
                RETURN e
                ORDER BY e.timestamp ASC
                LIMIT $limit
                """
                result = await session.run(query, entity=entity, limit=limit)
                records = await result.data()
                logger.debug(f"Found {len(records)} events in sequence for {entity}")
                return [dict(r["e"]) for r in records]
        except Exception as e:
            logger.error(f"Neo4j get_event_sequence failed: {e}")
            return []

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def run_query(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Run a custom Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            Query results as list of dicts
        """
        if not self.is_available():
            return []

        try:
            async with self._driver.session(database=self._database) as session:
                result = await session.run(query, **(parameters or {}))
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"Neo4j run_query failed: {e}")
            return []


# =============================================================================
# Singleton Factory
# =============================================================================

_neo4j_client: Optional[Neo4jClient] = None


async def get_neo4j_client() -> Optional[Neo4jClient]:
    """
    Get or create singleton Neo4j client.

    Returns:
        Neo4jClient instance or None if unavailable
    """
    global _neo4j_client

    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
        await _neo4j_client.connect()

    return _neo4j_client if _neo4j_client.is_available() else None


async def close_neo4j_client() -> None:
    """Close singleton Neo4j client."""
    global _neo4j_client
    if _neo4j_client:
        await _neo4j_client.disconnect()
        _neo4j_client = None


__all__ = ["Neo4jClient", "get_neo4j_client", "close_neo4j_client"]
