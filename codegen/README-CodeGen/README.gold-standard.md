# L9 Secure AI OS: Root README

## Project Overview

**L9 Secure AI OS** is a governed, production-grade agent runtime platform that enables autonomous systems research and AI agent development with built-in security, memory persistence, and tool orchestration. It solves the critical problem of **safely executing autonomous agents at scale** by combining sandboxed execution, multi-layer memory substrates, and governance-first design.

This project serves:
- **AI researchers** building multi-step autonomous workflows and agent architectures.
- **Operations teams** deploying governed agents in production with audit trails and rollback.
- **DevOps and security engineers** who need deterministic, reproducible agent execution.

**Primary Goals:**
- Provide a secure, governed runtime for executing AI agents and tools.
- Support multi-layer memory (short-term, long-term, audit) with semantic retrieval.
- Enable seamless integration of external tools (APIs, databases, webhooks) with sandboxing.
- Maintain full observability: structured logging, metrics, distributed tracing, and incident dashboards.
- Support long-horizon planning with breakpoints, checkpointing, and multi-step execution.

**Non-Goals:**
- General-purpose web framework (not Django/FastAPI replacement).
- Unrestricted code execution or arbitrary Python eval.
- Machine learning training framework.
- Synchronous request-response API (async-first design).

---

## Architecture Summary

L9 OS is organized around four core subsystems that work together to enable secure, governed agent execution:

1. **API & Gateway** — WebSocket and HTTP interfaces for agent communication, tool dispatch, and memory queries.
2. **Agent Kernel** — Agent execution engine with kernel entry points, lifecycle management, and delegation.
3. **Memory Substrate** — Multi-layer storage (Redis, PostgreSQL, semantic index) with retrieval and audit trails.
4. **Tool Registry & Sandbox** — Tool manifest registry with resource limits, input validation, and execution isolation.

These subsystems communicate through:
- **Task Queue** — Redis-backed work queue for async execution and scheduling.
- **Long Plan Graph** — DAG-based execution for multi-step workflows with breakpoints.
- **WebSocket Orchestrator** — Real-time agent communication and state synchronization.

For a complete architecture diagram and detailed subsystem specs, see [`docs/architecture.md`](docs/architecture.md).

---

## Repository Layout

```
l9/                                # Core L9 runtime (APIs, agents, memory, tools)
  ├── server.py                    # FastAPI app, route registration, WebSocket handlers
  ├── kernel_loader.py             # Agent kernel entry points and dispatcher
  ├── task_queue.py                # Task queueing, scheduling, worker lifecycle
  ├── executor.py                  # Execution engine, context, signal handling
  ├── websocket_orchestrator.py    # Real-time agent communication
  ├── redis_client.py              # Redis substrate and memory backend
  ├── memory_helpers.py            # Memory utilities, schema, serialization
  ├── tool_registry.py             # Tool manifest registry, dispatch, sandboxing
  ├── long_plan_graph.py           # DAG execution, breakpoints, checkpointing
  ├── core/
  │   ├── agents/                  # Agent kernels, configs, profiles
  │   ├── memory/                  # Semantic retrieval, audit logs, knowledge graph
  │   ├── tools/                   # Tool wrappers, validators, executors
  │   └── scheduler/               # Background tasks, recurring workflows
  ├── integrations/                # External systems (Slack, MCP, webhooks, databases)
  └── utils/                       # Helpers: logging, serialization, validation
docs/                              # Architecture, governance, operational docs
  ├── architecture.md              # System design, subsystems, data flow
  ├── ai-collaboration.md          # AI tool usage rules, change gates, workflows
  ├── capabilities.md              # What the system can/cannot do
  ├── memory-and-tools.md          # Memory layers, tool registry, invariants
  ├── agents.md                    # Agent profiles, roles, responsibilities
  ├── governance.md                # Decision-making, ownership, approval flows
  ├── deployments.md               # Dev/stage/prod procedures, rollbacks
  ├── troubleshooting.md           # Common failure symptoms, diagnostics
  ├── maintenance-tasks.md         # Health checks, migrations, log rotation
  ├── roadmap.md                   # Near/medium-term planned changes
  ├── api/
  │   ├── http-api.md              # REST/WebSocket endpoints, auth, examples
  │   ├── webhooks.md              # Inbound/outbound webhook contracts
  │   └── integrations.md          # External systems: Slack, MCP, databases
  ├── operational-playbooks/
  │   ├── oncall-runbook.md        # Core service failures and responses
  │   └── incident-response.md     # Severity levels, comms, timelines
  └── adr/                         # Architecture Decision Records
scripts/                           # Automation, dev, and deployment helpers
  ├── local-dev.sh                 # Dev environment setup
  ├── migrations/                  # Database schema versions
  └── vps-mri.sh                   # VPS deployment and monitoring
tests/                             # Unit, integration, and smoke tests
  ├── unit/                        # Component-level tests
  ├── integration/                 # Cross-subsystem tests (agents + memory + tools)
  └── smoke_test.py                # Sanity checks for core workflows
config.yaml                        # Global runtime configuration
.env.example                       # Safe reference for required env vars
docker-compose.yml                 # Local dev services (Redis, PostgreSQL)
requirements.txt                   # Python dependencies
Makefile                           # Common dev tasks
LICENSE                            # MIT License
README.md                          # This file
```

