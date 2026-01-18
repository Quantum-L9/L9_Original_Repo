"""
L9 Memory - Dynamic Schema Introspection
=========================================

Enables agents to "discover" database schemas at runtime.
No code changes needed when schema evolves.

Provides introspection tools for:
- PostgreSQL (information_schema, pg_catalog)
- Neo4j (db.labels, db.relationshipTypes, apoc.meta.schema)

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Dynamic Schema Introspection",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-12T21:19:05Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "schema_introspection",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL"],
        "memory_layers": [],
        "imported_by": ["memory.__init__"],
    },
}
# ============================================================================

import structlog
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# Schema Models
# =============================================================================


@dataclass
class ColumnInfo:
    """Information about a database column."""

    name: str
    data_type: str
    is_nullable: bool
    column_default: Optional[str] = None
    character_maximum_length: Optional[int] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False


@dataclass
class TableInfo:
    """Information about a database table."""

    schema_name: str
    table_name: str
    table_type: str  # 'BASE TABLE', 'VIEW'
    columns: list[ColumnInfo]
    row_count_estimate: Optional[int] = None


@dataclass
class IndexInfo:
    """Information about a database index."""

    index_name: str
    table_name: str
    column_names: list[str]
    is_unique: bool
    is_primary: bool


@dataclass
class Neo4jLabelInfo:
    """Information about a Neo4j node label."""

    label: str
    properties: list[str]
    property_types: dict[str, str]  # property -> type
    node_count: int


@dataclass
class Neo4jRelationshipInfo:
    """Information about a Neo4j relationship type."""

    relationship_type: str
    properties: list[str]
    start_labels: list[str]
    end_labels: list[str]
    count: int


@dataclass
class SchemaSnapshot:
    """Complete schema snapshot."""

    # PostgreSQL
    tables: list[TableInfo]
    indexes: list[IndexInfo]

    # Neo4j
    labels: list[Neo4jLabelInfo]
    relationship_types: list[Neo4jRelationshipInfo]

    # Metadata
    captured_at: datetime
    postgres_version: Optional[str] = None
    neo4j_version: Optional[str] = None


# =============================================================================
# PostgreSQL Introspector
# =============================================================================


class PostgresIntrospector:
    """
    Introspects PostgreSQL database schema.

    Uses information_schema and pg_catalog for discovery.
    """

    def __init__(self, pool: Any):  # asyncpg.Pool
        """
        Initialize with connection pool.

        Args:
            pool: asyncpg connection pool
        """
        self._pool = pool

    async def get_tables(
        self,
        schema_name: str = "public",
        include_views: bool = False,
    ) -> list[TableInfo]:
        """
        Get all tables in a schema.

        Args:
            schema_name: Schema to inspect (default: public)
            include_views: Include views in results

        Returns:
            List of TableInfo
        """
        table_types = ["BASE TABLE"]
        if include_views:
            table_types.append("VIEW")

        type_filter = ", ".join(f"'{t}'" for t in table_types)

        async with self._pool.acquire() as conn:
            # Get tables
            tables_query = f"""
                SELECT table_schema, table_name, table_type
                FROM information_schema.tables
                WHERE table_schema = $1
                AND table_type IN ({type_filter})
                ORDER BY table_name
            """
            table_rows = await conn.fetch(tables_query, schema_name)

            results = []
            for row in table_rows:
                # Get columns for this table
                columns = await self._get_columns(conn, schema_name, row["table_name"])

                # Get row count estimate
                count_query = """
                    SELECT reltuples::bigint as estimate
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = $1 AND n.nspname = $2
                """
                count_row = await conn.fetchrow(
                    count_query, row["table_name"], schema_name
                )
                row_count = count_row["estimate"] if count_row else None

                results.append(
                    TableInfo(
                        schema_name=row["table_schema"],
                        table_name=row["table_name"],
                        table_type=row["table_type"],
                        columns=columns,
                        row_count_estimate=row_count,
                    )
                )

            logger.debug(f"Found {len(results)} tables in schema {schema_name}")
            return results

    async def _get_columns(
        self,
        conn: Any,
        schema_name: str,
        table_name: str,
    ) -> list[ColumnInfo]:
        """Get columns for a table."""
        query = """
            SELECT 
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                c.character_maximum_length,
                CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key,
                CASE WHEN fk.column_name IS NOT NULL THEN true ELSE false END as is_foreign_key
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT ku.column_name, ku.table_name, ku.table_schema
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku 
                    ON tc.constraint_name = ku.constraint_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
            ) pk ON pk.column_name = c.column_name 
                AND pk.table_name = c.table_name 
                AND pk.table_schema = c.table_schema
            LEFT JOIN (
                SELECT ku.column_name, ku.table_name, ku.table_schema
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku 
                    ON tc.constraint_name = ku.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
            ) fk ON fk.column_name = c.column_name 
                AND fk.table_name = c.table_name 
                AND fk.table_schema = c.table_schema
            WHERE c.table_schema = $1 AND c.table_name = $2
            ORDER BY c.ordinal_position
        """
        rows = await conn.fetch(query, schema_name, table_name)

        return [
            ColumnInfo(
                name=row["column_name"],
                data_type=row["data_type"],
                is_nullable=row["is_nullable"] == "YES",
                column_default=row["column_default"],
                character_maximum_length=row["character_maximum_length"],
                is_primary_key=row["is_primary_key"],
                is_foreign_key=row["is_foreign_key"],
            )
            for row in rows
        ]

    async def get_indexes(self, schema_name: str = "public") -> list[IndexInfo]:
        """
        Get all indexes in a schema.

        Args:
            schema_name: Schema to inspect

        Returns:
            List of IndexInfo
        """
        async with self._pool.acquire() as conn:
            query = """
                SELECT 
                    i.relname as index_name,
                    t.relname as table_name,
                    array_agg(a.attname ORDER BY x.ordinality) as column_names,
                    ix.indisunique as is_unique,
                    ix.indisprimary as is_primary
                FROM pg_index ix
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_class t ON t.oid = ix.indrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                CROSS JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY as x(attnum, ordinality)
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = x.attnum
                WHERE n.nspname = $1
                GROUP BY i.relname, t.relname, ix.indisunique, ix.indisprimary
                ORDER BY t.relname, i.relname
            """
            rows = await conn.fetch(query, schema_name)

            return [
                IndexInfo(
                    index_name=row["index_name"],
                    table_name=row["table_name"],
                    column_names=row["column_names"],
                    is_unique=row["is_unique"],
                    is_primary=row["is_primary"],
                )
                for row in rows
            ]

    async def get_version(self) -> str:
        """Get PostgreSQL version."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT version()")
            return row["version"] if row else "unknown"

    async def get_schema_summary(self, schema_name: str = "public") -> dict[str, Any]:
        """
        Get a summary of the schema for LLM context.

        Returns a condensed representation suitable for injection into prompts.
        """
        tables = await self.get_tables(schema_name)

        summary = {
            "schema": schema_name,
            "tables": [],
        }

        for table in tables:
            table_summary = {
                "name": table.table_name,
                "type": table.table_type,
                "columns": [
                    {
                        "name": col.name,
                        "type": col.data_type,
                        "pk": col.is_primary_key,
                    }
                    for col in table.columns
                ],
                "row_count": table.row_count_estimate,
            }
            summary["tables"].append(table_summary)

        return summary


