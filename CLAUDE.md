# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) and all AI agents when working with code in this repository.

## Agent Quick-Start Protocol

**Before writing any code**, follow this sequence:

1. **Read this file** — understand project structure, conventions, and anti-patterns
2. **Read `readme/adr/README.md`** — scan all CRITICAL-tier ADRs (0002, 0006, 0012, 0014, 0019, 0055, 0087, 0088)
3. **Check repo indexes** — `reports/repo-index/` has 34 pre-built indexes (class definitions, function signatures, route handlers, etc.) — use them before grepping
4. **Check `workflow_state.md`** — understand current phase and active work
5. **Begin work** — apply ADR constraints during all code generation

---

## Project Overview

**L9 Secure AI OS** is a production-grade autonomous agent runtime with:

- **10-Kernel Identity Stack** — YAML-configured governance/identity/behavior kernels
- **Agent Executor** — AgentExecutorService, AIOSRuntime for task-driven reasoning
- **Memory Substrate** — PostgreSQL + pgvector packet store, Neo4j knowledge graph, semantic embeddings
- **9 Orchestration Patterns** — Reasoning, Memory, ActionTool, WorldModel, Evolution, Meta, Pattern, ResearchSwarm, AgentExecution
- **Governance Engine** — Policy conflict resolution, approval gates, tool risk assessment
- **Tool Graph** — Registry-based tool dispatch with dynamic discovery and approval gates
- **WebSocket Orchestrator** — Real-time bidirectional agent communication
- **MCP Memory Server** — Model Context Protocol server for memory operations

---

## 🧠 Memory Stack Hierarchy (5-Layer)

All agents share a unified memory stack. Access via `agents/cursor/cursor_memory_client.py`.

| Layer | Technology | Purpose | Retention |
|-------|------------|---------|-----------|
| **L1: MCP** | MCP Server | Primary interface for agents | Persistent |
| **L2: Cache** | Redis | Session context, real-time state | 4-24 hours |
| **L3: Graph** | Neo4j | Relationships, repo structure, entities | Persistent |
| **L4: Store** | PostgreSQL | Canonical PacketStore + pgvector | Persistent |
| **L5: Local** | Markdown/YAML | Local configs, workflow_state.md | Persistent |

---

## 🔒 Unified Memory Pipeline

**Flow**: `Cursor -> Nginx (Port 80) -> l9-api (Port 8000) -> Substrate (Postgres/Neo4j)`

- **External Access**: Port 80 (Nginx) routes `/memory/*` to MCP server.
- **Internal Access**: Services talk directly via Docker network.
- **Validation**: `intake_node` in `substrate_dag.py` is the only validation point.

---

## 🛡️ Governance & Risk Tiers

| Tier | Risk | Approval Required | Examples |
|------|------|-------------------|----------|
| **T0** | Critical | **IGOR_APPROVAL** | Kernel changes, memory deletion |
| **T1** | High | **L_CTO_APPROVAL** | Tool registry updates, schema changes |
| **T2** | Medium | Auto-Gate | Feature work, refactors, documentation |

---

## 📊 Module Tier Mapping

| Tier | Scope | GMP Module |
|------|-------|------------|
| **KERNEL_TIER** | Kernels, Executor, Memory Core | GMP-System + GMP-Audit |
| **RUNTIME_TIER** | Task Queue, Tool Registry, Agents | GMP-Action + Integration-Tests |
| **INFRA_TIER** | Docker, K8s, Deploy Scripts | DEPLOYMENT_MANIFEST + Smoke Tests |
| **UX_TIER** | Frontend, Docs, Glue Scripts | Unit-Test-Quality + Generator |

---

## Build & Development Commands

```bash
# Local development
make dev              # Start local dev server
make test             # Run all pytest tests
make test-fast        # Run tests without slow markers
make test-smoke       # Run smoke tests only
make lint             # Run ruff linter & formatter
make typecheck        # Run mypy (api/, core/, memory/)

# Run single test
python3 -m pytest tests/path/to/test_file.py::test_function -v

# Docker
make docker-setup     # Setup .env from .env.template
make docker-env-check # Validate env vars for Docker
make docker-up        # Start dev stack (base + dev overlay)
make docker-up-prod   # Start prod stack (base + prod overlay)
make docker-build-prod # Build prod images
make docker-down      # Stop dev stack
make docker-logs      # Tail dev stack logs
make docker-clean     # Remove all L9 Docker resources
make smoke            # Run Docker smoke test (pre-commit)

# Deployment
make deploy           # Deploy to VPS (includes CI gates + smoke)
make deploy-dry       # Show what would be deployed (rsync dry run)
make rollback         # Rollback to previous VPS version
make vps-logs         # Tail VPS Docker logs
make vps-status       # Check VPS service status

# Database
make migrate          # Run migrations on VPS
make migrate-local    # Run migrations locally

# CI validation
make ci-validate      # Run all CI gates (SPEC, FILES)
make ci-spec          # Validate module spec v2.5
make ci-code          # Validate generated code
make ci-all-specs     # Validate all specs in repo

# Reports & utilities
make architecture-reports  # Generate architecture reports
make cursor-start          # Run Cursor session startup
make clean                 # Clean Python cache and build artifacts
make env-check             # Validate environment variables
make help                  # List all available targets
```

