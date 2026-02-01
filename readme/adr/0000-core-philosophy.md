# ADR-0000: Core Philosophy — 100% Done or Not Done

**Status:** Accepted  
**Date:** 2026-02-01  
**Author:** Igor Beylin  
**Priority:** ULTRA-CRITICAL  

## Context

Work completed to 95% is **NOT DONE**. It's broken code waiting to fail in production.

**Incident that prompted this ADR:**
- 2026-01-31: Agent added `--requirepass` to Redis but didn't update the healthcheck
- Result: Healthcheck would fail → container marked unhealthy → service won't start
- Root cause: Made point change without tracing downstream dependencies

This pattern repeats: edit the requested line, miss the implicit requirements, leave code broken.

## Decision

**Policy: 100% Done or it's NOT DONE. There is no 95%.**

### The Completion Ladder

| Level | % | Status | Reality |
|-------|---|--------|---------|
| Edit made | 50% | NOT DONE | May not even compile |
| Syntax valid | 60% | NOT DONE | Probably doesn't work |
| Lints pass | 70% | NOT DONE | Logic may be wrong |
| Tests pass | 85% | NOT DONE | Dependencies may break |
| Integration verified | 95% | NOT DONE | Edge cases may fail |
| **Actually works end-to-end** | 100% | **DONE** | Ship it |

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

| Anti-Pattern | Why It's Broken |
|--------------|-----------------|
| "Added the line you asked for" | Didn't check what else depends on it |
| "Change made, should work" | No verification |
| "Updated X, you'll need to update Y" | Incomplete — should have updated Y too |
| "Here's the fix" (no test) | How do you know it's fixed? |
| 95% confident | 5% chance of production outage |

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

## Enforcement

### 1. Pre-Commit Hook (Automated)

```bash
# .git/hooks/pre-commit addition
# Check for incomplete auth changes
if git diff --cached | grep -q "requirepass\|password"; then
  if ! git diff --cached | grep -q "healthcheck"; then
    echo "⚠️ WARNING: Auth change detected but no healthcheck update"
    echo "Run CVP checklist before committing"
  fi
fi
```

### 2. CI Gate (Automated)

Add to `ci/check_completion.py`:
- Scan for common incomplete patterns
- Require CVP checklist in PR description
- Block merge if verification missing

### 3. Agent Rules (Behavioral)

Added to `repeated-mistakes.md`:
- Lesson #21: TRACE ALL DEPENDENCIES
- After ANY change, grep for all references to changed entity
- Update each reference or document why it doesn't need updating

### 4. PR Template (Process)

```markdown
## Completion Verification

### Files Changed
- [ ] `file1.py` — reason
- [ ] `file2.py` — reason

### Downstream Impact Verified
- [ ] Healthchecks updated (if auth/config changed)
- [ ] Tests updated (if behavior changed)
- [ ] Docs updated (if API changed)

### Evidence
\`\`\`
<paste actual test output here>
\`\`\`
```

## Consequences

### Positive
- No more "fixed but broken" deployments
- Downstream dependencies always traced
- Clear verification trail
- Trust maintained

### Negative
- Changes take longer (but less rework)
- More verification steps (but fewer production bugs)
- More rigorous process (but higher quality)

## Implementation Checklist

- [x] Created ADR-0000 (this document)
- [ ] Add Lesson #21 to repeated-mistakes.md
- [ ] Create ci/check_completion.py
- [ ] Update PR template
- [ ] Add pre-commit hook for auth changes

## Mantra

> **"If you changed X, what else uses X? Update ALL of them."**

---

## Addendum: The Automation Efficiency Principle

**Incident:** 2026-02-01 — Test Generator Anti-Pattern

### The Problem

The `core/testing/test_generator.py` had a fundamental design flaw:
1. AST parsing extracted function/class structure ✅
2. Generated TODO stub tests ❌
3. Required manual completion of each test ❌

**Result:** Every test file cost $5-50+ in Cursor tokens for manual completion.

### The WRONG Approach (What We Had)

```python
# test_generator.py - WRONG
def _generate_function_tests(self, func):
    return f'''
def test_{func.name}_happy_path():
    """Test {func.name} with valid inputs."""
    # TODO(GMP-109): Add appropriate test inputs  ← HUMAN MUST FINISH
    pass
'''
```

**Cost per test file:** $5-50 (Cursor tokens for manual completion)
**200 missing test files:** $1,000-10,000+ in wasted tokens

### The RIGHT Approach (What We Fixed)

