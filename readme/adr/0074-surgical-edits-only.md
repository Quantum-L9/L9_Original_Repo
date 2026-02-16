# ADR-0074: Surgical Edits Only

**Status:** Accepted
**Date:** 2026-01-31
**Author:** Igor Beylin

## Context

Rewriting entire files to make small changes is dangerous, inefficient, and destroys version control clarity. It introduces bugs, loses context, and makes code review impossible.

December 2025 incident: Cursor destroyed `docker-compose.yml` by using the `write` tool (full rewrite) instead of `search_replace` for a single service change. Result: All backend services offline, ~2 hour recovery.

## Decision

**Policy: Make surgical, targeted edits. Never rewrite entire files.**

### Edit Tool Selection

| Scenario                | Tool                         | Why                  |
| ----------------------- | ---------------------------- | -------------------- |
| Change one function     | `search_replace`             | Minimal diff         |
| Add import              | `search_replace` at file top | Precise insertion    |
| Fix bug in method       | `search_replace` on method   | Targeted fix         |
| Create new file         | `write`                      | File doesn't exist   |
| Complete rewrite needed | **ASK FIRST**                | Rare, needs approval |

### Never Use `write` Tool On

- `docker-compose.yml`
- `Dockerfile`
- `.env` files
- `Caddyfile`
- Any infrastructure config
- Any file > 100 lines that exists

### Surgical Edit Principles

1. **Minimal context** — Include only enough surrounding code to identify the location
2. **Preserve formatting** — Match existing indentation, style, whitespace
3. **One concern per edit** — Don't combine unrelated changes
4. **Review-friendly** — Diff should clearly show intent

### Anti-Patterns

| Anti-Pattern                       | Why It's Wrong                        |
| ---------------------------------- | ------------------------------------- |
| Full file rewrite for small change | Destroys git history, introduces bugs |
| "Let me regenerate the whole file" | Loses comments, context, formatting   |
| Combining 10 changes in one edit   | Can't review or rollback individually |
| Reformatting unchanged code        | Creates noise in diffs                |

### When Full Rewrite IS Acceptable

Only with explicit approval when:

- File is < 50 lines and completely wrong
- User explicitly requests "rewrite from scratch"
- Creating a new file that doesn't exist

## Implementation

### Edit Size Limits

| File Type     | Max Edits Before Asking |
| ------------- | ----------------------- |
| Config files  | 3                       |
| Source code   | 10                      |
| Tests         | 10                      |
| Documentation | 15                      |

If more edits needed: "This file needs significant changes. Should I proceed with [N] edits, or would you prefer a different approach?"

### Pre-Edit Checklist

- [ ] Is this the minimal change to achieve the goal?
- [ ] Am I using `search_replace`, not `write`?
- [ ] Does the diff clearly show the intent?
- [ ] Will code review be easy?

## Consequences

### Positive

- Clean git history
- Easy code review
- Fewer accidental changes
- Safer refactoring

### Negative

- Multiple small edits instead of one big one
- Requires more careful planning

## Related

- ADR-0072: Diagnose Before Fix
- ADR-0073: Evidence-Based Claims
