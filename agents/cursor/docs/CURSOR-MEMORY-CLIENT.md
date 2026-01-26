# Cursor Memory Client

> **File:** `agents/cursor/cursor_memory_client.py` > **API:** `https://l9.quantumaipartners.com` > **Last Verified:** 2026-01-18

---

## Quick Start

```bash
cd /Users/ib-mac/Projects/L9

# Health check
python3 agents/cursor/cursor_memory_client.py health

# Search memory
python3 agents/cursor/cursor_memory_client.py search "error handling"

# Write to memory
python3 agents/cursor/cursor_memory_client.py write "lesson content" --kind lesson
```

---

## Environment

```bash
# Required in .env
MCP_API_KEY_C=<cursor-key>        # PRIMARY
L9_EXECUTOR_API_KEY=<fallback>    # Legacy fallback
```

---

## All 27 Commands

### Core Memory Commands (6)

| Command    | What It Does                         | Definition                |
| ---------- | ------------------------------------ | ------------------------- |
| `health`   | Check MCP endpoint + API health      | `cmd_health()` line 249   |
| `stats`    | Get packet counts, embeddings, facts | `cmd_stats()` line 237    |
| `search`   | Semantic search with filtering       | `cmd_search()` line 329   |
| `write`    | Write packet to memory               | `cmd_write()` line 387    |
| `session`  | Show current daily session UUID      | `cmd_session()` line 431  |
| `mcp-test` | Round-trip test (write + search)     | `cmd_mcp_test()` line 447 |

**Examples:**

```bash
python3 agents/cursor/cursor_memory_client.py health
python3 agents/cursor/cursor_memory_client.py stats
python3 agents/cursor/cursor_memory_client.py search "docker error" --limit 5 --min-confidence 0.3
python3 agents/cursor/cursor_memory_client.py write "Always use surgical edits" --kind lesson
python3 agents/cursor/cursor_memory_client.py session
python3 agents/cursor/cursor_memory_client.py mcp-test
```

---

### Session Commands (4)

| Command          | What It Does                           | Definition                      |
| ---------------- | -------------------------------------- | ------------------------------- |
| `session-close`  | Close session, create embedding anchor | `cmd_session_close()` line 551  |
| `session-resume` | Resume with context from past sessions | `cmd_session_resume()` line 622 |
| `resume-for`     | Resume for specific task by similarity | `cmd_resume_for()` line 721     |
| `session-diff`   | Compare current session to previous    | `cmd_session_diff()` line 1217  |

**Examples:**

```bash
python3 agents/cursor/cursor_memory_client.py session-close
python3 agents/cursor/cursor_memory_client.py session-resume --task "memory work"
python3 agents/cursor/cursor_memory_client.py resume-for "implement Redis caching"
python3 agents/cursor/cursor_memory_client.py session-diff
```

---

### Context Injection Commands (6)

| Command        | What It Does                                                           | Definition                     |
| -------------- | ---------------------------------------------------------------------- | ------------------------------ |
| `inject`       | 5-layer context injection (prefs, lessons, domain, temporal, warnings) | `cmd_inject()` line 845        |
| `warn`         | Surface past mistakes relevant to task                                 | `cmd_warn()` line 730          |
| `suggest`      | Pattern-based next-step suggestions                                    | `cmd_suggest()` line 1101      |
| `temporal`     | Time-windowed search (24h, 7d, 30d)                                    | `cmd_temporal()` line 977      |
| `fix-error`    | Find past fixes for an error                                           | `cmd_fix_error()` line 1020    |
| `dedupe-check` | Check if content already exists                                        | `cmd_dedupe_check()` line 1163 |

**Examples:**

```bash
python3 agents/cursor/cursor_memory_client.py inject "working on memory substrate"
python3 agents/cursor/cursor_memory_client.py warn "modifying docker-compose"
python3 agents/cursor/cursor_memory_client.py suggest "current context"
python3 agents/cursor/cursor_memory_client.py temporal "migration" --since 7d
python3 agents/cursor/cursor_memory_client.py fix-error "connection refused port 5432"
python3 agents/cursor/cursor_memory_client.py dedupe-check "Igor prefers tables"
```

---

### Graph Commands - Neo4j (5)

