# ADR-0078: Explicit Approval for Destructive Operations

**Status:** Accepted
**Date:** 2026-01-31
**Author:** Igor Beylin

## Context

Destructive operations—server rebuilds, file deletions, database drops, production deployments—cannot be undone. Executing them without explicit approval causes catastrophic failures.

Example incident (2026-01-21): Agent rebuilt C1 server via Hetzner API without asking. User had not approved. Critical governance violation.

Example incident (2026-01-20): Agent deleted `core/symbolic_computation/` (8 files, ~1,200 lines) because "nothing imports it." User had intentionally preserved it.

## Decision

**Policy: Destructive operations require explicit user approval before execution.**

### Destructive Operations (Always Require Approval)

| Category       | Operations                                 |
| -------------- | ------------------------------------------ |
| Infrastructure | Server rebuild, server delete, DNS changes |
| Files          | `rm -rf`, folder deletion, file moves      |
| Database       | DROP TABLE, TRUNCATE, DELETE without WHERE |
| Git            | force push, hard reset, branch deletion    |
| Deployment     | Production deploy, rollback                |

### Approval Protocol

Before ANY destructive operation:

1. **STOP** — Do not execute
2. **PROPOSE** — "I recommend [action]. This will [consequence]."
3. **EXPLAIN** — What will be lost/changed
4. **ASK** — "Do I have your explicit approval?"
5. **WAIT** — Only proceed after explicit "yes" or "approved"

### Approval Phrases (Proceed)

- "yes, delete it"
- "approved"
- "go ahead"
- "yes, rebuild"
- User explicitly types the command themselves

### Non-Approval Phrases (DO NOT Proceed)

- Silence
- "let me check"
- "maybe"
- "I'm not sure"
- General discussion about the operation

### "Nothing imports it" is NOT Approval

Code may be valuable even if not currently imported:

- In-progress work
- Alternative implementation
- Intentionally preserved
- Future work
- Reference implementation

### Anti-Patterns

| Anti-Pattern                  | Why It's Wrong               |
| ----------------------------- | ---------------------------- |
| "I'll just clean this up"     | Destructive without approval |
| "This looks like a duplicate" | Assumption, not fact         |
| "Nothing uses this"           | Not sufficient justification |
| "I'll rebuild to fix it"      | Disproportionate response    |

## Implementation

### Pre-Destructive Checklist

Before any destructive operation:

- [ ] Is there a non-destructive alternative?
- [ ] Have I explained the consequences?
- [ ] Have I received explicit approval?
- [ ] Have I documented the approval?

### Shell Command Guards

```bash
# ❌ BAD — No confirmation
rm -rf $FOLDER

# ✅ GOOD — Require confirmation
echo "About to delete $FOLDER ($(find $FOLDER -type f | wc -l) files)"
read -p "Type 'yes' to confirm: " confirm
[ "$confirm" = "yes" ] && rm -rf $FOLDER
```

### API Call Guards

```python
# ❌ BAD — No confirmation
client.servers.rebuild(server_id)

# ✅ GOOD — Require confirmation
print(f"⚠️  DESTRUCTIVE: Rebuild server {server_id}")
print("This will wipe all data. Type 'REBUILD' to confirm:")
if input() == "REBUILD":
    client.servers.rebuild(server_id)
```

## Consequences

### Positive

- No accidental data loss
- User maintains control
- Clear audit trail
- Recovery possible (approval = checkpoint)

### Negative

- Slower execution of destructive tasks
- Requires explicit interaction

## Related

- ADR-0063: No Silent Changes
