# L9 VPS MRI Results

**Generated:** 2026-01-09 12:08:02 EST
**Deployment:** 9bfb180
**Health Status:** ok

---


===== L9 VPS MRI – UPDATED FULL DIAGNOSTIC =====
Fri Jan  9 05:08:00 PM UTC 2026


A1) SYSTEM IDENTITY
-------------------
L9
root
    inet 157.180.73.53/32 metric 100 scope global dynamic eth0
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
    inet 172.18.0.1/16 brd 172.18.255.255 scope global br-7a4fdc71f44b
Linux L9 6.8.0-88-generic #89-Ubuntu SMP PREEMPT_DYNAMIC Sat Oct 11 01:02:46 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux

A2) ALL LISTENING PORTS (TOP 50)
--------------------------------
State  Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess                                   
LISTEN 0      4096       127.0.0.1:3000       0.0.0.0:*    users:(("docker-proxy",pid=3124511,fd=7))
LISTEN 0      4096      127.0.0.54:53         0.0.0.0:*    users:(("systemd-resolve",pid=656,fd=17))
LISTEN 0      4096       127.0.0.1:9090       0.0.0.0:*    users:(("docker-proxy",pid=3123999,fd=7))
LISTEN 0      4096       127.0.0.1:16686      0.0.0.0:*    users:(("docker-proxy",pid=3123951,fd=7))
LISTEN 0      200       172.17.0.1:5432       0.0.0.0:*    users:(("postgres",pid=1366480,fd=7))    
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=3123837,fd=7))
LISTEN 0      4096       127.0.0.1:8000       0.0.0.0:*    users:(("docker-proxy",pid=1649135,fd=7))
LISTEN 0      4096       127.0.0.1:2019       0.0.0.0:*    users:(("caddy",pid=9230,fd=14))         
LISTEN 0      4096       127.0.0.1:14268      0.0.0.0:*    users:(("docker-proxy",pid=3123935,fd=7))
LISTEN 0      2048       127.0.0.1:8100       0.0.0.0:*    users:(("python",pid=362268,fd=13))      
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=995235,fd=7)) 
LISTEN 0      128          0.0.0.0:22         0.0.0.0:*    users:(("sshd",pid=954,fd=3))            
LISTEN 0      4096   127.0.0.53%lo:53         0.0.0.0:*    users:(("systemd-resolve",pid=656,fd=15))
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=995219,fd=7)) 
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=3123972,fd=7))
LISTEN 0      4096         0.0.0.0:631        0.0.0.0:*    users:(("cupsd",pid=1349,fd=9))          
LISTEN 0      4096               *:443              *:*    users:(("caddy",pid=9230,fd=16))         
LISTEN 0      128             [::]:22            [::]:*    users:(("sshd",pid=954,fd=4))            
LISTEN 0      4096               *:80               *:*    users:(("caddy",pid=9230,fd=15))         
LISTEN 0      4096               *:9001             *:*    users:(("caddy",pid=9230,fd=17))         
LISTEN 0      200            [::1]:5432          [::]:*    users:(("postgres",pid=1366480,fd=6))    
LISTEN 0      4096            [::]:631           [::]:*    users:(("cupsd",pid=1349,fd=10))         

A3) FIREWALL STATUS (UFW + CLOUD-FIREWALL HINT)
----------------------------------------------
Status: active

     To                         Action      From
     --                         ------      ----
[ 1] OpenSSH                    ALLOW IN    Anywhere                  
[ 2] 80/tcp                     ALLOW IN    Anywhere                  
[ 3] 22/tcp                     ALLOW IN    Anywhere                  
[ 4] 443/tcp                    ALLOW IN    Anywhere                  
[ 5] 9001/tcp                   ALLOW IN    Anywhere                  
[ 6] OpenSSH (v6)               ALLOW IN    Anywhere (v6)             
[ 7] 80/tcp (v6)                ALLOW IN    Anywhere (v6)             
[ 8] 22/tcp (v6)                ALLOW IN    Anywhere (v6)             
[ 9] 443/tcp (v6)               ALLOW IN    Anywhere (v6)             
[10] 9001/tcp (v6)              ALLOW IN    Anywhere (v6)             


