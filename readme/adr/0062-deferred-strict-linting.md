# ADR-0062: Deferred Strict Linting Configuration

**Status:** Accepted  
**Date:** 2026-01-24  
**Decision Makers:** Igor (Human), Claude (Agent)  
**Context:** PR #58 CI/CD Enhancement Review

## Context

PR #58 proposed comprehensive CI/CD marketplace integration including stricter linting configurations:

| Tool | PR #58 Proposed | Current L9 | Delta |
|------|-----------------|------------|-------|
| Ruff `line-length` | 120 | 88 | +32 chars |
| MyPy `strict` | `true` | N/A | Breaking |
| MyPy `disallow_untyped_defs` | `true` | N/A | Breaking |
| MyPy `warn_return_any` | `true` | `false` | Breaking |
| Ruff rules | +A, PIE, Q, N, C901 | F, E7, E9, W, I, B, UP, TCH | More strict |

## Problem

Adopting stricter linting immediately would:

1. **Break CI** — Estimated 1,000+ mypy errors across 200+ files
2. **Mass reformatting** — Line-length change from 88→120 would reformat entire codebase
3. **Block development** — No PRs could merge until all violations fixed
4. **Git history pollution** — One massive formatting commit

## Decision

**DEFER strict linting adoption.** Accept only the NEW additive files from PR #58:

### Adopted (5 files)

| File | Purpose |
|------|---------|
| `codecov.yml` | Coverage tracking (75% floor) |
| `coderabbit.yaml` | AI code review with L9-specific patterns |
| `sonar-project.properties` | SonarCloud configuration |
| `.datree-policy.yaml` | YAML validation rules |
| `tests/test_ci_configuration.py` | CI configuration validation tests |

### Deferred (pyproject.toml changes)

| Setting | Reason for Deferral |
|---------|---------------------|
| `line-length: 120` | Would reformat all files; keep 88 (Black default) |
| `mypy.strict = true` | ~1000+ errors; adopt incrementally |
| `mypy.disallow_untyped_defs` | Core modules only (future GMP) |
| Additional Ruff rules (A, PIE, Q, N) | Add one rule set at a time |

## Incremental Adoption Path

### Phase 1: Current (ADR-0062)
- ✅ Keep `line-length: 88`
- ✅ Keep relaxed mypy
- ✅ Add Codecov, SonarCloud, CodeRabbit

### Phase 2: Future GMP (TBD)
- Enable `mypy.strict` for `core/` only via `[[tool.mypy.overrides]]`
- Add one Ruff rule set (e.g., `A` for builtins)

### Phase 3: Future GMP (TBD)
- Expand mypy strict to `memory/`, `runtime/`
- Add `PIE`, `Q` rules

### Phase 4: Final Strictness
- Full `mypy.strict = true`
- All proposed Ruff rules

## Consequences

### Positive
- CI remains green
- Development velocity maintained
- Strict linting adopted incrementally with manageable PRs
- Each strictness increase is a single reviewable GMP

### Negative
- Technical debt: relaxed typing persists short-term
- Potential type bugs not caught until Phase 2+

### Neutral
- PR #58 cannot be merged as-is (partial adoption only)

## Compliance

- **GMP-114:** PR #58 analysis identified conflicts
- **ADR-0040:** CI/CD security scanning (this extends it)
- **Rule 92:** Learned lesson — incremental over breaking

## References

- PR #58: `feat/ci-marketplace-integration`
- Current `pyproject.toml`: `line-length: 88`, relaxed mypy
- Black default: `line-length: 88`
- PEP 8: 79 chars (we exceed this intentionally)
