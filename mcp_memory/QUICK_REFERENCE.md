# MCP Memory - Quick Reference

**Updated:** 2026-02-13 | **Status:** Active

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

| Endpoint     | Method | Auth         |
| ------------ | ------ | ------------ |
| `/health`    | GET    | None         |
| `/mcp/tools` | GET    | Bearer token |
| `/mcp/call`  | POST   | Bearer token |

**URL:** `https://157.180.73.53:9001` or `https://l9.quantumaipartners.com`

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

Writes to 4 tables: `packet_store`, `memory_embeddings`, `knowledge_facts`, `reasoning_traces`

**Pipeline:** `main_dag`
**Latency:** 650-1800ms

## Troubleshooting

| Problem | Cause | Fix |
| ------- | ----- | --- |
| **502 Bad Gateway** | Caddy routing to wrong port | Check Caddyfile, ensure routes to `127.0.0.1:8000` |
| **401 Unauthorized** | Invalid/missing API key | Verify `L9_EXECUTOR_API_KEY` in local `.env` matches VPS `MCP_API_KEY_C` |
| **429 Rate Limit** | >60 req/min | Wait 60 seconds; check `docker compose logs l9-api \| grep rate` |
| **Auth blocked** | 5 failed auth attempts | Fix API key, wait 5 minutes for block to expire |
| **Search empty** | Embedding not indexed | Wait 2-5 seconds after save before searching |
| **Governance error** | VPS needs rebuild | `docker-compose build --no-cache l9-api && docker-compose up -d` |

## Source of Truth

`memory/MCP-MEMORY-CAPSULE.md` — full architecture, Caddy config, Neo4j posture, deployment protocol.