If ports look blocked externally, check cloud firewall rules (TCP 22, 80, 443, 9001, 7474, 7687, 5432, 6379, 9090, 3000, 16686 as needed).

A4) DISK SPACE (KEY PATHS)
--------------------------
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        38G   29G  6.8G  82% /
/dev/sda1        38G   29G  6.8G  82% /
/dev/sda1        38G   29G  6.8G  82% /
/dev/sda1        38G   29G  6.8G  82% /

B1) GIT STATE (/opt/l9)
-----------------------

Git status:
On branch main
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean

Git diff (HEAD vs working tree, first 100 lines):

Untracked files (first 20):

C1) DOCKER / COMPOSE VERSIONS
-----------------------------
Docker version 29.1.1, build 0aedba5
Docker Compose version v2.40.3
active

C2) DOCKER COMPOSE PS
----------------------
NAME            IMAGE                           COMMAND                  SERVICE       CREATED          STATUS                    PORTS
l9-api          l9-l9-api                       "uvicorn api.server:…"   l9-api        30 seconds ago   Up 27 seconds (healthy)   127.0.0.1:8000->8000/tcp
l9-grafana      grafana/grafana:10.2.0          "/run.sh"                grafana       47 hours ago     Up 47 hours (healthy)     127.0.0.1:3000->3000/tcp
l9-jaeger       jaegertracing/all-in-one:1.52   "/go/bin/all-in-one-…"   jaeger        47 hours ago     Up 47 hours (healthy)     4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-neo4j        neo4j:5-community               "tini -g -- /startup…"   neo4j         11 hours ago     Up 11 hours (healthy)     127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-postgres     pgvector/pgvector:pg16          "docker-entrypoint.s…"   l9-postgres   47 hours ago     Up 47 hours (healthy)     127.0.0.1:5432->5432/tcp
l9-prometheus   prom/prometheus:v2.48.0         "/bin/prometheus --c…"   prometheus    47 hours ago     Up 47 hours (healthy)     127.0.0.1:9090->9090/tcp
l9-redis        redis:7-alpine                  "docker-entrypoint.s…"   redis         47 hours ago     Up 47 hours (healthy)     127.0.0.1:6379->6379/tcp

