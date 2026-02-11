> ^C
root@C1:/opt/l9# cd /opt/l9
sleep 30  # Wait for healthchecks to pass
docker compose ps  # Check if l9-api is now healthy
docker compose logs l9-api --tail=100 | grep -E "startup_ready|embedding|error|unhealthy"  # Check for errors
curl -s http://127.0.0.1:8000/health | jq .  # Direct health check
NAME                 IMAGE                                    COMMAND                  SERVICE         CREATED         STATUS                   PORTS
l9-grafana           grafana/grafana:10.2.0                   "/run.sh"                grafana         3 minutes ago   Up 3 minutes (healthy)   127.0.0.1:3000->3000/tcp
l9-jaeger            jaegertracing/all-in-one:1.52            "/go/bin/all-in-one-…"   jaeger          3 minutes ago   Up 3 minutes (healthy)   4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-l9-api-1          ghcr.io/cryptoxdog/l9-api:4.1.0          "uvicorn api.server:…"   l9-api          3 minutes ago   Up 3 minutes (healthy)   127.0.0.1:8000->8000/tcp
l9-l9-mcp-memory-1   ghcr.io/cryptoxdog/l9-mcp-memory:4.1.0   "uvicorn mcp_memory.…"   l9-mcp-memory   3 minutes ago   Up 3 minutes (healthy)   127.0.0.1:9002->9002/tcp
l9-neo4j             neo4j:5-community                        "tini -g -- /startup…"   neo4j           3 minutes ago   Up 3 minutes (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-nginx-1           nginx:alpine                             "/docker-entrypoint.…"   nginx           3 minutes ago   Up 3 minutes             0.0.0.0:80->80/tcp, 0.0.0.0:30379->30379/tcp, 0.0.0.0:30432->30432/tcp, 0.0.0.0:30474->30474/tcp, 0.0.0.0:30687->30687/tcp
l9-postgres          pgvector/pgvector:pg16                   "docker-entrypoint.s…"   l9-postgres     3 minutes ago   Up 3 minutes (healthy)   127.0.0.1:5432->5432/tcp
l9-prometheus        prom/prometheus:v2.48.0                  "/bin/prometheus --c…"   prometheus      3 minutes ago   Up 3 minutes (healthy)   127.0.0.1:9090->9090/tcp
l9-redis             redis:7-alpine                           "docker-entrypoint.s…"   redis           3 minutes ago   Up 3 minutes (healthy)   127.0.0.1:6379->6379/tcp
{
  "status": "ok",
  "service": "l9-api",
  "startup_ready": true
}
root@C1:/opt/l9# # C1 Comprehensive MRI (Medical Readiness Inspection)
# Run after container rebuild to verify full system health

cd /opt/l9
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: INFRASTRUCTURE BASELINE
# ═══════════════════════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo "SECTION 1: INFRASTRUCTURE BASELINE"
echo "═══════════════════════════════════════════════════════════════"

# 1.1 System resources
echo -e "\n[1.1] SYSTEM RESOURCES"
echo "─────────────────────"
free -h
echo ""
df -h / /var/lib/docker 2>/dev/null || df -h /
echo ""
uptime

# 1.2 Docker info
echo -e "\n[1.2] DOCKER ENGINE"
echo "───────────────────"
docker info 2>/dev/null | grep -E "Server Version|Storage Driver|Docker Root Dir|Total Memory|CPUs"

# 1.3 Configuration files
echo -e "\n[1.3] CONFIGURATION FILES"
echo "─────────────────────────"
ls -la docker-compose*.yml .env* 2>/dev/null
echo ""
echo "Git commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
echo "Git branch: $(git branch --show-current 2>/dev/null || echo 'N/A')"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: CONTAINER STATUS
# ═══════════════════════════════════════════════════════════════════════════════

echo -e "\n═══════════════════════════════════════════════════════════════"
echo "SECTION 2: CONTAINER STATUS"
echo "═══════════════════════════════════════════════════════════════"

# 2.1 All containers (including exited)
echo -e "\n[2.1] ALL CONTAINERS"
echo "────────────────────"
$COMPOSE ps -a

# 2.2 Container health/restart counts
echo -e "\n[2.2] CONTAINER DETAILS (restarts, created, status)"
echo "────────────────────────────────────────────────────"
  echo "╚═══════════════════════════════════════════════════════════════╝"then echo "❌")o "❌")ER BY count DESC LIMIT 10"}]}' 2>/dev/null | jq -r '.results[0].data[].row | "\(.[0]
═══════════════════════════════════════════════════════════════
SECTION 1: INFRASTRUCTURE BASELINE
═══════════════════════════════════════════════════════════════

[1.1] SYSTEM RESOURCES
─────────────────────
               total        used        free      shared  buff/cache   available
Mem:           7.6Gi       4.9Gi       408Mi        48Mi       2.7Gi       2.7Gi
Swap:             0B          0B          0B

Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       150G   18G  127G  13% /
/dev/sda1       150G   18G  127G  13% /

 08:52:11 up 14 days, 12:29,  1 user,  load average: 0.56, 1.02, 1.02

[1.2] DOCKER ENGINE
───────────────────
 Server Version: 29.2.0
 Storage Driver: overlay2
 CPUs: 4
 Total Memory: 7.564GiB
 Docker Root Dir: /var/lib/docker

[1.3] CONFIGURATION FILES
─────────────────────────
-rw-r--r-- 1 root root 11691 Feb  6 08:08 docker-compose.prod.yml
-rw-r--r-- 1 root root  8011 Feb  6 08:08 docker-compose.yml
-rw------- 1 root root  6826 Feb  6 08:43 .env
-rw-r--r-- 1 root root  6795 Feb  2 18:29 .env.bak2
-rw-r--r-- 1 root root  4345 Feb  6 01:21 .env.bak.20260206_030831
-rw------- 1 root root  6792 Feb  6 08:08 .env.bak.20260206_031219
-rw------- 1 root root  6792 Feb  6 08:12 .env.bak.20260206_031404
-rw------- 1 root root  6792 Feb  6 08:14 .env.bak.20260206_031655
-rw------- 1 root root  6792 Feb  6 08:16 .env.bak.20260206_034353
-rw-r--r-- 1 root root  5047 Jan 24 22:53 .env.example
-rw-r--r-- 1 root root  5297 Feb  6 08:08 .env.vps.template

Git commit: 20282955
Git branch: main

═══════════════════════════════════════════════════════════════
SECTION 2: CONTAINER STATUS
═══════════════════════════════════════════════════════════════

[2.1] ALL CONTAINERS
────────────────────
NAME                 IMAGE                                    COMMAND                  SERVICE         CREATED         STATUS                     PORTS
l9-bootstrap         ghcr.io/cryptoxdog/l9-api:4.1.0          "python -m bootstrap"    l9-bootstrap    6 minutes ago   Exited (0) 6 minutes ago   
l9-grafana           grafana/grafana:10.2.0                   "/run.sh"                grafana         6 minutes ago   Up 6 minutes (healthy)     127.0.0.1:3000->3000/tcp
l9-jaeger            jaegertracing/all-in-one:1.52            "/go/bin/all-in-one-…"   jaeger          6 minutes ago   Up 6 minutes (healthy)     4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-l9-api-1          ghcr.io/cryptoxdog/l9-api:4.1.0          "uvicorn api.server:…"   l9-api          6 minutes ago   Up 6 minutes (healthy)     127.0.0.1:8000->8000/tcp
l9-l9-mcp-memory-1   ghcr.io/cryptoxdog/l9-mcp-memory:4.1.0   "uvicorn mcp_memory.…"   l9-mcp-memory   6 minutes ago   Up 6 minutes (healthy)     127.0.0.1:9002->9002/tcp
l9-neo4j             neo4j:5-community                        "tini -g -- /startup…"   neo4j           6 minutes ago   Up 6 minutes (healthy)     127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-nginx-1           nginx:alpine                             "/docker-entrypoint.…"   nginx           6 minutes ago   Up 6 minutes               0.0.0.0:80->80/tcp, 0.0.0.0:30379->30379/tcp, 0.0.0.0:30432->30432/tcp, 0.0.0.0:30474->30474/tcp, 0.0.0.0:30687->30687/tcp
l9-postgres          pgvector/pgvector:pg16                   "docker-entrypoint.s…"   l9-postgres     6 minutes ago   Up 6 minutes (healthy)     127.0.0.1:5432->5432/tcp
l9-prometheus        prom/prometheus:v2.48.0                  "/bin/prometheus --c…"   prometheus      6 minutes ago   Up 6 minutes (healthy)     127.0.0.1:9090->9090/tcp
l9-redis             redis:7-alpine                           "docker-entrypoint.s…"   redis           6 minutes ago   Up 6 minutes (healthy)     127.0.0.1:6379->6379/tcp

[2.2] CONTAINER DETAILS (restarts, created, status)
────────────────────────────────────────────────────
NAMES                STATUS                     PORTS
l9-nginx-1           Up 6 minutes               0.0.0.0:80->80/tcp, 0.0.0.0:30379->30379/tcp, 0.0.0.0:30432->30432/tcp, 0.0.0.0:30474->30474/tcp, 0.0.0.0:30687->30687/tcp
l9-l9-api-1          Up 6 minutes (healthy)     127.0.0.1:8000->8000/tcp
l9-l9-mcp-memory-1   Up 6 minutes (healthy)     127.0.0.1:9002->9002/tcp
l9-bootstrap         Exited (0) 6 minutes ago   
l9-grafana           Up 6 minutes (healthy)     127.0.0.1:3000->3000/tcp
l9-postgres          Up 6 minutes (healthy)     127.0.0.1:5432->5432/tcp
l9-neo4j             Up 6 minutes (healthy)     127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-jaeger            Up 6 minutes (healthy)     4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-prometheus        Up 6 minutes (healthy)     127.0.0.1:9090->9090/tcp
l9-redis             Up 6 minutes (healthy)     127.0.0.1:6379->6379/tcp

[2.3] IMAGES IN USE
───────────────────
ghcr.io/cryptoxdog/l9-api          4.1.0         1.75GB    6 minutes ago
ghcr.io/cryptoxdog/l9-mcp-memory   4.1.0         434MB     7 minutes ago
redis                              7-alpine      41.4MB    9 days ago
neo4j                              5-community   555MB     13 days ago

═══════════════════════════════════════════════════════════════
SECTION 3: SERVICE HEALTH CHECKS
═══════════════════════════════════════════════════════════════

[3.1] L9 API HEALTH
───────────────────
{"status":"ok","service":"l9-api","startup_ready":true}

[3.2] POSTGRESQL HEALTH
───────────────────────
/var/run/postgresql:5432 - accepting connections
✅ PostgreSQL ready
(query failed)

[3.3] NEO4J HEALTH
──────────────────
✅ Neo4j browser accessible
❌ Cypher query failed

[3.4] REDIS HEALTH
──────────────────
NOAUTH Authentication required.

✅ Redis responding
(memory info N/A)

[3.5] MCP MEMORY HEALTH
───────────────────────
⚠️ MCP Memory not responding (may be expected)

═══════════════════════════════════════════════════════════════
SECTION 4: NETWORK & PORTS
═══════════════════════════════════════════════════════════════

[4.1] LISTENING PORTS
─────────────────────
State  Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess                                                    
LISTEN 0      4096       127.0.0.1:9002       0.0.0.0:*    users:(("docker-proxy",pid=3895235,fd=8))                 
LISTEN 0      4096       127.0.0.1:9090       0.0.0.0:*    users:(("docker-proxy",pid=3894270,fd=8))                 
LISTEN 0      4096       127.0.0.1:16686      0.0.0.0:*    users:(("docker-proxy",pid=3894183,fd=8))                 
LISTEN 0      4096       127.0.0.1:14268      0.0.0.0:*    users:(("docker-proxy",pid=3894165,fd=8))                 
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=3894206,fd=8))                 
LISTEN 0      4096       127.0.0.1:3000       0.0.0.0:*    users:(("docker-proxy",pid=3894929,fd=8))                 
LISTEN 0      4096         0.0.0.0:30687      0.0.0.0:*    users:(("docker-proxy",pid=3895475,fd=8))                 
LISTEN 0      4096      127.0.0.54:53         0.0.0.0:*    users:(("systemd-resolve",pid=2660798,fd=17))             
LISTEN 0      4096         0.0.0.0:30474      0.0.0.0:*    users:(("docker-proxy",pid=3895461,fd=8))                 
LISTEN 0      4096   127.0.0.53%lo:53         0.0.0.0:*    users:(("systemd-resolve",pid=2660798,fd=15))             
LISTEN 0      4096         0.0.0.0:30432      0.0.0.0:*    users:(("docker-proxy",pid=3895447,fd=8))                 
LISTEN 0      4096         0.0.0.0:30379      0.0.0.0:*    users:(("docker-proxy",pid=3895433,fd=8))                 
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=3894233,fd=8))                 
LISTEN 0      4096       127.0.0.1:8000       0.0.0.0:*    users:(("docker-proxy",pid=3895345,fd=8))                 
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=3894335,fd=8))                 
LISTEN 0      4096         0.0.0.0:80         0.0.0.0:*    users:(("docker-proxy",pid=3895420,fd=8))                 
LISTEN 0      4096         0.0.0.0:22         0.0.0.0:*    users:(("sshd",pid=2660781,fd=3),("systemd",pid=1,fd=218))
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=3894313,fd=8))                 
LISTEN 0      4096            [::]:22            [::]:*    users:(("sshd",pid=2660781,fd=4),("systemd",pid=1,fd=219))

