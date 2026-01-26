# MCP Memory - Quick Reference

**Updated:** 2026-01-16 | **Status:** Active

## CLI Commands

```bash
cd /Users/ib-mac/Projects/L9
python3 agents/cursor/cursor_memory_client.py health
python3 agents/cursor/cursor_memory_client.py write "content" --kind fact
python3 agents/cursor/cursor_memory_client.py search "query"
python3 agents/cursor/cursor_memory_client.py stats
```

**Kinds:** `fact`, `insight`, `lesson`, `milestone`, `preference`, `pattern`
**Scopes:** `developer` (shared), `l-private` (L only), `global`

## MCP Tools

| Tool                        | Purpose                |
| --------------------------- | ---------------------- |
| `save_memory`               | Store with embedding   |
| `search_memory`             | Semantic search        |
| `get_memory_stats`          | Statistics             |
| `graph_query`               | Neo4j Cypher queries   |
| `graph_get_entity`          | Get entity by type/ID  |
| `get_context_injection`     | Auto-context for tasks |
| `extract_session_learnings` | Extract patterns       |
| `query_temporal`            | Time-based queries     |

## Endpoints

| Endpoint     | Method |
| ------------ | ------ |
| `/health`    | GET    |
| `/mcp/tools` | GET    |
| `/mcp/call`  | POST   |

**URL:** `https://157.180.73.53:9001` or `https://l9.quantumaipartners.com:9001`

## Env Vars (Local .env)

```bash
L9_API_URL=https://157.180.73.53:9001
L9_EXECUTOR_API_KEY=<MCP_API_KEY_C from VPS>
```

## API Keys

| Key             | Caller | Permissions                |
| --------------- | ------ | -------------------------- |
| `MCP_API_KEY_L` | L-CTO  | Full access                |
| `MCP_API_KEY_C` | Cursor | Read all, write/delete own |

## Pipeline

Writes to 6 tables: `packet_store`, `agent_memory_events`, `reasoning_traces`, `semantic_memory`, `knowledge_facts`, `graph_checkpoints`

**Latency:** 650-1800ms

## Troubleshooting

**Governance error:** VPS needs rebuild: `docker-compose build --no-cache l9-api && docker-compose up -d`
**401 Unauthorized:** Check `L9_EXECUTOR_API_KEY` in local `.env`
**Logs:** `docker logs l9-api --tail 50`
