# ⚠️ DEPRECATED: This File is Outdated

**Status:** This file is **OUTDATED** as of 2026-01-09  
**Reason:** MCP Memory Server has been **REVIVED and ACTIVATED** (GMP-49)

## Current Status

The MCP Memory Server is **ACTIVE** and serves as the primary interface for Cursor memory operations:

- ✅ **MCP Server:** Running on port 9002 (systemd service `l9-mcp`)
- ✅ **Caddy Routing:** Routes `/mcp/*` to MCP server (port 9002)
- ✅ **Cursor Integration:** `cursor_memory_client.py` uses MCP tools exclusively
- ✅ **Unified Substrate:** Uses `packet_store` + `memory_embeddings` (not deprecated tables)

## Current Memory Access

**PRIMARY METHOD:** Use MCP Memory Server

```bash
# Search memory (via MCP)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py search "query"

# Write to memory (via MCP)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py write "content" --kind lesson

# Check health (via MCP)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py health

# Get stats (via MCP)
python3 .cursor-commands/cursor-memory/cursor_memory_client.py stats
```

**Legacy HTTP-only mode** is supported but **not recommended** when MCP is available.

## Migration Notes

- **Old:** REST API only (`/api/v1/memory/*`)
- **New:** MCP protocol preferred (`/mcp/call` with MCP tools)
- **Backward Compatibility:** REST routes still work but are legacy escape hatches

## See Also

- **Active Documentation:** `mcp_memory/README.md`
- **Deployment Guide:** `mcp_memory/docs/L9-MCP-IMPL.md`
- **GMP Report:** `reports/GMP_Report_GMP-49-MCP-Server-Revival.md`


