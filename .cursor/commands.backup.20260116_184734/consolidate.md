---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "7.0.0"
component_id: "CMD-CONSOLIDATE-001"
component_name: "Consolidate - File Organization"
layer: "commands"
domain: "organization"
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
name: consolidate
description: "L9-native file consolidation — organize, dedupe, rename, archive with governance"
memory_inject: true            # INJECT: Search VPS memory for preferences/lessons before execution
before_chain: extract-chat   # EXTRACT: Write learnings to VPS memory
auto_chain: ynp
---

# === L9 CONSOLIDATE: File Organization & Cleanup ===
# Cursor Slash Command: /consolidate
# Version: 7.0.0 (L9-native)
# Updated: 2026-01-01

---

## ⛓️ AUTO-CHAINS TO /ynp

After consolidation, **automatically runs /ynp** to recommend next cleanup, verification, or proceed to other work.

---

## WHAT IT DOES

**Comprehensive file organization and cleanup:**

1. **Duplicate Detection** — Find exact and near-duplicate files
2. **Orphan Identification** — Files not imported/referenced anywhere
3. **Naming Standardization** — kebab-case, consistent conventions
4. **Archive Management** — Move deprecated files safely
5. **Structure Optimization** — Merge underutilized folders

**Key principle:** Clean structure = fast development. Remove noise, keep signal.

---

## ⚠️ KERNEL_TIER REDIRECT

**If consolidation affects KERNEL_TIER files, STOP and redirect to /gmp:**

```
PROTECTED FILES (redirect to /gmp):
├── core/kernels/kernel_loader.py
├── core/agents/executor.py
├── memory/substrate_service.py
├── runtime/websocket_orchestrator.py
├── docker-compose.yml
└── Any file in kernels/ directory

IF ANY target in PROTECTED FILES:
  → "⚠️ KERNEL_TIER detected. Redirecting to /gmp for controlled consolidation."
  → Generate GMP TODO plan for consolidation actions
  → Execute via /gmp protocol (Phases 0-6)
```

---

## EXECUTION PROTOCOL

### Step 0: STATE_SYNC + TIER CHECK

```
1. Read workflow_state.md
2. Note current PHASE and priority
3. Check if consolidation is in active scope
4. **TIER CHECK:** Classify all target files
   - If ANY target is KERNEL_TIER → REDIRECT to /gmp
   - Else → proceed with /consolidate
```

### Step 1: ANALYSIS PHASE

Scan target directory and identify:

```
ANALYSIS TARGETS:
├── Duplicates: Files with identical or 90%+ similar content
├── Near-Duplicates: Files with same purpose, different versions
├── Orphans: Files not imported/referenced anywhere
├── Naming Issues: Non-standard naming (Title_Case, spaces, etc.)
├── Empty Folders: Directories with no useful content
├── Misplaced Files: Files in wrong directory per L9 conventions
└── Missing Files: Expected files that don't exist
```

### Step 2: CLASSIFICATION

For each issue found, classify:

| Category | Action | Risk Level |
|----------|--------|------------|
| **Exact Duplicate** | Archive older version | 🟢 Low |
| **Near-Duplicate** | Identify canonical, archive others | 🟡 Medium |
| **Orphan (unused)** | Verify truly unused, then archive | 🟡 Medium |
| **Naming Issue** | Rename to kebab-case | 🟢 Low |
| **Empty Folder** | Delete | 🟢 Low |
| **Misplaced** | Move to correct location | 🟡 Medium |

### Step 3: CONSOLIDATION PLAN

Generate phased execution plan:

```markdown
## 📋 CONSOLIDATION PLAN

### Phase 1: High-Confidence Moves (Immediate)
- Move cleanup scripts to utilities
- Consolidate duplicate index files
- Delete empty folders

### Phase 2: Deduplication (High Priority)
- Identify canonical versions
- Move duplicates to DEPRECATED with cross-references
- Update imports if needed

### Phase 3: Renaming (Medium Priority)
- Rename Title_Case files to kebab-case
- Update all cross-references
- Verify no broken links

### Phase 4: Archive (Lower Priority)
- Move orphan files to archive/deprecated/
- Add deprecation headers
- Document removal date

### Phase 5: Structure Optimization
- Merge underutilized folders
- Create missing __init__.py files
- Add README where missing
```

### Step 4: EXECUTION

Execute each phase with:
- **Pre-action check** — Verify target exists
- **Action** — Move/rename/delete
- **Post-action verify** — Confirm success
- **Rollback spec** — How to undo if needed

### Step 5: REPORT

Generate consolidation report with:
- Files moved/renamed/deleted
- Cross-references updated
- Verification results
- Remaining issues

---

## L9 CONVENTIONS

### File Naming
```
✅ kebab-case: my-module-name.py
❌ Title_Case: My_Module_Name.py
❌ camelCase: myModuleName.py
❌ spaces: my module name.py
```

### Directory Structure
```
l9/
├── core/           # Core runtime (agents, kernels, tools)
├── api/            # FastAPI routes and adapters
├── memory/         # Memory substrate
├── orchestration/  # Task routing and planning
├── runtime/        # Background tasks, queues
├── services/       # Domain-specific services
├── tests/          # All tests (mirrors source structure)
├── archive/        # Deprecated code (date-stamped)
│   └── deprecated/ # Old implementations
├── docs/           # Documentation
└── scripts/        # Utility scripts
```

