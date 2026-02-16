# ADR-0000: L9 Core Philosophy — Automation-First, 100% Done

**Status:** Accepted
**Date:** 2026-02-02
**Author:** Igor Beylin
**Priority:** ULTRA-CRITICAL

## Summary

L9 is built on two non-negotiable principles:

1. **Automation-First** — Every manual process must be automated
2. **100% Done** — Work completed to 95% is NOT DONE

---

## Part 1: Automation-First Philosophy

### Core Principle

Automation is not a feature — it is the foundation upon which L9 is built. Every aspect of the system should trend toward full automation.

| Layer          | Manual Today           | Automated Tomorrow              |
| -------------- | ---------------------- | ------------------------------- |
| **Reports**    | Token-consuming drafts | Script-generated, verified      |
| **Reviews**    | Human-only reviews     | AI + human hybrid               |
| **Indexes**    | Manual catalog updates | Auto-generated on session start |
| **Compliance** | Manual DORA checks     | CI-enforced DORA validation     |
| **Migrations** | Manual SQL execution   | Auto-applied at startup         |
| **Memory**     | Manual context loading | MCP-injected context            |
| **Tests**      | Manual stub completion | LLM-generated full tests        |

### Automation Improvement Cycle

```
┌─────────────────────────────────────────────────────────────────┐
│                 L9 AUTOMATION CYCLE                             │
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐                │
│   │ IDENTIFY │ → │ AUTOMATE │ → │ IMPROVE  │ → (repeat)      │
│   └──────────┘    └──────────┘    └──────────┘                │
│                                                                 │
│   Manual process? → Create script → Measure & enhance          │
│   Existing script? → Profile it → Optimize or replace          │
│   New capability? → Can it auto-run? → Add to pipeline         │
└─────────────────────────────────────────────────────────────────┘
```

### AI Code Reviews Must Suggest Automation

**This is a hard requirement.** When reviewing code, AI agents MUST actively look for:

1. **Repetitive patterns** → Suggest abstraction into reusable function
2. **Manual data entry** → Suggest code generation or configuration
3. **Copy-paste patterns** → Suggest template or factory
4. **Manual verification** → Suggest automated validation script
5. **Human decision points** → Suggest decision automation or ML-based routing
6. **Manual triggers** → Suggest scheduled jobs or event-driven automation

### Automation Tiers

**Tier 1: Must Be Automated (Day 0)**

- GMP report generation
- Code validation (py_compile, import test, lint)
- Session startup (load governance, workflow state)
- Pre-commit hooks (security, format, type-check)

**Tier 2: Should Be Automated (Sprint N)**

- Code review suggestions
- Documentation generation
- Test scaffolding
- Dependency updates

**Tier 3: Can Be Automated (Future)**

- Architecture decision suggestions
- Refactoring recommendations
- Performance optimization detection
- Security vulnerability prediction

### The Automation Efficiency Principle

> **"If a tool generates stubs that need manual completion, the tool is 50% done. Finish the automation."**

| Status             | Description               | Reality                   |
| ------------------ | ------------------------- | ------------------------- |
| Stub generator     | Creates TODO placeholders | 50% tool, 50% manual work |
| **Full generator** | Creates runnable code     | 100% automation           |

**Cost Comparison (Test Generation Example):**

| Approach      | Per File   | 200 Files      | Quality    |
| ------------- | ---------- | -------------- | ---------- |
| Manual Cursor | $5-50      | $1,000-10,000  | Variable   |
| LLM API       | $0.01-0.10 | $2-20          | Consistent |
| **Savings**   | **99%**    | **$998-9,980** | Better     |

> **"Don't pay dollars for what costs pennies. If there's an LLM-automatable step, automate it."**

---

## Part 2: 100% Done Philosophy

### Core Principle

**Policy: 100% Done or it's NOT DONE. There is no 95%.**

Work completed to 95% is broken code waiting to fail in production.

### The Completion Ladder

| Level                         | %    | Status   | Reality                |
| ----------------------------- | ---- | -------- | ---------------------- |
| Edit made                     | 50%  | NOT DONE | May not even compile   |
| Syntax valid                  | 60%  | NOT DONE | Probably doesn't work  |
| Lints pass                    | 70%  | NOT DONE | Logic may be wrong     |
| Tests pass                    | 85%  | NOT DONE | Dependencies may break |
| Integration verified          | 95%  | NOT DONE | Edge cases may fail    |
| **Actually works end-to-end** | 100% | **DONE** | Ship it                |

### Completion Verification Protocol (CVP)

**MANDATORY for every change:**

```markdown
## ✅ COMPLETION VERIFICATION

### 1. Change Scope Trace

- [ ] Listed ALL files that reference the changed entity
- [ ] Verified each reference still works with the change
- [ ] Checked healthchecks, tests, configs, docs

### 2. Downstream Impact

- [ ] Traced what depends on this change
- [ ] Updated all dependents
- [ ] No orphaned references

### 3. Verification Evidence

- [ ] Command run: `<actual command>`
- [ ] Output: `<actual output>`
- [ ] Exit code: 0

### 4. Integration Test

- [ ] Tested with actual dependencies (not mocks)
- [ ] Verified end-to-end flow works
```

