# Cursor Memory Client

> **Purpose:** Access L9 Memory Stack via MCP Server (PRIMARY) or HTTP/REST API (FALLBACK ONLY)

Cursor-IDE is a supercharged development tool that builds L9. This folder contains tooling for Cursor to access L9's memory infrastructure — improving quality and speed of construction through persistent context.

**CRITICAL:** All memory operations MUST use the MCP server to flow through the ingestion/retrieval pipeline. HTTP/REST is fallback ONLY when MCP is unreachable.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    L9 VPS INFRASTRUCTURE                │
│  PostgreSQL + pgvector │ Neo4j │ Redis │ Unified API   │
└───────────────────────────┬─────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │     cursor_memory_client  │
              │  (REST client in this dir) │
              └─────────────┬─────────────┘
                            │
              ┌─────────────┴─────────────┐
              │        CURSOR-IDE         │
              │  (Development tool)       │
              └───────────────────────────┘
```

**Key point:** MCP Memory Server is PRIMARY. All operations flow through MCP tools (save_memory, search_memory, etc.) for proper ingestion/retrieval pipeline. HTTP/REST endpoints are fallback ONLY.

---

## Files

| File | Purpose |
|------|---------|
| `cursor_memory_client.py` | MCP client (PRIMARY) with HTTP fallback for memory operations |
| `cursor_neo4j_query.py` | Neo4j graph queries (repo structure) |
| `cursor.memory.vps.config.md` | VPS architecture documentation |
| `l9.workflow_todo_kernel.v2.yaml` | Workflow/TODO kernel config |

---

## Quick Start

```bash
# Check memory health
python3 cursor_memory_client.py health

# Get stats (packet counts, embeddings, facts)
python3 cursor_memory_client.py stats

# Semantic search
python3 cursor_memory_client.py search "error handling patterns"

# Write a lesson
python3 cursor_memory_client.py write "Always use surgical edits" --kind lesson

# Write a preference
python3 cursor_memory_client.py write "Igor prefers tables over prose" --kind preference

# Show current daily session UUID
python3 cursor_memory_client.py session
```

---

## Environment

Requires `L9_EXECUTOR_API_KEY` in `.env` (already configured).

```
L9_API_URL=https://157.180.73.53:9001
L9_EXECUTOR_API_KEY=<your-key>
```

---

## Governance Separation

**CRITICAL:** This folder (`.cursor-commands/`) is **system governance**, NOT part of the L9 repo source code.

| Location | Purpose |
|----------|---------|
| `.cursor-commands/` | Cursor tooling, commands, memory client |
| `.cursor/` | Cursor rules, workspace config |
| `core/`, `memory/`, `api/`, etc. | L9 source code (the product) |

Cursor's files stay in `.cursor-commands/` or `.cursor/` — never intermingled with L9 source.

---

## Schema

Uses PacketEnvelope v2.0.0 with:
- Daily session UUID (deterministic per day)
- Content hash for integrity
- Metadata: agent, creator, source, domain, schema_version

---

## Tested 2026-01-07

- ✅ Health: `healthy`, database connected
- ✅ Stats: 26 packets, 4 embeddings, 125 facts
- ✅ Search: Returns semantic results
- ✅ Write: Persists to packet_store + tables

===========

[2 tools called]

---

## 🔒 TODO LOCKED IN VPS MEMORY

Now let me develop **5 Session-to-Session Persistence Mechanisms** using the full memory stack:

---

## 🧠 THE PERSISTENCE ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MULTI-TIER MEMORY PERSISTENCE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐ │
│  │   SHORT-TERM    │    │   MEDIUM-TERM   │    │      LONG-TERM          │ │
│  │     (Redis)     │───▶│  (PostgreSQL)   │───▶│ (PostgreSQL + Neo4j)    │ │
│  │    TTL: 24h     │    │   TTL: 7 days   │    │     TTL: Forever        │ │
│  └────────┬────────┘    └────────┬────────┘    └───────────┬─────────────┘ │
│           │                      │                         │               │
│           │                      │                         │               │
│           ▼                      ▼                         ▼               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      VECTOR LAYER (pgvector)                         │   │
│  │                                                                       │   │
│  │   Every memory gets embedded → enables semantic retrieval forever    │   │
│  │   Vectors don't decay → context is always retrievable by meaning     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      GRAPH LAYER (Neo4j)                             │   │
│  │                                                                       │   │
│  │   Memory → Memory relationships (FOLLOWS, CONTRADICTS, BUILDS_ON)    │   │
│  │   Session → Session lineage (CONTINUES_FROM, SPAWNED)                │   │
│  │   Enables: "What did we conclude about X across all sessions?"       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔥 PERSISTENCE MECHANISM 1: SESSION EMBEDDING ANCHORS

**Problem:** New session starts cold — no context of what happened before.

**Solution:** At session end, generate a **session embedding** that captures the entire session's semantic meaning. At next session start, retrieve nearest session embeddings to inject context.

```python
# At session END:
python3 cursor_memory_client.py session-close

