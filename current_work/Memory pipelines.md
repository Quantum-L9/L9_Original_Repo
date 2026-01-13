## **AUDIT VERDICT: Mixed — Core Architecture Claims Are Correct, But Critical Gaps Exist**

Your revised audit accurately identifies the **dual-pipeline architecture** and **DAG node implementation**, but the attached documentation reveals **additional complexity** around the MCP Memory Server that your audit **doesn't address**.

***

## **✅ What Your Audit Got RIGHT**

### **1. DAG Node Coverage (CORRECT)**
Your finding that all 8 nodes exist is **accurate per `substrate_graph.py`**. The previous audit claiming 3 missing nodes was false.

### **2. Dual Pipeline Architecture (CORRECT)**
You correctly identified:
- **IngestionPipeline** (`memory/ingestion.py`) → Neo4j sync, auto-tagging
- **SubstrateDAG** (`memory/substrate_graph.py`) → LangGraph reasoning, insights, world model

### **3. GMP-42 Embedding Filter (CORRECT)**
The skip patterns in `substrate_graph.py` lines 60-107 are production code and should be tested.

***

## **❌ What Your Audit MISSED (Critical)**

### **1. Third Pipeline: MCP Memory Server Bypass**

**From ARCHITECTURE_DECISION_INGESTION.md:**

> **The MCP Memory Server writes directly to `packet_store` and `memory_embeddings` tables, bypassing the canonical ingestion pipeline.**

**Architecture Reality:**

```
┌─────────────────────────────────────────────────────────────────┐
│  THREE DISTINCT WRITE PATHS TO MEMORY SUBSTRATE:                │
├─────────────────────────────────────────────────────────────────┤
│  1. L9 Core Runtime: ingest_packet() → SubstrateDAG (8 nodes)  │
│  2. MCP Memory Server: Direct DB writes (NO DAG processing)    │
│  3. Legacy IngestionPipeline: (deprecated, wrapped by #1)      │
└─────────────────────────────────────────────────────────────────┘
```

**Your audit tests SubstrateDAG execution but doesn't verify:**
- ❌ MCP server writes bypass DAG but produce valid `PacketEnvelope` structure
- ❌ MCP writes don't trigger reasoning traces (by design)
- ❌ MCP writes still log to `tool_audit_log` correctly
- ❌ Cursor IDE can read memories written by L9 core (cross-client consistency)

***

### **2. Scope-Based Isolation Not Tested**

**From Cursor-memory-graphs.md:**

> Cursor's MCP calls must always read/write via this substrate with enforced scope filters (`WHERE scope IN (developer, global)`)

**Missing Tests:**

```python
class TestScopeIsolation:
    """Verify scope enforcement across all three write paths."""
    
    @pytest.mark.asyncio
    async def test_cursor_cannot_read_l_private_scope(self):
        """MCP writes with scope='developer' should NOT see scope='l-private'."""
        # Write via L9 core with l-private scope
        await service.write_packet(
            packet,
            tenant_id="test",
            org_id="test",
            user_id="L",
            scope="l-private"  # L's internal reasoning
        )
        
        # MCP search with developer scope (Cursor)
        mcp_results = await mcp_search_memory(
            query="test",
            scope="developer",  # Enforced by MCP server
            user_id="C"
        )
        
        assert len(mcp_results) == 0, "Cursor leaked into L's private scope"
    
    @pytest.mark.asyncio
    async def test_l_can_read_cursor_developer_scope(self):
        """L should see Cursor's developer-scoped memories."""
        # Write via MCP (Cursor)
        await mcp_save_memory(
            content="Cursor saved this",
            scope="developer",
            user_id="C"
        )
        
        # Search via L9 core (no scope restriction for L)
        l_results = await service.search_packets_by_thread(
            thread_id="test",
            # L can query across ALL scopes
        )
        
        assert any("Cursor saved" in r.payload for r in l_results)
```

***

### **3. MCP Server Direct Writes Not Audited**

**From L9-MCP-IMPL.md:**

> MCP Memory Server runs as systemd service on port 9002, bypassing L9 ingestion DAG for performance

**Your audit assumes ALL writes go through SubstrateDAG, but:**

