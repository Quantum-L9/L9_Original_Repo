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
local     l9_grafana_data
local     l9_neo4j_data
local     l9_neo4j_logs
local     l9_postgres_data
local     l9_prometheus_data
local     l9_redis_data
=== SYSTEM INFO ===
 Static hostname: C1
       Icon name: computer-vm
         Chassis: vm 🖴
      Machine ID: 7343fe7e7d2241538f74956b71567e2f
         Boot ID: 0a314a6ea7cb4b2195293270bfd229e5
  Virtualization: kvm
Operating System: Ubuntu 24.04.3 LTS              
          Kernel: Linux 6.8.0-90-generic
    Architecture: x86-64
 Hardware Vendor: Hetzner
  Hardware Model: vServer
Firmware Version: 20171111
   Firmware Date: Sat 2017-11-11
    Firmware Age: 8y 2month 3w 1d                 
----
PRETTY_NAME="Ubuntu 24.04.3 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04.3 LTS (Noble Numbat)"
VERSION_CODENAME=noble
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=noble
LOGO=ubuntu-logo
----
               total        used        free      shared  buff/cache   available
Mem:           7.6Gi       4.5Gi       210Mi        45Mi       3.2Gi       3.1Gi
Swap:             0B          0B          0B
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       150G   37G  107G  26% /
=== DOCKER STATE ===
Client: Docker Engine - Community
 Version:           29.2.0
 API version:       1.53
 Go version:        go1.25.6
 Git commit:        0b9d198
 Built:             Mon Jan 26 19:27:07 2026
 OS/Arch:           linux/amd64
 Context:           default

Server: Docker Engine - Community
 Engine:
  Version:          29.2.0
  API version:      1.53 (minimum version 1.44)
  Go version:       go1.25.6
  Git commit:       9c62384
  Built:            Mon Jan 26 19:27:07 2026
  OS/Arch:          linux/amd64
  Experimental:     false
 containerd:
  Version:          v2.2.1
  GitCommit:        dea7da592f5d1d2b7755e3a161be07f43fad8f75
 runc:
  Version:          1.3.4
  GitCommit:        v1.3.4-0-gd6d73eb8
 docker-init:
  Version:          0.19.0
  GitCommit:        de40ad0
----
CONTAINER ID   IMAGE                                    COMMAND                  CREATED          STATUS                     PORTS                                                                                                                                                NAMES
caee3e6371cc   ghcr.io/cryptoxdog/l9-api:4.1.0          "uvicorn api.server:…"   17 minutes ago   Up 3 minutes (unhealthy)   127.0.0.1:8000->8000/tcp                                                                                                                             l9-l9-api-1
8f5005f727a2   pgvector/pgvector:pg16                   "docker-entrypoint.s…"   18 minutes ago   Up 18 minutes (healthy)    127.0.0.1:5432->5432/tcp                                                                                                                             l9-postgres
ac6486dce67b   redis:7-alpine                           "docker-entrypoint.s…"   18 minutes ago   Up 18 minutes (healthy)    127.0.0.1:6379->6379/tcp                                                                                                                             l9-redis
8706cb5c653d   ghcr.io/cryptoxdog/l9-mcp-memory:4.1.0   "uvicorn mcp_memory.…"   2 hours ago      Up 2 hours (healthy)       127.0.0.1:9002->9002/tcp                                                                                                                             l9-l9-mcp-memory-1
b087aade46f4   grafana/grafana:10.2.0                   "/run.sh"                2 hours ago      Up 2 hours (healthy)       127.0.0.1:3000->3000/tcp                                                                                                                             l9-grafana
64fdb56dc23f   prom/prometheus:v2.48.0                  "/bin/prometheus --c…"   2 hours ago      Up 2 hours (healthy)       127.0.0.1:9090->9090/tcp                                                                                                                             l9-prometheus
178d37385a93   neo4j:5-community                        "tini -g -- /startup…"   2 hours ago      Up 2 hours (healthy)       127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp                                                                                         l9-neo4j
01c9901588c5   jaegertracing/all-in-one:1.52            "/go/bin/all-in-one-…"   2 hours ago      Up 2 hours (healthy)       4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp   l9-jaeger
----
WARNING: This output is designed for human readability. For machine-readable output, please use --format.
IMAGE                                     ID             DISK USAGE   CONTENT SIZE   EXTRA
ghcr.io/cryptoxdog/l9-api:4.1.0           efa77c70c52a       8.18GB             0B   U    
ghcr.io/cryptoxdog/l9-api:latest          a90a6f6de6ce       8.18GB             0B        
ghcr.io/cryptoxdog/l9-mcp-memory:4.1.0    fc1f4ddde6a9        434MB             0B   U    
ghcr.io/cryptoxdog/l9-mcp-memory:latest   b835559fe894        433MB             0B        
grafana/grafana:10.2.0                    2fbe6143d3ba        399MB             0B   U    
jaegertracing/all-in-one:1.52             f54c2e9a1e62         74MB             0B   U    
neo4j:5-community                         689a608bc822        555MB             0B   U    
nginx:alpine                              2a855eac5070       61.9MB             0B        
pgvector/pgvector:pg16                    68f823d56bc9        507MB             0B   U    
prom/prometheus:v2.48.0                   620d5e2a39df        247MB             0B   U    
redis:7-alpine                            e08bd8d5a677       41.4MB             0B   U    
no configuration file provided: not found
no configuration file provided: not found
no configuration file provided: not found
no configuration file provided: not found
NAMES                IMAGE                                    STATUS
l9-l9-api-1          ghcr.io/cryptoxdog/l9-api:4.1.0          Up 3 minutes (unhealthy)
l9-postgres          pgvector/pgvector:pg16                   Up 18 minutes (healthy)
l9-redis             redis:7-alpine                           Up 18 minutes (healthy)
l9-l9-mcp-memory-1   ghcr.io/cryptoxdog/l9-mcp-memory:4.1.0   Up 2 hours (healthy)
l9-grafana           grafana/grafana:10.2.0                   Up 2 hours (healthy)
l9-prometheus        prom/prometheus:v2.48.0                  Up 2 hours (healthy)
l9-neo4j             neo4j:5-community                        Up 2 hours (healthy)
l9-jaeger            jaegertracing/all-in-one:1.52            Up 2 hours (healthy)
ls: cannot access 'docker-compose*.yml': No such file or directory
cat: docker-compose.yml: No such file or directory
grep: option requires an argument -- 'A'
Usage: grep [OPTION]... PATTERNS [FILE]...
Try 'grep --help' for more information.
cat: docker-compose.prod.yml: No such file or directory
no configuration file provided: not found
grep: docker-compose*.yml: No such file or directory
no configuration file provided: not found
cat: .env: No such file or directory
open /root/docker-compose.yml: no such file or directory
curl: (56) Recv failure: Connection reset by peer
error: no such object: l9-api
root@C1:~# # Navigate to L9 repo
cd /opt/l9

