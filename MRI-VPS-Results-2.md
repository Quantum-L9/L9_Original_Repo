###############################################################################
# PART A: SYSTEM IDENTITY
###############################################################################

echo "A1) SYSTEM IDENTITY"
echo "-------------------"
hostname
whoami
ip addr show | grep 'inet ' | grep -v '127.0.0.1'
uname -a

echo
echo "A2) CRITICAL PORTS"
echo "------------------"
sudo ss -tlnp 2>/dev/null | grep -E '(:8000|:9001|:5432|:7474|:7687|:6379)' || echo "No critical ports listening"

echo
echo "A3) DISK SPACE"
echo "--------------"
df -h / | tail -1

###############################################################################
# PART B: GIT STATE
###############################################################################

echo
echo "B1) GIT STATE (/opt/l9)"
echo "-----------------------"
cd /opt/l9 2>/dev/null || { echo "/opt/l9 missing"; exit 1; }
git status --short  # Concise format
echo "===== END OF MRI v2 =====" for port conflicts"span init errors)"PENAI_API_KEY)"ep -c healthy || echo 0)/3 healthy"e for error details" ||
===== L9 VPS MRI v2 – AGENT EXECUTOR FOCUSED =====
Wed Jan 14 09:42:44 PM UTC 2026

A1) SYSTEM IDENTITY
-------------------
L9
admin
    inet 157.180.73.53/32 metric 100 scope global dynamic eth0
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
    inet 172.18.0.1/16 brd 172.18.255.255 scope global br-1e6017fa3bc4
Linux L9 6.8.0-88-generic #89-Ubuntu SMP PREEMPT_DYNAMIC Sat Oct 11 01:02:46 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux

A2) CRITICAL PORTS
------------------
[sudo] password for admin: 
LISTEN 0      200       172.17.0.1:5432       0.0.0.0:*    users:(("postgres",pid=1366480,fd=7))    
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=254331,fd=7)) 
LISTEN 0      4096       127.0.0.1:8000       0.0.0.0:*    users:(("docker-proxy",pid=387256,fd=7)) 
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=254300,fd=7)) 
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=254283,fd=7)) 
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=254257,fd=7)) 
LISTEN 0      4096               *:9001             *:*    users:(("caddy",pid=9230,fd=20))         
LISTEN 0      200            [::1]:5432          [::]:*    users:(("postgres",pid=1366480,fd=6))    

A3) DISK SPACE
--------------
/dev/sda1        38G   29G  7.0G  81% /

B1) GIT STATE (/opt/l9)
-----------------------

C1) DOCKER COMPOSE PS
---------------------
NAME            IMAGE                           COMMAND                  SERVICE         CREATED          STATUS                    PORTS
l9-api          l9-l9-api                       "uvicorn api.server:…"   l9-api          18 minutes ago   Up 43 seconds (healthy)   127.0.0.1:8000->8000/tcp
l9-grafana      grafana/grafana:10.2.0          "/run.sh"                grafana         2 hours ago      Up 2 hours (healthy)      127.0.0.1:3000->3000/tcp
l9-jaeger       jaegertracing/all-in-one:1.52   "/go/bin/all-in-one-…"   jaeger          2 hours ago      Up 2 hours (healthy)      4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-mcp-memory   l9-l9-mcp-memory                "uvicorn mcp_memory.…"   l9-mcp-memory   47 minutes ago   Up 47 minutes (healthy)   127.0.0.1:9002->9002/tcp
l9-neo4j        neo4j:5-community               "tini -g -- /startup…"   neo4j           2 hours ago      Up 2 hours (healthy)      127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-postgres     pgvector/pgvector:pg16          "docker-entrypoint.s…"   l9-postgres     2 hours ago      Up 2 hours (healthy)      127.0.0.1:5432->5432/tcp
l9-prometheus   prom/prometheus:v2.48.0         "/bin/prometheus --c…"   prometheus      2 hours ago      Up 2 hours (healthy)      127.0.0.1:9090->9090/tcp
l9-redis        redis:7-alpine                  "docker-entrypoint.s…"   redis           2 hours ago      Up 2 hours (healthy)      127.0.0.1:6379->6379/tcp