### Anti-Patterns (VIOLATIONS)

| Anti-Pattern                         | Why It's Broken                        |
| ------------------------------------ | -------------------------------------- |
| "Added the line you asked for"       | Didn't check what else depends on it   |
| "Change made, should work"           | No verification                        |
| "Updated X, you'll need to update Y" | Incomplete — should have updated Y too |
| "Here's the fix" (no test)           | How do you know it's fixed?            |
| 95% confident                        | 5% chance of production outage         |

### The Redis Healthcheck Lesson

```yaml
# WRONG: Point change only
command: redis-server --requirepass ${REDIS_PASSWORD}
healthcheck:
  test: ["CMD", "redis-cli", "ping"]  # ← STILL BROKEN

# RIGHT: Complete change
command: redis-server --requirepass ${REDIS_PASSWORD}
healthcheck:
  test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]  # ← FIXED
```

**The mistake:** Changed auth requirement but didn't trace what else uses Redis.

**The lesson:** Every change has ripples. Trace them ALL.

### The Formula

```
100% DONE = Code + Tests Pass + Evidence
95% DONE = Code + Tests Exist = NOT DONE
90% DONE = Code + TODO Stubs = NOT DONE
```

---

## Rules (Enforcement)

### Automation Rules

1. Every GMP report MUST be generated by `scripts/generate_gmp_report.py` — never manually drafted
2. Every code review MUST include at least one automation suggestion if applicable
3. Every new script MUST have automated verification (no "trust me, it works")
4. Every manual process that occurs more than twice MUST have an issue filed to automate it
5. Every automation MUST be measured (timing, success rate, error rate)
6. NEVER accept "it's too complex to automate" without exploring options first

### Completion Rules

7. NEVER claim "fixed" or "done" without running actual tests and showing evidence
8. ALWAYS trace ALL files that reference a changed entity
9. ALWAYS update healthchecks, tests, configs when changing auth/config
10. ALWAYS provide verification evidence (command, output, exit code)

---

## AI Guidance

**DO:**

- Suggest automation opportunities in every code review
- Create scripts for repetitive tasks before doing them manually
- Add `--dry-run` and `--verify` flags to all automation scripts
- Chain automations together (e.g., generate → validate → update state)
- Measure automation effectiveness with timing and success metrics
- Trace ALL dependencies when making changes
- Provide evidence (test output, exit codes) before claiming done

**DO NOT:**

- Manually draft reports, indexes, or catalogs that can be generated
- Accept manual processes without questioning if they can be automated
- Create automation without verification/validation steps
- Skip the automation improvement cycle ("it works, don't touch it")
- Consume tokens on tasks that scripts should handle
- Make point changes without checking downstream dependencies
- Claim "should work" without evidence

---

## Files

- `scripts/generate_gmp_report.py` - Auto-generates GMP reports
- `scripts/validate_gmp_report.py` - Auto-validates reports
- `tools/export_repo_indexes.py` - Auto-generates 34 repo index files
- `.cursor-commands/startup/session_startup.py` - Auto-loads governance context
- `ci/dora_compliance_check.py` - Auto-enforces DORA metadata
- `scripts/hooks/pre-commit` - Auto-runs 8 security gates
- `core/testing/test_generator.py` - LLM-powered test generation

---

## Metrics for Health

| Metric                            | Target | How to Measure                           |
| --------------------------------- | ------ | ---------------------------------------- |
| Manual report drafts              | 0      | Count reports not in `reports/`          |
| Automation coverage               | >80%   | Scripts / Total processes                |
| Automation suggestions per review | ≥1     | Track in code review logs                |
| Script verification rate          | 100%   | Scripts with `--verify` or tests         |
| Automation failure rate           | <5%    | Failed runs / Total runs                 |
| Incomplete changes caught         | 100%   | CVP checklist enforcement                |
| 95% done incidents                | 0      | Production failures from incomplete work |

---

## Mantras

> **"If you changed X, what else uses X? Update ALL of them."**

> **"Don't pay dollars for what costs pennies. Automate all the way."**

> **"100% DONE = Code + Tests Pass + Evidence"**

---

## Related ADRs

- [ADR-0004: Singleton Auto-Registry](0004-singleton-auto-registry.md) - Auto-registration pattern
- [ADR-0012: Memory DAG Pipeline](0012-memory-dag-pipeline.md) - Automated packet processing
- [ADR-0035: ADR Bootstrap Protocol](0035-adr-bootstrap-protocol.md) - Automated ADR creation
- [ADR-0072: Diagnose Before Fix](0072-diagnose-before-fix.md)
- [ADR-0073: Evidence-Based Claims](0073-evidence-based-claims.md)
- [ADR-0074: Surgical Edits Only](0074-surgical-edits-only.md)
- [ADR-0091: Definition of Done](0091-definition-of-done.md) - CI Gate 17

## Changelog

- 2026-02-02: Consolidated from 0000-l9-philosophy.md and 0000-core-philosophy.md
- 2026-02-01: Added automation efficiency principle (test generator lesson)
- 2026-01-31: Added 100% done enforcement
- 2026-01-20: Initial creation — automation-first philosophy
