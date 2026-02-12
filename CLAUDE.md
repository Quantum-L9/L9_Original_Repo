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

| ADR | Constraint |
|-----|------------|
| 0002 | Use `TYPE_CHECKING` for circular imports |
| 0006 | All operations emit PacketEnvelope audit trails |
| 0012 | Packets flow through DAG pipeline; validation in `intake_node` only |
| 0014 | Every module needs `__dora_meta__` dict |
| 0019 | Use structlog (not `print()` or standard `logging`) |
| 0055 | Fail loudly — no silent error swallowing |
| 0087 | SQL parameterization — never use f-strings for queries |
| 0088 | No pickle serialization — use JSON/msgpack |

---

## Key Architecture Patterns

### PacketEnvelope (ADR-0006)
All meaningful operations emit `PacketEnvelope` for audit trail. Schema: `core/schemas/packet_envelope_v2.py`

### Memory DAG Pipeline (ADR-0012)
- Validation happens in `intake_node` only — no duplicate validation
- Canonical ingestion: `memory/ingestion.py` → `ingest_packet()`
- DAG pipeline: `memory/substrate_dag.py`

### DORA Metadata Block (ADR-0014)
Every module has a DORA header with `__dora_meta__` dict containing component_name, version, status.

### 10-Kernel Stack
Kernels loaded via YAML configs in `private/kernels/00_system/` by `runtime/kernel_loader.py`:
Master, Identity, Cognitive, Behavioral, Memory, WorldModel, Execution, Safety, Developer, Packet Protocol

### Protocol-Based Abstractions (ADR-0026)
Interfaces defined as `typing.Protocol` in `core/protocols/`. Concrete implementations depend on protocols, not other concrete classes.

### Singleton Auto-Registry (ADR-0004)
New singletons use `@register_singleton` decorator from `core/singleton_auto_registry.py`. Do NOT add try/except blocks to `_register_core_singletons()`.

### Governance Engine
Policy conflict resolution via `core/governance/engine.py`. Approval gates for high-risk tools. Authority hierarchy: Igor > L (CTO) > Research agents > Mac agent.

---

## Directory Structure

### Core Runtime

| Directory | Description | Key Files |
|-----------|-------------|-----------|
| `api/` | FastAPI server, routes, auth, middleware, adapters (Slack, Email, Calendar) | `server.py`, `routes/` |
| `core/agents/` | AgentExecutorService, AIOSRuntime, AgentInstance, KernelRegistry | `executor.py`, `registry.py` |
| `core/governance/` | Approval gates, policy engine, conflict resolution, tool risk | `engine.py`, `policy_engine.py` |
| `core/tools/` | Tool graph, registry, dynamic discovery, semantic search, capabilities | `tool_graph.py`, `registry_adapter.py` |
| `core/observability/` | Five-tier observability: circuit breaker, Prometheus, Jaeger, security alerts | `circuit_breaker.py` |
| `core/protocols/` | Protocol-based abstractions (memory, agent, kernel, observability) | `*_protocols.py` |
| `core/schemas/` | Pydantic models, PacketEnvelope schema | `packet_envelope_v2.py` |
| `runtime/` | Kernel loader, task queue, Redis client, rate limiter, WebSocket, MCP client | `kernel_loader.py` |
| `config/` | Settings, DI config, policies, kernel discovery, agent configs, schemas | `settings.py`, `di_config.py` |

### Memory & Storage

| Directory | Description | Key Files |
|-----------|-------------|-----------|
| `memory/` | Substrate service, DAG pipeline, ingestion, retrieval, consolidation, validators | `ingestion.py`, `substrate_dag.py` |
| `memory_cache/` | Working memory service, cache invalidation, versioned snapshots | `working_memory_service.py` |
| `mcp_memory/` | MCP Memory server — routes, substrate integration, safety | `src/routes/` |
| `migrations/` | SQL migrations (0001–0030 + extras), applied sequentially | `0030_*.sql` (latest numbered) |

### Orchestration & Agents

| Directory | Description | Key Files |
|-----------|-------------|-----------|
| `orchestrators/` | 9 orchestration patterns + registry | See below |
| `orchestration/` | TaskRouter, PlanExecutor, UnifiedController | `task_router.py` |
| `agents/` | L-CTO, architect, coder, research, cursor IDE integration | `cursor/cursor_memory_client.py` |
| `collaborative_cells/` | Multi-agent collaborative cell orchestration | |

### Orchestrator Patterns (in `orchestrators/`)

