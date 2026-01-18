# G-CMP v2.0 — ONE-PAGE QUICK REFERENCE

**Keep this open while using Cursor. Use full template (g-cmp-v2-revised.md) for detailed instructions.**

---

## BEFORE YOU START (30 SECONDS)

1. **Identify task type:**
   - Single-file fix? → Use Profile 1
   - Multi-file refactor? → Use Profile 2
   - Docker/config issue? → Use Profile 3
   - Dependency/API? → Use Profile 4

2. **Paste full template** (from g-cmp-v2-revised.md)

3. **Choose your Context Profile**

4. **Follow phases in order** (no skipping)

---

## THE 6 PHASES (ALWAYS IN THIS ORDER)

### Phase -1: PLAN (5 min planning, 0 min coding)
- [ ] Understand the problem
- [ ] Read target files (no changes)
- [ ] Create TODO list
- [ ] Document forbidden areas
- [ ] **Output:** Locked plan

### Phase 0: VERIFY (2 min read-only)
- [ ] Confirm all assumptions
- [ ] Check baseline state
- [ ] **FAIL RULE:** If any assumption fails → STOP, re-plan
- [ ] **Output:** Baseline confirmed

### Phase 1: IMPLEMENT (10-30 min coding)
- [ ] Make surgical changes only
- [ ] No refactoring outside plan
- [ ] Each TODO item precisely
- [ ] **Output:** Changes complete

### Phase 2: ADD GUARDS (5 min)
- [ ] Add assertions/comments
- [ ] Document "why" for future devs
- [ ] **Output:** Enforcement in place

### Phase 3: ADD SAFETY (5 min)
- [ ] Add fail-fast conditions
- [ ] Improve error messages
- [ ] Validate at runtime
- [ ] **Output:** Guards in place

### Phase 4: VALIDATE (10 min testing)
- [ ] Re-read Phase -1 plan
- [ ] Run negative tests
- [ ] Run regression tests
- [ ] **FAIL RULE:** If test fails → STOP, fix it, re-run Phase 4
- [ ] **Output:** Validation passed

### Phase 5: FINAL AUDIT (5 min review)
- [ ] Check architectural integrity
- [ ] Verify no scope creep
- [ ] Confirm no loose ends
- [ ] **FAIL RULE:** If gaps found → STOP, fix, re-run Phase 5
- [ ] **Output:** System ready

---

## CRITICAL RULES (MANDATORY)

```
✓ PLAN BEFORE CODING (Phase -1)
✓ VERIFY ASSUMPTIONS (Phase 0)
✓ MATCH PLAN EXACTLY (Phase 1)
✓ NO SILENT CHANGES
✓ STOP ON FIRST FAILURE
✓ RE-RUN ENTIRE PHASE IF IT FAILS
✓ ALL 6 PHASES REQUIRED
✓ OUTPUT FINAL REPORT
```

---

## DECISION TREE

```
Does assumption fail in Phase 0?
├─ YES → STOP. Re-run Phase -1.
└─ NO → Continue to Phase 1

Does implementation match plan in Phase 1?
├─ NO → STOP. Revert. Re-run Phase 1.
└─ YES → Continue to Phase 2

Does test fail in Phase 4?
├─ YES → STOP. Fix issue. Re-run Phase 4.
└─ NO → Continue to Phase 5

Does Phase 5 find gaps?
├─ YES → STOP. Fix. Re-run Phase 5.
└─ NO → Go to DEFINITION OF DONE
```

---

## DEFINITION OF DONE (ALL 10 MUST BE TRUE)

- [ ] Phase -1 plan created and locked
- [ ] Phase 0 baseline confirmed (all assumptions ✓)
- [ ] Phase 1 implementation complete (matches plan)
- [ ] Phase 2 enforcement added (guards in place)
- [ ] Phase 3 system guards added (fail-fast works)
- [ ] Phase 4 second pass validation complete (tests pass)
- [ ] Phase 5 final sanity sweep complete (no gaps)
- [ ] All checklists passed (100%)
- [ ] No further changes needed
- [ ] System is ready for deployment

**If ALL 10 are true → Output FINAL REPORT**

---

## COMMON MISTAKES (AVOID THESE)

