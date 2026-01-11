Perfect. I hear you loud and clear:

1. **No SSH tunnel** – you don't want background processes draining your Mac's CPU
2. **Direct HTTP API** – access MCP and L9 tools over clean HTTP from Cursor, VPS handles it remotely  
3. **Fix the zsh parse error** – that openssl command had a syntax issue

Here's the **clean solution**:

***

## 1. **Generate Credentials (Fixed zsh syntax)**

```bash
# Generate unique password (32-char hex)
POSTGRES_PASSWORD=$(openssl rand -hex 32)

# Generate MCP API key (32-char hex)
MCP_API_KEY=$(openssl rand -hex 32)

# Generate UUID v4 for user
USER_ID=$(python3 -c "import uuid; print(uuid.uuid4())")

# Generate username
CURSOR_USERNAME="cursor_$(openssl rand -hex 4)"

# Print all together
echo "=== SAVE THESE ===" 
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
echo "MCP_API_KEY=$MCP_API_KEY"
echo "USER_ID=$USER_ID"
echo "CURSOR_USERNAME=$CURSOR_USERNAME"
```

***

## 2. **No SSH Tunnel Needed – Use Public API Path**

Your VPS MCP server runs at `http://157.180.73.53:9001` (publicly accessible via Caddy reverse proxy on your VPS).

**`.cursormcp.json` on your Mac** (no tunnel required):

```json
{
  "mcpServers": {
    "l9-memory": {
      "command": "curl",
      "args": [
        "-X",
        "GET",
        "http://157.180.73.53:9001/mcptools",
        "-H",
        "Authorization: Bearer YOUR_MCP_API_KEY_HERE",
        "-s"
      ],
      "env": {
        "MCP_URL": "http://157.180.73.53:9001",
        "MCP_API_KEY": "YOUR_MCP_API_KEY_HERE"
      }
    }
  }
}
```

Replace `YOUR_MCP_API_KEY_HERE` with the value from the credentials above.

***

## 3. **VPS Configuration (one-time, in `/opt/l9/.env`)**

```bash
# ============================================
# MCP Server (exposes to Cursor remotely)
# ============================================

MCP_HOST=0.0.0.0  # <-- THIS, not 127.0.0.1
MCP_PORT=9001
MCP_ENV=production
MCP_API_KEY=YOUR_MCP_API_KEY_HERE

# PostgreSQL (memory substrate)
MEMORY_DSN=postgresql://cursor_a7f9b2c1:YOUR_POSTGRES_PASSWORD@localhost:5432/l9memory

# ============================================
# Everything else...
# ============================================

OPENAI_API_KEY=sk-...
# ... (rest as before)
```

**Key change: `MCP_HOST=0.0.0.0` instead of `127.0.0.1`**. This makes the server listen on all interfaces (including the public IP), which Caddy reverse proxy on your VPS already handles securely.

***

## 4. **Caddy Reverse Proxy Setup (VPS)**

Your VPS already has Caddy. Add this to `/opt/l9/caddy/Caddyfile` (or create if missing):

```
l9-mcp.yourdomain.com {
    reverse_proxy http://127.0.0.1:9001
}

# OR if using IP:
157.180.73.53:9001 {
    reverse_proxy http://127.0.0.1:9001
}
```

Then reload Caddy:
```bash
sudo systemctl reload caddy
```

Now Cursor can hit `http://157.180.73.53:9001/mcptools` **without any tunnel**.

***

## 5. **Summary: What Runs Where**

| Component | Location | Network Path | Cursor Access |
|-----------|----------|--------------|---|
| **Cursor IDE** | Your Mac | N/A | Reads `.cursormcp.json` |
| **MCP API Server** | VPS (`/opt/l9/mcp-memory`) | Listens on `0.0.0.0:9001` | `http://157.180.73.53:9001` (Caddy proxy) |
| **PostgreSQL** | VPS (`docker` container) | `localhost:5432` | Via MCP server only |
| **L9 Core API** | VPS (`docker`) | `localhost:8000` | Via Caddy at port `443` |

**No tunnel, no background processes, no CPU drain.**

***

## 6. **Test It**

From your Mac terminal:
```bash
curl -H "Authorization: Bearer YOUR_MCP_API_KEY_HERE" \
  http://157.180.73.53:9001/mcptools
```

Should return JSON with available MCP tools.

***

## 7. **Complete `.cursormcp.json` Template**

```json
{
  "mcpServers": {
    "l9-memory": {
      "command": "curl",
      "args": [
        "-X",
        "GET",
        "http://157.180.73.53:9001/mcptools",
        "-H",
        "Authorization: Bearer b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
        "-s"
      ],
      "env": {
        "MCP_URL": "http://157.180.73.53:9001",
        "MCP_API_KEY": "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
        "CURSOR_DB_USER": "cursor_a7f9b2c1",
        "CURSOR_DB_PASSWORD": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
        "CURSOR_USER_ID": "550e8400-e29b-41d4-a716-446655440000"
      }
    }
  }
}
```

***

**Done. No tunnel. No CPU overhead. Just HTTP API calls from Cursor to your VPS.**
