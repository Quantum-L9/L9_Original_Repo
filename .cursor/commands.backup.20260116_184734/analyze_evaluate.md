---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "7.0.0"
component_id: "CMD-ANALYZEEVALUATE-001"
component_name: "Analyze+Evaluate - Combined Analysis"
layer: "commands"
domain: "analysis"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-01T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "informational"
compliance_required: false
audit_trail: false
security_classification: "internal"

# === COMMAND METADATA ===
name: analyze+evaluate
description: "Combined rapid exploration + deep audit in one pass with cross-referencing and impact projection"
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
before_chain: extract-chat   # EXTRACT: Write learnings to VPS memory
auto_chain: ynp
---

# === L9 ANALYZE+EVALUATE: Combined Deep Analysis ===
# Cursor Slash Command: /analyze+evaluate
# Version: 7.0.0 (L9-native)
# Updated: 2026-01-01

---

## ⛓️ AUTO-CHAINS TO /ynp

This command **automatically runs /ynp at the end** to recommend the highest-leverage fix based on combined analysis + evaluation findings.

---

## WHAT IT DOES

Combines `/analyze` (explore) + `/evaluate` (audit) in a **single intelligent pass** with 5 unique capabilities only available in the combined command:

| Capability | What It Does | Why Combined is Better |
|------------|--------------|------------------------|
| **Cross-Reference** | Analyze findings inform evaluate checks | Structure issues → compliance gaps |
| **Deduplication** | Same issue not reported twice | One unified finding per problem |
| **Impact Projection** | "If we fix X, Y becomes unblocked" | Prioritize by cascade effect |
| **Tech Debt Score** | Single score: structure + compliance | Unified metric for comparison |
| **Auto-Fix Candidates** | Flag issues that can be auto-fixed | Know what's quick vs manual |

**Key principle:** More than sum of parts. Cross-referencing reveals insights neither command alone would find.

---

## WHEN TO USE

| Use `/analyze+evaluate` When... | Use Individual Commands When... |
|--------------------------------|--------------------------------|
| Before refactoring or merging | Just exploring (use `/analyze`) |
| Before promoting to canonical | Just auditing for deploy (use `/evaluate`) |
| Inheriting messy code/prompts | Time-critical, need speed |
| Need full picture before GMP | Already know the issues |
| Comparing two versions | Single-dimension check only |

---

## EXECUTION PROTOCOL

### Step 0: MEMORY INJECTION (/mem READ phase)

**MANDATORY** — Load context from L9 memory via MCP server before analysis:

```bash
# 1. User preferences and patterns (via MCP search_memory tool)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "Igor preferences patterns"

# 2. Recent lessons and errors (via MCP search_memory tool)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "lessons errors recent"

# 3. Analysis/evaluation patterns (via MCP search_memory tool)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "analysis evaluation patterns lessons"

# 4. Target-specific context (via MCP search_memory tool)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "[TARGET_KEYWORDS] patterns history"
```

**Note:** All searches use MCP server (PRIMARY). Client falls back to HTTP only if MCP unreachable.

**Output format:**

```
## 🧠 MEMORY CONTEXT LOADED

### Preferences Found
- [preference 1]
- [preference 2]

### Relevant Lessons
- [lesson 1]
- [lesson 2]

### Analysis Patterns
- [pattern 1]

### Target-Specific Matches
- [match 1]

---
📍 Memory context loaded. Proceeding with analysis.
```

### Step 1: STATE_SYNC (Required)

```
1. Read workflow_state.md
2. Extract: PHASE, TODOs, priority tier
3. Identify target scope and tier classification
```

### Step 1: CLASSIFY TARGET

```
ASSET TYPES:
├── MODULE: Python package with __init__.py
├── SERVICE: Class with methods, dependencies
├── AGENT: Agent class (BaseAgent subclass)
├── ROUTER: FastAPI router with endpoints
├── TOOL: Tool definition in registry
├── KERNEL: YAML kernel file
├── PROMPT: Markdown prompt/command file
├── MIGRATION: SQL file
├── CONFIG: Settings, docker-compose, env
├── SPEC: YAML spec file
├── MIXED: Multiple types in scope
└── UNKNOWN: Needs deeper inspection
```

### Step 2: PARALLEL ANALYSIS

Run both phases simultaneously, feeding insights between them:

```
┌─────────────────────────────────────────────────────────────┐
│                    ANALYZE PHASE                            │
│  ├── Structure Map (files, classes, functions)              │
│  ├── Flow Trace (entry points, data paths)                  │
│  ├── Hotspot Detection (critical areas)                     │
│  └── Dependency Graph (imports, relationships)              │
└─────────────────────┬───────────────────────────────────────┘
                      │ Cross-reference
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    EVALUATE PHASE                           │
│  ├── L9 Code Health (patterns, anti-patterns)               │
│  ├── GMP Compliance (phase gates, TODOs)                    │
│  ├── Tier Compliance (KERNEL/RUNTIME/INFRA/UX)              │
│  └── Gap Analysis (vs production-ready)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │ Synthesize
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 COMBINED INSIGHTS                           │
│  ├── Cross-Referenced Findings (structure → compliance)     │
│  ├── Impact Projection (fix X → unblocks Y)                 │
│  ├── Tech Debt Score (unified metric)                       │
│  ├── Auto-Fix Candidates (quick wins)                       │
│  └── Prioritized Action Plan (by cascade effect)            │
└─────────────────────────────────────────────────────────────┘
```

### Step 3: CROSS-REFERENCE ANALYSIS

Connect structure issues to compliance gaps:

```
CROSS-REFERENCE PATTERNS:
├── Hotspot + Anti-pattern → HIGH PRIORITY (complex AND broken)
├── Orphan + No Tests → DEAD CODE (safe to remove)
├── Entry Point + Missing Packet → AUDIT GAP (needs logging)
├── Complex Flow + No Error Handling → RELIABILITY RISK
├── Cross-Tier Import + KERNEL_TIER → ARCHITECTURE VIOLATION
└── High Coupling + Missing Types → MAINTENANCE DEBT
```

### Step 4: IMPACT PROJECTION

Calculate cascade effects:

```
IMPACT SCORING:
For each finding:
1. What blocks if this isn't fixed? (downstream_blocked)
2. What unblocks if this IS fixed? (upstream_unlocked)
3. How many other findings does this affect? (cross_impact)
4. Is this on critical path? (critical_path_multiplier)

Impact Score = (downstream_blocked × 2) + upstream_unlocked + cross_impact
              × critical_path_multiplier
```

### Step 5: TECH DEBT SCORING

Unified metric combining structure + compliance:

```python
TECH_DEBT_SCORE = {
    # Structure (from /analyze)
    "complexity_score": 0-100,      # Cyclomatic complexity, nesting depth
    "coupling_score": 0-100,        # Dependencies, cross-tier violations
    "orphan_score": 0-100,          # Dead code, unused exports
    
    # Compliance (from /evaluate)
    "pattern_score": 0-100,         # L9 patterns compliance
    "test_coverage_score": 0-100,   # Test existence and quality
    "governance_score": 0-100,      # GMP compliance, approval gates
    
    # Combined
    "overall_tech_debt": weighted_average(all_scores),
    "trend": "improving" | "stable" | "degrading",
}
```

### Step 6: AUTO-FIX CANDIDATES

Identify what can be fixed automatically:

```
AUTO-FIX CATEGORIES:
├── 🤖 AUTOMATABLE (< 1 min)
│   ├── Missing imports (add from context)
│   ├── Unused imports (remove)
│   ├── Type hint additions (infer from usage)
│   ├── Formatting issues (black/ruff)
│   └── Simple bare except → specific exception
│
├── 🔧 SEMI-AUTO (1-5 min, needs review)
│   ├── Missing docstrings (generate template)
│   ├── Timeout additions (add default)
│   ├── Packet logging (add boilerplate)
│   └── Error handling templates
│
└── 👤 MANUAL REQUIRED (> 5 min)
    ├── Architectural changes
    ├── Complex refactoring
    ├── Business logic fixes
    └── Cross-module changes
```

---

## OUTPUT FORMAT

```
## 🔍 L9 ANALYZE+EVALUATE: [Target Name]

### 📍 STATE_SYNC
- **PHASE:** [0-6] — [phase name]
- **Priority Tier:** [🔴/🟠/🟡/🔵]
- **Target Type:** [MODULE/SERVICE/AGENT/etc.]
- **Target Tier:** [KERNEL/RUNTIME/INFRA/UX]

---

### 📊 EXECUTIVE SUMMARY

| Metric | Score | Status |
|--------|-------|--------|
| Structure Health | 78% | 🟡 |
| Code Quality | 85% | 🟢 |
| GMP Compliance | 60% | 🟠 |
| Test Coverage | 45% | 🔴 |
| **Tech Debt Score** | **67%** | 🟡 |

**Trend:** [improving/stable/degrading] vs last evaluation

---

### 🗺️ STRUCTURE MAP (from Analyze)

```
[target]/
├── __init__.py (exports: X, Y, Z)
├── models.py (3 classes)
├── service.py (main: FooService) ← 🎯 HOTSPOT
└── tests/ (8 tests, 45% coverage)
```

**Key Flows:**
```
POST /api/foo → routes.py → service.py → memory.py
                              ↓
                         governance.check()