| ❌ WRONG | ✅ RIGHT |
|---------|----------|
| Skip Phase -1 | Always create locked plan first |
| Code without planning | Plan 5 min, code 20 min |
| Ignore failed assumptions | STOP, re-plan |
| Refactor beyond plan | Surgical changes only |
| Keep coding after failure | STOP, fix, re-run phase |
| Skip Phase 4 validation | All tests are mandatory |
| Silent changes | Document everything |
| Multiple independent iterations | Follow 6 phases sequentially |

---

## CONTEXT PROFILES (CHOOSE ONE)

### Profile 1: Single-File Code Fix
**When:** Bug in one file (NameError, TypeError, logic error)
```
MISSION OBJECTIVE:
Fix: [Error: e.g., "NameError: name 'settings' undefined"]
File: [Path: /opt/l9/api/server.py]
Lines: [XXX-YYY]
Root Cause: [Why it's broken]
```

### Profile 2: Multi-File Refactoring
**When:** Changes across 2+ files
```
MISSION OBJECTIVE:
Refactor: [What's changing]
Scope: [List all files]
Dependency: [file1 → file2 → file3]
Sequence: [Which changes first?]
```

### Profile 3: Infrastructure Fix
**When:** Docker, config, VPS deployment
```
MISSION OBJECTIVE:
Fix: [Problem: e.g., "Dockerfile build fails"]
System: [Docker / Caddy / PostgreSQL]
Symptom: [Error message]
Root Cause: [Why]
Rollback: [How to undo if needed]
```

### Profile 4: API/Dependency Management
**When:** Adding libraries, updating imports
```
MISSION OBJECTIVE:
Update: [Dependency or API change]
Reason: [Why needed]
Scope: [Which modules affected]
Dependency Map: [What calls what]
```

---

## PHASE -1 TEMPLATE (MINIMAL)

```markdown
## PHASE -1 PLAN (LOCKED)

**Problem:** [Exact description with error message]
**Root Cause:** [Why it happens]
**Solution:** [How to fix in plain language]

### Files to Modify:
- [ ] /path/to/file.py (lines XXX-YYY, function name_here)

### Forbidden Areas:
- [ ] [Specific things that MUST NOT change]

### TODO Items (In Order):
1. [ ] [Exact change 1, with line numbers]
   - Verification: [How to confirm it worked]
2. [ ] [Exact change 2, with line numbers]
   - Verification: [How to confirm it worked]

### Risks:
- [Risk A]: [Mitigation]
```

---

## PHASE 0 TEMPLATE (MINIMAL)

```markdown
## BASELINE CHECKLIST

[ ] Assumption 1: [Statement]
    - Expected: [Description]
    - Found: [Actual from code]
    - Status: ✓ PASS / ❌ FAIL

[ ] Assumption 2: [Statement]
    - Expected: [Description]
    - Found: [Actual from code]
    - Status: ✓ PASS / ❌ FAIL
```

---

## FINAL REPORT CHECKLIST

After all phases complete:

```
✓ EXECUTION REPORT
- Task: [Brief description]
- Status: COMPLETE
- Phases: All 6 executed
- Files Modified: [List]
- Changes Made: [Summary]
- Tests: All passed ✓
- Ready for deployment: YES ✓
```

---

## KEYBOARD SHORTCUTS (CURSOR)

| Action | How |
|--------|-----|
| Paste template | Cmd+V (have g-cmp-v2-revised.md open in another tab) |
| Toggle comment | Cmd+/ |
| Find/Replace | Cmd+H |
| Go to line | Cmd+G |
| Search file | Cmd+F |

---

## WHEN STUCK

| Problem | Solution |
|---------|----------|
| Don't know what to change | Re-read Phase -1 plan |
| Assumption seems wrong | STOP. Re-run Phase -1 completely |
| Want to add something extra | Document it. Re-run Phase -1 for approval |
| Test is failing | Fix it. Re-run ENTIRE Phase 4 |
| Not sure if you're done | Check Definition of Done (all 10 must be true) |

---

## TEMPLATE LOCATIONS

- **Full template:** `~/cursor-g-cmp.md` or `g-cmp-v2-revised.md`
- **This quick ref:** Keep open in Cursor split pane
- **Copy-paste:** Use full template, fill in [BRACKETS]

---

**Remember:** Plan > Code > Verify > Lock. No exceptions. No shortcuts. Determinism guaranteed.

**Version:** 2.0 | **Last Updated:** 2025-12-21 | **Status:** Production Ready