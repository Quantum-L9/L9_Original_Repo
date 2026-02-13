# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for the L9 codebase.

## AI Agent Bootstrap Protocol (ADR-0035)

**MANDATORY**: All AI agents (Cursor, Claude Code, L-CTO, CodeGenAgent) MUST:

1. Read this README at session startup
2. Scan all `Status: Accepted` ADRs — apply their constraints during code analysis/generation
3. Check proposed changes against CRITICAL-tier ADRs before committing
4. Treat ADR violations as **blockers** — do not merge violating code

## Priority Tiers

Not all ADRs are equal. Focus attention based on tier:

### CRITICAL — Must-Read Before Any Code Change

These ADRs enforce safety, audit, and structural invariants. Violating them breaks the system.

| ADR                                                   | Title                               | Constraint                                                |
| ----------------------------------------------------- | ----------------------------------- | --------------------------------------------------------- |
| [0002](./0002-circular-import-prevention.md)          | Circular Import Prevention          | Use `TYPE_CHECKING` for type-only imports                 |
| [0006](./0006-packet-envelope-audit-trail.md)         | PacketEnvelope Audit Trail          | All operations emit PacketEnvelope                        |
| [0012](./0012-memory-dag-pipeline.md)                 | Memory DAG Pipeline                 | Validation in `intake_node` only; no duplicate validation |
| [0014](./0014-dora-metadata-block.md)                 | DORA Metadata Block                 | Every module needs `__dora_meta__` dict                   |
| [0019](./0019-structlog-logging-standard.md)          | structlog Logging                   | Use structlog, never `print()` or `logging`               |
| [0055](./0055-fail-loudly-vs-graceful-degradation.md) | Fail-Loudly vs Graceful Degradation | Explicit failure semantics; no silent swallowing          |
| [0087](./0087-sql-parameterization.md)                | SQL Parameterization                | Never use f-strings for SQL; always parameterize          |
| [0088](./0088-no-pickle-serialization.md)             | No Pickle Serialization             | Never use pickle; use JSON/msgpack                        |

### IMPORTANT — Read When Working in Related Area

| ADR                                                 | Title                        | Area                 |
| --------------------------------------------------- | ---------------------------- | -------------------- |
| [0004](./0004-singleton-auto-registry.md)           | Singleton Auto-Registry      | Singletons, DI       |
| [0007](./0007-seven-phase-bootstrap.md)             | 7-Phase Bootstrap            | Server startup       |
| [0010](./0010-must-stay-async-decorator.md)         | must_stay_async Decorator    | Async enforcement    |
| [0013](./0013-governance-authority-hierarchy.md)    | Governance Authority         | Approval gates       |
| [0025](./0025-fastapi-dependency-injection.md)      | FastAPI Dependency Injection | API routes           |
| [0026](./0026-protocol-based-abstractions.md)       | Protocol-Based Abstractions  | Interfaces           |
| [0030](./0030-kernel-yaml-schema.md)                | Kernel YAML Schema           | Kernel configs       |
| [0034](./0034-agent-capability-scoping.md)          | Agent Capability Scoping     | Tool access          |
| [0037](./0037-tool-wiring-protocol.md)              | Tool Wiring Protocol         | Tool registration    |
| [0052](./0052-di-dip-foundation.md)                 | DI/DIP Foundation            | Dependency injection |
| [0064](./0064-dynamic-tool-discovery.md)            | Dynamic Tool Discovery       | Tool discovery       |
| [0068](./0068-unified-resilience-protocol-layer.md) | Unified Resilience Protocol  | Error handling       |

### REFERENCE — Consult As Needed

All remaining ADRs. See the full inventory below.

---

## ADR Dependency Map

```
0000 (Core Philosophy)
 ├── 0006 (PacketEnvelope) ──→ 0012 (Memory DAG) ──→ 0023 (Error Packet)
 ├── 0002 (Circular Import) ──→ 0026 (Protocol Abstractions) ──→ 0052 (DI/DIP)
 ├── 0013 (Governance Authority) ──→ 0034 (Agent Capability) ──→ 0044 (Agent Policy)
 ├── 0007 (Bootstrap) ──→ 0004 (Singleton Registry) ──→ 0011 (Lazy Init)
 ├── 0017 (Tool Schema) ──→ 0037 (Tool Wiring) ──→ 0064 (Dynamic Discovery)
 ├── 0030 (Kernel YAML) ──→ 0053 (Kernel Externalization)
 ├── 0009 (Circuit Breaker) ──→ 0024 (Resilience Mixin) ──→ 0068 (Unified Resilience)
 ├── 0019 (structlog) ──→ 0014 (DORA Metadata)
 └── 0035 (ADR Bootstrap) ──→ 0065 (Cursor ADR Enforcement)
```