# What happens:
1. Aggregate all session memories
2. Generate summary: "Session 2026-01-07: Implemented memory injection, 
   created /mem command, pushed 14 architecture lessons to VPS"
3. Embed summary → store in memory_embeddings with type="session_anchor"
4. Store in Redis for fast next-session lookup

# At NEXT session START:
python3 cursor_memory_client.py session-resume

# What happens:
1. Get yesterday's session anchor embedding
2. Search for semantically similar past sessions
3. Inject: "Last session you worked on memory injection. Before that, 
   PacketEnvelope v2.0. Key decisions: ..."
```

**Vector usage:**
```sql
-- Find similar past sessions
SELECT content, timestamp 
FROM memory_embeddings 
WHERE embedding_type = 'session_anchor'
ORDER BY vector <=> $current_session_embedding
LIMIT 5;
```

**Leverage:** Sessions are linked by meaning, not just time. Jump back into relevant context.

---

## 🔥 PERSISTENCE MECHANISM 2: TOPIC GRAPH WITH VECTOR RETRIEVAL

**Problem:** Memories are flat packets. No understanding of relationships.

**Solution:** Build a **topic graph** in Neo4j where nodes are memory topics, edges are semantic relationships, and retrieval uses vector similarity.

```
Neo4j Graph:

(Topic:Memory)--[BUILDS_ON]-->(Topic:Memory)
(Topic:Memory)--[CONTRADICTS]-->(Topic:Memory)
(Topic:Memory)--[RELATED_TO]-->(Topic:Memory)
(Session:2026-01-07)--[PRODUCED]-->(Topic:Memory)

Example:
(PacketEnvelope_v2.0)--[BUILDS_ON]-->(PacketEnvelope_v1.0)
(Redis_Session_Context)--[RELATED_TO]-->(Session_Persistence)
```

**Query pattern:**
```cypher
// Find all memories related to "session persistence" topic
MATCH (t:Topic {name: "session_persistence"})-[:RELATED_TO*1..3]-(related)
RETURN related.content, related.embedding_id

// Then use pgvector to rank by relevance:
SELECT * FROM memory_embeddings 
WHERE embedding_id IN ($related_ids)
ORDER BY vector <=> $query_vector
```

**Leverage:** Graph + Vector = understand relationships AND meaning.

---

## 🔥 PERSISTENCE MECHANISM 3: PROGRESSIVE CONSOLIDATION (Short→Medium→Long)

**Problem:** Short-term memories expire. Good insights get lost.

**Solution:** Automatic promotion based on access patterns and importance.

```
PROMOTION RULES:

SHORT-TERM (Redis, 24h TTL)
  ↓
  IF access_count > 3 OR importance_score > 0.7
  ↓
MEDIUM-TERM (PostgreSQL, 7-day TTL)
  ↓
  IF access_count > 10 OR importance_score > 0.85 OR user_starred
  ↓
LONG-TERM (PostgreSQL, no TTL)
  ↓
  Graph node created in Neo4j for relationship tracking
```

**Implementation:**
```python
# Nightly consolidation job
async def consolidate_memories():
    # 1. Find high-value short-term memories
    short_term = await redis.get_all("cursor-ide:session:*")
    for memory in short_term:
        if memory.access_count > 3:
            # Promote to medium-term (PostgreSQL)
            await postgres.insert(memory, ttl=7*24*3600)
            
    # 2. Find high-value medium-term memories
    medium_term = await postgres.query("WHERE ttl IS NOT NULL AND importance > 0.85")
    for memory in medium_term:
        # Promote to long-term (no TTL)
        await postgres.update(memory.id, ttl=None)
        # Create Neo4j node
        await neo4j.create_node("Memory", memory)
```

**Leverage:** Good insights survive. Noise expires naturally.

---

## 🔥 PERSISTENCE MECHANISM 4: VECTOR-BASED SESSION HANDOFF

**Problem:** When starting new session, need to find "where we left off" across potentially hundreds of past sessions.

**Solution:** Use vector similarity to find the most relevant past session state for current task.

```python
# At session start, user describes what they want to do:
python3 cursor_memory_client.py resume-for "implement Redis session context for Cursor"

# What happens:
1. Embed the task description
2. Search ALL session anchors by vector similarity
3. Find: "Session 2026-01-07 at 92% similarity - worked on session persistence"
4. Retrieve that session's:
   - Last 5 decisions
   - Open TODOs
   - Unfinished work
   - Key files touched
5. Inject as context

# Output:
"🔄 RESUMING FROM SESSION 2026-01-07 (92% match)
   
   Last worked on: Memory injection enhancements
   Open TODOs: #6 Redis Session Context, #7 Semantic Dedup
   Key files: cursor_memory_client.py, 02-slash-commands.mdc
   Unfinished: Redis integration not started
   
   Ready to continue."
