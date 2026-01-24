# PR Adoption Summary (2026-01-24)

> **IMPORTANT:** Agents reviewing code MUST read this before suggesting changes from closed PRs.

## Overview

This document tracks PR adoption decisions for the L9 codebase. Several PRs were analyzed and partially adopted via cherry-pick rather than full merge due to breaking changes or conflicts.

---

## ✅ MERGED (Full Adoption)

| PR | Title | Files | Notes |
|----|-------|-------|-------|
| #62 | setup-python v4/v5 → v6 | 4 workflows | Dependabot |
| #63 | codecov-action v3 → v5 | 1 workflow | Dependabot |
| #64 | github-script v6/v7 → v8 | 2 workflows | Dependabot |
| #66 | urllib3 <2 → <3 | requirements.txt | Dependabot |

---

## ⚠️ CHERRY-PICKED (Partial Adoption)

### PR #58: CI/CD Enhancement

**Adopted:**
- `codecov.yml` — Coverage config (75% floor)
- `coderabbit.yaml` — AI code review config
- `sonar-project.properties` — SonarCloud config (kept for future)
- `.datree-policy.yaml` — YAML policy validation
- `tests/test_ci_configuration.py` — 20 CI validation tests

**Skipped:**
- `pyproject.toml` stricter Ruff/MyPy — Breaking changes, documented in ADR-0062

**Decision:** ADR-0062 created for deferred strict linting adoption path.

---

### PR #60: Gemini-Perplexity AI PR Review Pipeline

**Adopted (9 files):**
- `.gemini/styleguide.md` — L9 patterns for Gemini Code Assist
- `.github/pr_review_config.yaml` — PR review pipeline config
- `scripts/pr_review/gemini_auto_editor.py` — Gemini API integration
- `scripts/pr_review/perplexity_reviewer.py` — Perplexity API integration
- `tests/unit/pr_review/__init__.py` — Test package
- `tests/unit/pr_review/test_pr_review_scripts.py` — PR review tests
- `tests/unit/adr/test_adr_enforcer.py` — ADR enforcer test
- `readme/AI_PR_REVIEW_WORKFLOW.md` — Workflow documentation
- `.env.example` — GEMINI/PERPLEXITY API key placeholders

**Skipped (40+ files):**
All files adding `@singleton` decorator from `core.patterns.singleton`

**Reason:** The module `core/patterns/singleton.py` does not exist. Importing from it would cause `ImportError` on all modified files.

---

### PR #61: DI Container Bootstrap with Tiered Initialization

**Adopted (3 files):**
- `examples/fastapi_lifespan_di_bootstrap.py` — FastAPI lifespan DI example
- `readme/DI_BOOTSTRAP_GUIDE.md` — DI bootstrap documentation
- `tests/unit/test_di_bootstrap.py` — DI bootstrap tests

**Skipped:**
- `core/di/container.py` — PR version (229 lines) conflicts with existing repo version (886 lines)
- 40+ `@singleton` changes — Same issue as PR #60
- 9 files already adopted from PR #60

---

### PR #65: actions/checkout v3/v4 → v6

**Status:** CLOSED (changes applied manually)

**Reason:** Merge conflict with modified `ci.yml`. Changes applied via `sed` and committed directly.

---

## ❌ CLOSED WITHOUT ADOPTION

| PR | Title | Reason |
|----|-------|--------|
| #57 | @singleton decorator to 40 classes | `core.patterns.singleton` doesn't exist |
| #59 | ADR Enforcement Validator | Files already exist in repo |

---

## 🚫 PATTERNS TO AVOID

### 1. `@singleton` from `core.patterns.singleton`

```python
# ❌ WRONG - Module doesn't exist
from core.patterns.singleton import singleton

@singleton
class MyService:
    pass
```

**L9's actual singleton pattern:**
```python
# ✅ CORRECT - Use existing L9 pattern
from core.singleton_auto_registry import register_singleton

@register_singleton(
    category="memory",
    lifecycle=SingletonLifecycle.LAZY,
    description="My service"
)
async def get_my_service() -> MyService:
    return MyService()
```

### 2. Direct DI Container Replacement

L9 has a comprehensive DI system at `core/di/`:
- `container.py` (886 lines) — Full DI container
- `bootstrap.py` (343 lines) — Service registration
- `bootstrap_integration.py` (315 lines) — Integration layer

**Do not** replace with simpler implementations from PRs.

---

## 📁 Files Added This Session

```
.gemini/styleguide.md
.github/pr_review_config.yaml
codecov.yml
coderabbit.yaml
sonar-project.properties
.datree-policy.yaml
examples/fastapi_lifespan_di_bootstrap.py
readme/AI_PR_REVIEW_WORKFLOW.md
readme/DI_BOOTSTRAP_GUIDE.md
readme/adr/0062-deferred-strict-linting.md
scripts/pr_review/gemini_auto_editor.py
scripts/pr_review/perplexity_reviewer.py
tests/test_ci_configuration.py
tests/unit/adr/test_adr_enforcer.py
tests/unit/pr_review/__init__.py
tests/unit/pr_review/test_pr_review_scripts.py
tests/unit/test_di_bootstrap.py
```

---

## 🔧 Workflows Updated

All GitHub Actions workflows updated to:
- `actions/checkout@v6`
- `actions/setup-python@v6`
- `codecov/codecov-action@v5`
- `actions/github-script@v8`

---

## Reference

- **ADR-0062:** Deferred Strict Linting (`readme/adr/0062-deferred-strict-linting.md`)
- **Session Date:** 2026-01-24
- **GMPs:** GMP-117 (Dependabot batch), GMP-118 (DI Bootstrap)
