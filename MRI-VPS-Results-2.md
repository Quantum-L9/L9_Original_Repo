###############################################################################
# PART A: SYSTEM IDENTITY
###############################################################################

echo "A1) SYSTEM IDENTITY"
echo "-------------------"
hostname
whoami
ip addr show | grep 'inet ' | grep -v '127.0.0.1' | head -3
uname -r  # Just kernel version, not full uname

echo
echo "A2) CRITICAL PORTS"
echo "------------------"
sudo ss -tlnp 2>/dev/null | grep -E '(:8000|:8080|:9001|:5432|:7474|:7687|:6379)' || echo "No critical ports listening"

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

echo "===== END OF MRI v3 ====="gration status"icts"emory --format '{{.Status}}' 2>/dev/null || echo 'unknown')"_at FROM schema_migrations ORDER BY applied_at DESC LIMIT 5" 2>/dev/n
===== L9 VPS MRI v3 – FRESH SLATE DIAGNOSTICS =====
Sat Jan 17 02:00:24 PM UTC 2026

A1) SYSTEM IDENTITY
-------------------
L9
admin
    inet 157.180.73.53/32 metric 100 scope global dynamic eth0
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
6.8.0-90-generic

A2) CRITICAL PORTS
------------------
[sudo] password for admin: 
LISTEN 0      2048       127.0.0.1:8000       0.0.0.0:*    users:(("python",pid=1167877,fd=13))     
LISTEN 0      4096               *:9001             *:*    users:(("caddy",pid=964,fd=9))           

A3) DISK SPACE
--------------
/dev/sda1        38G   28G  7.9G  79% /

B1) GIT STATE (/opt/l9)
-----------------------

C1) DOCKER COMPOSE PS (ALL CONTAINERS)
---------------------------------------
NAME      STATUS    PORTS

C2) L9-API LOGS (AGENT EXECUTOR FOCUS)
--------------------------------------
=== Last 20 lines ===

=== Errors/Exceptions ===
No errors in logs

=== Lifespan startup sequence ===
No lifespan logs

C3) L9-MCP-MEMORY STATUS
------------------------

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
✅ API healthy: {"status":"healthy","service":"L9 Phase 2 Memory System","version":"0.3.0","database":"connected","memory_system":"operational"}

E2) BACKEND SERVICES
--------------------
Postgres (5432):
  ❌ Not ready
Redis (6379):
  ❌ Not responding
Neo4j (7687):
  ❌ Not connected (check NEO4J_PASSWORD)

E3) MCP MEMORY API (8080)
-------------------------
❌ MCP Memory not responding: curl: (7) Failed to connect to 127.0.0.1 port 8080 after 0 ms: Couldn't connect to server
FAIL

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
LISTEN 0      2048       127.0.0.1:8000       0.0.0.0:*    users:(("python",pid=1167877,fd=13))     
  ❌ CONFLICT DETECTED:
LISTEN 0      2048       127.0.0.1:8000       0.0.0.0:*    users:(("python",pid=1167877,fd=13))     
  Run: sudo kill -9 <PID> to free port 8000

Step 4: Recent container restarts
  ✅ No restart loop

H1) MIGRATION STATUS
--------------------
Applied migrations (schema_migrations table): 0
Migration files in migrations/: 22
Recent migrations:
  (cannot query schema_migrations)

===== DIAGNOSTIC SUMMARY =====
📦 Containers: 0
0/0
0 healthy
🔌 l9-api: 
🔌 l9-mcp-memory: 
📊 Migrations: 0 applied

🔍 TROUBLESHOOTING:
   1. Check PART D1 for missing env vars
   2. Check PART C2/C3 for container errors
   3. Check PART G1 Step 3 for port conflicts
   4. Check PART H1 for migration status

===== END OF MRI v3 =====
