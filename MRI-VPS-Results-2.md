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
git diff --stat | head -10 || true

###############################################################################
# PART C: DOCKER STACK
###############################################################################

echo
echo "C1) DOCKER COMPOSE PS"
echo "---------------------"
docker compose ps

echo
echo "C2) L9-API LOGS (AGENT EXECUTOR FOCUS)"
echo "--------------------------------------"
echo "===== END OF MRI v2 =====" for port conflicts"span init errors)"PENAI_API_KEY)"ep -c healthy || echo 0)/3 healthy"e for error details" || echo "  ✅ No restart loop"
===== L9 VPS MRI v2 – AGENT EXECUTOR FOCUSED =====
Fri Jan 16 02:10:58 PM UTC 2026

A1) SYSTEM IDENTITY
-------------------
L9
admin
    inet 157.180.73.53/32 metric 100 scope global dynamic eth0
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
    inet 172.18.0.1/16 brd 172.18.255.255 scope global br-1e6017fa3bc4
Linux L9 6.8.0-90-generic #91-Ubuntu SMP PREEMPT_DYNAMIC Tue Nov 18 14:14:30 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux

A2) CRITICAL PORTS
------------------
[sudo] password for admin: 
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=2268,fd=7))   
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=2416,fd=7))   
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=2540,fd=7))   
LISTEN 0      4096       127.0.0.1:8000       0.0.0.0:*    users:(("docker-proxy",pid=3900,fd=7))   
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=2432,fd=7))   
LISTEN 0      4096               *:9001             *:*    users:(("caddy",pid=962,fd=9))           

A3) DISK SPACE
--------------
/dev/sda1        38G   32G  4.2G  89% /

B1) GIT STATE (/opt/l9)
-----------------------
 M .dockerignore
 M api/server_memory.py
 .dockerignore        | 63 +++++++++++++---------------------------------------
 api/server_memory.py |  2 +-
 2 files changed, 17 insertions(+), 48 deletions(-)

C1) DOCKER COMPOSE PS
---------------------
NAME            IMAGE                           COMMAND                  SERVICE         CREATED        STATUS                             PORTS
l9-api          l9-l9-api                       "uvicorn api.server:…"   l9-api          9 hours ago    Up 6 seconds (health: starting)    127.0.0.1:8000->8000/tcp
l9-grafana      grafana/grafana:10.2.0          "/run.sh"                grafana         42 hours ago   Up 34 seconds (healthy)            127.0.0.1:3000->3000/tcp
l9-jaeger       jaegertracing/all-in-one:1.52   "/go/bin/all-in-one-…"   jaeger          42 hours ago   Up 34 seconds (healthy)            4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-mcp-memory   l9-l9-mcp-memory                "uvicorn mcp_memory.…"   l9-mcp-memory   23 hours ago   Up 34 seconds (healthy)            127.0.0.1:9002->9002/tcp
l9-neo4j        neo4j:5-community               "tini -g -- /startup…"   neo4j           43 hours ago   Up 34 seconds (health: starting)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-postgres     pgvector/pgvector:pg16          "docker-entrypoint.s…"   l9-postgres     43 hours ago   Up 34 seconds (healthy)            127.0.0.1:5432->5432/tcp
l9-prometheus   prom/prometheus:v2.48.0         "/bin/prometheus --c…"   prometheus      42 hours ago   Up 34 seconds (healthy)            127.0.0.1:9090->9090/tcp
l9-redis        redis:7-alpine                  "docker-entrypoint.s…"   redis           43 hours ago   Up 34 seconds (healthy)            127.0.0.1:6379->6379/tcp

C2) L9-API LOGS (AGENT EXECUTOR FOCUS)
--------------------------------------
=== Last 30 lines ===
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.626841Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.626880Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.626921Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.626979Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.627043Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.627110Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.627198Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.627267Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.627335Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.627403Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.627469Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.627533Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.627598Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.627663Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.627745Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.627815Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.627882Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.627948Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.628019Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.628086Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.628959Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.629165Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.629371Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.629558Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.629759Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-16T14:11:02.629948Z"}
l9-api  | {"event": "Failed to initialize Agent Executor: cannot access local variable 'settings' where it is not associated with a value", "logger": "api.server", "level": "error", "timestamp": "2026-01-16T14:11:02.630186Z", "exception": "Traceback (most recent call last):\n  File \"/app/api/server.py\", line 781, in lifespan\n    skip_startup = settings.l9_skip_startup_checks\n                   ^^^^^^^^\nUnboundLocalError: cannot access local variable 'settings' where it is not associated with a value"}
l9-api  | {"event": "Patterns file not found: /app/seed/architectural_patterns.yaml", "logger": "world_model.seed_loader", "level": "warning", "timestamp": "2026-01-16T14:11:02.664537Z"}
l9-api  | {"event": "Heuristics file not found: /app/seed/coding_heuristics.yaml", "logger": "world_model.seed_loader", "level": "warning", "timestamp": "2026-01-16T14:11:02.667330Z"}
l9-api  | {"event": "Error querying packets: Governance context required for memory operation: repository.search_packets_by_type", "logger": "memory.substrate_service", "level": "error", "timestamp": "2026-01-16T14:11:02.667720Z"}

=== Agent Executor errors only ===