[4.2] DOCKER NETWORKS
─────────────────────
NETWORK ID     NAME         DRIVER    SCOPE
5409207cb8ee   l9-network   bridge    local

(network inspect failed)

═══════════════════════════════════════════════════════════════
SECTION 5: LOGS & ERRORS (last 5 min)
═══════════════════════════════════════════════════════════════

[5.1] L9 API ERRORS
───────────────────
l9-api-1  | {"event": "Redis dequeue failed: Timeout connecting to server", "logger": "runtime.redis_client", "level": "error", "timestamp": "2026-02-06T08:47:46.460711Z"}
l9-api-1  | {"event": "Redis dequeue failed: Timeout connecting to server", "logger": "runtime.redis_client", "level": "error", "timestamp": "2026-02-06T08:47:46.466689Z"}
l9-api-1  | {"event": "Redis dequeue failed: Timeout connecting to server", "logger": "runtime.redis_client", "level": "error", "timestamp": "2026-02-06T08:47:46.697959Z"}
l9-api-1  | {"event": "Redis dequeue failed: Timeout connecting to server", "logger": "runtime.redis_client", "level": "error", "timestamp": "2026-02-06T08:47:47.201143Z"}

[5.2] POSTGRESQL ERRORS
───────────────────────
l9-postgres  | 2026-02-06 08:47:24.289 UTC [267] ERROR:  relation "packets" does not exist at character 38
l9-postgres  | 2026-02-06 08:47:31.172 UTC [290] ERROR:  relation "packets" does not exist at character 34
l9-postgres  | 2026-02-06 08:47:31.404 UTC [297] FATAL:  role "l9_user" is not permitted to log in
l9-postgres  | 2026-02-06 08:52:12.607 UTC [774] ERROR:  relation "packets" does not exist at character 38

[5.3] NEO4J ERRORS
──────────────────

[5.4] REDIS ERRORS
──────────────────

[5.5] BOOTSTRAP STATUS
──────────────────────
NAME                 IMAGE                                    COMMAND                  SERVICE         CREATED         STATUS                     PORTS
l9-bootstrap         ghcr.io/cryptoxdog/l9-api:4.1.0          "python -m bootstrap"    l9-bootstrap    6 minutes ago   Exited (0) 6 minutes ago   
l9-bootstrap  | [BOOTSTRAP:OK] Bootstrap already completed. Skipping.

