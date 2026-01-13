TITLE: GMP-L9-MCP-SERVER-REVIVAL.v1.0

OWNER:
- L-CTO

GOAL:
- Reactivate and standardize the dedicated L9 MCP Memory Server as the primary interface for Cursor, ensuring all Cursor memory interactions go through a first-class MCP protocol entrypoint rather than ad-hoc HTTP calls.

NON-GOALS:
- Do not fork or duplicate the memory substrate DB.
- Do not introduce a second, divergent memory API surface; MCP is a thin protocol layer over the existing substrate.
- Do not change production TLS/ports exposed by Caddy beyond MCP routing.

SCOPE:
- Code: `mcpmemory/` package, API surfacing, and integration with existing memory substrate.
- Config: environment variables, systemd, Docker, and Caddy wiring.
- Clients: Cursor MCP configuration and any internal L9 MCP client usage.

---

## PHASE 1 – CURRENT STATE INVENTORY

1. Confirm MCP server code + entrypoints
   - [ ] Locate MCP server implementation:
     - `mcpmemory/src/main.py`
     - `mcpmemory/src/mcpserver.py`
     - `mcpmemory/src/models.py`
     - `mcpmemory/src/config.py`
   - [ ] Verify FastAPI app exposes:
     - `GET /health`
     - `GET /mcptools`
     - `POST /mcpcall`
     - `ROUTER /memory/*` (ingestion, search, temporal, session learning, proactive recall, context injection).  
   - [ ] Confirm Pydantic models align with the substrate contracts:
     - `SearchMemoryRequest`, `SaveMemoryRequest`, `MemoryResponse`, `MemoryStatsResponse`, `ContextInjectionRequest`, `SessionLearningRequest`, `TemporalQueryRequest` etc. use the same substrate types as `memorysubstrate*` modules.

2. Confirm systemd + deploy scripts
   - [ ] Inspect systemd unit:
     - `mcpmemory/deploy/systemd/l9-mcp.service`
   - [ ] Verify the unit:
     - Uses `uvicorn mcpmemory.src.main:app`
     - Binds to host/port from `MCPHOST` / `MCPPORT`
     - Uses `/opt/l9` as WorkingDirectory and the same Python env as `l9-api` (or the standard venv for services).

3. Confirm current env and routing
   - [ ] In `/opt/l9/.env`, list MCP-related envs:
     - `MCP_API_KEY`, `MCP_API_KEYC`, `MCP_API_KEYL`, `MCPL9MEMORYKEY`
     - `MCPHOST`, `MCPPORT`, `MCPENV`, `MCPMEMORYURL` (if present)
   - [ ] In `/etc/caddy/Caddyfile`:
     - Locate the `:9001` site / `l9.quantumaipartners.com` block.
     - Locate any `/mcp/*` or `/mcpmemory/*` `reverse_proxy` lines.
   - [ ] Confirm Docker does **not** run MCP (no `mcp-memory` service in `docker-compose.yml`).

DELIVERABLE (PHASE 1):
- Short markdown note `docs/01-XX-2026-MCP-STATE.md` summarizing:
  - MCP code location
  - systemd wiring
  - env keys in use
  - current Caddy routing

---

## PHASE 2 – SERVER CONTRACT HARDENING

4. Normalize MCP config contract
   - [ ] In `mcpmemory/src/config.py`:
     - Ensure a single source of truth for:
       - `MCPHOST` (default `127.0.0.1`)
       - `MCPPORT` (default `9002`)
       - `MCPENV` (default `production`)
     - Ensure supported keys:
       - `MCP_API_KEY` (shared)
       - `MCP_API_KEYC` (Cursor)
       - `MCP_API_KEYL` (L-CTO / internal)
       - `MCPL9MEMORYKEY` (legacy alias)
   - [ ] Make sure missing keys fail fast with clear error messages, not silent 500s.

5. Harden auth and caller identity
   - [ ] In `mcpmemory/src/main.py`:
     - Confirm there is a `CallerIdentity` abstraction that:
       - Maps bearer tokens → caller type (`cursor`, `l-cto`, `default`, etc.).
       - Annotates memory packets with creator/source metadata.
     - Ensure env-driven mapping:
       - `MCP_API_KEYC` → identity `cursor-mcp`
       - `MCP_API_KEYL` → identity `l-cto-mcp`
       - `MCPL9MEMORYKEY` / `MCP_API_KEY` → shared fallback identity.
   - [ ] Verify rate limiting path:
     - Uses Redis if configured, otherwise in-memory fallback.
     - Enforces reasonable per-IP / per-key limits with configurable thresholds.

6. Wire to unified memory substrate
   - [ ] Confirm MCP routes call into the **existing** memory substrate repository/service:
     - Use `memorysubstraterepository.py`, `memorysubstratesemantic.py`, `memorysubstrateservice.py`, `memoryretrieval.py`, `memoryingestion.py`, etc.
   - [ ] Ensure no new DB schemas; reuse tables:
     - `packetstore`, `semanticmemory`, `knowledgefacts`, `reasoningtraces`, etc.
   - [ ] Add explicit tests (if missing) in `mcpmemory/tests/`:
     - `test_search_memory_roundtrip.py` (write + search).
     - `test_session_learning_flow.py`.
     - `test_context_injection_flow.py`.
     - `test_auth_and_rate_limit.py`.

