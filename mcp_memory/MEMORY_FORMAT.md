# Memory Format

## Write

```bash
python3 agents/cursor/cursor_memory_client.py write "CONTENT" --kind KIND
```

| Arg | Required | Default |
|-----|----------|---------|
| `content` | Yes | - |
| `--kind` | No | `fact` |
| `--scope` | No | `developer` |

**Kinds:** `fact`, `insight`, `lesson`, `milestone`, `preference`, `pattern`  
**Scopes:** `developer`, `l-private`, `global`

### Response

```json
{
  "packet_id": "uuid",
  "kind": "fact",
  "written_tables": ["packet_store", "agent_memory_events", "reasoning_traces", "semantic_memory", "knowledge_facts", "graph_checkpoints"],
  "ingest_time_ms": 1804
}
```

## Search

```bash
python3 agents/cursor/cursor_memory_client.py search "QUERY" --limit 10
```

### Response

```json
{
  "results": [{"id": "uuid", "content": "...", "similarity": 0.92, "kind": "fact"}],
  "total": 1
}
```

## Graph Query

```bash
curl -X POST "https://157.180.73.53:9001/mcp/call" \
  -H "Authorization: Bearer $MCP_API_KEY_C" \
  -d '{"tool_name": "graph_query", "arguments": {"query": "MATCH (n) RETURN n LIMIT 5"}}'
```

## MCP Tools

| Tool | Args |
|------|------|
| `save_memory` | `content`, `kind`, `scope` |
| `search_memory` | `query`, `limit` |
| `graph_query` | `query` (Cypher) |
| `graph_get_entity` | `type`, `id` |