═══════════════════════════════════════════════════════════════
SECTION 6: DATA PERSISTENCE (VOLUMES)
═══════════════════════════════════════════════════════════════

[6.1] DOCKER VOLUMES
────────────────────
DRIVER    VOLUME NAME
local     l9-grafana-data
local     l9-grafana-data-prod
local     l9-jaeger-data-prod
local     l9-neo4j-data
local     l9-neo4j-data-prod
local     l9-neo4j-logs
local     l9-neo4j-logs-prod
local     l9-postgres-data
local     l9-postgres-data-prod
local     l9-prometheus-data
local     l9-prometheus-data-prod
local     l9-redis-data
local     l9-redis-data-prod

[6.2] VOLUME SIZES
──────────────────
l9-grafana-data: 1.0M
l9-grafana-data-prod: 1.0M
l9-jaeger-data-prod: 4.0K
l9-neo4j-data: 517.2M
l9-neo4j-data-prod: 516.0M
l9-neo4j-logs: 5.8M
l9-neo4j-logs-prod: 112.0K
l9-postgres-data: 1.1G
l9-postgres-data-prod: 67.8M
l9-prometheus-data: 54.2M
l9-prometheus-data-prod: 1.3M
l9-redis-data: 96.0K
l9-redis-data-prod: 16.0K

[6.3] POSTGRESQL DATA SUMMARY
──────────────────────────────
(query failed)

[6.4] NEO4J DATA SUMMARY
────────────────────────

═══════════════════════════════════════════════════════════════
SECTION 7: API ENDPOINT TESTS
═══════════════════════════════════════════════════════════════

[7.1] CRITICAL ENDPOINTS
────────────────────────
✅ http://127.0.0.1:8000/health (200)
❌ http://127.0.0.1:8000/api/v1/status (404000)
✅ http://127.0.0.1:8000/docs (200)
❌ http://127.0.0.1:8000/openapi.json (500000)

═══════════════════════════════════════════════════════════════
SECTION 8: ENVIRONMENT VALIDATION
═══════════════════════════════════════════════════════════════

[8.1] REQUIRED ENV VARS
───────────────────────
✅ POSTGRES_PASSWORD is set
✅ NEO4J_PASSWORD is set
✅ OPENAI_API_KEY is set
✅ L9_API_KEY is set

[8.2] ENV FILE (redacted)
─────────────────────────
# =============================================================================
# L9 DOCKER/VPS Environment (.env.vps)
# For Docker Compose on VPS - uses service DNS names (NOT localhost!)
#
# ⚠️  CRITICAL: NO INLINE COMMENTS ALLOWED
#     Pydantic-settings parses entire line as value
# =============================================================================

# -----------------------------------------------------------------------------
# Database (use container service names, NOT localhost/127.0.0.1)
# -----------------------------------------------------------------------------
POSTGRES_USER=postgres
POSTGRES_PASSWORD=***REDACTED***
POSTGRES_DB=l9_memory
MEMORY_DSN=postgresql://postgres:***@l9-postgres:5432/l9_memory
DATABASE_URL=postgresql://postgres:***@l9-postgres:5432/l9_memory

# -----------------------------------------------------------------------------
# API Keys
# -----------------------------------------------------------------------------
L9_EXECUTOR_API_KEY=***REDACTED***
L9_API_KEY=***REDACTED***
OPENAI_API_KEY=***REDACTED***
PERPLEXITY_API_KEY=***REDACTED***
GOOGLE_CALENDAR_API_KEY=***REDACTED***
GMAIL_API_KEY=***REDACTED***
GPG_KEY=***REDACTED***
L9_API_URL=http://mcp.quantumaipartners.com:30080
# -----------------------------------------------------------------------------
# Neo4j Graph Database (use container name)

═══════════════════════════════════════════════════════════════
SECTION 9: MRI SUMMARY
═══════════════════════════════════════════════════════════════

Timestamp: 2026-02-06 08:52:19 UTC
Hostname: C1
Git commit: 20282955

SERVICE STATUS SUMMARY:
───────────────────────
  L9 API:     ✅
  PostgreSQL: ✅
  Neo4j:      ✅
  Redis:      ✅

