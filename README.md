# L9 Secure AI OS

> **Version:** 2.2.0  
> **Status:** Production Ready (VPS Deployed)  
> **Updated:** 2026-01-11

---

## Overview

**L9 Secure AI OS** is a governed, production-grade autonomous agent runtime with:

- **10-Kernel Identity Stack** — Master, Identity, Cognitive, Behavioral, Memory, WorldModel, Execution, Safety, Developer, and Packet Protocol kernels
- **Memory Substrate** — PostgreSQL + pgvector for semantic & episodic memory with audit trails
- **Agent Executor** — LangGraph-powered DAG orchestration with tool dispatch and approval gates
- **World Model** — Insight-driven entity/relationship tracking with scheduled updates
- **7 Orchestrators** — Reasoning, Memory, ActionTool, WorldModel, Evolution, Meta, and ResearchSwarm
- **Governance Engine** — Closed-loop learning from Igor approvals, compliance audit trails
- **Five-Tier Observability** — Distributed tracing, failure detection, context strategies, metrics aggregation, multi-backend export (Console, Substrate, Datadog, Honeycomb)

**Primary Goals:**
- Secure, governed runtime for autonomous AI agents
- Multi-layer memory (short-term, long-term, semantic, audit) with retrieval
- Tool execution with sandboxing, approval gates, and rollback
- Full observability: structured logging, packet trails, compliance reporting

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         L9 API Server (FastAPI)                         │
│  ┌──────────┐ ┌───────────┐ ┌─────────┐ ┌──────────┐ ┌───────────────┐  │
│  │OS Routes │ │Agent      │ │Memory   │ │WebSocket │ │Slack/Research │  │
│  │          │ │Routes     │ │Routes   │ │/wsagent  │ │/compliance    │  │
│  └────┬─────┘ └─────┬─────┘ └────┬────┘ └────┬─────┘ └───────┬───────┘  │
└───────┼─────────────┼────────────┼───────────┼───────────────┼──────────┘
        │             │            │           │               │
        ▼             ▼            ▼           ▼               ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                       Core Agent Execution Layer                          │
│  AgentExecutorService → KernelAwareAgentRegistry → AIOSRuntime            │
│  (10-kernel stack)    (agent configs + tools)    (reasoning loop)         │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│  Memory Substrate │   │     Orchestrators     │   │   Governance Engine   │
│  ├─ PacketStore   │   │  ├─ ReasoningOrch     │   │  ├─ ApprovalManager   │
│  ├─ SemanticMemory│   │  ├─ MemoryOrch        │   │  ├─ GovernancePatterns│
│  ├─ KnowledgeFacts│   │  ├─ ActionToolOrch    │   │  ├─ AdaptivePrompting │
│  └─ InsightGraph  │   │  ├─ WorldModelOrch    │   │  └─ ComplianceAudit   │
└─────────┬─────────┘   │  ├─ EvolutionOrch     │   └───────────────────────┘
          │             │  ├─ MetaOrch          │
          ▼             │  └─ ResearchSwarmOrch │
