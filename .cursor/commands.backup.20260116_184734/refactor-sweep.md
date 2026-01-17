---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "CMD-REFACTORSWEEP-001"
component_name: "Refactor-Sweep - Pattern Replacement"
layer: "commands"
domain: "refactoring"
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
name: refactor-sweep
description: "Surgical codebase-wide term replacement with categorization, impact analysis, and GMP-ready execution"
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
before_chain: extract-chat   # EXTRACT: Write learnings to VPS memory
auto_chain: gmp
---

# === L9 REFACTOR-SWEEP: Comprehensive Term/Pattern Replacement ===
# Cursor Slash Command: /refactor-sweep
# Version: 1.0.0 (L9-native)
# Updated: 2026-01-01

---

## ⛓️ AUTO-CHAINS TO /gmp

After generating the sweep plan:
- Creates GMP-ready TODO plan
- Chains to `/gmp` for tracked execution with audit trail

---

## WHAT IT DOES

Comprehensive sweep to replace deprecated terms/patterns across entire codebase:

1. **SCAN** — Find all occurrences of target term(s)
2. **CATEGORIZE** — Active code vs Archive vs Docs vs Config
3. **ANALYZE** — Impact score per file, identify complex cases
4. **PROPOSE** — Translation map (old → new terms)
5. **GENERATE** — GMP-ready TODO plan (Phase 0 locked format)
6. **EXECUTE** — Run as GMP with full audit trail

**Key principle:** Surgical replacement with categorization. Skip archived code. Audit everything.

---

## WHEN TO USE

| Use Case | Example |
|----------|---------|
| Deprecating a dependency | n8n → L9 agents, supabase → postgres |
| Renaming core concepts | user_id → customer_id across codebase |
| Removing vendor lock-in | Specific vendor refs → generic patterns |
| Platform migration cleanup | Old platform → new platform terms |
| Terminology standardization | Inconsistent naming → consistent naming |

---

## EXECUTION PROTOCOL

### Step 1: TARGET DEFINITION

```
/refactor-sweep --term "supabase" --replace-with "postgres" --scope "active"

Required:
  --term STRING          Term to find (case-insensitive by default)

Optional:
  --replace-with STRING  Replacement term (omit for audit-only)
  --scope STRING         "all" | "active" | "archive" | "docs" (default: "active")
  --dry-run              Show plan without executing
  --include-archived     Include archived files in scope
  --regex                Treat term as regex pattern
  --case-sensitive       Case-sensitive search
  --gmp-id STRING        Override GMP ID (default: auto-increment)
```

### Step 2: SCAN + CATEGORIZE

Run comprehensive scan and categorize results:

```
## 🔍 SWEEP SCAN: "[term]"

### By Category

| Category | Files | Refs | Action |
|----------|-------|------|--------|
| 🔴 Active Code | X | Y | REPLACE |
| 🟠 Active Docs | X | Y | REPLACE (context-aware) |
| 🟡 Archive | X | Y | SKIP (deprecated) |
| 🔵 Historical Docs | X | Y | SKIP (history preserved) |
| ⬜ Configs | X | Y | REPLACE |

**Total:** N files, M refs
**Actionable:** N files, M refs (excludes archive)
```

**Category Definitions:**

| Category | Criteria | Default Action |
|----------|----------|----------------|
| **Active Code** | `*.py`, `*.ts`, `*.tsx` NOT in archive/ | REPLACE |
| **Active Docs** | `*.md` in root, docs/, .cursor-commands/ | REPLACE |
| **Archive** | Anything in `archive/`, `deprecated/`, `_archived/` | SKIP |
| **Historical Docs** | `*.md` in archive/, old dates in path | SKIP |
| **Configs** | `*.yaml`, `*.json`, `*.env*`, `*.toml` | REPLACE |

### Step 3: TRANSLATION MAP

Generate context-aware replacements:

```
## 🔄 TRANSLATION MAP

| Old Pattern | New Pattern | Context |
|-------------|-------------|---------|
| `old_term` | `new_term` | General reference |
| `old_term_client` | `new_term_client` | Client variable names |
| `OLD_TERM_URL` | `NEW_TERM_URL` | Environment variables |
| `oldTermApi` | `newTermApi` | API references |
| `from old_term import` | `from new_module import` | Import statements |

### ⚠️ Manual Review Required
Files with complex logic that need human verification:
- `path/to/complex_file.py` — Multiple contexts, verify each
```

### Step 4: GENERATE GMP TODO

Output in locked Phase 0 format:

```
## 📋 GMP TODO PLAN (LOCKED)

**GMP ID:** GMP-[N]: [Term] Sweep
**TIER:** RUNTIME_TIER
**SCOPE:** Codebase-wide term replacement

- [T1] File: `/path/to/file1.py`
       Lines: [range]
       Action: Replace
       Change: "[old]" → "[new]" in [context]
       Gate: None
       
- [T2] File: `/path/to/file2.py`
       Lines: [range]
       Action: Replace
       Change: "[old]" → "[new]" in [context]
       Gate: Manual review (complex logic)
       
... [continues for all actionable files]

## TODO INDEX HASH
SHA256: GMP[N]_TODO_PLAN_v1 = T1+T2+...+TN
Checksum: N TODOs, M files, 0 new files
```

