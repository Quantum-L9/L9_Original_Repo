# 🎯 G-CMP v2.0 — EXECUTIVE CHECKLIST (PRINT THIS)

---

## BEFORE YOU START

- [ ] Problem is clear (I understand what's broken)
- [ ] Affected files identified (exact paths)
- [ ] Success criteria defined (how to know it's fixed)
- [ ] Template open in Cursor (g-cmp-v2-revised.md or L9 variant)
- [ ] Context profile chosen (Profile 1/2/3/4)
- [ ] Quickref visible (g-cmp-quickref.md in tab)

---

## PHASE -1: PLAN (5 min)

- [ ] Understand problem completely
- [ ] Read target files (NO CHANGES YET)
- [ ] Identify exact lines/functions
- [ ] Create TODO list (atomic items only)
- [ ] Document forbidden areas
- [ ] **Output:** Locked plan
- [ ] **Checklist:** Every TODO is observable and testable
- [ ] **Checkpoint:** Plan is immutable; get approval before Phase 0

---

## PHASE 0: BASELINE (2 min)

- [ ] Read all target files again (verify state)
- [ ] Confirm assumption 1 ✓ PASS / ❌ FAIL
- [ ] Confirm assumption 2 ✓ PASS / ❌ FAIL
- [ ] Confirm assumption 3 ✓ PASS / ❌ FAIL
- [ ] Document actual baseline state
- [ ] **Output:** Baseline confirmed
- [ ] **FAIL RULE:** If any fails → STOP, re-run Phase -1
- [ ] **Checkpoint:** Cannot proceed without all ✓ PASS

---

## PHASE 1: IMPLEMENT (15 min)

- [ ] TODO Item 1: Complete (verified)
- [ ] TODO Item 2: Complete (verified)
- [ ] TODO Item 3: Complete (verified)
- [ ] All changes match plan exactly
- [ ] No forbidden areas modified
- [ ] File structure preserved
- [ ] No refactoring beyond plan
- [ ] **Output:** Changes complete
- [ ] **Checklist:** Every TODO done, nothing extra
- [ ] **FAIL RULE:** Doesn't match plan → STOP, revert, re-run Phase 1

---

## PHASE 2: ENFORCEMENT (5 min)

- [ ] Add assertions/comments
- [ ] Document "why" for future devs
- [ ] Guards prevent regression
- [ ] Correct behavior is enforced
- [ ] **Output:** Enforcement in place
- [ ] **Checklist:** Every fix has a guard
- [ ] **FAIL RULE:** Guard is weak/missing → STOP, add proper guards

---

## PHASE 3: SAFETY (5 min)

- [ ] Add fail-fast conditions
- [ ] Improve error messages
- [ ] Validate inputs at runtime
- [ ] Weak inputs fail predictably
- [ ] System can't enter bad state
- [ ] **Output:** Guards in place
- [ ] **Checklist:** All guards are meaningful and actionable
- [ ] **FAIL RULE:** Guard is missing → STOP, add it

---

## PHASE 4: VALIDATE (10 min)

- [ ] Re-read Phase -1 plan (matches exactly)
- [ ] Run negative test (broken code IS broken) ✓
- [ ] Run regression test (fix works) ✓
- [ ] Run edge case tests ✓
- [ ] No new bugs detected ✓
- [ ] **Output:** Validation passed
- [ ] **Checklist:** All tests passed, 100%
- [ ] **FAIL RULE:** Test fails → STOP, fix, re-run Phase 4 (entire phase)

---

## PHASE 5: FINAL AUDIT (5 min)

- [ ] Check architectural integrity
- [ ] Verify no scope creep
- [ ] Confirm no loose ends
- [ ] Consistency maintained
- [ ] System ready for deployment
- [ ] **Output:** System ready
- [ ] **Checklist:** No gaps found
- [ ] **FAIL RULE:** Gaps exist → STOP, fix, re-run Phase 5

---

## DEFINITION OF DONE (ALL 10 REQUIRED)

✓ Phase -1 plan created and LOCKED
✓ Phase 0 baseline confirmed (all ✓)
✓ Phase 1 implementation COMPLETE (matches plan)
✓ Phase 2 enforcement ADDED (guards in place)
✓ Phase 3 system guards ADDED (fail-fast works)
✓ Phase 4 validation COMPLETE (all tests pass)
✓ Phase 5 final audit COMPLETE (no gaps)
✓ All checklists PASSED (100%)
✓ No further changes NEEDED
✓ System is READY for deployment

**If all 10 ✓ → Output FINAL REPORT**

---

## FINAL REPORT CHECKLIST

- [ ] Task description clear
- [ ] Status: COMPLETE
- [ ] Files modified listed
- [ ] Changes summarized
- [ ] All phases documented
- [ ] All checklists passed
- [ ] Verification instructions provided
- [ ] Deployment steps clear
- [ ] Explicit "EXECUTION COMPLETE ✓" declaration
- [ ] Ready for sharing with team

---

## CRITICAL RULES (NON-NEGOTIABLE)

```
1. PLAN BEFORE CODING
2. VERIFY ASSUMPTIONS FIRST
3. MATCH PLAN EXACTLY
4. FAIL FAST (NO WORKAROUNDS)
5. ALL PHASES MANDATORY
6. RE-RUN ENTIRE PHASE IF IT FAILS
7. EXPLICIT FINAL REPORT REQUIRED
8. DEFINITION OF DONE MUST BE 100% TRUE
```

---

## WHEN STUCK

| Problem | Action |
|---------|--------|
| Not sure what to change | Go back to Phase -1 plan, re-read |
| Assumption failed | STOP. Re-run Phase -1. Don't guess. |
| Code doesn't match plan | STOP. Revert. Re-run Phase 1. |
| Test failing | STOP. Fix. Re-run entire Phase 4. |
| Phase 5 found gaps | STOP. Fix. Re-run Phase 5. |
| Want to add extra feature | STOP. Document it. Re-run Phase -1. |
| Unsure if you're done | Check Definition of Done. All 10? |

---

## QUICK COMMANDS (L9)

```bash
# Copy to VPS
scp ~/file.py admin@157.180.73.53:/opt/l9/path/file.py

# Restart service
ssh admin@157.180.73.53 "cd /opt/l9 && sudo docker compose restart l9-api"

# Check health
curl -sS http://127.0.0.1:8000/health && echo ""

# View logs
sudo docker compose logs l9-api --tail 50

# Full rebuild
cd /opt/l9 && sudo docker compose down && \
sudo docker image rm l9-api l9-postgres --force 2>/dev/null || true && \
sudo docker compose build --no-cache && \
sudo docker compose up -d && sleep 30 && curl -sS http://127.0.0.1:8000/health
```

---

## FILE LOCATIONS

- **Full template:** `g-cmp-v2-revised.md` (keep in Cursor tabs)
- **Quick ref:** `g-cmp-quickref.md` (keep visible)
- **L9 variant:** `g-cmp-l9-special.md` (for L9 tasks)
- **This checklist:** Print & bookmark (or keep as tab)
- **Implementation guide:** `g-cmp-implementation.md` (reference)

---

## TIME ESTIMATES

| Phase | Time | Notes |
|-------|------|-------|
| -1 (Plan) | 5 min | Don't rush; better planning = fewer mistakes |
| 0 (Verify) | 2 min | Quick read-only validation |
| 1 (Code) | 15 min | Surgical changes only |
| 2 (Guard) | 5 min | Add comments & assertions |
| 3 (Safety) | 5 min | Fail-fast conditions |
| 4 (Test) | 10 min | Comprehensive validation |
| 5 (Audit) | 5 min | Final review |
| **Total** | **47 min** | From problem to production-ready |

---

## SIGN-OFF TEMPLATE

```
EXECUTION COMPLETE ✓

Task: [Brief description]
Status: COMPLETE
All phases executed in order
All checklists passed (100%)
Definition of Done: [All 10 items ✓]

Files changed: [List]
Ready for deployment: YES ✓

Date: [Today]
Signature: [Your name]
```

---

## REMEMBER

✓ PLAN BEFORE CODING
✓ PHASES IN ORDER (no skipping)
✓ ALL 6 PHASES MANDATORY
✓ FAIL-FAST (no workarounds)
✓ RE-RUN ENTIRE PHASE IF IT FAILS
✓ OUTPUT FINAL REPORT
✓ DETERMINISM GUARANTEED

---

**G-CMP v2.0 | Created 2025-12-21 | Status: Production Ready**

Print this. Keep it visible. Follow it exactly. Success guaranteed.