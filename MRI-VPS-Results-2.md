###############################################################################
# PART A: SYSTEM-LEVEL DIAGNOSTICS
###############################################################################

echo
echo "A1) SYSTEM IDENTITY"
echo "-------------------"
hostname
whoami
ip addr show | grep 'inet ' | grep -v '127.0.0.1'
uname -a

echo
echo "A2) ALL LISTENING PORTS (TOP 50)"
echo "--------------------------------"
sudo ss -tlnp 2>/dev/null | head -50 || true

echo
echo "A3) FIREWALL STATUS (UFW + CLOUD-FIREWALL HINT)"
echo "----------------------------------------------"
sudo ufw status numbered 2>/dev/null || echo "UFW not active or not installed"
echo
echo "If ports look blocked externally, check cloud firewall rules (TCP 22, 80, 443, 9001, 7474, 7687, 5432, 6379, 9090, 3000, 16686 as needed)."

echo
echo "A4) DISK SPACE (KEY PATHS)"
echo "--------------------------"
df -h / /opt /var /tmp 2>/dev/null || true

echo
echo "A5) MEMORY (RAM)"
echo "----------------"
free -h

echo
echo "A6) SYSTEM LOAD"
echo "---------------"
uptime

echo "===== END OF L9 VPS MRI ====="t Executor required for new Slack routing', set L9_ENABLE_LEGACY_SLACK_ROUTER=true as workaround" observability).")"yload)"ad)"semantic search no

===== L9 VPS MRI – UPDATED FULL DIAGNOSTIC =====
Sun Jan 18 05:13:19 PM UTC 2026


A1) SYSTEM IDENTITY
-------------------
L9
admin
    inet 157.180.73.53/32 metric 100 scope global dynamic eth0
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
    inet 172.18.0.1/16 brd 172.18.255.255 scope global br-1e6017fa3bc4
Linux L9 6.8.0-90-generic #91-Ubuntu SMP PREEMPT_DYNAMIC Tue Nov 18 14:14:30 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux

A2) ALL LISTENING PORTS (TOP 50)
--------------------------------
[sudo] password for admin: 
Sorry, try again.
[sudo] password for admin: 
State  Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess                                   
LISTEN 0      128          0.0.0.0:22         0.0.0.0:*    users:(("sshd",pid=1045,fd=3))           
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=2492,fd=7))   
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=2456,fd=7))   
LISTEN 0      4096         0.0.0.0:631        0.0.0.0:*    users:(("cupsd",pid=1837,fd=9))          
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=2517,fd=7))   
LISTEN 0      4096   127.0.0.53%lo:53         0.0.0.0:*    users:(("systemd-resolve",pid=738,fd=15))
LISTEN 0      2048       127.0.0.1:8000       0.0.0.0:*    users:(("python",pid=2848,fd=13))        
LISTEN 0      4096       127.0.0.1:2019       0.0.0.0:*    users:(("caddy",pid=961,fd=3))           
LISTEN 0      4096       127.0.0.1:14268      0.0.0.0:*    users:(("docker-proxy",pid=2368,fd=7))   
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=2435,fd=7))   
LISTEN 0      4096       127.0.0.1:16686      0.0.0.0:*    users:(("docker-proxy",pid=2385,fd=7))   
LISTEN 0      4096      127.0.0.54:53         0.0.0.0:*    users:(("systemd-resolve",pid=738,fd=17))
LISTEN 0      4096       127.0.0.1:9002       0.0.0.0:*    users:(("docker-proxy",pid=2550,fd=7))   
LISTEN 0      4096       127.0.0.1:3000       0.0.0.0:*    users:(("docker-proxy",pid=2414,fd=7))   
LISTEN 0      4096       127.0.0.1:9090       0.0.0.0:*    users:(("docker-proxy",pid=2271,fd=7))   
LISTEN 0      4096               *:80               *:*    users:(("caddy",pid=961,fd=7))           
LISTEN 0      128             [::]:22            [::]:*    users:(("sshd",pid=1045,fd=4))           
LISTEN 0      4096               *:443              *:*    users:(("caddy",pid=961,fd=8))           
LISTEN 0      4096            [::]:631           [::]:*    users:(("cupsd",pid=1837,fd=10))         
LISTEN 0      4096               *:9001             *:*    users:(("caddy",pid=961,fd=10))          

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
/dev/sda1        38G   29G  7.3G  80% /
/dev/sda1        38G   29G  7.3G  80% /
/dev/sda1        38G   29G  7.3G  80% /
/dev/sda1        38G   29G  7.3G  80% /

