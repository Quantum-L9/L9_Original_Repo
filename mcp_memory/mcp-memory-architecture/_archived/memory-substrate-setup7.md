Perfect! **L-CTO Agent credentials are NOW GENERATED.** Follow the 6 steps above in order. Let me walk you through each one:

***

## 🚀 **QUICK EXECUTION PLAN**

### **STEP 1: SSH into VPS and update `.env`**

```bash
ssh admin@157.180.73.53
nano /opt/l9/.env
```

Add these lines:
```bash
L_CTO_USER_ID=504cb4e9-9016-46a4-bfba-bf04d10b292b
L_CTO_USERNAME=cto_62efb5d2
L_CTO_POSTGRES_PASSWORD=1ce2f7ed58c508a7f1eacef25328ed06082321f7027c41327a99fcbbccf51511
MCP_API_KEY=9a260d163ccae7c5a0f259d79a4f8ec71cab570fc2ad72d7e580849577001634
```

Save: `Ctrl+O`, `Enter`, `Ctrl+X`

***

### **STEP 2: Create PostgreSQL user on VPS**

```bash
docker exec -it l9-postgres psql -U postgres -d l9memory
```

Then in psql, paste this entire block (all 6 lines):

```sql
CREATE USER cto_62efb5d2 WITH PASSWORD '1ce2f7ed58c508a7f1eacef25328ed06082321f7027c41327a99fcbbccf51511';
GRANT CONNECT ON DATABASE l9memory TO cto_62efb5d2;
GRANT USAGE ON SCHEMA public TO cto_62efb5d2;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO cto_62efb5d2;
GRANT INSERT ON packetstore TO cto_62efb5d2;
GRANT INSERT ON semanticmemory TO cto_62efb5d2;
GRANT SELECT ON semanticmemory TO cto_62efb5d2;
```

Then exit psql:
```bash
\q
```

***

### **STEP 3: Update `.cursormcp.json` on Your Mac**

Create/update: `~/.cursormcp.json` or in your L9 repo root (wherever Cursor reads it)

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
        "Authorization: Bearer 9a260d163ccae7c5a0f259d79a4f8ec71cab570fc2ad72d7e580849577001634",
        "-s"
      ],
      "env": {
        "MCP_URL": "http://157.180.73.53:9001",
        "MCP_API_KEY": "9a260d163ccae7c5a0f259d79a4f8ec71cab570fc2ad72d7e580849577001634",
        "CURSOR_L_CTO_USER_ID": "504cb4e9-9016-46a4-bfba-bf04d10b292b",
        "L_CTO_USERNAME": "cto_62efb5d2"
      }
    }
  }
}
```

***

### **STEP 4: Test PostgreSQL connection**

```bash
docker exec -it l9-postgres psql -U cto_62efb5d2 -d l9memory -c "SELECT COUNT(*) FROM packetstore;"
```

**Expected output:**
```
 count
-------
     0
(1 row)
```

***

### **STEP 5: Test MCP API from Mac**

Open Mac terminal:

```bash
curl -H "Authorization: Bearer 9a260d163ccae7c5a0f259d79a4f8ec71cab570fc2ad72d7e580849577001634" \
  http://157.180.73.53:9001/mcptools
```

**Expected output:** JSON array with tools like `saveMemory`, `searchMemory`, etc.

***

### **STEP 6: Test in Cursor**

1. **Restart Cursor** (to reload `.cursormcp.json`)
2. **Open Cursor** on your L9 repo
3. **In chat**, type: `@mcp l9-memory`
4. **Should see available tools**: saveMemory, searchMemory, getMemoryStats, deleteExpiredMemories

***

## ✅ **VERIFICATION CHECKLIST**

- [ ] Updated `/opt/l9/.env` with L_CTO credentials
- [ ] Created PostgreSQL user `cto_62efb5d2` on VPS
- [ ] Granted all necessary permissions to user
- [ ] Updated `.cursormcp.json` on Mac with MCP_API_KEY
- [ ] Tested PostgreSQL connection from VPS (`SELECT COUNT...` works)
- [ ] Tested MCP API from Mac (`curl` returns JSON tools)
- [ ] Restarted Cursor
- [ ] Verified `@mcp l9-memory` shows tools in Cursor chat

***

**Once all 6 steps are done and checklist passes, L-CTO agent is LIVE and wired to Cursor.** Ready to test?
