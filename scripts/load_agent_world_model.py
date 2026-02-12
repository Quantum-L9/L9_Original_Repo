#!/usr/bin/env python3
"""
Load Agent World Model into Neo4j
=================================

Loads the agent_world_model.yaml seed file into Neo4j graph database.

Creates:
- Entity nodes (Human, Agent, Repository, Server)
- Relationship edges (REPORTS_TO, OWNS, MAINTAINS, etc.)
- Tool capability bindings
- SOPs, Directives, Responsibilities

Usage:
    python scripts/load_agent_world_model.py

Environment:
    NEO4J_URI: Neo4j connection URI (default: bolt://46.62.243.82:30687)
    NEO4J_USER: Neo4j username (default: neo4j)
    NEO4J_PASSWORD: Neo4j password (required)
"""

import asyncio
import os
import sys
from pathlib import Path

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import AsyncGraphDatabase

# Neo4j connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://46.62.243.82:30687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

SEED_FILE = Path(__file__).parent.parent / "config" / "seeds" / "agent_world_model.yaml"


async def load_seed_data():
    """Load seed YAML file."""
    if not SEED_FILE.exists():
        print(f"ERROR: Seed file not found: {SEED_FILE}")
        sys.exit(1)

    with open(SEED_FILE) as f:
        return yaml.safe_load(f)


async def create_entities(tx, entities: list):
    """Create entity nodes in Neo4j."""
    for entity in entities:
        entity_id = entity["id"]
        entity_type = entity["type"]
        name = entity["name"]
        properties = entity.get("properties", {})

        # Create node with dynamic label based on type
        query = f"""
        MERGE (e:{entity_type} {{id: $id}})
        SET e.name = $name
        SET e += $properties
        RETURN e
        """
        await tx.run(query, id=entity_id, name=name, properties=properties)
        print(f"  ✓ Created {entity_type}: {name} ({entity_id})")


async def create_relations(tx, relations: list):
    """Create relationship edges in Neo4j."""
    for rel in relations:
        from_id = rel["from"]
        to_id = rel["to"]
        rel_type = rel["type"]
        properties = rel.get("properties", {})

        # Create relationship (match by id, any label)
        query = f"""
        MATCH (from {{id: $from_id}})
        MATCH (to {{id: $to_id}})
        MERGE (from)-[r:{rel_type}]->(to)
        SET r += $properties
        RETURN r
        """
        result = await tx.run(
            query, from_id=from_id, to_id=to_id, properties=properties
        )
        record = await result.single()
        if record:
            print(f"  ✓ Created {from_id} -[{rel_type}]-> {to_id}")
        else:
            print(f"  ⚠ Could not create {from_id} -[{rel_type}]-> {to_id}")


async def create_tool_capabilities(tx, tool_caps: dict):
    """Create tool capability bindings."""
    for agent_id, caps in tool_caps.items():
        # High-risk tools
        for tool in caps.get("high_risk", []):
            query = """
            MATCH (a {id: $agent_id})
            MERGE (t:Tool {name: $tool_name})
            SET t.description = $description
            SET t.requires_approval = $requires_approval
            SET t.risk_level = 'HIGH'
            MERGE (a)-[r:CAN_EXECUTE]->(t)
            SET r.requires_approval = $requires_approval
            RETURN r
            """
            await tx.run(
                query,
                agent_id=agent_id,
                tool_name=tool["tool"],
                description=tool.get("description", ""),
                requires_approval=tool.get("requires_approval", True),
            )
            print(f"  ✓ {agent_id} CAN_EXECUTE {tool['tool']} (HIGH RISK)")

        # Standard tools
        for tool in caps.get("standard", []):
            query = """
            MATCH (a {id: $agent_id})
            MERGE (t:Tool {name: $tool_name})
            SET t.description = $description
            SET t.requires_approval = false
            SET t.risk_level = 'STANDARD'
            MERGE (a)-[r:CAN_EXECUTE]->(t)
            SET r.requires_approval = false
            RETURN r
            """
            await tx.run(
                query,
                agent_id=agent_id,
                tool_name=tool["tool"],
                description=tool.get("description", ""),
            )
            print(f"  ✓ {agent_id} CAN_EXECUTE {tool['tool']}")


