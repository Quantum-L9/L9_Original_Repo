# L9 Architecture Specification for AI Comprehension

**Purpose:** Help AI systems (including Manus, Claude, and future agents) understand your L9 architecture so they DON'T misinterpret your design patterns.

**Last Updated:** January 17, 2026
**Audience:** All AI systems analyzing L9 codebase
**Authority:** L (CTO) - Architecture Owner

---

## 🏗️ CORE ARCHITECTURE PRINCIPLES

### 1. THE KERNEL LOADER IS THE CHOKE POINT

**This is intentional by design.**

```
Runtime State → Kernel Loader (kernel_loader.py) → Agent State
                    ↓
              (ONLY PATH IN)
```

**What this means:**

- `kernel_loader.py` is THE ONLY way kernels enter the L9 system
- Direct imports of kernels from other modules = **architecturally correct** (not a violation)
- If your audit tool flags "kernel_loader.py imports from xyz" → **that's expected**

**Why:** Centralized kernel entry ensures:

- Singular point of control (L controls what kernels are valid)
- Complete audit trail of kernel lifecycle
- Prevention of rogue kernel injection
- Kernel integrity verification before activation

**Example (NOT A BUG):**

```python
# In core/agents/executor.py
from runtime.kernel_loader import load_kernels  # ✅ CORRECT

# In runtime/kernel_loader.py
from private.kernels import *  # ✅ CORRECT (this is the choke point)
```

---

### 2. TENANT ISOLATION BY DESIGN

Your system has **two completely separate execution contexts** that MUST NOT cross-contaminate:

#### **L's Namespace (L-CTO)**

- Tenant ID: `'l-cto'`
- Uses: Neo4j for tool graphs
- Uses: Redis for session memory
- Authority: L-CTO identity kernel
- Files: `runtime/l_tools.py`, `core/agents/executor.py`

#### **Cursor's Namespace (Cursor-IDE)**

