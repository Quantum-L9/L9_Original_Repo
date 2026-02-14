# Memory Format

## Write

```bash
python3 agents/cursor/cursor_memory_client.py write "CONTENT" --kind KIND
```

| Arg       | Required | Default     |
| --------- | -------- | ----------- |
| `content` | Yes      | -           |
| `--kind`  | No       | `fact`      |
| `--scope` | No       | `developer` |

**Kinds:** `fact`, `insight`, `lesson`, `milestone`, `preference`, `pattern`
**Scopes:** `developer` (shared), `l-private` (L only), `global`

### Response

```json
{
  "packet_id": "uuid",
  "pipeline": "main_dag",
  "written_tables": [
    "packet_store",
    "memory_embeddings",
    "knowledge_facts",
    "reasoning_traces"
  ],
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
  "results": [
    { "id": "uuid", "content": "...", "similarity": 0.92, "kind": "fact" }
  ],
  "total": 1
}
```

## Graph Query

```bash
curl -ks -X POST "https://157.180.73.53:9001/mcp/call" \
  -H "Authorization: Bearer $MCP_API_KEY_C" \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "graph_query", "arguments": {"query": "MATCH (n) RETURN n LIMIT 5"}}'
```

## MCP Tools

| Tool                        | Args                       | Purpose                |
| --------------------------- | -------------------------- | ---------------------- |
| `save_memory`               | `content`, `kind`, `scope` | Store with embedding   |
| `search_memory`             | `query`, `limit`           | Semantic search        |
| `get_memory_stats`          | -                          | Statistics             |
| `graph_query`               | `query` (Cypher)           | Neo4j Cypher queries   |
| `graph_get_entity`          | `type`, `id`               | Get entity by type/ID  |
| `get_context_injection`     | `task`                     | Auto-context for tasks |
| `extract_session_learnings` | `session`                  | Extract patterns       |
| `query_temporal`            | `query`, `time_range`      | Time-based queries     |

## Governance

| Caller | API Key         | Read         | Write    | Delete   |
| ------ | --------------- | ------------ | -------- | -------- |
| **L**  | `MCP_API_KEY_L` | All memories | All      | All      |
| **C**  | `MCP_API_KEY_C` | All memories | Own only | Own only |
