═══════════════════════════════════════════════════════════════
SECTION 1: INFRASTRUCTURE BASELINE
═══════════════════════════════════════════════════════════════

[1.1] SYSTEM RESOURCES
─────────────────────
               total        used        free      shared  buff/cache   available
Mem:           7.6Gi       4.9Gi       409Mi        47Mi       2.6Gi       2.7Gi
Swap:             0B          0B          0B

Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       150G   18G  127G  13% /
/dev/sda1       150G   18G  127G  13% /

 08:47:23 up 14 days, 12:24,  1 user,  load average: 2.16, 1.66, 1.16

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
NAME                 IMAGE                                    COMMAND                  SERVICE         CREATED              STATUS                          PORTS
l9-bootstrap         ghcr.io/cryptoxdog/l9-api:4.1.0          "python -m bootstrap"    l9-bootstrap    About a minute ago   Exited (0) About a minute ago   
l9-grafana           grafana/grafana:10.2.0                   "/run.sh"                grafana         About a minute ago   Up About a minute (healthy)     127.0.0.1:3000->3000/tcp
l9-jaeger            jaegertracing/all-in-one:1.52            "/go/bin/all-in-one-…"   jaeger          About a minute ago   Up About a minute (healthy)     4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-l9-api-1          ghcr.io/cryptoxdog/l9-api:4.1.0          "uvicorn api.server:…"   l9-api          About a minute ago   Up About a minute (unhealthy)   127.0.0.1:8000->8000/tcp
l9-l9-mcp-memory-1   ghcr.io/cryptoxdog/l9-mcp-memory:4.1.0   "uvicorn mcp_memory.…"   l9-mcp-memory   About a minute ago   Up About a minute (healthy)     127.0.0.1:9002->9002/tcp
l9-neo4j             neo4j:5-community                        "tini -g -- /startup…"   neo4j           About a minute ago   Up About a minute (healthy)     127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-nginx-1           nginx:alpine                             "/docker-entrypoint.…"   nginx           About a minute ago   Up About a minute               0.0.0.0:80->80/tcp, 0.0.0.0:30379->30379/tcp, 0.0.0.0:30432->30432/tcp, 0.0.0.0:30474->30474/tcp, 0.0.0.0:30687->30687/tcp
l9-postgres          pgvector/pgvector:pg16                   "docker-entrypoint.s…"   l9-postgres     About a minute ago   Up About a minute (healthy)     127.0.0.1:5432->5432/tcp
l9-prometheus        prom/prometheus:v2.48.0                  "/bin/prometheus --c…"   prometheus      About a minute ago   Up About a minute (healthy)     127.0.0.1:9090->9090/tcp
l9-redis             redis:7-alpine                           "docker-entrypoint.s…"   redis           About a minute ago   Up About a minute (healthy)     127.0.0.1:6379->6379/tcp

[2.2] CONTAINER DETAILS (restarts, created, status)
────────────────────────────────────────────────────
NAMES                STATUS                          PORTS
l9-nginx-1           Up About a minute               0.0.0.0:80->80/tcp, 0.0.0.0:30379->30379/tcp, 0.0.0.0:30432->30432/tcp, 0.0.0.0:30474->30474/tcp, 0.0.0.0:30687->30687/tcp
l9-l9-api-1          Up About a minute (unhealthy)   127.0.0.1:8000->8000/tcp
l9-l9-mcp-memory-1   Up About a minute (healthy)     127.0.0.1:9002->9002/tcp
l9-bootstrap         Exited (0) About a minute ago   
l9-grafana           Up About a minute (healthy)     127.0.0.1:3000->3000/tcp
l9-postgres          Up About a minute (healthy)     127.0.0.1:5432->5432/tcp
l9-neo4j             Up About a minute (healthy)     127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-jaeger            Up About a minute (healthy)     4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-prometheus        Up About a minute (healthy)     127.0.0.1:9090->9090/tcp
l9-redis             Up About a minute (healthy)     127.0.0.1:6379->6379/tcp