┌───────────────────┐   └───────────────────────┘
│ PostgreSQL+pgvector│
│ (l9_memory DB)     │
└────────────────────┘
```

---

## Directory Structure

```
L9/
├── api/                      # FastAPI server & routes
│   ├── server.py             # Main app, lifespan, WebSocket
│   ├── routes/               # Modular routers (commands, compliance, worldmodel)
│   ├── memory/               # Memory API router
│   ├── adapters/             # External adapters (Slack, Email, Calendar, Twilio)
│   └── webhook_slack.py      # Slack event handling
├── agents/                   # Agent implementations
│   ├── cursor/               # Cursor IDE integration (consolidated)
│   │   ├── cursor_memory_kernel.py
│   │   ├── cursor_client.py
│   │   ├── integrations/     # LangGraph integration (GMP-48 complete)
│   │   │   ├── cursor_langgraph.py
│   │   │   ├── cursor_gateway.py
│   │   │   └── cursor_executor.py
│   │   ├── scripts/          # Cursor-specific scripts
│   │   ├── extractors/       # Action extractors
│   │   └── docs/             # Cursor documentation
│   ├── codegenagent/         # Code generation agent
│   └── [other agents]        # Architect, Coder, QA, Research, etc.
├── core/                     # Core schemas, agents, governance
│   ├── agents/               # AgentExecutorService, KernelRegistry, schemas
│   ├── commands/             # Igor command parser, intent extraction
│   ├── compliance/           # Audit logging, compliance reporting
│   ├── governance/           # Approval engine, patterns, validation
│   ├── kernel_wiring/        # 10 kernel wirings (master→packet_protocol)
│   ├── observability/        # Five-tier observability system
│   ├── schemas/              # Pydantic models, capabilities, tasks
│   ├── testing/              # Test generation, execution, agent
│   ├── tools/                # Tool graph, registry adapter
│   └── worldmodel/           # World model service, insight emitter
├── memory/                   # Memory substrate implementation
│   ├── substrate_*.py        # Graph, models, repository, service, semantic
│   ├── governance_patterns.py # Closed-loop learning patterns
│   └── retrieval.py          # Context retrieval, pattern lookup
├── orchestrators/            # 7 orchestration patterns
│   ├── reasoning/            # CoT/ToT/FoT reasoning engine
│   ├── memory/               # Memory housekeeping
│   ├── action_tool/          # Tool execution with validation
│   ├── world_model/          # Insight-driven updates + scheduler
│   ├── evolution/            # Self-improvement engine
│   ├── meta/                 # Meta-reasoning
│   └── research_swarm/       # Multi-agent research
├── runtime/                  # Runtime infrastructure
│   ├── kernel_loader.py      # YAML kernel loading
│   ├── task_queue.py         # Redis-backed task queue
│   ├── websocket_orchestrator.py # Real-time agent comms
│   ├── l_tools.py            # L-CTO tool definitions
│   └── mcp_client.py         # MCP memory client
├── services/                 # Business services
│   ├── research/             # Perplexity-powered research agents
│   ├── research_factory/     # Code generation validation
│   └── symbolic_computation/ # SymPy computation service
├── private/                  # Protected kernel files
│   └── kernels/00_system/    # 10 production kernels (01-10)
├── migrations/               # SQL migrations (0001-0009)
├── tests/                    # 119 test files
│   ├── integration/          # 17 integration tests
│   ├── unit/                 # Component tests by module
│   └── smoke_*.py            # Pre-deploy smoke tests
├── docs/                     # Documentation
│   ├── cursor-briefs/        # Cursor-generated analysis (52 files)
│   ├── _GMP-Active/          # Active GMP prompts (14 files)
│   └── _GMP-Complete/        # Executed GMPs (16 files)
├── reports/                  # GMP execution reports (30+ files)
├── config/                   # Settings, agent configs, policies
├── .cursor/                  # Cursor rules & protocols
└── workflow_state.md         # Active session state
```

---

## Architecture Decisions

See [architecture_decisions.md](architecture_decisions.md) for documented architecture decisions.

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16 with pgvector extension
- Redis (optional, for task queue)
- OpenAI API key (or use stub provider)

### Local Development

```bash
# 1. Clone and setup
cd /path/to/L9
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Start PostgreSQL with pgvector
docker run -d --name l9-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=YOUR_PASSWORD \
  -e POSTGRES_DB=l9_memory \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# 3. Set environment variables
export DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@localhost:5432/l9_memory"
export OPENAI_API_KEY="sk-..."  # Optional

# 4. Apply migrations
for f in migrations/000*.sql; do psql $DATABASE_URL -f $f; done

