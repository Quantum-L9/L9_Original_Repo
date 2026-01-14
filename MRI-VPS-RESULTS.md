###############################################################################
# PART J: SUMMARY HINTS
###############################################################################

echo
echo "===== MRI SUMMARY HINTS (READ OUTPUT ABOVE) ====="
echo "- If l9-api is unhealthy or degraded in docker compose ps, check /health payload and lo✓ L9 API: Healthy
ib-mac@Mac ~ % 
ib-mac@Mac ~ % # PostgreSQL
zsh: command not found: #
ib-mac@Mac ~ % if sudo ss -tlnp 2>/dev/null | grep -q ":5432 "; then
then>     echo "✓ PostgreSQL: Listening"
then> else
else>     echo "⚠ PostgreSQL: Not detected on 5432"
else> fi
Password:
Sorry, try again.
Password:
Sorry, try again.
Password:
ib-mac@Mac ~ % ssh l9
Welcome to Ubuntu 24.04.3 LTS (GNU/Linux 6.8.0-88-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/pro

 System information as of Wed Jan 14 08:12:07 PM UTC 2026

  System load:  0.03               Processes:             187
  Usage of /:   71.2% of 37.23GB   Users logged in:       1
  Memory usage: 43%                IPv4 address for eth0: 157.180.73.53
  Swap usage:   0%

 * Strictly confined Kubernetes makes edge and IoT secure. Learn how MicroK8s
   just raised the bar for easy, resilient and secure K8s cluster deployment.

   https://ubuntu.com/engage/secure-kubernetes-at-the-edge

Expanded Security Maintenance for Applications is not enabled.

46 updates can be applied immediately.
2 of these updates are standard security updates.
To see these additional updates run: apt list --upgradable

13 additional security updates can be applied with ESM Apps.
Learn more about enabling ESM Apps service at https://ubuntu.com/esm


*** System restart required ***
Last login: Wed Jan 14 19:57:23 2026 from 190.108.207.98
admin@L9:~$ #!/usr/bin/env bash
# L9 VPS CONSOLIDATED MRI (UPDATED 2026-01-14)
# Host assumptions:
# - Code: /opt/l9
# - Docker Compose: /opt/l9/docker-compose.yml
# - Services: l9-api, l9-postgres, redis, neo4j, prometheus, grafana, jaeger
# - Optional: l9-mcp-memory (port 9002)
# - Caddy: systemd service, Caddyfile at /etc/caddy/Caddyfile
# - Slack Adapter: SLACK_APP_ENABLED, SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET

set -euo pipefail

echo
echo "===== L9 VPS MRI – UPDATED FULL DIAGNOSTIC ====="
date
echo

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
echo "===== END OF L9 VPS MRI ====="t Executor required for new Slack routing', set L9_ENABLE_LEGACY_SLACK_ROUTER=true as

===== L9 VPS MRI – UPDATED FULL DIAGNOSTIC =====
Wed Jan 14 08:12:25 PM UTC 2026


A1) SYSTEM IDENTITY
-------------------
L9
admin
    inet 157.180.73.53/32 metric 100 scope global dynamic eth0
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
    inet 172.18.0.1/16 brd 172.18.255.255 scope global br-1e6017fa3bc4
Linux L9 6.8.0-88-generic #89-Ubuntu SMP PREEMPT_DYNAMIC Sat Oct 11 01:02:46 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux

A2) ALL LISTENING PORTS (TOP 50)
--------------------------------
[sudo] password for admin: 
State  Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess                                   
LISTEN 0      4096       127.0.0.1:3000       0.0.0.0:*    users:(("docker-proxy",pid=263681,fd=7)) 
LISTEN 0      4096      127.0.0.54:53         0.0.0.0:*    users:(("systemd-resolve",pid=656,fd=17))
LISTEN 0      4096       127.0.0.1:9090       0.0.0.0:*    users:(("docker-proxy",pid=263292,fd=7)) 
LISTEN 0      4096       127.0.0.1:16686      0.0.0.0:*    users:(("docker-proxy",pid=263270,fd=7)) 
LISTEN 0      200       172.17.0.1:5432       0.0.0.0:*    users:(("postgres",pid=1366480,fd=7))    
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=254331,fd=7)) 
LISTEN 0      2048       127.0.0.1:8000       0.0.0.0:*    users:(("python",pid=259745,fd=13))      
LISTEN 0      4096       127.0.0.1:2019       0.0.0.0:*    users:(("caddy",pid=9230,fd=15))         
LISTEN 0      4096       127.0.0.1:14268      0.0.0.0:*    users:(("docker-proxy",pid=263254,fd=7)) 
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=254300,fd=7)) 
LISTEN 0      128          0.0.0.0:22         0.0.0.0:*    users:(("sshd",pid=954,fd=3))            
LISTEN 0      128        127.0.0.1:22222      0.0.0.0:*    users:(("sshd",pid=164710,fd=7))         
LISTEN 0      4096   127.0.0.53%lo:53         0.0.0.0:*    users:(("systemd-resolve",pid=656,fd=15))
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=254283,fd=7)) 
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=254257,fd=7)) 
LISTEN 0      4096         0.0.0.0:631        0.0.0.0:*    users:(("cupsd",pid=1349,fd=9))          
LISTEN 0      4096               *:443              *:*    users:(("caddy",pid=9230,fd=19))         
LISTEN 0      128            [::1]:22222         [::]:*    users:(("sshd",pid=164710,fd=5))         
LISTEN 0      128             [::]:22            [::]:*    users:(("sshd",pid=954,fd=4))            
LISTEN 0      4096               *:80               *:*    users:(("caddy",pid=9230,fd=10))         
LISTEN 0      4096               *:9001             *:*    users:(("caddy",pid=9230,fd=20))         
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
/dev/sda1        38G   27G  9.2G  75% /
/dev/sda1        38G   27G  9.2G  75% /
/dev/sda1        38G   27G  9.2G  75% /
/dev/sda1        38G   27G  9.2G  75% /

A5) MEMORY (RAM)
----------------
               total        used        free      shared  buff/cache   available
Mem:           3.7Gi       1.5Gi       279Mi        41Mi       2.2Gi       2.2Gi
Swap:             0B          0B          0B

A6) SYSTEM LOAD
---------------
 20:12:28 up 30 days, 17:12,  9 users,  load average: 0.02, 0.10, 0.20

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
l9-grafana      grafana/grafana:10.2.0          "/run.sh"                grafana       23 minutes ago   Up 23 minutes (healthy)   127.0.0.1:3000->3000/tcp
l9-jaeger       jaegertracing/all-in-one:1.52   "/go/bin/all-in-one-…"   jaeger        23 minutes ago   Up 23 minutes (healthy)   4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-neo4j        neo4j:5-community               "tini -g -- /startup…"   neo4j         34 minutes ago   Up 34 minutes (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-postgres     pgvector/pgvector:pg16          "docker-entrypoint.s…"   l9-postgres   34 minutes ago   Up 34 minutes (healthy)   127.0.0.1:5432->5432/tcp
l9-prometheus   prom/prometheus:v2.48.0         "/bin/prometheus --c…"   prometheus    23 minutes ago   Up 23 minutes (healthy)   127.0.0.1:9090->9090/tcp
l9-redis        redis:7-alpine                  "docker-entrypoint.s…"   redis         34 minutes ago   Up 34 minutes (healthy)   127.0.0.1:6379->6379/tcp

C3) CONTAINER LOGS (l9-api last 80 lines)
-----------------------------------------

C4) DOCKER NETWORK + PORTS OF INTEREST
--------------------------------------
docker0 / bridge networks:
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
    inet6 fe80::f414:77ff:fe38:57f9/64 scope link 

Explicit port checks (8000, 9001, 5432, 7474, 7687, 6379, 9090, 3000, 16686):
LISTEN 0      4096       127.0.0.1:3000       0.0.0.0:*    users:(("docker-proxy",pid=263681,fd=7)) 
LISTEN 0      4096       127.0.0.1:9090       0.0.0.0:*    users:(("docker-proxy",pid=263292,fd=7)) 
LISTEN 0      4096       127.0.0.1:16686      0.0.0.0:*    users:(("docker-proxy",pid=263270,fd=7)) 
LISTEN 0      200       172.17.0.1:5432       0.0.0.0:*    users:(("postgres",pid=1366480,fd=7))    
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=254331,fd=7)) 
LISTEN 0      2048       127.0.0.1:8000       0.0.0.0:*    users:(("python",pid=259745,fd=13))      
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=254300,fd=7)) 
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=254283,fd=7)) 
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=254257,fd=7)) 
LISTEN 0      4096               *:9001             *:*    users:(("caddy",pid=9230,fd=20))         
LISTEN 0      200            [::1]:5432          [::]:*    users:(("postgres",pid=1366480,fd=6))    