C3) CONTAINER LOGS (l9-api last 80 lines)
-----------------------------------------
l9-api  | 2026-01-09 17:07:41 [debug    ] Created relationship: Agent:L -[CAN_EXECUTE]-> Tool:world_model_restore
l9-api  | 2026-01-09 17:07:41 [info     ] Registered tool in graph: world_model_restore
l9-api  | 2026-01-09 17:07:41 [debug    ] Neo4j: registered world_model_restore
l9-api  | 2026-01-09 17:07:41 [info     ] Registered tool: world_model_restore (world_model_restore)
l9-api  | 2026-01-09 17:07:41 [info     ] ✓ Registered tool: world_model_restore (risk=high, schema=yes)
l9-api  | 2026-01-09 17:07:41 [debug    ] Created/updated entity: Tool:world_model_list_updates
l9-api  | 2026-01-09 17:07:41 [debug    ] Agent L ensured in graph
l9-api  | 2026-01-09 17:07:41 [debug    ] Created relationship: Agent:L -[CAN_EXECUTE]-> Tool:world_model_list_updates
l9-api  | 2026-01-09 17:07:41 [info     ] Registered tool in graph: world_model_list_updates
l9-api  | 2026-01-09 17:07:41 [debug    ] Neo4j: registered world_model_list_updates
l9-api  | 2026-01-09 17:07:41 [info     ] Registered tool: world_model_list_updates (world_model_list_updates)
l9-api  | 2026-01-09 17:07:41 [info     ] ✓ Registered tool: world_model_list_updates (risk=low, schema=yes)
l9-api  | 2026-01-09 17:07:41 [info     ] ✓✓ L-CTO tools registered: 71 total, 4 high-risk requiring approval, executors wired to base registry
l9-api  | 2026-01-09 17:07:41 [info     ] ✓ L-CTO tools registered: 71 tools available
l9-api  | 2026-01-09 17:07:41 [debug    ] Memory tool memory_search already registered, skipping
l9-api  | 2026-01-09 17:07:41 [debug    ] Memory tool memory_write already registered, skipping
l9-api  | 2026-01-09 17:07:41 [info     ] ✓ Memory tools registered: 2 tools
l9-api  | 2026-01-09 17:07:41 [info     ] ✓ Memory tools registered: 2 tools
l9-api  | 2026-01-09 17:07:41 [info     ] Memory metrics initialized
l9-api  | 2026-01-09 17:07:41 [info     ] ✓ Prometheus metrics initialized
l9-api  | 2026-01-09 17:07:41 [info     ] ╔════════════════════════════════════════╗
l9-api  | 2026-01-09 17:07:41 [info     ] ║  Stage 3: Wiring Enterprise Modules    ║
l9-api  | 2026-01-09 17:07:41 [info     ] ╚════════════════════════════════════════╝
l9-api  | 2026-01-09 17:07:41 [info     ] Tool audit service started
l9-api  | 2026-01-09 17:07:41 [info     ] ✓ ToolAuditService initialized (Postgres audit trail)
l9-api  | 2026-01-09 17:07:41 [info     ] Event-driven coordination initialized
l9-api  | 2026-01-09 17:07:41 [info     ] ✓ EventQueue initialized (async coordination)
l9-api  | 2026-01-09 17:07:41 [info     ] ✓ VirtualContextManager initialized (tiered memory)
l9-api  | 2026-01-09 17:07:41 [info     ] ✓ Evaluator initialized (LLM-as-judge)
l9-api  | 2026-01-09 17:07:41 [info     ] Stage 3 module wiring complete
l9-api  | 2026-01-09 17:07:41 [info     ] ╔════════════════════════════════════════╗
l9-api  | 2026-01-09 17:07:41 [info     ] ║  Stage 4: Memory Consolidation         ║
l9-api  | 2026-01-09 17:07:41 [info     ] ╚════════════════════════════════════════╝
l9-api  | 2026-01-09 17:07:41 [info     ] ✓ MemoryConsolidationService initialized (24h cleanup cycle)
l9-api  | 2026-01-09 17:07:41 [info     ] ╔════════════════════════════════════════╗
l9-api  | 2026-01-09 17:07:41 [info     ] ║  Stage 5: Graph-Backed Agent State     ║
l9-api  | 2026-01-09 17:07:41 [info     ] ╚════════════════════════════════════════╝
l9-api  | 2026-01-09 17:07:41 [info     ] ✓ AgentGraphLoader initialized
l9-api  | 2026-01-09 17:07:41 [info     ] ✓ GraphHydrator initialized
l9-api  | 2026-01-09 17:07:41 [info     ] ✓ AgentSelfModifyTool initialized
l9-api  | 2026-01-09 17:07:41 [info     ] Event queue processor started
l9-api  | 2026-01-09 17:07:41 [info     ] Memory consolidation scheduled every 4 hours
l9-api  | 2026-01-09 17:07:41 [info     ] ✓ L agent found in Neo4j graph
l9-api  | 2026-01-09 17:07:41 [info     ] Stage 5 (Graph-Backed Agent State) complete
l9-api  | 2026-01-09 17:07:41 [info     ] GraphToWorldModelSync started (interval=300s)
l9-api  | 2026-01-09 17:07:41 [info     ] ✅ UKG Phase 3: Graph-WM Sync started
l9-api  | 2026-01-09 17:07:41 [info     ] ToolPatternExtractor started (interval=6h)
l9-api  | 2026-01-09 17:07:41 [info     ] ✅ UKG Phase 4: Tool Pattern Extraction started (6h interval)
l9-api  | 2026-01-09 17:07:41 [info     ] Initializing Five-Tier Observability...
l9-api  | 2026-01-09 17:07:41 [info     ] ObservabilityService initialized extra={'sampling_rate': 0.1, 'exporters': ['console', 'substrate']}
l9-api  | 2026-01-09 17:07:41 [info     ] Instrumented agent executor (start_agent_task)
l9-api  | 2026-01-09 17:07:41 [info     ] Instrumented tool registry (dispatch_tool_call)
l9-api  | 2026-01-09 17:07:41 [info     ] Instrumented governance engine (evaluate)
l9-api  | 2026-01-09 17:07:41 [debug    ] Instrumented substrate.write_packet
l9-api  | 2026-01-09 17:07:41 [debug    ] Instrumented substrate.semantic_search
l9-api  | 2026-01-09 17:07:41 [debug    ] Instrumented substrate.get_packet
l9-api  | 2026-01-09 17:07:41 [debug    ] Instrumented substrate.query_packets
l9-api  | 2026-01-09 17:07:41 [info     ] Instrumented memory substrate (4 methods)
l9-api  | 2026-01-09 17:07:41 [info     ] ✅ Five-Tier Observability initialized instrumented={'executor': True, 'tool_registry': True, 'governance': True, 'substrate': True}
l9-api  | 2026-01-09 17:07:41 [info     ] Loading agent state from Neo4j agent_id=L
l9-api  | 2026-01-09 17:07:41 [info     ] Starting tool pattern extraction...
l9-api  | INFO:     Application startup complete.
l9-api  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
l9-api  | 2026-01-09 17:07:42 [info     ] Database connection pool initialized
l9-api  | 2026-01-09 17:07:42 [info     ] Database connection pool closed
l9-api  | 2026-01-09 17:07:42 [info     ] No audit data to analyze
l9-api  | INFO:     172.18.0.5:39224 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.5:39224 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | Received notification from DBMS server: <GqlStatusObject gql_status='01N51', status_description='warn: relationship type does not exist. The relationship type `COLLABORATES_WITH` does not exist. Verify that the spelling is correct.', position=<SummaryInputPosition line=8, column=24, offset=330>, raw_classification='UNRECOGNIZED', classification=<NotificationClassification.UNRECOGNIZED: 'UNRECOGNIZED'>, raw_severity='WARNING', severity=<NotificationSeverity.WARNING: 'WARNING'>, diagnostic_record={'_classification': 'UNRECOGNIZED', '_severity': 'WARNING', '_position': {'offset': 330, 'line': 8, 'column': 24}, 'OPERATION': '', 'OPERATION_CODE': '0', 'CURRENT_SCHEMA': '/'}> for query: '
MATCH (a:Agent {agent_id: $agent_id})
OPTIONAL MATCH (a)-[r1:HAS_RESPONSIBILITY]->(resp:Responsibility)
OPTIONAL MATCH (a)-[r2:HAS_DIRECTIVE]->(dir:Directive)
OPTIONAL MATCH (a)-[r3:HAS_SOP]->(sop:SOP)
OPTIONAL MATCH (a)-[r4:CAN_EXECUTE]->(tool:Tool)
OPTIONAL MATCH (a)-[r5:REPORTS_TO]->(supervisor:Agent)
OPTIONAL MATCH (a)-[r6:COLLABORATES_WITH]->(peer:Agent)
RETURN a,
       collect(DISTINCT resp) as responsibilities,
       collect(DISTINCT dir) as directives,
       collect(DISTINCT sop) as sops,
       collect(DISTINCT tool) as tools,
       supervisor,
       collect(DISTINCT peer) as collaborators