| Pattern | Orchestrator Class | Purpose |
|---------|-------------------|---------|
| `action_tool/` | ActionToolOrchestrator | Tool execution with validation |
| `agent_execution/` | AgentExecutionOrchestrator | Agent task lifecycle |
| `evolution/` | EvolutionOrchestrator | Self-improvement cycles |
| `memory/` | MemoryOrchestrator | Memory operations + housekeeping |
| `meta/` | MetaOrchestrator | Blueprint-driven orchestration |
| `pattern/` | PatternOrchestrator, MasterOrchestrator | Pattern matching + cell agents |
| `reasoning/` | ReasoningOrchestrator | Multi-step reasoning chains |
| `research_swarm/` | ResearchSwarmOrchestrator | Parallel research convergence |
| `world_model/` | WorldModelOrchestrator | World model sync + scheduling |

### Infrastructure & Services

| Directory | Description |
|-----------|-------------|
| `deploy/` | C1 Kubernetes deployment, Helm charts, nginx configs |
| `services/` | Research agents, symbolic computation, tool feedback |
| `workers/` | Background workers |
| `workflows/` | DAG workflows, GMP executor, harvest deploy |
| `telemetry/` | Metrics and observability exporters |
| `grafana/` | Grafana dashboards and datasources |

### Domain-Specific

| Directory | Description |
|-----------|-------------|
| `domain_tensor_bridge/` | Domain tensor bridge, reasoning engine |
| `world_model/` | World model engine, nodes, repository |
| `ir_engine/` | Intermediate representation engine |
| `motifs/` | Tensor motif linker, feedback graph |
| `simulation/` | Simulation engine |
| `email_agent/` | Email agent implementation |
| `mac_agent/` | Mac agent and WebSocket client |

### Development & Tooling

| Directory | Description |
|-----------|-------------|
| `tests/` | Unit, integration, smoke tests (~323 test files) |
| `scripts/` | Audit, memory, research, refactor scripts |
| `tools/` | ADR tooling, codegen, architecture report generators |
| `ci/` | CI checks (ADR, DORA, imports, tool wiring) |
| `reports/` | Architecture reports, **34 repo index files** |
| `private/` | Protected kernel configs, security specs |
| `readme/` | README pipeline, ADRs |

---

## Repo Index Files (Use Before Searching!)

`reports/repo-index/` contains **34 pre-built indexes**. Query these before grepping the codebase:

| Index | Use For |
|-------|---------|
| `class_definitions.txt` | "Where is class X?" — 1,900+ classes with paths |
| `function_signatures.txt` | "What args does Y take?" — 4,794 functions |
| `method_catalog.txt` | "What methods does X have?" — 5,288 methods |
| `inheritance_graph.txt` | "What extends BaseAgent?" — 802 relationships |
| `route_handlers.txt` | "What handles POST /api/memory?" — 180 routes |
| `pydantic_models.txt` | "What's the schema for X?" — 470 BaseModel subclasses |
| `async_function_map.txt` | "Is this function async?" — 2,599 async functions |
| `dynamic_tool_catalog.txt` | Tool discovery from core/tools/ |
| `agent_catalog.txt` | All agents |
| `kernel_catalog.txt` | All kernels |
| `orchestrator_catalog.txt` | All orchestrators |
| `imports.txt` | Import graph |
| `wiring_map.txt` | Module connections |
| `tree.txt` | Full directory tree |

Regenerate with: `python3 tools/export_repo_indexes.py`

---

## Critical Anti-Patterns (Never Do These)

| Anti-Pattern | Correct Approach | ADR |
|--------------|-----------------|-----|
| `print()` or `logging.info()` | `structlog.get_logger(__name__)` | 0019 |
| `except:` or `except Exception: pass` | Catch specific exceptions, log with `exc_info=True`, re-raise or emit error packet | 0055 |
| `f"SELECT * FROM x WHERE id={val}"` | `"SELECT * FROM x WHERE id = $1"` with params | 0087 |
| `import Foo` at module level causing circular import | `if TYPE_CHECKING: import Foo` | 0002 |
| `pickle.dumps()` / `pickle.loads()` | `json.dumps()` / `msgpack` | 0088 |
| Sync I/O in async function (`time.sleep()`) | `await asyncio.sleep()` | 0010 |
| Missing `__dora_meta__` in new module | Add DORA header dict | 0014 |
| Hardcoded secrets in code | `os.getenv("SECRET_NAME")` with `.env` | 0090 |
| Duplicate validation outside `intake_node` | Validate only in `intake_node` | 0012 |
| `eval()` / `exec()` on untrusted input | Safe alternatives per ADR-0041 | 0041 |

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