| Command         | What It Does                 | Definition                            |
| --------------- | ---------------------------- | ------------------------------------- |
| `graph-health`  | Check Neo4j health           | `cmd_graph_health()` line 1290        |
| `graph-context` | Get context for a domain     | `cmd_graph_context()` line 1296       |
| `graph-query`   | Run Cypher query             | `cmd_graph_query()` line 1307         |
| `graph-entity`  | Get entity by type and ID    | `cmd_graph_entity()` line 1326        |
| `graph-rels`    | Get relationships for entity | `cmd_graph_relationships()` line 1338 |

**Examples:**

```bash
python3 agents/cursor/cursor_memory_client.py graph-health
python3 agents/cursor/cursor_memory_client.py graph-context memory --limit 20
python3 agents/cursor/cursor_memory_client.py graph-query "MATCH (n:Agent) RETURN n LIMIT 5"
python3 agents/cursor/cursor_memory_client.py graph-entity Agent L-CTO
python3 agents/cursor/cursor_memory_client.py graph-rels Agent L-CTO --direction outgoing
```

---

### Cache Commands - Redis (6)

| Command             | What It Does                | Definition                                  |
| ------------------- | --------------------------- | ------------------------------------------- |
| `cache-health`      | Check Redis health          | `cmd_cache_health()` line 1358              |
| `cache-get`         | Get value by key            | `cmd_cache_get()` line 1364                 |
| `cache-set`         | Set value with optional TTL | `cmd_cache_set()` line 1374                 |
| `cache-session`     | Get current session context | `cmd_cache_session_context()` line 1389     |
| `cache-set-session` | Set session context         | `cmd_cache_set_session_context()` line 1403 |
| `cache-sessions`    | List recent sessions        | `cmd_cache_list_sessions()` line 1427       |

**Examples:**

```bash
python3 agents/cursor/cursor_memory_client.py cache-health
python3 agents/cursor/cursor_memory_client.py cache-get mykey
python3 agents/cursor/cursor_memory_client.py cache-set mykey "value" --ttl 3600
python3 agents/cursor/cursor_memory_client.py cache-session
python3 agents/cursor/cursor_memory_client.py cache-set-session '{"summary":"working on X"}'
python3 agents/cursor/cursor_memory_client.py cache-sessions
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  VPS (l9.quantumaipartners.com)                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Neo4j      │  │  PostgreSQL │  │  Redis      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                         │                                   │
│                    ┌────▼────┐                              │
│                    │ L9 API  │ ← /mcp/call endpoint         │
│                    └────┬────┘                              │
└─────────────────────────│───────────────────────────────────┘
                          │ HTTPS
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Mac                                                        │
│  cursor_memory_client.py → mcp_call_tool() line 154         │
└─────────────────────────────────────────────────────────────┘
```

---

## Code Structure

| Section             | Lines     | Purpose                                         |
| ------------------- | --------- | ----------------------------------------------- |
| Schema/Session UUID | 94-124    | PacketEnvelope v2.0.0, daily session ID         |
| Configuration       | 126-147   | Load .env, set API URL and key                  |
| MCP Client          | 150-189   | `mcp_call_tool()` - PRIMARY method              |
| HTTP Fallback       | 191-229   | `api_request()` - FALLBACK for graph/cache      |
| Core Commands       | 234-548   | stats, health, search, write, session, mcp-test |
| Session Commands    | 551-728   | session-close, session-resume, resume-for       |
| Context Commands    | 730-1099  | warn, inject, temporal, fix-error, suggest      |
| Dedupe/Diff         | 1163-1282 | dedupe-check, session-diff                      |
| Graph Commands      | 1285-1350 | Neo4j operations                                |
| Cache Commands      | 1353-1435 | Redis operations                                |
| Main/Argparse       | 1438-1681 | CLI argument parsing                            |

---

## Write Kinds

| Kind         | Duration | Use For            |
| ------------ | -------- | ------------------ |
| `preference` | long     | Igor's preferences |
| `lesson`     | long     | Lessons learned    |
| `insight`    | long     | Strategic insights |
| `fact`       | long     | Knowledge facts    |
| `error`      | medium   | Error patterns     |
| `note`       | medium   | General notes      |

---

## Search Options

```bash
--limit N           # Max results (default 10)
--min-confidence X  # 0.0-1.0 threshold
--sort TYPE         # relevance | importance | recency
```

---

## Inject Layers

The `inject` command loads 5 layers:

1. **Preferences** — Igor's coding style
2. **Lessons** — Past mistakes and learnings
3. **Domain** — Context for current task
4. **Temporal** — Recent session activity
5. **Warnings** — Anti-patterns to avoid