# 5. Start API server
uvicorn api.server:app --reload --port 8000
```

### Docker Compose

> ⚠️ **DOCKER AUTHORITY:** Use ROOT `docker-compose.yml` only. Files in `docs/` are reference copies, not production. See [`VPS-Repo-Files/VPS-Deploy-Sequence/DOCKER-DEPLOYMENT-GUIDE.md`](VPS-Repo-Files/VPS-Deploy-Sequence/DOCKER-DEPLOYMENT-GUIDE.md) for full details.

```bash
docker compose up -d
docker compose logs -f l9-api
```

---

## API Endpoints

### Core Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root status |
| `/health` | GET | Health check |
| `/os/health` | GET | OS layer health |
| `/os/status` | GET | System status |

### Agent Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agent/health` | GET | Agent layer health |
| `/agent/task` | POST | Submit agent task |
| `/lchat` | POST | L-CTO chat endpoint |
| `/wsagent` | WebSocket | Real-time agent communication |

### Memory Routes (`/api/v1/memory`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/packet/{id}` | GET | Get packet by ID |
| `/thread/{id}` | GET | Get thread packets |
| `/ingest` | POST | Ingest packet |
| `/hybrid/search` | POST | Semantic + filter search |
| `/facts` | GET | Query knowledge facts |
| `/insights` | GET | Query insights |

### Governance & Compliance

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/commands/execute` | POST | Execute @L command |
| `/commands/governance/feedback` | POST | Approval feedback |
| `/compliance/report` | GET | Compliance summary |
| `/compliance/audit-log` | GET | Audit trail |

### World Model

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/worldmodel/agents` | GET | Agent capabilities |
| `/worldmodel/infra` | GET | Infrastructure status |
| `/worldmodel/approvals` | GET | Approval history |
| `/worldmodel/context` | POST | Contextual search |

---

## Key Modules

| Module | Purpose | Status |
|--------|---------|--------|
| `core/agents/` | Agent execution, kernel loading, task management | ✅ Production |
| `core/governance/` | Approval gates, pattern learning, validation | ✅ Production |
| `core/commands/` | Igor @L command parsing, intent extraction | ✅ Production |
| `core/compliance/` | Audit logging, compliance reporting | ✅ Production |
| `core/testing/` | Test generation, recursive self-testing | ✅ Production |
| `core/worldmodel/` | World model service, insight emission | ✅ Production |
| `core/observability/` | Five-tier observability: tracing, failure detection, metrics, context strategies | ✅ Production |
| `memory/` | PacketEnvelope, semantic search, insight extraction | ✅ Production |
| `orchestrators/` | 7 orchestration patterns | ✅ Production |
| `runtime/` | Kernel loader, task queue, WebSocket | ✅ Production |
| `services/research/` | Perplexity research agents | ✅ Production |

---

## Migrations

Apply in order (0001-0009):

```bash
# Core memory substrate
psql $DATABASE_URL -f migrations/0001_init_memory_substrate.sql
psql $DATABASE_URL -f migrations/0002_enhance_packet_store.sql
psql $DATABASE_URL -f migrations/0003_init_tasks.sql

# World model
psql $DATABASE_URL -f migrations/0004_init_world_model_entities.sql
psql $DATABASE_URL -f migrations/0005_init_knowledge_facts.sql
psql $DATABASE_URL -f migrations/0006_init_world_model_updates.sql
psql $DATABASE_URL -f migrations/0007_init_world_model_snapshots.sql

# 10X upgrade + effectiveness tracking
psql $DATABASE_URL -f migrations/0008_memory_substrate_10x.sql
psql $DATABASE_URL -f migrations/0009_feedback_and_effectiveness.sql
```

---

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `OPENAI_API_KEY` | No | — | For OpenAI embeddings/LLM |
| `EMBEDDING_PROVIDER` | No | `openai` | `openai` or `stub` |
| `EMBEDDING_MODEL` | No | `text-embedding-3-large` | Embedding model |
| `L9_API_KEY` | No | — | API authentication key |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `SLACK_APP_ENABLED` | No | `false` | Enable Slack integration |
| `L9_ENABLE_LEGACY_SLACK_ROUTER` | No | `true` | Use legacy Slack routing |
| `L9_OBSERVABILITY` | No | `true` | Enable Five-Tier Observability system |
| `OBS_ENABLED` | No | `true` | Observability subsystem enabled |
| `OBS_SAMPLING_RATE` | No | `0.10` | Fraction of requests to sample (0.0-1.0) |
| `OBS_EXPORTERS` | No | `console` | Exporters: console, file, substrate, datadog, honeycomb |
| `OBS_SUBSTRATE_ENABLED` | No | `true` | Export spans to L9 Memory Substrate |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Smoke tests (pre-deploy)
python tests/smoke_test_root.py
python tests/smoke_email.py