**Critical Entrypoints:**
- **API Server:** `l9/server.py:app` (FastAPI application)
- **Agent Kernel:** `l9/kernel_loader.py:Kernel.execute()` (Entry point for agent execution)
- **Task Worker:** `l9/executor.py:Worker.run()` (Executes enqueued tasks)
- **Infrastructure:** `docker-compose.yml` (Local dev: Redis, PostgreSQL, optional webhooks)

---

## Getting Started

### Prerequisites

- **Python 3.11 or later** (for type hints, match statements, asyncio improvements)
- **PostgreSQL 14+** (memory substrate, audit logs, agent state)
- **Redis 7+** (task queue, caching, WebSocket pub/sub)
- **Docker + docker-compose** (local dev and CI/CD)
- **make** (optional, for common dev tasks)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd l9-secure-ai-os
   ```

2. **Create a virtual environment:**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Copy environment template and fill in secrets:**
   ```bash
   cp .env.example .env
   # Edit .env with your OPENAI_API_KEY, DATABASE_URL, REDIS_URL, etc.
   ```

5. **Start services (Redis, PostgreSQL):**
   ```bash
   docker-compose up -d
   ```

6. **Run database migrations:**
   ```bash
   python -m alembic upgrade head
   ```

### Quickstart

1. **Start the API server:**
   ```bash
   uvicorn l9.server:app --reload --host 0.0.0.0 --port 8000
   ```

2. **In another terminal, test basic agent execution:**
   ```bash
   python -m pytest tests/smoke_test.py -v
   ```

3. **Explore the WebSocket interface:**
   ```bash
   # Connect to ws://localhost:8000/ws
   # Send: {"type": "agent.execute", "agent_id": "researcher", "input": "What is AI?"}
   ```

4. **View memory and logs:**
   ```bash
   curl http://localhost:8000/memory/search?q=AI
   curl http://localhost:8000/memory/audit?limit=50
   ```

---

## Configuration and Environments

### Configuration Files

- **`config.yaml`** — Global runtime configuration (timeouts, memory limits, feature flags).
- **`.env`** — Environment-specific secrets and overrides (API keys, database URLs, Redis URLs).
- **`docker-compose.yml`** — Service definitions for local dev (PostgreSQL, Redis, Caddy reverse proxy).

### Required Environment Variables

```bash
# LLM and External Services
OPENAI_API_KEY=sk-...              # OpenAI API key for agent reasoning
ANTHROPIC_API_KEY=sk-...           # Claude API (optional)

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/l9_os
DATABASE_POOL_SIZE=20
DATABASE_POOL_TIMEOUT=10

# Memory and Caching
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=                    # Optional

