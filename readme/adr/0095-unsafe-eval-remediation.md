# ADR 0095: Unsafe eval() Remediation

**Date**: 2026-01-21

**Status**: Proposed

## Context

The Priming Prompt Sequence analysis (Step 5) identified three critical security vulnerabilities related to the use of `eval()` and `__import__()`:

1.  **`core/di/container.py`**: Used `eval()` to resolve string annotations for dependency injection.
2.  **`core/tools/base_registry.py`**: Used `eval()` to execute mathematical expressions in the calculator tool.
3.  **`core/error_tracking.py`**: Used `__import__()` for dynamic import of `datetime.timedelta`.

These usages pose a significant security risk, as they can be exploited for arbitrary code execution.

## Decision

We will remediate these vulnerabilities by replacing the unsafe functions with safer alternatives:

1.  **DI Container**: Replace `eval()` with `typing.get_type_hints()`, which safely resolves string annotations without executing code.
2.  **Tool Registry**: Replace `eval()` with `ast.literal_eval()`, which only allows safe literals (strings, numbers, lists, dicts) and prevents code execution.
3.  **Error Tracking**: Replace `__import__()` with a direct, static import of `datetime.timedelta`.

## Consequences

### Positive

- **Eliminates critical security vulnerabilities** related to code injection.
- **Improves code quality** by using safer, more explicit functions.
- **Reduces attack surface** for the L9 platform.

### Negative

- **Slightly more verbose code** in the DI container to handle `get_type_hints()`.
- **Calculator tool functionality is reduced** to simple literals (no functions like `abs()`, `round()`). This is an acceptable trade-off for security.

### Neutral

- No performance impact.

## Alternatives Considered

- **Sandboxing `eval()`**: Considered using a restricted `eval()` environment, but this is complex and still carries risks.
- **Custom Parser**: Considered writing a custom parser for the calculator tool, but this is overkill for the current use case.

## DORA Metadata

- **component_id**: ADR-0095
- **governance_level**: high
- **compliance_required**: True
- **audit_trail**: True
- **dependencies**: ["core.di.container", "core.tools.base_registry", "core.error_tracking"]
- **tags**: ["adr", "security", "remediation", "eval", "injection"]
- **keywords**: ["adr", "security", "eval", "injection", "remediation"]
- **business_value**: "Remediates critical security vulnerabilities related to unsafe eval() and __import__() usage, preventing code injection attacks."
- **last_modified**: "2026-01-21T19:00:00Z"
- **modified_by**: "Manus_AI"
- **change_summary**: "Initial ADR for unsafe eval() remediation; renumbered from duplicate 0041 to 0095"
