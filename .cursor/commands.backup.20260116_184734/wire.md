---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "7.0.0"
component_id: "CMD-WIRE-001"
component_name: "Wire - Integration Protocol"
layer: "commands"
domain: "integration"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-01T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "operational"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === COMMAND METADATA ===
name: wire
description: "L9-native wiring — integrate generated files into repo with imports, routes, and registrations"
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
before_chain: extract-chat   # EXTRACT: Write learnings to VPS memory
auto_chain: ynp
---

# === L9 WIRE: Integration & Wiring Protocol ===
# Cursor Slash Command: /wire
# Version: 7.0.0 (L9-native)
# Updated: 2026-01-01

---

## ⛓️ AUTO-CHAINS TO /ynp

After wiring, **automatically runs /ynp** to recommend validation, testing, or next integration task.

---

## WHAT IT DOES

**Integrates generated files into the L9 repository:**

1. **File Movement** — Copy from generated/ to target locations
2. **Import Registration** — Add imports to __init__.py files
3. **Route Registration** — Wire new routes into api/server.py
4. **Tool Registration** — Add tools to tool registry
5. **Service Wiring** — Connect services to dependency injection
6. **Validation** — Verify imports resolve, tests pass

**Key principle:** Generated files are useless until wired. Wire completely or not at all.

---

## ⚠️ KERNEL_TIER REDIRECT

**If wiring targets KERNEL_TIER files, STOP and redirect to /gmp:**

```
PROTECTED FILES (redirect to /gmp):
├── core/kernels/kernel_loader.py
├── core/agents/executor.py
├── memory/substrate_service.py
├── runtime/websocket_orchestrator.py
├── docker-compose.yml
└── Any file in kernels/ directory

IF target in PROTECTED FILES:
  → "⚠️ KERNEL_TIER detected. Redirecting to /gmp for controlled wiring."
  → Generate GMP TODO plan for wiring
  → Execute via /gmp protocol (Phases 0-6)
```

---

## EXECUTION PROTOCOL

### Step 0: STATE_SYNC + TIER CHECK

```
1. Read workflow_state.md
2. Check if wiring is in current scope
3. Identify generated files to wire
4. **TIER CHECK:** Classify all target files
   - If ANY target is KERNEL_TIER → REDIRECT to /gmp
   - Else → proceed with /wire
```

### Step 1: INVENTORY

Scan generated/ directory (or specified source):

```
WIRING INVENTORY:
├── Python Modules: .py files needing __init__.py registration
├── Routes: FastAPI routers needing server.py registration
├── Tools: Tool definitions needing registry registration
├── Services: Service classes needing DI wiring
├── Configs: YAML/JSON needing settings integration
├── Migrations: SQL needing migration registration
└── Tests: Test files needing pytest discovery
```

### Step 2: GENERATE WIRING PLAN

```markdown
## 🔌 WIRING PLAN

### Files to Move
| Source | Destination | Type |
|--------|-------------|------|
| generated/core/observability/models.py | core/observability/models.py | Module |
| generated/api/routes/metrics.py | api/routes/metrics.py | Router |

### Import Registrations
| File | Import to Add |
|------|---------------|
| core/observability/__init__.py | from .models import TraceContext, Span |
| api/routes/__init__.py | from .metrics import router as metrics_router |

### Route Registrations
| File | Registration |
|------|--------------|
| api/server.py | app.include_router(metrics_router, prefix="/api/v1/metrics") |

### Tool Registrations
| File | Registration |
|------|--------------|
| core/tools/registry.py | register_tool(ObservabilityTool()) |

### Validation Steps
1. py_compile all new files
2. Run import check
3. Run affected tests
```

### Step 3: EXECUTE WIRING

For each item in plan:

1. **Move file** to destination
2. **Add imports** to __init__.py (surgically, not rewrite)
3. **Add registrations** to appropriate files
4. **Validate** imports resolve

### Step 4: VALIDATION

```
WIRING VALIDATION:
├── [ ] All files in target locations
├── [ ] All imports added to __init__.py
├── [ ] All routes registered in server.py
├── [ ] py_compile passes for all new files
├── [ ] Import resolution check passes
├── [ ] Affected tests pass
└── [ ] No circular imports introduced
```

### Step 5: REPORT

Generate wiring report with all changes made.

---

## OUTPUT FORMAT

```markdown
## 🔌 WIRING COMPLETE

### 📦 Files Moved
| Source | Destination | Status |
|--------|-------------|--------|
| generated/core/obs/models.py | core/observability/models.py | ✅ |
| generated/core/obs/tracing.py | core/observability/tracing.py | ✅ |
| generated/api/routes/metrics.py | api/routes/metrics.py | ✅ |

### 📥 Imports Added

**core/observability/__init__.py:**
```python
from .models import TraceContext, Span, LLMGenerationSpan
from .tracing import trace_context, auto_trace
```

**api/routes/__init__.py:**
```python
from .metrics import router as metrics_router
```

### 🔗 Registrations Added

**api/server.py (line 45):**
```python
app.include_router(metrics_router, prefix="/api/v1/metrics", tags=["metrics"])
```

### ✅ Validation Results
- py_compile: ✅ All files valid
- Import check: ✅ All imports resolve
- Tests: ✅ 12 passed, 0 failed
- Circular imports: ✅ None detected

### 🎯 YNP (Your Next Play)
**Primary:** /evaluate @core/observability/ to verify integration
**Alternates:** Run full test suite, Deploy to VPS
```