# Security and Auth
JWT_SECRET=your-secret-key-min-32-chars
AUTH_ENABLED=true
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Logging and Observability
LOG_LEVEL=INFO
LOG_FORMAT=json                    # json or text
SENTRY_DSN=https://...             # Optional error tracking
DATADOG_API_KEY=                   # Optional metrics

# Feature Flags
L9_ENABLE_LONG_PLANS=true
L9_ENABLE_SEMANTIC_MEMORY=true
L9_ENABLE_TOOL_AUDIT=true
L9_ENABLE_WEBHOOK_INGESTION=false  # Enable to accept external webhooks

# VPS Deployment
DEPLOYMENT_ENV=local               # local, staging, production
VPS_CADDY_CONFIG=/etc/caddy/Caddyfile
VPS_SYSTEMD_SERVICE=l9-os.service
```

### Environment Profiles

| Profile | Usage | Database | Redis | Notes |
|---------|-------|----------|-------|-------|
| **local** | Development, testing | Local PostgreSQL | localhost:6379 | Full verbosity, hot reload enabled |
| **staging** | Pre-production validation | Cloud PostgreSQL | Cloud Redis | Staging dataset, rate limiting enabled |
| **production** | Live agent execution | Cloud PostgreSQL (backup enabled) | Cloud Redis (persistence) | Minimal logging, strict auth, audit trails required |

---

## Running Tests and Quality Gates

### Test Commands

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/ -v

# Run integration tests (requires Docker services running)
pytest tests/integration/ -v

# Run smoke tests (sanity checks for critical workflows)
pytest tests/smoke_test.py -v

# Run with coverage report
pytest --cov=l9 --cov-report=html

# Linting and type checking
ruff check .                       # Fast Python linter
mypy l9/                           # Static type checking
black --check l9/                  # Code formatting (check mode)
```

### Quality Gates (Pre-commit)

Before merging, all of these must pass:

- **Unit tests:** ✅ 100% pass
- **Integration tests:** ✅ Pass against staging database
- **Type checking:** ✅ `mypy l9/` with no errors
- **Linting:** ✅ `ruff check .` with no errors
- **Code coverage:** ✅ Minimum 80% coverage for new code
- **Smoke tests:** ✅ Core workflows execute end-to-end

### Running Tests Locally

1. **Start services:**
   ```bash
   docker-compose up -d
   ```

2. **Run all tests with coverage:**
   ```bash
   pytest --cov=l9 --cov-report=term-missing
   ```

3. **Check coverage gaps:**
   ```bash
   coverage report -m
   ```

---

## Deployment

### Deployment Strategy

L9 OS is deployed as a **containerized service on a VPS** behind **Caddy reverse proxy** with:
- PostgreSQL for persistent state
- Redis for task queue and WebSocket pub/sub
- Systemd service for restart/recovery
- SSL/TLS termination via Caddy
- Automatic log rotation and health checks

### Production Entrypoints

```bash
# Start the API server (using gunicorn in production)
gunicorn l9.server:app \
  -k uvicorn.workers.UvicornWorker \
  -w 4 \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

### Deployment Procedures

For step-by-step deployment to VPS, rollback procedures, and health checks, see [`docs/deployments.md`](docs/deployments.md).

**Quick deployment (if you have SSH and Caddy):**
```bash
./scripts/vps-mri.sh deploy production
```

---

## Observability and Operations

### Logging

- **Format:** JSON structured logs (via `python-json-logger`)
- **Levels:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Output:** stdout (containers) and `/var/log/l9/` (VPS)
- **Rotation:** Daily, 14 days retention

**Example log entry:**
```json
{
  "timestamp": "2025-12-25T08:42:00Z",
  "level": "INFO",
  "module": "executor",
  "message": "Agent execution started",
  "agent_id": "researcher-001",
  "task_id": "task-abc123",
  "correlation_id": "corr-xyz789",
  "duration_ms": 1250
}
```

### Metrics and Dashboards

- **Collected via:** Prometheus client library
- **Stored in:** Datadog (production) or Prometheus (self-hosted)
- **Key metrics:**
  - `agent_execution_duration_ms` — Agent task latency
  - `tool_execution_count` — Total tool invocations
  - `memory_retrieval_latency_ms` — Semantic search latency
  - `task_queue_depth` — Pending tasks
  - `database_connection_pool` — Active connections
  - `redis_memory_usage_bytes` — Cache size

**Grafana dashboard:** Available at `https://<vps-host>/grafana/d/l9-core` (staging/prod only)