'
l9-api  | 2026-01-09 17:07:42 [info     ] Loaded agent state from Neo4j  agent_id=L directives=0 responsibilities=0 sops=0 supervisor=None tools=0
l9-api  | 2026-01-09 17:07:42 [info     ] WorldModelService initialized
l9-api  | 2026-01-09 17:07:42 [info     ] World Model DB pool initialized
l9-api  | 2026-01-09 17:07:42 [debug    ] Upserted entity: agent:L
l9-api  | 2026-01-09 17:07:42 [info     ] Synced agent L to World Model  extra={'responsibilities': 0, 'directives': 0, 'tools': 0}
l9-api  | 2026-01-09 17:07:42 [info     ] TaskQueue: Redis backend active
l9-api  | INFO:     127.0.0.1:38548 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.1:47788 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.5:42050 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.5:42050 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | INFO:     127.0.0.1:59308 - "GET /health HTTP/1.1" 200 OK

C4) DOCKER NETWORK + PORTS OF INTEREST
--------------------------------------
docker0 / bridge networks:
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
    inet6 fe80::f414:77ff:fe38:57f9/64 scope link 

Explicit port checks (8000, 9001, 5432, 7474, 7687, 6379, 9090, 3000, 16686):
LISTEN 0      4096       127.0.0.1:3000       0.0.0.0:*    users:(("docker-proxy",pid=3124511,fd=7))
LISTEN 0      4096       127.0.0.1:9090       0.0.0.0:*    users:(("docker-proxy",pid=3123999,fd=7))
LISTEN 0      4096       127.0.0.1:16686      0.0.0.0:*    users:(("docker-proxy",pid=3123951,fd=7))
LISTEN 0      200       172.17.0.1:5432       0.0.0.0:*    users:(("postgres",pid=1366480,fd=7))    
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=3123837,fd=7))
LISTEN 0      4096       127.0.0.1:8000       0.0.0.0:*    users:(("docker-proxy",pid=1649135,fd=7))
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=995235,fd=7)) 
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=995219,fd=7)) 
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=3123972,fd=7))
LISTEN 0      4096               *:9001             *:*    users:(("caddy",pid=9230,fd=17))         
LISTEN 0      200            [::1]:5432          [::]:*    users:(("postgres",pid=1366480,fd=6))    

