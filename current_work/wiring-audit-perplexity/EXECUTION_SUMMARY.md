# EXECUTION SUMMARY: L9 Memory + Cursor Wiring Audit (Phase 0 LOCKED)

**Generated:** January 13, 2026  
**Status:** Ready for Cursor/Human execution  
**Scope:** Repo-wide wiring invariant audit for Memory APIs + Cursor integration

---

## WHAT YOU NOW HAVE

### 1️⃣ **Phase 0 TODO Plan** (`wiring-audit-phase0-plan.md`)
   - **Reframes** the original audit from "local doc fixes" → "repo-wide wiring invariant"
   - **Declares** canonical routers (apimemoryrouter, mcpmemorysrc*, apiroutescursor, cursor extractors)
   - **Provides** structured doc–code alignment table (old path → new path → actual module)
   - **Lists** 5 concrete TODOs with file paths, match patterns, and expected outcomes
   - **Includes** telemetry sanity checks (observability/metrics still wired post-fix)
   - **Enforces** L9 invariants (governance, protocol, substrate untouched)
   - **Gives** final validation checklist + effort estimate (~40 min)

### 2️⃣ **Wiring Validator Script** (`validate_wiring_alignment.py`)
   - **Executable** Python script you can run immediately
   - **Scans** docs (*.md), audit scripts, `.audit_cache/manifest.json`
   - **Detects** all 5 stale path patterns (api/routes/memory.py, tools/cursor_client, etc.)
   - **Verifies** canonical routers exist in codebase
   - **Checks** protected L9 modules are untouched
   - **Reports** structured results (errors, warnings, PASS/FAIL)
   - **Exit codes:** 0=PASS, 1=FAIL, 2=config error
   - **Usage:**
     ```bash
     python3 scripts/audit/validate_wiring_alignment.py --verbose
     ```

---

## HOW TO USE

### **Step A: Review the Plan** (5 min)
1. Open `wiring-audit-phase0-plan.md`
2. Read PART I (Invariant) and PART II (Alignment Table)
3. Review the 5 TODOs in PART III
4. Confirm the DO/DO NOT boundaries and checklist

### **Step B: Run the Validator Pre-Fix** (5 min)
```bash
# Copy validator to your L9 repo
cp validate_wiring_alignment.py scripts/audit/

# Run it (should FAIL because stale paths exist)
python3 scripts/audit/validate_wiring_alignment.py --verbose

# Expected output: Lists all docs/cache entries with stale refs
```

### **Step C: Execute the TODOs** (30 min)
Execute the 5 TODOs from the plan in order:

- **TODO-1:** Replace `api/routes/memory.py` with correct path in `gap-analysis-memory.md` (7 occurrences)
- **TODO-2:** Batch-search docs/scripts for stale Cursor paths; replace with canonical paths
- **TODO-3:** Regenerate `.audit_cache` (rm -rf + run_all.py)
- **TODO-4:** Spot-check async function map matches router counts
- **TODO-5:** (Optional) Create full validator script (already done for you)

### **Step D: Run the Validator Post-Fix** (5 min)
```bash
# Should now PASS
python3 scripts/audit/validate_wiring_alignment.py --verbose

# Expected output: "✅ PASS - All paths aligned, no L9 invariants broken"
```

### **Step E: Run Telemetry Sanity Checks** (5 min)
```bash
# Confirm observability metrics still wire
grep -r "l9memorywritestotal\|l9memorysearchestotal" coreobservability*.py | head -3

# Confirm tool audit logs reference memory substrate, not ghosts
grep -r "memorysubstrateservice\|memorysubstraterepository" coreobservability*.py | head -3
```

### **Step F: Final Checklist** (5 min)
Use the validation checklist from PART V of the plan:
- [ ] gap-analysis-memory.md has zero `api/routes/memory.py` refs
- [ ] All docs/scripts use new Cursor paths (agents/cursor/*)
- [ ] Audit cache regenerated and clean (no stale paths)
- [ ] Validator script passes (exit code 0)
- [ ] Observability metrics wired
- [ ] L9 invariants untouched (governance, protocol, substrate)
- [ ] architecture_decisions.md NOT modified

---

## KEY DIFFERENCES FROM ORIGINAL PLAN

| Aspect | Original | Phase 0 LOCKED |
|---|---|---|
| **Scope** | "Fix gap-analysis-memory.md" | Repo-wide wiring invariant for Memory + Cursor |
| **Validation** | "Run grep once" | Automated script + multi-phase checks |
| **Data** | Prose only | Structured table + file_metrics anchor |
| **L9 Safety** | Implicit | Explicit (declared protected modules, invariants) |
| **Observability** | Ignored | Telemetry checks post-fix |
| **Effort** | Vague | ~40 min with breakdown |

---

## CORE INSIGHT

This is **not just doc cleanup**. It's a **wiring audit** that ensures:

1. **Docs match code:** Every path reference points to a real, canonical module
2. **Audit cache is honest:** No stale entries, no ghost paths
3. **L9 safety:** Governance, protocol, substrate untouched
4. **Observability survives:** Metrics still wire after changes
5. **Future-proof:** Validator script can be run anytime to catch regressions

---

## NEXT STEPS

1. **Copy the validator script** to `scripts/audit/`
2. **Run it pre-fix** (will fail; that's expected)
3. **Execute the 5 TODOs** from the phase 0 plan (30 min, mostly mechanical)
4. **Run validator post-fix** (should pass)
5. **Run telemetry checks** (5 min spot-checks)
6. **Mark complete** in the checklist

---

## FILES PROVIDED

- **`wiring-audit-phase0-plan.md`** — Full phase 0 plan with TODOs, invariants, alignment table
- **`validate_wiring_alignment.py`** — Executable validator script (drop in `scripts/audit/`)

Both are production-ready and can be integrated into CI/CD immediately.

---

## SUPPORT

If execution stalls:
1. Check that all referenced files exist (grep from file_metrics.txt)
2. Verify `.audit_cache` generation doesn't fail (may need migration)
3. Confirm no L9 invariant has been accidentally touched
4. Re-run validator with `--verbose` for detailed logs

Good luck! 🚀