╔═══════════════════════════════════════════════════════════════╗
║  ✅ Docker Compose - 50 Logs                                  ║
╚═══════════════════════════════════════════════════════════════╝
total 1024
drwxr-xr-x 58 root root   4096 Feb  6 08:43 .
drwxr-xr-x  5 root root   4096 Jan 22 20:56 ..
drwxr-xr-x  3 root root   4096 Feb  1 04:28 adapters
drwxr-xr-x  6 root root   4096 Feb  1 04:28 agents
drwxr-xr-x  7 root root   4096 Feb  6 08:08 api
drwxr-xr-x  5 root root   4096 Jan 22 20:56 _archived
drwxr-xr-x  4 root root   4096 Feb  1 03:45 .backup
-rw-r--r--  1 root root    652 Jan 24 22:53 .bandit
drwxr-xr-x  2 root root   4096 Feb  2 21:42 bootstrap
drwxr-xr-x  3 root root   4096 Feb  6 08:08 ci
-rw-r--r--  1 root root   4153 Feb  2 15:28 CLAUDE.md
drwxr-xr-x  2 root root   4096 Feb  3 01:03 clients
-rw-r--r--  1 root root   1751 Jan 26 22:25 codecov.yml
drwxr-xr-x  4 root root   4096 Feb  1 03:45 codegenagent
-rw-r--r--  1 root root   2233 Jan 26 22:25 coderabbit.yaml
drwxr-xr-x  2 root root   4096 Feb  1 04:28 collaborative_cells
drwxr-xr-x  9 root root   4096 Feb  1 04:28 config
-rw-r--r--  1 root root   6795 Feb  1 04:28 conftest.py
drwxr-xr-x 41 root root   4096 Feb  3 00:20 core
drwxr-xr-x  3 root root   4096 Jan 31 14:55 current_work
-rw-r--r--  1 root root    231 Feb  1 03:45 .cursorignore
-rw-r--r--  1 root root   1779 Jan 26 22:25 .datree-policy.yaml
drwxr-xr-x  5 root root   4096 Feb  6 08:08 deploy
-rw-r--r--  1 root root  11691 Feb  6 08:08 docker-compose.prod.yml
-rw-r--r--  1 root root   8011 Feb  6 08:08 docker-compose.yml
-rw-r--r--  1 root root   4828 Feb  2 21:55 Dockerfile
-rw-r--r--  1 root root   5009 Feb  1 03:45 Dockerfile.mcp-memory
-rw-r--r--  1 root root    438 Jan 26 22:25 .dockerignore
drwxr-xr-x  4 root root   4096 Feb  2 18:29 docs
drwxr-xr-x  5 root root   4096 Feb  1 04:28 domain_tensor_bridge
-rw-r--r--  1 root root 306391 Feb  1 04:28 dora_complete_injection_report.json
-rw-r--r--  1 root root    458 Jan 24 22:53 .editorconfig
drwxr-xr-x  2 root root   4096 Feb  1 04:28 email_agent
-rw-------  1 root root   6826 Feb  6 08:43 .env
-rw-r--r--  1 root root   6795 Feb  2 18:29 .env.bak2
-rw-r--r--  1 root root   4345 Feb  6 01:21 .env.bak.20260206_030831
-rw-------  1 root root   6792 Feb  6 08:08 .env.bak.20260206_031219
-rw-------  1 root root   6792 Feb  6 08:12 .env.bak.20260206_031404
-rw-------  1 root root   6792 Feb  6 08:14 .env.bak.20260206_031655
-rw-------  1 root root   6792 Feb  6 08:16 .env.bak.20260206_034353
-rw-r--r--  1 root root   5047 Jan 24 22:53 .env.example
-rw-r--r--  1 root root   5297 Feb  6 08:08 .env.vps.template
drwxr-xr-x  2 root root   4096 Feb  1 04:28 examples
drwxr-xr-x  2 root root   4096 Jan 26 22:25 .gemini
drwxr-xr-x  8 root root   4096 Feb  6 08:43 .git
drwxr-xr-x  4 root root   4096 Jan 26 22:25 .github
-rw-r--r--  1 root root   2383 Feb  6 08:08 .gitignore
-rw-r--r--  1 root root    442 Feb  3 01:25 .gitleaksignore
-rw-r--r--  1 root root   2332 Jan 25 16:21 .gitleaks.toml
-rw-r--r--  1 root root   2246 Feb  2 23:35 .gmp_executor_state.json
drwxr-xr-x  2 root root   4096 Feb  1 04:28 governance
drwxr-xr-x  3 root root   4096 Jan 22 20:56 grafana
drwxr-xr-x  2 root root   4096 Feb  1 04:28 graph_adapter
-rw-r--r--  1 root root   2037 Feb  1 04:28 __init__.py
drwxr-xr-x  2 root root   4096 Feb  1 04:28 ir_engine
-rw-r--r--  1 root root     71 Jan 26 22:25 L9.code-workspace
drwxr-xr-x  2 root root   4096 Feb  1 03:45 langgraph
drwxr-xr-x  2 root root   4096 Jan 31 14:55 local_dashboard
drwxr-xr-x  3 root root   4096 Feb  1 04:28 mac_agent
-rw-r--r--  1 root root  10794 Feb  1 03:45 Makefile
drwxr-xr-x  4 root root   4096 Feb  1 03:45 mcp_memory
drwxr-xr-x  6 root root   4096 Feb  6 08:43 memory
drwxr-xr-x  2 root root   4096 Feb  2 18:29 memory_cache
drwxr-xr-x  2 root root   4096 Feb  2 23:24 migrations
-rw-r--r--  1 root root      0 Jan 22 20:56 .migrations_applied
drwxr-xr-x  2 root root   4096 Feb  6 08:08 motifs
drwxr-xr-x  2 root root   4096 Jan 22 20:56 ops
drwxr-xr-x  2 root root   4096 Feb  1 04:28 orchestration
drwxr-xr-x 11 root root   4096 Feb  1 04:28 orchestrators
-rw-r--r--  1 root root   6892 Feb  1 03:45 .pre-commit-config.yaml
drwxr-xr-x  5 root root   4096 Feb  1 04:28 private
drwxr-xr-x  6 root root   4096 Jan 31 14:55 prompts
-rw-r--r--  1 root root   3528 Jan 29 02:07 pyproject.toml
-rw-r--r--  1 root root    422 Jan 26 22:25 pytest.ini
drwxr-xr-x  6 root root   4096 Feb  1 03:45 readme
-rw-r--r--  1 root root  24333 Jan 29 02:07 README.md
drwxr-xr-x  2 root root   4096 Feb  1 03:45 .refactor-config
drwxr-xr-x  2 root root   4096 Jan 26 22:25 .refactor-reports
drwxr-xr-x  6 root root   4096 Feb  2 23:35 reports
-rw-r--r--  1 root root   3049 Jan 26 22:25 requirements-docker.txt
-rw-r--r--  1 root root    815 Feb  1 03:45 requirements-mcp-memory.txt
-rw-r--r--  1 root root   1760 Jan 26 22:25 requirements.txt
-rw-r--r--  1 root root   5588 Jan 29 02:07 ruff.toml
-rw-r--r--  1 root root   1660 Jan 22 20:56 RUNBOOK.md
drwxr-xr-x  2 root root   4096 Feb  2 23:21 runtime
drwxr-xr-x 21 root root   4096 Feb  6 01:21 scripts
drwxr-xr-x  2 root root   4096 Feb  6 08:08 SDK
drwxr-xr-x  2 root root   4096 Jan 26 22:25 .sec
-rw-r--r--  1 root root   2123 Jan 26 22:25 SECURITY.md
drwxr-xr-x  2 root root   4096 Feb  2 18:29 seed
drwxr-xr-x  2 root root   4096 Feb  1 04:28 .semgrep
drwxr-xr-x  4 root root   4096 Feb  1 04:28 services
drwxr-xr-x  2 root root   4096 Feb  1 04:28 simulation
-rw-r--r--  1 root root    510 Jan 24 22:53 sonar-project.properties
-rw-r--r--  1 root root    819 Jan 26 22:25 .suite6-config.json
-rw-r--r--  1 root root   9249 Jan 26 22:25 TECHNICAL_DEBT_CLEANUP_PR.md
drwxr-xr-x  2 root root   4096 Feb  1 04:28 telemetry
drwxr-xr-x 37 root root   4096 Feb  1 04:28 tests
-rw-r--r--  1 root root   8688 Jan 26 22:25 TODO-AB-Testing-Framework.md
-rw-r--r--  1 root root   6624 Jan 26 22:25 TODO-Compile-Chat-Transcripts.md
-rw-r--r--  1 root root   9225 Feb  2 21:26 TODO-DORA_BLOCK_ROOT_CAUSE_ANALYSIS.md
-rw-r--r--  1 root root  55366 Feb  2 21:26 TODO-gap-analysis-memory.md
-rw-r--r--  1 root root  33496 Jan 31 14:55 TODO.md
-rw-r--r--  1 root root   3365 Jan 26 22:25 TODO-Research.md
-rw-r--r--  1 root root   3737 Jan 26 22:25 TODO-Update-Extractors.md
drwxr-xr-x  6 root root   4096 Feb  1 04:28 tools
-rw-r--r--  1 root root    520 Jan 26 22:25 VPS-Commands.md
-rw-r--r--  1 root root      0 Jan 22 20:56 .vultureignore
-rw-r--r--  1 root root    301 Feb  6 08:08 .wire_executor_state.json
drwxr-xr-x  2 root root   4096 Feb  1 04:28 workers
drwxr-xr-x  7 root root   4096 Feb  2 18:29 workflows
-rw-r--r--  1 root root  19151 Feb  2 23:35 workflow_state.md
drwxr-xr-x  5 root root   4096 Feb  2 21:18 world_model
-rw-r--r--  1 root root  55199 Jan 29 02:07 z-test.md
-rw-r--r-- 1 root root 11691 Feb  6 08:08 docker-compose.prod.yml
service "l9-api" depends on undefined service "l9-postgres": invalid compose project
SNIPER ERROR LOCATOR ->
service "l9-mcp-memory" depends on undefined service "redis": invalid compose project
> cd /opt/l9
docker compose exec l9-postgres psql -U postgres -d l9_memory -c "TRUNCATE TABLE semantic_memory CASCADE;"  # Delete 9M rows (instant)
docker compose exec l9-postgres psql -U postgres -d l9_memory -c "VACUUM FULL semantic_memory;"  # Reclaim 113GB (be patient, this is the slow part)
docker compose exec l9-postgres psql -U postgres -d l9_memory -c "REINDEX TABLE semantic_memory;"  # Rebuild indexes (~1 min)
docker compose exec l9-postgres psql -U postgres -d l9_memory -c "SELECT COUNT(*), pg_size_pretty(pg_total_relation_size('semantic_memory'));"  # Verify cleanup
df -h | grep sda1  # Check disk space reclaimed
^C
root@C1:/opt/l9# cd /opt/l9
docker compose exec l9-postgres psql -U postgres -d l9_memory -c "TRUNCATE TABLE semantic_memory CASCADE;"  # Delete 9M rows (instant)
docker compose exec l9-postgres psql -U postgres -d l9_memory -c "VACUUM FULL semantic_memory;"  # Reclaim 113GB (be patient, this is the slow part)
docker compose exec l9-postgres psql -U postgres -d l9_memory -c "REINDEX TABLE semantic_memory;"  # Rebuild indexes (~1 min)
docker compose exec l9-postgres psql -U postgres -d l9_memory -c "SELECT COUNT(*), pg_size_pretty(pg_total_relation_size('semantic_memory'));"  # Verify cleanup
df -h | grep sda1  # Check disk space reclaimed
TRUNCATE TABLE
VACUUM
REINDEX
 count | pg_size_pretty 
