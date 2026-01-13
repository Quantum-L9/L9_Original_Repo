# L9 Memory System - Agent Usage Guide

**Purpose:** Reference guide for AI agents (Cursor, L-CTO) on how to use the L9 Memory Substrate API.

**Last Updated:** 2026-01-05

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [Saving Memories](#saving-memories)
4. [Searching Memories](#searching-memories)
5. [Querying Facts & Insights](#querying-facts--insights)
6. [Common Patterns](#common-patterns)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)

---

## Quick Start

### Base URL
- **Local:** `http://127.0.0.1:8000/api/v1/memory`
- **VPS (HTTPS):** `https://l9.quantumaipartners.com:9001/api/v1/memory`
- **VPS (Local):** `http://127.0.0.1:8000/api/v1/memory`

### Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer <L9_EXECUTOR_API_KEY>
```

---

## Authentication

### Getting the API Key

**On VPS:**
```bash
ssh root@157.180.73.53 "cd /opt/l9 && grep L9_EXECUTOR_API_KEY .env"
```

**In Code:**
```python
import os
api_key = os.environ.get("L9_EXECUTOR_API_KEY")
```

### Header Format
```bash
-H "Authorization: Bearer <api_key>"
```

---

## Saving Memories

### Endpoint
```
POST /api/v1/memory/packet
```

### Request Format

```json
{
  "packet_type": "memory.<category>",
  "payload": {
    "content": "The actual memory content",
    "kind": "milestone|lesson|pattern|decision|preference"
  },
  "metadata": {
    "source": "cursor-ide|l-cto|slack",
    "creator": "Agent identifier",
    "domain": "l9"
  },
  "tags": ["tag1", "tag2"],
  "thread_id": "optional-uuid-string",
  "ttl": 86400
}
```

### Common Packet Types

| Type | Use Case |
|------|----------|
| `memory.milestone` | Important achievements, first-time events |
| `memory.lesson` | Lessons learned, mistakes to avoid |
| `memory.pattern` | Code patterns, architectural decisions |
| `memory.preference` | User preferences, style choices |
| `memory.decision` | Strategic decisions, trade-offs |
| `memory.error` | Error patterns and fixes |

### Example: Save a Milestone

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/memory/packet" \
  -H "Authorization: Bearer $L9_EXECUTOR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "packet_type": "memory.milestone",
    "payload": {
      "content": "today'\''s the first day mcp server memory works",
      "kind": "milestone"
    },
    "metadata": {
      "source": "cursor-ide",
      "creator": "Cursor-IDE"
    },
    "tags": ["mcp", "milestone", "first-day"]
  }'
```

### Response Format

```json
{
  "packet_id": "cff80210-2e42-4d1d-8ee3-8c875bbd53e8",
  "status": "ok",
  "written_tables": [
    "packet_store",
    "agent_memory_events",
    "reasoning_traces",
    "semantic_memory",
    "knowledge_facts",
    "graph_checkpoints"
  ],
  "error_message": null
}
```

### Important Notes

1. **`confidence` field:** If provided, must be a **dict** with `score` and `rationale`, NOT a number:
   ```json
   "confidence": {
     "score": 0.95,
     "rationale": "High confidence based on successful test"
   }
   ```
   Or omit it entirely (defaults to None).

2. **All fields are optional except:**
   - `packet_type` (required)
   - `payload` (required)

3. **Automatic Processing:** The packet goes through the full DAG pipeline:
   - Validation
   - Storage in `packet_store`
   - Semantic embedding generation
   - Graph sync (Neo4j)
   - Fact extraction
   - Reasoning trace creation

---

## Searching Memories

### Semantic Search

**Endpoint:** `POST /api/v1/memory/semantic/search`

**Request:**
```json
{
  "query": "search query text",
  "top_k": 5,
  "min_score": 0.5,
  "agent_id": "optional-agent-filter"
}
```

**Example:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/memory/semantic/search" \
  -H "Authorization: Bearer $L9_EXECUTOR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "first day mcp server memory works",
    "top_k": 5
  }'
```

**Response:**
```json
{
  "query": "first day mcp server memory works",
  "hits": [
    {
      "packet_id": "...",
      "content": "...",
      "score": 0.92,
      "metadata": {...}
    }
  ]
}
```

**Note:** Embeddings may take a few seconds to index. If search returns empty immediately after saving, wait 2-5 seconds and retry.

### Hybrid Search

**Endpoint:** `POST /api/v1/memory/hybrid/search?query=<text>&top_k=<n>&min_score=<0.0-1.0>`

**Request:** Query params + JSON body for filters

**Example:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/memory/hybrid/search?query=mcp%20memory&top_k=10&min_score=0.7" \
  -H "Authorization: Bearer $L9_EXECUTOR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "packet_type": "memory.milestone",
    "tags": ["mcp"]
  }'
```

---

## Querying Facts & Insights

### Get Facts

**Endpoint:** `GET /api/v1/memory/facts?subject=<subject>&predicate=<predicate>&limit=<n>`

**Example:**
```bash
curl "http://127.0.0.1:8000/api/v1/memory/facts?subject=memory&limit=10" \
  -H "Authorization: Bearer $L9_EXECUTOR_API_KEY"
```

### Get Insights

**Endpoint:** `GET /api/v1/memory/insights?packet_id=<uuid>&insight_type=<type>&limit=<n>`

**Example:**
```bash
curl "http://127.0.0.1:8000/api/v1/memory/insights?packet_id=cff80210-2e42-4d1d-8ee3-8c875bbd53e8" \
  -H "Authorization: Bearer $L9_EXECUTOR_API_KEY"
```

### Get Stats

**Endpoint:** `GET /api/v1/memory/stats`

**Example:**
```bash
curl "http://127.0.0.1:8000/api/v1/memory/stats" \
  -H "Authorization: Bearer $L9_EXECUTOR_API_KEY"
```

**Response:**
```json
{
  "status": "operational",
  "packets": 1234,
  "embeddings": 1200,
  "facts": 567,
  "health": {...}
}
```

---

## Common Patterns

### Pattern 1: Save a Lesson Learned

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/memory/packet" \
  -H "Authorization: Bearer $L9_EXECUTOR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "packet_type": "memory.lesson",
    "payload": {
      "content": "Always use $HOME instead of hardcoded /Users/ib-mac paths",
      "kind": "lesson",
      "context": "Path handling in scripts",
      "fix": "Use Path.home() or os.path.expanduser(\"~\")"
    },
    "metadata": {
      "source": "cursor-ide",
      "creator": "Cursor-IDE",
      "workspace": "L9"
    },
    "tags": ["lesson", "paths", "portability"]
  }'
```

### Pattern 2: Save a Code Pattern

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/memory/packet" \
  -H "Authorization: Bearer $L9_EXECUTOR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "packet_type": "memory.pattern",
    "payload": {
      "content": "Use search_replace for surgical edits, never rewrite entire files",
      "kind": "pattern",
      "pattern_type": "code-editing",
      "example": "search_replace(file_path, old_string, new_string)"
    },
    "metadata": {
      "source": "cursor-ide",
      "domain": "l9"
    },
    "tags": ["pattern", "editing", "best-practice"]
  }'
```

### Pattern 3: Save a User Preference

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/memory/packet" \
  -H "Authorization: Bearer $L9_EXECUTOR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "packet_type": "memory.preference",
    "payload": {
      "content": "User prefers Docker-based activation over systemd",
      "kind": "preference",
      "scope": "deployment",
      "rationale": "Faster, simpler, aligned with existing infrastructure"
    },
    "metadata": {
      "source": "cursor-ide",
      "user": "igor"
    },
    "tags": ["preference", "docker", "deployment"]
  }'
```

### Pattern 4: Search for Similar Solutions

```bash
# Find lessons about a specific topic
curl -X POST "http://127.0.0.1:8000/api/v1/memory/semantic/search" \
  -H "Authorization: Bearer $L9_EXECUTOR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "error handling in API routes",
    "top_k": 5,
    "min_score": 0.7
  }'