D1) .env (SANITIZED KEYS ONLY)
------------------------------
DATABASE_URL=REDACTED
L9_API_KEY=REDACTED
L9_ENABLE_LEGACY_SLACK_ROUTER=REDACTED
L9_EXECUTOR_API_KEY=REDACTED
L_SLACK_USER_ID=REDACTED
NEO4J_PASSWORD=REDACTED
NEO4J_URI=REDACTED
NEO4J_USER=REDACTED
OPENAI_API_KEY=REDACTED
PERPLEXITY_API_KEY=REDACTED
POSTGRES_DB=REDACTED
POSTGRES_PASSWORD=REDACTED
POSTGRES_USER=REDACTED
QDRANT_HOST=REDACTED
QDRANT_PORT=REDACTED
REDIS_HOST=REDACTED
REDIS_PORT=REDACTED
SLACK_APP_ENABLED=REDACTED
SLACK_APP_ID=REDACTED
SLACK_BOT_TOKEN=REDACTED
SLACK_BOT_USER_ID=REDACTED
SLACK_CLIENT_ID=REDACTED
SLACK_CLIENT_SECRET=REDACTED
SLACK_SIGNING_SECRET=REDACTED
SLACK_VERIFICATION_TOKEN=REDACTED

D2) NEO4J ENV VARS PRESENCE CHECK
---------------------------------
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=FVmgaD1diPcz41zRbYLLP0UzyGvAi4E