---

## Complete ADR Inventory (92 files)

### Philosophy (0000)

| ADR                               | Title                                            | Status   |
| --------------------------------- | ------------------------------------------------ | -------- |
| [0000](./0000-core-philosophy.md) | L9 Core Philosophy — Automation-First, 100% Done | Accepted |

### Foundation (0001–0013)

| ADR                                              | Title                                            | Status   |
| ------------------------------------------------ | ------------------------------------------------ | -------- |
| [0001](./0001-path-safety.md)                    | Sandboxed Path Resolution                        | Accepted |
| [0002](./0002-circular-import-prevention.md)     | Circular Import Prevention via TYPE_CHECKING     | Accepted |
| [0003](./0003-documentation-standards.md)        | Documentation Standards for AI-Readable Codebase | Accepted |
| [0004](./0004-singleton-auto-registry.md)        | Singleton Auto-Registry Pattern                  | Accepted |
| [0005](./0005-rls-shared-tenant-model.md)        | RLS Shared Tenant Model                          | Accepted |
| [0006](./0006-packet-envelope-audit-trail.md)    | PacketEnvelope Audit Trail                       | Accepted |
| [0007](./0007-seven-phase-bootstrap.md)          | 7-Phase Bootstrap Ceremony                       | Accepted |
| [0008](./0008-feature-flag-gating.md)            | Feature Flag Gating Pattern                      | Accepted |
| [0009](./0009-circuit-breaker-resilience.md)     | Circuit Breaker Resilience                       | Accepted |
| [0010](./0010-must-stay-async-decorator.md)      | must_stay_async Decorator                        | Accepted |
| [0011](./0011-lazy-initialization-pattern.md)    | Lazy Initialization Pattern                      | Accepted |
| [0012](./0012-memory-dag-pipeline.md)            | Memory DAG Pipeline                              | Accepted |
| [0013](./0013-governance-authority-hierarchy.md) | Governance Authority Hierarchy                   | Accepted |

### Core Patterns (0014–0023)

| ADR                                           | Title                          | Status                            |
| --------------------------------------------- | ------------------------------ | --------------------------------- |
| [0014](./0014-dora-metadata-block.md)         | DORA Metadata Block Pattern    | Accepted                          |
| [0015](./0015-migration-sequential-apply.md)  | Migration Sequential Apply     | Accepted                          |
| [0016](./0016-typeddict-pydantic-boundary.md) | TypedDict vs Pydantic Boundary | Accepted                          |
| [0017](./0017-tool-definition-schema.md)      | Tool Definition Schema         | Accepted                          |
| ~~0018~~                                      | ~~Async Retry Pattern~~        | **Missing — file does not exist** |
| [0019](./0019-structlog-logging-standard.md)  | structlog Logging Standard     | Accepted                          |
| [0020](./0020-test-fixture-hierarchy.md)      | Test Fixture Hierarchy         | Accepted                          |
| [0021](./0021-langgraph-node-wrapper.md)      | LangGraph Node Wrapper Pattern | Accepted                          |
| [0022](./0022-registry-pattern.md)            | Registry Pattern               | Accepted                          |
| [0023](./0023-error-packet-pattern.md)        | Error Packet Pattern           | Accepted                          |

### Advanced Patterns (0024–0040)

| ADR                                             | Title                         | Status   |
| ----------------------------------------------- | ----------------------------- | -------- |
| [0024](./0024-resilience-mixin-pattern.md)      | Resilience Mixin Pattern      | Accepted |
| [0025](./0025-fastapi-dependency-injection.md)  | FastAPI Dependency Injection  | Accepted |
| [0026](./0026-protocol-based-abstractions.md)   | Protocol-Based Abstractions   | Accepted |
| [0027](./0027-lru-cache-pattern.md)             | LRU Cache Pattern             | Accepted |
| [0028](./0028-database-transaction-context.md)  | Database Transaction Context  | Accepted |
| [0029](./0029-embedding-generation-pipeline.md) | Embedding Generation Pipeline | Accepted |
| [0030](./0030-kernel-yaml-schema.md)            | Kernel YAML Schema            | Accepted |
| [0031](./0031-websocket-connection-pattern.md)  | WebSocket Connection Pattern  | Accepted |
| [0032](./0032-neo4j-cypher-query-pattern.md)    | Neo4j Cypher Query Pattern    | Accepted |
| [0033](./0033-async-context-manager-pattern.md) | Async Context Manager Pattern | Accepted |
| [0034](./0034-agent-capability-scoping.md)      | Agent Capability Scoping      | Accepted |
| [0035](./0035-adr-bootstrap-protocol.md)        | ADR Bootstrap Protocol        | Accepted |
| [0036](./0036-schema-organization-pattern.md)   | Schema Organization Pattern   | Accepted |
| [0037](./0037-tool-wiring-protocol.md)          | Tool Wiring Protocol          | Accepted |
| [0038](./0038-secrets-management-protocol.md)   | Secrets Management Protocol   | Proposed |
| [0039](./0039-l9-cli-tool.md)                   | L9 CLI Tool                   | Proposed |
| [0040](./0040-ci-cd-security-scanning.md)       | CI/CD Security Scanning       | Proposed |

