"""PostgreSQL Substrate - Relational Persistence for World Model.

DDL Schema:
- entity_types (schema registry)
- entities (entity instances)
- relations (directed edges)
- entity_attributes (kv store per entity)

ACID compliance + NIST AI RMF Govern-2 (persistence governance).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Relational Persistence for World Model.",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T23:45:01Z",
    "updated_at": "2026-01-17T23:47:57Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "postgres_substrate",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from typing import List, Optional
from dataclasses import dataclass
import json
import logging

from world_model.interfaces import (
    Entity,
    Relation,
    EntityTypeSchema,
    RelationTypeSchema,
)
from world_model.state import WorldModelState


logger = logging.getLogger(__name__)


@dataclass
class PostgresConfig:
    """PostgreSQL connection config."""

    host: str = "localhost"
    port: int = 5432
    database: str = "world_model"
    user: str = "postgres"
    password: str = "postgres"
    pool_size: int = 10


class PostgresSubstrate:
    """PostgreSQL-backed persistence layer for World Model."""

    def __init__(self, config: Optional[PostgresConfig] = None):
        """Initialize PostgreSQL substrate.

        Args:
            config: PostgresConfig instance (default: localhost)
        """
        self.config = config or PostgresConfig()
        self._connection = None
        self._pool = None
        self.logger = logger

    # ========== CONNECTION MANAGEMENT ==========

    def connect(self) -> None:
        """Establish connection pool to PostgreSQL.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            import psycopg2
            from psycopg2 import pool

            self._pool = pool.SimpleConnectionPool(
                1,
                self.config.pool_size,
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
            )

            self._connection = self._pool.getconn()
            self.logger.info(
                f"Connected to PostgreSQL {self.config.host}:{self.config.port}/{self.config.database}"
            )

        except ImportError:
            raise ImportError("psycopg2 required for PostgreSQL substrate")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}")

    def disconnect(self) -> None:
        """Close all connections in pool."""
        if self._pool:
            try:
                self._pool.closeall()
                self.logger.info("Disconnected from PostgreSQL")
            except Exception as e:
                self.logger.error(f"Error closing PostgreSQL connection: {e}")

    def get_connection(self):
        """Get connection from pool."""
        if not self._pool:
            raise RuntimeError("Not connected to PostgreSQL")
        return self._pool.getconn()

    def return_connection(self, conn):
        """Return connection to pool."""
        if self._pool:
            self._pool.putconn(conn)

    # ========== SCHEMA SETUP ==========

    def create_schema(self) -> None:
        """Create all required tables.

        Idempotent: safe to call multiple times.
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            # Entity types registry
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_types (
                    type_name VARCHAR(255) PRIMARY KEY,
                    description TEXT,
                    properties JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Entities
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id VARCHAR(255) PRIMARY KEY,
                    type_name VARCHAR(255) NOT NULL REFERENCES entity_types(type_name),
                    attributes JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type_name)"
            )

            # Relation types registry
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relation_types (
                    type_name VARCHAR(255) PRIMARY KEY,
                    description TEXT,
                    properties JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Relations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relations (
                    id VARCHAR(255) PRIMARY KEY,
                    type_name VARCHAR(255) NOT NULL REFERENCES relation_types(type_name),
                    source_entity_id VARCHAR(255) NOT NULL REFERENCES entities(id),
                    target_entity_id VARCHAR(255) NOT NULL REFERENCES entities(id),
                    attributes JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_entity_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_entity_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(type_name)"
            )

            conn.commit()
            self.logger.info("Schema created successfully")

        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to create schema: {e}")
        finally:
            self.return_connection(conn)

    def drop_schema(self) -> None:
        """Drop all tables (DESTRUCTIVE)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            # Drop in dependency order
            cursor.execute("DROP TABLE IF EXISTS relations CASCADE")
            cursor.execute("DROP TABLE IF EXISTS relation_types CASCADE")
            cursor.execute("DROP TABLE IF EXISTS entities CASCADE")
            cursor.execute("DROP TABLE IF EXISTS entity_types CASCADE")

            conn.commit()
            self.logger.info("Schema dropped")

        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to drop schema: {e}")
        finally:
            self.return_connection(conn)

    # ========== REGISTRY PERSISTENCE ==========

    def store_entity_type(self, type_name: str, schema: EntityTypeSchema) -> None:
        """Store entity type schema.

        Args:
            type_name: Entity type name
            schema: EntityTypeSchema instance
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO entity_types (type_name, description, properties)
                VALUES (%s, %s, %s)
                ON CONFLICT (type_name) DO UPDATE
                SET description = EXCLUDED.description,
                    properties = EXCLUDED.properties,
                    updated_at = NOW()
            """,
                (
                    type_name,
                    schema.description,
                    json.dumps(
                        schema.properties if hasattr(schema, "properties") else {}
                    ),
                ),
            )

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to store entity type {type_name}: {e}")
        finally:
            self.return_connection(conn)

    def store_relation_type(self, type_name: str, schema: RelationTypeSchema) -> None:
        """Store relation type schema.

        Args:
            type_name: Relation type name
            schema: RelationTypeSchema instance
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO relation_types (type_name, description, properties)
                VALUES (%s, %s, %s)
                ON CONFLICT (type_name) DO UPDATE
                SET description = EXCLUDED.description,
                    properties = EXCLUDED.properties,
                    updated_at = NOW()
            """,
                (
                    type_name,
                    schema.description,
                    json.dumps(
                        schema.properties if hasattr(schema, "properties") else {}
                    ),
                ),
            )

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to store relation type {type_name}: {e}")
        finally:
            self.return_connection(conn)

    # ========== ENTITY PERSISTENCE ==========

    def store_entity(self, entity: Entity) -> None:
        """Store entity to database.

        Args:
            entity: Entity instance
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO entities (id, type_name, attributes)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET attributes = EXCLUDED.attributes,
                    updated_at = NOW()
            """,
                (
                    entity.id,
                    entity.type,
                    json.dumps(entity.attributes),
                ),
            )

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to store entity {entity.id}: {e}")
        finally:
            self.return_connection(conn)

    def load_entity(self, entity_id: str) -> Optional[Entity]:
        """Load entity from database.

        Args:
            entity_id: Entity ID

        Returns:
            Entity instance or None if not found
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, type_name, attributes
                FROM entities
                WHERE id = %s
            """,
                (entity_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return Entity(
                id=row[0],
                type=row[1],
                attributes=row[2] or {},
            )

        except Exception as e:
            self.logger.error(f"Failed to load entity {entity_id}: {e}")
            return None
        finally:
            self.return_connection(conn)

    def load_all_entities(self) -> List[Entity]:
        """Load all entities from database.

        Returns:
            List of Entity instances
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, type_name, attributes
                FROM entities
            """)

            entities = []
            for row in cursor.fetchall():
                entities.append(
                    Entity(
                        id=row[0],
                        type=row[1],
                        attributes=row[2] or {},
                    )
                )

            return entities

        except Exception as e:
            self.logger.error(f"Failed to load entities: {e}")
            return []
        finally:
            self.return_connection(conn)

    def delete_entity(self, entity_id: str) -> None:
        """Delete entity from database.

        Args:
            entity_id: Entity ID
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM entities WHERE id = %s", (entity_id,))

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to delete entity {entity_id}: {e}")
        finally:
            self.return_connection(conn)

    # ========== RELATION PERSISTENCE ==========

    def store_relation(self, relation: Relation) -> None:
        """Store relation to database.

        Args:
            relation: Relation instance
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO relations (id, type_name, source_entity_id, target_entity_id, attributes)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET attributes = EXCLUDED.attributes,
                    updated_at = NOW()
            """,
                (
                    relation.id,
                    relation.type,
                    relation.source_entity_id,
                    relation.target_entity_id,
                    json.dumps(relation.attributes),
                ),
            )

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to store relation {relation.id}: {e}")
        finally:
            self.return_connection(conn)

    def load_relation(self, relation_id: str) -> Optional[Relation]:
        """Load relation from database.

        Args:
            relation_id: Relation ID

        Returns:
            Relation instance or None if not found
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, type_name, source_entity_id, target_entity_id, attributes
                FROM relations
                WHERE id = %s
            """,
                (relation_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return Relation(
                id=row[0],
                type=row[1],
                source_entity_id=row[2],
                target_entity_id=row[3],
                attributes=row[4] or {},
            )

        except Exception as e:
            self.logger.error(f"Failed to load relation {relation_id}: {e}")
            return None
        finally:
            self.return_connection(conn)

    def load_all_relations(self) -> List[Relation]:
        """Load all relations from database.

        Returns:
            List of Relation instances
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, type_name, source_entity_id, target_entity_id, attributes
                FROM relations
            """)

            relations = []
            for row in cursor.fetchall():
                relations.append(
                    Relation(
                        id=row[0],
                        type=row[1],
                        source_entity_id=row[2],
                        target_entity_id=row[3],
                        attributes=row[4] or {},
                    )
                )

            return relations

        except Exception as e:
            self.logger.error(f"Failed to load relations: {e}")
            return []
        finally:
            self.return_connection(conn)

    def delete_relation(self, relation_id: str) -> None:
        """Delete relation from database.

        Args:
            relation_id: Relation ID
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM relations WHERE id = %s", (relation_id,))

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to delete relation {relation_id}: {e}")
        finally:
            self.return_connection(conn)

    # ========== STATE SYNC ==========

    def sync_state_to_db(self, state: WorldModelState) -> None:
        """Sync entire WorldModelState to database.

        Args:
            state: WorldModelState to persist
        """
        for entity in state.get_all_entities():
            self.store_entity(entity)

        for relation in state.get_all_relations():
            self.store_relation(relation)

        self.logger.info("State synced to PostgreSQL")

    def load_state_from_db(self) -> WorldModelState:
        """Load entire state from database.

        Returns:
            Reconstructed WorldModelState
        """
        state = WorldModelState()

        for entity in self.load_all_entities():
            state.add_entity(entity)

        for relation in self.load_all_relations():
            state.add_relation(relation)

        self.logger.info("State loaded from PostgreSQL")
        return state

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-019",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["dataclass", "learning", "serialization", "world-model"],
    "keywords": ["all", "compliance", "connect", "connection", "create", "delete", "disconnect", "drop"],
    "business_value": "Provides postgres substrate components including PostgresConfig, PostgresSubstrate",
    "last_modified": "2026-01-17T23:47:57Z",
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