C2) L9-API LOGS (AGENT EXECUTOR FOCUS)
--------------------------------------
=== Last 30 lines ===
l9-api  | 2026-01-14 21:42:09 [warning  ] pyautogui not available - desktop screenshots disabled
l9-api  | 2026-01-14 21:42:09 [info     ] Email Agent router registered at /email/{account}/*
l9-api  | 2026-01-14 21:42:09 [info     ] PacketEnvelope upgrades router registered at /api/v1/upgrades
l9-api  | INFO:     Started server process [1]
l9-api  | INFO:     Waiting for application startup.
l9-api  | {"event": "Patterns file not found: /app/seed/architectural_patterns.yaml", "logger": "world_model.seed_loader", "level": "warning", "timestamp": "2026-01-14T21:42:10.431801Z"}
l9-api  | {"event": "Heuristics file not found: /app/seed/coding_heuristics.yaml", "logger": "world_model.seed_loader", "level": "warning", "timestamp": "2026-01-14T21:42:10.432022Z"}
l9-api  | {"event": "Seed loading failed: 'NoneType' object is not iterable", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-01-14T21:42:10.432158Z"}
l9-api  | {"event": "Failed to bootstrap governance schema: No module named 'scripts.bootstrap_neo4j_schema'", "logger": "api.server", "level": "warning", "timestamp": "2026-01-14T21:42:10.441349Z"}
l9-api  | {"event": "Tool registry not initialized, will create during bootstrap", "logger": "core.agents.bootstrap.phase_0_validate", "level": "warning", "timestamp": "2026-01-14T21:42:11.213399Z"}
l9-api  | {"agent_id": "l-cto", "tried_path": "private/agents/identity/l-cto_identity.yaml", "event": "Identity YAML not found, using defaults", "logger": "core.agents.bootstrap.phase_4_load_identity", "level": "warning", "timestamp": "2026-01-14T21:42:11.375481Z"}
l9-api  | {"packet_id": "6b8f0e84-c579-4eb3-ac72-d44d937f74a1", "packet_type": "memory_write", "marker_count": 1, "markers": [], "event": "injection_markers_detected", "logger": "memory.audit_utils", "level": "warning", "timestamp": "2026-01-14T21:42:11.431695Z"}
l9-api  | {"event": "RLS scope not provided for write_packet - queries may be restricted", "logger": "memory.substrate_service", "level": "warning", "timestamp": "2026-01-14T21:42:11.432298Z"}
l9-api  | {"event": "store_insights_node: Failed to store: invalid input syntax for type json\nDETAIL:  Token \"audit\" is invalid.", "logger": "memory.substrate_dag", "level": "error", "timestamp": "2026-01-14T21:42:11.449670Z"}
l9-api  | {"event": "STARTUP VALIDATION: SessionStartup result not available", "logger": "api.server", "level": "warning", "timestamp": "2026-01-14T21:42:11.543088Z"}
l9-api  | INFO:     Application startup complete.
l9-api  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
l9-api  | Received notification from DBMS server: <GqlStatusObject gql_status='01N51', status_description='warn: relationship type does not exist. The relationship type `COLLABORATES_WITH` does not exist. Verify that the spelling is correct.', position=<SummaryInputPosition line=8, column=24, offset=330>, raw_classification='UNRECOGNIZED', classification=<NotificationClassification.UNRECOGNIZED: 'UNRECOGNIZED'>, raw_severity='WARNING', severity=<NotificationSeverity.WARNING: 'WARNING'>, diagnostic_record={'_classification': 'UNRECOGNIZED', '_severity': 'WARNING', '_position': {'offset': 330, 'line': 8, 'column': 24}, 'OPERATION': '', 'OPERATION_CODE': '0', 'CURRENT_SCHEMA': '/'}> for query: '\nMATCH (a:Agent {agent_id: $agent_id})\nOPTIONAL MATCH (a)-[r1:HAS_RESPONSIBILITY]->(resp:Responsibility)\nOPTIONAL MATCH (a)-[r2:HAS_DIRECTIVE]->(dir:Directive)\nOPTIONAL MATCH (a)-[r3:HAS_SOP]->(sop:SOP)\nOPTIONAL MATCH (a)-[r4:CAN_EXECUTE]->(tool:Tool)\nOPTIONAL MATCH (a)-[r5:REPORTS_TO]->(supervisor:Agent)\nOPTIONAL MATCH (a)-[r6:COLLABORATES_WITH]->(peer:Agent)\nRETURN a,\n       collect(DISTINCT resp) as responsibilities,\n       collect(DISTINCT dir) as directives,\n       collect(DISTINCT sop) as sops,\n       collect(DISTINCT tool) as tools,\n       supervisor,\n       collect(DISTINCT peer) as collaborators\n'
l9-api  | INFO:     172.18.0.6:50216 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.6:50216 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | INFO:     127.0.0.1:55930 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.6:35980 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.6:35980 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | INFO:     127.0.0.1:51028 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.6:41746 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.6:41746 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | INFO:     127.0.0.1:46864 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.6:40880 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.6:40880 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | INFO:     127.0.0.1:60700 - "GET /health HTTP/1.1" 200 OK

=== Agent Executor errors only ===
No Agent Executor errors in logs

=== Lifespan startup sequence ===
l9-api  | 2026-01-14 21:24:49 [info     ] WebSocketOrchestrator initialized
l9-api  | INFO:     Waiting for application startup.
l9-api  | {"event": "Tool registry not initialized, will create during bootstrap", "logger": "core.agents.bootstrap.phase_0_validate", "level": "warning", "timestamp": "2026-01-14T21:24:52.817327Z"}
l9-api  | INFO:     Application startup complete.
l9-api  | 2026-01-14 21:25:48 [info     ] WebSocketOrchestrator initialized
l9-api  | INFO:     Waiting for application startup.
l9-api  | {"event": "Tool registry not initialized, will create during bootstrap", "logger": "core.agents.bootstrap.phase_0_validate", "level": "warning", "timestamp": "2026-01-14T21:25:51.627783Z"}
l9-api  | INFO:     Application startup complete.
l9-api  | 2026-01-14 21:27:32 [info     ] WebSocketOrchestrator initialized
l9-api  | INFO:     Waiting for application startup.
l9-api  | {"event": "Tool registry not initialized, will create during bootstrap", "logger": "core.agents.bootstrap.phase_0_validate", "level": "warning", "timestamp": "2026-01-14T21:27:35.136991Z"}
l9-api  | INFO:     Application startup complete.
l9-api  | 2026-01-14 21:38:06 [info     ] WebSocketOrchestrator initialized
l9-api  | INFO:     Waiting for application startup.
l9-api  | {"event": "Tool registry not initialized, will create during bootstrap", "logger": "core.agents.bootstrap.phase_0_validate", "level": "warning", "timestamp": "2026-01-14T21:38:09.751440Z"}
l9-api  | INFO:     Application startup complete.
l9-api  | 2026-01-14 21:42:08 [info     ] WebSocketOrchestrator initialized
l9-api  | INFO:     Waiting for application startup.
l9-api  | {"event": "Tool registry not initialized, will create during bootstrap", "logger": "core.agents.bootstrap.phase_0_validate", "level": "warning", "timestamp": "2026-01-14T21:42:11.213399Z"}
l9-api  | INFO:     Application startup complete.

D1) AGENT EXECUTOR ENV VARS
---------------------------
L9_EXECUTOR_API_KEY:
L9_EXECUTOR_API_KEY=SET
OPENAI_API_KEY:
OPENAI_API_KEY=SET
OPENAI_MODEL:
OPENAI_MODEL=gpt-4o
L9_ENABLE_LEGACY_SLACK_ROUTER:
L9_ENABLE_LEGACY_SLACK_ROUTER=true
SLACK_BOT_TOKEN:
SLACK_BOT_TOKEN=SET
SLACK_SIGNING_SECRET:
SLACK_SIGNING_SECRET=SET

D2) POSTGRES CONNECTION STRING
-------------------------------
DATABASE_URL=postgresql://USER:PASS@l9-postgres:5432/l9_memory

E1) L9 API HEALTH
-----------------
{"status":"ok","service":"l9-api","startup_ready":true}
E2) BACKEND SERVICES
--------------------
Postgres (5432):
LISTEN 0      200       172.17.0.1:5432       0.0.0.0:*    users:(("postgres",pid=1366480,fd=7))    
Redis (6379):
PONG
Neo4j (7687):
-bash: NEO4J_PASSWORD: unbound variable
  ❌ Not connected

F1) CADDY STATUS
----------------
active
✅ Caddy running

F2) PUBLIC HEALTH
-----------------
❌ Public API down

G1) AGENT EXECUTOR DIAGNOSIS
----------------------------
Step 1: Check if l9-api container is running
  ✅ Container is UP

Step 2: Check for Agent Executor in environment
L9_EXECUTOR_API_KEY=SET
OPENAI_MODEL=SET
OPENAI_API_KEY=SET

Step 3: Port 8000 conflict check
  ✅ No port 8000 conflicts (only Docker)

Step 4: Recent container restarts
  ✅ No restart loop

===== DIAGNOSTIC SUMMARY =====
✅ Git clean, no divergence from origin/main
no such service: l9-redis
✅ Postgres/Redis/Neo4j: 0
0/3 healthy
❓ l9-api status: Up 44 seconds (healthy)

🔍 AGENT EXECUTOR TROUBLESHOOTING:
   1. Check PART D1 for missing env vars (L9_EXECUTOR_API_KEY, OPENAI_API_KEY)
   2. Check PART C2 for Python traceback (lifespan init errors)
   3. Check PART G1 Step 3 for port conflicts

===== END OF MRI v2 =====