```

---

### 🩺 HEALTH SCAN (from Evaluate)

#### L9 Pattern Compliance
| Pattern | Status | Location |
|---------|--------|----------|
| structlog | ✅ 100% | — |
| httpx | ✅ 100% | — |
| Packet logging | ⚠️ 72% | Missing L:45, L:89, L:156 |
| Type hints | ⚠️ 68% | 12 functions missing |
| Async I/O | ✅ 95% | 1 sync call L:234 |

#### Anti-Patterns Found
| Location | Issue | Severity | Auto-Fix? |
|----------|-------|----------|-----------|
| service.py:45 | Bare except | 🟡 | 🤖 Yes |
| service.py:89 | Missing timeout | 🟡 | 🔧 Semi |
| routes.py:156 | No packet log | 🟠 | 🔧 Semi |

---

### 🔗 CROSS-REFERENCED FINDINGS

| # | Structure Issue | + Compliance Gap | = Combined Finding | Impact |
|---|-----------------|------------------|-------------------|--------|
| 1 | service.py:45 is HOTSPOT | + has bare except | = **HIGH RISK**: Critical path with poor error handling | 🔴 9.2 |
| 2 | routes.py is ENTRY POINT | + no packet logging | = **AUDIT GAP**: API entry not tracked | 🟠 7.5 |
| 3 | models.py HIGH COUPLING | + missing type hints | = **MAINTENANCE DEBT**: Hard to change safely | 🟡 5.3 |

---

### 📈 IMPACT PROJECTION

If we fix these issues, here's what unblocks:

| Fix This | Unblocks | Cascade Score |
|----------|----------|---------------|
| #1 Bare except in service.py | GMP-16 can proceed, deploy unblocked | ⭐⭐⭐⭐⭐ |
| #2 Packet logging in routes.py | Audit compliance, observability | ⭐⭐⭐⭐ |
| #3 Type hints in models.py | Refactoring confidence, IDE support | ⭐⭐⭐ |

**Recommendation:** Fix #1 first — highest cascade effect.

---

### 🛠️ AUTO-FIX CANDIDATES

#### 🤖 Automatable (run now)
```bash
# These can be fixed immediately:
ruff check --fix service.py  # bare except → specific exception
ruff check --fix models.py   # unused imports
```

#### 🔧 Semi-Auto (template + review)
| Issue | Template Available | Time |
|-------|-------------------|------|
| Packet logging | ✅ PacketEnvelope boilerplate | 2 min |
| Timeout addition | ✅ httpx timeout param | 1 min |
| Missing docstrings | ✅ Google-style template | 3 min |

#### 👤 Manual Required
| Issue | Why Manual | Est. Time |
|-------|-----------|-----------|
| service.py refactor | Complex branching logic | 30 min |
| Cross-module types | Affects 5 files | 45 min |

---

### 📋 PRIORITIZED ACTION PLAN

| Priority | TODO | Scope | Files | Impact | Auto? |
|----------|------|-------|-------|--------|-------|
| 🔴 1 | Fix bare except + add error packets | RUNTIME | service.py | Unblocks GMP-16, deploy | 🔧 Semi |
| 🔴 2 | Add packet logging to entry points | RUNTIME | routes.py | Audit compliance | 🔧 Semi |
| 🟠 3 | Add type hints to public APIs | RUNTIME | models.py, service.py | Maintenance | 🤖 Auto |
| 🟡 4 | Add missing docstrings | RUNTIME | 8 functions | Documentation | 🤖 Auto |

---

### 📦 BATCH OPPORTUNITIES

**Batch 1: RUNTIME Error Handling (TODO 1 + 2)**
- Scope: service.py, routes.py
- Theme: Error handling + packet logging
- Time: 15 min combined
- Impact: Unblocks deploy + audit compliance

**Batch 2: RUNTIME Type Safety (TODO 3 + 4)**
- Scope: models.py, service.py
- Theme: Types + docs (can auto-generate)
- Time: 10 min with tooling
- Impact: Maintenance improvement

---

### 🎯 YNP (Your Next Play)

**Primary:** `/gmp` with Batch 1 (error handling + packet logging)
**Why:** Highest cascade score (9.2), unblocks GMP-16 and deploy
**Scope:** service.py, routes.py — both RUNTIME_TIER

**Batch opportunity:** Chain TODO 1 + 2 in single GMP run

**Alternates:**
1. Run auto-fixes first (`ruff --fix`) to clear quick wins
2. If GMP-16 blocked by other issues, start Batch 2 instead

---

### 📝 ANALYSIS METADATA

```yaml
analyze_evaluate:
  timestamp: 2026-01-01T12:00:00Z
  target: core/agents/
  type: MODULE
  tier: RUNTIME_TIER
  files_scanned: 12
  total_lines: 2,450
  
  findings:
    from_analyze: 8
    from_evaluate: 12
    cross_referenced: 5
    deduplicated: 3
    
  scores:
    structure_health: 78
    code_quality: 85
    gmp_compliance: 60
    test_coverage: 45
    tech_debt: 67
    
  auto_fix:
    automatable: 4
    semi_auto: 3
    manual: 2
    
  impact:
    highest_cascade: "bare except in service.py"
    cascade_score: 9.2
    unblocks: ["GMP-16", "deploy", "audit"]
