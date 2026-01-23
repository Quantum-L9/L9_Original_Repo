---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "CMD-MEM-001"
component_name: "Memory-Aware Execution"
layer: "commands"
domain: "memory"
type: "slash_command"
status: "active"
created: "2026-01-07T00:00:00Z"
updated: "2026-01-07T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "standard"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === COMMAND METADATA ===
name: mem
description: "Memory-aware execution: READ context → EXECUTE with SEARCH → WRITE insights"
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
auto_chain: ynp
---

# === /mem: Memory-Aware Execution ===
# Cursor Slash Command: /mem
# Version: 1.1.0
# Updated: 2026-01-12
# Change: All operations now use MCP tools exclusively (save_memory, search_memory, get_memory_stats)

---

## WHAT IT DOES

**Forces memory-first execution** for every task:

1. **READ** — Load context from L9 memory via MCP tools (`search_memory`) before analyzing
2. **EXECUTE** — Do the task with continuous SEARCH throughout (via MCP `search_memory` tool)
3. **WRITE** — Record insights, actions, learnings back to memory (via MCP `save_memory` tool)

**Key principle:** Never start blind. Always check what you know. Always record what you learn.

---

## 🧠 MEMORY CLIENT (MCP Tools ONLY)

**PRIMARY METHOD:** All memory operations MUST use MCP tools via `/mcp/call` endpoint at `https://l9.quantumaipartners.com/mcp`

**MCP Server:** `https://l9.quantumaipartners.com/mcp` (or `https://157.180.73.53:9001/mcp`)

```bash
python3 .cursor-commands/cursor-memory/cursor_memory_client.py [command]
```

| Command | Purpose | MCP Tool Used | Endpoint |
|---------|---------|---------------|----------|
| `search "query"` | Semantic search | `search_memory` | `/mcp/call` |
| `write "content" --kind TYPE` | Write packet | `save_memory` | `/mcp/call` |
| `stats` | Packet counts | `get_memory_stats` | `/mcp/call` |
| `health` | MCP server health | Direct HTTP | `/health` |
| `session` | Current daily session UUID | N/A (local) | N/A |

**CRITICAL:** 
- ✅ **ALL memory operations use MCP tools** (`save_memory`, `search_memory`, `get_memory_stats`)
- ✅ **MCP tools flow through proper ingestion/retrieval pipeline**
- ✅ **Scope enforcement handled by MCP server** (developer/global for Cursor)
- ✅ **Governance metadata set by MCP server** (creator, source, caller)
- ❌ **HTTP/REST API is DEPRECATED** — only used for health checks and graph/cache operations (no MCP tools available)

**Implementation:** `cursor_memory_client.py` uses `mcp_call_tool()` function which calls `/mcp/call` with tool name and arguments.

---

## EXECUTION PROTOCOL

### PHASE 1: READ (Before Task Analysis)

**MANDATORY** — Run these searches via MCP `search_memory` tool before even analyzing the task:

```bash
# 1. User preferences and patterns (uses MCP search_memory tool)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "Igor preferences patterns"

# 2. Recent lessons and errors (uses MCP search_memory tool)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "lessons errors recent"

# 3. Repo structure and tools (if code task) (uses MCP search_memory tool)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "repo structure tools endpoints"

# 4. Task-specific context (extract keywords from user request) (uses MCP search_memory tool)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "[TASK_KEYWORDS]"
```

**All searches use MCP `search_memory` tool** which:
- Queries unified L9 memory substrate (packet_store + memory_embeddings)
- Enforces scope filtering (Cursor = developer/global only)
- Returns semantic similarity results with metadata
- Updates access tracking (last_accessed, access_count)

**Output format:**

```
## 🧠 MEMORY CONTEXT LOADED

### Preferences Found
- [preference 1]
- [preference 2]

### Relevant Lessons
- [lesson 1]
- [lesson 2]

### Repo/Tool Context
- [context item]

### Task-Specific Matches
- [match 1]

---
📍 Memory context loaded. Proceeding with task.
```

---

### PHASE 2: EXECUTE (With Continuous SEARCH)

During task execution, **actively search** before:

| Trigger | Search Query (via MCP search_memory) |
|---------|--------------|
| About to modify a file | `search "[filename] patterns lessons"` |
| Encountering an error | `search "error [error_type] fix"` |
| Making architectural decision | `search "[component] architecture decisions"` |
| Unsure about approach | `search "[approach] pros cons lessons"` |
| Before destructive operation | `search "destructive [operation] warnings"` |

**All searches use MCP `search_memory` tool** — no HTTP calls.

**10X Rule:** When in doubt, SEARCH. Memory is faster than mistakes.

---

### PHASE 3: WRITE (After Task Completion)

**MANDATORY** — Write back to memory via MCP `save_memory` tool:

```bash
# 1. What was done (always) - uses MCP save_memory tool
python3 .cursor-commands/cursor-memory/cursor_memory_client.py write \
  "TASK: [description]. FILES: [files]. OUTCOME: [success/partial/failed]." \
  --kind note

# 2. Lessons learned (if any) - uses MCP save_memory tool
python3 .cursor-commands/cursor-memory/cursor_memory_client.py write \
  "LESSON: [what was learned]. CONTEXT: [when this applies]." \
  --kind lesson

# 3. Errors encountered (if any) - uses MCP save_memory tool
python3 .cursor-commands/cursor-memory/cursor_memory_client.py write \
  "ERROR: [error]. CAUSE: [cause]. FIX: [fix applied]." \
  --kind error

# 4. Insights discovered (if any) - uses MCP save_memory tool
python3 .cursor-commands/cursor-memory/cursor_memory_client.py write \
  "INSIGHT: [insight]. APPLIES_TO: [context]." \
  --kind insight

# 5. New preferences detected (if user corrects behavior) - uses MCP save_memory tool
python3 .cursor-commands/cursor-memory/cursor_memory_client.py write \
  "PREFERENCE: [preference]. SOURCE: user correction." \
  --kind preference
```

**All writes use MCP `save_memory` tool** which:
- Writes to unified L9 memory substrate (packet_store + memory_embeddings)
- Generates PacketEnvelope v2.0 structure automatically
- Creates vector embedding via OpenAI
- Enforces scope (Cursor = developer scope only, cannot write l-private)
- Sets governance metadata (creator: "Cursor-IDE", source: "cursor-ide", caller: "C")
- Maps MCP scopes → DB scopes (developer → shared)

**Output format:**

```
## 📝 MEMORY UPDATED

| Type | Content | Status |
|------|---------|--------|
| note | Task completion summary | ✅ written |
| lesson | [if applicable] | ✅ written |
| error | [if applicable] | ✅ written |

Session: [daily_session_id]
Timestamp: [ISO timestamp]
```

---

## USAGE

### Basic Usage
```
/mem fix the timeout issue in api/client.py

Flow:
1. READ: Search preferences, lessons, repo context, "timeout api client"
2. EXECUTE: Fix issue, SEARCH before each decision
3. WRITE: Record what was done, any lessons learned
```

### With Explicit Context
```
/mem @api/client.py add retry logic with exponential backoff

Flow:
1. READ: Search for retry patterns, backoff lessons, api/client.py history
2. EXECUTE: Implement with continuous SEARCH for best practices
3. WRITE: Record implementation details, patterns used
```

### Research/Analysis Mode
```
/mem analyze the memory substrate for optimization opportunities

Flow:
1. READ: Search architecture decisions, performance lessons, substrate patterns
2. EXECUTE: Analyze with SEARCH for prior optimization attempts
3. WRITE: Record findings, recommendations, insights
```

---

## SEARCH STRATEGIES

### Keyword Extraction
From user request, extract:
- **Nouns:** Files, components, concepts
- **Verbs:** Actions (fix, add, refactor, analyze)
- **Domains:** API, memory, executor, tools

### Query Patterns

| Goal | Query Pattern |
|------|---------------|
| Find prior work | `"[component] changes history"` |
| Find errors | `"error [component] [symptom]"` |
| Find patterns | `"[pattern_name] implementation"` |
| Find preferences | `"Igor [topic] preference"` |
| Find decisions | `"decision [topic] rationale"` |

### Progressive Refinement
If first search yields nothing:
1. Broaden: Remove specific terms
2. Synonyms: Try alternate terminology
3. Related: Search adjacent concepts

---

## WRITE TAXONOMY

