# 🔌 Cursor-L9 Integration Guide

**Generated:** 2026-01-08 20:15 EST  
**Purpose:** How Cursor IDE can leverage L9's infrastructure  
**L's Tools:** 71 (auto-discovered from ToolDefinition.agent_id)

---

## 📊 Integration Status

| Capability | Status | How |
|------------|--------|-----|
| **Memory Read** | ✅ WORKS | MCP `search_memory` tool via `l9-memory` server |
| **Memory Write** | ✅ WORKS | MCP `save_memory` tool via `l9-memory` server |
| **Kernel Reference** | ✅ WORKS | `readme/L9-KERNEL-REFERENCE.md` |
| **Mistake Prevention** | ✅ WORKS | `python scripts/cursor_check_mistakes.py` |
| **MCP Memory Server** | ✅ ACTIVE | `https://l9.quantumaipartners.com/mcp` |
| **Simulation** | ❌ NOT YET | Requires runtime execution |

---

## 1. Memory Read (PostgreSQL Direct Access)

Cursor has **direct read access** to L9's PostgreSQL database via `mcp_postgres_query`.

### Available Tables

| Table | Contents | Example Query |
|-------|----------|---------------|
| `packet_store` | All memory packets | `SELECT * FROM packet_store LIMIT 5` |
| `reasoning_traces` | L's reasoning steps | `SELECT steps FROM reasoning_traces ORDER BY created_at DESC LIMIT 3` |
| `semantic_memory` | Semantic embeddings | `SELECT content FROM semantic_memory` |
| `knowledge_facts` | Knowledge graph facts | `SELECT * FROM knowledge_facts` |
| `agent_memory_events` | Tool calls, decisions | `SELECT * FROM agent_memory_events` |

### Example: Read L's Recent Reasoning

```sql
SELECT 
    agent_id, 
    steps, 
    confidence_scores, 
    created_at 
FROM reasoning_traces 
ORDER BY created_at DESC 
LIMIT 3;
```

### Example: Search Memory Packets

```sql
SELECT 
    packet_type,
    envelope->>'content' as content,
    timestamp
FROM packet_store 
WHERE envelope::text ILIKE '%search term%'
ORDER BY timestamp DESC
LIMIT 10;
```

---

## 2. Kernel Reference (Governance Rules)

L9's 10 kernels are in `private/` which is blocked by `.cursorignore`.

**Solution:** Readable summary at `readme/L9-KERNEL-REFERENCE.md`

### Key Governance Rules to Follow

| Kernel | Key Rule for Cursor |
|--------|---------------------|
| **Master** | Igor-only authority, executive mode by default |
| **Behavioral** | Confidence ≥0.80 → execute, <0.50 → ask one question |
| **Memory** | Never repeat mistakes, log all corrections |
| **Developer** | Use structlog, httpx, Pydantic v2 |

### Apply Kernel Rules

When generating code, reference the kernel summary:

```python
# ✅ L9 Pattern (from Developer Kernel)
import structlog
import httpx
from pydantic import BaseModel

# ❌ NOT L9 Pattern
import logging
import requests
```

---

## 3. Mistake Prevention (Script-Based)

L9's `MistakePrevention` engine blocks known anti-patterns.

### Usage

```bash
# Check inline content
python scripts/cursor_check_mistakes.py "content to check"

# Check a file
python scripts/cursor_check_mistakes.py --file path/to/file.py

# List all rules
python scripts/cursor_check_mistakes.py --list-rules

# Check from stdin
echo "content" | python scripts/cursor_check_mistakes.py --stdin
```

### Current Rules

| Rule | Severity | Pattern |
|------|----------|---------|
| MP-001 | CRITICAL | Data fabrication (fake, placeholder, example.com) |
| MP-002 | HIGH | Claiming fixed without proof |
| MP-003 | CRITICAL | Wrong GlobalCommands path (Library not Dropbox) |
| MP-004 | CRITICAL | Hardcoded /Users/ib-mac/ paths |
| MP-008 | HIGH | host.docker.internal on Linux |
| MP-009 | CRITICAL | git push without explicit request |
| MP-010 | HIGH | Creating reports/briefs documentation |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No violations |
| 1 | Warnings (non-blocking) |
| 2 | CRITICAL violations (would block) |