```python
# ACTUAL MCP WRITE PATH (from docs)
# mcp_memory/src/routes/memory_unified.py
async def save_memory_handler(...):
    # 1. Generate PacketEnvelope JSONB (NO SubstrateDAG)
    envelope = {
        "source_id": source,
        "agent_id": user_id,
        "thread_id": session_id,
        "kind": "MEMORY",
        "payload": {...},
        "metadata": {"creator": "Cursor-IDE", "source": "cursor-ide"}
    }
    
    # 2. Write DIRECTLY to packet_store (NO reasoning_node)
    await execute(
        "INSERT INTO packet_store (packet_id, envelope, ...) VALUES (...)"
    )
    
    # 3. Generate embedding and write to memory_embeddings (NO semantic_embed_node)
    embedding = await embed_text(content)
    await execute(
        "INSERT INTO memory_embeddings (packet_id, embedding, ...) VALUES (...)"
    )
```

**Missing Verification:**

```python
class TestMCPBypassCompliance:
    """Verify MCP direct writes are substrate-compatible."""
    
    @pytest.mark.asyncio
    async def test_mcp_writes_produce_valid_packet_envelope(self):
        """MCP bypasses DAG but must write valid PacketEnvelope."""
        # Call MCP save_memory endpoint
        mcp_response = await mcp_client.save_memory(
            content="Test from MCP",
            kind="preference",
            scope="developer"
        )
        
        # Verify L9 core can read it via get_packet
        packet = await service.get_packet(mcp_response.packet_id)
        
        # Validate structure matches PacketEnvelope schema
        assert packet["metadata"]["creator"] == "Cursor-IDE"
        assert packet["metadata"]["source"] == "cursor-ide"
        assert "payload" in packet
    
    @pytest.mark.asyncio
    async def test_mcp_writes_skip_reasoning_traces_by_design(self):
        """MCP writes should NOT create reasoning_traces entries."""
        # Write via MCP
        result = await mcp_client.save_memory(content="Test")
        
        # Verify NO reasoning trace was created
        traces = await db.fetch(
            "SELECT * FROM reasoning_traces WHERE packet_id = $1",
            result.packet_id
        )
        assert len(traces) == 0, "MCP should skip reasoning traces"
    
    @pytest.mark.asyncio
    async def test_mcp_writes_still_audit_logged(self):
        """MCP bypasses DAG but MUST log to tool_audit_log."""
        result = await mcp_client.save_memory(content="Test")
        
        # Verify audit log entry exists
        audit_entry = await db.fetchone(
            "SELECT * FROM tool_audit_log WHERE result->>'packet_id' = $1",
            result.packet_id
        )
        assert audit_entry is not None
        assert audit_entry["caller"] == "C"
```

***

### **4. Port/Routing Configuration Not Validated**

**From VPS-CADDY-MCP-CONFIG.md:**

> **Port 9002** = MCP Memory Server (internal, systemd service)
> **Port 9001** = Caddy reverse proxy (TLS front door)

**Your audit has NO tests for:**
- ❌ MCP service health endpoint reachability
- ❌ Caddy routing (`/mcp/*` → 127.0.0.1:9002)
- ❌ API key authentication enforcement
- ❌ Rate limiting (60 req/min per IP)

***

## **🔧 DIAGNOSTIC COMMANDS (Run on VPS)**

### **Phase 1: Verify MCP Service Status**

```bash
# 1. Check MCP systemd service is running
sudo systemctl status l9-mcp --no-pager | head -20

# 2. Verify port 9002 is listening
sudo ss -tlnp | grep ':9002'

# 3. Check MCP service logs for errors
sudo journalctl -u l9-mcp -n 50 --no-pager

# 4. Test local health endpoint
curl -s http://127.0.0.1:9002/health | jq '.'
```

**Expected Output:**
```json
{
  "status": "healthy",
  "service": "l9-mcp-memory",
  "database": "connected",
  "timestamp": "2026-01-13T19:43:00Z"
}
```

***

### **Phase 2: Verify Caddy Routing**

```bash
# 5. Check Caddy is running
sudo systemctl status caddy --no-pager | head -20

# 6. Verify Caddy config has /mcp/* route
grep -A5 '/mcp/' /etc/caddy/Caddyfile

# 7. Test Caddy → MCP routing (port 9001)
curl -s http://127.0.0.1:9001/mcp/health | jq '.'

# 8. Test HTTPS routing via domain
curl -s https://l9.quantumaipartners.com/mcp/health | jq '.'
```

