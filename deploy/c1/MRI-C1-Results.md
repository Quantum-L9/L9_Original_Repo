═══════════════════════════════════════════════════════════════
SECTION 1: INFRASTRUCTURE BASELINE
═══════════════════════════════════════════════════════════════

[1.1] SYSTEM RESOURCES
─────────────────────
               total        used        free      shared  buff/cache   available
Mem:           7.6Gi       1.6Gi       3.5Gi        20Mi       2.7Gi       5.9Gi
Swap:             0B          0B          0B

Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       150G  126G   18G  88% /
/dev/sda1       150G  126G   18G  88% /

 01:26:11 up 14 days,  5:03,  1 user,  load average: 0.16, 0.30, 0.39

[1.2] DOCKER ENGINE
───────────────────
 Server Version: 29.2.0
 Storage Driver: overlay2
 CPUs: 4
 Total Memory: 7.564GiB
 Docker Root Dir: /var/lib/docker

[1.3] CONFIGURATION FILES
─────────────────────────
-rw-r--r-- 1 root root 11647 Feb  2 20:12 docker-compose.prod.yml
-rw-r--r-- 1 root root  7986 Feb  1 04:28 docker-compose.yml
-rw-r--r-- 1 root root  4345 Feb  6 01:21 .env
-rw-r--r-- 1 root root  6795 Feb  2 18:29 .env.bak2
-rw-r--r-- 1 root root  5047 Jan 24 22:53 .env.example

Git commit: 25214f88
Git branch: main

═══════════════════════════════════════════════════════════════
SECTION 2: CONTAINER STATUS
═══════════════════════════════════════════════════════════════

[2.1] ALL CONTAINERS
────────────────────
NAME      IMAGE     COMMAND   SERVICE   CREATED   STATUS    PORTS

[2.2] CONTAINER DETAILS (restarts, created, status)
────────────────────────────────────────────────────
NAMES     STATUS    PORTS

[2.3] IMAGES IN USE
───────────────────
ghcr.io/cryptoxdog/l9-api          4.1.0         1.75GB    3 days ago
ghcr.io/cryptoxdog/l9-mcp-memory   4.1.0         434MB     3 days ago
redis                              7-alpine      41.4MB    8 days ago
neo4j                              5-community   555MB     13 days ago

═══════════════════════════════════════════════════════════════
SECTION 3: SERVICE HEALTH CHECKS
═══════════════════════════════════════════════════════════════

[3.1] L9 API HEALTH
───────────────────
❌ API not responding

[3.2] POSTGRESQL HEALTH
───────────────────────
❌ PostgreSQL not ready
(query failed)

[3.3] NEO4J HEALTH
──────────────────
❌ Neo4j browser not responding
❌ Cypher query failed

[3.4] REDIS HEALTH
──────────────────
❌ Redis not responding
(memory info N/A)

[3.5] MCP MEMORY HEALTH
───────────────────────
⚠️ MCP Memory not responding (may be expected)

═══════════════════════════════════════════════════════════════
SECTION 4: NETWORK & PORTS
═══════════════════════════════════════════════════════════════

[4.1] LISTENING PORTS
─────────────────────
State  Recv-Q Send-Q Local Address:Port Peer Address:PortProcess                                                    
LISTEN 0      4096      127.0.0.54:53        0.0.0.0:*    users:(("systemd-resolve",pid=2660798,fd=17))             
LISTEN 0      4096   127.0.0.53%lo:53        0.0.0.0:*    users:(("systemd-resolve",pid=2660798,fd=15))             
LISTEN 0      4096         0.0.0.0:22        0.0.0.0:*    users:(("sshd",pid=2660781,fd=3),("systemd",pid=1,fd=218))
LISTEN 0      4096            [::]:22           [::]:*    users:(("sshd",pid=2660781,fd=4),("systemd",pid=1,fd=219))

[4.2] DOCKER NETWORKS
─────────────────────
NETWORK ID     NAME      DRIVER    SCOPE

(network inspect failed)

═══════════════════════════════════════════════════════════════
SECTION 5: LOGS & ERRORS (last 5 min)
═══════════════════════════════════════════════════════════════

[5.1] L9 API ERRORS
───────────────────

[5.2] POSTGRESQL ERRORS
───────────────────────

[5.3] NEO4J ERRORS
──────────────────

[5.4] REDIS ERRORS
──────────────────

[5.5] BOOTSTRAP STATUS
──────────────────────
NAME      IMAGE     COMMAND   SERVICE   CREATED   STATUS    PORTS

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
l9-neo4j-logs: 5.6M
l9-neo4j-logs-prod: 112.0K
l9-postgres-data: 113.7G
l9-postgres-data-prod: 67.8M
l9-prometheus-data: 58.7M
l9-prometheus-data-prod: 1.3M
l9-redis-data: 92.0K
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
❌ http://127.0.0.1:8000/health (000000)
❌ http://127.0.0.1:8000/api/v1/status (000000)
❌ http://127.0.0.1:8000/docs (000000)
❌ http://127.0.0.1:8000/openapi.json (000000)

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

# -----------------------------------------------------------------------------
# Database (use container service names, NOT localhost/127.0.0.1)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=***REDACTED***
POSTGRES_DB=l9_memory
MEMORY_DSN=postgresql://postgres:***@l9-postgres:5432/l9_memory
DATABASE_URL=postgresql://postgres:***@l9-postgres:5432/l9_memory
# API Keys
L9_EXECUTOR_API_KEY=***REDACTED***
L9_API_KEY=***REDACTED***
OPENAI_API_KEY=***REDACTED***
PERPLEXITY_API_KEY=***REDACTED***
GOOGLE_CALENDAR_API_KEY=***REDACTED***
GMAIL_API_KEY=***REDACTED***
GPG_KEY=***REDACTED***
L9_API_URL=http://mcp.quantumaipartners.com:30080
# Neo4j Graph Database (use container name)
NEO4J_URL=bolt://neo4j:7687
NEO4J_URI=${NEO4J_URL}
NEO4J_USER=neo4j
NEO4J_PASSWORD=***REDACTED***
# Redis (use container name)
REDIS_HOST=localhost

═══════════════════════════════════════════════════════════════
SECTION 9: MRI SUMMARY
═══════════════════════════════════════════════════════════════

Timestamp: 2026-02-06 01:26:22 UTC
Hostname: C1
Git commit: 25214f88

SERVICE STATUS SUMMARY:
───────────────────────
  L9 API:     ❌
  PostgreSQL: ❌
  Neo4j:      ❌
  Redis:      ❌

╔═══════════════════════════════════════════════════════════════╗
║  ❌ MRI FAILED - Check sections above for issues             ║
╚═══════════════════════════════════════════════════════════════╝