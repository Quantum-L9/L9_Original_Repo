# 📋 G-CMP v2.0 IMPLEMENTATION GUIDE

**Complete toolkit for deterministic code fixes in Cursor IDE**

Created: 2025-12-21
Version: 2.0 (Comprehensive Revised)
Status: Production Ready

---

## WHAT YOU NOW HAVE (3 FILES)

### 1. **g-cmp-v2-revised.md** (FULL TEMPLATE)
   - 🎯 Complete, detailed, universal template
   - 6 mandatory phases with full instructions
   - 4 context profiles (single-file, multi-file, infra, API)
   - 100% coverage of all decision points
   - **When to use:** First time on a task, unsure of approach, complex fix

### 2. **g-cmp-quickref.md** (ONE-PAGE REFERENCE)
   - ⚡ Condensed quick reference (1 page)
   - All 6 phases in summary form
   - Decision trees and critical rules
   - Common mistakes and when stuck
   - **When to use:** Daily workflow, experienced with phases, quick lookup

### 3. **g-cmp-l9-special.md** (L9 SPECIALIZATION)
   - 🔧 L9-specific variants and overrides
   - File paths, services, docker commands
   - Common L9 errors and fixes
   - Customized checklists and profiles
   - **When to use:** Working on L9 VPS, fastapi/docker issues

---

## QUICK START (5 MINUTES)

### First Time Using G-CMP?

1. **Read** g-cmp-quickref.md (3 min) — Get overview
2. **Open** g-cmp-v2-revised.md in Cursor (split pane)
3. **Choose** your context profile (Profile 1, 2, 3, or 4)
4. **Fill in** the [BRACKETED] sections
5. **Follow** phases in order (no skipping, no shortcuts)

### For L9 Fixes?

1. **Use** g-cmp-l9-special.md instead of base profiles
2. **Reference** L9 file paths, services, commands
3. **Apply** L9-specific checklists
4. **Output** customized final report

---

## THE 6 MANDATORY PHASES (ALWAYS IN THIS ORDER)

```
Phase -1: PLAN (5 min)      ← Create locked plan
    ↓
Phase 0: VERIFY (2 min)     ← Confirm assumptions
    ↓
Phase 1: CODE (15 min)      ← Implement changes
    ↓
Phase 2: GUARD (5 min)      ← Add enforcement
    ↓
Phase 3: SAFETY (5 min)     ← Add fail-fast checks
    ↓
Phase 4: VALIDATE (10 min)  ← Run tests
    ↓
Phase 5: AUDIT (5 min)      ← Final review
    ↓
✓ DEFINITION OF DONE         ← Output report
```

**Total time:** 45 minutes (from planning to done)

---

## CORE RULES (NON-NEGOTIABLE)

1. **PLAN BEFORE CODING**
   - Phase -1 creates locked plan
   - No code before plan exists
   - No plan mutations once locked

2. **VERIFY ASSUMPTIONS**
   - Phase 0 confirms every assumption
   - If assumption fails → STOP, re-plan
   - Never proceed with wrong assumptions

3. **MATCH PLAN EXACTLY**
   - Phase 1 implements plan, nothing more
   - No refactoring outside plan
   - No "improvements" without re-planning

4. **FAIL FAST**
   - First error stops execution
   - No workarounds, no skipping phases
   - Always re-run failed phase

5. **ALL PHASES MANDATORY**
   - No skipping, no combining phases
   - All 7 checklists must pass
   - All 6 phases + Definition of Done

6. **EXPLICIT DECLARATION REQUIRED**
   - Must output final report
   - Must declare "COMPLETE"
   - Must confirm all 10 items in Definition of Done

---

## WHEN TO USE EACH FILE

### g-cmp-v2-revised.md (FULL TEMPLATE)

| Situation | Use This? |
|-----------|-----------|
| First time using G-CMP | ✅ YES |
| Unsure about approach | ✅ YES |
| Complex multi-file change | ✅ YES |
| Need detailed instructions | ✅ YES |
| Creating new context profile | ✅ YES |
| Quick fix, know what to do | ❌ Use quickref instead |