A5) MEMORY (RAM)
----------------
               total        used        free      shared  buff/cache   available
Mem:           3.7Gi       1.3Gi       1.3Gi        19Mi       1.4Gi       2.4Gi
Swap:             0B          0B          0B

A6) SYSTEM LOAD
---------------
 17:13:30 up 12 min,  1 user,  load average: 0.11, 0.12, 0.13

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
NAME            IMAGE                           COMMAND                  SERVICE         CREATED      STATUS                    PORTS
l9-grafana      grafana/grafana:10.2.0          "/run.sh"                grafana         3 days ago   Up 12 minutes (healthy)   127.0.0.1:3000->3000/tcp
l9-jaeger       jaegertracing/all-in-one:1.52   "/go/bin/all-in-one-…"   jaeger          3 days ago   Up 12 minutes (healthy)   4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-mcp-memory   l9-l9-mcp-memory                "uvicorn mcp_memory.…"   l9-mcp-memory   3 days ago   Up 12 minutes (healthy)   127.0.0.1:9002->9002/tcp
l9-neo4j        neo4j:5-community               "tini -g -- /startup…"   neo4j           3 days ago   Up 12 minutes (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-postgres     pgvector/pgvector:pg16          "docker-entrypoint.s…"   l9-postgres     3 days ago   Up 12 minutes (healthy)   127.0.0.1:5432->5432/tcp
l9-prometheus   prom/prometheus:v2.48.0         "/bin/prometheus --c…"   prometheus      3 days ago   Up 12 minutes (healthy)   127.0.0.1:9090->9090/tcp
l9-redis        redis:7-alpine                  "docker-entrypoint.s…"   redis           3 days ago   Up 12 minutes (healthy)   127.0.0.1:6379->6379/tcp

C3) CONTAINER LOGS (l9-api last 80 lines)
-----------------------------------------

C4) DOCKER NETWORK + PORTS OF INTEREST
--------------------------------------
docker0 / bridge networks:
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0

Explicit port checks (8000, 9001, 5432, 7474, 7687, 6379, 9090, 3000, 16686):
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=2492,fd=7))   
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=2456,fd=7))   
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=2517,fd=7))   
LISTEN 0      2048       127.0.0.1:8000       0.0.0.0:*    users:(("python",pid=2848,fd=13))        
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=2435,fd=7))   
LISTEN 0      4096       127.0.0.1:16686      0.0.0.0:*    users:(("docker-proxy",pid=2385,fd=7))   
LISTEN 0      4096       127.0.0.1:3000       0.0.0.0:*    users:(("docker-proxy",pid=2414,fd=7))   
LISTEN 0      4096       127.0.0.1:9090       0.0.0.0:*    users:(("docker-proxy",pid=2271,fd=7))   
LISTEN 0      4096               *:9001             *:*    users:(("caddy",pid=961,fd=10))          

C5) DOCKER IMAGES
-----------------
REPOSITORY                 TAG           SIZE
l9-l9-api                  latest        1.31GB
l9-l9-mcp-memory           latest        770MB
neo4j                      5-community   853MB
pgvector/pgvector          pg16          723MB
redis                      7-alpine      61.2MB
jaegertracing/all-in-one   1.52          109MB
prom/prometheus            v2.48.0       349MB
grafana/grafana            10.2.0        538MB

C6) DOCKER NETWORKS
-------------------
NETWORK ID     NAME            DRIVER    SCOPE
37cbcac2bfb1   bridge          bridge    local
7fd8092b1eee   host            host      local
1e6017fa3bc4   l9_l9-network   bridge    local
8e2e6b859253   none            null      local

