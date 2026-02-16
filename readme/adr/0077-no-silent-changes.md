# ADR-0077: No Silent Changes

**Status:** Accepted
**Date:** 2026-01-31
**Author:** Igor Beylin

## Context

Silent changes—placeholders added without disclosure, config values changed without mention, "cleanup" edits snuck in—break trust and cause subtle bugs that are hard to trace.

Example incident: Agent added `database_write` and `database_migrate` to `high_risk_tools.yaml` as "aspirational" tools. These tools don't exist. User caught it.

## Decision

**Policy: Every change must be visible, intentional, and disclosed.**

### Change Visibility Rules

1. **No silent placeholders** — Never add placeholder/aspirational items without explicit disclosure
2. **No drive-by edits** — Don't "fix" unrelated code while doing something else
3. **No undisclosed additions** — Everything added must be mentioned
4. **No hidden deletions** — Everything removed must be mentioned

### Disclosure Requirements

| Change Type        | Disclosure Required                                 |
| ------------------ | --------------------------------------------------- |
| Adding placeholder | "I'm adding X as placeholder because [reason]"      |
| Removing code      | "I'm removing X because [reason]"                   |
| Reformatting       | "I'm also reformatting [section] for consistency"   |
| Adding TODO        | "I'm adding TODO for [future work]"                 |
| Changing defaults  | "I'm changing default from X to Y because [reason]" |

### Placeholder Rules

Before adding ANY placeholder:

1. Ask: "Does this thing actually exist in the codebase?"
2. If NO: Don't add it, OR explicitly tell user and get approval
3. If adding: State "I'm adding X as a placeholder because [justifiable reason]"

Valid reasons for placeholders:

- Interface completeness (required by contract)
- Test stub (needed for test to compile)
- Configuration template (user will fill in)

Invalid reasons:

- "We might need this later"
- "Good to have"
- "I think this would be useful"

### Anti-Patterns

| Anti-Pattern                   | Why It's Wrong                       |
| ------------------------------ | ------------------------------------ |
| Adding unused config keys      | Confuses future maintainers          |
| "While I was there, I also..." | Scope creep, hidden changes          |
| Aspirational tools in policy   | Claims capabilities that don't exist |
| Silent reformatting            | Obscures real changes in diff        |

## Implementation

### Commit Message Requirements

Every commit must list:

- What was added (if anything)
- What was removed (if anything)
- What was changed (and why)

```
feat(module): add X functionality

Added:
- new_function() for handling Y
- NewClass for representing Z

Changed:
- existing_function() now accepts optional param
- DEFAULT_TIMEOUT from 30 to 60

Removed:
- deprecated_function() (unused since v2.0)
```

### Code Review Signals

Flag for review if:

- New config keys don't have corresponding code
- New imports aren't used
- New functions aren't called
- Placeholder comments without tracking issue

## Consequences

### Positive

- Changes are traceable
- No surprise behavior
- Trust maintained
- Easy code review

### Negative

- More verbose commit messages
- Can't "quickly fix" things noticed along the way

## Related

- ADR-0074: Surgical Edits Only