---

## Architecture Decision Records (ADRs)

**MANDATORY**: Read `readme/adr/README.md` before code operations. 92 ADRs total.

### CRITICAL ADRs (Must-Read)

| ADR  | Constraint                                                          |
| ---- | ------------------------------------------------------------------- |
| 0002 | Use `TYPE_CHECKING` for circular imports                            |
| 0006 | All operations emit PacketEnvelope audit trails                     |
| 0012 | Packets flow through DAG pipeline; validation in `intake_node` only |
| 0014 | Every module needs `__dora_meta__` dict                             |
| 0019 | Use structlog (not `print()` or standard `logging`)                 |
| 0055 | Fail loudly — no silent error swallowing                            |
| 0087 | SQL parameterization — never use f-strings for queries              |
| 0088 | No pickle serialization — use JSON/msgpack                          |

---

## Key Architecture Patterns

### PacketEnvelope (ADR-0006)

All meaningful operations emit `PacketEnvelope` for audit trail. Schema: `core/schemas/packet_envelope_v2.py`

### Memory DAG Pipeline (ADR-0012)

- Validation happens in `intake_node` only — no duplicate validation
- Canonical ingestion: `memory/ingestion.py` → `ingest_packet()`
- DAG pipeline: `memory/substrate_dag.py`

### DORA Compliance (ADR-0014)

Every module MUST have a DORA header and footer.

```python
# Header
__dora_meta__ = {
    "component_name": "My Component",
    "module_version": "1.0.0",
    "status": "active",
}

# Footer
__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}
```

### 10-Kernel Stack

Kernels loaded via YAML configs in `private/kernels/00_system/` by `runtime/kernel_loader.py`:
Master, Identity, Cognitive, Behavioral, Memory, WorldModel, Execution, Safety, Developer, Packet Protocol

### Protocol-Based Abstractions (ADR-0026)

Interfaces defined as `typing.Protocol` in `core/protocols/`. Concrete implementations depend on protocols, not other concrete classes.

### Singleton Auto-Registry (ADR-0004)

New singletons use `@register_singleton` decorator from `core/singleton_auto_registry.py`. Do NOT add try/except blocks to `_register_core_singletons()`.

---

## Directory Structure

### Core Runtime

| Directory             | Description                                                                   | Key Files                              |
| --------------------- | ----------------------------------------------------------------------------- | -------------------------------------- |
| `api/`                | FastAPI server, routes, auth, middleware, adapters (Slack, Email, Calendar)   | `server.py`, `routes/`                 |
| `core/agents/`        | AgentExecutorService, AIOSRuntime, AgentInstance, KernelRegistry              | `executor.py`, `registry.py`           |
| `core/governance/`    | Approval gates, policy engine, conflict resolution, tool risk                 | `engine.py`, `policy_engine.py`        |
| `core/tools/`         | Tool graph, registry, dynamic discovery, semantic search, capabilities        | `tool_graph.py`, `registry_adapter.py` |
| `core/observability/` | Five-tier observability: circuit breaker, Prometheus, Jaeger, security alerts | `circuit_breaker.py`                   |
| `core/protocols/`     | Protocol-based abstractions (memory, agent, kernel, observability)            | `*_protocols.py`                       |
| `core/schemas/`       | Pydantic models, PacketEnvelope schema                                        | `packet_envelope_v2.py`                |
| `runtime/`            | Kernel loader, task queue, Redis client, rate limiter, WebSocket, MCP client  | `kernel_loader.py`                     |
| `config/`             | Settings, DI config, policies, kernel discovery, agent configs, schemas       | `settings.py`, `di_config.py`          |

### Memory & Storage