---

## USAGE

### Wire Generated Files
```
/wire

Wires all files in generated/ to appropriate locations.
```

### Wire Specific Source
```
/wire @generated/core/observability/

Wires only files from specified directory.
```

### Wire with Target
```
/wire generated/slack_adapter.py → api/slack_adapter.py

Explicit source → destination mapping.
```

### Wire from Harvest
```
/harvest @perplexity-chat.md
/wire

Chains: harvest extracts files, wire integrates them.
```

### Dry Run
```
/wire --dry-run

Shows wiring plan without executing.
```

---

## WIRING PATTERNS

### Pattern 1: Python Module

```
Source: generated/core/observability/models.py
Destination: core/observability/models.py

Wiring:
1. Create core/observability/ if not exists
2. Create core/observability/__init__.py if not exists
3. Move models.py to destination
4. Add exports to __init__.py:
   from .models import TraceContext, Span
```

### Pattern 2: FastAPI Router

```
Source: generated/api/routes/metrics.py
Destination: api/routes/metrics.py

Wiring:
1. Move file to destination
2. Add to api/routes/__init__.py:
   from .metrics import router as metrics_router
3. Add to api/server.py:
   app.include_router(metrics_router, prefix="/api/v1/metrics")
```

### Pattern 3: Tool Registration

```
Source: generated/core/tools/observability_tool.py
Destination: core/tools/observability_tool.py

Wiring:
1. Move file to destination
2. Add to core/tools/__init__.py:
   from .observability_tool import ObservabilityTool
3. Add to tool registry (LTOOLSDEFINITIONS):
   ToolDefinition(name="observability", ...)
```

### Pattern 4: Service Wiring

```
Source: generated/services/metrics_service.py
Destination: services/metrics_service.py

Wiring:
1. Move file to destination
2. Add to services/__init__.py
3. Wire into FastAPI dependency injection
```

### Pattern 5: Migration

```
Source: generated/migrations/0010_observability.sql
Destination: migrations/0010_observability.sql

Wiring:
1. Determine next migration number
2. Rename file with correct sequence
3. Add to migration index if exists
```

---

## SURGICAL EDITS

**CRITICAL:** Use search_replace for ALL edits. NEVER rewrite entire files.

```python
# ✅ CORRECT: Surgical import addition
# In core/observability/__init__.py, add at end:
from .models import TraceContext, Span

# ❌ WRONG: Rewriting entire file
# Don't regenerate __init__.py from scratch
```

### Import Addition Template

```python
# Add to end of imports section:
from .new_module import NewClass, new_function
```

### Route Registration Template

```python
# Add after other router includes:
app.include_router(new_router, prefix="/api/v1/new", tags=["new"])
```

---

## VALIDATION CHECKS

```bash
# 1. Syntax check all new files
python -m py_compile core/observability/*.py

# 2. Import resolution check
python -c "from core.observability import *"

# 3. Run affected tests
pytest tests/core/observability/ -v

# 4. Check for circular imports
python -c "import core.observability; import api.routes"
```

---

## INTEGRATION

- **Chains from:** `/harvest` (extracts files), `/forge` (generates files)
- **Chains to:** `/ynp` (next action), `/evaluate` (verify integration)
- **Updates:** `workflow_state.md` with wiring results

---

## ANTI-PATTERNS

❌ **DON'T:** Wire KERNEL_TIER files (use /gmp instead)
❌ **DON'T:** Rewrite entire __init__.py files
❌ **DON'T:** Skip validation after wiring
❌ **DON'T:** Wire without checking for conflicts
❌ **DON'T:** Forget to add exports to __init__.py
❌ **DON'T:** Wire to wrong directory structure

✅ **DO:** Check tier BEFORE wiring — redirect to /gmp if KERNEL_TIER
✅ **DO:** Use surgical search_replace edits
✅ **DO:** Run validation after every wire
✅ **DO:** Check for existing files before overwriting
✅ **DO:** Add all necessary exports
✅ **DO:** Follow L9 directory conventions

---

## EXAMPLES

### Example 1: Wire Observability Module
```
/wire @generated/core/observability/

WIRING COMPLETE:

📦 Files Moved: 5
- models.py → core/observability/models.py ✅
- tracing.py → core/observability/tracing.py ✅
- metrics.py → core/observability/metrics.py ✅
- decorators.py → core/observability/decorators.py ✅
- __init__.py → core/observability/__init__.py ✅

📥 Exports Added to __init__.py:
from .models import TraceContext, Span, LLMGenerationSpan
from .tracing import trace_context, with_tracing
from .metrics import MetricsAggregator
from .decorators import auto_trace, trace_llm

✅ Validation: All checks passed

🎯 YNP: /evaluate @core/observability/ to verify
```

### Example 2: Wire New Route
```
/wire generated/api/routes/commands.py → api/routes/commands.py

WIRING COMPLETE:

📦 File Moved:
- commands.py → api/routes/commands.py ✅

📥 Import Added to api/routes/__init__.py:
from .commands import router as commands_router

🔗 Registration Added to api/server.py (line 67):
app.include_router(commands_router, prefix="/api/v1/commands", tags=["commands"])

✅ Validation: All checks passed

🎯 YNP: Test new /api/v1/commands endpoints
```
