# G-CMP ↔ L9 GMP Phase Alignment

**Purpose:** Map G-CMP v2.0 phases to L9 GMP v1.0 phases for seamless integration

**Version:** 1.0.0  
**Created:** 2026-01-12  
**Status:** ✅ Production Ready

---

## PHASE MAPPING

| G-CMP Phase | L9 GMP Phase | Purpose | Alignment |
|-------------|--------------|---------|-----------|
| **Phase -1: PLAN** | **Phase 0: TODO PLAN LOCK** | Create locked, deterministic plan before any code | ✅ Direct mapping |
| **Phase 0: VERIFY** | **Phase 1: BASELINE CONFIRMATION** | Verify plan matches repo state | ✅ Direct mapping |
| **Phase 1: CODE** | **Phase 2: IMPLEMENTATION** | Execute locked TODO plan | ✅ Direct mapping |
| **Phase 2: GUARD** | **Phase 3: ENFORCEMENT** | Add guards, validation, fail-fast checks | ✅ Direct mapping |
| **Phase 3: SAFETY** | **Phase 3: ENFORCEMENT** | Additional safety checks (merged with Phase 2) | ⚠️ Combined |
| **Phase 4: TEST** | **Phase 4: VALIDATION** | Comprehensive testing (unit, integration, regression) | ✅ Direct mapping |
| **Phase 5: AUDIT** | **Phase 5: RECURSIVE VERIFICATION** + **Phase 6: FINAL AUDIT** | Final review + recursive scope check | ⚠️ Split across 2 phases |

---

## DETAILED ALIGNMENT

### G-CMP Phase -1 → L9 GMP Phase 0

**G-CMP:**
- Create locked TODO plan
- Define files, lines, actions
- No code changes

**L9 GMP:**
- Research & analysis
- TODO PLAN LOCK (immutable)
- TODO INDEX HASH generation
- Report file creation

**✅ Alignment:** Perfect match. Both require locked plan before any code.

---

### G-CMP Phase 0 → L9 GMP Phase 1

**G-CMP:**
- Verify all assumptions
- Confirm files exist
- Check baseline state

**L9 GMP:**
- BASELINE CONFIRMATION
- Verify TODO targets exist
- Record baseline per TODO ID

**✅ Alignment:** Perfect match. Both verify plan matches reality.

---

### G-CMP Phase 1 → L9 GMP Phase 2

**G-CMP:**
- Implement changes
- Match plan exactly
- No scope drift

**L9 GMP:**
- IMPLEMENTATION
- Execute TODO items in order
- Zero drift outside scope

**✅ Alignment:** Perfect match. Both execute locked plan.

---

### G-CMP Phase 2 + 3 → L9 GMP Phase 3

**G-CMP Phase 2:**
- Add enforcement/guards
- Input validation
- Error handling

**G-CMP Phase 3:**
- System guards
- Fail-fast checks
- Safety constraints

**L9 GMP Phase 3:**
- ENFORCEMENT
- Guards, validation, fail-fast
- All safety checks

**⚠️ Alignment:** G-CMP splits enforcement into 2 phases, L9 GMP combines into 1. **Recommendation:** Use L9 GMP Phase 3 for both G-CMP Phase 2 and 3.

---

### G-CMP Phase 4 → L9 GMP Phase 4

**G-CMP:**
- Comprehensive testing
- Positive/negative tests
- Regression tests

**L9 GMP:**
- VALIDATION
- Unit + integration + critical-path tests
- All tests must pass

**✅ Alignment:** Perfect match. Both require comprehensive testing.

---

### G-CMP Phase 5 → L9 GMP Phase 5 + 6

**G-CMP Phase 5:**
- Final sanity sweep
- Recursive verification
- Definition of Done check

**L9 GMP Phase 5:**
- RECURSIVE VERIFICATION
- Scope drift check
- TODO → Change map verification

**L9 GMP Phase 6:**
- FINAL AUDIT + REPORT
- Definition of Done
- Final declaration

**⚠️ Alignment:** G-CMP combines final review into 1 phase, L9 GMP splits into 2. **Recommendation:** Use L9 GMP Phase 5 for recursive check, Phase 6 for final audit.

---

## USAGE RECOMMENDATIONS

### For Quick Fixes (< 3 files, < 30 min)
**Use:** G-CMP v2.0 (6 phases, faster workflow)
- Follow G-CMP phases -1 through 5
- Map to L9 GMP phases for reporting if needed
- Generate GMP report at end

### For Large Changes (Multi-file, refactors, new features)
**Use:** L9 GMP v1.0 (7 phases, stricter governance)
- Follow L9 GMP Phase 0-6
- Use G-CMP as reference for detailed phase guidance
- Generate GMP report (required)

### For L9 VPS/Docker Work
**Use:** `g-cmp-l9-special.md` (L9-specific variant)
- Follow G-CMP phases
- Use L9 file paths, service names, Docker commands
- Generate GMP report at end

---

## INTEGRATION CHECKLIST

When using G-CMP in L9 context:

- [ ] **Phase -1:** Create TODO plan in L9 GMP format (with TODO INDEX HASH)
- [ ] **Phase 0:** Verify baseline matches L9 GMP Phase 1 requirements
- [ ] **Phase 1:** Implement with L9 GMP Phase 2 constraints (no scope drift)
- [ ] **Phase 2+3:** Combine into L9 GMP Phase 3 (enforcement + safety)
- [ ] **Phase 4:** Run L9 GMP Phase 4 validation (unit + integration + critical-path)
- [ ] **Phase 5:** Split into L9 GMP Phase 5 (recursive) + Phase 6 (final audit)
- [ ] **Report:** Generate `GMP_Report_GMP-XX.md` in L9 format
- [ ] **Memory:** Write insights via `/mem` protocol

---

## FILE REFERENCES

- **L9 GMP Command:** `.cursor-commands/commands/gmp.md`
- **L9 GMP Canonical:** `codegen/C-GMP Suite/canonical/GMP-Action-Prompt-Canonical-v1.0.md`
- **G-CMP Main:** `codegen/C-GMP Suite/g-cmp-v2-revised.md`
- **G-CMP L9 Variant:** `codegen/C-GMP Suite/g-cmp-l9-special.md`

---

## VERSION HISTORY

- **v1.0.0** (2026-01-12): Initial alignment mapping created

---

**Status:** ✅ Production Ready  
**Next Update:** When L9 GMP v1.1 or G-CMP v3.0 released

