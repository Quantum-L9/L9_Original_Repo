#!/usr/bin/env python3
"""
Test All Database Layers - Redis, PostgreSQL, Neo4j
=====================================================

Comprehensive test suite for all three L9 memory stack layers.

Usage:
    # Run all tests
    pytest mcp_memory/tests/test_all_layers.py -v

    # Run specific layer
    pytest mcp_memory/tests/test_all_layers.py -v -k "redis"
    pytest mcp_memory/tests/test_all_layers.py -v -k "postgres"
    pytest mcp_memory/tests/test_all_layers.py -v -k "neo4j"

    # Run as standalone script (quick connection check)
    python mcp_memory/tests/test_all_layers.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
import structlog

# Add project root to path for imports
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

logger = structlog.get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# PostgreSQL
POSTGRES_DSN = os.getenv(
    "MEMORY_DSN",
    os.getenv("DATABASE_URL", "postgresql://postgres@127.0.0.1:5432/l9_memory"),
)

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Neo4j
NEO4J_URI = os.getenv("NEO4J_URL", os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687"))
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")


# =============================================================================
# LAYER 1: Redis Tests
# =============================================================================


class TestRedisLayer:
    """Tests for Redis connection and operations."""

    @pytest.fixture
    async def redis_client(self):
        """Create Redis client for testing."""
        try:
            from runtime.redis_client import RedisClient
        except ImportError:
            pytest.skip("redis_client module not available")

        client = RedisClient(host=REDIS_HOST, port=REDIS_PORT)
        connected = await client.connect()
        if not connected:
            pytest.skip("Redis not available")
        yield client
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_redis_connection(self, redis_client):
        """Test basic Redis connection."""
        assert redis_client.is_available(), "Redis should be available"

    @pytest.mark.asyncio
    async def test_redis_set_get(self, redis_client):
        """Test Redis set/get operations."""
        test_key = f"test:all_layers:{uuid.uuid4()}"
        test_value = f"test_value_{datetime.now().isoformat()}"

        # Set value
        result = await redis_client.set(test_key, test_value, ttl=60)
        assert result is True, "Set should return True"

        # Get value
        retrieved = await redis_client.get(test_key)
        assert retrieved == test_value, f"Expected {test_value}, got {retrieved}"

        # Cleanup
        await redis_client.delete(test_key)

    @pytest.mark.asyncio
    async def test_redis_rate_limiting(self, redis_client):
        """Test Redis rate limiting operations."""
        rate_key = f"rate_limit:test:{uuid.uuid4()}"

        # Increment
        count1 = await redis_client.increment_rate_limit(rate_key, ttl=60)
        assert count1 == 1, "First increment should be 1"

        count2 = await redis_client.increment_rate_limit(rate_key, ttl=60)
        assert count2 == 2, "Second increment should be 2"

        # Get current
        current = await redis_client.get_rate_limit(rate_key)
        assert current == 2, "Current should be 2"

        # Cleanup
        await redis_client.delete(rate_key)

    @pytest.mark.asyncio
    async def test_redis_task_queue(self, redis_client):
        """Test Redis task queue operations."""
        queue_name = f"test_queue:{uuid.uuid4()}"
        task_data = {
            "action": "test_action",
            "payload": {"key": "value"},
            "timestamp": datetime.now().isoformat(),
        }

        # Enqueue
        task_id = await redis_client.enqueue_task(queue_name, task_data, priority=5)
        assert task_id is not None, "Should return task ID"

        # Check queue size
        size = await redis_client.queue_size(queue_name)
        assert size == 1, f"Queue size should be 1, got {size}"

        # Dequeue
        dequeued = await redis_client.dequeue_task(queue_name)
        assert dequeued is not None, "Should dequeue task"
        assert dequeued["action"] == "test_action"

        # Queue should be empty
        size = await redis_client.queue_size(queue_name)
        assert size == 0, "Queue should be empty"


# =============================================================================
# LAYER 2: PostgreSQL Tests
# =============================================================================


class TestPostgresLayer:
    """Tests for PostgreSQL connection and operations."""

    @pytest.fixture
    async def pg_pool(self):
        """Create PostgreSQL connection pool for testing."""
        try:
            import asyncpg
        except ImportError:
            pytest.skip("asyncpg not available")

        try:
            pool = await asyncpg.create_pool(
                dsn=POSTGRES_DSN,
                min_size=1,
                max_size=5,
                command_timeout=30,
            )
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")

        yield pool
        await pool.close()

    @pytest.mark.asyncio
    async def test_postgres_connection(self, pg_pool):
        """Test basic PostgreSQL connection."""
        async with pg_pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1, "PostgreSQL should return 1"

    @pytest.mark.asyncio
    async def test_postgres_version(self, pg_pool):
        """Test PostgreSQL version."""
        async with pg_pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            assert "PostgreSQL" in version, f"Expected PostgreSQL, got {version}"
            logger.info("postgres_version", version=version[:60])

    @pytest.mark.asyncio
    async def test_pgvector_extension(self, pg_pool):
        """Test pgvector extension is installed."""
        async with pg_pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            assert result is True, "pgvector extension should be installed"

    @pytest.mark.asyncio
    async def test_postgres_packet_store_table(self, pg_pool):
        """Test packet_store table exists and has correct schema."""
        async with pg_pool.acquire() as conn:
            # Check table exists
            exists = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'packet_store'
                )
            """)
            assert exists is True, "packet_store table should exist"

            # Check key columns
            columns = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'packet_store'
                ORDER BY ordinal_position
            """)
            column_names = [c["column_name"] for c in columns]

            # Required columns in L9 packet_store schema
            required = ["packet_id", "envelope", "timestamp", "scope", "tenant_id"]
            for col in required:
                assert col in column_names, f"Column {col} should exist"

    @pytest.mark.asyncio
    async def test_postgres_memory_embeddings_table(self, pg_pool):
        """Test memory_embeddings table for vector search."""
        async with pg_pool.acquire() as conn:
            exists = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'memory_embeddings'
                )
            """)
            assert exists is True, "memory_embeddings table should exist"

            # Check for vector column (L9 uses 'vector' not 'embedding')
            has_vector = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'memory_embeddings'
                    AND column_name = 'vector'
                )
            """)
            assert has_vector is True, "vector column should exist"

            # Check RLS columns
            required_cols = ["tenant_id", "org_id", "user_id", "packet_id"]
            for col in required_cols:
                has_col = await conn.fetchval(
                    """
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'memory_embeddings'
                        AND column_name = $1
                    )
                """,
                    col,
                )
                assert has_col is True, f"{col} column should exist"

    @pytest.mark.asyncio
    async def test_postgres_vector_search(self, pg_pool):
        """Test vector similarity search capability."""
        async with pg_pool.acquire() as conn:
            # Check we can create a test vector and compute cosine distance
            result = await conn.fetchval("""
                SELECT 1 - (ARRAY[1,0,0]::vector(3) <=> ARRAY[1,0,0]::vector(3)) as similarity
            """)
            # Same vector should have similarity of 1.0
            assert abs(result - 1.0) < 0.001, (
                f"Same vector similarity should be 1.0, got {result}"
            )


# =============================================================================
# LAYER 3: Neo4j Tests
# =============================================================================


class TestNeo4jLayer:
    """Tests for Neo4j connection and operations."""

    @pytest.fixture
    async def neo4j_client(self):
        """Create Neo4j client for testing."""
        try:
            from memory.graph_client import Neo4jClient
        except ImportError:
            pytest.skip("graph_client module not available")

        if not NEO4J_PASSWORD:
            pytest.skip("NEO4J_PASSWORD not set")

        client = Neo4jClient(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)
        connected = await client.connect()
        if not connected:
            pytest.skip("Neo4j not available")

        yield client
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_neo4j_connection(self, neo4j_client):
        """Test basic Neo4j connection."""
        assert neo4j_client.is_available(), "Neo4j should be available"

    @pytest.mark.asyncio
    async def test_neo4j_simple_query(self, neo4j_client):
        """Test simple Cypher query."""
        result = await neo4j_client.run_query("RETURN 1 as n")
        assert len(result) == 1, "Should return one result"
        assert result[0]["n"] == 1, "Should return 1"

    @pytest.mark.asyncio
    async def test_neo4j_create_and_query_node(self, neo4j_client):
        """Test creating and querying a test node."""
        test_id = str(uuid.uuid4())

        # Create test node
        await neo4j_client.run_query(
            """
            CREATE (t:TestNode {test_id: $test_id, created_at: datetime()})
            """,
            {"test_id": test_id},
        )

        # Query the node
        result = await neo4j_client.run_query(
            "MATCH (t:TestNode {test_id: $test_id}) RETURN t.test_id as id",
            {"test_id": test_id},
        )
        assert len(result) == 1, "Should find the test node"
        assert result[0]["id"] == test_id

        # Cleanup
        await neo4j_client.run_query(
            "MATCH (t:TestNode {test_id: $test_id}) DELETE t", {"test_id": test_id}
        )

    @pytest.mark.asyncio
    async def test_neo4j_relationship(self, neo4j_client):
        """Test creating and querying relationships."""
        test_id = str(uuid.uuid4())

        # Create two nodes with a relationship
        await neo4j_client.run_query(
            """
            CREATE (a:TestNodeA {test_id: $test_id})
            CREATE (b:TestNodeB {test_id: $test_id})
            CREATE (a)-[:TEST_REL {test_id: $test_id}]->(b)
            """,
            {"test_id": test_id},
        )

        # Query the relationship
        result = await neo4j_client.run_query(
            """
            MATCH (a:TestNodeA {test_id: $test_id})-[r:TEST_REL]->(b:TestNodeB)
            RETURN type(r) as rel_type
            """,
            {"test_id": test_id},
        )
        assert len(result) == 1, "Should find the relationship"
        assert result[0]["rel_type"] == "TEST_REL"

        # Cleanup
        await neo4j_client.run_query(
            """
            MATCH (a:TestNodeA {test_id: $test_id})-[r:TEST_REL]->(b:TestNodeB {test_id: $test_id})
            DELETE r, a, b
            """,
            {"test_id": test_id},
        )

    @pytest.mark.asyncio
    async def test_neo4j_labels(self, neo4j_client):
        """Test that Neo4j can list labels (for introspection)."""
        result = await neo4j_client.run_query("CALL db.labels()")
        # Just verify the query works - labels list may be empty
        assert isinstance(result, list), "Should return a list"


# =============================================================================
# Integration Tests (All Layers)
# =============================================================================


class TestAllLayersIntegration:
    """Integration tests that span multiple layers."""

    @pytest.mark.asyncio
    async def test_all_layers_available(self):
        """Test that all three layers are available."""
        results = {"redis": False, "postgres": False, "neo4j": False}
        errors = {}

        # Test Redis
        try:
            from runtime.redis_client import RedisClient

            client = RedisClient(host=REDIS_HOST, port=REDIS_PORT)
            results["redis"] = await client.connect()
            await client.disconnect()
        except Exception as e:
            errors["redis"] = str(e)

        # Test PostgreSQL
        try:
            import asyncpg

            pool = await asyncpg.create_pool(dsn=POSTGRES_DSN, min_size=1, max_size=2)
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            results["postgres"] = True
            await pool.close()
        except Exception as e:
            errors["postgres"] = str(e)

        # Test Neo4j
        try:
            from memory.graph_client import Neo4jClient

            if NEO4J_PASSWORD:
                client = Neo4jClient(
                    uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD
                )
                results["neo4j"] = await client.connect()
                await client.disconnect()
            else:
                errors["neo4j"] = "NEO4J_PASSWORD not set"
        except Exception as e:
            errors["neo4j"] = str(e)

        # Log results
        logger.info("layer_availability", results=results, errors=errors)

        # At minimum, Postgres should be available (it's required)
        assert results["postgres"], f"PostgreSQL must be available. Errors: {errors}"

        # Report on optional layers
        if not results["redis"]:
            logger.warning("redis_unavailable", error=errors.get("redis"))
        if not results["neo4j"]:
            logger.warning("neo4j_unavailable", error=errors.get("neo4j"))


# =============================================================================
# Standalone Connection Check (Quick Health Check)
# =============================================================================


async def check_all_connections() -> dict[str, Any]:
    """Quick health check for all database layers."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "redis": {"available": False, "error": None},
        "postgres": {"available": False, "error": None, "version": None},
        "neo4j": {"available": False, "error": None},
    }

    # Check Redis
    print("\n🔴 Checking Redis...")
    try:
        from runtime.redis_client import RedisClient

        client = RedisClient(host=REDIS_HOST, port=REDIS_PORT)
        connected = await client.connect()
        if connected:
            results["redis"]["available"] = True
            print(f"   ✅ Redis: Connected ({REDIS_HOST}:{REDIS_PORT})")
        else:
            results["redis"]["error"] = "Connection failed"
            print("   ❌ Redis: Connection failed")
        await client.disconnect()
    except Exception as e:
        results["redis"]["error"] = str(e)
        print(f"   ❌ Redis: {e}")

    # Check PostgreSQL
    print("\n🐘 Checking PostgreSQL...")
    try:
        import asyncpg

        pool = await asyncpg.create_pool(
            dsn=POSTGRES_DSN, min_size=1, max_size=2, command_timeout=10
        )
        async with pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            vector_ok = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
        results["postgres"]["available"] = True
        results["postgres"]["version"] = version[:50] + "..."
        results["postgres"]["pgvector"] = vector_ok
        await pool.close()
        print("   ✅ PostgreSQL: Connected")
        print(f"      Version: {version[:50]}...")
        print(f"      pgvector: {'✅ Installed' if vector_ok else '❌ Not installed'}")
    except Exception as e:
        results["postgres"]["error"] = str(e)
        print(f"   ❌ PostgreSQL: {e}")

    # Check Neo4j
    print("\n🔵 Checking Neo4j...")
    try:
        from memory.graph_client import Neo4jClient

        if not NEO4J_PASSWORD:
            results["neo4j"]["error"] = "NEO4J_PASSWORD not set"
            print("   ⚠️  Neo4j: NEO4J_PASSWORD not set (skipped)")
        else:
            client = Neo4jClient(
                uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD
            )
            connected = await client.connect()
            if connected:
                results["neo4j"]["available"] = True
                print(f"   ✅ Neo4j: Connected ({NEO4J_URI})")
            else:
                results["neo4j"]["error"] = "Connection failed"
                print("   ❌ Neo4j: Connection failed")
            await client.disconnect()
    except Exception as e:
        results["neo4j"]["error"] = str(e)
        print(f"   ❌ Neo4j: {e}")

    # Summary
    print("\n" + "=" * 50)
    available = sum(
        1 for k in ["redis", "postgres", "neo4j"] if results[k]["available"]
    )
    print(f"📊 Summary: {available}/3 layers available")

    if results["postgres"]["available"]:
        print("   ✅ PostgreSQL (required) - OK")
    else:
        print("   ❌ PostgreSQL (required) - FAILED")

    if results["redis"]["available"]:
        print("   ✅ Redis (optional) - OK")
    else:
        print("   ⚠️  Redis (optional) - Not available")

    if results["neo4j"]["available"]:
        print("   ✅ Neo4j (optional) - OK")
    else:
        print("   ⚠️  Neo4j (optional) - Not available")

    print("=" * 50)

    return results


# =============================================================================
# Main (Standalone Execution)
# =============================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("L9 Memory Stack - All Layers Connection Test")
    print("=" * 50)
    print("\nConfiguration:")
    print(f"  PostgreSQL: {POSTGRES_DSN[:50]}...")
    print(f"  Redis:      {REDIS_HOST}:{REDIS_PORT}")
    print(f"  Neo4j:      {NEO4J_URI}")
    print(f"  Neo4j User: {NEO4J_USER}")
    print(f"  Neo4j Pass: {'[SET]' if NEO4J_PASSWORD else '[NOT SET]'}")

    results = asyncio.run(check_all_connections())

    # Exit with appropriate code
    if not results["postgres"]["available"]:
        print("\n❌ CRITICAL: PostgreSQL is required but not available!")
        sys.exit(1)

    sys.exit(0)
