# ADR-0063: Incremental Configuration Adoption (No Breaking Replacements)

**Status:** Accepted  
**Date:** 2026-01-24  
**Decision Makers:** Igor (Human), Claude (Agent)  
**Context:** PR #58 CI/CD Enhancement, Spring Cleaning batch analysis

## Context

During PR review and adoption, we identified a recurring anti-pattern: PRs that **replace** configuration files wholesale rather than **merging** new functionality into existing configs.

### Examples Encountered

| PR | File | Anti-Pattern | Risk |
|----|------|--------------|------|
| #58 | `pyproject.toml` | Strict linting flags | 1000+ errors, blocked CI |
| #58 | `.gitleaks.toml` | Removed allowlist paths | False positives in CI |
| #49 | `.pre-commit-config.yaml` | Different hook structure | Broke existing hooks |

## Problem

**Wholesale config replacement** causes:

1. **Silent Regressions** — Existing settings removed without notice
2. **CI Breakage** — Stricter rules fail on existing code
3. **False Positives** — Allowlists/exceptions lost
4. **Git History Pollution** — Mass reformatting commits
5. **Development Blocking** — No PRs can merge until all violations fixed

## Decision

### Rule 1: Additive Over Replacement

**NEVER replace config files wholesale. ALWAYS merge additively.**

```
❌ WRONG: Copy PR's pyproject.toml over existing
✅ RIGHT: Extract new settings, merge into existing file
```

### Rule 2: Breaking Changes Require Incremental Rollout

| Change Type | Adoption Strategy |
|-------------|-------------------|
| New tool/integration | ✅ Add immediately |
| New lint rule | ⚠️ Enable per-module first |
| Stricter type checking | ⚠️ Enable per-module first |
| Format changes (line-length) | ❌ Defer or reject |
| Allowlist removal | ❌ Never (additive only) |

### Rule 3: Config Files Are Protected Surfaces

These config files require **additive merge** review:

| File | Protected Elements |
|------|-------------------|
| `pyproject.toml` | `line-length`, `strict`, `select` rules |
| `.gitleaks.toml` | `[allowlist]` paths and regexes |
| `.pre-commit-config.yaml` | Existing hooks |
| `ruff.toml` / `mypy.ini` | Existing exceptions |
| `codecov.yml` | Coverage thresholds |

### Rule 4: Cherry-Pick Pattern for Config PRs

When a PR modifies config files:

```bash
# 1. Extract ONLY the new additions
gh pr diff {number} | grep "^+" | grep -v "^+++"

# 2. Review what would be REMOVED
gh pr diff {number} | grep "^-" | grep -v "^---"

# 3. Merge additively (keep existing + add new)
# NEVER just copy the PR file over
```

## Examples

### ✅ Correct: Additive Merge (.gitleaks.toml)

```toml
# EXISTING (keep)
[allowlist]
paths = [".cursor/", "readme/", "tests/"]

# NEW (add from PR)
[[rules]]
id = "sendgrid-api-key"
regex = "SG\\.[a-zA-Z0-9_-]{22}..."
```

### ❌ Wrong: Wholesale Replacement

```toml
# PR replaces entire file — LOSES allowlist
[[rules]]
id = "sendgrid-api-key"
...
# allowlist section GONE
```

### ✅ Correct: Incremental Strict Linting

```toml
# Phase 1: Enable strict mypy for ONE module
[[tool.mypy.overrides]]
module = "core.agents.*"
strict = true

# Phase 2 (future GMP): Add another module
[[tool.mypy.overrides]]
module = "memory.*"
strict = true
```

### ❌ Wrong: Global Strict Flag

```toml
# Breaks 200+ files immediately
[tool.mypy]
strict = true  # DON'T DO THIS
```

## Checklist for Config PR Review

Before merging any PR that touches config files:

- [ ] **Diff inspection:** What existing settings would be REMOVED?
- [ ] **Allowlist preserved:** Are all exception paths still present?
- [ ] **Incremental adoption:** Are breaking changes module-scoped?
- [ ] **CI impact:** Would this fail on existing code?
- [ ] **Additive merge:** Can we cherry-pick new items only?

## Consequences

### Positive

- CI remains green during adoption
- No mass reformatting commits
- Allowlists/exceptions never lost
- Each strictness increase is reviewable
- Development velocity maintained

### Negative

- Some PRs cannot be merged as-is (require cherry-pick)
- Technical debt persists until incremental rollout
- More review effort for config PRs

### Neutral

- Config changes take longer to fully adopt
- ADR documentation required for each deferral

## Related ADRs

- **ADR-0062:** Deferred Strict Linting (specific instance)
- **ADR-0040:** CI/CD Security Scanning
- **Rule 92:** Learned lesson — incremental over breaking

## References

- PR #58: `.gitleaks.toml` wholesale replacement → cherry-picked additively
- PR #58: `pyproject.toml` strict flags → deferred per ADR-0062
- Commit `1040ddf1`: Example of correct additive merge