### First Steps During Incidents

1. **Check service health:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **View recent logs:**
   ```bash
   tail -f /var/log/l9/app.log | jq .
   ```

3. **Check database connection:**
   ```bash
   psql $DATABASE_URL -c "SELECT 1;"
   ```

4. **Check Redis:**
   ```bash
   redis-cli -u $REDIS_URL PING
   ```

For detailed incident response procedures, see [`docs/operational-playbooks/oncall-runbook.md`](docs/operational-playbooks/oncall-runbook.md).

---

## Security and Compliance

### Threat Model

We protect against:
- **Malicious agents:** Agents cannot access secrets, execute arbitrary code, or modify system state without explicit tool invocation.
- **Tool abuse:** All tool invocations are sandboxed, logged, and rate-limited.
- **Memory leakage:** Sensitive data (tokens, API keys) is encrypted at rest and in transit.
- **Unauthorized access:** API endpoints require JWT authentication; WebSocket connections are validated.

### Sensitive Components

These files must **never be modified without explicit human review**:

- **`l9/kernel_loader.py`** — Agent kernel entry point; changes here break all agents.
- **`l9/tool_registry.py`** — Tool sandboxing and dispatch; changes here enable tool abuse.
- **`l9/websocket_orchestrator.py`** — Agent communication channel; changes here enable eavesdropping.
- **`l9/redis_client.py`** — Memory substrate; changes here corrupt agent state.
- **`.env` and secrets files** — Never commit secrets; use environment variables.

### Data Handling Policies

- **PII:** Agents must not be given access to personally identifiable information (email, phone, SSN, etc.). If an agent needs PII, it must be hashed or tokenized first.
- **Encryption:** All data at rest in PostgreSQL is encrypted using AES-256 (via `pgcrypto` extension). Data in transit uses TLS 1.3.
- **Retention:** Audit logs are retained for 90 days. Agent state is retained until explicitly deleted. Memory snapshots are retained for 30 days.
- **Access control:** Only authenticated agents and authorized humans can read memory or execution history.

---

## Working with AI on This Repo

### Allowed Scopes for AI Changes

AI tools (e.g., code generation, documentation refactoring) **are allowed** to modify:

- **Application logic** under `l9/core/` (agents, memory, tools subsystems) — excluding kernel entry points.
- **Tests** — unit tests, integration tests, fixtures.
- **Documentation** — READMEs, guides, examples, architecture diagrams (not governance decisions).
- **Configuration** — `config.yaml` defaults, feature flag descriptions, non-secret environment docs.
- **Scripts** — `scripts/local-dev.sh`, database migrations (not VPS automation).

### Restricted Scopes Requiring Human Review

High-risk changes that require **explicit human approval** before merging:

- **Feature flags** — Changes to `L9_ENABLE_*` flags must be reviewed by Igor.
- **Memory substrate** — Any change to `redis_client.py`, schema migrations, or memory contract.
- **API contracts** — Changes to `http-api.md`, WebSocket message schemas, or endpoint signatures.
- **Tool registry** — Changes to sandboxing rules, tool manifests, or resource limits.
- **Dependency upgrades** — Major version bumps to FastAPI, SQLAlchemy, Redis, PostgreSQL drivers.

### Forbidden Scopes for AI Changes

AI **must not modify**:

- **`l9/kernel_loader.py`** — Agent kernel entry points.
- **`l9/websocket_orchestrator.py`** — Agent communication channel.
- **`.env`, `secrets.yaml`, private keys** — Never commit credentials.
- **Docker Compose, Caddy config, systemd services** — Infrastructure is human-managed.
- **Authentication and authorization** — Token handling, JWT validation, access control.
- **Cryptographic code** — Encryption, hashing, key derivation.