# =============================================================================
# Neo4j Introspector
# =============================================================================


class Neo4jIntrospector:
    """
    Introspects Neo4j graph schema.

    Uses db.labels(), db.relationshipTypes(), and APOC if available.
    """

    def __init__(self, neo4j_client: Any):  # Neo4jClient from memory.graph_client
        """
        Initialize with Neo4j client.

        Args:
            neo4j_client: Neo4jClient instance
        """
        self._client = neo4j_client

    async def get_labels(self) -> list[Neo4jLabelInfo]:
        """
        Get all node labels with property information.

        Returns:
            List of Neo4jLabelInfo
        """
        if not self._client.is_available():
            logger.warning("Neo4j not available for schema introspection")
            return []

        # Get all labels
        labels_result = await self._client.run_query(
            "CALL db.labels() YIELD label RETURN label"
        )

        results = []
        for row in labels_result:
            label = row["label"]

            # Get property info for this label (sample first 100 nodes)
            prop_query = f"""
                MATCH (n:`{label}`)
                WITH n LIMIT 100
                UNWIND keys(n) as key
                RETURN DISTINCT key as property, 
                       head(collect(DISTINCT apoc.meta.cypher.type(n[key]))) as type
            """

            try:
                prop_result = await self._client.run_query(prop_query)
                properties = [r["property"] for r in prop_result]
                property_types = {
                    r["property"]: r["type"] or "unknown" for r in prop_result
                }
            except Exception:
                # Fallback if APOC not available
                prop_query_fallback = f"""
                    MATCH (n:`{label}`)
                    WITH n LIMIT 100
                    UNWIND keys(n) as key
                    RETURN DISTINCT key as property
                """
                prop_result = await self._client.run_query(prop_query_fallback)
                properties = [r["property"] for r in prop_result]
                property_types = {p: "unknown" for p in properties}

            # Get node count
            count_result = await self._client.run_query(
                f"MATCH (n:`{label}`) RETURN count(n) as count"
            )
            node_count = count_result[0]["count"] if count_result else 0

            results.append(
                Neo4jLabelInfo(
                    label=label,
                    properties=properties,
                    property_types=property_types,
                    node_count=node_count,
                )
            )

        logger.debug(f"Found {len(results)} Neo4j labels")
        return results

    async def get_relationship_types(self) -> list[Neo4jRelationshipInfo]:
        """
        Get all relationship types with endpoint information.

        Returns:
            List of Neo4jRelationshipInfo
        """
        if not self._client.is_available():
            return []

        # Get all relationship types
        rel_result = await self._client.run_query(
            "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        )

        results = []
        for row in rel_result:
            rel_type = row["relationshipType"]

            # Get endpoint labels and properties
            detail_query = f"""
                MATCH (a)-[r:`{rel_type}`]->(b)
                WITH labels(a) as start_labels, labels(b) as end_labels, keys(r) as props
                LIMIT 100
                RETURN 
                    collect(DISTINCT start_labels[0]) as start_labels,
                    collect(DISTINCT end_labels[0]) as end_labels,
                    collect(DISTINCT props) as all_props
            """
            detail_result = await self._client.run_query(detail_query)

            if detail_result:
                detail = detail_result[0]
                start_labels = detail.get("start_labels", [])
                end_labels = detail.get("end_labels", [])
                # Flatten property lists
                all_props = detail.get("all_props", [[]])
                properties = list(set(p for props in all_props for p in props))
            else:
                start_labels = []
                end_labels = []
                properties = []

            # Get count
            count_result = await self._client.run_query(
                f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) as count"
            )
            count = count_result[0]["count"] if count_result else 0

            results.append(
                Neo4jRelationshipInfo(
                    relationship_type=rel_type,
                    properties=properties,
                    start_labels=start_labels,
                    end_labels=end_labels,
                    count=count,
                )
            )

        logger.debug(f"Found {len(results)} Neo4j relationship types")
        return results

    async def get_version(self) -> str:
        """Get Neo4j version."""
        if not self._client.is_available():
            return "unavailable"

        result = await self._client.run_query(
            "CALL dbms.components() YIELD name, versions RETURN name, versions[0] as version"
        )
        if result:
            return result[0].get("version", "unknown")
        return "unknown"

    async def get_schema_summary(self) -> dict[str, Any]:
        """
        Get a summary of the graph schema for LLM context.

        Returns a condensed representation suitable for injection into prompts.
        """
        labels = await self.get_labels()
        rel_types = await self.get_relationship_types()

        return {
            "labels": [
                {
                    "name": label.label,
                    "properties": label.properties[:10],  # Limit for context window
                    "node_count": label.node_count,
                }
                for label in labels
            ],
            "relationships": [
                {
                    "type": rel.relationship_type,
                    "from": rel.start_labels[:3],
                    "to": rel.end_labels[:3],
                    "count": rel.count,
                }
                for rel in rel_types
            ],
        }


