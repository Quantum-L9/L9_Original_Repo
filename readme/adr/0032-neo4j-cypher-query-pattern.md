# ADR 0032: Neo4j Cypher Query Pattern

## Status

Accepted

## Pattern

ALL Cypher queries parameterized; use templates from `cypher_templates.py`; never string interpolation.

## Files

- `memory/cypher_templates.py` - Query templates
- `memory/graph_client.py` - Neo4j client
- `scripts/memory/bootstrap_neo4j_schema.py` - Schema setup

## Import Block

```python
from neo4j import AsyncGraphDatabase
from memory.cypher_templates import (
    FIND_AGENT,
    CREATE_ENTITY,
    FIND_RELATED,
)
import structlog

logger = structlog.get_logger(__name__)
```

## Minimal Implementation

```python
# === memory/cypher_templates.py ===
"""
Cypher query templates for Neo4j.

ALL queries MUST be parameterized using $param syntax.
NEVER use string interpolation (f-strings, .format()).
"""

# Find agent by ID with tenant isolation
FIND_AGENT = """
MATCH (a:Agent {agent_id: $agent_id})
WHERE a.tenant_id = $tenant_id
RETURN a.name, a.capabilities, a.created_at
"""

# Create entity with properties
CREATE_ENTITY = """
MERGE (e:Entity {entity_id: $entity_id, tenant_id: $tenant_id})
ON CREATE SET
    e.name = $name,
    e.type = $entity_type,
    e.created_at = datetime()
ON MATCH SET
    e.updated_at = datetime()
RETURN e
"""

# Find related entities
FIND_RELATED = """
MATCH (e:Entity {entity_id: $entity_id})-[r:RELATES_TO]->(related)
WHERE e.tenant_id = $tenant_id
RETURN related.entity_id, related.name, type(r) as relation_type
LIMIT $limit
"""

# Create relationship between entities
CREATE_RELATION = """
MATCH (from:Entity {entity_id: $from_id, tenant_id: $tenant_id})
MATCH (to:Entity {entity_id: $to_id, tenant_id: $tenant_id})
MERGE (from)-[r:RELATES_TO {relation_type: $relation_type}]->(to)
SET r.created_at = datetime()
RETURN r
"""


# === memory/graph_client.py ===
from neo4j import AsyncGraphDatabase
from typing import Any
import structlog

logger = structlog.get_logger(__name__)

class GraphClient:
    """Neo4j client with parameterized queries."""

    def __init__(self, uri: str, user: str, password: str):
        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def run(
        self,
        query: str,
        **params: Any,
    ) -> list[dict]:
        """
        Execute parameterized Cypher query.

        Args:
            query: Cypher query with $param placeholders
            **params: Parameter values

        Returns:
            List of result records as dicts
        """
        async with self._driver.session() as session:
            result = await session.run(query, params)
            records = [record.data() async for record in result]

            logger.debug(
                "cypher.executed",
                query_preview=query[:50],
                param_count=len(params),
                result_count=len(records),
            )

            return records

    async def close(self):
        """Close driver connection."""
        await self._driver.close()
```

## Usage Example

```python
from memory.graph_client import GraphClient
from memory.cypher_templates import FIND_AGENT, CREATE_ENTITY, FIND_RELATED

# Initialize client
client = GraphClient(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password",
)

# Find agent (parameterized)
agents = await client.run(
    FIND_AGENT,
    agent_id="l-cto",
    tenant_id="73350468-3158-5d0f-9b8c-9b193d96fc4b",
)

# Create entity (parameterized)
result = await client.run(
    CREATE_ENTITY,
    entity_id="user-123",
    tenant_id=tenant_id,
    name="John Doe",
    entity_type="person",
)

# Find related entities (parameterized)
related = await client.run(
    FIND_RELATED,
    entity_id="user-123",
    tenant_id=tenant_id,
    limit=10,
)

# Close when done
await client.close()
```

## Anti-Pattern Example

```python
# ❌ WRONG — String interpolation (SQL/Cypher injection risk!)
agent_id = "l-cto"
query = f"MATCH (a:Agent {{agent_id: '{agent_id}'}}) RETURN a"
# Attacker could inject: '}}) DETACH DELETE n //

# ❌ WRONG — .format() interpolation
query = "MATCH (a:Agent {{agent_id: '{}'}}) RETURN a".format(agent_id)

# ❌ WRONG — Concatenation
query = "MATCH (a:Agent {agent_id: '" + agent_id + "'}) RETURN a"

# ❌ WRONG — No tenant_id filter
query = """
MATCH (a:Agent {agent_id: $agent_id})
RETURN a
"""  # Missing tenant isolation!

# ✅ CORRECT — Parameterized with tenant isolation
query = """
MATCH (a:Agent {agent_id: $agent_id})
WHERE a.tenant_id = $tenant_id
RETURN a.name, a.capabilities
"""
await client.run(query, agent_id=agent_id, tenant_id=tenant_id)
```

## Node Types

| Node   | Properties                    | Purpose              |
| ------ | ----------------------------- | -------------------- |
| Agent  | agent_id, tenant_id, name     | Agent entities       |
| Tool   | tool_id, name, category       | Tool definitions     |
| Entity | entity_id, type, tenant_id    | World model entities |
| Fact   | fact_id, subject, predicate   | Knowledge facts      |
| Memory | memory_id, content, tenant_id | Memory entries       |

## Relationship Types

| Relationship | From   | To     | Purpose          |
| ------------ | ------ | ------ | ---------------- |
| CAN_EXECUTE  | Agent  | Tool   | Tool permissions |
| KNOWS        | Agent  | Entity | Agent knowledge  |
| RELATES_TO   | Entity | Entity | Entity relations |
| DERIVED_FROM | Fact   | Memory | Fact provenance  |

## Rules

1. ALL queries MUST use `$param` syntax
2. Add queries to `cypher_templates.py`
3. Always filter by `tenant_id`
4. Use MERGE for idempotent creates
5. Return only needed properties

## AI Guidance

**DO:**

- Use `$parameter` syntax for all values
- Add new queries to `cypher_templates.py`
- Include `tenant_id` in WHERE clause
- Use MERGE for upserts

**DO NOT:**

- Use string interpolation (f-strings)
- Embed values directly in query
- Skip tenant_id filtering
- Return entire nodes (select properties)