```python
# test_generator.py - RIGHT
def generate_unit_tests(self, code_proposal, module_name):
    # 1. AST parse → extract structure (FREE)
    ast_info = self._extract_ast_info(ast.parse(code_proposal))
    
    # 2. LLM generates FULL implementations (PENNIES)
    if self._use_llm and self._llm_client:
        return self._generate_tests_with_llm(code_proposal, ast_info)
    
    # 3. Fallback to stubs only if no LLM available
    return self._generate_stub_tests(...)
```

**Cost per test file:** $0.01-0.10 (LLM API)
**200 test files:** $2-20 total

### Cost Comparison

| Approach | Per File | 200 Files | Quality |
|----------|----------|-----------|---------|
| Manual Cursor | $5-50 | $1,000-10,000 | Variable |
| LLM API | $0.01-0.10 | $2-20 | Consistent |
| **Savings** | **99%** | **$998-9,980** | Better |

### The Design Principle

> **"If a tool generates stubs that need manual completion, 
> the tool is 50% done. Finish the automation."**

| Status | Description | Reality |
|--------|-------------|---------|
| Stub generator | Creates TODO placeholders | 50% tool, 50% manual work |
| **Full generator** | Creates runnable code | 100% automation |

### Implementation Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CORRECT AUTOMATION PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
     ┌──────────────────────────────┼──────────────────────────────┐
     │                              │                              │
     ▼                              ▼                              ▼
┌─────────────┐            ┌─────────────────┐           ┌─────────────────┐
│ AST Parse   │            │ Build Context   │           │ LLM Generate    │
│ (FREE)      │     →      │ (FREE)          │     →     │ ($0.01/file)    │
│             │            │                 │           │                 │
│ Extract:    │            │ Create prompt:  │           │ Output:         │
│ - functions │            │ - signatures    │           │ - full tests    │
│ - classes   │            │ - dependencies  │           │ - assertions    │
│ - methods   │            │ - patterns      │           │ - mocks         │
└─────────────┘            └─────────────────┘           └─────────────────┘
```

### Applied to Test Generation

**Before (WRONG):**
```bash
# Generate stubs → manually complete each
python -c "from core.testing import generate_unit_tests; ..."
# Output: TODO stubs requiring $50 of Cursor work
```

**After (RIGHT):**
```bash
# Generate complete tests automatically  
python -c "
from core.testing import generate_test_file
from pathlib import Path

code = Path('memory/enrichment_dag.py').read_text()
tests = generate_test_file(code, 'memory.enrichment_dag')
Path('tests/memory/test_enrichment_dag.py').write_text(tests)
"
# Output: Complete, runnable tests for $0.05
```

### The Mantra

> **"Don't pay dollars for what costs pennies. 
> If there's an LLM-automatable step, automate it."**

---

## Addendum: 100% DONE Enforcement (2026-01-31)

### The Problem: 95% Done ≠ Done

Tasks left at 95% completion are NOT DONE. Examples:
- Tests generated but not run → NOT DONE
- Code written but not validated → NOT DONE
- Feature implemented but tests fail → NOT DONE

### Enforcement Mechanisms

**1. CI Gate: All Tests Must Pass**
```yaml
# .github/workflows/ci.yml
- name: Test Gate
  run: pytest --tb=short
  # Fails CI if ANY test fails
```

**2. Pre-commit Hook: Syntax Validation**
```bash
# .git/hooks/pre-commit
python -m py_compile $file || exit 1
```

**3. Definition of Done Checklist (DoD-Gate)**
Before marking COMPLETE, verify:
- [ ] All tests pass (`pytest` exits 0)
- [ ] No linter errors (`ruff check .`)
- [ ] Type checks pass (`mypy`)
- [ ] Evidence provided (test output, exit code)

**4. Agent Rule: Verify Before Claiming Done**

```
CRITICAL: Do NOT claim "fixed" or "done" without:
1. Running the actual command/test
2. Showing the output/exit code
3. Confirming success evidence

Saying "it should work" is NOT evidence.
```

### The Formula

```
100% DONE = Code + Tests Pass + Evidence
95% DONE = Code + Tests Exist = NOT DONE
90% DONE = Code + TODO Stubs = NOT DONE
```

### Lessons

| Pattern | Status | Fix |
|---------|--------|-----|
| Tests generated but 2 fail | NOT DONE | Fix failures, run again |
| Code written, tests not run | NOT DONE | Run tests, show output |
| "Should work" claim | NOT DONE | Provide evidence |

---

## Related

- **ADR-0091: Definition of Done** ← Enforceable checklist (CI Gate 17)
- ADR-0072: Diagnose Before Fix
- ADR-0073: Evidence-Based Claims
- ADR-0074: Surgical Edits Only
- Lesson #20: Verify Paths Exist
- Lesson #21: Trace All Dependencies
- Lesson #22: Definition of Done
- **Lesson #23: Automate All The Way** ← NEW: Stub generators are 50% done
