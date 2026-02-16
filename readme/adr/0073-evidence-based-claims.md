# ADR-0073: Evidence-Based Claims

**Status:** Accepted
**Date:** 2026-01-31
**Author:** Igor Beylin

## Context

Claiming "it's fixed" without proof wastes time and erodes trust. When fixes aren't verified, problems reappear, causing rework cycles and frustration.

## Decision

**Policy: Never claim success without demonstrable evidence.**

### Evidence Requirements

| Claim                  | Required Evidence                           |
| ---------------------- | ------------------------------------------- |
| "Bug fixed"            | Test passes, error no longer reproduces     |
| "Feature works"        | Demo output, screenshot, or test result     |
| "Tests pass"           | Actual pytest/jest output with exit code 0  |
| "Deployed"             | Health check response, logs showing startup |
| "Performance improved" | Before/after metrics with numbers           |

### Evidence Format

```markdown
## Verification

**Claim:** [What you're claiming]

**Evidence:**
```

[Actual command output, test result, or screenshot]

```

**Exit code:** 0 ✓
```

### Anti-Patterns

| Anti-Pattern          | Why It's Wrong                |
| --------------------- | ----------------------------- |
| "It should work now"  | No proof provided             |
| "I tested it locally" | Where's the output?           |
| "Looks good to me"    | Subjective, not evidence      |
| "Fixed!" (no details) | What was fixed? How verified? |

### Verification Checklist

Before claiming any fix:

- [ ] Error condition no longer occurs
- [ ] Relevant tests pass (show output)
- [ ] Edge cases checked
- [ ] Exit code is 0
- [ ] Provide clickable file links for changed files

## Implementation

### Commit Message Pattern

```
fix(module): brief description

- Root cause: [what caused the issue]
- Fix: [what was changed]
- Verification: [how you proved it works]
- Tests: [which tests pass]
```

### PR Description Pattern

```markdown
## Changes

[What changed]

## Verification

[Command run and output]

## Test Results

[pytest/jest output]
```

## Consequences

### Positive

- Fixes are actually verified
- Trust is maintained
- Fewer "fixed but not really" issues
- Clear audit trail

### Negative

- Takes slightly longer to document
- Requires running verification commands

## Related

- ADR-0072: Diagnose Before Fix