## Database & Migrations

PostgreSQL 16 with pgvector extension. Neo4j for knowledge graph.

- **Migrations directory**: `migrations/`
- **Total migrations**: 31 SQL + 1 Cypher
- **Latest numbered**: `0030_semantic_memory_scope_project_index.sql`
- **Naming convention**: `NNNN_description.sql` (sequential 4-digit prefix)
- **Runner**: `memory.migration_runner.run_migrations()` (invoked from `api/server.py` lifespan)
- **Apply locally**: `make migrate-local`
- **Apply to VPS**: `make migrate`

When creating new migrations, use the next number: **0031**.

---

## Environment Variables

### Required

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `NEO4J_PASSWORD` | Neo4j password |
| `GRAFANA_PASSWORD` | Grafana password |

### Optional

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | — | For embeddings (or use `EMBEDDING_PROVIDER=stub`) |
| `L9_API_KEY` | — | API authentication |
| `L9_OBSERVABILITY` | `true` | Enable observability |
| `L9_ENV` | `production` | Environment (`production` / `development`) |

### Feature Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `L9_USE_KERNELS` | `true` | Load kernels from YAML files |
| `L9_USE_KERNEL_CONFIG` | `true` | Use kernel config discovery |
| `L9_DI_ENABLED` | `true` | Enable dependency injection |
| `L9_DI_SUBSTRATES` | `false` | Enable DI for substrate services |
| `L9_OBSERVABILITY` | `true` | Enable observability stack |
| `L9_MINIMAL_MODE` | `false` | Minimal startup (skip optional services) |
| `L9_DYNAMIC_TOOL_DISCOVERY` | `true` | Enable dynamic tool discovery |
| `L9_MEMORY_WARMING_ENABLED` | `true` | Enable memory warming on startup |
| `L9_TOOL_PATTERN_EXTRACTION` | `true` | Enable tool pattern extraction |
| `L9_STAGE3_MODULES` | `true` | Enable Stage 3 module loading |
| `L9_STAGE4_CONSOLIDATION` | `true` | Enable Stage 4 memory consolidation |
| `L9_GRAPH_AGENT_STATE` | `true` | Enable graph-based agent state |
| `L9_GRAPH_WM_SYNC` | `true` | Enable world model graph sync |
| `L9_NEW_AGENT_INIT` | `true` | Use new agent initialization path |
| `L9_ENABLE_CALIBRATION` | `false` | Enable calibration system |
| `L9_ENABLE_BAYESIAN_REASONING` | `false` | Enable Bayesian reasoning kernel |
| `L9_GMP_LEARNING_ENABLED` | `false` | Enable GMP pattern learning |
| `L9_SKIP_STARTUP_CHECKS` | `false` | Skip startup health checks |
| `L9_ENABLE_LEGACY_CHAT` | `false` | Legacy chat endpoint (deprecated) |
| `L9_ENABLE_LEGACY_SLACK_ROUTER` | `false` | Legacy Slack router (deprecated) |
| `L9_ENABLE_WS_ORCHESTRATOR` | `true` | WebSocket orchestrator |
| `L9_ALLOW_STUB_EMBEDDINGS` | — | Allow stub embeddings (set to `"1"`) |

---

## Key Files for Understanding Codebase

| File | Purpose |
|------|---------|
| `api/server.py` | FastAPI entry point, lifespan, route registration |
| `core/agents/executor.py` | Core agent execution loop |
| `core/schemas/packet_envelope_v2.py` | PacketEnvelope schema |
| `core/governance/engine.py` | Governance policy evaluation |
| `core/tools/tool_graph.py` | Tool definitions and dispatch |
| `runtime/kernel_loader.py` | Kernel YAML loading and validation |
| `memory/ingestion.py` | `ingest_packet()` — canonical memory ingestion |
| `memory/substrate_dag.py` | Memory DAG pipeline |
| `memory/validators/packet_validator.py` | Packet validation |
| `config/settings.py` | Application settings and feature flags |
| `config/di_config.py` | Dependency injection factory functions |
| `orchestrators/orchestrator_registry.py` | Orchestrator auto-discovery |

---

## Testing

- **Test directory**: `tests/` (~323 test files)
- **Framework**: pytest with `asyncio_mode=auto`
- **Markers**: `@pytest.mark.slow`, `@pytest.mark.integration`
- **Run all**: `make test`
- **Run fast**: `make test-fast` (excludes slow markers)
- **Run single**: `python3 -m pytest tests/path/to/test.py::test_name -v`
- **Smoke tests**: `make test-smoke` or `make smoke` (Docker)