[2.3] IMAGES IN USE
───────────────────
ghcr.io/cryptoxdog/l9-api          4.1.0         1.75GB    2 minutes ago
ghcr.io/cryptoxdog/l9-mcp-memory   4.1.0         434MB     2 minutes ago
redis                              7-alpine      41.4MB    9 days ago
neo4j                              5-community   555MB     13 days ago

═══════════════════════════════════════════════════════════════
SECTION 3: SERVICE HEALTH CHECKS
═══════════════════════════════════════════════════════════════

[3.1] L9 API HEALTH
───────────────────
❌ API not responding

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
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "Semantic enrichment failed: Embedding request failed after 3 retries: Error code: 404 - {'error': {'message': 'The model `text-embedding-3-smal` does not exist or you do not have access to it.', 'type': 'invalid_request_error', 'param': None, 'code': 'model_not_found'}}", "event": "enrichment_dag_tier_1_failed", "logger": "memory.enrichment_dag", "level": "warning", "timestamp": "2026-02-06T08:46:43.738039Z"}
l9-api-1  | {"operation": "embed_text", "attempt": 1, "max_retries": 3, "error": "Error code: 404 - {'error': {'message': 'The model `text-embedding-3-smal` does not exist or you do not have access to it.', 'type': 'invalid_request_error', 'param': None, 'code': 'model_not_found'}}", "delay": 0.587, "event": "Embedding request failed, retrying", "logger": "memory.substrate_semantic", "level": "warning", "timestamp": "2026-02-06T08:46:43.831789Z"}
l9-api-1  | {"operation": "embed_text", "attempt": 2, "max_retries": 3, "error": "Error code: 404 - {'error': {'message': 'The model `text-embedding-3-smal` does not exist or you do not have access to it.', 'type': 'invalid_request_error', 'param': None, 'code': 'model_not_found'}}", "delay": 1.07, "event": "Embedding request failed, retrying", "logger": "memory.substrate_semantic", "level": "warning", "timestamp": "2026-02-06T08:46:44.557382Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "Embedding request failed after 3 retries: Error code: 404 - {'error': {'message': 'The model `text-embedding-3-smal` does not exist or you do not have access to it.', 'type': 'invalid_request_error', 'param': None, 'code': 'model_not_found'}}", "event": "enrichment_tier_2_failed", "logger": "memory.enrichment_dag", "level": "error", "timestamp": "2026-02-06T08:46:45.693117Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "Embedding request failed after 3 retries: Error code: 404 - {'error': {'message': 'The model `text-embedding-3-smal` does not exist or you do not have access to it.', 'type': 'invalid_request_error', 'param': None, 'code': 'model_not_found'}}", "event": "enrichment_dag_tier_2_failed", "logger": "memory.enrichment_dag", "level": "warning", "timestamp": "2026-02-06T08:46:45.693414Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "new row for relation \"packet_store\" violates check constraint \"packet_store_project_id_not_null\"\nDETAIL:  Failing row contains (56d6b905-41a4-566e-a89b-29035dd89639, seed.cross_task_graph, \"{\\\"packet_id\\\":\\\"56d6b905-41a4-566e-a89b-29035dd89639\\\",\\\"packe..., 2026-02-06 08:46:41.66351+00, null, null, null, {}, {}, null, shared, 0.5, 0, null, null, 0, 1, f, null, complete, null, null, null, df03157b-be82-40a3-a035-6a0d304a63c4, null, null).", "event": "enrichment_tier_3_failed", "logger": "memory.enrichment_dag", "level": "error", "timestamp": "2026-02-06T08:46:45.695793Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "new row for relation \"packet_store\" violates check constraint \"packet_store_project_id_not_null\"\nDETAIL:  Failing row contains (56d6b905-41a4-566e-a89b-29035dd89639, seed.cross_task_graph, \"{\\\"packet_id\\\":\\\"56d6b905-41a4-566e-a89b-29035dd89639\\\",\\\"packe..., 2026-02-06 08:46:41.66351+00, null, null, null, {}, {}, null, shared, 0.5, 0, null, null, 0, 1, f, null, complete, null, null, null, df03157b-be82-40a3-a035-6a0d304a63c4, null, null).", "event": "enrichment_dag_tier_3_failed", "logger": "memory.enrichment_dag", "level": "warning", "timestamp": "2026-02-06T08:46:45.696033Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "'NoneType' object has no attribute 'push'", "event": "enrichment_dag_dlq_push_failed", "logger": "memory.enrichment_dag", "level": "error", "timestamp": "2026-02-06T08:46:45.696279Z"}
l9-api-1  | {"event": "Packet 56d6b905-41a4-566e-a89b-29035dd89639 processed: status=error, tables=[]", "logger": "memory.substrate_service", "level": "info", "timestamp": "2026-02-06T08:46:45.698286Z"}
l9-api-1  | {"event": "Failed to write packet: All enrichment tiers failed; pushed to DLQ", "logger": "world_model.seed_loader", "level": "error", "timestamp": "2026-02-06T08:46:45.698442Z"}
l9-api-1  | {"event": "Ingestion failed: Target entity packet_envelope not found", "logger": "world_model.knowledge_ingestor", "level": "error", "timestamp": "2026-02-06T08:46:45.726519Z"}
l9-api-1  | {"event": "Ingestion failed: Target entity memory_substrate not found", "logger": "world_model.knowledge_ingestor", "level": "error", "timestamp": "2026-02-06T08:46:45.727099Z"}
l9-api-1  | {"loaded_count": 10, "hash_count": 10, "error_count": 0, "event": "kernel_loader.phase1_complete", "logger": "core.kernels.kernelloader", "level": "info", "timestamp": "2026-02-06T08:47:01.217942Z"}
l9-api-1  | {"loaded_count": 10, "hash_count": 10, "error_count": 0, "event": "kernel_loader.phase1_complete", "logger": "core.kernels.kernelloader", "level": "info", "timestamp": "2026-02-06T08:47:02.697050Z"}
l9-api-1  | {"loaded_count": 10, "hash_count": 10, "error_count": 0, "event": "kernel_loader.phase1_complete", "logger": "core.kernels.kernelloader", "level": "info", "timestamp": "2026-02-06T08:47:02.947540Z"}
l9-api-1  | {"event": "Error in GMP worker loop: TaskQueue: Redis unavailable; execution blocked", "logger": "runtime.gmp_worker", "level": "error", "timestamp": "2026-02-06T08:47:04.569609Z", "exception": "Traceback (most recent call last):\n  File \"/app/runtime/gmp_worker.py\", line 111, in _worker_loop\n    task = await GMP_QUEUE.dequeue()\n           ^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/app/runtime/task_queue.py\", line 300, in dequeue\n    await self._ensure_redis()\n  File \"/app/runtime/task_queue.py\", line 234, in _ensure_redis\n    raise RuntimeError(\"TaskQueue: Redis unavailable; execution blocked\")\nRuntimeError: TaskQueue: Redis unavailable; execution blocked"}
l9-api-1  | {"event": "Error in GMP worker loop: TaskQueue: Redis unavailable; execution blocked", "logger": "runtime.gmp_worker", "level": "error", "timestamp": "2026-02-06T08:47:04.587888Z", "exception": "Traceback (most recent call last):\n  File \"/app/runtime/gmp_worker.py\", line 111, in _worker_loop\n    task = await GMP_QUEUE.dequeue()\n           ^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/app/runtime/task_queue.py\", line 300, in dequeue\n    await self._ensure_redis()\n  File \"/app/runtime/task_queue.py\", line 234, in _ensure_redis\n    raise RuntimeError(\"TaskQueue: Redis unavailable; execution blocked\")\nRuntimeError: TaskQueue: Redis unavailable; execution blocked"}
l9-api-1  | {"event": "Error in GMP worker loop: TaskQueue: Redis unavailable; execution blocked", "logger": "runtime.gmp_worker", "level": "error", "timestamp": "2026-02-06T08:47:04.595712Z", "exception": "Traceback (most recent call last):\n  File \"/app/runtime/gmp_worker.py\", line 111, in _worker_loop\n    task = await GMP_QUEUE.dequeue()\n           ^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/app/runtime/task_queue.py\", line 300, in dequeue\n    await self._ensure_redis()\n  File \"/app/runtime/task_queue.py\", line 234, in _ensure_redis\n    raise RuntimeError(\"TaskQueue: Redis unavailable; execution blocked\")\nRuntimeError: TaskQueue: Redis unavailable; execution blocked"}
l9-api-1  | {"loaded_count": 10, "hash_count": 10, "error_count": 0, "event": "kernel_loader.phase1_complete", "logger": "core.kernels.kernelloader", "level": "info", "timestamp": "2026-02-06T08:47:04.948527Z"}
l9-api-1  | {"event": "Error in GMP worker loop: TaskQueue: Redis unavailable; execution blocked", "logger": "runtime.gmp_worker", "level": "error", "timestamp": "2026-02-06T08:47:06.535045Z", "exception": "Traceback (most recent call last):\n  File \"/app/runtime/gmp_worker.py\", line 111, in _worker_loop\n    task = await GMP_QUEUE.dequeue()\n           ^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/app/runtime/task_queue.py\", line 300, in dequeue\n    await self._ensure_redis()\n  File \"/app/runtime/task_queue.py\", line 234, in _ensure_redis\n    raise RuntimeError(\"TaskQueue: Redis unavailable; execution blocked\")\nRuntimeError: TaskQueue: Redis unavailable; execution blocked"}

[5.2] POSTGRESQL ERRORS
───────────────────────
l9-postgres  | 2026-02-06 08:46:35.635 UTC [161] ERROR:  new row for relation "packet_store" violates check constraint "packet_store_project_id_not_null"
l9-postgres  | 2026-02-06 08:46:37.516 UTC [170] ERROR:  new row for relation "packet_store" violates check constraint "packet_store_project_id_not_null"
l9-postgres  | 2026-02-06 08:46:37.641 UTC [180] ERROR:  new row for relation "packet_store" violates check constraint "packet_store_project_id_not_null"
l9-postgres  | 2026-02-06 08:46:39.465 UTC [161] ERROR:  new row for relation "packet_store" violates check constraint "packet_store_project_id_not_null"
l9-postgres  | 2026-02-06 08:46:39.516 UTC [171] ERROR:  new row for relation "packet_store" violates check constraint "packet_store_project_id_not_null"
l9-postgres  | 2026-02-06 08:46:41.439 UTC [170] ERROR:  new row for relation "packet_store" violates check constraint "packet_store_project_id_not_null"
l9-postgres  | 2026-02-06 08:46:41.621 UTC [180] ERROR:  new row for relation "packet_store" violates check constraint "packet_store_project_id_not_null"
l9-postgres  | 2026-02-06 08:46:43.411 UTC [171] ERROR:  new row for relation "packet_store" violates check constraint "packet_store_project_id_not_null"
l9-postgres  | 2026-02-06 08:46:45.694 UTC [180] ERROR:  new row for relation "packet_store" violates check constraint "packet_store_project_id_not_null"
l9-postgres  | 2026-02-06 08:47:24.289 UTC [267] ERROR:  relation "packets" does not exist at character 38

[5.3] NEO4J ERRORS
──────────────────

[5.4] REDIS ERRORS
──────────────────

[5.5] BOOTSTRAP STATUS
──────────────────────
NAME                 IMAGE                                    COMMAND                  SERVICE         CREATED              STATUS                          PORTS
l9-bootstrap         ghcr.io/cryptoxdog/l9-api:4.1.0          "python -m bootstrap"    l9-bootstrap    About a minute ago   Exited (0) About a minute ago   
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
l9-prometheus-data: 53.9M
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

Timestamp: 2026-02-06 08:47:31 UTC
Hostname: C1
Git commit: 20282955

SERVICE STATUS SUMMARY:
───────────────────────
  L9 API:     ❌
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
service "l9-mcp-memory" depends on undefined service "l9-postgres": invalid compose project
SNIPER ERROR LOCATOR ->
service "l9-api" depends on undefined service "neo4j": invalid compose project
