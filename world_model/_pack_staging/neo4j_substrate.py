"""Neo4j Substrate - Graph-Native Query Engine for World Model.

Properties Graph Model:
- Nodes (entities) with labels + attributes
- Relationships (directed, typed, attributed)
- Cypher query support for advanced graph traversals

Performance: Optimized for relationship traversal (vs. relational SQL joins).
NIST AI RMF Map-2 (graph-native analytics).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Graph-Native Query Engine for World Model.",
    "module_version": "1.0.1",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T23:45:01Z",
    "updated_at": "2026-01-21T01:57:00Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "neo4j_substrate",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

from world_model.state import Entity, Relation, WorldModelState


logger = logging.getLogger(__name__)


@dataclass
class Neo4jConfig:
    """Neo4j connection config."""

    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"


class Neo4jSubstrate:
    """Neo4j graph-native persistence layer for World Model."""

    def __init__(self, config: Optional[Neo4jConfig] = None):
        """Initialize Neo4j substrate.

        Args:
            config: Neo4jConfig instance (default: localhost)
        """
        self.config = config or Neo4jConfig()
        self._driver = None
        self.logger = logger

    # ========== CONNECTION MANAGEMENT ==========

    def connect(self) -> None:
        """Establish connection to Neo4j.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.username, self.config.password),
            )

            # Test connection
            with self._driver.session(database=self.config.database) as session:
                session.run("RETURN 1")

            self.logger.info(f"Connected to Neo4j {self.config.uri}")

        except ImportError:
            raise ImportError("neo4j package required for Neo4j substrate")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Neo4j: {e}")

    def disconnect(self) -> None:
        """Close Neo4j driver."""
        if self._driver:
            try:
                self._driver.close()
                self.logger.info("Disconnected from Neo4j")
            except Exception as e:
                self.logger.error(f"Error closing Neo4j connection: {e}")

    # ========== SCHEMA SETUP ==========

    def create_schema(self) -> None:
        """Create Neo4j indexes and constraints.

        Idempotent: safe to call multiple times.
        """
        with self._driver.session(database=self.config.database) as session:
            try:
                # Unique constraint on entity ID
                session.run("""
                    CREATE CONSTRAINT IF NOT EXISTS
                    FOR (e:Entity)
                    REQUIRE e.id IS UNIQUE
                """)

                # Unique constraint on relation ID
                session.run("""
                    CREATE CONSTRAINT IF NOT EXISTS
                    FOR (r:Relation)
                    REQUIRE r.id IS UNIQUE
                """)

                # Indexes for type-based queries
                session.run("""
                    CREATE INDEX IF NOT EXISTS
                    FOR (e:Entity)
                    ON (e.type)
                """)

                session.run("""
                    CREATE INDEX IF NOT EXISTS
                    FOR (r:Relation)
                    ON (r.type)
                """)

                self.logger.info("Neo4j schema created")

            except Exception as e:
                self.logger.error(f"Failed to create Neo4j schema: {e}")
                raise

    def drop_schema(self) -> None:
        """Drop all data from Neo4j (DESTRUCTIVE)."""
        with self._driver.session(database=self.config.database) as session:
            try:
                session.run("MATCH (n) DETACH DELETE n")
                self.logger.info("Neo4j data dropped")
            except Exception as e:
                self.logger.error(f"Failed to drop Neo4j data: {e}")
                raise

    # ========== ENTITY OPERATIONS ==========

    def store_entity(self, entity: Entity) -> None:
        """Store entity to Neo4j.

        Args:
            entity: Entity instance
        """
        with self._driver.session(database=self.config.database) as session:
            try:
                # Create node with dynamic labels
                labels = f"Entity:{entity.type}"

                session.run(
                    f"""
                    MERGE (e:{labels} {{id: $id}})
                    SET e += $attributes
                """,
                    {
                        "id": entity.id,
                        "attributes": entity.attributes,
                    },
                )

                self.logger.debug(f"Stored entity {entity.id}")

            except Exception as e:
                self.logger.error(f"Failed to store entity {entity.id}: {e}")
                raise

    def load_entity(self, entity_id: str) -> Optional[Entity]:
        """Load entity from Neo4j.

        Args:
            entity_id: Entity ID

        Returns:
            Entity instance or None if not found
        """
        with self._driver.session(database=self.config.database) as session:
            try:
                result = session.run(
                    """
                    MATCH (e:Entity {id: $id})
                    RETURN e, labels(e) as labels
                """,
                    {"id": entity_id},
                )

                record = result.single()
                if not record:
                    return None

                node = record["e"]
                labels = record["labels"]

                # Extract type from labels (skip "Entity" label)
                entity_type = next((l for l in labels if l != "Entity"), None)

                return Entity(
                    id=node["id"],
                    type=entity_type,
                    attributes=dict(node),
                )

            except Exception as e:
                self.logger.error(f"Failed to load entity {entity_id}: {e}")
                return None

    def load_all_entities(self) -> List[Entity]:
        """Load all entities from Neo4j.

        Returns:
            List of Entity instances
        """
        with self._driver.session(database=self.config.database) as session:
            try:
                result = session.run("""
                    MATCH (e:Entity)
                    RETURN e, labels(e) as labels
                """)

                entities = []
                for record in result:
                    node = record["e"]
                    labels = record["labels"]
                    entity_type = next((l for l in labels if l != "Entity"), None)

                    entities.append(
                        Entity(
                            id=node["id"],
                            type=entity_type,
                            attributes=dict(node),
                        )
                    )

                return entities

            except Exception as e:
                self.logger.error(f"Failed to load entities: {e}")
                return []

    def delete_entity(self, entity_id: str) -> None:
        """Delete entity from Neo4j.

        Args:
            entity_id: Entity ID
        """
        with self._driver.session(database=self.config.database) as session:
            try:
                session.run(
                    """
                    MATCH (e:Entity {id: $id})
                    DETACH DELETE e
                """,
                    {"id": entity_id},
                )

                self.logger.debug(f"Deleted entity {entity_id}")

            except Exception as e:
                self.logger.error(f"Failed to delete entity {entity_id}: {e}")
                raise

    # ========== RELATION OPERATIONS ==========

    def store_relation(self, relation: Relation) -> None:
        """Store relation to Neo4j.

        Args:
            relation: Relation instance
        """
        with self._driver.session(database=self.config.database) as session:
            try:
                # Create relationship between entities
                rel_type = relation.type.upper().replace("-", "_")

                session.run(
                    f"""
                    MATCH (source:Entity {{id: $source_id}})
                    MATCH (target:Entity {{id: $target_id}})
                    MERGE (source)-[r:{rel_type} {{id: $rel_id}}]->(target)
                    SET r += $attributes
                """,
                    {
                        "source_id": relation.source_entity_id,
                        "target_id": relation.target_entity_id,
                        "rel_id": relation.id,
                        "attributes": relation.attributes,
                    },
                )

                self.logger.debug(f"Stored relation {relation.id}")

            except Exception as e:
                self.logger.error(f"Failed to store relation {relation.id}: {e}")
                raise

    def load_relation(self, relation_id: str) -> Optional[Relation]:
        """Load relation from Neo4j.

        Args:
            relation_id: Relation ID

        Returns:
            Relation instance or None if not found
        """
        with self._driver.session(database=self.config.database) as session:
            try:
                result = session.run(
                    """
                    MATCH (source)-[r {id: $id}]->(target)
                    RETURN r, type(r) as rel_type, 
                           source.id as source_id, target.id as target_id
                """,
                    {"id": relation_id},
                )

                record = result.single()
                if not record:
                    return None

                rel = record["r"]

                return Relation(
                    id=rel["id"],
                    type=record["rel_type"],
                    source_entity_id=record["source_id"],
                    target_entity_id=record["target_id"],
                    attributes=dict(rel),
                )

            except Exception as e:
                self.logger.error(f"Failed to load relation {relation_id}: {e}")
                return None

    def load_all_relations(self) -> List[Relation]:
        """Load all relations from Neo4j.

        Returns:
            List of Relation instances
        """
        with self._driver.session(database=self.config.database) as session:
            try:
                result = session.run("""
                    MATCH (source)-[r]->(target)
                    RETURN r, type(r) as rel_type,
                           source.id as source_id, target.id as target_id
                """)

                relations = []
                for record in result:
                    rel = record["r"]
                    relations.append(
                        Relation(
                            id=rel["id"],
                            type=record["rel_type"],
                            source_entity_id=record["source_id"],
                            target_entity_id=record["target_id"],
                            attributes=dict(rel),
                        )
                    )

                return relations

            except Exception as e:
                self.logger.error(f"Failed to load relations: {e}")
                return []

    def delete_relation(self, relation_id: str) -> None:
        """Delete relation from Neo4j.

        Args:
            relation_id: Relation ID
        """
        with self._driver.session(database=self.config.database) as session:
            try:
                session.run(
                    """
                    MATCH ()-[r {id: $id}]->()
                    DELETE r
                """,
                    {"id": relation_id},
                )

                self.logger.debug(f"Deleted relation {relation_id}")

            except Exception as e:
                self.logger.error(f"Failed to delete relation {relation_id}: {e}")
                raise

    # ========== CYPHER QUERIES ==========

    def execute_cypher(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute arbitrary Cypher query.

        Args:
            query: Cypher query string
            params: Query parameters (optional)

        Returns:
            List of result records as dicts
        """
        with self._driver.session(database=self.config.database) as session:
            try:
                result = session.run(query, params or {})
                return [dict(record) for record in result]

            except Exception as e:
                self.logger.error(f"Cypher query failed: {e}")
                raise

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        relation_type: Optional[str] = None,
        max_length: int = 5,
    ) -> List[List[str]]:
        """Find paths between entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relation_type: Filter by relation type (optional)
            max_length: Maximum path length

        Returns:
            List of entity ID paths
        """
        rel_filter = f":{relation_type}" if relation_type else ""

        query = f"""
            MATCH paths = (source:Entity {{id: $source_id}})-[{rel_filter}*..{max_length}]->
                          (target:Entity {{id: $target_id}})
            RETURN [node.id IN nodes(path) | node.id] as path
            ORDER BY LENGTH(path)
        """

        results = self.execute_cypher(
            query,
            {
                "source_id": source_id,
                "target_id": target_id,
            },
        )

        return [record["path"] for record in results]

    def find_neighbors(
        self, entity_id: str, relation_type: Optional[str] = None
    ) -> List[str]:
        """Find neighbor entities.

        Args:
            entity_id: Starting entity ID
            relation_type: Filter by relation type (optional)

        Returns:
            List of neighbor entity IDs
        """
        rel_filter = f":{relation_type}" if relation_type else ""

        query = f"""
            MATCH (e:Entity {{id: $id}})-[{rel_filter}]->(neighbor)
            RETURN DISTINCT neighbor.id as id
        """

        results = self.execute_cypher(query, {"id": entity_id})
        return [record["id"] for record in results]

    # ========== STATE SYNC ==========

    def sync_state_to_db(self, state: WorldModelState) -> None:
        """Sync entire WorldModelState to Neo4j.

        Args:
            state: WorldModelState to persist
        """
        for entity in state.get_all_entities():
            self.store_entity(entity)

        for relation in state.get_all_relations():
            self.store_relation(relation)

        self.logger.info("State synced to Neo4j")

    def load_state_from_db(self) -> WorldModelState:
        """Load entire state from Neo4j.

        Returns:
            Reconstructed WorldModelState
        """
        state = WorldModelState()

        for entity in self.load_all_entities():
            state.add_entity(entity)

        for relation in self.load_all_relations():
            state.add_relation(relation)

        self.logger.info("State loaded from Neo4j")
        return state


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-025",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "auth",
        "dataclass",
        "debugging",
        "graph-db",
        "learning",
        "testing",
        "world-model",
    ],
    "keywords": [
        "all",
        "connect",
        "create",
        "cypher",
        "delete",
        "disconnect",
        "drop",
        "engine",
    ],
    "business_value": "Provides neo4j substrate components including Neo4jConfig, Neo4jSubstrate",
    "last_modified": "2026-01-21T01:57:00Z",
    "modified_by": "L9_GMP_Phase2",
    "change_summary": "Fixed import: world_model.interfaces -> world_model.state",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
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
