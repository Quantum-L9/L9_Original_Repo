# ADR-0082: Neo4j is Required, Not Optional

## Status

**ACCEPTED** — 2026-01-31

## Context

L9's architecture depends on Neo4j for:

1. **Tool Graph** — Tool relationships, dependencies, blast radius analysis
2. **Agent State** — Graph-backed agent state (directives, responsibilities, SOPs)
3. **Repo Indexes** — Class inheritance, imports, wiring relationships
4. **Knowledge Graph** — Entity relationships, causal graphs, world model

Without Neo4j, these capabilities are **completely unavailable**, not degraded:
- `tools_get_dependencies()` fails
- `tools_get_blast_radius()` fails
- Agent self-modify operations fail
- Repo index graph queries fail

## Decision

**Neo4j is a REQUIRED dependency, not optional.**

### Enforcement

1. **Startup Gate** — API server MUST verify Neo4j connectivity before accepting requests
2. **Environment Validation** — Scripts MUST fail fast if `NEO4J_URL` and `NEO4J_PASSWORD` not set
3. **Health Checks** — Neo4j health MUST be included in `/health` endpoint
4. **CI Pipeline** — Tests requiring Neo4j MUST run against real Neo4j (not mocked)

### Required Environment Variables

```bash
# C1 VPS (Production)
NEO4J_URL=bolt://46.62.243.82:30687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<secret>

# Local Docker
NEO4J_URL=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<secret>
```

### Services That REQUIRE Neo4j

| Service | Dependency | Failure Mode |
|---------|------------|--------------|
| Tool Registry | Tool graph queries | All tool introspection fails |
| Agent Bootstrap | Graph state loading | Agent init fails |
| `/index` Pipeline | Repo graph loading | Indexes not queryable |
| Memory Substrate | Knowledge graph | Relationship queries fail |
| World Model | Causal graph | Reasoning degraded |

## Consequences

### Positive

- Clear dependency contract
- No silent failures from missing Neo4j
- Consistent behavior across environments
- Tool graph features always available

### Negative

- Cannot run L9 without Neo4j instance
- Local development requires Docker or VPS connection
- Slightly higher infrastructure requirements

## Compliance

All code that uses Neo4j MUST:

1. Check `NEO4J_URL` at startup, fail if not set
2. NOT provide fallback/stub behavior
3. Log clearly if Neo4j connection fails
4. Be included in health check aggregation

## References

- `core/agents/graph_state/schema.py` — Graph state queries
- `core/tools/tool_graph.py` — Tool graph operations
- `scripts/memory/load_indexes_to_neo4j.py` — Index loading
- `ADR-0032` — Neo4j Cypher query patterns