---

## 4. Memory Write (Via L9 API)

The MCP PostgreSQL connection is **read-only**. To write to memory:

### Option A: Use L9 API Endpoint

```bash
# When Docker is running:
curl -X POST http://localhost:8000/api/memory/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "packet_type": "cursor_memory",
    "envelope": {
      "content": "Memory content",
      "agent": "cursor"
    }
  }'
```

### Option B: Run Python Script

```bash
python -c "
from memory.substrate_service import get_service
substrate = get_service()
# Use substrate.ingest_packet() for writes
"
```

### Current Limitation

Cursor cannot write to memory directly via MCP. This is by design (security).

**Workaround:** For important learnings, use Cursor's native `update_memory` tool which stores in Cursor's memory system.

---

## 5. What Cursor Shares with L

| Shared | Details |
|--------|---------|
| **Codebase** | Same L9 workspace |
| **Rules** | Same `.cursor/rules/*.mdc` files |
| **Patterns** | Same Python/TypeScript conventions |
| **PostgreSQL** | Same database (read for Cursor) |

| NOT Shared | Details |
|------------|---------|
| **Neo4j Tool Graph** | L uses direct tools; Cursor uses CLI script |
| **Redis Session** | Separate tenant IDs (cursor vs l-cto) |
| **Private Kernels** | Cursor reads summary only |

---

## 6. Neo4j Graph Access (GMP-34)

Cursor can query L9's Neo4j repo graph using CLI:

```bash
# Count nodes by type
python scripts/cursor_neo4j_query.py --count-nodes

# Find a class
python scripts/cursor_neo4j_query.py --find-class ToolRegistry

# Find files
python scripts/cursor_neo4j_query.py --find-file executor

# List all tools
python scripts/cursor_neo4j_query.py --list-tools

# Custom Cypher
python scripts/cursor_neo4j_query.py "MATCH (t:Tool) RETURN t.name LIMIT 10"
```

### Graph Contents

| Node Type | Count | Use For |
|-----------|-------|---------|
| RepoMethod | 4,404 | Method signatures |
| RepoClass | 1,915 | Class locations |
| RepoFile | 853 | File discovery |
| Tool | 86 | L9 tool registry |
| Kernel | 10 | Governance rules |

---

## 8. Tool Auto-Discovery (GMP-44)

L's tools are **auto-discovered** from `ToolDefinition.agent_id="L"` at startup.

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    TOOL REGISTRATION FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  register_l_tools() at startup:                                 │
│                                                                 │
│  1. ToolDefinition(name="tool_name", agent_id="L", ...)         │
│                        ↓                                        │
│  2. _TOOL_AGENT_IDS["tool_name"] = "L"                         │
│                        ↓                                        │
│  3. get_approved_tools() checks _TOOL_AGENT_IDS                │
│                        ↓                                        │
│  4. Tool available to L ✅                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Adding New Tools

| Step | File | Action |
|------|------|--------|
| 1 | `runtime/l_tools.py` | Add async executor function |
| 2 | `core/tools/registry_adapter.py` | Add ToolDefinition with `agent_id="L"` |

**No ToolName enum or DEFAULT_L_CAPABILITIES updates needed!**

### Verify Tool Wiring

```bash
python3 ci/check_tool_wiring.py
```

Expected output:
```
✅ CI GATE PASSED: Tool wiring is consistent
ℹ️  GMP-44: Auto-discovery from ToolDefinition.agent_id is active
```

---

## 7. Simulation Engine (Future)

**Status:** Needs API endpoint or MCP server.

### Implementation Path

| Step | Description | Effort |
|------|-------------|--------|
| 1 | Create API router `api/simulation/router.py` | 1 hour |
| 2 | Add Pydantic models for request/response | 30 min |
| 3 | Register in `api/server.py` | 15 min |
| 4 | Create Cursor CLI script | 30 min |
| 5 | Test with sample IR graph | 1 hour |
| **Total** | | **3-4 hours** |

