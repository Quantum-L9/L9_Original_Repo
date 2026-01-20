# ADR 0035: ADR Bootstrap Protocol

## Status
Accepted

## Context
ADR-0003 requires "Read all files in readme/adr/*.md at session start" — but how does an AI agent know to read ADRs if it hasn't read the ADR telling it to? This is a circular/bootstrap dependency.

Additionally, ADRs are the authoritative source for architectural constraints, but they're buried in a subdirectory that agents might not discover.

## Decision
Establish a **bootstrap protocol** that resolves the circular dependency:

### Bootstrap Entry Points (Priority Order)

1. **ROOT README.md** — Contains explicit pointer to ADRs with bootstrap instructions
2. **.cursor/rules/00-global.mdc** — Cursor-specific rules reference ADRs
3. **readme/adr/README.md** — ADR index with AI requirements

### Bootstrap Instructions (for AI Agents)

```
BEFORE ANY CODE OPERATION:
1. Read ROOT README.md → Find "Architecture Decision Records" section
2. Read readme/adr/README.md → Get ADR index
3. Scan all ADRs for Status: Accepted
4. Index key constraints from each ADR
5. Apply constraints during code analysis/generation
```

### Root README Must Contain

```markdown
## Architecture Decision Records (ADRs)

**MANDATORY FOR AI AGENTS**: Read ALL ADRs before code operations.

Location: `readme/adr/`
Index: `readme/adr/README.md`
Count: [N] ADRs (Accepted: [M])

Key architectural constraints are defined in ADRs. Violating them breaks L9.
```

## Files
- `README.md` (root) — Bootstrap entry point
- `readme/adr/README.md` — ADR index
- `.cursor/rules/00-global.mdc` — Cursor rules (references ADRs)

## Rules
1. Root README MUST reference ADRs with explicit bootstrap instructions
2. ADR reading is MANDATORY, not optional
3. This ADR is the exception to the "no circular reference" rule (it bootstraps the ADR system itself)
4. AI agents MUST check for ADR violations before proposing changes

## AI Guidance
**DO:**
- Read root README first in any new session
- Follow bootstrap protocol to discover ADRs
- Check proposed changes against all Accepted ADRs
- Flag ADR violations as blockers

**DO NOT:**
- Skip ADR reading because "it takes too long"
- Assume you know the ADRs from training data (they change)
- Propose changes that violate ADRs without explicit approval
- Create duplicate systems that ADRs already solve