-------+----------------
     1 | 120 kB
(1 row)

/dev/sda1       150G   18G  127G  13% /
/dev/sda15      253M  146K  252M   1% /boot/efi
root@C1:/opt/l9# cd /opt/l9
curl -s http://127.0.0.1:8000/health | jq .  # Should return {"status":"ok"}
curl -s http://127.0.0.1:8000/docs 2>&1 | head -5  # Should return HTML
docker compose logs l9-api --tail=30 | grep -E "startup_ready|Application startup complete"  # Confirm API started
{
  "status": "ok",
  "service": "l9-api",
  "startup_ready": true
}

    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
root@C1:/opt/l9# cd /opt/l9
docker compose exec neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" "RETURN 1;"  # Test with auth
docker compose logs neo4j --tail=20 | grep -i "started\|ready"  # Confirm Neo4j ready
password: 
The client is unauthorized due to authentication failure.
l9-neo4j  | 2026-02-06 08:45:47.515+0000 INFO  Started.
root@C1:/opt/l9# cd /opt/l9
curl -s http://127.0.0.1:9002/health 2>&1  # Try /health endpoint
docker compose logs l9-mcp-memory --tail=30 | grep -E "startup|started|error"  # Check startup
{"status":"healthy","database":"connected","database_error":null,"mcp_version":"2025-03-26","index_type":"hnsw","compounding_enabled":true,"decay_enabled":true}root@C1:/opt/l9# cd /opt/l9          cd /opt/l9
docker compose exec l9-postgres psql -U postgres -d l9_memory -c "SELECT COUNT(*) FROM semantic_memory;"  # Should be 0 or very low
docker compose logs l9-api --tail=50 | grep -i "embedding"  # Check for errors
 count 
-------
     0
(1 row)

root@C1:/opt/l9# cd /opt/l9
# Monitor for 60 seconds - count should stay at 1 or grow slowly (< 5 rows/min is normal)
for i in {1..12}; do
  echo "Check $i/12: $(docker compose exec l9-postgres psql -U postgres -d l9_memory -tc 'SELECT COUNT(*) FROM semantic_memory;' | xargs)"
  sleep 5
done
Check 1/12: 0
Check 2/12: 0
Check 3/12: 0
^C
root@C1:/opt/l9# cd /opt/l9
grep NEO4J_PASSWORD .env  # Show the value (it's redacted in your env backup)
NEO4J_PASSWORD=FVmgaD1diPcz41zRbYLLP0UzyGvAi4E
root@C1:/opt/l9# docker compose exec neo4j cypher-shell -u neo4j -p "$(grep NEO4J_PASSWORD .env | cut -d= -f2)" "RETURN 1;"
+---+
| 1 |
+---+
| 1 |
+---+

1 row
ready to start consuming query after 0 ms, results consumed after another 1 ms
root@C1:/opt/l9# cd /opt/l9
echo "Starting 60-second monitor - count should stay at 0 or grow VERY slowly..."
for i in {1..12}; do
  count=$(docker compose exec l9-postgres psql -U postgres -d l9_memory -tc 'SELECT COUNT(*) FROM semantic_memory;' | xargs)
  timestamp=$(date '+%H:%M:%S')
  echo "[$timestamp] Check $i/12: $count rows"
  sleep 5