# =============================================================================
# Unified Schema Introspector
# =============================================================================


class SchemaIntrospector:
    """
    Unified schema introspector for both PostgreSQL and Neo4j.

    Provides a single interface for agents to discover database structure.

    Usage:
        introspector = SchemaIntrospector(postgres_pool, neo4j_client)

        # Get full schema snapshot
        snapshot = await introspector.get_snapshot()

        # Get LLM-friendly summary
        summary = await introspector.get_summary_for_context()
    """

    def __init__(
        self,
        postgres_pool: Optional[Any] = None,
        neo4j_client: Optional[Any] = None,
    ):
        """
        Initialize with database connections.

        Args:
            postgres_pool: asyncpg pool (optional)
            neo4j_client: Neo4jClient (optional)
        """
        self._postgres = PostgresIntrospector(postgres_pool) if postgres_pool else None
        self._neo4j = Neo4jIntrospector(neo4j_client) if neo4j_client else None

        logger.info(
            "SchemaIntrospector initialized",
            postgres=self._postgres is not None,
            neo4j=self._neo4j is not None,
        )

    async def get_snapshot(self, schema_name: str = "public") -> SchemaSnapshot:
        """
        Get complete schema snapshot from both databases.

        Args:
            schema_name: PostgreSQL schema to inspect

        Returns:
            SchemaSnapshot with all schema information
        """
        # PostgreSQL
        tables: list[TableInfo] = []
        indexes: list[IndexInfo] = []
        postgres_version = None

        if self._postgres:
            try:
                tables = await self._postgres.get_tables(schema_name)
                indexes = await self._postgres.get_indexes(schema_name)
                postgres_version = await self._postgres.get_version()
            except Exception as e:
                logger.warning(f"PostgreSQL introspection failed: {e}")

        # Neo4j
        labels: list[Neo4jLabelInfo] = []
        rel_types: list[Neo4jRelationshipInfo] = []
        neo4j_version = None

        if self._neo4j:
            try:
                labels = await self._neo4j.get_labels()
                rel_types = await self._neo4j.get_relationship_types()
                neo4j_version = await self._neo4j.get_version()
            except Exception as e:
                logger.warning(f"Neo4j introspection failed: {e}")

        return SchemaSnapshot(
            tables=tables,
            indexes=indexes,
            labels=labels,
            relationship_types=rel_types,
            captured_at=datetime.utcnow(),
            postgres_version=postgres_version,
            neo4j_version=neo4j_version,
        )

    async def get_summary_for_context(
        self, schema_name: str = "public"
    ) -> dict[str, Any]:
        """
        Get condensed schema summary suitable for LLM context injection.

        This produces a token-efficient summary that agents can use to
        understand available data without loading full schemas.

        Args:
            schema_name: PostgreSQL schema

        Returns:
            Dict with postgres and neo4j summaries
        """
        summary = {
            "captured_at": datetime.utcnow().isoformat(),
            "postgres": None,
            "neo4j": None,
        }

        if self._postgres:
            try:
                summary["postgres"] = await self._postgres.get_schema_summary(
                    schema_name
                )
            except Exception as e:
                summary["postgres"] = {"error": str(e)}

        if self._neo4j:
            try:
                summary["neo4j"] = await self._neo4j.get_schema_summary()
            except Exception as e:
                summary["neo4j"] = {"error": str(e)}

        return summary

    async def get_postgres_tables(self, schema_name: str = "public") -> list[str]:
        """Get list of table names (convenience method)."""
        if not self._postgres:
            return []
        tables = await self._postgres.get_tables(schema_name)
        return [t.table_name for t in tables]

    async def get_neo4j_labels(self) -> list[str]:
        """Get list of node labels (convenience method)."""
        if not self._neo4j:
            return []
        labels = await self._neo4j.get_labels()
        return [lbl.label for lbl in labels]

    async def get_neo4j_relationship_types(self) -> list[str]:
        """Get list of relationship types (convenience method)."""
        if not self._neo4j:
            return []
        rels = await self._neo4j.get_relationship_types()
        return [r.relationship_type for r in rels]