# Integration tests
pytest tests/integration/ -v

# Specific module
pytest tests/core/agents/ -v
```

**Test Coverage (as of 2026-01-11):**
- 54+ integration tests passing
- 119+ test files total
- Key test suites: closed_loop_learning (7), world_model (19), recursive_self_testing (20), compliance_audit (15), observability (32)

---

## VPS Deployment

See [docs/Go-Live.md](docs/Go-Live.md) for complete deployment guide.

```bash
# 1. Local pre-flight
venv/bin/python tests/smoke_test_root.py

# 2. Push to main
git push origin main

# 3. SSH to VPS and run release gate
ssh l9
cd /opt/l9 && sudo bash ops/vps_release_gate.sh

# 4. Verify
curl -sS http://127.0.0.1:8000/health | jq .
```

**VPS Details:**
- IP: 157.180.73.53
- Domain: l9.quantumaipartners.com (Cloudflare proxied)
- Ports: 8000 (l9-api), 9001 (mcp-memory)

---

## Recent GMPs Completed

| GMP | Description | Date |
|-----|-------------|------|
| GMP-48 | Cursor + LangGraph + L9 Memory Integration | 2026-01-11 |
| GMP-47 | Stub Elimination (Fail Loudly + Implement) | 2026-01-09 |
| GMP-46 | OpenAI Tool Name Validation | 2026-01-08 |
| GMP-45 | ToolInputSanitizer + ModuleRegistry | 2026-01-08 |
| GMP-44 | Auto-Discovery Tool Capabilities | 2026-01-08 |
| GMP-34 | EmbeddingProvider Default (stub → openai) | 2026-01-09 |
| GMP-33 | CircuitBreaker Memory Wiring | 2026-01-09 |
| GMP-32 | CircuitBreaker Integration | 2026-01-09 |
| GMP-21 | Compliance audit trail and reporting | 2026-01-01 |
| GMP-19 | Recursive self-testing and validation | 2026-01-01 |
| GMP-18 | World model population and reasoning | 2026-01-01 |
| GMP-16 | Closed-loop learning from approvals | 2026-01-01 |
| GMP-11 | Igor command interface with intent extraction | 2026-01-01 |

See [reports/](reports/) for detailed execution reports.

---

## Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| Go-Live Checklist | [docs/Go-Live.md](docs/Go-Live.md) | VPS deployment guide |
| Roadmap | [docs/ROADMAP.md](docs/ROADMAP.md) | Development roadmap |
| Memory Substrate | [memory/README.md](memory/README.md) | Memory system docs |
| Observability | [core/observability/OBSERVABILITY.md](core/observability/OBSERVABILITY.md) | Five-tier observability system |
| Kernel Loading | [private/kernels/00_system/Loading Instructions.md](private/kernels/00_system/Loading%20Instructions.md) | Kernel config |
| GMP Reports | [reports/](reports/) | Execution reports (25 files) |
| Cursor Briefs | [docs/cursor-briefs/](docs/cursor-briefs/) | Analysis briefs (52 files) |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.2.0 | 2026-01-11 | Cursor+LangGraph integration (GMP-48), Five-Tier Observability, Stub Elimination (GMP-47), CircuitBreaker (GMP-32/33), Tool improvements (GMP-44/45/46) |
| 2.1.0 | 2026-01-01 | 4 HIGH GMPs (16,18,19,21), Emma Substrate 10X, Igor commands, 54 tests |
| 2.0.0 | 2025-12-31 | Research Factory, SymPy integration, CodeGenAgent specs |
| 1.1.0 | 2025-12-08 | Insight extraction, knowledge facts, world model integration |
| 1.0.0 | 2025-12-01 | Initial memory substrate release |

---

*L9 Secure AI OS — Internal Use*