DELIVERABLE (PHASE 2):
- Updated MCP server code with:
  - Clear config contract.
  - Auth/identity mapping.
  - Tests verifying substrate integration and auth.

---

## PHASE 3 – VPS DEPLOYMENT INTEGRATION

7. Standardize MCP env on VPS
   - [ ] In `/opt/l9/.env` (and `/Users/ib-mac/Projects/L9/.env` for parity):
     - Set:
       - `MCPHOST=127.0.0.1`
       - `MCPPORT=9002`
       - `MCPENV=production`
     - Keep existing keys (`MCP_API_KEY*`, `MCPL9MEMORYKEY`) but document:
       - `MCP_API_KEYC` = **Cursor** primary key
       - `MCP_API_KEYL` = **L-CTO / internal**
       - `MCPL9MEMORYKEY` / `MCP_API_KEY` = shared legacy aliases.

8. Finalize systemd unit
   - [ ] Ensure `mcpmemory/deploy/systemd/l9-mcp.service`:
     - Uses `/opt/l9` as `WorkingDirectory`.
     - Uses the correct Python interpreter/venv.
     - Reads env from `/opt/l9/.env` (via `EnvironmentFile=` or wrapper script).
     - Restarts on failure with sane limits.
   - [ ] Add `docs/L9-MCP-IMPL.md` section:
     - “How to enable on VPS”:
       - `sudo cp /opt/l9/mcpmemory/deploy/systemd/l9-mcp.service /etc/systemd/system/`
       - `sudo systemctl daemon-reload && sudo systemctl enable --now l9-mcp`
       - `sudo ss -tlnp | grep ':9002'`
       - `curl -vk https://127.0.0.1:9001/mcptools` (via Caddy).

9. Caddy routing alignment
   - [ ] Update the Caddyfile **in the repo** (if tracked) and document VPS override:
     - Keep Caddy listening on `:9001` for MCP.
     - Ensure:
       - Non-MCP paths (e.g. `/`, `/api/*`, `/health`) → `127.0.0.1:8000` (`l9-api`).
       - MCP paths (e.g. `/mcp/*`) → `127.0.0.1:9002` (`l9-mcp`).
     - Example:
       ```caddyfile
       handle_path /mcp/* {
           reverse_proxy 127.0.0.1:9002
       }

       handle {
           reverse_proxy 127.0.0.1:8000
       }
       ```
   - [ ] Add a short doc `VPS-CADDY-MCP-CONFIG.md` explaining:
     - 9001 = TLS front door for MCP.
     - Upstream split: `/mcp/*` → MCP server, everything else → L9 API.

DELIVERABLE (PHASE 3):
- Repo-level docs + unit file describing standardized MCP deployment.

---

## PHASE 4 – CURSOR + INTERNAL CLIENT INTEGRATION

10. Cursor MCP configuration
   - [ ] In `Cursor-Directive.md` or `L9Cursor Integration Protocol.md`:
     - Document canonical Cursor MCP config:
       ```json
       {
         "mcpServers": {
           "l9-memory": {
             "command": "npx",
             "args": [
               "-y",
               "modelcontextprotocol/server-http"
             ],
             "env": {
               "MCP_SERVER_URL": "https://l9.quantumaipartners.com/mcp",
               "MCP_API_KEY": "<MCP_API_KEYC>"
             }
           }
         }
       }
       ```
   - [ ] Clarify:
     - Cursor must use the **MCP** key (`MCP_API_KEYC`).
     - All ingestion/extraction goes through MCP tools (not raw `/apiv1/memory`).

11. Internal L9 MCP client
   - [ ] Review `runtime/mcpclient.py`:
     - Ensure it can target the same MCP server (host/port + key).
     - Confirm call patterns:
       - `getmcpclient()` honors env like `MCP_SERVER_URL`, `MCP_API_KEY`.
   - [ ] Add optional wiring:
     - A config flag to let L9 itself call the MCP server (for dogfooding and E2E tests).

DELIVERABLE (PHASE 4):
- Updated docs for Cursor integration.
->  internal MCP client alignment.

---

## PHASE 5 – VALIDATION & GUARDRAILS

12. Automated checks
   - [ ] Add a CI smoke test script (e.g. `tests/test-mcp-server-smoke.py`) that:
     - Spins up MCP app in-process.
     - Calls `/mcptools` and `/mcpcall` for:
       - `searchmemory`
       - `savememory`
       - `contextinjection`
   - [ ] Add a governance check doc:
     - “MCP server is **preferred** path for external dev tools; raw HTTP routes are considered legacy escape hatches.”

13. Migration guardrails
   - [ ] In docs that previously called MCP “deprecated”:
     - Update language to:
       - “Legacy HTTP-only mode is supported but **not recommended** when MCP is available.”
   - [ ] Mark any direct Cursor-over-HTTP examples as legacy and point to MCP examples.

DELIVERABLE (PHASE 5):
- CI / docs that enforce MCP as the canonical path for Cursor and similar tools.

---

SUCCESS CRITERIA:
- `l9-mcp` systemd service runs on `127.0.0.1:9002` and passes health + tool smoke tests.
- Caddy on 9001 routes `/mcp/*` → MCP server and everything else → `l9-api`.
- Cursor, using MCP-only config and `MCP_API_KEYC`, can:
  - Save memory.
  - Search memory.
  - Invoke context injection / session learning.
  - See correct caller identity and audit trails in the substrate.