```

### Pattern 5: Save with Thread Context

```bash
# Link memories to a conversation thread
curl -X POST "http://127.0.0.1:8000/api/v1/memory/packet" \
  -H "Authorization: Bearer $L9_EXECUTOR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "packet_type": "memory.decision",
    "payload": {
      "content": "Decision: Use /api/v1/memory/packet as canonical endpoint",
      "kind": "decision"
    },
    "thread_id": "86fcd09e-eb31-4dd9-897d-6bd1eaf246ad",
    "tags": ["decision", "api", "memory"]
  }'
```

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `401 Unauthorized` | Missing or invalid API key | Check `L9_EXECUTOR_API_KEY` in `.env` |
| `400 Bad Request` | Invalid request format | Check JSON structure, required fields |
| `503 Service Unavailable` | Memory system not initialized | Check server logs, ensure migrations ran |
| `500 Internal Server Error` | Database/embedding failure | Check server logs, verify database connection |

### Error Response Format

```json
{
  "detail": "Error message here"
}
```

### Validation Errors

If `confidence` is provided as a number instead of dict:
```json
{
  "detail": [
    {
      "type": "dict_type",
      "loc": ["body", "confidence"],
      "msg": "Input should be a valid dictionary",
      "input": 1.0
    }
  ]
}
```

**Fix:** Either omit `confidence` or provide it as:
```json
"confidence": {
  "score": 0.95,
  "rationale": "High confidence based on successful test"
}
```

---

## Best Practices

### 1. Use Descriptive Packet Types

✅ **Good:**
```json
"packet_type": "memory.lesson"
"packet_type": "memory.pattern"
"packet_type": "memory.milestone"
```

❌ **Bad:**
```json
"packet_type": "memory"
"packet_type": "note"
"packet_type": "thing"
```

### 2. Include Rich Metadata

✅ **Good:**
```json
{
  "metadata": {
    "source": "cursor-ide",
    "creator": "Cursor-IDE",
    "workspace": "L9",
    "domain": "l9",
    "timestamp": "2026-01-05T12:00:00Z"
  }
}
```

### 3. Use Tags for Filtering

✅ **Good:**
```json
"tags": ["lesson", "paths", "portability", "bash", "error-prevention"]
```

❌ **Bad:**
```json
"tags": ["stuff"]
```

### 4. Structure Payload Content

✅ **Good:**
```json
{
  "payload": {
    "content": "Main content here",
    "kind": "lesson",
    "context": "Additional context",
    "fix": "How to fix it",
    "example": "Code example if applicable"
  }
}
```

### 5. Wait for Embeddings After Save

After saving a memory, wait 2-5 seconds before searching to allow embeddings to be generated and indexed.

### 6. Use Thread IDs for Context

When saving memories related to a specific conversation or task, include `thread_id` to link them together.

### 7. Test Locally First

Always test memory operations on local VPS (`http://127.0.0.1:8000`) before using HTTPS endpoint.