### Refactoring Patterns (0041–0055)

| ADR                                                              | Title                                 | Status   |
| ---------------------------------------------------------------- | ------------------------------------- | -------- |
| [0041 (builder)](./0041-executor-builder-pattern.md)             | Executor Builder Pattern              | Proposed |
| [0041 (eval)](./0041-unsafe-eval-remediation.md)                 | Unsafe eval() Remediation             | Proposed |
| [0042](./0042-execution-profiles.md)                             | Execution Profiles                    | Proposed |
| [0043 (controller)](./0043-controller-profiles.md)               | Controller Profiles                   | Proposed |
| [0043 (security)](./0043-security-rate-limiting-architecture.md) | Security & Rate Limiting Architecture | Accepted |
| [0044](./0044-agent-policy-protocols.md)                         | Agent Policy Protocols                | Proposed |
| [0045](./0045-online-offline-execution-split.md)                 | Online/Offline Execution Split        | Proposed |
| [0046](./0046-pipeline-stage-organization.md)                    | Pipeline Stage Organization           | Proposed |
| [0047](./0047-memory-facade-decomposition.md)                    | Memory Facade Decomposition           | Proposed |
| [0048](./0048-tool-dispatch-strategy.md)                         | Tool Dispatch Strategy                | Proposed |
| [0049](./0049-checkpoint-plan-snapshots.md)                      | Checkpoint Plan Snapshots             | Proposed |
| [0050](./0050-tool-registry-cache.md)                            | Tool Registry Cache                   | Proposed |
| [0051](./0051-cursor-file-organization.md)                       | Cursor File Organization              | Accepted |
| [0052](./0052-di-dip-foundation.md)                              | DI/DIP Foundation                     | Accepted |
| [0053](./0053-kernel-config-externalization.md)                  | Kernel Configuration Externalization  | Accepted |
| [0054](./0054-loop-stage-protocol.md)                            | Loop Stage Protocol                   | Proposed |
| [0055](./0055-fail-loudly-vs-graceful-degradation.md)            | Fail-Loudly vs Graceful Degradation   | Accepted |

### Infrastructure & Deployment (0058–0070)

| ADR                                                           | Title                                         | Status      |
| ------------------------------------------------------------- | --------------------------------------------- | ----------- |
| [0058](./0058-c1-deployment-workflow.md)                      | C1 Kubernetes Deployment Workflow             | Accepted    |
| [0059](./0059-inline-analysis-script-reports.md)              | Inline Analysis with Script-Generated Reports | Accepted    |
| [0060](./0060-mediator-pattern-agent-communication.md)        | Mediator Pattern for Agent Communication      | Accepted    |
| [0061](./0061-l9-facade-simplified-api.md)                    | L9 Facade Pattern for Simplified API          | Accepted    |
| [0062](./0062-deferred-strict-linting.md)                     | Deferred Strict Linting Configuration         | Accepted    |
| [0063](./0063-incremental-config-adoption.md)                 | Incremental Configuration Adoption            | Accepted    |
| [0064](./0064-dynamic-tool-discovery.md)                      | Dynamic Tool Discovery                        | Implemented |
| [0065](./0065-cursor-adr-enforcement.md)                      | Cursor ADR Enforcement Rules                  | Accepted    |
| [0066 (S3)](./0066-aws-s3-storage-architecture.md)            | AWS S3 Storage Architecture                   | Accepted    |
| [0066 (governance)](./0066-governance-authority-superpack.md) | Governance & Authority Superpack              | Reference   |
| [0067](./0067-aws-secrets-manager-integration.md)             | AWS Secrets Manager Integration               | Accepted    |
| [0068](./0068-unified-resilience-protocol-layer.md)           | Unified Resilience Protocol Layer             | Accepted    |
| [0069](./0069-automated-documentation-generation.md)          | Automated Documentation Generation            | Accepted    |
| [0070](./0070-session-dag-workflow-orchestration.md)          | Session DAG Workflow Orchestration            | Implemented |

