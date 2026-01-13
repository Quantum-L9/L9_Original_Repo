

## 1. Make MCP usage “official”

- Lock in the URL and key you actually used to get the green E2E output and bake them into:
  - Your Cursor MCP config (`mcpServers.l9-memory` → `MCPSERVERURL` and `MCPAPIKEYC`).[1]
  - A small `mcp_memory/MCP-MEMORY-CAPSULE.md` checked into `/opt/l9` (and `/Users/ib-mac/Projects/L9`) so future you doesn’t have to rediscover the wiring.

## 2. Clean up Caddy story

- Ensure `/etc/caddy/Caddyfile` reflects the unified design:
  - `l9.quantumaipartners.com` → 8000 (already true).
  - `157.180.73.53:9001` → **only** `127.0.0.1:8000` (no 9002, no `/mcp/*` special case).
- Remove or rewrite any internal docs that still talk about a separate MCP server on 9002 so nobody “fixes” it back later.[1]

## 3. Nail the auth / rate-limit angle (optional but good)

- The MCP layer has support for:
  - Distinct keys (`MCPAPIKEY`, `MCPAPIKEYC`, `MCPAPIKEYL`, `MCPL9MEMORYKEY`).[1]
  - Per-IP + per-key rate limiting and auth-failure blocking.[1]
- You have not yet:
  - Run the “tight loop” tests from Mac that deliberately hit the limiter (50× `mcpcall` / `memorysave` to see 429s).[1]
  - Documented “what to do when Cursor gets blocked” (e.g., fix key, wait, optionally clear Redis keys).[1]

## 4. Graph / Neo4j posture (deliberate decision)

- Neo4j is wired in the docker-compose template and env, but the system is allowed to run in Postgres-only mode.:
  - “Enable Neo4j on VPS per `TODO-ON-VPS.md` (set `NEO4JPASSWORD` in `.env`, run `load_indexes_to_neo4j`, etc.) and then expose world-model HTTP routes.”

## 5. Git & docs hygiene

- Prior MRI runs found `/opt/l9` diverging from GitHub `main` (extra commits, backup compose files).[1]
- To avoid future confusion:
  - Move all edits (Caddy, MCP capsule, etc.) into `/Users/ib-mac/Projects/L9`, commit, push, then `git fetch` + `git reset --hard origin/main` on the VPS.
  - Keep `L9-VPS-BRIEFING.md` and the new MCP capsule updated to describe the unified MCP + memory setup you just proved out.
