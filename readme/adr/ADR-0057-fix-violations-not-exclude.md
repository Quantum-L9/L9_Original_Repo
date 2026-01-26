# ADR-0057: Fix Violations, Don't Exclude

**Status:** Accepted  
**Date:** 2026-01-26  
**Author:** Igor Beylin  

## Context

During code quality improvements, there's often temptation to exclude files or directories from linting, type checking, and other validation tools rather than fixing the underlying issues. This creates "hidden technical debt" where violations accumulate in excluded areas.

## Decision

**Policy: Fix violations at the source, don't hide them with exclusions.**

### Enforcement Rules

1. **File exclusions must be justified** - Every exclusion pattern in pre-commit, ruff.toml, pyproject.toml, or CI configs must have a documented justification.

2. **Valid exclusion reasons:**
   - **Truly unparseable content**: Helm templates (Go syntax), generated code, vendor code
   - **Intentional format differences**: Code examples in documentation that show "bad" patterns
   - **External dependencies**: Third-party code we don't control
   
3. **Invalid exclusion reasons:**
   - "Too many errors to fix" → Create a tracking issue instead
   - "Will fix later" → Fix now or create ADR for gradual rollout
   - "Not important" → If it's not important, remove the rule entirely

### File Categories

| Category | Can Exclude? | Reason |
|----------|-------------|--------|
| `_archived/` | Yes | Legacy code preserved for reference |
| `.backup/` | Yes | Temporary backups |
| `deploy/helm/*/templates/` | Yes | Go template syntax, not YAML |
| `**/tests/` | No | Tests need same quality as prod |
| `readme/**/*.yaml` | Sometimes | Only if showing intentional bad examples |
| Production code | No | Never exclude production code |

### Documentation File Naming

Documentation files containing code examples should use appropriate extensions:
- `.md` for markdown with embedded code blocks
- `.yaml.example` for example YAML (not validated)
- Never use `.yaml` for files that aren't valid YAML

## Implementation

### Pre-commit Config
```yaml
# Global exclude - document each pattern
exclude: "(_archived|.backup)"  # Legacy/backup code

# Hook-specific excludes require inline comments
- id: prettier
  exclude: "^deploy/helm/.*/templates/"  # Go template syntax
```

### Ruff Config
```toml
# Document exclusion categories
exclude = [
    "_archived",     # Legacy preserved code
    ".backup",       # Temporary backups
    "_pack_staging", # Work-in-progress codegen
]
```

### Mypy Exception

Mypy is temporarily disabled in pre-commit (1369 errors in 325 files) until a dedicated type coverage initiative. This is documented, tracked, and runs in CI reporting mode.

## Consequences

### Positive
- No hidden technical debt
- Clear understanding of codebase health
- Exclusions are intentional and documented
- Gradual improvement possible with tracking

### Negative
- Initial cleanup requires more effort
- Some edge cases need judgment calls

## Related
- ADR-0014: DORA Metadata pattern (explains E402 ignore)
- ADR-0002: Import organization rules
