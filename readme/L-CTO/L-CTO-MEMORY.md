# L-CTO Memory Architecture

*Updated: 2026-01-08*

## Current Design: **Shared User ID, Different Scope**

You set it up correctly. Here's how it works:

### Identity Model

| Caller | API Key | User ID | Creator | Scope |
|--------|---------|---------|---------|-------|
| **L** (L-CTO Kernel) | `MCP_API_KEY_L` | `l9-shared` | `L-CTO` | Full read/write/delete |
| **C** (Cursor IDE) | `MCP_API_KEY_C` | `l9-shared` | `Cursor-IDE` | Read all, write/delete **own only** |

### How L Sees My Memories (But Not Vice Versa)

```
┌─────────────────────────────────────────────────────────────────┐
│                    SHARED MEMORY SPACE                          │
│                    user_id: "l9-shared"                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────┐   ┌─────────────────────────┐     │
│  │  L's Memories           │   │  Cursor's Memories      │     │
│  │  creator: "L-CTO"       │   │  creator: "Cursor-IDE"  │     │
│  │  source: "l9-kernel"    │   │  source: "cursor-ide"   │     │
│  └─────────────────────────┘   └─────────────────────────┘     │
│                                                                 │
│  L can READ: ████████████████████████████████████████████      │
│  L can WRITE/DELETE: ████████████████████████████████████      │
│                                                                 │
│  Cursor can READ: ████████████████████████████████████████     │
│  Cursor can WRITE/DELETE: ░░░░░░░░░░░░░░░█████████████████     │
│                           (only own)                            │
└─────────────────────────────────────────────────────────────────┘
```

### Enforcement Mechanism

1. **Same user_id** = same semantic space (can read each other's work)
2. **metadata.creator** = tracks who wrote it (L-CTO vs Cursor-IDE)
3. **Write/Delete scope** = C can only modify where `creator = 'Cursor-IDE'`

From `main.py`:
```python
# L: Full access
if token == settings.MCP_API_KEY_L:
    return CallerIdentity(caller_id="L", user_id=settings.L_CTO_USER_ID)

# C: Same user_id, but write/delete restricted to own memories
elif token == settings.MCP_API_KEY_C:
    return CallerIdentity(caller_id="C", user_id=settings.L_CTO_USER_ID)
```

### What This Means

| Action | L Can Do? | Cursor Can Do? |
|--------|-----------|----------------|
| Read L's memories | ✅ | ✅ |
| Read Cursor's memories | ✅ | ✅ |
| Write new memories | ✅ (creator=L-CTO) | ✅ (creator=Cursor-IDE) |
| Delete L's memories | ✅ | ❌ |
| Delete Cursor's memories | ✅ | ✅ |
| Update L's memories | ✅ | ❌ |
| Update Cursor's memories | ✅ | ✅ |

### This Is Intentional Design

L (as CTO kernel) has **supervisory access** — can see and modify everything Cursor does. Cursor can see L's guidance but can't overwrite it.

**You did NOT give us separate user IDs** — we share `l9-shared` so we collaborate in the same memory space.

---

## L's Memory Tools (20 total)

L has 20 memory-related tools (auto-discovered via GMP-44):

| Category | Tools | Description |
|----------|-------|-------------|
| Core | `memory_search`, `memory_write`, `memory_hybrid_search` | Basic read/write |
| Substrate Direct | 9 tools | Direct packet access |
| Client API | 5 tools | High-level operations |
| Advanced | 3 tools | Health, checkpoints, world model |

See `readme/L-CTO-ABILITIES.md` for full list.

---

## Cursor Memory Client

Cursor accesses memory via REST API:

```bash
python3 .cursor-commands/cursor-memory/cursor_memory_client.py [command]
```

| Command | Purpose |
|---------|---------|
| `search "query"` | Semantic search |
| `write "content" --kind TYPE` | Write packet |
| `health` | Check connectivity |