| Kind | When to Use | Example |
|------|-------------|---------|
| `note` | Task completion, session summary | "Completed GMP-25, modified 3 files" |
| `lesson` | Learning from mistake or discovery | "LESSON: Always check migration status before schema changes" |
| `error` | Error encountered and fixed | "ERROR: Import cycle. FIX: Moved shared types to core/types.py" |
| `insight` | Pattern or optimization discovered | "INSIGHT: Batch DB writes 10x faster than individual" |
| `preference` | User correction or stated preference | "PREFERENCE: Igor prefers tables over prose" |

---

## INTEGRATION WITH OTHER COMMANDS

```
/mem → /rules → /gmp
     ↓
  READ memory context
     ↓
  /rules loads state + tier classification
     ↓
  /gmp executes with memory-enhanced context
     ↓
  WRITE back to memory
```

**Chain pattern:**
```
/mem /gmp "add rate limiting to API"

Executes:
1. /mem READ phase
2. /rules (auto-called by /gmp)
3. /gmp Phase 0-6
4. /mem WRITE phase
```

---

## ANTI-PATTERNS

❌ **DON'T:** Skip READ phase to "save time" — memory lookup is faster than mistakes
❌ **DON'T:** Only SEARCH at start — continuous SEARCH catches more
❌ **DON'T:** Skip WRITE phase — future you needs this context
❌ **DON'T:** Write vague notes — specific > generic
❌ **DON'T:** Ignore search results — they exist for a reason

✅ **DO:** READ before analyzing the task
✅ **DO:** SEARCH before every significant decision
✅ **DO:** WRITE specific, actionable content
✅ **DO:** Include timestamps and session context
✅ **DO:** Record errors even if fixed immediately

---

## EXAMPLE EXECUTION

```
User: /mem fix the database connection timeout in substrate_repository.py

---

## 🧠 MEMORY CONTEXT LOADED

### Preferences Found
- Igor prefers surgical edits over rewrites
- Always show evidence before claiming fixed

### Relevant Lessons
- LESSON: Database timeouts often caused by missing connection pool limits
- LESSON: substrate_repository.py is RUNTIME_TIER, not KERNEL

### Task-Specific Matches
- Previous fix: Added 30s timeout to API client (2026-01-05)
- ERROR: Connection leak in async context (fixed with context manager)

---
📍 Memory context loaded. Proceeding with task.

[... EXECUTION with SEARCH before modifying code ...]

---

## 📝 MEMORY UPDATED

| Type | Content | Status |
|------|---------|--------|
| note | Fixed DB timeout in substrate_repository.py:45-52. Added pool_timeout=30. | ✅ written |
| lesson | LESSON: asyncpg requires explicit pool_timeout, default is None (infinite). | ✅ written |

Session: a1b2c3d4-...
Timestamp: 2026-01-07T14:32:00Z
```

---

## FAIL-SAFES

### If MCP Server Unreachable

```bash
python3 .cursor-commands/cursor-memory/cursor_memory_client.py health
```

If MCP server fails:
1. **Check API key:** Verify `L9_EXECUTOR_API_KEY` is set in `.env` or environment
2. **Check network:** Verify `https://l9.quantumaipartners.com/mcp` is reachable
3. **Check MCP endpoint:** Verify `/mcp/call` endpoint is responding
4. **Log error:** "⚠️ MCP server unreachable. Check API key and network connectivity."
5. **DO NOT fallback to HTTP** — MCP is required for proper memory operations
6. **Stop execution** — Memory operations are critical, cannot proceed without MCP

**Note:** HTTP/REST API endpoints are deprecated and should NOT be used as fallback. All memory operations require MCP tools for proper governance, scope enforcement, and ingestion pipeline.

### If Search Returns Empty

1. Broaden search terms
2. Try 2-3 alternate queries
3. If still empty: "No prior context found. Proceeding with fresh analysis."

---

## SESSION TRACKING

All writes include daily session UUID:

```bash
python3 .cursor-commands/cursor-memory/cursor_memory_client.py session
```

Output:
```json
{
  "date": "2026-01-07",
  "session_id": "a1b2c3d4-e5f6-...",
  "schema_version": "2.0.0"
}
```

Same session ID for entire day → groups related work together.

