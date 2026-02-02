# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

L9 Secure AI OS is a production-grade autonomous agent runtime with a 10-kernel identity stack, multi-layer memory substrate (PostgreSQL + pgvector), LangGraph-powered DAG orchestration, and governance engine with approval gates.

## Build & Development Commands

```bash
# Local development
make dev              # Start local dev server
make test             # Run all pytest tests
make test-fast        # Run tests without slow markers
make lint             # Run ruff linter & formatter
make typecheck        # Run mypy type checking

# Run single test
python3 -m pytest tests/path/to/test_file.py::test_function -v

# Docker
make docker-setup     # Setup .env from template
make docker-up        # Start dev stack (base + dev overlay)
make docker-down      # Stop dev stack
make smoke            # Run Docker smoke test (pre-commit)

# Deployment
make deploy           # Deploy to VPS (includes CI gates)
make vps-status       # Check VPS service status
```

## Architecture Decision Records (ADRs)

**MANDATORY**: Read `readme/adr/README.md` before code operations. Key ADRs:

| ADR | Constraint |
|-----|------------|
| 0002 | Use `TYPE_CHECKING` for circular imports |
| 0006 | All operations emit PacketEnvelope audit trails |
| 0012 | Packets flow through DAG pipeline; validation in `intake_node` only |
| 0014 | Every module needs DORA metadata block |
| 0019 | Use structlog (not standard logging) |

## Key Architecture Patterns

### PacketEnvelope (ADR-0006)
All meaningful operations emit `PacketEnvelope` for audit trail. Schema: `core/schemas/packet_envelope_v2.py`

### Memory DAG Pipeline (ADR-0012)
- Validation happens in `intake_node` only - no duplicate validation
- Canonical ingestion: `memory/ingestion.py` → `ingest_packet()`
- DAG pipeline: `memory/substrate_dag.py`

### DORA Metadata Block (ADR-0014)
Every module has a DORA header with `__dora_meta__` dict containing component_name, version, status.

### 10-Kernel Stack
Kernels loaded via YAML configs in `private/kernels/00_system/` by `runtime/kernel_loader.py`:
Master, Identity, Cognitive, Behavioral, Memory, WorldModel, Execution, Safety, Developer, Packet Protocol

## Directory Structure

- `api/` - FastAPI server, routes, adapters (Slack, Email, Calendar)
- `core/agents/` - AgentExecutorService, KernelRegistry
- `core/governance/` - Approval gates, pattern learning, validation
- `core/observability/` - Five-tier observability system
- `memory/` - PacketEnvelope storage, semantic search, retrieval
- `orchestrators/` - 7 orchestration patterns (Reasoning, Memory, ActionTool, WorldModel, Evolution, Meta, ResearchSwarm)
- `runtime/` - Kernel loader, task queue, WebSocket, MCP client
- `agents/cursor/` - Cursor IDE integration with LangGraph
- `private/kernels/` - Protected 10-kernel system configs

## Code Conventions

- **Python**: 3.12+, ruff for linting/formatting, mypy with pydantic plugin
- **Logging**: structlog only (not standard logging)
- **Imports**: Use `TYPE_CHECKING` for type-only imports to prevent circular imports
- **Async**: All database/network operations use async
- **Tests**: pytest with asyncio_mode=auto, markers: `slow`, `integration`

## Database & Migrations

PostgreSQL 16 with pgvector. Migrations in `migrations/` (0001-0024), apply sequentially:
```bash
make migrate-local    # Run migrations locally
```

## Environment Variables

Required:
- `DATABASE_URL` - PostgreSQL connection string
- `POSTGRES_PASSWORD`, `NEO4J_PASSWORD`, `GRAFANA_PASSWORD`

Optional:
- `OPENAI_API_KEY` - For embeddings (or use `EMBEDDING_PROVIDER=stub`)
- `L9_API_KEY` - API authentication
- `L9_OBSERVABILITY` - Enable observability (default: true)

## Key Files for Understanding Codebase

- `core/schemas/packet_envelope_v2.py` - PacketEnvelope schema
- `memory/validators/packet_validator.py` - Packet validation
- `memory/substrate_dag.py` - DAG pipeline
- `memory/ingestion.py` - `ingest_packet()` function
- `core/agents/executor.py` - Agent execution
- `api/server.py` - FastAPI entry point
