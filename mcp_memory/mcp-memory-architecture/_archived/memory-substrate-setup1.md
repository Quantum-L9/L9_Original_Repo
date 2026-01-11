You already have exactly what you need in this repo: the Cursor MCP Memory Server implementation pack, plus the L9 OS memory substrate and client wiring. The way to “reuse the same infra with a different user ID” for the C repo is:

## 1. Use the existing MCP memory server

Your Dropbox doc `L9-MCP-IMPL.md` describes the dedicated MCP memory server for Cursor, with pgvector and FastAPI, including all tables and tools.[1]

Key points:

- Service lives at something like `127.0.0.1:9001` behind SSH tunnel from Cursor.[1]
- Environment config is `opt/l9/mcp/memory` (or similar) with `.env` containing:
  - `OPENAI_API_KEY`
  - `MEMORY_DSN` pointing at the same Postgres `l9memory` DB L9 uses
  - Retention, vector search, and MCP API key settings.[1]
- Tools exposed to Cursor:
  - `saveMemory`
  - `searchMemory`
  - `getMemoryStats`
  - `deleteExpiredMemories`[1]

That is already wired to the same Postgres/pgvector memory substrate your L9 OS uses, via the `memory.shortterm`, `memory.mediumterm`, `memory.longterm` tables.[1]

## 2. Match user IDs instead of creating new infra

The only field that ties Cursor-side memory to L9 memory is `userId` in the tables and in the MCP tools’ schemas.[1]

Your current schema:

- `memory.shortterm`: `user_id`, `session_id`, `kind`, `content`, `embedding`, `metadata`, `expires_at`.[1]
- `memory.mediumterm`: same, plus `importance`.[1]
- `memory.longterm`: `user_id`, `scope`, `kind`, `content`, `embedding`, `importance`, `tags`.[1]

And the MCP tools all require `userId` as an argument.[1]

To “reuse infra with a different user ID” for C:

- Decide the **Cursor-side user ID** you want to use for C, e.g. `cursor-c` or a UUID.
- In Cursor’s MCP config for this memory server, set:
  - `userId` param you pass in tool calls for C = whatever you want C’s memory namespace to be.
- In L9, for the same human user, you can:
  - Continue to use the existing L9 user ID for L,
  - Or also switch L to that same ID if you want shared memory,
  - Or keep them separate and only cross-query by explicitly choosing `userId` in your own tools.

No new DB, no new tables; just different `userId` strings. The MCP server is already written to scope all queries by `userId`.[1]

## 3. Wire Cursor to that MCP server (C’s side)

From the MCP implementation doc:[1]

- Ensure the MCP memory server is running on the VPS (FastAPI app `opt/l9/mcp/memory/main.py` or equivalent).
- Ensure SSH tunnel from your MacBook (Cursor) to VPS is running, e.g.:

  - `ssh -L 9001:127.0.0.1:9001 admin@<vps-ip>`

- In Cursor’s MCP config for the C repo:
  - Point to `http://127.0.0.1:9001` (or whatever host/port you set in `MCP_HOST/MCP_PORT`).[1]
  - Set the `Authorization` header or API key to `MCP_API_KEY` from the .env.[1]

Cursor’s `mcp.json` (or the IDE’s MCP UI) then exposes `saveMemory/searchMemory/getMemoryStats` tools directly in that repo, all backed by the same Postgres memory.

## 4. Reuse L9’s memory substrate semantics

From `README.gold-standard.md`, L9 OS uses a **multi-layer memory substrate** (short-term, long-term, semantic retrieval) as a core subsystem.[2]

- That substrate is exactly what the MCP memory server is talking to:
  - Same Postgres
  - Same pgvector extension
  - Same tables for semantic search and stats.[2][1]
- L9’s root README explicitly describes memory as a subsystem integrated with agents through the task queue and WebSocket orchestrator.[2]

So as long as your MCP memory server for Cursor points at the same Postgres DSN L9 uses, you are “plugged into” the same substrate.[2][1]

## 5. What you still need from you

To give precise, repo-level steps for “C wiring” inside this L9 repo (GMP workflow), the missing piece is:

- The **Cursor MCP config** (or the Dropbox link) for your separate C repo:
  - How you currently define tools there.
  - The exact user ID you want to use.

Send either:

- The Dropbox link content you mentioned, or
- The Cursor MCP config file for the C repo (or its snippet with the current memory wiring).

Then the next answer can be a strict Phase 0–6 plan plus exact code/config edits (file paths, diffs) to:

- Add a dedicated `userId` mapping for C requests; and/or
- Add an L9-side “proxy tool” that queries the same MCP memory server under that ID.