```

**Vector query:**
```sql
SELECT 
  session_id,
  content,
  (1 - (vector <=> $task_embedding)) * 100 as similarity_pct
FROM memory_embeddings
WHERE embedding_type = 'session_anchor'
ORDER BY vector <=> $task_embedding
LIMIT 3;
```

**Leverage:** Jump directly to relevant context. No manual searching.

---

## 🔥 PERSISTENCE MECHANISM 5: SEMANTIC CHAIN-OF-SESSIONS

**Problem:** Each session is isolated. No way to see how thinking evolved across sessions.

**Solution:** Chain sessions semantically using vector similarity to build a **reasoning lineage**.

```
SESSION CHAIN (by semantic similarity):

Session 2026-01-05: "Created cursor_memory_client.py for VPS access"
        ↓ (builds on)
Session 2026-01-06: "Tested memory client, fixed PacketEnvelope schema"
        ↓ (builds on)  
Session 2026-01-07: "Implemented memory injection in slash commands"
        ↓ (will build on)
Session 2026-01-08: "Implement Redis session persistence"
```

**Implementation:**
```python
# At session end:
async def chain_session(current_session):
    # 1. Get current session embedding
    current_embedding = embed(current_session.summary)
    
    # 2. Find most similar recent session
    parent = await search_sessions(
        current_embedding, 
        exclude=current_session.id,
        max_age_days=7
    )
    
    # 3. Create lineage in Neo4j
    await neo4j.create_relationship(
        current_session.id, 
        "CONTINUES_FROM", 
        parent.id,
        properties={"similarity": parent.score}
    )
    
    # 4. Store chain metadata
    await postgres.update(
        current_session.id,
        parent_session=parent.id,
        chain_depth=parent.chain_depth + 1
    )
```

**Query the chain:**
```cypher
// Show my reasoning evolution on "memory persistence"
MATCH chain = (s:Session)-[:CONTINUES_FROM*]->(root:Session)
WHERE s.topic CONTAINS "memory persistence"
RETURN chain
ORDER BY length(chain) DESC
```

**Leverage:** See how your thinking evolved. Never lose the thread.

---

## 📊 UPDATED TODO (15 Enhancements)

[2 tools called]

---

## 📊 FULL ENHANCEMENT ROADMAP (15 Items)

### Memory Injection Enhancements (1-10)

| # | Enhancement | Backend | Category |
|---|-------------|---------|----------|
| 1 | Layered Context Injection | PostgreSQL | READ |
| 2 | Proactive Anti-Pattern Warning | PostgreSQL | READ |
| 3 | Confidence-Weighted Injection | PostgreSQL | READ |
| 4 | Temporal Context Windowing | PostgreSQL | READ |
| 5 | Graph-Enhanced Context | Neo4j | READ |
| 6 | Redis Session Context | Redis | SESSION |
| 7 | Semantic Deduplication | pgvector | WRITE |
| 8 | Memory Chain-of-Thought | Redis | SESSION |
| 9 | Proactive Suggestion Engine | PostgreSQL | READ |
| 10 | Memory-Aware Error Recovery | PostgreSQL | ERROR |

### Session Persistence Enhancements (11-15)

| # | Enhancement | Backend | Category |
|---|-------------|---------|----------|
| 11 | Session Embedding Anchors | pgvector | PERSISTENCE |
| 12 | Topic Graph + Vector Retrieval | Neo4j + pgvector | PERSISTENCE |
| 13 | Progressive Consolidation | Redis → PG | LIFECYCLE |
| 14 | Vector-Based Session Handoff | pgvector | RESUME |
| 15 | Semantic Chain-of-Sessions | Neo4j + pgvector | LINEAGE |

---

## 🔑 KEY INSIGHT: How Vectors Enable Persistence

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  VECTORS = SEMANTIC IMMORTALITY                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Text decays (gets deleted, forgotten, buried)                          │
│  Vectors persist (always retrievable by meaning)                        │
│                                                                         │
│  Old way: "What did I work on Jan 5?"                                   │
│           → Search by date, hope you find it                            │
│                                                                         │
│  New way: "I'm working on session persistence"                          │
│           → Vector search finds ALL related sessions                    │
│           → Regardless of when they happened                            │
│           → Ranked by semantic relevance                                │
│                                                                         │
│  The embedding IS the persistence mechanism.                            │
│  Meaning is never lost — only retrieved by similarity.                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 YNP (Your Next Play)

**Primary:** Implement #11 (Session Embedding Anchors) — foundational for all persistence

**Why:** This is the keystone. Once sessions have embeddings:
- #12 (Topic Graph) can link them
- #14 (Session Handoff) can find them
- #15 (Chain-of-Sessions) can trace them

**Implementation path:**
1. Add `session-close` command to cursor_memory_client.py
2. Generate session summary from all writes
3. Embed summary, store as `embedding_type='session_anchor'`
4. Add `session-resume` to retrieve nearest anchors