# 1. Check docker-compose files exist
ls -la docker-compose*.yml

# 2. Check .env exists
ls -la .env

# 3. Check running containers
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 4. Get l9-api crash logs (CRITICAL)
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs l9-api --tail=200

# 5. Check for Python errors
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs l9-api --tail=200 | grep -i "error\|exception\|traceback\|fatal"

# 6. Test health endpoint
curl -v http://127.0.0.1:8000/health

# 7. Check if bootstrap completed successfully
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps -a | grep bootstrap

# 8. Verify .env has required vars (secrets redacted)
cat .env | sed 's/\(PASSWORD\|KEY\|SECRET\)=.*/\1=***REDACTED***/g' | head -50
-rw-r--r-- 1 root root 11647 Feb  2 20:12 docker-compose.prod.yml
-rw-r--r-- 1 root root  7986 Feb  1 04:28 docker-compose.yml
-rw-r--r-- 1 root root 4108 Feb  2 19:47 .env
NAME                 IMAGE                                    COMMAND                  SERVICE         CREATED          STATUS                    PORTS
l9-grafana           grafana/grafana:10.2.0                   "/run.sh"                grafana         2 hours ago      Up 2 hours (healthy)      127.0.0.1:3000->3000/tcp
l9-jaeger            jaegertracing/all-in-one:1.52            "/go/bin/all-in-one-…"   jaeger          2 hours ago      Up 2 hours (healthy)      4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-l9-api-1          ghcr.io/cryptoxdog/l9-api:4.1.0          "uvicorn api.server:…"   l9-api          3 minutes ago    Up 3 minutes (healthy)    127.0.0.1:8000->8000/tcp
l9-l9-mcp-memory-1   ghcr.io/cryptoxdog/l9-mcp-memory:4.1.0   "uvicorn mcp_memory.…"   l9-mcp-memory   2 hours ago      Up 2 hours (healthy)      127.0.0.1:9002->9002/tcp
l9-neo4j             neo4j:5-community                        "tini -g -- /startup…"   neo4j           2 hours ago      Up 2 hours (healthy)      127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-postgres          pgvector/pgvector:pg16                   "docker-entrypoint.s…"   l9-postgres     28 minutes ago   Up 28 minutes (healthy)   127.0.0.1:5432->5432/tcp
l9-prometheus        prom/prometheus:v2.48.0                  "/bin/prometheus --c…"   prometheus      2 hours ago      Up 2 hours (healthy)      127.0.0.1:9090->9090/tcp
l9-redis             redis:7-alpine                           "docker-entrypoint.s…"   redis           28 minutes ago   Up 28 minutes (healthy)   127.0.0.1:6379->6379/tcp
l9-api-1  | {"name": "06_worldmodel_kernel", "version": "1.0.0", "hash_prefix": "6dc335a6", "event": "Loaded kernel", "logger": "core.agents.bootstrap.phase_1_load_kernels", "level": "info", "timestamp": "2026-02-02T20:14:37.851166Z"}
l9-api-1  | {"name": "07_execution_kernel", "version": "1.0.0", "hash_prefix": "7dbefcc1", "event": "Loaded kernel", "logger": "core.agents.bootstrap.phase_1_load_kernels", "level": "info", "timestamp": "2026-02-02T20:14:37.855255Z"}
l9-api-1  | {"name": "08_safety_kernel", "version": "1.0.0", "hash_prefix": "97fa6e06", "event": "Loaded kernel", "logger": "core.agents.bootstrap.phase_1_load_kernels", "level": "info", "timestamp": "2026-02-02T20:14:37.859750Z"}
l9-api-1  | {"name": "09_developer_kernel", "version": "1.0.0", "hash_prefix": "be89fa0a", "event": "Loaded kernel", "logger": "core.agents.bootstrap.phase_1_load_kernels", "level": "info", "timestamp": "2026-02-02T20:14:37.867831Z"}
l9-api-1  | {"event": "\u2713 Memory tools registered: 2 tools", "logger": "core.tools.memory_tools", "level": "info", "timestamp": "2026-02-02T20:14:37.874575Z"}
l9-api-1  | {"event": "\u2713 Memory tools registered: 2 tools", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.874841Z"}
l9-api-1  | {"event": "Memory metrics initialized", "logger": "telemetry.memory_metrics", "level": "info", "timestamp": "2026-02-02T20:14:37.875130Z"}
l9-api-1  | {"event": "\u2713 Prometheus metrics initialized", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.875247Z"}
l9-api-1  | {"event": "\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.875385Z"}
l9-api-1  | {"event": "\u2551  Stage 3: Wiring Enterprise Modules    \u2551", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.875506Z"}
l9-api-1  | {"event": "\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.875638Z"}
l9-api-1  | {"event": "Tool audit service started", "logger": "core.tools.tool_audit", "level": "info", "timestamp": "2026-02-02T20:14:37.875821Z"}
l9-api-1  | {"event": "\u2713 ToolAuditService initialized (Postgres audit trail)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.875970Z"}
l9-api-1  | {"event": "Event-driven coordination initialized", "logger": "core.coordination.event_queue", "level": "info", "timestamp": "2026-02-02T20:14:37.876712Z"}
l9-api-1  | {"event": "\u2713 EventQueue initialized (async coordination)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.876846Z"}
l9-api-1  | {"event": "\u2713 VirtualContextManager initialized (tiered memory)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.877028Z"}
l9-api-1  | {"name": "information_retrieval", "examples": 10, "event": "Defined eval set", "logger": "core.evaluation.evaluator", "level": "info", "timestamp": "2026-02-02T20:14:37.877208Z"}
l9-api-1  | {"name": "code_analysis", "examples": 10, "event": "Defined eval set", "logger": "core.evaluation.evaluator", "level": "info", "timestamp": "2026-02-02T20:14:37.877318Z"}
l9-api-1  | {"name": "multi_tool_orchestration", "examples": 10, "event": "Defined eval set", "logger": "core.evaluation.evaluator", "level": "info", "timestamp": "2026-02-02T20:14:37.877411Z"}
l9-api-1  | {"name": "memory_operations", "examples": 10, "event": "Defined eval set", "logger": "core.evaluation.evaluator", "level": "info", "timestamp": "2026-02-02T20:14:37.877489Z"}
l9-api-1  | {"event": "\u2713 Evaluator initialized (LLM-as-judge, 4 eval sets)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.877572Z"}
l9-api-1  | {"event": "agent.executor.tool_audit_set: enabled=True", "logger": "core.agents.executor", "level": "info", "timestamp": "2026-02-02T20:14:37.877731Z"}
l9-api-1  | {"event": "\u2713 ToolAuditService wired to AgentExecutor", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.877814Z"}
l9-api-1  | {"event": "agent.executor.virtual_context_set: enabled=True", "logger": "core.agents.executor", "level": "info", "timestamp": "2026-02-02T20:14:37.877963Z"}
l9-api-1  | {"event": "\u2713 VirtualContextManager wired to AgentExecutor", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.878045Z"}
l9-api-1  | {"event": "agent.executor.event_queue_set: enabled=True", "logger": "core.agents.executor", "level": "info", "timestamp": "2026-02-02T20:14:37.878159Z"}
l9-api-1  | {"name": "10_packet_protocol_kernel", "version": "1.0.0", "hash_prefix": "0cd5d4b3", "event": "Loaded kernel", "logger": "core.agents.bootstrap.phase_1_load_kernels", "level": "info", "timestamp": "2026-02-02T20:14:37.878151Z"}
l9-api-1  | {"kernel_count": 10, "event": "All kernels loaded and parsed", "logger": "core.agents.bootstrap.phase_1_load_kernels", "level": "info", "timestamp": "2026-02-02T20:14:37.878229Z"}
l9-api-1  | {"event": "\u2713 EventQueue wired to AgentExecutor", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.878231Z"}
l9-api-1  | {"event": "\u2713 Phase 1 complete (10 kernels loaded)", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.878367Z"}
l9-api-1  | {"event": "Phase 2: Instantiating agent...", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.878403Z"}
l9-api-1  | {"event": "Stage 3 module wiring complete", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.878358Z"}
l9-api-1  | {"event": "\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.878473Z"}
l9-api-1  | {"event": "\u2551  Stage 4: Memory Consolidation         \u2551", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.878602Z"}
l9-api-1  | {"event": "\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.878730Z"}
l9-api-1  | {"decay_constant": 0.05, "min_threshold": 0.1, "dry_run": false, "event": "NeuralDecayScheduler initialized", "logger": "memory.neural_decay_scheduler", "level": "info", "timestamp": "2026-02-02T20:14:37.878949Z"}
l9-api-1  | {"event": "\u2713 NeuralDecayScheduler initialized", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.879057Z"}
l9-api-1  | {"dry_run": false, "tiers": ["session", "daily", "weekly"], "event": "HierarchicalSummarizer initialized", "logger": "memory.hierarchical_summarizer", "level": "info", "timestamp": "2026-02-02T20:14:37.879206Z"}
l9-api-1  | {"agent_id": "l-cto", "instance_id": "a684b6ec-5eb8-496b-861e-008f3bb48c56", "redis_working_memory": true, "event": "Instantiated agent", "logger": "core.agents.bootstrap.phase_2_instantiate", "level": "info", "timestamp": "2026-02-02T20:14:37.879261Z"}
l9-api-1  | {"event": "\u2713 HierarchicalSummarizer initialized", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.879297Z"}
l9-api-1  | {"event": "\u2713 Phase 2 complete (instance: a684b6ec...)", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.879374Z"}
l9-api-1  | {"event": "Phase 3: Binding kernels...", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.879411Z"}
l9-api-1  | {"event": "Neo4j not available, skipping kernel binding in graph", "logger": "core.agents.bootstrap.phase_3_bind_kernels", "level": "warning", "timestamp": "2026-02-02T20:14:37.879458Z"}
l9-api-1  | {"task": "memory_consolidation", "interval_seconds": 14400, "enabled_flag": null, "event": "Background task registered", "logger": "runtime.background_tasks", "level": "info", "timestamp": "2026-02-02T20:14:37.879459Z"}
l9-api-1  | {"event": "\u2713 Phase 3 complete", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.879522Z"}
l9-api-1  | {"event": "Phase 4: Loading identity persona...", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.879550Z"}
l9-api-1  | {"event": "\u2713 MemoryConsolidationService initialized (4h cycle)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.879541Z"}
l9-api-1  | {"agent_id": "l-cto", "tried_path": "private/agents/identity/l-cto_identity.yaml", "event": "Identity YAML not found, using defaults", "logger": "core.agents.bootstrap.phase_4_load_identity", "level": "warning", "timestamp": "2026-02-02T20:14:37.879682Z"}
l9-api-1  | {"event": "\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.879666Z"}
l9-api-1  | {"event": "\u2713 Phase 4 complete", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.879787Z"}
l9-api-1  | {"event": "Phase 5: Binding tools & capabilities...", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.879837Z"}
l9-api-1  | {"event": "\u2551  Stage 5: Graph-Backed Agent State     \u2551", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.879775Z"}
l9-api-1  | {"tool_count": 4, "event": "Neo4j not available, tools bound in memory only", "logger": "core.agents.bootstrap.phase_5_bind_tools", "level": "info", "timestamp": "2026-02-02T20:14:37.879960Z"}
l9-api-1  | {"event": "\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.879922Z"}
l9-api-1  | {"event": "\u2713 Phase 5 complete", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.880067Z"}
l9-api-1  | {"event": "Phase 6: Wiring governance gates...", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.880101Z"}
l9-api-1  | {"neo4j_uri": "bolt://neo4j:7687", "l9_graph_agent_state": true, "event": "Graph agent state requested but Neo4j is unavailable; disabling graph-backed agent state for this run.", "logger": "api.server", "level": "warning", "timestamp": "2026-02-02T20:14:37.880045Z"}
l9-api-1  | {"event": "Neo4j not available, governance gates set in memory only", "logger": "core.agents.bootstrap.phase_6_wire_governance", "level": "info", "timestamp": "2026-02-02T20:14:37.880138Z"}
l9-api-1  | {"event": "\u2713 Phase 6 complete", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.880191Z"}
l9-api-1  | {"event": "Phase 7: Verifying & locking...", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.880216Z"}
l9-api-1  | {"event": "Stage 5 skipped - Neo4j unavailable (app continuing in degraded mode)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.880162Z"}
l9-api-1  | {"count": 10, "event": "\u2713 Kernels verified", "logger": "core.agents.bootstrap.phase_7_verify_and_lock", "level": "info", "timestamp": "2026-02-02T20:14:37.880249Z"}
l9-api-1  | {"designation": "l-cto", "event": "\u2713 Identity verified", "logger": "core.agents.bootstrap.phase_7_verify_and_lock", "level": "info", "timestamp": "2026-02-02T20:14:37.880279Z"}
l9-api-1  | {"agent_id": "l-cto", "signature": "ab7ccdbff14962ae...", "event": "\u2713 Agent initialized and READY", "logger": "core.agents.bootstrap.phase_7_verify_and_lock", "level": "info", "timestamp": "2026-02-02T20:14:37.880322Z"}
l9-api-1  | {"neo4j_uri": "bolt://neo4j:7687", "l9_graph_wm_sync": true, "event": "Graph-WM Sync requested but Neo4j is unavailable; disabling Graph-WM Sync for this run.", "logger": "api.server", "level": "warning", "timestamp": "2026-02-02T20:14:37.880277Z"}
l9-api-1  | {"event": "\u2713 Phase 7 complete (signature: ab7ccdbff14962ae...)", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.880403Z"}
l9-api-1  | {"event": "\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.880435Z"}
l9-api-1  | {"event": "Graph-WM Sync skipped - Neo4j unavailable (app continuing)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.880390Z"}
l9-api-1  | {"event": "\u2551  SUCCESS: l-cto initialized", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.880457Z"}
l9-api-1  | {"event": "\u2551  Instance: a684b6ec-5eb...", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.880488Z"}
l9-api-1  | {"event": "\u2551  Status: READY", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.880520Z"}
l9-api-1  | {"event": "\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d", "logger": "core.agents.bootstrap.orchestrator", "level": "info", "timestamp": "2026-02-02T20:14:37.880538Z"}
l9-api-1  | {"instance_id": "a684b6ec-5eb", "signature": "ab7ccdbff14962ae", "event": "\u2713 L-CTO Agent Bootstrap complete", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.880673Z"}
l9-api-1  | {"event": "Slack enabled but Permission Graph not available. RBAC checks will be skipped.", "logger": "api.server", "level": "warning", "timestamp": "2026-02-02T20:14:37.880731Z"}
l9-api-1  | {"event": "\u2713\u2713\u2713 L9 FULLY INITIALIZED WITH ACTIVE KERNELS \u2713\u2713\u2713", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.880768Z"}
l9-api-1  | {"event": "STARTUP VALIDATION: SessionStartup result not available", "logger": "api.server", "level": "warning", "timestamp": "2026-02-02T20:14:37.880800Z"}
l9-api-1  | {"extra": {"alert": "tool_graph_failed"}, "event": "\u274c Tool registration failed: Component 'memory_search' already registered in tool_executors. Tool graph unavailable.", "logger": "api.server", "level": "error", "timestamp": "2026-02-02T20:14:37.891814Z", "exception": "Traceback (most recent call last):\n  File \"/app/api/server.py\", line 1923, in lifespan\n    tool_count = await register_l_tools()\n                 ^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/app/core/tools/registry_adapter.py\", line 2849, in register_l_tools\n    from runtime.l_tools import TOOL_EXECUTORS\n  File \"/app/runtime/l_tools.py\", line 58, in <module>\n    @register_tool(category=\"memory\", priority=10, description=\"memory_search tool\")\n     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/app/runtime/tool_registry.py\", line 109, in decorator\n    tool_executor_registry.register_instance(\n  File \"/app/core/auto_registry.py\", line 274, in register_instance\n    raise DuplicateRegistrationError(\ncore.auto_registry.DuplicateRegistrationError: Component 'memory_search' already registered in tool_executors"}
l9-api-1  | {"event": "Registered tool: memory_search (memory_search)", "logger": "core.tools.base_registry", "level": "info", "timestamp": "2026-02-02T20:14:37.896325Z"}
l9-api-1  | {"event": "ToolPatternExtractor started (interval=6h)", "logger": "core.integration.tool_pattern_extractor", "level": "info", "timestamp": "2026-02-02T20:14:37.898210Z"}
l9-api-1  | {"event": "\u2705 UKG Phase 4: Tool Pattern Extraction started (6h interval)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.898397Z"}
l9-api-1  | {"event": "Initializing Five-Tier Observability...", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.898556Z"}
l9-api-1  | {"extra": {"sampling_rate": 0.1, "exporters": ["console", "substrate"]}, "event": "ObservabilityService initialized", "logger": "core.observability.service", "level": "info", "timestamp": "2026-02-02T20:14:37.900723Z"}
l9-api-1  | {"event": "Observability Prometheus exporter initialized", "logger": "core.observability.prometheus_exporter", "level": "info", "timestamp": "2026-02-02T20:14:37.901498Z"}
l9-api-1  | {"event": "Observability Prometheus exporter initialized", "logger": "core.observability.prometheus_exporter", "level": "info", "timestamp": "2026-02-02T20:14:37.901634Z"}
l9-api-1  | {"event": "Instrumented agent executor (start_agent_task)", "logger": "core.observability.l9_integration", "level": "info", "timestamp": "2026-02-02T20:14:37.901775Z"}
l9-api-1  | {"event": "Instrumented tool registry (dispatch_tool_call)", "logger": "core.observability.l9_integration", "level": "info", "timestamp": "2026-02-02T20:14:37.901866Z"}
l9-api-1  | {"event": "Instrumented governance engine (evaluate)", "logger": "core.observability.l9_integration", "level": "info", "timestamp": "2026-02-02T20:14:37.901967Z"}
l9-api-1  | {"event": "Instrumented memory substrate (4 methods)", "logger": "core.observability.l9_integration", "level": "info", "timestamp": "2026-02-02T20:14:37.902038Z"}
l9-api-1  | {"instrumented": {"executor": true, "tool_registry": true, "governance": true, "substrate": true}, "event": "\u2705 Five-Tier Observability initialized", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.902102Z"}
l9-api-1  | {"task": "observability_metrics", "interval_seconds": 30, "enabled_flag": null, "event": "Background task registered", "logger": "runtime.background_tasks", "level": "info", "timestamp": "2026-02-02T20:14:37.902299Z"}
l9-api-1  | {"event": "Observability metrics task registered (30s interval)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.902373Z"}
l9-api-1  | {"event": "Event queue processor started", "logger": "core.coordination.event_queue", "level": "info", "timestamp": "2026-02-02T20:14:37.903574Z"}
l9-api-1  | {"event": "Starting tool pattern extraction...", "logger": "core.integration.tool_pattern_extractor", "level": "info", "timestamp": "2026-02-02T20:14:37.903767Z"}
l9-api-1  | {"min_size": 0, "max_size": 15, "event": "Database connection pool initialized", "logger": "memory.substrate_repository", "level": "info", "timestamp": "2026-02-02T20:14:37.903981Z"}
l9-api-1  | {"event": "Registered tool: memory_write (memory_write)", "logger": "core.tools.base_registry", "level": "info", "timestamp": "2026-02-02T20:14:37.904566Z"}
l9-api-1  | {"event": "Redis connected: redis:6379/0", "logger": "runtime.redis_client", "level": "info", "timestamp": "2026-02-02T20:14:37.907468Z"}
l9-api-1  | {"cache_ttl_seconds": 300, "event": "cache_initialized_with_l9_redis", "logger": "memory.predictive_cache", "level": "info", "timestamp": "2026-02-02T20:14:37.907670Z"}
l9-api-1  | {"event": "warming_service_initialized", "logger": "memory.warming_service", "level": "info", "timestamp": "2026-02-02T20:14:37.907793Z"}
l9-api-1  | {"graph_client_available": false, "event": "Memory Warming Service initialized (Stage 5)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.907915Z"}
l9-api-1  | {"event": "agent.executor.memory_warming_set: enabled=True", "logger": "core.agents.executor", "level": "info", "timestamp": "2026-02-02T20:14:37.908073Z"}
l9-api-1  | {"event": "Memory Warming Service wired to Agent Executor", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.908141Z"}
l9-api-1  | INFO:     Application startup complete.
l9-api-1  | {"event": "\u2713 Memory tools registered: 2 tools", "logger": "core.tools.memory_tools", "level": "info", "timestamp": "2026-02-02T20:14:37.920062Z"}
l9-api-1  | {"event": "\u2713 Memory tools registered: 2 tools", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.920263Z"}
l9-api-1  | {"event": "Memory metrics initialized", "logger": "telemetry.memory_metrics", "level": "info", "timestamp": "2026-02-02T20:14:37.920455Z"}
l9-api-1  | {"event": "\u2713 Prometheus metrics initialized", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.920549Z"}
l9-api-1  | {"event": "\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.920713Z"}
l9-api-1  | {"event": "\u2551  Stage 3: Wiring Enterprise Modules    \u2551", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.920829Z"}
l9-api-1  | {"event": "\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.920978Z"}
l9-api-1  | {"event": "Tool audit service started", "logger": "core.tools.tool_audit", "level": "info", "timestamp": "2026-02-02T20:14:37.921122Z"}
l9-api-1  | {"event": "\u2713 ToolAuditService initialized (Postgres audit trail)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.921200Z"}
l9-api-1  | {"event": "Event-driven coordination initialized", "logger": "core.coordination.event_queue", "level": "info", "timestamp": "2026-02-02T20:14:37.921368Z"}
l9-api-1  | {"event": "\u2713 EventQueue initialized (async coordination)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.921522Z"}
l9-api-1  | {"event": "\u2713 VirtualContextManager initialized (tiered memory)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.921654Z"}
l9-api-1  | {"name": "information_retrieval", "examples": 10, "event": "Defined eval set", "logger": "core.evaluation.evaluator", "level": "info", "timestamp": "2026-02-02T20:14:37.921783Z"}
l9-api-1  | {"name": "code_analysis", "examples": 10, "event": "Defined eval set", "logger": "core.evaluation.evaluator", "level": "info", "timestamp": "2026-02-02T20:14:37.921863Z"}
l9-api-1  | {"name": "multi_tool_orchestration", "examples": 10, "event": "Defined eval set", "logger": "core.evaluation.evaluator", "level": "info", "timestamp": "2026-02-02T20:14:37.921976Z"}
l9-api-1  | {"name": "memory_operations", "examples": 10, "event": "Defined eval set", "logger": "core.evaluation.evaluator", "level": "info", "timestamp": "2026-02-02T20:14:37.922056Z"}
l9-api-1  | {"event": "\u2713 Evaluator initialized (LLM-as-judge, 4 eval sets)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.922254Z"}
l9-api-1  | {"event": "agent.executor.tool_audit_set: enabled=True", "logger": "core.agents.executor", "level": "info", "timestamp": "2026-02-02T20:14:37.922446Z"}
l9-api-1  | {"event": "\u2713 ToolAuditService wired to AgentExecutor", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.922514Z"}
l9-api-1  | {"event": "agent.executor.virtual_context_set: enabled=True", "logger": "core.agents.executor", "level": "info", "timestamp": "2026-02-02T20:14:37.922635Z"}
l9-api-1  | {"event": "\u2713 VirtualContextManager wired to AgentExecutor", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.922689Z"}
l9-api-1  | {"event": "agent.executor.event_queue_set: enabled=True", "logger": "core.agents.executor", "level": "info", "timestamp": "2026-02-02T20:14:37.922775Z"}
l9-api-1  | {"event": "\u2713 EventQueue wired to AgentExecutor", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.922822Z"}
l9-api-1  | {"event": "Stage 3 module wiring complete", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.922993Z"}
l9-api-1  | {"event": "\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.923120Z"}
l9-api-1  | {"event": "\u2551  Stage 4: Memory Consolidation         \u2551", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.923209Z"}
l9-api-1  | {"event": "\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.923300Z"}
l9-api-1  | {"decay_constant": 0.05, "min_threshold": 0.1, "dry_run": false, "event": "NeuralDecayScheduler initialized", "logger": "memory.neural_decay_scheduler", "level": "info", "timestamp": "2026-02-02T20:14:37.923450Z"}
l9-api-1  | {"event": "\u2713 NeuralDecayScheduler initialized", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.923539Z"}
l9-api-1  | {"dry_run": false, "tiers": ["session", "daily", "weekly"], "event": "HierarchicalSummarizer initialized", "logger": "memory.hierarchical_summarizer", "level": "info", "timestamp": "2026-02-02T20:14:37.923674Z"}
l9-api-1  | {"event": "\u2713 HierarchicalSummarizer initialized", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.923761Z"}
l9-api-1  | {"task": "memory_consolidation", "interval_seconds": 14400, "enabled_flag": null, "event": "Background task registered", "logger": "runtime.background_tasks", "level": "info", "timestamp": "2026-02-02T20:14:37.923929Z"}
l9-api-1  | {"event": "\u2713 MemoryConsolidationService initialized (4h cycle)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.924020Z"}
l9-api-1  | {"event": "\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.924107Z"}
l9-api-1  | {"event": "\u2551  Stage 5: Graph-Backed Agent State     \u2551", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.924189Z"}
l9-api-1  | {"event": "\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.924288Z"}
l9-api-1  | {"neo4j_uri": "bolt://neo4j:7687", "l9_graph_agent_state": true, "event": "Graph agent state requested but Neo4j is unavailable; disabling graph-backed agent state for this run.", "logger": "api.server", "level": "warning", "timestamp": "2026-02-02T20:14:37.924383Z"}
l9-api-1  | {"event": "Stage 5 skipped - Neo4j unavailable (app continuing in degraded mode)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.924521Z"}
l9-api-1  | {"neo4j_uri": "bolt://neo4j:7687", "l9_graph_wm_sync": true, "event": "Graph-WM Sync requested but Neo4j is unavailable; disabling Graph-WM Sync for this run.", "logger": "api.server", "level": "warning", "timestamp": "2026-02-02T20:14:37.924646Z"}
l9-api-1  | {"event": "Graph-WM Sync skipped - Neo4j unavailable (app continuing)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.924781Z"}
l9-api-1  | {"event": "ToolPatternExtractor started (interval=6h)", "logger": "core.integration.tool_pattern_extractor", "level": "info", "timestamp": "2026-02-02T20:14:37.940711Z"}
l9-api-1  | {"event": "\u2705 UKG Phase 4: Tool Pattern Extraction started (6h interval)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.940921Z"}
l9-api-1  | {"event": "Initializing Five-Tier Observability...", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.941108Z"}
l9-api-1  | {"extra": {"sampling_rate": 0.1, "exporters": ["console", "substrate"]}, "event": "ObservabilityService initialized", "logger": "core.observability.service", "level": "info", "timestamp": "2026-02-02T20:14:37.946866Z"}
l9-api-1  | {"event": "Observability Prometheus exporter initialized", "logger": "core.observability.prometheus_exporter", "level": "info", "timestamp": "2026-02-02T20:14:37.947840Z"}
l9-api-1  | {"event": "Observability Prometheus exporter initialized", "logger": "core.observability.prometheus_exporter", "level": "info", "timestamp": "2026-02-02T20:14:37.948088Z"}
l9-api-1  | {"event": "Instrumented agent executor (start_agent_task)", "logger": "core.observability.l9_integration", "level": "info", "timestamp": "2026-02-02T20:14:37.948277Z"}
l9-api-1  | {"event": "Instrumented tool registry (dispatch_tool_call)", "logger": "core.observability.l9_integration", "level": "info", "timestamp": "2026-02-02T20:14:37.948382Z"}
l9-api-1  | {"event": "Instrumented governance engine (evaluate)", "logger": "core.observability.l9_integration", "level": "info", "timestamp": "2026-02-02T20:14:37.948458Z"}
l9-api-1  | {"event": "Instrumented memory substrate (4 methods)", "logger": "core.observability.l9_integration", "level": "info", "timestamp": "2026-02-02T20:14:37.948534Z"}
l9-api-1  | {"instrumented": {"executor": true, "tool_registry": true, "governance": true, "substrate": true}, "event": "\u2705 Five-Tier Observability initialized", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.948623Z"}
l9-api-1  | {"task": "observability_metrics", "interval_seconds": 30, "enabled_flag": null, "event": "Background task registered", "logger": "runtime.background_tasks", "level": "info", "timestamp": "2026-02-02T20:14:37.948784Z"}
l9-api-1  | {"event": "Observability metrics task registered (30s interval)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.948862Z"}
l9-api-1  | {"event": "Event queue processor started", "logger": "core.coordination.event_queue", "level": "info", "timestamp": "2026-02-02T20:14:37.949932Z"}
l9-api-1  | {"event": "Starting tool pattern extraction...", "logger": "core.integration.tool_pattern_extractor", "level": "info", "timestamp": "2026-02-02T20:14:37.950125Z"}
l9-api-1  | {"min_size": 0, "max_size": 15, "event": "Database connection pool initialized", "logger": "memory.substrate_repository", "level": "info", "timestamp": "2026-02-02T20:14:37.950303Z"}
l9-api-1  | {"event": "Redis connected: redis:6379/0", "logger": "runtime.redis_client", "level": "info", "timestamp": "2026-02-02T20:14:37.953840Z"}
l9-api-1  | {"cache_ttl_seconds": 300, "event": "cache_initialized_with_l9_redis", "logger": "memory.predictive_cache", "level": "info", "timestamp": "2026-02-02T20:14:37.954067Z"}
l9-api-1  | {"event": "warming_service_initialized", "logger": "memory.warming_service", "level": "info", "timestamp": "2026-02-02T20:14:37.954189Z"}
l9-api-1  | {"graph_client_available": false, "event": "Memory Warming Service initialized (Stage 5)", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.954267Z"}
l9-api-1  | {"event": "agent.executor.memory_warming_set: enabled=True", "logger": "core.agents.executor", "level": "info", "timestamp": "2026-02-02T20:14:37.954412Z"}
l9-api-1  | {"event": "Memory Warming Service wired to Agent Executor", "logger": "api.server", "level": "info", "timestamp": "2026-02-02T20:14:37.954477Z"}
l9-api-1  | INFO:     Application startup complete.
l9-api-1  | {"event": "Database connection pool closed", "logger": "memory.substrate_repository", "level": "info", "timestamp": "2026-02-02T20:14:37.963849Z"}
l9-api-1  | {"event": "WorldModelService initialized", "logger": "world_model.service", "level": "info", "timestamp": "2026-02-02T20:14:37.964428Z"}
l9-api-1  | {"event": "Database connection pool closed", "logger": "memory.substrate_repository", "level": "info", "timestamp": "2026-02-02T20:14:38.009653Z"}
l9-api-1  | {"event": "WorldModelService initialized", "logger": "world_model.service", "level": "info", "timestamp": "2026-02-02T20:14:38.009999Z"}
l9-api-1  | {"event": "World Model DB pool initialized with JSON codecs", "logger": "world_model.repository", "level": "info", "timestamp": "2026-02-02T20:14:38.066917Z"}
l9-api-1  | {"extra": {"tools_analyzed": 2, "total_invocations": 36}, "event": "Tool pattern extraction complete", "logger": "core.integration.tool_pattern_extractor", "level": "info", "timestamp": "2026-02-02T20:14:38.076613Z"}
l9-api-1  | {"event": "World Model DB pool initialized with JSON codecs", "logger": "world_model.repository", "level": "info", "timestamp": "2026-02-02T20:14:38.110656Z"}
l9-api-1  | {"extra": {"tools_analyzed": 2, "total_invocations": 36}, "event": "Tool pattern extraction complete", "logger": "core.integration.tool_pattern_extractor", "level": "info", "timestamp": "2026-02-02T20:14:38.117746Z"}
l9-api-1  | INFO:     172.18.0.1:50136 - "GET /health HTTP/1.1" 200 OK
l9-api-1  | INFO:     172.18.0.2:37754 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api-1  | INFO:     172.18.0.2:37754 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api-1  | INFO:     127.0.0.1:38234 - "GET /health HTTP/1.1" 200 OK
l9-api-1  | INFO:     172.18.0.2:60438 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api-1  | INFO:     172.18.0.2:60438 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api-1  | INFO:     127.0.0.1:56106 - "GET /health HTTP/1.1" 200 OK
l9-api-1  | INFO:     172.18.0.2:37406 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api-1  | INFO:     172.18.0.2:37406 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api-1  | INFO:     127.0.0.1:60952 - "GET /health HTTP/1.1" 200 OK
l9-api-1  | INFO:     172.18.0.2:50278 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api-1  | INFO:     172.18.0.2:50278 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api-1  | INFO:     127.0.0.1:60966 - "GET /health HTTP/1.1" 200 OK
l9-api-1  | {"event": "Failed to fetch packets from substrate: RLS scope required for MemorySubstratePacketSource (tenant_id, org_id, user_id).", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-02-02T20:15:24.111551Z"}
l9-api-1  | {"event": "Failed to fetch packets from substrate: RLS scope required for MemorySubstratePacketSource (tenant_id, org_id, user_id).", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-02-02T20:15:24.120991Z"}
l9-api-1  | {"event": "Failed to fetch packets from substrate: RLS scope required for MemorySubstratePacketSource (tenant_id, org_id, user_id).", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-02-02T20:15:24.141705Z"}
l9-api-1  | {"event": "Failed to fetch packets from substrate: RLS scope required for MemorySubstratePacketSource (tenant_id, org_id, user_id).", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-02-02T20:15:24.205943Z"}
l9-api-1  | INFO:     172.18.0.2:37836 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api-1  | INFO:     172.18.0.2:37836 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api-1  | INFO:     127.0.0.1:49258 - "GET /health HTTP/1.1" 200 OK
l9-api-1  | INFO:     172.18.0.1:42176 - "GET /health HTTP/1.1" 200 OK
l9-api-1  | INFO:     172.18.0.2:36896 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api-1  | INFO:     172.18.0.2:36896 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api-1  | INFO:     127.0.0.1:47050 - "GET /health HTTP/1.1" 200 OK
l9-api-1  | INFO:     172.18.0.2:34892 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api-1  | INFO:     172.18.0.2:34892 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api-1  | INFO:     127.0.0.1:39000 - "GET /health HTTP/1.1" 200 OK
l9-api-1  | {"extra": {"alert": "tool_graph_failed"}, "event": "\u274c Tool registration failed: Component 'memory_search' already registered in tool_executors. Tool graph unavailable.", "logger": "api.server", "level": "error", "timestamp": "2026-02-02T20:14:37.891814Z", "exception": "Traceback (most recent call last):\n  File \"/app/api/server.py\", line 1923, in lifespan\n    tool_count = await register_l_tools()\n                 ^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/app/core/tools/registry_adapter.py\", line 2849, in register_l_tools\n    from runtime.l_tools import TOOL_EXECUTORS\n  File \"/app/runtime/l_tools.py\", line 58, in <module>\n    @register_tool(category=\"memory\", priority=10, description=\"memory_search tool\")\n     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/app/runtime/tool_registry.py\", line 109, in decorator\n    tool_executor_registry.register_instance(\n  File \"/app/core/auto_registry.py\", line 274, in register_instance\n    raise DuplicateRegistrationError(\ncore.auto_registry.DuplicateRegistrationError: Component 'memory_search' already registered in tool_executors"}
l9-api-1  | {"event": "Failed to fetch packets from substrate: RLS scope required for MemorySubstratePacketSource (tenant_id, org_id, user_id).", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-02-02T20:15:24.111551Z"}
l9-api-1  | {"event": "Failed to fetch packets from substrate: RLS scope required for MemorySubstratePacketSource (tenant_id, org_id, user_id).", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-02-02T20:15:24.120991Z"}
l9-api-1  | {"event": "Failed to fetch packets from substrate: RLS scope required for MemorySubstratePacketSource (tenant_id, org_id, user_id).", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-02-02T20:15:24.141705Z"}
l9-api-1  | {"event": "Failed to fetch packets from substrate: RLS scope required for MemorySubstratePacketSource (tenant_id, org_id, user_id).", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-02-02T20:15:24.205943Z"}
*   Trying 127.0.0.1:8000...
* Connected to 127.0.0.1 (127.0.0.1) port 8000
> GET /health HTTP/1.1
> Host: 127.0.0.1:8000
> User-Agent: curl/8.5.0
> Accept: */*
> 
< HTTP/1.1 200 OK
< date: Mon, 02 Feb 2026 20:15:49 GMT
< server: uvicorn
< content-length: 55
< content-type: application/json
< 
* Connection #0 to host 127.0.0.1 left intact
{"status":"ok","service":"l9-api","startup_ready":true}# =============================================================================
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
MEMORY_DSN=postgresql://postgres:8e4fXWM6Q3M87*b3@l9-postgres:5432/l9_memory
DATABASE_URL=postgresql://postgres:8e4fXWM6Q3M87*b3@l9-postgres:5432/l9_memory
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
REDIS_PORT=6379
REDIS_PASSWORD=***REDACTED***
# Qdrant Vector Store (use container name)
QDRANT_HOST=qdrant
QDRANT_PORT=6333
# Slack Integration
SLACK_APP_ENABLED=true
SLACK_APP_ID=A0A3MLBJ55Y
SLACK_SIGNING_SECRET=***REDACTED***
SLACK_CLIENT_SECRET=***REDACTED***
SLACK_CLIENT_ID=5756690555681.10123691617202
SLACK_BOT_TOKEN=xoxb-5756690555681-10120570028437-0GsjsVSUP0rsKfxOoHFPrpxc
SLACK_VERIFICATION_TOKEN=nFrKJ0NVekjgzIpOtpyYqUCK
SLACK_BOT_USER_ID=U0A3JGS0UCV
L_SLACK_USER_ID=U0A3JGS0UCV
# Twilio
TWILIO_ENABLED=false
TWILIO_ACCOUNT_SID=AC4daa74c868f142472f9717e3ac6c8c0f
TWILIO_AUTH_TOKEN=d3d1d33dd9afb72f36c210dc845a4ea3
TWILIO_SMS_NUMBER=17047416314