async def create_sops(tx, sops: list):
    """Create SOP nodes and link to owners."""
    for sop in sops:
        query = """
        MERGE (s:SOP {id: $id})
        SET s.name = $name
        SET s.steps = $steps
        WITH s
        MATCH (a {id: $owner})
        MERGE (a)-[:HAS_SOP]->(s)
        RETURN s
        """
        await tx.run(
            query,
            id=sop["id"],
            name=sop["name"],
            steps=sop["steps"],
            owner=sop["owner"],
        )
        print(f"  ✓ Created SOP: {sop['name']}")


async def create_directives(tx, directives: list):
    """Create directive nodes."""
    for directive in directives:
        query = """
        MERGE (d:Directive {id: $id})
        SET d.priority = $priority
        SET d.rule = $rule
        SET d.enforced_by = $enforced_by
        RETURN d
        """
        await tx.run(
            query,
            id=directive["id"],
            priority=directive["priority"],
            rule=directive["rule"],
            enforced_by=directive["enforced_by"],
        )
        print(f"  ✓ Created Directive: {directive['id']} ({directive['priority']})")

    # Link directives to L-CTO
    query = """
    MATCH (a:Agent {id: 'l-cto'})
    MATCH (d:Directive)
    MERGE (a)-[:HAS_DIRECTIVE]->(d)
    """
    await tx.run(query)


async def create_responsibilities(tx, responsibilities: dict):
    """Create responsibility nodes and link to agents."""
    for agent_id, resps in responsibilities.items():
        for resp in resps:
            query = """
            MERGE (r:Responsibility {id: $id})
            SET r.name = $name
            SET r.description = $description
            SET r.scope = $scope
            WITH r
            MATCH (a {id: $agent_id})
            MERGE (a)-[:HAS_RESPONSIBILITY]->(r)
            RETURN r
            """
            await tx.run(
                query,
                id=resp["id"],
                name=resp["name"],
                description=resp["description"],
                scope=resp["scope"],
                agent_id=agent_id,
            )
            print(f"  ✓ Created Responsibility: {resp['name']}")


async def main():
    """Main entry point."""
    if not NEO4J_PASSWORD:
        print("ERROR: NEO4J_PASSWORD environment variable required")
        print("Usage: NEO4J_PASSWORD=xxx python scripts/load_agent_world_model.py")
        sys.exit(1)

    print("=" * 60)
    print("L9 Agent World Model Loader")
    print("=" * 60)
    print(f"Neo4j URI: {NEO4J_URI}")
    print(f"Seed file: {SEED_FILE}")
    print()

    # Load seed data
    print("Loading seed data...")
    data = await load_seed_data()
    print(f"  ✓ Loaded {len(data.get('entities', []))} entities")
    print(f"  ✓ Loaded {len(data.get('relations', []))} relations")
    print()

    # Connect to Neo4j
    print("Connecting to Neo4j...")
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        async with driver.session() as session:
            # Create entities
            print("\nCreating entities...")
            await session.execute_write(create_entities, data.get("entities", []))

            # Create relations
            print("\nCreating relations...")
            await session.execute_write(create_relations, data.get("relations", []))

            # Create tool capabilities
            if "tool_capabilities" in data:
                print("\nCreating tool capabilities...")
                await session.execute_write(
                    create_tool_capabilities, data["tool_capabilities"]
                )

            # Create SOPs
            if "sops" in data:
                print("\nCreating SOPs...")
                await session.execute_write(create_sops, data["sops"])

            # Create directives
            if "directives" in data:
                print("\nCreating directives...")
                await session.execute_write(create_directives, data["directives"])

            # Create responsibilities
            if "responsibilities" in data:
                print("\nCreating responsibilities...")
                await session.execute_write(
                    create_responsibilities, data["responsibilities"]
                )

        print("\n" + "=" * 60)
        print("✓ Agent World Model loaded successfully!")
        print("=" * 60)

        # Print summary query
        print("\nVerification queries:")
        print("  MATCH (n) RETURN labels(n)[0] as type, count(*) as count")
        print("  MATCH ()-[r]->() RETURN type(r) as type, count(*) as count")
        print("  MATCH (l:Agent {id: 'l-cto'})-[r]->(n) RETURN type(r), n.name")

    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
