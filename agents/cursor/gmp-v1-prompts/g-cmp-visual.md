# 🎨 G-CMP v2.0 — VISUAL QUICK REFERENCE

**One-page visual guide to the entire system**

---

## YOUR TOOLKIT (6 FILES)

```
┌─────────────────────────────────────────────────────────────┐
│                    G-CMP v2.0 TOOLKIT                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1️⃣  g-cmp-v2-revised.md                                     │
│      ├─ Full, detailed template                             │
│      ├─ 6 phases + 4 profiles                               │
│      └─ Use for: Complex fixes, first time                  │
│                                                               │
│  2️⃣  g-cmp-l9-special.md                                     │
│      ├─ L9-specific file paths & commands                  │
│      ├─ 4 L9 context profiles                               │
│      └─ Use for: L9 VPS, Docker, PostgreSQL                │
│                                                               │
│  3️⃣  g-cmp-quickref.md                                       │
│      ├─ One-page condensed version                          │
│      ├─ All 6 phases at-a-glance                            │
│      └─ Use for: Daily reference, quick lookup              │
│                                                               │
│  4️⃣  g-cmp-implementation.md                                 │
│      ├─ Setup guide & how to use all files                 │
│      ├─ Quick start (5 min)                                 │
│      └─ Use for: Initial setup, understanding              │
│                                                               │
│  5️⃣  g-cmp-checklist.md                                      │
│      ├─ Executive checklist (per-phase)                    │
│      ├─ Print & keep visible                               │
│      └─ Use for: Progress tracking, verification           │
│                                                               │
│  6️⃣  README-INDEX.md (this directory index)                 │
│      ├─ Overview of entire system                          │
│      ├─ File selection guide                               │
│      └─ Use for: First-time orientation                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## THE 6 PHASES (ALWAYS IN ORDER)

```
TASK RECEIVED
    │
    ↓
┌─────────────────────────────────────────┐
│ Phase -1: PLAN (5 min)                  │
│ ✓ Read problem & target files           │
│ ✓ Create locked TODO list               │
│ ✓ Document forbidden areas              │
│ Output: Locked plan                     │
└─────────────────────────────────────────┘
    │
    ↓ (STOP if plan is unclear)
┌─────────────────────────────────────────┐
│ Phase 0: VERIFY (2 min)                 │
│ ✓ Confirm all assumptions               │
│ ✓ Check baseline state                  │
│ ✓ Document actual findings              │
│ Output: Baseline confirmed              │
└─────────────────────────────────────────┘
    │
    ↓ (STOP if assumption fails)
