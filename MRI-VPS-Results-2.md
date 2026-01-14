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
echo "===== END OF MRI v2 =====" for port conflicts"span init errors)"PENAI_API_KEY)"ep -c healthy || echo 0)/3 healthy"e
===== L9 VPS MRI v2 – AGENT EXECUTOR FOCUSED =====
Wed Jan 14 08:05:50 PM UTC 2026

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
LISTEN 0      2048       127.0.0.1:8000       0.0.0.0:*    users:(("python",pid=259745,fd=13))      
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=254300,fd=7)) 
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=254283,fd=7)) 
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=254257,fd=7)) 
LISTEN 0      4096               *:9001             *:*    users:(("caddy",pid=9230,fd=20))         
LISTEN 0      200            [::1]:5432          [::]:*    users:(("postgres",pid=1366480,fd=6))    

A3) DISK SPACE
--------------
/dev/sda1        38G   27G  9.2G  75% /

B1) GIT STATE (/opt/l9)
-----------------------

C1) DOCKER COMPOSE PS
---------------------
NAME            IMAGE                           COMMAND                  SERVICE       CREATED          STATUS                    PORTS
l9-grafana      grafana/grafana:10.2.0          "/run.sh"                grafana       17 minutes ago   Up 16 minutes (healthy)   127.0.0.1:3000->3000/tcp
l9-jaeger       jaegertracing/all-in-one:1.52   "/go/bin/all-in-one-…"   jaeger        17 minutes ago   Up 17 minutes (healthy)   4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-neo4j        neo4j:5-community               "tini -g -- /startup…"   neo4j         27 minutes ago   Up 27 minutes (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-postgres     pgvector/pgvector:pg16          "docker-entrypoint.s…"   l9-postgres   27 minutes ago   Up 27 minutes (healthy)   127.0.0.1:5432->5432/tcp
l9-prometheus   prom/prometheus:v2.48.0         "/bin/prometheus --c…"   prometheus    17 minutes ago   Up 17 minutes (healthy)   127.0.0.1:9090->9090/tcp
l9-redis        redis:7-alpine                  "docker-entrypoint.s…"   redis         27 minutes ago   Up 27 minutes (healthy)   127.0.0.1:6379->6379/tcp

C2) L9-API LOGS (AGENT EXECUTOR FOCUS)
--------------------------------------
=== Last 30 lines ===

=== Agent Executor errors only ===
No Agent Executor errors in logs

=== Lifespan startup sequence ===
No lifespan logs

D1) AGENT EXECUTOR ENV VARS
---------------------------
L9_EXECUTOR_API_KEY:
L9_EXECUTOR_API_KEY=SET
OPENAI_API_KEY:
OPENAI_API_KEY=SET
OPENAI_MODEL:
OPENAI_MODEL=gpt-4o
L9_ENABLE_LEGACY_SLACK_ROUTER:
L9_ENABLE_LEGACY_SLACK_ROUTER=false
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
{"status":"healthy","service":"L9 Phase 2 Memory System","version":"0.3.0","database":"connected","memory_system":"operational"}
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
✅ Public API healthy

G1) AGENT EXECUTOR DIAGNOSIS
----------------------------
Step 1: Check if l9-api container is running
  ❌ Container is DOWN

Step 2: Check for Agent Executor in environment
  ⚠️  Cannot exec into container (not running)

Step 3: Port 8000 conflict check
LISTEN 0      2048       127.0.0.1:8000       0.0.0.0:*    users:(("python",pid=259745,fd=13))      
  ❌ CONFLICT DETECTED:
LISTEN 0      2048       127.0.0.1:8000       0.0.0.0:*    users:(("python",pid=259745,fd=13))      
  Run: sudo kill -9 <PID> to free port 8000

Step 4: Recent container restarts
  ✅ No restart loop

===== DIAGNOSTIC SUMMARY =====
✅ Git clean, no divergence from origin/main
no such service: l9-redis
✅ Postgres/Redis/Neo4j: 0
0/3 healthy
❓ l9-api status: 

🔍 AGENT EXECUTOR TROUBLESHOOTING:
   1. Check PART D1 for missing env vars (L9_EXECUTOR_API_KEY, OPENAI_API_KEY)
   2. Check PART C2 for Python traceback (lifespan init errors)
   3. Check PART G1 Step 3 for port conflicts

===== END OF MRI v2 =====