### Step 5: EXECUTE AS GMP

If `--dry-run` not specified:
1. Runs as GMP-[N] with full 7-phase protocol
2. Generates report at `/reports/GMP_Report_GMP-[N].md`
3. Updates `workflow_state.md`
4. Chains to `/ynp` for next action

---

## SCOPE DEFINITIONS

### `--scope "active"` (DEFAULT)
- ✅ Active Python/TypeScript code
- ✅ Active markdown docs (not in archive)
- ✅ Config files
- ❌ Archived code
- ❌ Historical docs

### `--scope "all"`
- ✅ Everything including archive
- ⚠️ Use with caution — may break historical context

### `--scope "docs"`
- ✅ All markdown files
- ❌ Code files
- ❌ Configs

### `--scope "archive"`
- ✅ Only archived files
- ⚠️ Rarely needed — use for cleanup operations

---

## FLAGS REFERENCE

| Flag | Description | Default |
|------|-------------|---------|
| `--term` | Search term (required) | — |
| `--replace-with` | Replacement term | — (audit only) |
| `--scope` | "all", "active", "archive", "docs" | "active" |
| `--dry-run` | Preview only, no changes | false |
| `--include-archived` | Include archived files | false |
| `--regex` | Treat term as regex | false |
| `--case-sensitive` | Case-sensitive search | false |
| `--gmp-id` | Override GMP ID | auto-increment |
| `--quick` | Skip detailed analysis, just counts | false |

---

## EXAMPLES

### Example 1: Supabase Removal (Dry Run)
```
/refactor-sweep --term "supabase" --replace-with "postgres" --dry-run
```
Shows plan without making changes.

### Example 2: N8N Cleanup (Already Done via GMP-23)
```
/refactor-sweep --term "n8n" --replace-with "L9 agent" --scope "active"
```
Replaces in active code, skips archive.

### Example 3: Vendor Rename (Full Scope)
```
/refactor-sweep --term "oldvendor" --replace-with "newvendor" --include-archived
```
Includes archived files in replacement.

### Example 4: Audit Only (No Replacement)
```
/refactor-sweep --term "deprecated_function" --dry-run
```
Just counts occurrences, no replacement defined.

### Example 5: Regex Pattern
```
/refactor-sweep --term "user_?id" --replace-with "customer_id" --regex
```
Matches `userid`, `user_id`, `userID` etc.

---

## OUTPUT FORMAT

### Dry-Run Output
```
## 🔍 REFACTOR-SWEEP: DRY RUN

### Target: "supabase" → "postgres"
### Scope: active

### Scan Results

| Category | Files | Refs | Action |
|----------|-------|------|--------|
| 🔴 Active Code | 6 | 23 | REPLACE |
| 🟠 Active Docs | 5 | 18 | REPLACE |
| 🟡 Archive | 23 | 89 | SKIP |
| ⬜ Configs | 2 | 5 | REPLACE |

**Actionable:** 13 files, 46 refs (archive excluded)

### Files to Modify

1. `core/governance/quick_fixes.py` (4 refs)
2. `core/governance/credentials_policy.py` (3 refs)
3. `memory/extractor/memory_extractor.py` (8 refs) ⚠️ Manual review
...

### Translation Map

| Old | New | Count |
|-----|-----|-------|
| supabase | postgres | 35 |
| SUPABASE_ | POSTGRES_ | 8 |
| supabaseApi | postgresApi | 3 |

---

🔒 **DRY RUN COMPLETE** — No changes made.
To execute: Run without `--dry-run` flag
```

---

## INTEGRATION

- **Chains from:** `/analyze+evaluate` (tech debt findings), `/rules` (state sync)
- **Chains to:** `/gmp` (for execution with audit trail)
- **Updates:** `workflow_state.md` with GMP entry
- **Produces:** Report at `/reports/GMP_Report_*.md`

---

## ANTI-PATTERNS

❌ **DON'T:** Replace terms in archived code (wastes time, breaks history)
❌ **DON'T:** Replace without translation map review
❌ **DON'T:** Skip dry-run for large sweeps (> 50 files)
❌ **DON'T:** Replace in historical docs (loses migration context)
❌ **DON'T:** Use `--include-archived` without specific reason

✅ **DO:** Always dry-run first for new terms
✅ **DO:** Review translation map for context-specific replacements
✅ **DO:** Mark complex files for manual review
✅ **DO:** Let it chain to /gmp for proper audit trail
✅ **DO:** Update workflow_state.md after completion

---

## COMPARISON TO OTHER COMMANDS

| Command | Use When | Scope |
|---------|----------|-------|
| `/refactor-sweep` | Deprecating terms/patterns codebase-wide | Term replacement |
| `/gmp` | Any code changes with audit trail | Single GMP scope |
| `/forge` | Fast autonomous changes (UX_TIER) | Untracked changes |
| `/analyze+evaluate` | Understanding codebase before changes | Read-only analysis |

---

## REFERENCE

- **GMP Protocol:** `/gmp` command for execution
- **Previous Sweeps:** GMP-23 (n8n sanitization)
- **Reports:** `/reports/GMP_Report_*.md`