### Agent Behavior Rules (0071–0091)

These ADRs codify lessons learned from agent mistakes. They govern how AI agents interact with the codebase.

| ADR                                                 | Title                                    | Status   |
| --------------------------------------------------- | ---------------------------------------- | -------- |
| [0071](./0071-fix-violations-not-exclude.md)        | Fix Violations, Don't Exclude            | Accepted |
| [0072](./0072-diagnose-before-fix.md)               | Diagnose Before Fix                      | Accepted |
| [0073](./0073-evidence-based-claims.md)             | Evidence-Based Claims                    | Accepted |
| [0074](./0074-surgical-edits-only.md)               | Surgical Edits Only                      | Accepted |
| [0075](./0075-ask-before-build.md)                  | Ask Before Build                         | Accepted |
| [0076](./0076-search-before-create.md)              | Search Before Create                     | Accepted |
| [0077](./0077-no-silent-changes.md)                 | No Silent Changes                        | Accepted |
| [0078](./0078-explicit-approval-destructive-ops.md) | Explicit Approval for Destructive Ops    | Accepted |
| [0079](./0079-real-data-only.md)                    | Real Data Only                           | Accepted |
| [0080](./0080-understand-user-intent.md)            | Understand User Intent                   | Accepted |
| [0081](./0081-phase-discipline.md)                  | Phase Discipline                         | Accepted |
| [0082](./0082-neo4j-required-not-optional.md)       | Neo4j is Required, Not Optional          | Accepted |
| [0083](./0083-datetime-utc-standard.md)             | Datetime UTC Standard                    | Accepted |
| [0084](./0084-async-resource-cleanup.md)            | Async Resource Cleanup Pattern           | Accepted |
| [0085](./0085-thread-safe-singletons.md)            | Thread-Safe Singleton Pattern            | Accepted |
| [0086](./0086-safe-type-conversion.md)              | Safe Type Conversion Pattern             | Accepted |
| [0087](./0087-sql-parameterization.md)              | SQL Parameterization Standard            | Accepted |
| [0088](./0088-no-pickle-serialization.md)           | No Pickle Serialization                  | Accepted |
| [0089](./0089-hierarchical-compose-symlinks.md)     | Hierarchical Compose and C1 Symlinks     | Accepted |
| [0090](./0090-no-hardcoded-credentials-in-rules.md) | No Hardcoded Credentials in Cursor Rules | Accepted |
| [0091](./0091-definition-of-done.md)                | Definition of Done (Enforceable)         | Accepted |

> **Note:** ADR numbers 0041, 0043, and 0066 each have two files with different topics sharing the same number. These are listed separately above. Future ADRs should use the next available number (0092+).

---

## Status Summary

| Status          | Count  |
| --------------- | ------ |
| Accepted        | 72     |
| Proposed        | 15     |
| Implemented     | 2      |
| Reference       | 1      |
| Missing (0018)  | 1      |
| **Total files** | **92** |

---

## ADR Format (AI-Optimized)

**Canonical Schema:** `config/schemas/adr_schema.yaml`

All ADRs MUST follow this structure with copy-paste code templates:

````markdown
# ADR XXXX: Title

## Status

Accepted | Deprecated | Superseded | Proposed

## Pattern

[One-line description]

## Files

[Bullet list of affected files]

## Import Block

```python
from package import Module, Class
```

## Minimal Implementation

```python
# Complete working example ready to copy-paste
class Example:
    ...
```

## Usage Example

```python
# How to use in practice
result = await example.method()
```

## Anti-Pattern Example

```python
# ❌ WRONG — Explanation
bad_example()

# ✅ CORRECT — Explanation
good_example()
```

## Rules

[Numbered list of invariants]

## AI Guidance

DO: [What to do]
DO NOT: [What not to do]
````

## Creating New ADRs

1. Use next sequential number: `0092-short-title.md` (next available)
2. Include all sections: Status, Pattern, Files, Import Block, Rules, AI Guidance
3. Update this README — add to the correct category table
4. Update `reports/repo-index/adr_catalog.txt` via `python3 tools/export_repo_indexes.py`
