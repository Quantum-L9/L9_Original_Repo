Those MCP files are intentionally **standalone infra** and only need three wires inside your L9 world:

1. **To the same Postgres memory DB L already uses**  
2. **To your VPS/systemd deployment flow**  
3. **To Cursor via MCP config**  

Nothing inside the existing `/l9/` Python package, Docker, or API server needs to import them.

***

## 1. Wire to the existing Postgres memory substrate

In `mcp-memory/.env`:

- Set `MEMORY_DSN` to the same Postgres DB your L9 memory substrate already uses (the `l9memory` DB/schema from your VPS setup).[1][2]

Example:

```env
MEMORY_DSN=postgresql://postgres:YOURPASSWORD@127.0.0.1:5432/l9memory
```

This lets the MCP server read/write the *same* `memory.shortterm/mediumterm/longterm/auditlog` tables L uses; no changes inside the L9 repo are required for that.[2][1]

***

## 2. Wire to VPS deployment (systemd)

The `mcp-memory/scripts/install.sh` and `systemd-l9-mcp.service` need to be invoked from your **deployment workflow**, but not imported by L9 code:

- After committing `mcp-memory/` into the repo and pushing to GitHub, on the VPS:

  ```bash
  # In /opt/l9 (your repo root)
  cd /opt/l9
  # Optional: pull latest
  git pull origin main

  # Run the MCP installer
  cd mcp-memory
  ./scripts/install.sh
  ```

This script:

- Copies `mcp-memory/` to `/opt/l9/mcp/memory`.[1]
- Creates `/opt/l9/venv-mcp`.  
- Installs `requirements-mcp.txt`.  
- Runs `scripts/migrate_db.py` (which uses `schema/init.sql`) to ensure the `memory.*` tables and indexes exist.[1]
- Installs and enables `l9-mcp.service` in systemd and starts it.[1]

No change is needed to:

- `/l9/server.py`, `/l9/kernelloader.py`, `/l9/memory_helpers.py`, `docker-compose.yml` or existing runtime wiring.[2]

***

## 3. Wire to Cursor (C) via MCP config

The only in-editor wiring is the `.cursormcp.json` (or MCP UI) in your **custom Cursor workspace**:

- Ensure you have an SSH tunnel from your laptop:

  ```bash
  ssh -L 9001:127.0.0.1:9001 admin@<vps-ip>
  ```

- Use the MCP config you generated:

```jsonc
{
  "mcpServers": {
    "l9-memory": {
      "command": "curl",
      "args": [
        "-X",
        "GET",
        "http://127.0.0.1:9001/mcptools",
        "-H",
        "Authorization: Bearer YOUR_MCP_API_KEY_HERE"
      ],
      "env": {
        "MCP_URL": "http://127.0.0.1:9001",
        "MCP_API_KEY": "YOUR_MCP_API_KEY_HERE"
      }
    }
  }
}
```

Cursor will then discover the tools `saveMemory`, `searchMemory`, `getMemoryStats`, `deleteExpiredMemories` from the MCP server and call `/mcpcall` on `http://127.0.0.1:9001` (through the tunnel).[1]

You control separation via the `userid` you pass in those tool calls; no extra wiring into L9 code is required for that.

***

## 4. Optional: docs / scripts references

If you want to make this “first-class” in the repo, the only *optional* wires are:

- Add a short note in `README.gold-standard.md` under “Memory Substrate” that there is an **external MCP memory server** in `mcp-memory/` for Cursor clients.[2]
- Add a helper in `scripts/` (e.g. `scripts/install-mcp-memory.sh`) that just calls `mcp-memory/scripts/install.sh`.

But for Option A, the core answer is: these MCP files are **fully decoupled**; they wire to:

- Postgres (via `MEMORY_DSN`),
- systemd on the VPS (via `install.sh` + `systemd-l9-mcp.service`),
- Cursor (via `.cursormcp.json`),

and do **not** need to be imported or referenced inside `/l9/` Python modules.