| Directory       | Description                                                                      | Key Files                          |
| --------------- | -------------------------------------------------------------------------------- | ---------------------------------- |
| `memory/`       | Substrate service, DAG pipeline, ingestion, retrieval, consolidation, validators | `ingestion.py`, `substrate_dag.py` |
| `memory_cache/` | Working memory service, cache invalidation, versioned snapshots                  | `working_memory_service.py`        |
| `mcp_memory/`   | MCP Memory server — routes, substrate integration, safety                        | `src/routes/`                      |
| `migrations/`   | SQL migrations (0001–0031 + extras), applied sequentially                        | `0031_*.sql` (latest numbered)     |

---

## Slash Command Reference

| Command | Purpose |
|---------|---------|
| `/analyze_evaluate` | Combined deep analysis of module structure and compliance |
| `/gmp` | Governance Managed Process - phased execution |
| `/start-session` | Initialize session context and health check |
| `/end-session` | Close session, extract learnings, update workflow_state.md |
| `/index` | Regenerate repo index files |

---

## Critical Anti-Patterns (Never Do These)

| Anti-Pattern                                         | Correct Approach                                                                   | ADR  |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------- | ---- |
| `print()` or `logging.info()`                        | `structlog.get_logger(__name__)`                                                   | 0019 |
| `except:` or `except Exception: pass`                | Catch specific exceptions, log with `exc_info=True`, re-raise or emit error packet | 0055 |
| `f"SELECT * FROM x WHERE id={val}"`                  | `"SELECT * FROM x WHERE id = $1"` with params                                      | 0087 |
| `import Foo` at module level causing circular import | `if TYPE_CHECKING: import Foo`                                                     | 0002 |
| `pickle.dumps()` / `pickle.loads()`                  | `json.dumps()` / `msgpack`                                                         | 0088 |
| Sync I/O in async function (`time.sleep()`)          | `await asyncio.sleep()`                                                            | 0010 |
| Missing `__dora_meta__` in new module                | Add DORA header dict                                                               | 0014 |
| Hardcoded secrets in code                            | `os.getenv("SECRET_NAME")` with `.env`                                             | 0090 |
| Duplicate validation outside `intake_node`           | Validate only in `intake_node`                                                     | 0012 |
| `eval()` / `exec()` on untrusted input               | Safe alternatives per ADR-0095                                                     | 0095 |

---

## Code Conventions

- **Python**: 3.12+, ruff for linting/formatting, mypy with pydantic plugin
- **Logging**: structlog only (not standard logging, not print)
- **Imports**: Use `TYPE_CHECKING` for type-only imports to prevent circular imports
- **Async**: All database/network operations use async. Use `@must_stay_async` decorator.
- **Tests**: pytest with `asyncio_mode=auto`, markers: `slow`, `integration`
- **Type hints**: Modern `str | None` syntax (not `Optional[str]`)
- **Singletons**: Use `@register_singleton` decorator, not manual registration
- **Protocols**: Define in `core/protocols/`, use `@runtime_checkable` if `isinstance()` needed

---

## Environment Variables

### Required

| Variable            | Purpose                      |
| ------------------- | ---------------------------- |
| `DATABASE_URL`      | PostgreSQL connection string |
| `POSTGRES_PASSWORD` | PostgreSQL password          |
| `NEO4J_PASSWORD`    | Neo4j password               |
| `GRAFANA_PASSWORD`  | Grafana password             |

### Feature Flags

| Flag                            | Default | Purpose                                  |
| ------------------------------- | ------- | ---------------------------------------- |
| `L9_USE_KERNELS`                | `true`  | Load kernels from YAML files             |
| `L9_DYNAMIC_TOOL_DISCOVERY`     | `true`  | Enable dynamic tool discovery            |
| `L9_STAGE4_CONSOLIDATION`       | `true`  | Enable Stage 4 memory consolidation      |
| `L9_GRAPH_AGENT_STATE`          | `true`  | Enable graph-based agent state           |
| `L9_ENABLE_WS_ORCHESTRATOR`     | `true`  | WebSocket orchestrator                   |

---

## Testing Strategy

| Test Type | Command | Purpose |
|-----------|---------|---------|
| **Unit** | `make test-fast` | Fast validation of individual functions |
| **Integration** | `make test` | Cross-module flows and database links |
| **Smoke** | `make smoke` | Docker-level health check |
| **MRI** | `./scripts/deployment/deep_mri.sh` | Operational health on VPS |
| **GODMODE** | `./scripts/e2e_test_GODMODE.sh` | Full E2E validation on VPS |