# =============================================================================
# Singleton Factory
# =============================================================================


_introspector: Optional[SchemaIntrospector] = None


@must_stay_async("callers use await")
async def get_schema_introspector(
    postgres_pool: Optional[Any] = None,
    neo4j_client: Optional[Any] = None,
) -> SchemaIntrospector:
    """
    Get or create singleton schema introspector.

    Args:
        postgres_pool: asyncpg pool (uses existing if already set)
        neo4j_client: Neo4jClient (uses existing if already set)

    Returns:
        SchemaIntrospector instance
    """
    global _introspector

    if _introspector is None:
        _introspector = SchemaIntrospector(postgres_pool, neo4j_client)

    return _introspector


__all__ = [
    "ColumnInfo",
    "TableInfo",
    "IndexInfo",
    "Neo4jLabelInfo",
    "Neo4jRelationshipInfo",
    "SchemaSnapshot",
    "PostgresIntrospector",
    "Neo4jIntrospector",
    "SchemaIntrospector",
    "get_schema_introspector",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-016",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["async", "dataclass", "debugging", "learning", "logging", "memory-substrate"],
    "keywords": ["column", "dynamic", "index", "indexes", "introspection", "introspector", "label", "labels"],
    "business_value": "PostgreSQL (information_schema, pg_catalog) Neo4j (db.labels, db.relationshipTypes, apoc.meta.schema) Version: 1.0.0",
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
