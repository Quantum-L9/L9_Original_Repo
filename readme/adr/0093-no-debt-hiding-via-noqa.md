# ADR-0093: No Debt Hiding via Noqa

## Status
ACCEPTED

## Context
The `# noqa` comment mechanism is intended to flag false positives where a linter or compliance checker incorrectly identifies a violation. However, it has been used to "hide" legitimate violations (technical debt) to make CI pass without actually fixing the underlying issue.

Specific examples of misuse:
- Adding `# noqa: ADR-0019` to `print()` statements in production code instead of converting to `structlog`.
- Adding `# noqa: ADR-0010` to `async` functions missing the `@must_stay_async` decorator instead of adding the decorator.
- Adding `# noqa: ADR-0087` to potential SQL injection vectors instead of parameterizing queries.

This practice "brushes dirt under the rug," making the codebase appear compliant while retaining defects, security vulnerabilities, and observability gaps.

## Decision

1.  **False Positives Only**: `# noqa` comments MUST ONLY be used when the code is actually correct and the linter/checker is wrong (a false positive).
2.  **Explicit Justification**: Every `# noqa` comment MUST include a specific justification explaining *why* it is a false positive.
    *   ❌ `# noqa: ADR-0019`
    *   ✅ `# noqa: ADR-0019 - CLI tool, stdout required`
3.  **No Auto-Hiding**: Automated tools (like `ci/auto_fix_adr.py`) are PROHIBITED from automatically adding `# noqa` comments to suppress violations unless they can deterministically prove it is a false positive.
4.  **Security Non-Negotiable**: Security-related ADRs (ADR-0087 SQL, ADR-0088 Pickle, ADR-0090 Secrets) CANNOT be suppressed with `# noqa` without explicit, written approval from the Security Architect (Igor/L).
5.  **Fix, Don't Hide**: If a violation is legitimate, the code MUST be refactored to comply. If refactoring is not immediately possible, a formal tracking ticket must be created, and the `noqa` must reference that ticket.

## Consequences

### Positive
- **True Compliance**: CI passing actually means the code follows standards.
- **Better Observability**: Production logs will not be fragmented between `structlog` and `print`.
- **Reduced Risk**: Security vulnerabilities will not be masked.

### Negative
- **Higher Friction**: "Quick fixes" to get CI passing will require actual code changes.
- **Initial Cleanup**: Existing "hidden" debt (like the 1,000+ auto-generated noqas) will need to be audited and fixed properly.

## Compliance
This ADR is enforced by:
- `ci/check_adr_compliance.py`: Will be updated to flag unjustified `noqa` usage.
- Code Review: Reviewers must reject PRs that add `noqa` to hide valid issues.
