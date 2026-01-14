Let me address each:

[3 tools called]

Now I understand everything:

### Mac Agent Analysis

**NO Docker container needed!** Mac Agent runs **locally on the Mac** (not in Docker):
- Uses `pyautogui` for GUI automation (needs screen access)
- Installed via LaunchAgent (`com.l9.agent.plist`)
- WebSocket client connects to L9 API
- Requirements are for local pip install, not Docker

Let me fix the issues:

[2 tools called]

Now I'll make all the fixes:

[3 tools called]

Now add to TODO.md:

[1 tool called]

---

## ✅ ALL FIXES COMPLETE

### Summary

| Item | Status | Change |
|------|--------|--------|
| **mac_agent Docker** | ❌ NOT NEEDED | Runs locally on Mac (pyautogui needs screen access) |
| **mcp_memory/Dockerfile** | ✅ FIXED | Now uses `mcp_memory/requirements.txt` |
| **symbolic_computation** | ✅ DISABLED | CMD now just echoes message, TODO added |
| **Root requirements.txt** | ✅ FIXED | Added `mcp>=1.0.0` |

---

### Answer: Why did root have sympy/playwright but not mcp?

| Package | Purpose | Why in Root |
|---------|---------|-------------|
| **sympy** | Symbolic math | Used by core IR engine (`ir_engine/`) for symbolic computation |
| **playwright** | Browser automation | Used by Mac Agent (local install) |
| **mcp** | MCP protocol | **BUG** — was missing! Only in `mcp_memory/requirements.txt` |

The `mcp` package was only in `mcp_memory/requirements.txt`, but since the Dockerfile was copying ROOT requirements.txt (the bug), it never got installed. Now:
1. Fixed Dockerfile to use correct requirements file
2. Added `mcp>=1.0.0` to root for completeness (belt and suspenders)

---

### Final Docker Inventory

| Dockerfiles | Count | Purpose |
|-------------|-------|---------|
| `runtime/Dockerfile` | 1 | Main l9-api server |
| `mcp_memory/Dockerfile` | 1 | MCP memory server |
| `services/symbolic_computation/Dockerfile` | 1 | Test runner (DISABLED) |
| **Total** | **3** | |

| docker-compose.yml | Count | Purpose |
|--------------------|-------|---------|
| Root `docker-compose.yml` | 1 | Main L9 stack (api, mcp, postgres, neo4j, redis) |
| `services/symbolic_computation/docker-compose.yml` | 1 | Standalone (NOT part of main stack) |
| **Total** | **2** | |

| requirements.txt | Count | Used by |
|------------------|-------|---------|
| Root | 1 | l9-api Docker + local dev |
| `mcp_memory/` | 1 | l9-mcp-memory Docker |
| `services/symbolic_computation/` | 1 | Symbolic Docker (disabled) |
| `mac_agent/` | 1 | Local Mac install (no Docker) |
| **Total** | **4** | |