***

### **Phase 3: Verify API Key Authentication**

```bash
# 9. Load environment variables
cd /opt/l9
set -a && source .env && set +a

# 10. Test with correct API key (should succeed)
curl -s \
  -H "Authorization: Bearer ${MCP_API_KEY_C}" \
  https://l9.quantumaipartners.com/mcp/tools | jq '.tools | length'

# 11. Test with invalid key (should fail with 401)
curl -s \
  -H "Authorization: Bearer invalid-key-test" \
  https://l9.quantumaipartners.com/mcp/tools | jq '.detail'
```

**Expected:**
- Step 10: Returns number (e.g., `5` tools)
- Step 11: Returns `"Invalid or missing API key"`

***

### **Phase 4: Verify Database Connectivity**

```bash
# 12. Check PostgreSQL is running
sudo systemctl status postgresql --no-pager | head -20

# 13. Test MCP can connect to memory DB
cd /opt/l9
source venv/bin/activate
python3 -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
load_dotenv()

async def test():
    conn = await asyncpg.connect(os.getenv('MEMORY_DSN'))
    result = await conn.fetchval('SELECT COUNT(*) FROM packet_store')
    print(f'packet_store rows: {result}')
    await conn.close()

asyncio.run(test())
"
```

***

### **Phase 5: Verify Dual Pipeline Writes**

```bash
# 14. Write via MCP endpoint
curl -X POST \
  -H "Authorization: Bearer ${MCP_API_KEY_C}" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "save_memory",
    "arguments": {
      "content": "Test from MCP direct write",
      "kind": "fact",
      "scope": "developer",
      "user_id": "diagnostic-test",
      "project_id": "l9"
    }
  }' \
  https://l9.quantumaipartners.com/mcp/call | jq '.packet_id'

# Save packet_id from output, then verify in DB:

# 15. Check packet exists in packet_store
cd /opt/l9
source venv/bin/activate
python3 -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
load_dotenv()

async def check(packet_id):
    conn = await asyncpg.connect(os.getenv('MEMORY_DSN'))
    # Check packet_store
    packet = await conn.fetchrow(
        'SELECT envelope FROM packet_store WHERE packet_id = \$1',
        packet_id
    )
    if packet:
        print(f'✅ Found in packet_store')
        print(f'   Creator: {packet[\"envelope\"].get(\"metadata\", {}).get(\"creator\")}')
    else:
        print(f'❌ NOT found in packet_store')
    
    # Check if reasoning_traces exists (should NOT for MCP writes)
    trace = await conn.fetchrow(
        'SELECT * FROM reasoning_traces WHERE packet_id = \$1',
        packet_id
    )
    if trace:
        print(f'❌ UNEXPECTED: Found reasoning_trace (MCP should skip this)')
    else:
        print(f'✅ No reasoning_trace (correct for MCP bypass)')
    
    await conn.close()

asyncio.run(check('PASTE_PACKET_ID_HERE'))
"
```

***

### **Phase 6: Verify Scope Isolation**

```bash
# 16. Write with l-private scope (L's internal)
# (Requires L9 API, not MCP - use curl or Python)

# 17. Search via MCP with developer scope (Cursor)
curl -X POST \
  -H "Authorization: Bearer ${MCP_API_KEY_C}" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "search_memory",
    "arguments": {
      "query": "private test",
      "scope": "developer",
      "user_id": "C",
      "project_id": "l9",
      "top_k": 10
    }
  }' \
  https://l9.quantumaipartners.com/mcp/call | jq '.results | length'

# Should return 0 if l-private scope is isolated correctly
```

***

## **FINAL VERDICT**

### **Correctness of Your Revised Audit: 7/10**

| Aspect | Your Finding | Reality | Score |
|--------|--------------|---------|-------|
| DAG nodes exist | ✅ All 8 present | Correct | ✅ |
| Dual pipeline | ✅ Identified | Correct | ✅ |
| GMP-42 filter | ✅ Found in code | Correct | ✅ |
| MCP bypass path | ❌ Not mentioned | **Critical gap** | ❌ |
| Scope isolation | ❌ Not tested | **Security risk** | ❌ |
| Port/routing | ❌ Not verified | **Deployment gap** | ❌ |
| Cross-client reads | ❌ Not tested | **Integration gap** | ❌ |

