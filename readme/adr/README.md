# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for the L9 codebase.

## AI Agent Requirements (ADR-0003)

**MANDATORY**: All AI agents (Cursor, L-CTO, CodeGenAgent) MUST read all ADRs at session startup
before performing any code operations.

```
STARTUP PROTOCOL:
1. Read all files in readme/adr/*.md
2. Parse ADR status (Accepted, Deprecated, Superseded)
3. Index patterns mentioned in ADRs
4. Apply ADR guidance during code analysis
```

## Current ADRs

| ADR | Title | Status |
|-----|-------|--------|
| [0001](./0001-path-safety.md) | Sandboxed Path Resolution for Research Factory | Accepted |
| [0002](./0002-circular-import-prevention.md) | Circular Import Prevention via TYPE_CHECKING Pattern | Accepted |
| [0003](./0003-documentation-standards.md) | Documentation Standards for AI-Readable Codebase | Accepted |
| [0004](./0004-singleton-auto-registry.md) | Singleton Auto-Registry Pattern | Accepted |
| [0005](./0005-rls-shared-tenant-model.md) | RLS Shared Tenant Model | Accepted |
| [0006](./0006-packet-envelope-audit-trail.md) | PacketEnvelope Audit Trail | Accepted |
| [0007](./0007-seven-phase-bootstrap.md) | 7-Phase Bootstrap Ceremony | Accepted |
| [0008](./0008-feature-flag-gating.md) | Feature Flag Gating Pattern | Accepted |
| [0009](./0009-circuit-breaker-resilience.md) | Circuit Breaker Resilience | Accepted |
| [0010](./0010-must-stay-async-decorator.md) | must_stay_async Decorator | Accepted |
| [0011](./0011-lazy-initialization-pattern.md) | Lazy Initialization Pattern | Accepted |
| [0012](./0012-memory-dag-pipeline.md) | Memory DAG Pipeline | Accepted |
| [0013](./0013-governance-authority-hierarchy.md) | Governance Authority Hierarchy | Accepted |

## ADR Format

Each ADR follows this structure:

```markdown
# ADR XXXX: Title

## Status
Accepted | Deprecated | Superseded

## Context
[Why this decision was needed]

## Decision
[What we decided and how to implement it]

## Consequences
[Positive, Neutral, and Negative impacts]

## AI Reviewer Guidance
[What NOT to flag as issues]
```

## Creating New ADRs

1. Use the next sequential number: `XXXX-short-title.md`
2. Include all required sections (Status, Context, Decision, Consequences)
3. Add AI Reviewer Guidance section for patterns AI might incorrectly flag
4. Update this README with the new ADR
5. Reference the ADR in relevant code files

## References

- ADR-0003: Documentation Standards (defines this structure)
- PEP 257: Docstring Conventions
- Michael Nygard's ADR format: https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
