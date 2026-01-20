# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for the L9 codebase.

## AI Agent Requirements

**MANDATORY**: All AI agents (Cursor, L-CTO, CodeGenAgent) MUST read all ADRs at session startup
before performing any code operations. See ADR-0035 for bootstrap protocol.

**Bootstrap**: If you're reading this, you found the ADRs. Now scan all `Status: Accepted` ADRs
and apply their constraints during code analysis/generation.

## Current ADRs (37 total)

### Philosophy (0000)
| ADR | Title | Status |
|-----|-------|--------|
| [0000](./0000-l9-philosophy.md) | **L9 Philosophy — Automation First** | Accepted |

> **ADR-0000 is foundational.** All other ADRs derive from the automation-first principle.
> Every manual process should be automated. Every automation should be improved.
> AI code reviews MUST suggest automation opportunities.

### Foundation (0001-0013)
| ADR | Title | Status |
|-----|-------|--------|
| [0001](./0001-path-safety.md) | Sandboxed Path Resolution | Accepted |
| [0002](./0002-circular-import-prevention.md) | Circular Import Prevention | Accepted |
| [0003](./0003-documentation-standards.md) | Documentation Standards | Accepted |
| [0004](./0004-singleton-auto-registry.md) | Singleton Auto-Registry | Accepted |
| [0005](./0005-rls-shared-tenant-model.md) | RLS Shared Tenant Model | Accepted |
| [0006](./0006-packet-envelope-audit-trail.md) | PacketEnvelope Audit Trail | Accepted |
| [0007](./0007-seven-phase-bootstrap.md) | 7-Phase Bootstrap | Accepted |
| [0008](./0008-feature-flag-gating.md) | Feature Flag Gating | Accepted |
| [0009](./0009-circuit-breaker-resilience.md) | Circuit Breaker Resilience | Accepted |
| [0010](./0010-must-stay-async-decorator.md) | must_stay_async Decorator | Accepted |
| [0011](./0011-lazy-initialization-pattern.md) | Lazy Initialization | Accepted |
| [0012](./0012-memory-dag-pipeline.md) | Memory DAG Pipeline | Accepted |
| [0013](./0013-governance-authority-hierarchy.md) | Governance Authority | Accepted |

### Core Patterns (0014-0023)
| ADR | Title | Status |
|-----|-------|--------|
| [0014](./0014-dora-metadata-block.md) | DORA Metadata Block | Accepted |
| [0015](./0015-migration-sequential-apply.md) | Migration Sequential Apply | Accepted |
| [0016](./0016-typeddict-pydantic-boundary.md) | TypedDict vs Pydantic | Accepted |
| [0017](./0017-tool-definition-schema.md) | Tool Definition Schema | Accepted |
| [0018](./0018-async-retry-pattern.md) | Async Retry Pattern | Accepted |
| [0019](./0019-structlog-logging-standard.md) | structlog Logging | Accepted |
| [0020](./0020-test-fixture-hierarchy.md) | Test Fixture Hierarchy | Accepted |
| [0021](./0021-langgraph-node-wrapper.md) | LangGraph Node Wrapper | Accepted |
| [0022](./0022-registry-pattern.md) | Registry Pattern | Accepted |
| [0023](./0023-error-packet-pattern.md) | Error Packet Pattern | Accepted |

### Advanced Patterns (0024-0036)
| ADR | Title | Status |
|-----|-------|--------|
| [0024](./0024-resilience-mixin-pattern.md) | Resilience Mixin | Proposed |
| [0025](./0025-fastapi-dependency-injection.md) | FastAPI Dependency Injection | Accepted |
| [0026](./0026-protocol-based-abstractions.md) | Protocol-Based Abstractions | Accepted |
| [0027](./0027-lru-cache-pattern.md) | LRU Cache Pattern | Accepted |
| [0028](./0028-database-transaction-context.md) | Database Transaction Context | Accepted |
| [0029](./0029-embedding-generation-pipeline.md) | Embedding Generation | Accepted |
| [0030](./0030-kernel-yaml-schema.md) | Kernel YAML Schema | Accepted |
| [0031](./0031-websocket-connection-pattern.md) | WebSocket Connection | Accepted |
| [0032](./0032-neo4j-cypher-query-pattern.md) | Neo4j Cypher Query | Accepted |
| [0033](./0033-async-context-manager-pattern.md) | Async Context Manager | Accepted |
| [0034](./0034-agent-capability-scoping.md) | Agent Capability Scoping | Accepted |
| [0035](./0035-adr-bootstrap-protocol.md) | ADR Bootstrap Protocol | Accepted |
| [0036](./0036-schema-organization-pattern.md) | Schema Organization Pattern | Accepted |

## ADR Format (AI-Optimized)

**Canonical Schema:** `config/schemas/adr_schema.yaml`

All ADRs MUST follow this structure with copy-paste code templates:

```markdown
# ADR XXXX: Title

## Status
Accepted | Deprecated | Superseded | Proposed

## Pattern
[One-line description]

## Files
[Bullet list of affected files]

## Import Block
\```python
from package import Module, Class
\```

## Minimal Implementation
\```python
# Complete working example ready to copy-paste
class Example:
    ...
\```

## Usage Example
\```python
# How to use in practice
result = await example.method()
\```

## Anti-Pattern Example
\```python
# ❌ WRONG — Explanation
bad_example()

# ✅ CORRECT — Explanation  
good_example()
\```

## Rules
[Numbered list of invariants]

## AI Guidance
DO: [What to do]
DO NOT: [What not to do]
```

## Creating New ADRs

1. Use next sequential number: `XXXX-short-title.md`
2. Include: Status, Pattern, Files, Rules, AI Guidance
3. Update this README and `readme/repo-index/adr_catalog.txt`