D3) docker-compose.yml (SERVICES + NEO4J SECTION)
------------------------------------------------
-- services (first 60 lines) --
services:
  # ===========================================================================
  # Redis (Task queues, rate limiting, caching)
  # ===========================================================================
  redis:
    image: redis:7-alpine
    container_name: l9-redis
    restart: unless-stopped
    ports:
      - "127.0.0.1:${REDIS_PORT:-6379}:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - l9-network

  # ===========================================================================
  # Neo4j (Knowledge graph, entity relationships, event timelines)
  # ===========================================================================
  neo4j:
    image: neo4j:5-community
    container_name: l9-neo4j
    restart: unless-stopped
    environment:
      NEO4J_AUTH: ${NEO4J_USER:-neo4j}/${NEO4J_PASSWORD:-YOUR_NEO4J_PASSWORD}
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_dbms_security_procedures_unrestricted: apoc.*
    ports:
      - "127.0.0.1:${NEO4J_HTTP_PORT:-7474}:7474" # Browser UI (localhost only)
      - "127.0.0.1:${NEO4J_BOLT_PORT:-7687}:7687" # Bolt protocol (localhost only)
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - l9-network

  # ===========================================================================
  # L9 Main API (FastAPI Application)
  # ===========================================================================
  l9-api:
    build:
      context: .
      dockerfile: runtime/Dockerfile
    container_name: l9-api
    restart: unless-stopped
    depends_on:
      redis:
        condition: service_healthy
      neo4j:

-- neo4j service block (if any) --
25:  neo4j:
26:    image: neo4j:5-community
27:    container_name: l9-neo4j
30:      NEO4J_AUTH: ${NEO4J_USER:-neo4j}/${NEO4J_PASSWORD:-YOUR_NEO4J_PASSWORD}
37:      - neo4j_data:/data
38:      - neo4j_logs:/logs
60:      neo4j:
92:      NEO4J_URL: ${NEO4J_URL:-bolt://neo4j:7687}
93:      NEO4J_USER: ${NEO4J_USER:-neo4j}
243:  neo4j_data:
245:    name: l9-neo4j-data
246:  neo4j_logs:
248:    name: l9-neo4j-logs

D4) CADDY CONFIG (TOP 80 LINES)
-------------------------------
# L9 Main API
l9.quantumaipartners.com {
    encode gzip

    # Core
    reverse_proxy /health 127.0.0.1:8000
    reverse_proxy /docs* 127.0.0.1:8000
    reverse_proxy /openapi.json 127.0.0.1:8000

    # L9 routes
    reverse_proxy /memory* 127.0.0.1:8000
    reverse_proxy /twilio* 127.0.0.1:8000
    reverse_proxy /waba* 127.0.0.1:8000
    reverse_proxy /slack/* 127.0.0.1:8000

    # Default
    reverse_proxy 127.0.0.1:8000
}

# Cursor MCP endpoint (IP:9001)
# Routes /mcp/* to MCP Memory Server (9002)
# Routes everything else to l9-api (8000)
157.180.73.53:9001 {
    encode gzip
    
    # MCP Memory Server routes → port 9002
    reverse_proxy /mcp/* 127.0.0.1:9001
    
    # Default to l9-api → port 8000
    reverse_proxy 127.0.0.1:8000
}

E1) L9 API HEALTH (DIRECT ON 8000)
----------------------------------
{"status":"ok","service":"l9-api","startup_ready":true}
E2) L9 API WORLD MODEL HEALTH
-----------------------------
{"detail":"Not Found"}{"detail":"Not Found"}
E3) MCP / CADDY FRONT DOOR HEALTH (9001)
----------------------------------------
HTTP → expect 'Client sent an HTTP request to an HTTPS server' if TLS-only:
Client sent an HTTP request to an HTTPS server.

HTTPS → /health:
curl: (35) OpenSSL/3.0.13: error:0A000438:SSL routines::tlsv1 alert internal error
HTTPS /health on 9001 not responding (check Caddy and certs)

E4) PUBLIC HEALTH VIA DOMAIN (IF DNS CONFIGURED)
-----------------------------------------------
Public API health (443):
{"status":"ok","service":"l9-api","startup_ready":true}Public world model state-version (443):
curl: (22) The requested URL returned error: 404
Public worldmodel state-version failed

F1) POSTGRES STATUS + DB LIST
-----------------------------
● postgresql.service - PostgreSQL RDBMS
     Loaded: loaded (/usr/lib/systemd/system/postgresql.service; disabled; preset: enabled)
     Active: active (exited) since Fri 2025-12-26 22:15:53 UTC; 1 week 6 days ago
   Main PID: 1366498 (code=exited, status=0/SUCCESS)
        CPU: 4ms

Dec 26 22:15:53 L9 systemd[1]: Starting postgresql.service - PostgreSQL RDBMS...
Dec 26 22:15:53 L9 systemd[1]: Finished postgresql.service - PostgreSQL RDBMS.

Port 5432 listeners:
LISTEN 0      200       172.17.0.1:5432       0.0.0.0:*    users:(("postgres",pid=1366480,fd=7))    
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=3123972,fd=7))
LISTEN 0      200            [::1]:5432          [::]:*    users:(("postgres",pid=1366480,fd=6))    

Database list (first 15):
                                                       List of databases
   Name    |  Owner   | Encoding | Locale Provider |   Collate   |    Ctype    | ICU Locale | ICU Rules |   Access privileges   
-----------+----------+----------+-----------------+-------------+-------------+------------+-----------+-----------------------
 l9_memory | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |            |           | 
 l9db      | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |            |           | =Tc/postgres         +
           |          |          |                 |             |             |            |           | postgres=CTc/postgres+
           |          |          |                 |             |             |            |           | l9_app=c/postgres
 postgres  | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |            |           | 
 template0 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |            |           | =c/postgres          +
           |          |          |                 |             |             |            |           | postgres=CTc/postgres
 template1 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |            |           | =c/postgres          +
           |          |          |                 |             |             |            |           | postgres=CTc/postgres
(5 rows)


F2) NEO4J CONTAINER + PORTS
---------------------------
CONTAINER ID   IMAGE               STATUS                  PORTS
f1f1a8ccf661   neo4j:5-community   Up 11 hours (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp

Neo4j ports:
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=995235,fd=7)) 
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=995219,fd=7)) 

F3) NEO4J BOLT CONNECTIVITY (IF PASSWORD SET)
--------------------------------------------
Attempting Neo4j driver smoke test via python...
Neo4j Python driver test failed (driver not installed or auth error)

F4) REDIS STATUS (IF USED)
--------------------------
CONTAINER ID   IMAGE            STATUS                  PORTS
fb06cdb1fdfc   redis:7-alpine   Up 47 hours (healthy)   127.0.0.1:6379->6379/tcp

LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=3123837,fd=7))

G1) MEMORY SUBSTRATE STATS
--------------------------
{"detail":"Unauthorized"}
Memory healthcheck:
{"detail":"Unauthorized"}
G2) WORLD MODEL SNAPSHOT
------------------------
World model health (via /healthneo4j if present):
{"detail":"Not Found"}World model entities (first page via API):
{"detail":"Not Found"}
H1) PROMETHEUS STATUS
---------------------
CONTAINER ID   IMAGE                     STATUS                  PORTS
daba748c3708   prom/prometheus:v2.48.0   Up 47 hours (healthy)   127.0.0.1:9090->9090/tcp
Prometheus Server is Healthy.

H2) GRAFANA STATUS
------------------
CONTAINER ID   IMAGE                    STATUS                  PORTS
5460f2f201be   grafana/grafana:10.2.0   Up 47 hours (healthy)   127.0.0.1:3000->3000/tcp
{
  "commit": "895fbafb7a",
  "database": "ok",
  "version": "10.2.0"
}
H3) JAEGER STATUS
-----------------
CONTAINER ID   IMAGE                           STATUS                  PORTS
ec9433cabe6a   jaegertracing/all-in-one:1.52   Up 47 hours (healthy)   4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

===== MRI SUMMARY HINTS (READ OUTPUT ABOVE) =====
- If l9-api is unhealthy or degraded in docker compose ps, check /health payload and logs for failing optional backends (Neo4j, observability).
- If Postgres 5432 is not listening, memory + world model will be broken.
- If Neo4j container is up but NEO4J_* vars missing in .env, graph features are effectively OFF.
- If Caddy on 9001 responds with 'HTTP request to HTTPS server' over HTTP, that is expected (TLS only).
- If DNS for l9.quantumaipartners.com fails, public HTTPS access will fail; use IP or fix DNS.

===== END OF L9 VPS MRI =====