C7) DOCKER CONTAINER ERRORS (RECENT)
------------------------------------
--- l9-api ---
No recent errors
--- l9-postgres ---
2026-01-14 21:27:35.374 UTC [10810] ERROR:  invalid input syntax for type json
2026-01-14 21:38:10.030 UTC [11843] ERROR:  invalid input syntax for type json
2026-01-14 21:42:11.448 UTC [12259] ERROR:  invalid input syntax for type json
2026-01-14 21:51:03.852 UTC [13144] ERROR:  invalid input syntax for type json
2026-01-14 21:57:09.647 UTC [13745] ERROR:  invalid input syntax for type json
--- redis ---
Error response from daemon: No such container: redis
No recent errors
--- neo4j ---
Error response from daemon: No such container: neo4j
No recent errors

D1) .env (SANITIZED KEYS ONLY)
------------------------------
DATABASE_URL=REDACTED
GRAFANA_PASSWORD=REDACTED
GRAFANA_PORT=REDACTED
GRAFANA_USER=REDACTED
L9_API_KEY=REDACTED
L9_ENABLE_LEGACY_SLACK_ROUTER=REDACTED
L9_EXECUTOR_API_KEY=REDACTED
L_SLACK_USER_ID=REDACTED
MCP_API_KEY_C=REDACTED
MCP_API_KEY_C=REDACTED
MCP_API_KEY_L=REDACTED
MCP_API_KEY_L=REDACTED
MCP_API_KEY=REDACTED
NEO4J_PASSWORD=REDACTED
NEO4J_URI=REDACTED
NEO4J_URL=REDACTED
NEO4J_USER=REDACTED
OPENAI_API_KEY=REDACTED
OPENAI_MODEL=REDACTED
PERPLEXITY_API_KEY=REDACTED
POSTGRES_DB=REDACTED
POSTGRES_PASSWORD=REDACTED
POSTGRES_USER=REDACTED
PROMETHEUS_PORT=REDACTED
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