---

## Quick Reference

### Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/memory/packet` | Save a memory |
| `POST` | `/api/v1/memory/semantic/search` | Semantic search |
| `POST` | `/api/v1/memory/hybrid/search` | Hybrid search with filters |
| `GET` | `/api/v1/memory/facts` | Query knowledge facts |
| `GET` | `/api/v1/memory/insights` | Get insights for a packet |
| `GET` | `/api/v1/memory/stats` | System statistics |
| `GET` | `/api/v1/memory/health` | Health check |

### Required Headers

```bash
-H "Authorization: Bearer <L9_EXECUTOR_API_KEY>"
-H "Content-Type: application/json"
```

### Minimum Valid Request

```json
{
  "packet_type": "memory.milestone",
  "payload": {
    "content": "Memory content here"
  }
}
```

---

## Troubleshooting

### Memory Not Appearing in Search

1. **Wait 2-5 seconds** after saving (embeddings need time to index)
2. **Check packet_id** from save response to verify it was stored
3. **Try lower min_score** (default 0.5, try 0.3)
4. **Check tags** - search may filter by tags if provided

### Connection Timeouts

1. **Check container health:** `docker ps` (should show `healthy`)
2. **Check logs:** `docker logs l9-api`
3. **Try local endpoint first:** `http://127.0.0.1:8000` instead of HTTPS
4. **Verify API key:** Ensure `L9_EXECUTOR_API_KEY` is set in `.env`

### Unauthorized Errors

1. **Verify API key format:** Must be `Bearer <key>`, not just `<key>`
2. **Check .env file:** Ensure `L9_EXECUTOR_API_KEY` exists
3. **Restart container:** `docker compose restart l9-api` to pick up env changes

---

## Related Documentation

- **Memory README:** `memory/README.md`
- **Memory Wiring:** `memory/WIRING.md`
- **API Router:** `api/memory/router.py`
- **Substrate Models:** `memory/substrate_models.py`
- **Ingestion Pipeline:** `memory/ingestion.py`

---

**Remember:** The memory system is the canonical source of truth for all agent learnings, decisions, and patterns. Use it proactively to build institutional knowledge.