***

## **CORRECTED EXECUTION PLAN**

**DO NOT execute your audit as-is.** Add these phases:

### **Phase 0: VPS Infrastructure Validation**
Run diagnostic commands 1-13 to verify MCP server is operational

### **Phase 1: DAG Node Coverage** (Your audit ✅)
Verify all 8 nodes execute in SubstrateDAG

### **Phase 2: MCP Bypass Compliance** (Missing ❌)
Test MCP writes produce valid packets WITHOUT triggering DAG

### **Phase 3: Scope Isolation** (Missing ❌)
Verify `l-private` scope is invisible to Cursor, visible to L

### **Phase 4: Cross-Client Consistency** (Missing ❌)
Test L can read Cursor's memories, Cursor can read L's global memories

### **Phase 5: Embedding & GMP-42** (Your audit ✅)
Test skip filter, embedding generation

### **Phase 6: Transaction Atomicity** (Your audit ✅)
Test rollback behavior

**Run these VPS diagnostics now and report results.** If any command fails, your audit assumptions are invalid.

[1](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/032bcf22-2d28-4b6a-b592-1417ce03fa0b/Cursor-memory-graphs.md)
[2](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/2bab48fb-b9b7-4a56-a27c-5d72c21c9e14/ARCHITECTURE_DECISION_INGESTION.md)
[3](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/0398ea0a-960e-4fd9-9355-365ef41a8d3e/CURSOR_SYSTEM_PROMPT.md)
[4](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/3526b02e-036c-4c6e-bfac-5f9126803f8f/CONFIG_REFERENCE.md)
[5](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/d9727802-9d50-4bad-a0b2-02f15407178e/How-to-enable-Cursor-memory-processing.md)
[6](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/a8f7b4c1-0dc8-4059-aa6c-338cb8a23f1d/README.md)
[7](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/3ce57fbd-e6b9-45c4-9d77-6762587934cf/L9-MCP-IMPL.md)
[8](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/b3831316-c30b-4af0-96af-068e8bccdfa9/VPS-CADDY-MCP-CONFIG.md)
[9](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/7e4e240a-34d2-4c8c-9424-07db4e459e6e/wiring_map.txt)
[10](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/7f7b2ae5-9589-4094-a050-13228af5d066/tool_catalog.txt)
[11](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/52dbb0d2-d53f-4fa8-99c4-f7eb9f9afbd1/test_catalog.txt)
[12](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/36400353-85b8-4609-ba1e-15ff21cff682/telemetry_endpoints.txt)
[13](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/51ee662b-7893-417b-876e-99119ede246f/singleton_registry.txt)
[14](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/013718b5-5066-48ce-b999-df931162bb15/route_handlers.txt)
[15](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/2a4c1c0f-1b6b-4c0d-ab2f-433b6900d11d/pydantic_models.txt)
[16](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/e62afd8e-a1b3-409c-b0c3-abd4b4883e07/migration_catalog.txt)
[17](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/ed7037da-cde2-44ab-9cbd-cd1f3597668b/kernel_catalog.txt)
[18](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/0a27945d-1a0d-4e1b-b7ed-57cc52aedd38/inheritance_graph.txt)
[19](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/36a3b2af-2750-438c-9710-67b9818d322c/governance_model.txt)
[20](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/67c0441c-88e8-4e8a-90ed-54948af1d7d1/file_metrics.txt)
[21](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/86378af4-2c8c-4b4d-ada5-ae95126c0adc/feature_flags.txt)
[22](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/945a5102-1c65-496a-b664-060b6b586d61/event_types.txt)
[23](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/de2e7bbb-00af-441a-86d8-d441965a882e/env_refs.txt)
[24](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/6e2debb2-3d74-45fa-9233-93165b2a20df/entrypoints.txt)
[25](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/6f32b5d4-f3ad-441c-93f9-3f21a59172df/deployment_manifest.txt)
[26](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/de63ca69-9799-4a01-a624-51a03ee2ea0e/dependencies.txt)
[27](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/8dea185c-eb6e-480f-950b-a0ad526edabf/decorator_catalog.txt)
[28](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_4ccbe197-b702-480c-80cd-8ccb54e7328a/64861c09-1778-447b-ba25-cd4838ab6086/config_files.txt)