D1b) SLACK ADAPTER VARS CHECK
-----------------------------
SLACK_APP_ENABLED:
SLACK_APP_ENABLED=true
SLACK_BOT_TOKEN:
SLACK_BOT_TOKEN=SET
SLACK_SIGNING_SECRET:
SLACK_SIGNING_SECRET=SET
L9_ENABLE_LEGACY_SLACK_ROUTER:
L9_ENABLE_LEGACY_SLACK_ROUTER=true

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
94:      NEO4J_URL: ${NEO4J_URL:-bolt://neo4j:7687}
95:      NEO4J_USER: ${NEO4J_USER:-neo4j}
302:  neo4j_data:
304:    name: l9-neo4j-data
305:  neo4j_logs:
307:    name: l9-neo4j-logs

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
    reverse_proxy /mcp/* 127.0.0.1:8000
    
    # Default to l9-api → port 8000
    reverse_proxy 127.0.0.1:8000
}

E1) L9 API HEALTH (DIRECT ON 8000)
----------------------------------
{"status":"healthy","service":"L9 Phase 2 Memory System","version":"0.3.0","database":"connected","memory_system":"operational"}
E2) L9 MEMORY ENDPOINTS
-----------------------
{"detail":"Unauthorized"}{"detail":"Unauthorized"}
E3) MCP / CADDY FRONT DOOR HEALTH (9001)
----------------------------------------
HTTP → expect 'Client sent an HTTP request to an HTTPS server' if TLS-only:
Client sent an HTTP request to an HTTPS server.

HTTPS → /health:
curl: (35) OpenSSL/3.0.13: error:0A000438:SSL routines::tlsv1 alert internal error
HTTPS /health on 9001 not responding (check Caddy and certs)

E4) DNS RESOLUTION + PUBLIC IP
------------------------------
Public IP:
157.180.73.53
DNS resolution for l9.quantumaipartners.com:
2a06:98c1:3120::3 l9.quantumaipartners.com
2a06:98c1:3121::3 l9.quantumaipartners.com

E5) PUBLIC HEALTH VIA DOMAIN (IF DNS CONFIGURED)
-----------------------------------------------
Public API health (443):
{"status":"healthy","service":"L9 Phase 2 Memory System","version":"0.3.0","database":"connected","memory_system":"operational"}Public world model state-version (443):
curl: (22) The requested URL returned error: 404
Public worldmodel state-version failed

E6) API ROUTES AVAILABLE (via OpenAPI)
--------------------------------------
/
/chat
/health
/memory/batch
/memory/compact
/memory/consolidation/run
/memory/facts
/memory/gc/run
/memory/gc/stats
/memory/health
/memory/hybrid/search
/memory/insights
/memory/lineage/{packet_id}
/memory/packet
/memory/packet/{packet_id}
/memory/reasoning/replay
/memory/saga/correlate-timeline
/memory/saga/enrich-entities
/memory/saga/fetch-and-enrich
/memory/semantic/search
/memory/stats
/memory/test
/memory/thread/{thread_id}
/slack/commands
/slack/events

F1) POSTGRES STATUS + DB LIST
-----------------------------
○ postgresql.service - PostgreSQL RDBMS
     Loaded: loaded (/usr/lib/systemd/system/postgresql.service; disabled; preset: enabled)
     Active: inactive (dead)
PostgreSQL systemd unit not found or inactive

Port 5432 listeners:
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=2456,fd=7))   

Database list (first 15):
Unable to list databases as postgres user

F2) NEO4J CONTAINER + PORTS
---------------------------
CONTAINER ID   IMAGE               STATUS                    PORTS
18f7d5684f9f   neo4j:5-community   Up 12 minutes (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp

Neo4j ports:
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=2492,fd=7))   
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=2517,fd=7))   

F3) NEO4J BOLT CONNECTIVITY (IF PASSWORD SET)
--------------------------------------------
Attempting Neo4j driver smoke test via python...
Neo4j Python driver test failed (driver not installed or auth error)

F4) REDIS STATUS (IF USED)
--------------------------
CONTAINER ID   IMAGE            STATUS                    PORTS
4c5d09fdf245   redis:7-alpine   Up 12 minutes (healthy)   127.0.0.1:6379->6379/tcp

LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=2435,fd=7))   

G1) MEMORY SUBSTRATE DETAILED
-----------------------------
Memory stats:
{"detail":"Unauthorized"}
Memory GC stats:
{"detail":"Unauthorized"}
Semantic search test (empty query):
{"detail":"Unauthorized"}
G2) SLACK ADAPTER STATUS
------------------------
Slack commands endpoint:
Internal Server ErrorSlack events endpoint:
Internal Server Error
H1) PROMETHEUS STATUS
---------------------
CONTAINER ID   IMAGE                     STATUS                    PORTS
b8e4d7cf9509   prom/prometheus:v2.48.0   Up 12 minutes (healthy)   127.0.0.1:9090->9090/tcp
Prometheus Server is Healthy.

H2) GRAFANA STATUS
------------------
CONTAINER ID   IMAGE                    STATUS                    PORTS
0e619ad97f39   grafana/grafana:10.2.0   Up 12 minutes (healthy)   127.0.0.1:3000->3000/tcp
{
  "commit": "895fbafb7a",
  "database": "ok",
  "version": "10.2.0"
}
H3) JAEGER STATUS
-----------------
CONTAINER ID   IMAGE                           STATUS                    PORTS
027456ea4a1a   jaegertracing/all-in-one:1.52   Up 12 minutes (healthy)   4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

H4) MCP MEMORY SERVER STATUS (OPTIONAL)
---------------------------------------
CONTAINER ID   IMAGE              STATUS                    PORTS
f56729f3aaa8   l9-l9-mcp-memory   Up 12 minutes (healthy)   127.0.0.1:9002->9002/tcp
{"status":"healthy","database":"connected","database_error":null,"mcp_version":"2025-03-26","index_type":"hnsw","compounding_enabled":true,"decay_enabled":true}
H5) PYTHON/UVICORN PROCESSES (OUTSIDE DOCKER)
---------------------------------------------
root        1087  0.0  0.5 109664 23040 ?        Ssl  17:00   0:00 /usr/bin/python3 /usr/share/unattended-upgrades/unattended-upgrade-shutdown --wait-for-signal
root        2181  0.3  1.9 379892 74780 ?        Ssl  17:01   0:02 /usr/local/bin/python3.12 /usr/local/bin/uvicorn mcp_memory.src.main:app --host 0.0.0.0 --port 9002
l9          2848  0.4  3.8 500900 150256 ?       Ssl  17:01   0:03 /opt/l9/venv/bin/python -m uvicorn api.server_memory:app --host 127.0.0.1 --port 8000

Python version:
Python 3.12.3

===== QUICK STATUS SUMMARY =====
--------------------------------
✓ Docker: Running
✓ Reverse Proxy: Caddy
✓ L9 API: Healthy
✓ PostgreSQL: Listening
✓ Redis: Listening
✓ Neo4j: Listening
✓ Public HTTPS: Accessible

===== MRI SUMMARY HINTS (READ OUTPUT ABOVE) =====
- If l9-api is unhealthy or degraded in docker compose ps, check /health payload and logs for failing optional backends (Neo4j, observability).
- If Postgres 5432 is not listening, memory system will be broken.
- If Neo4j container is up but NEO4J_* vars missing in .env, graph features are effectively OFF.
- If Caddy on 9001 responds with 'HTTP request to HTTPS server' over HTTP, that is expected (TLS only).
- If DNS for l9.quantumaipartners.com fails, public HTTPS access will fail; use IP or fix DNS.
- SLACK ADAPTER: Requires SLACK_APP_ENABLED=true, SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET in .env
- SLACK ROUTING: If using new routing, agent_executor must initialize successfully (check startup logs)
- If l9-api crashes with 'Agent Executor required for new Slack routing', set L9_ENABLE_LEGACY_SLACK_ROUTER=true as workaround

===== END OF L9 VPS MRI =====
admin@L9:/opt/l9$ cd /opt/l9                                                     # ensure repo root

echo "===== L9 VPS MRI v4 – Docker, Caddy 9001, Neo4j‑Optional ====="
date -u +"%a %b %d %I:%M:%S %p UTC %Y"

###############################################################################
# PART A: SYSTEM IDENTITY
###############################################################################

echo
echo "A1) SYSTEM IDENTITY"
echo "-------------------"
hostname
whoami
ip addr show | grep 'inet ' | grep -v '127.0.0.1' | head -3
uname -r

echo
echo "A2) CRITICAL PORTS (Docker + Caddy)"
echo "-----------------------------------"
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
git status --short                                             # concise status
git diff --stat | head -10 || true                             # brief diff summary

###############################################################################
# PART C: DOCKER STACK
###############################################################################

echo
echo "C1) DOCKER COMPOSE PS (ALL CONTAINERS)"
echo "--------------------------------------"
docker compose ps                                              # container status

echo
echo "C2) L9-API LOGS (LAST 40 LINES)"
echo "--------------------------------"
docker compose logs l9-api --tail=40 || echo "No l9-api logs available"

###############################################################################
# PART D: CORE ENVS (SANITIZED FROM .env)
###############################################################################

echo
echo "===== END OF MRI v4 ====="orts reachable: see E2"######################## response>}"SSWORD|MCP_API_KEY_C|SLACK_BOT_TOKEN|SLACK_SIGNING_SECRET)=' .env \
===== L9 VPS MRI v4 – Docker, Caddy 9001, Neo4j‑Optional =====
Sun Jan 18 05:14:28 PM UTC 2026

A1) SYSTEM IDENTITY
-------------------
L9
admin
    inet 157.180.73.53/32 metric 100 scope global dynamic eth0
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
    inet 172.18.0.1/16 brd 172.18.255.255 scope global br-1e6017fa3bc4
6.8.0-90-generic

A2) CRITICAL PORTS (Docker + Caddy)
-----------------------------------
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=2492,fd=7))   
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=2456,fd=7))   
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=2517,fd=7))   
LISTEN 0      2048       127.0.0.1:8000       0.0.0.0:*    users:(("python",pid=2848,fd=13))        
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=2435,fd=7))   
LISTEN 0      4096               *:9001             *:*    users:(("caddy",pid=961,fd=10))          

A3) DISK SPACE
--------------
/dev/sda1        38G   29G  7.3G  80% /

B1) GIT STATE (/opt/l9)
-----------------------

C1) DOCKER COMPOSE PS (ALL CONTAINERS)
--------------------------------------
NAME            IMAGE                           COMMAND                  SERVICE         CREATED      STATUS                    PORTS
l9-grafana      grafana/grafana:10.2.0          "/run.sh"                grafana         3 days ago   Up 13 minutes (healthy)   127.0.0.1:3000->3000/tcp
l9-jaeger       jaegertracing/all-in-one:1.52   "/go/bin/all-in-one-…"   jaeger          3 days ago   Up 13 minutes (healthy)   4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-mcp-memory   l9-l9-mcp-memory                "uvicorn mcp_memory.…"   l9-mcp-memory   3 days ago   Up 13 minutes (healthy)   127.0.0.1:9002->9002/tcp
l9-neo4j        neo4j:5-community               "tini -g -- /startup…"   neo4j           3 days ago   Up 13 minutes (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-postgres     pgvector/pgvector:pg16          "docker-entrypoint.s…"   l9-postgres     3 days ago   Up 13 minutes (healthy)   127.0.0.1:5432->5432/tcp
l9-prometheus   prom/prometheus:v2.48.0         "/bin/prometheus --c…"   prometheus      3 days ago   Up 13 minutes (healthy)   127.0.0.1:9090->9090/tcp
l9-redis        redis:7-alpine                  "docker-entrypoint.s…"   redis           3 days ago   Up 13 minutes (healthy)   127.0.0.1:6379->6379/tcp

C2) L9-API LOGS (LAST 40 LINES)
--------------------------------

D1) CORE ENV VARS (sanitized)
-----------------------------
MEMORY_DSN=SET
DATABASE_URL=SET
OPENAI_API_KEY=SET
NEO4J_URI=SET
NEO4J_USER=SET
NEO4J_PASSWORD=SET
SLACK_SIGNING_SECRET=SET
SLACK_BOT_TOKEN=SET
MCP_API_KEY_C=SET
MCP_API_KEY_C=SET
NEO4J_URL=SET

E1) INTERNAL L9 API HEALTH (127.0.0.1:8000)
-------------------------------------------
❌ API health unexpected or empty: {"status":"healthy","service":"L9 Phase 2 Memory System","version":"0.3.0","database":"connected","memory_system":"operational"}

E2) BACKEND SERVICES
--------------------
Postgres (5432):
  ❌ Not ready (psql failed)
Redis (6379):
  ❌ Not responding
Neo4j (7687):
  ✅ TCP port open

E3) MCP MEMORY VIA CADDY (9001 /memory*)
----------------------------------------
ℹ️  MCP /memory/health response:
{"detail":"Unauthorized"}

F1) CADDY STATUS
----------------
active
✅ Caddy running

F2) PUBLIC HEALTH VIA CADDY 9001
--------------------------------
❌ Public API health unexpected or empty via 9001: {"status":"healthy","service":"L9 Phase 2 Memory System","version":"0.3.0","database":"connected","memory_system":"operational"}

===== DIAGNOSTIC SUMMARY =====
l9-grafana      grafana/grafana:10.2.0          "/run.sh"                grafana         3 days ago   Up 13 minutes (healthy)   127.0.0.1:3000->3000/tcp
l9-jaeger       jaegertracing/all-in-one:1.52   "/go/bin/all-in-one-…"   jaeger          3 days ago   Up 13 minutes (healthy)   4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-mcp-memory   l9-l9-mcp-memory                "uvicorn mcp_memory.…"   l9-mcp-memory   3 days ago   Up 13 minutes (healthy)   127.0.0.1:9002->9002/tcp
l9-neo4j        neo4j:5-community               "tini -g -- /startup…"   neo4j           3 days ago   Up 13 minutes (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-postgres     pgvector/pgvector:pg16          "docker-entrypoint.s…"   l9-postgres     3 days ago   Up 13 minutes (healthy)   127.0.0.1:5432->5432/tcp
l9-prometheus   prom/prometheus:v2.48.0         "/bin/prometheus --c…"   prometheus      3 days ago   Up 13 minutes (healthy)   127.0.0.1:9090->9090/tcp
l9-redis        redis:7-alpine                  "docker-entrypoint.s…"   redis           3 days ago   Up 13 minutes (healthy)   127.0.0.1:6379->6379/tcp

Key checks:
  - Internal API health: status ok? -> see E1
  - Caddy 9001 /health: status ok? -> see F2
  - Postgres/Redis/Neo4j ports reachable: see E2

===== END OF MRI v4 =====