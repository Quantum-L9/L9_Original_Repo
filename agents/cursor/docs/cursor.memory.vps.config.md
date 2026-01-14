```markdown
# L9 MCP Memory – Current VPS Reality Check

This file explains the **actual** MCP memory wiring on the L9 VPS so Cursor aligns with reality instead of legacy assumptions.

---

## 1. Current Production Topology

- VPS IP: `157.180.73.53`
- L9 code path on VPS: `/opt/l9`
- Main API: FastAPI (`l9-api`) on `127.0.0.1:8000`
- Postgres (memory substrate DB): `127.0.0.1:5432`, DB name `l9memory`
- Caddy:
  - 80/443 → `l9.quantumaipartners.com` → `127.0.0.1:8000`
  - 9001 → `157.180.73.53:9001` (HTTPS) → `127.0.0.1:8000`

**Key point:** There is **one** unified memory substrate behind the L9 API, not a separate MCP-only memory server.

---

## 2. What Is *Not* True Anymore (Legacy Model)

The following assumptions are **outdated** and should NOT drive behavior:

1. **Separate MCP process**  
   - Old idea: “MCP memory server runs as its own FastAPI app on some internal port (e.g., 9002), and Caddy routes `/mcp/*` there.”
   - Current reality: There is no dedicated `uvicorn src.main:app --port 9002` process in production. Memory is served by the main `l9-api` app.

2. **Hard-coded MCP endpoints like `/mcp/health` and `/mcp/sse`**  
   - Old idea: `/mcp/health` and `/mcp/sse` live on a separate MCP service.  
   - Current reality: MCP-style memory access is provided **through the unified L9 API + memory substrate**, not via a separate `/mcp/*` namespace on another process.

3. **“MCP Memory Server ❌ Not running” as a real outage**  
   - That statement only makes sense if you expect the deprecated MCP server binary.  
   - The system is healthy: L9 API is up, Caddy is proxying correctly, and the Postgres memory substrate is reachable and in use.

---

## 3. What Cursor Is Seeing (and Misinterpreting)

From Cursor’s perspective, recent checks looked like this:

- `l9.quantumaipartners.com` DNS: not resolving in the environment that performed the check.
- `https://157.180.73.53:9001`:
  - Port 9001 is listening.
  - Response is the **L9 API health** (`/health` from the unified FastAPI app), not a standalone MCP server banner.
- `http://157.180.73.53:9001/mcp/health`:
  - Returns: “Client sent an HTTP request to an HTTPS server.”
  - Explanation: Caddy serves **HTTPS** on 9001; hitting it with plain HTTP is expected to fail.

Cursor then concluded:

> “MCP Memory Server ❌ Not running”

This conclusion assumes the old “separate MCP server” architecture. In the **current** architecture:

- Memory routes are part of the unified L9 API process.
- Caddy’s 9001 site is just a **TLS front door** into that L9 API, not a separate MCP app.

---

## 4. The Truth: Unified Memory Substrate

### Database

- DSN pattern:

  ```text
  postgresql://POSTGRES_USER:POSTGRES_PASSWORD@HOST:5432/POSTGRES_DB
  ```

- In production, this resolves to something like:

  ```text
  postgresql://postgres:********@127.0.0.1:5432/l9memory
  ```

- This database contains:
  - `packetstore`, `semanticmemory`, `knowledgefacts`, and other tables used by the L9 memory substrate.
  - Row-level security (RLS) is applied for multi-tenant isolation.

### Application layer

- The unified FastAPI app (`l9-api`) exposes both:
  - Core L9 API routes (`/health`, `/chat`, etc.).
  - Memory substrate routes (packet ingestion, semantic search, stats, etc.).

- Caddy simply forwards:
  - `*:443` (hostname: `l9.quantumaipartners.com`) → `127.0.0.1:8000`
  - `*:9001` → `127.0.0.1:8000` (TLS on 9001, same backend).

**Therefore:**  
“MCP memory” is just **one more client** of the unified L9 memory substrate, not a separate server.

---

## 5. How Cursor Should Treat MCP Memory

Instead of trying to resurrect the deprecated MCP server, treat the L9 stack as follows:

1. **Do NOT assume a dedicated “MCP memory server” binary**  
   - No: “Start uvicorn `src.main:app` on 9002 and wire `/mcp/*` to it.”
   - Yes: “Use the existing L9 API + memory substrate, which is already running and wired to Postgres.”

2. **Do NOT infer outages from missing `/mcp/*` endpoints**  
   - Lack of a `/mcp/health` or `/mcp/sse` endpoint does **not** mean memory is down.
   - It means the interface is consolidated under the unified L9 API and substrate, per the newer architecture.

3. **Do NOT propose legacy fixes as mandatory**  
   - Proposals like “start `mcp_memory` venv + uvicorn on 9002 and patch Caddy `/mcp/*`” should be treated as **optional migration paths**, not as “production is broken.”
   - The actual production baseline is **unified L9 API + memory substrate**, as described above.

---

## 6. What Is Actually Needed From Cursor

When reasoning about MCP memory for this environment, Cursor should:

1. **Align with the unified architecture**  
   - Assume the memory substrate is accessed via the L9 API’s configured endpoints over HTTPS (via Caddy), not via a separate MCP server.

2. **Stop flagging “MCP Memory Server ❌ Not running” as a hard failure**  
   - Instead, recognize: “Legacy MCP server not present; memory is served by the unified L9 API.”

3. **When suggesting actions, favor these patterns:**
   - “Confirm L9 API health on 8000 / 9001.”
   - “Confirm Postgres `l9memory` connectivity via the configured DSN.”
   - “Use existing memory substrate routes instead of inventing a separate MCP stack.”

---

## 7. If a Dedicated MCP Frontend Is Ever Desired

If, in the future, a dedicated MCP server is desired as a **thin frontend** into the same substrate, the correct approach is:

- Start a small MCP adapter process that:
  - Speaks MCP to clients.
  - Talks to the existing L9 memory substrate (same DB / same abstraction).
- Route `/mcp/*` in Caddy to that adapter.
- **Do not** create a second, divergent memory database or substrate.

But that is an **optional enhancement**, not a correctness requirement for the current production system.

---

## TL;DR for Cursor

- There is **no separate MCP memory server** binary in this environment.
- MCP memory is provided by the **unified L9 API + Postgres memory substrate**, fronted by Caddy on 443 and 9001.
- Treat "legacy MCP server missing" as **"architecture evolved"**, not "system broken."

---

## 8. Working Solution: cursor_memory_client.py

Since the mcp.json SSE config won't work (no `/mcp/sse` endpoint), use the REST client:

```bash
# Stats
python .cursor-commands/cursor-memory/cursor_memory_client.py stats

# Search
python .cursor-commands/cursor-memory/cursor_memory_client.py search "Igor preferences"

# Write
python .cursor-commands/cursor-memory/cursor_memory_client.py write "Content here" --kind preference

# Health
python .cursor-commands/cursor-memory/cursor_memory_client.py health
```

**Requires:** `L9_EXECUTOR_API_KEY` in `.env` (already configured).

**Tested 2026-01-07:**
- ✅ Health: `healthy`, database connected
- ✅ Stats: 26 packets, 4 embeddings, 125 facts
- ✅ Search: Returns semantic results
- ✅ Write: Persists to packet_store + 4 other tables

---

## 9. What Would Make mcp.json Work

For Cursor's native MCP integration to work, L9 API would need:

1. SSE endpoint at `/mcp/sse` implementing MCP protocol
2. Tool definitions for `memory_search`, `memory_write`, etc.
3. Auth using `MCP_API_KEY_C` header

This is an **optional enhancement** — the REST client works now.
```