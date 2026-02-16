# ADR-0072: Diagnose Before Fix

**Status:** Accepted
**Date:** 2026-01-31
**Author:** Igor Beylin

## Context

When code fails, there's a temptation to apply quick fixes—suppressing errors, adding `|| true`, hiding warnings with `2>/dev/null`. These "fixes" mask the real problem and create hidden technical debt.

Example incident: Pre-commit hook failed because `.gitignore` pattern `codegen/` was too broad, catching `core/codegen/`. The lazy fix was `git add 2>/dev/null || true`. The correct fix was changing `.gitignore` to `/codegen/` (root-only match).

## Decision

**Policy: Always diagnose root cause before applying any fix.**

### Diagnosis Protocol

Before fixing ANY error:

1. **REPRODUCE** — Can you trigger the error consistently?
2. **TRACE** — What exact line/command/pattern causes it?
3. **WHY** — What is the underlying cause, not the symptom?
4. **FIX ROOT** — Address the actual cause, not the visible error

### Anti-Patterns

| Anti-Pattern            | Why It's Wrong        | Correct Approach              |
| ----------------------- | --------------------- | ----------------------------- | ------------------------- | ---------------- |
| `2>/dev/null`           | Hides the real error  | Read the error, fix the cause |
| `                       |                       | true`                         | Continues despite failure | Fix why it fails |
| `# type: ignore`        | Masks type errors     | Fix the type issue            |
| `# noqa` everywhere     | Hides lint violations | Fix the violations            |
| `try: ... except: pass` | Swallows all errors   | Handle specific exceptions    |

### Valid Suppression (Rare)

Suppression is acceptable ONLY when:

- The "error" is expected behavior (e.g., `mkdir -p` on existing dir)
- You've documented WHY suppression is acceptable
- There's no fix possible (third-party code, read-only)

### Diagnostic Questions

Before any fix, answer:

1. What is the EXACT error message?
2. What file/line/pattern triggers it?
3. Is this a symptom or the root cause?
4. Will this fix prevent recurrence, or just hide it?
5. Could this same root cause affect other code?

## Implementation

### Code Review Checklist

- [ ] Error suppression has documented justification
- [ ] Root cause is identified and addressed
- [ ] Fix prevents recurrence, not just hides symptoms
- [ ] Similar patterns elsewhere are also fixed

### Shell Script Rule

```bash
# ❌ BAD — Lazy fix
command 2>/dev/null || true

# ✅ GOOD — Diagnose first, then targeted handling
command || {
    echo "Failed: $(command 2>&1)"
    exit 1
}
```

## Consequences

### Positive

- Problems actually get fixed
- No hidden technical debt
- Fewer repeat failures
- Codebase improves over time

### Negative

- Initial fix takes longer
- Requires deeper investigation

## Related

- ADR-0071: Fix Violations, Don't Exclude