### Required Pre-Reading Before AI Edits

Any AI tool proposing changes to this repo **must** read these documents first:

1. **[`docs/architecture.md`](docs/architecture.md)** — Understand subsystem boundaries, data flow, and invariants.
2. **[`docs/ai-collaboration.md`](docs/ai-collaboration.md)** — Understand AI usage rules, change gates, and approval flows.
3. **Relevant subsystem README** — E.g., if editing agents, read `l9/core/agents/README.md`.
4. **This file (root README)** — You are reading it now.

### AI Change Policy

All changes proposed by AI tools **must** follow this workflow:

1. **Propose as a scoped PR** with clear commit message and diff.
2. **Include tests:** Unit tests (happy path + error cases) and regression tests.
3. **Update documentation:** If APIs or behavior change, update the relevant README.
4. **Respect feature flags:** Use `L9_ENABLE_*` flags for gradual rollout; include tests for both enabled/disabled states.
5. **Get human approval:** Changes to restricted scopes require explicit human review before merge.
6. **Pass all quality gates:** Tests, linting, type checking, smoke tests must all pass.

**Example AI workflow:**
```
1. Read docs/architecture.md and docs/ai-collaboration.md
2. Create branch: git checkout -b feat/agent-memory-optimization
3. Propose changes with tests in a commit
4. Create PR with clear description of problem, solution, and testing
5. Wait for human review (especially if touching memory or kernel)
6. Merge only after all checks pass and approval is granted
```

---

## Contributing

### Issue and PR Workflow

1. **Report bugs or request features** as GitHub issues.
2. **Propose changes** via pull requests with:
   - Clear description of the problem and solution.
   - Link to related issues.
   - Test cases (unit + integration if applicable).
3. **Code review:** At least one human approval required before merge.
4. **Merge:** Use squash merge to keep history clean.

### Coding Standards

We follow **PEP 8** with tool enforcement:

- **Linting:** `ruff check .` (fast, Rust-based linter)
- **Formatting:** `black --line-length=100 l9/` (or use editor plugin)
- **Type hints:** `mypy l9/` (strict mode: `mypy --strict l9/`)
- **Import sorting:** `isort l9/` (alphabetical with groups)

### Commit Message Conventions

Commit messages follow **Conventional Commits**:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Examples:**
```
feat(agents): add memory optimization for long plans

- Implement semantic clustering of memory entries
- Add L9_ENABLE_MEMORY_CLUSTERING flag for rollout
- Update agents.md with new behavior

Closes #123
```

```
fix(tools): validate tool input against manifest schema

- Prevent malformed tool invocations from reaching sandbox
- Add unit test for schema validation
- Update tool_registry.md with validation invariants

Fixes #456
```

### Code Review Expectations

- **Constructive feedback** on logic, performance, and style.
- **Tests are non-negotiable** — All new code requires tests.
- **Documentation updates** — If APIs change, docs must be updated.
- **Backwards compatibility** — Breaking changes require deprecation period.

### Escalation

For questions, design decisions, or approval:
- **Tag Igor** in PR discussions.
- **Email:** igor@l9os.dev (for urgent escalations).

---

## License and Attribution

**L9 Secure AI OS** is licensed under the **MIT License**.

See [`LICENSE`](LICENSE) for full terms.

**Ownership and Support:**
- **Lead architect:** Igor (igor@l9os.dev)
- **Maintainers:** [List team members]
- **Escalations:** Tag `@igor` on GitHub or email directly.

---

## Next Steps

- **First time?** Follow the [Getting Started](#getting-started) section above.
- **Want to contribute?** Read [Contributing](#contributing) and [`docs/ai-collaboration.md`](docs/ai-collaboration.md).
- **Need architecture details?** See [`docs/architecture.md`](docs/architecture.md).
- **Deploying to production?** Follow [`docs/deployments.md`](docs/deployments.md).
- **Something broken?** Check [`docs/troubleshooting.md`](docs/troubleshooting.md).

---

**L9 Secure AI OS** — *Building the future of governed, secure agent execution.*