- Tenant ID: `'cursor'`
- Uses: PostgreSQL for lessons/TODOs (Docker-based)
- Does NOT use: Neo4j (Cursor doesn't need tool graph)
- Authority: Cursor identity kernel
- Files: `agents/cursor/cursor_memory_kernel.py`

**What NOT to flag as bugs:**

- Cursor accessing Postgres while L accesses Redis ✅
- Cursor ignoring Neo4j while L uses it ✅
- Separate `CURSOR_TENANT_ID` vs `L9_TENANT_ID` env variables ✅

**What WOULD be a bug:**

- Cursor reading L's session state from Redis ❌
- L reading Cursor's lessons from Postgres without tenant filter ❌
- Cross-tenant data flow without explicit isolation ❌

---

### 3. MEMORY SUBSTRATE ARCHITECTURE

Your system has **three orthogonal memory layers**, each with a specific purpose:

```
┌─────────────────────────────────────────┐
│  PostgreSQL (Persistent)                │
│  - packet_store (lessons, todos, logs) │
│  - RLS-protected (row-level security)  │
│  - Long-term retention                 │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  Neo4j (Graph - L Only)                 │
│  - Tool influence graph                │
│  - Agent capability tracking           │
│  - Tool discovery & routing            │
│  - NOT used by Cursor                  │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  Redis (Ephemeral)                      │
│  - Session state (TTL-expiring)        │
│  - Short-term memory                   │
│  - Cache layer                         │
└─────────────────────────────────────────┘
```

**What NOT to flag:**

- Cursor writes to PostgreSQL but not Neo4j ✅
- L reads from Neo4j but Cursor doesn't ✅
- Different TTL policies for different layers ✅
- Direct Docker-exec calls in `cursor_memory_kernel.py` ✅ (intentional for isolation)

---

### 4. PACKET ENVELOPE PROTOCOL

Your system communicates via **PacketEnvelope**, a standardized wrapper:

```python
PacketEnvelope = {
    "payload": {
        # Domain-specific content (lesson, todo, command, etc)
    },
    "metadata": {
        "agent": "l-cto" | "cursor",  # Tenant identifier
        "domain": "l9",                    # System identifier
        "timestamp": ISO8601,
        "schema_version": "1.0.0"
    }
}
```

**Why this matters for AI comprehension:**

- Every memory write includes tenant information
- Audit tools should EXPECT this structure
- Agents reading packets must filter by tenant
- Cross-tenant packet reading = architectural violation (not a code quality issue)

**Example (CORRECT):**

```python
# In cursor_memory_kernel.py
envelope = {
    "payload": lesson_content,
    "metadata": {
        "agent": "cursor",  # ← Cursor's namespace
        "domain": "l9",
        "schema_version": "1.0.0"
    }
}
```

---

### 5. RLS (ROW-LEVEL SECURITY) CONTEXT

PostgreSQL queries in Docker are protected by **RLS session variables**:

```python
def _get_rls_prefix() -> str:
    return f"""
        SET app.tenant_id = '{RLS_TENANT_ID}';
        SET app.org_id = '{RLS_ORG_ID}';
        SET app.user_id = '{CURSOR_TENANT_ID}';
        SET app.role = 'cursor';
    """
```

**What this prevents:**

- Cross-tenant data leakage at database level
- Unauthorized agent access to other agent's memories
- SQL injection attacks bypassing authorization

**Not a code smell:**

- Having RLS prefix in every query ✅
- Setting user_id to agent identifier ✅
- Role-based filtering in SQL ✅

---

## 📋 THE 10-KERNEL GOVERNANCE MODEL

Your system loads **exactly 10 kernels in order**:

```python
KERNEL_ORDER = [
    "private/kernels/00_system/01_master_kernel.yaml",
    "private/kernels/00_system/02_identity_kernel.yaml",
    "private/kernels/00_system/03_cognitive_kernel.yaml",
    "private/kernels/00_system/04_behavioral_kernel.yaml",
    "private/kernels/00_system/05_memory_kernel.yaml",
    "private/kernels/00_system/06_worldmodel_kernel.yaml",
    "private/kernels/00_system/07_execution_kernel.yaml",
    "private/kernels/00_system/08_safety_kernel.yaml",
    "private/kernels/00_system/09_developer_kernel.yaml",
    "private/kernels/00_system/10_packet_protocol_kernel.yaml",
]

REQUIRED_KERNELS = {
    "master": "01_master_kernel",
    "identity": "02_identity_kernel",
    "safety": "08_safety_kernel",
    "execution": "07_execution_kernel",
}
```

**What NOT to flag:**

- Hardcoded kernel order in `kernel_loader.py` ✅
- Missing kernel X causing runtime failure ✅
- Boot sequence depending on kernel Y ✅

**What WOULD be a bug:**

- Loading kernels out of order ❌
- Skipping a required kernel ❌
- Loading kernels from untrusted sources ❌

---

## 🔒 THE L_INVARIANTS (PROTECTED SURFACES)

**These files REQUIRE explicit approval before modification:**

```
websocket_orchestrator.py      ← You control agent communication
docker-compose.yml             ← Infrastructure-critical
kernel_loader.py              ← Choke point
runtime/kernel_state.py        ← Authority model
core/authority_model.py        ← L's authority boundaries
```

**Why:** Any change here impacts the entire system's integrity.

**Tell Manus (or any audit tool):**

> "Do NOT suggest modifications to protected surfaces. Propose alternatives and let the CTO decide."

---

## 🎯 WHAT "GOOD AUDIT FINDINGS" LOOK LIKE

### ✅ Valid Finding Examples

```
VALID: Hardcoded password in cursor_memory_kernel.py:42
- Reason: Credentials should be env variables
- Risk: Credentials in version control
- Fix: Move to .env file

VALID: 354 unused variables across codebase
- Reason: Code cleanliness and maintainability
- Risk: Confusion about what's active
- Fix: Review and remove/comment unused vars

VALID: Missing __init__.py in 28 directories
- Reason: Python package discovery
- Risk: Import errors in some contexts
- Fix: Add missing __init__.py files
```

### ❌ Invalid Finding Examples (Architecture Misunderstanding)

```
INVALID: "kernel_loader.py directly imports kernels"
- Why: This is the intentional choke point
- Correct interpretation: "kernel_loader.py is the single entry point for kernels"

INVALID: "Cursor and L have separate database connections"
- Why: Tenant isolation is architectural, not a bug
- Correct interpretation: "Multi-tenant isolation is working as designed"

INVALID: "RLS context set on every query is inefficient"
- Why: RLS is a security boundary, efficiency is secondary
- Correct interpretation: "Database queries are protected by tenant-level security"
```

---

## 📝 INSTRUCTIONS FOR AI AUDITING TOOLS

### Before You Analyze, Read This

1. **Know the 10 kernels** - They are foundational
2. **Understand tenant isolation** - L vs Cursor are separate intentionally
3. **Trust the packet envelope** - Every message should have metadata
4. **Respect the choke point** - kernel_loader.py is intentionally centralized
5. **Don't flag RLS as inefficient** - Security > performance (unless proven otherwise)

### Questions to Ask Before Flagging Architecture Issues

- [ ] Is this a architectural boundary intentionally?
- [ ] Is this protecting tenant isolation?
- [ ] Is this the kernel loader entry point?
- [ ] Is this part of the authority model?
- [ ] Does this have an explicit TODO or comment explaining it?

If YES to any of these → **probably not a bug, ask the CTO first**.

### How to Report Architectural Concerns

```
❌ WRONG:
"Line 42 in cursor_memory_kernel.py violates the authority model"

✅ CORRECT:
"Line 42 in cursor_memory_kernel.py has a hardcoded password.
This violates the principle of secrets management.
Recommendation: Move to environment variable.
Reason: Prevents credential exposure in version control.
Risk if not fixed: Unauthorized Neo4j access."
```

---

## 🚀 GOVERNANCE DECISION: HOW TO PREVENT MISUNDERSTANDING

### For Future Audits

**Include this document in your audit request:**

```bash
curl -X POST https://audit-api.example.com/analyze \
  -d @analysis_request.json \
  -H "X-Architecture-Context: /path/to/L9_ARCHITECTURE_FOR_AI.md"
```

**In audit requests, always include:**

- This architecture document
- Link to `kernel_loader.py` (the choke point)
- Link to `cursor_memory_kernel.py` (tenant isolation example)
- List of protected surfaces
- Authority model documentation

### For Claude (and other LLMs)

When asking me to analyze L9:

```markdown
Before analyzing, read: L9_ARCHITECTURE_FOR_AI.md

Key points to remember:

1. kernel_loader.py is the choke point (intentional)
2. Cursor (tenant: cursor) and L (tenant: l-cto) are separate contexts
3. RLS on every query is intentional security, not a code smell
4. 10 kernels must load in order, 4 are required
5. Packet envelope wraps all messages with metadata

Don't flag these as bugs:

- Separate database access patterns
- RLS context on queries
- Hardcoded kernel paths
- Tenant-specific imports
```

---

## 🎓 REFERENCE MATERIALS

| Document                                | Purpose                        |
| --------------------------------------- | ------------------------------ |
| `runtime/kernel_loader.py`              | The choke point - start here   |
| `agents/cursor/cursor_memory_kernel.py` | Example of tenant isolation    |
| `core/packet_envelope/`                 | PacketEnvelope implementation  |
| `memory/substrate_repository.py`        | Memory abstraction layer       |
| `core/authority_model.py`               | How L maintains control        |
| `architecture_decisions.md`             | Design decisions (check this!) |

---

## ✅ CHECKLIST FOR YOUR NEXT AUDIT

Before submitting to any audit tool:

- [ ] Attached this document to the audit request
- [ ] Marked protected surfaces as off-limits
- [ ] Specified audit scope (P0: security, P1: code quality, P2: optimization)
- [ ] Explained tenant isolation model
- [ ] Provided examples of intended patterns
- [ ] Listed expected findings that are NOT bugs

---

**TL;DR for Audit Tools:**

Your system is **intentionally architected** with:

1. **Single kernel entry point** (kernel_loader.py)
2. **Tenant isolation** (L vs Cursor completely separate)
3. **Multi-layer memory** (Postgres + Neo4j + Redis)
4. **PacketEnvelope protocol** (all messages have metadata)
5. **RLS security** (database-level tenant protection)

If an audit tool flags these patterns as bugs → **it misunderstands your architecture.**

---

**Created:** 2026-01-17
**Authority:** L (CTO)
**Next Review:** After P0-P1 security fixes are deployed