done
echo "✅ Monitor complete. If count stayed 0-10, the fix is working!"
Starting 60-second monitor - count should stay at 0 or grow VERY slowly...
[08:57:19] Check 1/12: 0 rows
[08:57:25] Check 2/12: 0 rows
^C
✅ Monitor complete. If count stayed 0-10, the fix is working!
root@C1:/opt/l9# cd /opt/l9
./scripts/mri-c1.sh > ~/MRI-C1-Post-Fix-$(date +%Y%m%d_%H%M%S).md
-bash: ./scripts/mri-c1.sh: No such file or directory
root@C1:/opt/l9# cd /opt/l9
docker compose ps  # All containers should show "healthy"
curl -s http://127.0.0.1:8000/health | jq .  # API health
df -h | grep sda1  # Disk space (should stay < 50%)
NAME                 IMAGE                                    COMMAND                  SERVICE         CREATED          STATUS                    PORTS
l9-grafana           grafana/grafana:10.2.0                   "/run.sh"                grafana         13 minutes ago   Up 12 minutes (healthy)   127.0.0.1:3000->3000/tcp
l9-jaeger            jaegertracing/all-in-one:1.52            "/go/bin/all-in-one-…"   jaeger          13 minutes ago   Up 13 minutes (healthy)   4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-l9-api-1          ghcr.io/cryptoxdog/l9-api:4.1.0          "uvicorn api.server:…"   l9-api          13 minutes ago   Up 12 minutes (healthy)   127.0.0.1:8000->8000/tcp
l9-l9-mcp-memory-1   ghcr.io/cryptoxdog/l9-mcp-memory:4.1.0   "uvicorn mcp_memory.…"   l9-mcp-memory   13 minutes ago   Up 12 minutes (healthy)   127.0.0.1:9002->9002/tcp
l9-neo4j             neo4j:5-community                        "tini -g -- /startup…"   neo4j           13 minutes ago   Up 13 minutes (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-nginx-1           nginx:alpine                             "/docker-entrypoint.…"   nginx           13 minutes ago   Up 12 minutes             0.0.0.0:80->80/tcp, 0.0.0.0:30379->30379/tcp, 0.0.0.0:30432->30432/tcp, 0.0.0.0:30474->30474/tcp, 0.0.0.0:30687->30687/tcp
l9-postgres          pgvector/pgvector:pg16                   "docker-entrypoint.s…"   l9-postgres     13 minutes ago   Up 13 minutes (healthy)   127.0.0.1:5432->5432/tcp
l9-prometheus        prom/prometheus:v2.48.0                  "/bin/prometheus --c…"   prometheus      13 minutes ago   Up 13 minutes (healthy)   127.0.0.1:9090->9090/tcp
l9-redis             redis:7-alpine                           "docker-entrypoint.s…"   redis           13 minutes ago   Up 13 minutes (healthy)   127.0.0.1:6379->6379/tcp
{
  "status": "ok",
  "service": "l9-api",
  "startup_ready": true
}
/dev/sda1       150G   18G  127G  13% /
/dev/sda15      253M  146K  252M   1% /boot/efi
root@C1:/opt/l9# cd /opt/l9
./scripts/deployment/vps-mri.sh  # Full system diagnostic
╔════════════════════════════════════════════════════════════════╗
║           L9 VPS MRI - COMPLETE SYSTEM DIAGNOSTIC              ║
║                    (NO SUDO VERSION v1.1)                      ║
╚════════════════════════════════════════════════════════════════╝
Timestamp: 2026-02-06T08:58:52+00:00
Hostname:  C1
User:      root


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A1. SYSTEM IDENTITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Linux C1 6.8.0-90-generic #91-Ubuntu SMP PREEMPT_DYNAMIC Tue Nov 18 14:14:30 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux
    inet 127.0.0.1/8 scope host lo
    inet 46.62.243.82/32 metric 100 scope global dynamic eth0
    inet 10.42.0.0/32 scope global flannel.1


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A2. DISK SPACE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/dev/sda1       150G   18G  127G  13% /
/dev/sda1       150G   18G  127G  13% /
/dev/sda1       150G   18G  127G  13% /


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A3. MEMORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
               total        used        free      shared  buff/cache   available
Mem:           7.6Gi       4.8Gi       623Mi        53Mi       2.5Gi       2.7Gi
Swap:             0B          0B          0B


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A4. LOAD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 08:58:52 up 14 days, 12:35,  1 user,  load average: 0.73, 0.77, 0.90


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
B1. ALL LISTENING PORTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LISTEN 0      4096       127.0.0.1:9002       0.0.0.0:*          
LISTEN 0      4096       127.0.0.1:9090       0.0.0.0:*          
LISTEN 0      4096       127.0.0.1:16686      0.0.0.0:*          
LISTEN 0      4096       127.0.0.1:14268      0.0.0.0:*          
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*          
LISTEN 0      4096       127.0.0.1:3000       0.0.0.0:*          
LISTEN 0      4096         0.0.0.0:30687      0.0.0.0:*          
LISTEN 0      4096      127.0.0.54:53         0.0.0.0:*          
LISTEN 0      4096         0.0.0.0:30474      0.0.0.0:*          
LISTEN 0      4096   127.0.0.53%lo:53         0.0.0.0:*          
LISTEN 0      4096         0.0.0.0:30432      0.0.0.0:*          
LISTEN 0      4096         0.0.0.0:30379      0.0.0.0:*          
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*          
LISTEN 0      4096       127.0.0.1:8000       0.0.0.0:*          
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*          
LISTEN 0      4096         0.0.0.0:80         0.0.0.0:*          
LISTEN 0      4096         0.0.0.0:22         0.0.0.0:*          
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*          
LISTEN 0      4096            [::]:22            [::]:*          


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
B2. CRITICAL PORTS CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Port 80 (HTTP):
LISTEN 0      4096         0.0.0.0:80         0.0.0.0:*          
Port 443 (HTTPS):
  Not listening
Port 5432 (PostgreSQL):
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*          
Port 6379 (Redis):
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*          
Port 7687 (Neo4j Bolt):
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*          
Port 8000 (L9 API):
LISTEN 0      4096       127.0.0.1:8000       0.0.0.0:*          


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
B3. FIREWALL (UFW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: inactive


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
C1. CADDY STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠ Caddy not running or not installed


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
C2. CADDYFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠ No Caddyfile found


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
C3. NGINX STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Nginx not running or not installed


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
D1. DOCKER VERSION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Docker version 29.2.0, build 0b9d198
Docker Compose version v5.0.2


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
D2. DOCKER SERVICE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Docker daemon is RUNNING


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
D3. RUNNING CONTAINERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NAMES                STATUS                      PORTS
l9-nginx-1           Up 12 minutes               0.0.0.0:80->80/tcp, 0.0.0.0:30379->30379/tcp, 0.0.0.0:30432->30432/tcp, 0.0.0.0:30474->30474/tcp, 0.0.0.0:30687->30687/tcp
l9-l9-api-1          Up 12 minutes (healthy)     127.0.0.1:8000->8000/tcp
l9-l9-mcp-memory-1   Up 12 minutes (healthy)     127.0.0.1:9002->9002/tcp
l9-bootstrap         Exited (0) 12 minutes ago   
l9-grafana           Up 13 minutes (healthy)     127.0.0.1:3000->3000/tcp
l9-postgres          Up 13 minutes (healthy)     127.0.0.1:5432->5432/tcp
l9-neo4j             Up 13 minutes (healthy)     127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-jaeger            Up 13 minutes (healthy)     4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-prometheus        Up 13 minutes (healthy)     127.0.0.1:9090->9090/tcp
l9-redis             Up 13 minutes (healthy)     127.0.0.1:6379->6379/tcp


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
D4. DOCKER IMAGES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REPOSITORY                         TAG           SIZE
ghcr.io/cryptoxdog/l9-api          4.1.0         1.75GB
ghcr.io/cryptoxdog/l9-mcp-memory   4.1.0         434MB
nginx                              alpine        61.9MB
redis                              7-alpine      41.4MB
alpine                             latest        8.44MB
neo4j                              5-community   555MB
pgvector/pgvector                  pg16          507MB
jaegertracing/all-in-one           1.52          74MB
prom/prometheus                    v2.48.0       247MB


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
D5. DOCKER NETWORKS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NETWORK ID     NAME         DRIVER    SCOPE
ddc3319bce31   bridge       bridge    local
8c49853f9e40   host         host      local
5409207cb8ee   l9-network   bridge    local
9427dc1d4571   none         null      local


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
E1. L9 INSTALLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ /opt/l9 exists
total 1024
drwxr-xr-x 58 root root   4096 Feb  6 08:43 .
drwxr-xr-x  5 root root   4096 Jan 22 20:56 ..
drwxr-xr-x  3 root root   4096 Feb  1 04:28 adapters
drwxr-xr-x  6 root root   4096 Feb  1 04:28 agents
drwxr-xr-x  7 root root   4096 Feb  6 08:08 api
drwxr-xr-x  5 root root   4096 Jan 22 20:56 _archived
drwxr-xr-x  4 root root   4096 Feb  1 03:45 .backup
-rw-r--r--  1 root root    652 Jan 24 22:53 .bandit
drwxr-xr-x  2 root root   4096 Feb  2 21:42 bootstrap
drwxr-xr-x  3 root root   4096 Feb  6 08:08 ci
-rw-r--r--  1 root root   4153 Feb  2 15:28 CLAUDE.md
drwxr-xr-x  2 root root   4096 Feb  3 01:03 clients
-rw-r--r--  1 root root   1751 Jan 26 22:25 codecov.yml
drwxr-xr-x  4 root root   4096 Feb  1 03:45 codegenagent


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
E2. DOCKER CONTAINERS (Canonical Deployment)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Docker is the ONLY supported deployment method.
Systemd services (l9.service, l9-mcp.service) are DEPRECATED.

NAMES                STATUS                    PORTS
l9-nginx-1           Up 12 minutes             0.0.0.0:80->80/tcp, 0.0.0.0:30379->30379/tcp, 0.0.0.0:30432->30432/tcp, 0.0.0.0:30474->30474/tcp, 0.0.0.0:30687->30687/tcp
l9-l9-api-1          Up 12 minutes (healthy)   127.0.0.1:8000->8000/tcp
l9-l9-mcp-memory-1   Up 13 minutes (healthy)   127.0.0.1:9002->9002/tcp
l9-grafana           Up 13 minutes (healthy)   127.0.0.1:3000->3000/tcp
l9-postgres          Up 13 minutes (healthy)   127.0.0.1:5432->5432/tcp
l9-neo4j             Up 13 minutes (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-jaeger            Up 13 minutes (healthy)   4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-prometheus        Up 13 minutes (healthy)   127.0.0.1:9090->9090/tcp
l9-redis             Up 13 minutes (healthy)   127.0.0.1:6379->6379/tcp


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
E3. DOCKER-COMPOSE.YML
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Found: /opt/l9/docker-compose.yml

# component_name: "Docker-Compose"
# module_version: "1.0.0"
# created_by: "Igor"
# created_at: "2025-12-26T23:48:00Z"
# updated_at: "2026-01-31T22:53:39Z"
# layer: "operations"
# domain: "docker-compose.yml"
# file_name: "docker-compose"
# type: "utility"
# status: "active"

# =============================================================================
# L9 Docker Compose - BASE INFRASTRUCTURE
# =============================================================================
# Version: 4.0.0
# Purpose: Core infrastructure services (PostgreSQL, Neo4j, Redis, Monitoring)
# Usage: Base file for all environments, combined with overlays
#
# REQUIRED: .env (or --env-file) MUST contain ALL required variables.
# NO MISSING VARIABLES TOLERATED. Required: POSTGRES_PASSWORD, NEO4J_PASSWORD,
# GRAFANA_PASSWORD, OPENAI_API_KEY, L9_API_KEY. Validate: scripts/check_compose_env.sh [.env]
#
# USAGE PATTERNS:
#   Development:
#     docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file .env up
#
#   Production:
#     docker compose -f docker-compose.yml -f docker-compose.prod.yml \
#       --env-file deploy/c1/.env.c1 up -d
#
# PHILOSOPHY:
#   - This file contains ONLY infrastructure (no L9 application services)
#   - Application services (l9-api, l9-mcp-memory) are in overlay files
#   - All services use env_file directive for automatic variable injection
#   - No hardcoded secrets - everything from .env files
# =============================================================================

services:
  # ===========================================================================
  # PostgreSQL - Memory Substrate (PacketStore + pgvector)
  # ===========================================================================
  l9-postgres:
    image: pgvector/pgvector:pg16
    container_name: ${COMPOSE_PROJECT_NAME:-l9}-postgres
    restart: unless-stopped
    env_file:
      - .env
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_INITDB_ARGS: "-E UTF8 --locale=en_US.UTF-8"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 20
    networks:
      - l9-network
    labels:
      - "com.l9.service=postgres"
      - "com.l9.layer=substrate"

  # ===========================================================================
  # Neo4j - Knowledge Graph
  # ===========================================================================
  neo4j:
    image: neo4j:5-community
    container_name: ${COMPOSE_PROJECT_NAME:-l9}-neo4j
    restart: unless-stopped
    # NOTE: Do NOT use env_file for neo4j - Neo4j 5.x strict validation
    # treats ALL NEO4J_* env vars as config options and fails on unknown ones
    environment:
      NEO4J_AUTH: ${NEO4J_USER}/${NEO4J_PASSWORD}
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_dbms_security_procedures_unrestricted: apoc.*
      NEO4J_dbms_memory_heap_initial__size: 512m
      NEO4J_dbms_memory_heap_max__size: 1G
      NEO4J_dbms_memory_pagecache_size: 512m
    ports:
      - "127.0.0.1:7474:7474"
      - "127.0.0.1:7687:7687"
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p ${NEO4J_PASSWORD} 'RETURN 1' || exit 1"]
      interval: 10s
      timeout: 10s
      retries: 30
      start_period: 45s
    networks:
      - l9-network
    labels:
      - "com.l9.service=neo4j"
      - "com.l9.layer=substrate"

  # ===========================================================================
  # Redis - Task Queue, Caching, Pub/Sub
  # ===========================================================================
  redis:
    image: redis:7-alpine
    container_name: ${COMPOSE_PROJECT_NAME:-l9}-redis
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru --requirepass ${REDIS_PASSWORD:-changeme}
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-changeme}", "ping"]
      interval: 5s
      timeout: 5s
      retries: 20
    networks:
      - l9-network
    labels:
      - "com.l9.service=redis"
      - "com.l9.layer=substrate"

  # ===========================================================================
  # Prometheus - Metrics Collection
  # ===========================================================================
  prometheus:
    image: prom/prometheus:v2.48.0
    container_name: ${COMPOSE_PROJECT_NAME:-l9}-prometheus
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "127.0.0.1:9090:9090"
    volumes:
      - ./telemetry/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=30d"
      - "--web.enable-lifecycle"
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:9090/-/healthy"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - l9-network
    labels:
      - "com.l9.service=prometheus"
      - "com.l9.layer=observability"

  # ===========================================================================
  # Grafana - Visualization
  # ===========================================================================
  grafana:
    image: grafana/grafana:10.2.0
    container_name: ${COMPOSE_PROJECT_NAME:-l9}-grafana
    restart: unless-stopped
    depends_on:
      prometheus:
        condition: service_healthy
    env_file:
      - .env
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_SERVER_ROOT_URL: ${GRAFANA_ROOT_URL:-http://localhost:3000}
    ports:
      - "127.0.0.1:3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000/api/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - l9-network
    labels:
      - "com.l9.service=grafana"
      - "com.l9.layer=observability"

  # ===========================================================================
  # Jaeger - Distributed Tracing
  # ===========================================================================
  jaeger:
    image: jaegertracing/all-in-one:1.52
    container_name: ${COMPOSE_PROJECT_NAME:-l9}-jaeger
    restart: unless-stopped
    env_file:
      - .env
    environment:
      COLLECTOR_OTLP_ENABLED: "true"
    ports:
      - "127.0.0.1:16686:16686"
      - "127.0.0.1:14268:14268"
      - "127.0.0.1:6831:6831/udp"
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:14269/"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - l9-network
    labels:
      - "com.l9.service=jaeger"
      - "com.l9.layer=observability"

volumes:
  postgres_data:
    name: ${COMPOSE_PROJECT_NAME:-l9}-postgres-data
  redis_data:
    name: ${COMPOSE_PROJECT_NAME:-l9}-redis-data
  neo4j_data:
    name: ${COMPOSE_PROJECT_NAME:-l9}-neo4j-data
  neo4j_logs:
    name: ${COMPOSE_PROJECT_NAME:-l9}-neo4j-logs
  prometheus_data:
    name: ${COMPOSE_PROJECT_NAME:-l9}-prometheus-data
  grafana_data:
    name: ${COMPOSE_PROJECT_NAME:-l9}-grafana-data

networks:
  l9-network:
    driver: bridge
    name: ${COMPOSE_PROJECT_NAME:-l9}-network

# tags: ["api-config", "configuration", "docker-compose.yml", "openai", "operations", "redis-config", "utility"]
# keywords: ["compose", "docker", "networks", "services", "volumes"]
# last_modified: "2026-01-31T22:53:39Z"
# ============================================================================


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
E4. DOCKERFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Found: /opt/l9/Dockerfile
# =============================================================================
# L9 API Dockerfile - PRODUCTION & DEVELOPMENT
# =============================================================================
# Version: 4.0.0
# Created: 2026-01-31
# Purpose: Consolidated Dockerfile for L9 API with multi-stage builds
#
# STAGES:
#   - base: Common dependencies and user setup
#   - development: Hot-reload friendly, includes dev tools
#   - production: Optimized, immutable, security-hardened
#
# USAGE:
#   Development:
#     docker build --target development -t l9-api:dev .
#
#   Production:
#     docker build --target production \
#       --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
#       --build-arg VCS_REF=$(git rev-parse --short HEAD) \
#       --build-arg VERSION=4.0.0 \
#       -t l9-api:4.0.0 .
# =============================================================================

# =============================================================================
# BASE STAGE - Common dependencies
# =============================================================================
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    L9_CONTAINER_ENV=true

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 l9user && \
    mkdir -p /app/data/.l9/gmail/attachments && \
    chown -R l9user:l9user /app

# =============================================================================
# DEVELOPMENT STAGE - Hot-reload friendly
# =============================================================================
FROM base AS development

# Copy requirements first (layer caching optimization)
COPY requirements-docker.txt /app/

# Install Python dependencies (includes dev tools)
# NOTE: Install CPU-only PyTorch FIRST to avoid 3GB+ CUDA dependencies
# sentence-transformers depends on torch, but we don't need GPU support
RUN python -m pip install -U pip setuptools wheel && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements-docker.txt

# Copy application code (will be overridden by volume mounts in dev)
COPY --chown=l9user:l9user . /app/

USER l9user

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# PRODUCTION STAGE - Immutable, optimized
# =============================================================================
FROM base AS production

# Build arguments for image metadata
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=4.0.0

# Image metadata (OCI standard)
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.authors="QuantumAI Partners" \
      org.opencontainers.image.url="https://github.com/cryptoxdog/L9" \
      org.opencontainers.image.source="https://github.com/cryptoxdog/L9" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.title="L9 API" \
      org.opencontainers.image.description="L9 Secure AI OS - Main API Server" \
      com.l9.component="api" \
      com.l9.layer="application"

# Copy requirements first (layer caching optimization)
COPY requirements-docker.txt /app/

# Install Python dependencies (production only, no dev tools)
# NOTE: Install CPU-only PyTorch FIRST to avoid 3GB+ CUDA dependencies
# sentence-transformers depends on torch, but we don't need GPU support
RUN python -m pip install -U pip setuptools wheel && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements-docker.txt && \
    pip cache purge

# Copy application code
COPY --chown=l9user:l9user . /app/

# Validation: Ensure critical environment variables are set at runtime
# (We check files exist here, actual secret validation happens in healthcheck)
RUN test -f /app/api/server.py || (echo "ERROR: api/server.py not found" && exit 1) && \
    test -f /app/requirements-docker.txt || (echo "ERROR: requirements-docker.txt not found" && exit 1)

USER l9user

EXPOSE 8000

# Production healthcheck (stricter timing)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command (no --reload)
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", "--loop", "uvloop", "--log-level", "info"]


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
E5. .ENV (SANITIZED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# =<REDACTED>
# L9 DOCKER/VPS Environment (.env.vps)
# For Docker Compose on VPS - uses service DNS names (NOT localhost!)
#
# ⚠️  CRITICAL: NO INLINE COMMENTS ALLOWED
#     Pydantic-settings parses entire line as value
# =<REDACTED>

# -----------------------------------------------------------------------------
# Database (use container service names, NOT localhost/127.0.0.1)
# -----------------------------------------------------------------------------
POSTGRES_USER=<REDACTED>
POSTGRES_PASSWORD=<REDACTED>
POSTGRES_DB=<REDACTED>
MEMORY_DSN=<REDACTED>
DATABASE_URL=<REDACTED>

# -----------------------------------------------------------------------------
# API Keys
# -----------------------------------------------------------------------------
L9_EXECUTOR_API_KEY=<REDACTED>
L9_API_KEY=<REDACTED>
OPENAI_API_KEY=<REDACTED>
PERPLEXITY_API_KEY=<REDACTED>
GOOGLE_CALENDAR_API_KEY=<REDACTED>
GMAIL_API_KEY=<REDACTED>
GPG_KEY=<REDACTED>
L9_API_URL=<REDACTED>
# -----------------------------------------------------------------------------
# Neo4j Graph Database (use container name)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
E6. L9-API CONTAINER LOGS (last 30)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Error response from daemon: No such container: l9-api
No l9-api container


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F1. POSTGRESQL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ PostgreSQL running in Docker
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*          


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F2. POSTGRESQL DATABASES (via Docker)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cannot list databases


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F3. L9_MEMORY TABLES (via Docker)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cannot query tables


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F4. REDIS STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Redis running in Docker
NOAUTH Authentication required.



━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F5. NEO4J STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Neo4j running in Docker


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
G1. PYTHON/UVICORN PROCESSES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
root         815  0.0  0.1 109656 10624 ?        Ssl  Jan22   0:00 /usr/bin/python3 /usr/share/unattended-upgrades/unattended-upgrade-shutdown --wait-for-signal
1000     3895175  0.1  0.3  39068 29880 ?        Ss   08:45   0:01 /usr/local/bin/python3.12 /usr/local/bin/uvicorn mcp_memory.src.main:app --host 0.0.0.0 --port 9002 --workers 2 --loop uvloop --log-level info
1000     3895250  0.0  0.2  21124 17052 ?        S    08:45   0:00 /usr/local/bin/python3.12 -B -c from multiprocessing.resource_tracker import main;main(6)
1000     3895251  0.4  1.6 699848 128492 ?       Sl   08:45   0:03 /usr/local/bin/python3.12 -B -c from multiprocessing.spawn import spawn_main; spawn_main(tracker_fd=7, pipe_handle=9) --multiprocessing-fork
1000     3895252  0.4  1.6 699844 128540 ?       Sl   08:45   0:03 /usr/local/bin/python3.12 -B -c from multiprocessing.spawn import spawn_main; spawn_main(tracker_fd=7, pipe_handle=13) --multiprocessing-fork
1000     3895313  0.1  0.3  39464 30564 ?        Ss   08:45   0:01 /usr/local/bin/python /usr/local/bin/uvicorn api.server:app --host 0.0.0.0 --port 8000 --workers 4 --loop uvloop --log-level info
1000     3895508  0.0  0.2  21164 17232 ?        S    08:45   0:00 /usr/local/bin/python -B -c from multiprocessing.resource_tracker import main;main(6)
1000     3895510  2.7  7.1 1734260 570460 ?      Sl   08:45   0:21 /usr/local/bin/python -B -c from multiprocessing.spawn import spawn_main; spawn_main(tracker_fd=7, pipe_handle=9) --multiprocessing-fork
1000     3895512  2.7  7.1 1733948 570904 ?      Sl   08:45   0:21 /usr/local/bin/python -B -c from multiprocessing.spawn import spawn_main; spawn_main(tracker_fd=7, pipe_handle=13) --multiprocessing-fork
1000     3895515  2.6  7.2 1733924 571584 ?      Sl   08:45   0:20 /usr/local/bin/python -B -c from multiprocessing.spawn import spawn_main; spawn_main(tracker_fd=7, pipe_handle=17) --multiprocessing-fork
1000     3895518  2.6  7.1 1733244 570752 ?      Sl   08:45   0:20 /usr/local/bin/python -B -c from multiprocessing.spawn import spawn_main; spawn_main(tracker_fd=7, pipe_handle=21) --multiprocessing-fork


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
G2. PYTHON VERSION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Python 3.12.3


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
H1. PUBLIC IP & DNS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Public IP:
2a01:4f9:c012:54f2::1
DNS resolution for l9.quantumaipartners.com:
2a06:98c1:3121::3 l9.quantumaipartners.com
2a06:98c1:3120::3 l9.quantumaipartners.com


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
H2. LOCAL HEALTH CHECK (bypass proxy)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
http://127.0.0.1:8000/health:
{"status":"ok","service":"l9-api","startup_ready":true}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
H3. PUBLIC HEALTH CHECK (through Caddy)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
https://l9.quantumaipartners.com/health:
{"status":"ok","service":"l9-api","startup_ready":true}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
H4. API ROUTES AVAILABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━



━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I1. JOURNALCTL - L9 SERVICE (last 20)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- No entries --


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I2. JOURNALCTL - CADDY ERRORS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No Caddy errors (or no permission)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
I3. DOCKER CONTAINER ERRORS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
--- l9-postgres ---
2026-02-06 08:46:45.694 UTC [180] DETAIL:  Failing row contains (56d6b905-41a4-566e-a89b-29035dd89639, seed.cross_task_graph, "{\"packet_id\":\"56d6b905-41a4-566e-a89b-29035dd89639\",\"packe..., 2026-02-06 08:46:41.66351+00, null, null, null, {}, {}, null, shared, 0.5, 0, null, null, 0, 1, f, null, complete, null, null, null, df03157b-be82-40a3-a035-6a0d304a63c4, null, null).
2026-02-06 08:47:24.289 UTC [267] ERROR:  relation "packets" does not exist at character 38
2026-02-06 08:47:31.172 UTC [290] ERROR:  relation "packets" does not exist at character 34
2026-02-06 08:52:12.607 UTC [774] ERROR:  relation "packets" does not exist at character 38
2026-02-06 08:52:19.631 UTC [788] ERROR:  relation "packets" does not exist at character 34
--- l9-redis ---
No errors
--- l9-neo4j ---
2026-02-06 08:47:24.440+0000 WARN  Failed authentication attempt for 'neo4j' from 172.18.0.1
2026-02-06 08:47:31.194+0000 WARN  Failed authentication attempt for 'neo4j' from 172.18.0.1
2026-02-06 08:52:12.644+0000 WARN  Failed authentication attempt for 'neo4j' from 172.18.0.1
2026-02-06 08:52:19.645+0000 WARN  Failed authentication attempt for 'neo4j' from 172.18.0.1
2026-02-06 08:54:38.824+0000 WARN  [bolt-100] The client is unauthorized due to authentication failure.


╔════════════════════════════════════════════════════════════════╗
║                     MRI DIAGNOSTIC COMPLETE                     ║
╚════════════════════════════════════════════════════════════════╝

Quick Status:
─────────────
✗ Reverse Proxy: NONE RUNNING
✓ Docker: Running
✓ L9 API: Healthy
✓ PostgreSQL: Listening
✓ Redis: Listening
✓ Neo4j: Listening
✓ Public HTTPS: Accessible

Diagnostic completed at: 2026-02-06T08:58:55+00:00