### Archive Pattern
```
# When archiving:
1. Move to archive/deprecated/
2. Add header:
   """
   DEPRECATED: [date]
   Reason: [why deprecated]
   Replaced by: [new file path]
   Remove after: [date + 90 days]
   """
3. Keep for 90 days minimum
4. Remove after grace period
```

---

## OUTPUT FORMAT

```markdown
## 🧹 CONSOLIDATION REPORT

### 📊 Summary
- Files scanned: [count]
- Issues found: [count]
- Actions taken: [count]
- Remaining: [count]

### ✅ Completed Actions

| Action | Source | Destination | Type |
|--------|--------|-------------|------|
| Move | old/path/file.py | archive/deprecated/ | Duplicate |
| Rename | Old_Name.py | old-name.py | Naming |
| Delete | empty_folder/ | — | Empty |

### 🔗 Cross-References Updated

| File | Old Import | New Import |
|------|------------|------------|
| api/server.py | from old.path import X | from new.path import X |

### ⚠️ Requires Manual Review

| File | Issue | Why Manual |
|------|-------|------------|
| core/agents/executor.py | Orphan candidate | KERNEL_TIER, verify before archive |

### 🎯 YNP (Your Next Play)
**Primary:** [Next consolidation action or proceed]
**Alternates:** [1-2 alternatives]
```

---

## USAGE

### Full Workspace Consolidation
```
/consolidate

Scans entire workspace, generates full plan.
```

### Target Directory
```
/consolidate @docs/
/consolidate @core/tools/

Focuses on specific area.
```

### Specific Phase
```
/consolidate phase1
/consolidate phase2 @core/

Executes only specified phase.
```

### Dry Run
```
/consolidate --dry-run

Shows what would happen without making changes.
```

### Duplicates Only
```
/consolidate duplicates-only

Only finds and handles duplicates.
```

---

## CONSOLIDATION PHASES

### Phase 1: High-Confidence (Safe)
- Move cleanup scripts to scripts/
- Consolidate duplicate index files
- Move duplicate style guides to archive/
- Delete empty folders

### Phase 2: Deduplication (Review)
- Identify canonical version of each duplicate set
- Move non-canonical to archive/deprecated/
- Add cross-reference in archived file
- Update imports in dependent files

### Phase 3: Renaming (Careful)
- Rename Title_Case → kebab-case
- Update all import statements
- Verify no broken links
- Run tests after rename

### Phase 4: Header Standardization
- Audit files missing domain field
- Standardize domain values
- Align version numbers
- Update timestamps

### Phase 5: Structure Optimization
- Review folder structure
- Merge underutilized folders (< 3 files)
- Create missing README files
- Add __init__.py where needed

---

## SAFETY RULES

### Protected from Consolidation (Auto-Redirect to /gmp)
- **KERNEL_TIER files** → Automatically redirect to /gmp
  - core/kernels/kernel_loader.py
  - core/agents/executor.py
  - memory/substrate_service.py
  - runtime/websocket_orchestrator.py
  - docker-compose.yml
  - Any file in kernels/ directory
- Files with active references in workflow_state.md
- Recently modified files (< 7 days)
- Files in active GMP scope

### Require Manual Review
- Files with 5+ dependents
- Files modified in last 30 days
- Anything in core/agents/executor.py or similar

### Auto-Safe Actions
- Empty folder deletion
- Naming standardization
- Moving to archive/ with cross-reference
- Adding missing __init__.py

---

## INTEGRATION

- **Chains from:** `/analyze+evaluate` (identifies cleanup needs)
- **Chains to:** `/ynp` (next action)
- **Updates:** `workflow_state.md` with consolidation results
- **Respects:** Protected file list, tier classifications

---

## ANTI-PATTERNS

❌ **DON'T:** Consolidate KERNEL_TIER files without /gmp
❌ **DON'T:** Delete files without archiving first
❌ **DON'T:** Rename files without updating imports
❌ **DON'T:** Remove files with active dependents
❌ **DON'T:** Skip the dry-run for large consolidations

✅ **DO:** Start with --dry-run
✅ **DO:** Execute in phases (1 → 2 → 3 → 4 → 5)
✅ **DO:** Update cross-references after moves
✅ **DO:** Archive rather than delete
✅ **DO:** Run tests after consolidation

---

## EXAMPLES

### Example 1: Find Duplicates
```
/consolidate duplicates-only @core/

CONSOLIDATION REPORT:

📊 Summary
- Files scanned: 45
- Duplicates found: 3
- Near-duplicates: 2

Exact Duplicates:
1. core/tools/registry.py.bak → Archive (duplicate of registry.py)
2. core/agents/base.py.old → Archive (duplicate of base_agent.py)

Near-Duplicates (90%+ similar):
1. core/schemas/task.py vs core/schemas/task_v2.py
   → Recommend: Keep task_v2.py as canonical

🎯 YNP: /consolidate phase2 to execute deduplication
```

### Example 2: Full Cleanup
```
/consolidate @docs/

CONSOLIDATION REPORT:

📊 Summary
- Files scanned: 120
- Issues found: 15
- Actions taken: 12
- Remaining: 3 (require review)

✅ Phase 1 Complete:
- Deleted 3 empty folders
- Renamed 5 files to kebab-case
- Moved 4 duplicates to archive/

⚠️ Requires Review:
- docs/API_GAP_ANALYSIS.md (orphan candidate)
- docs/MEMO.md (no references found)

🎯 YNP: Review orphan candidates, then /consolidate phase3
```