┌─────────────────────────────────────────┐
│ Phase 1: CODE (15 min)                  │
│ ✓ Implement changes (plan only)         │
│ ✓ No refactoring beyond plan            │
│ ✓ Verify each change                    │
│ Output: Changes complete                │
└─────────────────────────────────────────┘
    │
    ↓ (STOP if doesn't match plan)
┌─────────────────────────────────────────┐
│ Phase 2: GUARD (5 min)                  │
│ ✓ Add assertions/comments               │
│ ✓ Document \"why\" for future devs       │
│ ✓ Prevent regression                    │
│ Output: Enforcement in place            │
└─────────────────────────────────────────┘
    │
    ↓
┌─────────────────────────────────────────┐
│ Phase 3: SAFETY (5 min)                 │
│ ✓ Add fail-fast conditions              │
│ ✓ Improve error messages                │
│ ✓ Validate at runtime                   │
│ Output: Guards in place                 │
└─────────────────────────────────────────┘
    │
    ↓
┌─────────────────────────────────────────┐
│ Phase 4: TEST (10 min)                  │
│ ✓ Run negative tests                    │
│ ✓ Run regression tests                  │
│ ✓ Check edge cases                      │
│ Output: All tests pass                  │
└─────────────────────────────────────────┘
    │
    ↓ (STOP if test fails)
┌─────────────────────────────────────────┐
│ Phase 5: AUDIT (5 min)                  │
│ ✓ Check architecture integrity          │
│ ✓ Verify no scope creep                 │
│ ✓ Confirm no loose ends                 │
│ Output: System ready                    │
└─────────────────────────────────────────┘
    │
    ↓ (STOP if gaps found)
┌─────────────────────────────────────────┐
│ DEFINITION OF DONE (All 10 ✓)           │
│ ✓ Plan locked                           │
│ ✓ Assumptions confirmed                 │
│ ✓ Implementation complete               │
│ ✓ Enforcement added                     │
│ ✓ Guards in place                       │
│ ✓ Tests pass                            │
│ ✓ Audit complete                        │
│ ✓ All checklists 100%                   │
│ ✓ No further changes needed             │
│ ✓ Ready for deployment                  │
└─────────────────────────────────────────┘
    │
    ↓
OUTPUT FINAL REPORT ✓
DECLARE COMPLETE ✓
DEPLOY WITH CONFIDENCE ✓
```

---

## CRITICAL RULES (MANDATORY)

```
┌──────────────────────────────────────────────────┐
│           NON-NEGOTIABLE RULES                  │
├──────────────────────────────────────────────────┤
│                                                  │
│  1. PLAN BEFORE CODING                          │
│     └─ Phase -1 must create locked plan         │
│                                                  │
│  2. VERIFY BEFORE IMPLEMENTING                  │
│     └─ Phase 0 must confirm all assumptions     │
│                                                  │
│  3. MATCH PLAN EXACTLY                          │
│     └─ Phase 1 implements plan, nothing more    │
│                                                  │
│  4. FAIL FAST                                   │
│     └─ First error stops execution              │
│                                                  │
│  5. ALL PHASES MANDATORY                        │
│     └─ 6 phases, in order, every time           │
│                                                  │
│  6. RE-RUN ENTIRE PHASE IF IT FAILS             │
│     └─ Not just the failed item                 │
│                                                  │
│  7. EXPLICIT FINAL REPORT REQUIRED              │
│     └─ Must declare \"COMPLETE ✓\"              │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## TIME BREAKDOWN

```
┌──────────────────────────────────────────────────┐
│         TASK TIMING ESTIMATES                   │
├──────────────────────────────────────────────────┤
│                                                  │
│  SIMPLE FIX (1 file, 1-3 changes)               │
│  ├─ Phase -1:  3 min  ████                      │
│  ├─ Phase 0:   1 min  ██                        │
│  ├─ Phase 1:   8 min  ██████████                │
│  ├─ Phase 2:   2 min  ███                       │
│  ├─ Phase 3:   2 min  ███                       │
│  ├─ Phase 4:   5 min  ██████                    │
│  ├─ Phase 5:   3 min  ████                      │
│  └─ TOTAL:    24 min  ██████████████████████    │
│                                                  │
│  MEDIUM FIX (1-2 files, multi-change)           │
│  ├─ Phase -1:  5 min  ██████                    │
│  ├─ Phase 0:   2 min  ███                       │
│  ├─ Phase 1:  15 min  ██████████████████        │
│  ├─ Phase 2:   5 min  ██████                    │
│  ├─ Phase 3:   5 min  ██████                    │
│  ├─ Phase 4:  10 min  ███████████               │
│  ├─ Phase 5:   5 min  ██████                    │
│  └─ TOTAL:    47 min  ███████████████████████   │
│                                                  │
│  COMPLEX FIX (3+ files, refactoring)            │
│  ├─ Phase -1: 10 min  ████████████              │
│  ├─ Phase 0:   3 min  ████                      │
│  ├─ Phase 1:  30 min  ███████████████████████   │
│  ├─ Phase 2:   8 min  ██████████                │
│  ├─ Phase 3:   8 min  ██████████                │
│  ├─ Phase 4:  15 min  ██████████████            │
│  ├─ Phase 5:  10 min  ███████████               │
│  └─ TOTAL:    84 min  ███████████████████████   │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## FILE DECISION TREE

```
┌─────────────────────────────────────────────────┐
│        WHICH FILE SHOULD I USE?                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  START HERE
│  │
│  └─→ First time with G-CMP?
│      │
│      ├─ YES  →  Read README-INDEX.md (5 min)
│      │          Then read g-cmp-implementation.md (10 min)
│      │          Then use g-cmp-v2-revised.md (your task)
│      │
│      └─ NO   →  Know the phases already?
│                 │
│                 ├─ YES  →  Use g-cmp-quickref.md (reference)
│                 │          Open g-cmp-v2-revised.md (if needed)
│                 │
│                 └─ NO   →  Read g-cmp-implementation.md (10 min)
│                            Then use g-cmp-v2-revised.md
│
│
│  WORKING ON L9?
│  │
│  ├─ YES  →  Use g-cmp-l9-special.md instead of v2-revised
│  │          Reference L9 file paths & commands
│  │          Follow L9 context profiles
│  │
│  └─ NO   →  Use g-cmp-v2-revised.md (universal)
│
│
│  NEED QUICK LOOKUP?
│  │
│  ├─ YES  →  Use g-cmp-quickref.md (1 page)
│  │          Then g-cmp-checklist.md (if tracking)
│  │
│  └─ NO   →  Use full template (g-cmp-v2-revised.md)
│
│
│  TRACKING PROGRESS?
│  │
│  ├─ YES  →  Print g-cmp-checklist.md
│  │          Check off each phase
│  │          Verify Definition of Done before declaring done
│  │
│  └─ NO   →  Optional (but recommended)
│
└─────────────────────────────────────────────────┘
```

---

## SETUP IN CURSOR IDE

```
┌─────────────────────────────────────────────────┐
│      CURSOR TAB ARRANGEMENT                    │
├─────────────────────────────────────────────────┤
│                                                 │
│  OPTION 1: THREE TABS (Recommended)             │
│  ┌──────────────────────────────────────────┐  │
│  │ Tab 1: g-cmp-quickref.md [ALWAYS OPEN]  │  │
│  │ Tab 2: g-cmp-v2-revised.md [WORK HERE]  │  │
│  │ Tab 3: server.py [FILE BEING EDITED]    │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  OPTION 2: SPLIT PANE (Advanced)                │
│  ┌──────────────────┬──────────────────────┐   │
│  │  LEFT PANE       │   RIGHT PANE         │   │
│  ├──────────────────┼──────────────────────┤   │
│  │ quickref.md      │ v2-revised.md        │   │
│  │ (reference)      │ (work here)          │   │
│  │                  │                      │   │
│  └──────────────────┴──────────────────────┘   │
│         BOTTOM PANE: server.py (editing)       │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## DEFINITION OF DONE

```
┌────────────────────────────────────────────────┐
│    MUST CHECK ALL 10 ITEMS BEFORE DONE        │
├────────────────────────────────────────────────┤
│                                                │
│ ✓ Phase -1 plan created and LOCKED            │
│ ✓ Phase 0 baseline confirmed (ALL ✓)          │
│ ✓ Phase 1 implementation COMPLETE             │
│ ✓ Phase 2 enforcement ADDED                   │
│ ✓ Phase 3 system guards ADDED                 │
│ ✓ Phase 4 validation COMPLETE                 │
│ ✓ Phase 5 final audit COMPLETE                │
│ ✓ All checklists PASSED (100%)                │
│ ✓ No further changes NEEDED                   │
│ ✓ System READY for deployment                 │
│                                                │
│ IF ALL 10 ✓ → OUTPUT FINAL REPORT             │
│ IF ANY ❌   → GO BACK TO FAILED PHASE          │
│                                                │
└────────────────────────────────────────────────┘
```

---

## WHEN STUCK (QUICK DECISION TREE)

```
STUCK? FOLLOW THIS:

Problem: \"I don't know what to change\"
  └─ Solution: Re-read Phase -1 plan
              If still unclear → Re-run Phase -1

Problem: \"Phase 0 assumption failed\"
  └─ Solution: STOP
              Document failure
              Re-run Phase -1 completely
              Create new locked plan

Problem: \"My code doesn't match the plan\"
  └─ Solution: STOP immediately
              Revert all changes
              Re-run Phase 1 carefully
              Follow plan exactly

Problem: \"Test failing in Phase 4\"
  └─ Solution: STOP immediately
              Fix the failing test
              Re-run ENTIRE Phase 4
              Do NOT skip to Phase 5

Problem: \"Phase 5 found gaps\"
  └─ Solution: STOP immediately
              Fix identified gaps
              Re-run Phase 5
              Then declare DONE

Problem: \"Want to add extra feature\"
  └─ Solution: STOP
              Document as follow-up task
              Keep current task in scope
              Complete first task, plan second task
```

---

## SUCCESS CHECKLIST

```
✅ YOU ARE READY WHEN:

- [ ] Understand what's broken (the problem)
- [ ] Know which files are affected (exact paths)
- [ ] Know what MUST NOT change (forbidden areas)
- [ ] Know how to verify the fix (success criteria)
- [ ] Have templates open in Cursor
- [ ] Have checklist visible (or printed)
- [ ] Have 45 minutes uninterrupted
- [ ] Ready to follow 6 phases without exception

✅ YOU ARE DONE WHEN:

- [ ] All 6 phases completed
- [ ] All 10 Definition of Done items ✓
- [ ] Final report output
- [ ] System ready for deployment
- [ ] Can hand off with confidence
```

---

## KEY METRICS TO TRACK

```
After each task, record:

Planning Time:        5-10 min (goal: not longer)
Implementation Time:  15-30 min (goal: surgical)
Testing Time:         10-20 min (goal: comprehensive)
Total Time:           30-60 min (goal: efficient)

Phases Completed:     6/6 (goal: 100%)
Tests Passed:         ?/? (goal: 100%)
Definition of Done:   10/10 (goal: 100%)

If you hit targets consistently → System is working ✓
```

---

## FINAL VISUALIZATION

```
┌──────────────────────────────────────────────────┐
│           THE COMPLETE CYCLE                    │
├──────────────────────────────────────────────────┤
│                                                  │
│  PROBLEM          PLAN           IMPLEMENT      │
│     │              │                 │          │
│     └─→ Phase -1 ──→ Phase 0 ──→ Phase 1        │
│        (5 min)     (2 min)       (15 min)       │
│                                     │           │
│                                     ↓           │
│                              GUARD & PROTECT    │
│                                     │           │
│                     Phase 2    Phase 3          │
│                     (5 min)    (5 min)          │
│                        ↓          ↓             │
│                     TEST & AUDIT                │
│                        ↑          ↑             │
│                     Phase 4    Phase 5          │
│                    (10 min)    (5 min)          │
│                        │          │             │
│                        └─→ DONE ✓ ──→ DEPLOY    │
│                         (45 min)                │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## REMEMBER

```
    ╔═══════════════════════════════════════╗
    ║  PLAN → CODE → GUARD → TEST → AUDIT  ║
    ║       6 PHASES, EVERY TIME, IN ORDER  ║
    ║                                       ║
    ║     No Exceptions. No Shortcuts.      ║
    ║    Determinism Guaranteed. ✓          ║
    ╚═══════════════════════════════════════╝
```

---

**G-CMP v2.0 | Comprehensive Revised | Production Ready ✅**

**Your fix is waiting. Go.** 🚀