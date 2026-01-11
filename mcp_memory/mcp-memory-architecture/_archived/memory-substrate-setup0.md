The MCP memory server described in `L9-MCP-IMPL.md` is **a design + code-in-a-doc**, not an already-present `/l9/` package in this repo, so Option A currently has a missing piece: that server must be instantiated as real code and deployed before C can use it.[1][2]

## 1. Current state in this repo

- The main L9 OS repo has:
  - Core API, kernel, memory substrate, Redis, Postgres, etc., wired via Docker and the existing memory helpers.[3][1]
  - No `opt/l9/mcp/memory` tree or `src/main.py`/`mcpserver.py` as actual files; those exist only as code blocks inside `L9-MCP-IMPL.md`.[2]
- The memory substrate L is using is **already working** (your recent memory fix work, tests, and Docker bringup).[1][3]
- The MCP server is described as living under `/opt/l9/mcp/memory` on the VPS with its own venv and systemd unit `l9-mcp`, but that is an installation plan, not confirmed code in this Git repo.[2][1]

So for Option A (“C talks directly to the existing L9 MCP memory server”), you first need that **MCP server implementation to exist somewhere real** and point at the same Postgres DB that L9 uses.[3][2]

## 2. What “needs to be built to deploy this” for Option A

To make Option A real, you need to materialize the MCP server from `L9-MCP-IMPL.md` into a running service on the VPS:

- **Code extraction into a repo / directory** (can be inside this L9 repo or as `/opt/l9/mcp/memory`):
  - `main.py` – FastAPI app with `/health`, `/mcptools`, `/mcpcall`, and `/memory/*` routes.[2]
  - `mcpserver.py` – MCP tool definitions (`saveMemory`, `searchMemory`, `getMemoryStats`, `deleteExpiredMemories`) and router.[2]
  - `db.py` – asyncpg pool + helpers (`init_db`, `close_db`, `execute`, `fetchone`, `fetchall`, `insertmany`).[2]
  - `embeddings.py` – OpenAI `AsyncOpenAI` client and `embed_text`/`embed_texts`.[2]
  - `models.py` – `SaveMemoryRequest`, `MemoryResponse`, `SearchMemoryRequest`, `SearchMemoryResponse`, `MemoryStatsResponse`.[2]
  - `config.py` – `Settings` with `MCP_HOST`, `MCP_PORT`, `OPENAI_API_KEY`, `MEMORY_DSN`, retention, thresholds, etc.[2]
  - `routes/memory.py` – CRUD + search + cleanup task for the `memory.shortterm/mediumterm/longterm/auditlog` tables.[2]
  - `routes/health.py` – healthcheck hook used by `/health`.[2]
  - `schema/init.sql` – pgvector extension + `memory.*` tables + indexes + `stats_view` and `auditlog`.[2]
  - `migrations.py` or `scripts/migrate_db.py` – runner for `init.sql`.[2]
  - `requirements-mcp.txt` – FastAPI, asyncpg, pgvector, openai, etc., as listed.[2]

- **Deployment artifacts**:
  - `.env` for the MCP service with `OPENAI_API_KEY`, `MEMORY_DSN` pointing at the same Postgres instance already used by L9 (`l9memory` schema).[3][2]
  - `systemd/l9-mcp.service` – runs `python main.py` in its venv with `WorkingDirectory=/opt/l9/mcp/memory`.[2]
  - `scripts/install.sh` – venv creation, `pip install -r requirements-mcp.txt`, run migrations, install systemd unit, start service.[2]
  - Optionally `docker/Dockerfile.mcp` + `docker-compose.mcp.yml` if you want it containerized instead of bare-metal.[2]

Once that exists and `curl http://127.0.0.1:9001/health` works on the VPS, **then** Option A is ready and C can point to it via SSH tunnel.[2]

## 3. Why this matters for wiring C’s memory

Option A assumes:

- There is a running MCP memory server with:
  - `GET /mcptools` returning the tool list.[2]
  - `POST /mcpcall` accepting `toolName`, `arguments`, and `userId`.[2]
- That server uses the **same** Postgres DB (`MEMORY_DSN`) L9 is already using for its memory substrate.[3][2]

Right now, you only have:

- The **spec and code blocks** for that server in `L9-MCP-IMPL.md`.[2]
- Working Postgres + memory substrate for L.[1][3]

So before C can “reuse the same infra with a different userId” via MCP, the missing step is: **actually build and deploy the MCP memory server from that spec**.

If you want, the next step can be a strict Phase‑0 TODO plan specifically for:

- Where in this repo to materialize that MCP server (paths),
- Exact files to create for `main.py`, `mcpserver.py`, `db.py`, etc., matching the L9 style and not touching Docker/VPS config outside that scope.