### What Simulation Does

The `SimulationEngine` evaluates IR graphs for:
- **Feasibility scoring** (0.0-1.0)
- **Failure mode detection**
- **Dependency analysis**
- **Resource estimation**
- **Bottleneck identification**

### Cursor Usage (When Enabled)

```bash
# Run simulation via API
curl -X POST http://localhost:8000/api/simulation/run \
  -H "Content-Type: application/json" \
  -d '{"graph_data": {...}, "mode": "thorough"}'

# Or via CLI script
python scripts/cursor_simulate.py --graph-file plan.json
```

---

## 9. Kernel Patterns for Cursor (GMP-34)

When generating code for L9, Cursor MUST follow these patterns from the kernels:

### Python Imports (MANDATORY)

```python
# ✅ REQUIRED - Always use these
import structlog              # NOT logging
import httpx                  # NOT requests
from pydantic import BaseModel  # Pydantic v2 (not v1)

# ❌ FORBIDDEN - Never use these
import logging   # Use structlog instead
import requests  # Use httpx instead
```

### Code Standards

| Pattern | Required |
|---------|----------|
| Type hints | All functions |
| Docstrings | Google style |
| Error handling | Explicit packets, not bare except |
| I/O operations | Always async |
| Data validation | Pydantic v2 BaseModel |

### Pre-Generation Checklist

Before outputting any Python code for L9:

1. ✅ Uses `structlog` (not `logging`)
2. ✅ Uses `httpx` (not `requests`)
3. ✅ Uses Pydantic v2 patterns
4. ✅ Has type hints on all functions
5. ✅ Has Google-style docstrings
6. ✅ No bare `except:` clauses
7. ✅ All I/O is async
8. ✅ Uses `$HOME` not hardcoded paths

### Example Compliant Code

```python
import structlog
import httpx
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class UserRequest(BaseModel):
    """Request model for user operations."""
    
    user_id: str = Field(..., description="Unique user identifier")
    action: str = Field(..., description="Action to perform")


async def fetch_user_data(user_id: str) -> dict:
    """
    Fetch user data from the API.
    
    Args:
        user_id: The unique user identifier
        
    Returns:
        User data dictionary
        
    Raises:
        httpx.HTTPError: On network failures
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/api/users/{user_id}")
        response.raise_for_status()
        return response.json()
```

---

## 🔧 Integration Points

### Files Cursor Should Reference

| File | Purpose |
|------|---------|
| `readme/L9-KERNEL-REFERENCE.md` | Kernel governance rules |
| `readme/L-CTO-ABILITIES.md` | L's 71 tools (auto-discovered) |
| `docs/CAPABILITY_ENABLING_PATTERN.md` | How to add new tools |
| `core/governance/mistake_prevention.py` | Mistake prevention source |
| `scripts/cursor_check_mistakes.py` | CLI for mistake checking |
| `.cursor/rules/*.mdc` | Cursor-native rules |

### How to Leverage L9 from Cursor

1. **Before generating code:** Check `L9-KERNEL-REFERENCE.md` for patterns
2. **Before outputting paths:** Run `cursor_check_mistakes.py` 
3. **To read L's context:** Query `mcp_postgres_query` for recent reasoning
4. **To persist learnings:** Use Cursor's native `update_memory`

---

## 🚀 Future Enhancements

| Enhancement | Status | Notes |
|-------------|--------|-------|
| MCP write permissions | Not planned | Security concern |
| Cursor-specific memory table | Possible | Separate from L's packets |
| Neo4j read access | Possible | For repo graph queries |
| Simulation dry-run | Future | Complex runtime needed |

---

## 📚 Related Documentation

- `readme/L9-KERNEL-REFERENCE.md` — All 10 kernels summarized
- `readme/L-CTO-ABILITIES.md` — L's 70 tools
- `.cursor-commands/learning/failures/repeated-mistakes.md` — Mistake database
- `core/governance/cursor_memory_kernel.py` — Cursor memory integration code