```
```

---

## COMPARISON MODES

### Standard (single target)
```
/analyze+evaluate @core/agents/
```

### Compare Two Targets
```
/analyze+evaluate @core/agents/ --compare @orchestration/
```
Outputs side-by-side comparison with relative tech debt.

### Regression Check (vs baseline)
```
/analyze+evaluate @core/agents/ --baseline main
```
Compares current branch vs main, shows what got better/worse.

### Focus Mode
```
/analyze+evaluate @core/agents/ --focus security
/analyze+evaluate @core/agents/ --focus performance
/analyze+evaluate @core/agents/ --focus compliance
```
Emphasizes specific dimension.

---

## FLAGS & OPTIONS

| Flag | Description | Default |
|------|-------------|---------|
| `--compare TARGET` | Side-by-side comparison | none |
| `--baseline BRANCH` | Regression check vs branch | none |
| `--focus DIMENSION` | Emphasize: security/performance/compliance | all |
| `--auto-fix` | Run automatable fixes immediately | false |
| `--quick` | Skip deep analysis, just scores + YNP | false |
| `--json` | Output as JSON for automation | false |

---

## UNIQUE VALUE (vs Running Separately)

| Capability | /analyze + /evaluate | /analyze+evaluate |
|------------|---------------------|-------------------|
| Context | Two separate loads | Single context, cross-ref |
| Deduplication | May report same issue twice | Unified findings |
| Impact scoring | None | Cascade effect calculation |
| Tech debt score | Separate metrics | Single unified score |
| Auto-fix detection | Not included | Categories + templates |
| Comparison mode | N/A | Built-in diff |
| Regression check | N/A | Built-in baseline |

---

## MEMORY WRITE (/mem WRITE phase)

**MANDATORY** — After analysis completes, write insights to L9 memory via MCP server:

```bash
# 1. Analysis summary (always) - via MCP save_memory tool
python3 .cursor-commands/cursor-memory/cursor_memory_client.py write \
  "ANALYZE+EVALUATE: [target]. TECH_DEBT: [score]%. FINDINGS: [count]. PRIORITY: [highest_cascade]." \
  --kind note

# 2. Lessons learned (if any patterns discovered) - via MCP save_memory tool
python3 .cursor-commands/cursor-memory/cursor_memory_client.py write \
  "LESSON: [pattern discovered]. CONTEXT: [when this applies]." \
  --kind lesson

# 3. Insights (if architectural insights found) - via MCP save_memory tool
python3 .cursor-commands/cursor-memory/cursor_memory_client.py write \
  "INSIGHT: [architectural insight]. APPLIES_TO: [context]." \
  --kind insight
```

**Note:** All writes use MCP server (PRIMARY) and flow through ingestion pipeline. Client falls back to HTTP only if MCP unreachable.

**Output format:**

```
## 📝 MEMORY UPDATED

| Type | Content | Status |
|------|---------|--------|
| note | Analysis summary | ✅ written |
| lesson | [if applicable] | ✅ written |
| insight | [if applicable] | ✅ written |

Session: [daily_session_id]
Timestamp: [ISO timestamp]
```

---

## INTEGRATION

- **Auto-chains to:** `/ynp` (always)
- **Chains from:** `/harvest` (after extraction), initial exploration, `/mem` (memory-first execution)
- **Chains to:** `/gmp` (with prioritized TODOs), `/refactor-upgrade` (for auto-fixes)
- **Updates:** `workflow_state.md` with tech debt score and findings
- **Memory integration:** Uses `/mem` READ phase before analysis, WRITE phase after completion

---

## ANTI-PATTERNS

❌ **DON'T:** Run /analyze then /evaluate separately (use this instead)
❌ **DON'T:** Ignore auto-fix candidates (quick wins!)
❌ **DON'T:** Fix low-impact issues before high-cascade ones
❌ **DON'T:** Skip comparison mode for refactoring decisions

✅ **DO:** Use impact projection to prioritize
✅ **DO:** Batch fixes by theme and tier
✅ **DO:** Run auto-fixes first to clear noise
✅ **DO:** Check regression before merging
✅ **DO:** Let YNP guide next action