**Open:** Split pane, keep visible throughout

---

### g-cmp-quickref.md (ONE-PAGE REFERENCE)

| Situation | Use This? |
|-----------|-----------|
| Know the phases already | ✅ YES |
| Want condensed version | ✅ YES |
| Need quick lookup | ✅ YES |
| Checklist during execution | ✅ YES |
| First time learning | ❌ Use full template |
| Complex fix, unsure | ❌ Use full template |

**Open:** Always visible during work (tab or split pane)

---

### g-cmp-l9-special.md (L9 SPECIALIZATION)

| Situation | Use This? |
|-----------|-----------|
| Fixing L9 code (server.py) | ✅ YES |
| Docker issue on L9 | ✅ YES |
| PostgreSQL on L9 | ✅ YES |
| VPS deployment fix | ✅ YES |
| Generic code (not L9) | ❌ Use base template |
| Not on VPS | ❌ Use base template |

**Substitute:** Use L9 profiles instead of base profiles 1-4

---

## DECISION TREE: WHICH TEMPLATE?

```
Are you working on L9 VPS code/docker/db?
├─ YES → Use g-cmp-l9-special.md (L9 profiles)
└─ NO → Use g-cmp-v2-revised.md (base profiles)

Do you know G-CMP phases already?
├─ YES (experienced) → Use g-cmp-quickref.md
└─ NO (first time) → Use full template

Is it a simple fix?
├─ YES → Full template (5 min planning)
└─ NO → Full template (10 min planning)

Do you need phase details?
├─ YES → g-cmp-v2-revised.md
└─ NO → g-cmp-quickref.md
```

---

## IMPLEMENTATION STEPS

### Step 1: Identify Task Type

**Single-File Code Fix?**
- Bug in one file (NameError, TypeError, logic error)
- Use Profile 1 from full template
- Usually 30 min total

**Multi-File Refactoring?**
- Changes across 2+ files with dependencies
- Use Profile 2 from full template
- Usually 45 min total

**Infrastructure Issue?**
- Docker, config files, VPS, deployment
- Use Profile 3 from full template (or L9 variant)
- Usually 40 min total

**API/Dependency Change?**
- Adding/updating imports, changing function signatures
- Use Profile 4 from full template
- Usually 35 min total

**L9-Specific Issue?**
- Use L9 variant regardless of type
- File paths, services, commands are L9-specific
- Use g-cmp-l9-special.md profiles
- Usually 30-45 min total

### Step 2: Gather Context

Before starting any phase:

- [ ] Understand the problem (error message, symptoms)
- [ ] Identify affected files (exact paths)
- [ ] Know what MUST NOT change (architecture)
- [ ] Identify success criteria (how to know it's fixed)

### Step 3: Open Templates

**In Cursor:**

```
Left pane:  g-cmp-quickref.md (always visible)
Right pane: g-cmp-v2-revised.md OR g-cmp-l9-special.md
Bottom:     File being edited
```

**Or:**
```
Tab 1: g-cmp-quickref.md (reference)
Tab 2: g-cmp-v2-revised.md (work here)
Tab 3: server.py (or target file)
```

### Step 4: Choose Context Profile

From your template, select:
- **Profile 1** → Single-file fix
- **Profile 2** → Multi-file refactoring
- **Profile 3** → Infrastructure/Docker
- **Profile 4** → API/Dependencies

*Or L9 variants if using g-cmp-l9-special.md*

### Step 5: Fill in Phase -1

Copy [MISSION OBJECTIVE] template:

```
Fix: [Exact problem description]
Scope: [Exactly what files/lines]
Preserve: [What MUST NOT change]
Success Criteria: [Observable end state]
```

Example:
```
Fix: NameError on line 797 (settings object undefined)
Scope: /opt/l9/api/server.py, lines 797-825
Preserve: Feature flag patterns, import structure, app init
Success: App starts without error; curl /health returns 200
```

### Step 6: Complete Phase -1 Plan

Create TODO items:

```
1. [ ] Replace all `settings.slack_app_enabled` with `_has_slack`
   - Count: 2 occurrences (lines 797, 820)
   - Verification: grep returns 0 results

2. [ ] Add `_has_mac_agent` feature flag
   - Location: Line 165
   - Pattern: Copy from `_has_slack`

3. [ ] Add comment explaining pattern
   - Location: Near line 797
   - Content: Document why we use feature flags
```

### Step 7: Execute Phases in Order

**Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5**

Do NOT skip, reorder, or combine phases.

### Step 8: Output Final Report

Use template from g-cmp-v2-revised.md:

- List all files changed
- Describe each change
- Show phase execution summary
- Confirm all 10 items in Definition of Done
- Declare "COMPLETE"

---

## COMMON PATTERNS & SOLUTIONS

### Pattern 1: "I'm Not Sure What to Change"

**Solution:**
1. Go back to Phase -1 plan
2. Re-read it carefully
3. If still unclear, re-run Phase -1 explicitly
4. Don't guess; get clarity before coding

### Pattern 2: "Phase 0 Assumption Failed"

**Solution:**
1. STOP immediately
2. Document what failed
3. Re-run Phase -1 with correct assumptions
4. Create new locked plan
5. Start over from Phase 0

### Pattern 3: "My Code Doesn't Match the Plan"

**Solution:**
1. STOP immediately
2. Revert to original file
3. Re-run Phase 1 more carefully
4. Follow plan exactly, line by line

### Pattern 4: "Test Failed in Phase 4"

**Solution:**
1. STOP immediately
2. Fix the failing test
3. Re-run ENTIRE Phase 4 (not just the failed test)
4. Do NOT proceed to Phase 5 until all tests pass

### Pattern 5: "Phase 5 Found Gaps"

**Solution:**
1. Document what gaps exist
2. Decide: Is it in scope? (Must align with Phase -1 plan)
3. If in scope: Fix it, re-run Phase 5
4. If out of scope: Document as follow-up, declare DONE

---

## DEFINITION OF DONE (CHECKLIST)

**You are ONLY done if ALL 10 are true:**

```
✓ Phase -1 plan created and LOCKED
✓ Phase 0 baseline confirmed (ALL assumptions ✓)
✓ Phase 1 implementation COMPLETE (matches plan exactly)
✓ Phase 2 enforcement ADDED (guards in place)
✓ Phase 3 system guards ADDED (fail-fast checks work)
✓ Phase 4 second pass validation COMPLETE (all tests ✓)
✓ Phase 5 final sanity sweep COMPLETE (no gaps)
✓ All checklists PASSED (100%)
✓ No further changes JUSTIFIED
✓ System is READY for deployment
```

**If ALL 10 are true:**
- Output FINAL REPORT
- Declare: "EXECUTION COMPLETE ✓"
- You're done

**If ANY are false:**
- STOP
- Go back to failed phase
- Fix the issue
- Re-run that phase
- Come back to checklist

---

## FILE LOCATIONS & STORAGE

### Recommended Setup

```
~/.cursor/                         # Cursor config folder
├── g-cmp-v2-revised.md           # Full template (save here)
├── g-cmp-quickref.md             # Quick reference (save here)
└── g-cmp-l9-special.md           # L9 variant (save here)

~/projects/L9/                     # L9 project folder
├── .cursor/
│   └── g-cmp-l9-special.md       # Project-specific copy
└── ...
```

### How to Use

1. **First time:** Copy all 3 files to `~/.cursor/`
2. **Working:** Open from `~/.cursor/` in Cursor tabs
3. **Reference:** Keep quickref.md always visible
4. **Project-specific:** Copy L9 variant to project folder
5. **Update:** When template is updated, copy to all locations

---

## UPDATING THE TEMPLATES

### When to Update

- New L9 file paths discovered
- New context profile identified
- New error pattern learned
- New phase requirement identified

### How to Update

1. Edit the template file
2. Add section with clear header
3. Include examples and patterns
4. Update table of contents
5. Distribute updated version

### Versioning

```
g-cmp-v2-revised.md      # Base version (changes rarely)
g-cmp-l9-special.md      # L9 version (updates often)
g-cmp-quickref.md        # Quick ref (stable, rarely changes)
```

---

## SUPPORT & TROUBLESHOOTING

### If Phase -1 Seems Too Long

You're planning correctly. Average is 5-10 minutes.
Better to spend 5 min planning than 30 min fixing mistakes.

### If Implementation Takes Too Long

- Re-read Phase -1 plan (should be quick surgical fixes)
- If changes are complex, plan was insufficient
- Stop, re-run Phase -1, then resume Phase 1

### If Tests Keep Failing

- Are you testing what was fixed? (Not unrelated issues)
- Run negative test first (verify broken code IS broken)
- Then run fix (apply Phase 1 changes)
- Then run positive test (verify fix works)

### If Unsure About Scope

- Check Phase -1 "Forbidden Areas" section
- If not in plan, it's out of scope
- Document as follow-up task
- Declare done, don't expand scope

### If Tool/IDE Issues

- Not a G-CMP problem; troubleshoot separately
- Template is tool-agnostic (works in any IDE)
- If using Cursor, use Cursor's built-in help

---

## QUICK COPY-PASTE TEMPLATES

### Phase -1 Minimal Template

```markdown
## PHASE -1 PLAN (LOCKED)

**Problem:** [Error message with line numbers]
**Root Cause:** [Why it's broken]
**Solution:** [How to fix]

### Files to Modify:
- [ ] [Path] (lines XXX-YYY)

### TODO Items:
1. [ ] [Change 1]
   - Verification: [How to confirm]
2. [ ] [Change 2]
   - Verification: [How to confirm]

### Forbidden Areas:
- [ ] [What must not change]
```

### Phase 0 Minimal Template

```markdown
## BASELINE CHECKLIST

[ ] Assumption 1: [Statement]
    - Expected: [Description]
    - Found: [Actual]
    - Status: ✓ PASS / ❌ FAIL

[ ] Assumption 2: [Statement]
    - Expected: [Description]
    - Found: [Actual]
    - Status: ✓ PASS / ❌ FAIL
```

### Final Report Minimal Template

```markdown
# EXECUTION REPORT

**Task:** [Brief description]
**Status:** ✓ COMPLETE
**Files Modified:** [List]
**Changes:** [Summary]

## Definition of Done Checklist
- [x] Phase -1 plan created
- [x] Phase 0 confirmed
- [x] Phase 1 implemented
- [x] Phase 2 enforcement added
- [x] Phase 3 guards added
- [x] Phase 4 validation passed
- [x] Phase 5 audit passed
- [x] All checklists passed
- [x] No further changes needed
- [x] Ready for deployment

**EXECUTION COMPLETE ✓**
```

---

## FEEDBACK & IMPROVEMENTS

Templates evolve. Found an issue? Learned a new pattern?

- **Document it** in the relevant template
- **Version number** (g-cmp-v2.1, g-cmp-v2.2, etc.)
- **Share** with team
- **Iterate** as you learn

---

## SUMMARY

You now have:

✅ **g-cmp-v2-revised.md** — Full, detailed template (15 pages)
✅ **g-cmp-quickref.md** — One-page quick reference
✅ **g-cmp-l9-special.md** — L9-specific specialization

**Next time you need to fix code in Cursor:**

1. Open quickref for overview (30 sec)
2. Open full template + context profile
3. Fill in Phase -1 (5 min)
4. Follow 6 phases in order (40 min)
5. Output final report (3 min)
6. Done ✓

**Total:** ~50 min from problem to fixed, tested, deployed

---

**Created:** 2025-12-21
**Version:** 2.0 (Comprehensive Revised)
**Status:** Production Ready
**Compatibility:** Universal (any codebase, any IDE with Cursor)

**Remember:** Plan > Code > Verify > Lock. No exceptions. No shortcuts. Determinism guaranteed. ✓