C5) DOCKER IMAGES
-----------------
REPOSITORY                 TAG           SIZE
l9-l9-api                  latest        2.2GB
neo4j                      5-community   853MB
pgvector/pgvector          pg16          723MB
redis                      7-alpine      61.2MB
jaegertracing/all-in-one   1.52          109MB
prom/prometheus            v2.48.0       349MB
grafana/grafana            10.2.0        538MB

C6) DOCKER NETWORKS
-------------------
NETWORK ID     NAME            DRIVER    SCOPE
028436097e20   bridge          bridge    local
7fd8092b1eee   host            host      local
1e6017fa3bc4   l9_l9-network   bridge    local
8e2e6b859253   none            null      local

C7) DOCKER CONTAINER ERRORS (RECENT)
------------------------------------
--- l9-api ---
No recent errors
--- l9-postgres ---
No recent errors
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
L9_ENABLE_LEGACY_SLACK_ROUTER=false
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
294:  neo4j_data:
296:    name: l9-neo4j-data
297:  neo4j_logs:
299:    name: l9-neo4j-logs

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
● postgresql.service - PostgreSQL RDBMS
     Loaded: loaded (/usr/lib/systemd/system/postgresql.service; disabled; preset: enabled)
     Active: active (exited) since Fri 2025-12-26 22:15:53 UTC; 2 weeks 4 days ago
   Main PID: 1366498 (code=exited, status=0/SUCCESS)
        CPU: 4ms

Notice: journal has been rotated since unit was started, output may be incomplete.

Port 5432 listeners:
LISTEN 0      200       172.17.0.1:5432       0.0.0.0:*    users:(("postgres",pid=1366480,fd=7))    
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=254257,fd=7)) 
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
CONTAINER ID   IMAGE               STATUS                    PORTS
18f7d5684f9f   neo4j:5-community   Up 34 minutes (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp

Neo4j ports:
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=254300,fd=7)) 
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=254283,fd=7)) 

F3) NEO4J BOLT CONNECTIVITY (IF PASSWORD SET)
--------------------------------------------
Attempting Neo4j driver smoke test via python...
Neo4j Python driver test failed (driver not installed or auth error)

F4) REDIS STATUS (IF USED)
--------------------------
CONTAINER ID   IMAGE            STATUS                    PORTS
4c5d09fdf245   redis:7-alpine   Up 34 minutes (healthy)   127.0.0.1:6379->6379/tcp

LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=254331,fd=7)) 

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
b8e4d7cf9509   prom/prometheus:v2.48.0   Up 23 minutes (healthy)   127.0.0.1:9090->9090/tcp
Prometheus Server is Healthy.

H2) GRAFANA STATUS
------------------
CONTAINER ID   IMAGE                    STATUS                    PORTS
0e619ad97f39   grafana/grafana:10.2.0   Up 23 minutes (healthy)   127.0.0.1:3000->3000/tcp
{
  "commit": "895fbafb7a",
  "database": "ok",
  "version": "10.2.0"
}
H3) JAEGER STATUS
-----------------
CONTAINER ID   IMAGE                           STATUS                    PORTS
027456ea4a1a   jaegertracing/all-in-one:1.52   Up 23 minutes (healthy)   4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

H4) MCP MEMORY SERVER STATUS (OPTIONAL)
---------------------------------------
CONTAINER ID   IMAGE     STATUS    PORTS
MCP Memory server not responding on 9002 (may not be deployed)

H5) PYTHON/UVICORN PROCESSES (OUTSIDE DOCKER)
---------------------------------------------
root         979  0.0  0.3 109688 13568 ?        Ssl   2025   0:00 /usr/bin/python3 /usr/share/unattended-upgrades/unattended-upgrade-shutdown --wait-for-signal
l9        259745  0.3  3.8 500900 150740 ?       Ssl  19:44   0:05 /opt/l9/venv/bin/python -m uvicorn api.server_memory:app --host 127.0.0.1 --port 8000

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