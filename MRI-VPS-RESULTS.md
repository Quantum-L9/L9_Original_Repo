###############################################################################
# PART A: SYSTEM-LEVEL DIAGNOSTICS
###############################################################################

echo
echo "A1) SYSTEM IDENTITY"
echo "-------------------"
hostname
whoami
echo "===== END OF L9 VPS MRI ====="ers.com fails, public HTTPS access will fail

===== L9 VPS MRI – UPDATED FULL DIAGNOSTIC =====
Wed Jan 14 07:06:07 PM UTC 2026


A1) SYSTEM IDENTITY
-------------------
L9
admin
    inet 157.180.73.53/32 metric 100 scope global dynamic eth0
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
    inet 172.18.0.1/16 brd 172.18.255.255 scope global br-3311ea13e9b0
Linux L9 6.8.0-88-generic #89-Ubuntu SMP PREEMPT_DYNAMIC Sat Oct 11 01:02:46 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux

A2) ALL LISTENING PORTS (TOP 50)
--------------------------------
[sudo] password for admin: 
State  Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess                                   
LISTEN 0      4096       127.0.0.1:3000       0.0.0.0:*    users:(("docker-proxy",pid=73815,fd=7))  
LISTEN 0      4096      127.0.0.54:53         0.0.0.0:*    users:(("systemd-resolve",pid=656,fd=17))
LISTEN 0      4096       127.0.0.1:9090       0.0.0.0:*    users:(("docker-proxy",pid=72817,fd=7))  
LISTEN 0      4096       127.0.0.1:16686      0.0.0.0:*    users:(("docker-proxy",pid=72943,fd=7))  
LISTEN 0      200       172.17.0.1:5432       0.0.0.0:*    users:(("postgres",pid=1366480,fd=7))    
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=72783,fd=7))  
LISTEN 0      2048       127.0.0.1:8000       0.0.0.0:*    users:(("python",pid=214532,fd=13))      
LISTEN 0      4096       127.0.0.1:2019       0.0.0.0:*    users:(("caddy",pid=9230,fd=15))         
LISTEN 0      4096       127.0.0.1:14268      0.0.0.0:*    users:(("docker-proxy",pid=72926,fd=7))  
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=72880,fd=7))  
LISTEN 0      128          0.0.0.0:22         0.0.0.0:*    users:(("sshd",pid=954,fd=3))            
LISTEN 0      128        127.0.0.1:22222      0.0.0.0:*    users:(("sshd",pid=164710,fd=7))         
LISTEN 0      4096   127.0.0.53%lo:53         0.0.0.0:*    users:(("systemd-resolve",pid=656,fd=15))
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=72860,fd=7))  
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=72733,fd=7))  
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
/dev/sda1        38G   30G  6.0G  84% /
/dev/sda1        38G   30G  6.0G  84% /
/dev/sda1        38G   30G  6.0G  84% /
/dev/sda1        38G   30G  6.0G  84% /

B1) GIT STATE (/opt/l9)
-----------------------

Git status:
On branch main
Your branch is up to date with 'origin/main'.

Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
	modified:   readme/repo-index/orchestrator_catalog.txt

Unmerged paths:
  (use "git restore --staged <file>..." to unstage)
  (use "git add <file>..." to mark resolution)
	both modified:   readme/repo-index/api_surfaces.txt
	both modified:   readme/repo-index/architecture.txt
	both modified:   readme/repo-index/async_function_map.txt
	both modified:   readme/repo-index/class_definitions.txt
	both modified:   readme/repo-index/config_files.txt
	both modified:   readme/repo-index/decorator_catalog.txt
	both modified:   readme/repo-index/dynamic_tool_catalog.txt
	both modified:   readme/repo-index/entrypoints.txt
	both modified:   readme/repo-index/env_refs.txt
	both modified:   readme/repo-index/feature_flags.txt
	both modified:   readme/repo-index/file_metrics.txt
	both modified:   readme/repo-index/function_signatures.txt
	both modified:   readme/repo-index/imports.txt
	both modified:   readme/repo-index/inheritance_graph.txt
	both modified:   readme/repo-index/method_catalog.txt
	both modified:   readme/repo-index/pydantic_models.txt
	both modified:   readme/repo-index/route_handlers.txt
	both modified:   readme/repo-index/test_catalog.txt
	both modified:   readme/repo-index/tree.txt


Git diff (HEAD vs working tree, first 100 lines):
diff --cc readme/repo-index/api_surfaces.txt
index 0918c48,ad76f23..0000000
--- a/readme/repo-index/api_surfaces.txt
+++ b/readme/repo-index/api_surfaces.txt
@@@ -20,6 -17,9 +20,12 @@@
    api/routes/slack.py::router
    api/routes/upgrades.py::router
    api/routes/worldmodel.py::router
++<<<<<<< Updated upstream
++=======
+   api/tools/router.py::router
+   api/webhook_mac_agent.py::router
+   api/webhook_slack.py::router
++>>>>>>> Stashed changes
  
  # SERVICES Surface:
    services/research/research_api.py::router
diff --cc readme/repo-index/architecture.txt
index a5d96c9,17ee309..0000000
--- a/readme/repo-index/architecture.txt
+++ b/readme/repo-index/architecture.txt
@@@ -13,15 -13,6 +13,18 @@@ api/routes/ - API routes package
  api/tools/ - 
  ci/ - 
  clients/ - 
++<<<<<<< Updated upstream
 +codegen/code-gen-files/ - 
 +codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.calendar_adapter/ - No module docstring
 +codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.email_adapter/ - No module docstring
 +codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.twilio_adapter/ - No module docstring
 +codegen/code-gen-files/jinja2-templates/ - 
 +codegen/compiler/ - 
 +codegen/compiler/emitters/ - 
 +codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/ - 
 +codegen/extractions/domain_tensor_bridge_v6_20260102/tests/domain_tensor_bridge/ - No module docstring
++=======
++>>>>>>> Stashed changes
  collaborative_cells/ - 
  config/ - L9 Configuration Module.
  core/ - 
@@@ -48,12 -37,8 +51,10 @@@ core/security/ 
  core/testing/ - 
  core/tools/ - 
  core/worldmodel/ - 
- dev/ - No module docstring
- dev/tools/ - No module docstring
  email_agent/ - L9 Email Agent - Gmail API integration.
  graph_adapter/ - L9 LangGraph Integration - PacketNodeAdapter for memory-logg
 +igor/01-09-2025/tokenizer/core/tokenizer/ - 
 +igor/01-09-2025/tokenizer/core/tokenizer/tests/ - 
  ir_engine/ - 
  mac_agent/ - L9 Mac Agent package.
  mac_agent/helpers/ - Mac Agent helper utilities.
@@@ -90,32 -69,8 +91,7 @@@ services/symbolic_computation/core/ 
  services/symbolic_computation/tools/ - 
  simulation/ - 
  telemetry/ - L9 Telemetry module.
- tests/ - 
- tests/api/ - 
- tests/clients/ - 
- tests/codegen/ - Tests for CodeGenAgent and IR Engine code generation.
- tests/collaborative_cells/ - 
- tests/core/agents/ - Tests for core.agents module.
- tests/core/aios/ - 
- tests/core/governance/ - Tests for governance engine.
- tests/core/observability/ - Tests for core.observability module.
- tests/core/security/ - 
- tests/core/tools/ - 
- tests/docker/ - Docker smoke tests for L9 stack validation.
- tests/email_agent/ - 
- tests/ir_engine/ - 
- tests/kernel/ - Kernel Tests
- tests/mac_agent/ - 
- tests/memory/ - Memory Tests
- tests/mocks/ - 
- tests/orchestrators/ - 
- tests/os/ - 
- tests/performance/ - Performance Tests
- tests/simulation/ - 
- tests/telemetry/ - 
- tests/upgrades/ - 
- tests/world_model/ - World Model Tests
  tools/ - 
  upgrades/ - 
 -upgrades/packet_envelope/ - 
  world_model/ - 
  world_model/nodes/ - 
diff --cc readme/repo-index/async_function_map.txt
index 03ba156,63bbfb4..0000000
--- a/readme/repo-index/async_function_map.txt
+++ b/readme/repo-index/async_function_map.txt
@@@ -8,32 -9,14 +9,41 @@@ async __aenter__() @ api/adapters/email
  async __aenter__() @ api/adapters/twilio_adapter/clients/twilio_adapter_client.py
  async __aenter__() @ clients/memory_client.py
  async __aenter__() @ clients/world_model_client.py
++<<<<<<< Updated upstream
 +async __aenter__() @ codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.calendar_adapter/clients/calendar_adapter_client.py
 +async __aenter__() @ codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.email_adapter/clients/email_adapter_client.py
 +async __aenter__() @ codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.twilio_adapter/clients/twilio_adapter_client.py
 +async __aenter__() @ docs/_archived/codegen_slack_adapter/module.slack_adapter/clients/slack_webhook_client.py

Untracked files (first 20):

C1) DOCKER / COMPOSE VERSIONS
-----------------------------
Docker version 29.1.1, build 0aedba5
Docker Compose version v2.40.3
active

C2) DOCKER COMPOSE PS
----------------------
NAME            IMAGE                           COMMAND                  SERVICE       CREATED       STATUS                         PORTS
l9-api          l9-l9-api                       "uvicorn api.server:…"   l9-api        3 hours ago   Restarting (1) 5 seconds ago   
l9-grafana      grafana/grafana:10.2.0          "/run.sh"                grafana       3 hours ago   Up 3 hours (healthy)           127.0.0.1:3000->3000/tcp
l9-jaeger       jaegertracing/all-in-one:1.52   "/go/bin/all-in-one-…"   jaeger        3 hours ago   Up 3 hours (healthy)           4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-neo4j        neo4j:5-community               "tini -g -- /startup…"   neo4j         3 hours ago   Up 3 hours (healthy)           127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-postgres     pgvector/pgvector:pg16          "docker-entrypoint.s…"   l9-postgres   3 hours ago   Up 3 hours (healthy)           127.0.0.1:5432->5432/tcp
l9-prometheus   prom/prometheus:v2.48.0         "/bin/prometheus --c…"   prometheus    3 hours ago   Up 3 hours (healthy)           127.0.0.1:9090->9090/tcp
l9-redis        redis:7-alpine                  "docker-entrypoint.s…"   redis         3 hours ago   Up 3 hours (healthy)           127.0.0.1:6379->6379/tcp

C3) CONTAINER LOGS (l9-api last 80 lines)
-----------------------------------------
l9-api  |   File "<frozen importlib._bootstrap_external>", line 999, in exec_module
l9-api  |   File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
l9-api  |   File "/app/api/server.py", line 407, in <module>
l9-api  |     db.init_db()
l9-api  |   File "/app/api/db.py", line 14, in init_db
l9-api  |     with psycopg.connect(MEMORY_DSN, autocommit=True) as conn:
l9-api  |          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
l9-api  |   File "/usr/local/lib/python3.12/site-packages/psycopg/connection.py", line 100, in connect
l9-api  |     attempts = conninfo_attempts(params)
l9-api  |                ^^^^^^^^^^^^^^^^^^^^^^^^^
l9-api  |   File "/usr/local/lib/python3.12/site-packages/psycopg/_conninfo_attempts.py", line 55, in conninfo_attempts
l9-api  |     raise last_exc
l9-api  | psycopg.OperationalError: failed to resolve host 'l9-postgres': [Errno -3] Temporary failure in name resolution
l9-api  | 2026-01-14 19:06:05 [info     ] WebSocketOrchestrator initialized
l9-api  | 2026-01-14 19:06:05 [debug    ] selfreflection.thresholds_loaded iteration_threshold=8 token_threshold=50000 tool_failure_threshold=3
l9-api  | 2026-01-14 19:06:06 [debug    ] Calendar Adapter not enabled (CALENDAR_ADAPTER_ENABLED != true)
l9-api  | 2026-01-14 19:06:06 [debug    ] Email Adapter not enabled (EMAIL_ENABLED != true)
l9-api  | 2026-01-14 19:06:06 [debug    ] Twilio Adapter not enabled (TWILIO_ENABLED != true)
l9-api  | 2026-01-14 19:06:06 [warning  ] Gmail API libraries not available
l9-api  | 2026-01-14 19:06:06 [warning  ] Gmail OAuth libraries not available
l9-api  | Traceback (most recent call last):
l9-api  |   File "/usr/local/bin/uvicorn", line 7, in <module>
l9-api  |     sys.exit(main())
l9-api  |              ^^^^^^
l9-api  |   File "/usr/local/lib/python3.12/site-packages/click/core.py", line 1485, in __call__
l9-api  |     return self.main(*args, **kwargs)
l9-api  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^
l9-api  |   File "/usr/local/lib/python3.12/site-packages/click/core.py", line 1406, in main
l9-api  |     rv = self.invoke(ctx)
l9-api  |          ^^^^^^^^^^^^^^^^
l9-api  |   File "/usr/local/lib/python3.12/site-packages/click/core.py", line 1269, in invoke
l9-api  |     return ctx.invoke(self.callback, **ctx.params)
l9-api  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
l9-api  |   File "/usr/local/lib/python3.12/site-packages/click/core.py", line 824, in invoke
l9-api  |     return callback(*args, **kwargs)
l9-api  |            ^^^^^^^^^^^^^^^^^^^^^^^^^
l9-api  |   File "/usr/local/lib/python3.12/site-packages/uvicorn/main.py", line 424, in main
l9-api  |     run(
l9-api  |   File "/usr/local/lib/python3.12/site-packages/uvicorn/main.py", line 594, in run
l9-api  |     server.run()
l9-api  |   File "/usr/local/lib/python3.12/site-packages/uvicorn/server.py", line 67, in run
l9-api  |     return asyncio_run(self.serve(sockets=sockets), loop_factory=self.config.get_loop_factory())
l9-api  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
l9-api  |   File "/usr/local/lib/python3.12/asyncio/runners.py", line 195, in run
l9-api  |     return runner.run(main)
l9-api  |            ^^^^^^^^^^^^^^^^
l9-api  |   File "/usr/local/lib/python3.12/asyncio/runners.py", line 118, in run
l9-api  |     return self._loop.run_until_complete(task)
l9-api  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
l9-api  |   File "uvloop/loop.pyx", line 1518, in uvloop.loop.Loop.run_until_complete
l9-api  |   File "/usr/local/lib/python3.12/site-packages/uvicorn/server.py", line 71, in serve
l9-api  |     await self._serve(sockets)
l9-api  |   File "/usr/local/lib/python3.12/site-packages/uvicorn/server.py", line 78, in _serve
l9-api  |     config.load()
l9-api  |   File "/usr/local/lib/python3.12/site-packages/uvicorn/config.py", line 439, in load
l9-api  |     self.loaded_app = import_from_string(self.app)
l9-api  |                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
l9-api  |   File "/usr/local/lib/python3.12/site-packages/uvicorn/importer.py", line 19, in import_from_string
l9-api  |     module = importlib.import_module(module_str)
l9-api  |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
l9-api  |   File "/usr/local/lib/python3.12/importlib/__init__.py", line 90, in import_module
l9-api  |     return _bootstrap._gcd_import(name[level:], package, level)
l9-api  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
l9-api  |   File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
l9-api  |   File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
l9-api  |   File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
l9-api  |   File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
l9-api  |   File "<frozen importlib._bootstrap_external>", line 999, in exec_module
l9-api  |   File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
l9-api  |   File "/app/api/server.py", line 407, in <module>
l9-api  |     db.init_db()
l9-api  |   File "/app/api/db.py", line 14, in init_db
l9-api  |     with psycopg.connect(MEMORY_DSN, autocommit=True) as conn:
l9-api  |          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
l9-api  |   File "/usr/local/lib/python3.12/site-packages/psycopg/connection.py", line 100, in connect
l9-api  |     attempts = conninfo_attempts(params)
l9-api  |                ^^^^^^^^^^^^^^^^^^^^^^^^^
l9-api  |   File "/usr/local/lib/python3.12/site-packages/psycopg/_conninfo_attempts.py", line 55, in conninfo_attempts
l9-api  |     raise last_exc
l9-api  | psycopg.OperationalError: failed to resolve host 'l9-postgres': [Errno -3] Temporary failure in name resolution

C4) DOCKER NETWORK + PORTS OF INTEREST
--------------------------------------
docker0 / bridge networks:
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
    inet6 fe80::f414:77ff:fe38:57f9/64 scope link 

Explicit port checks (8000, 9001, 5432, 7474, 7687, 6379, 9090, 3000, 16686):
LISTEN 0      4096       127.0.0.1:3000       0.0.0.0:*    users:(("docker-proxy",pid=73815,fd=7))  
LISTEN 0      4096       127.0.0.1:9090       0.0.0.0:*    users:(("docker-proxy",pid=72817,fd=7))  
LISTEN 0      4096       127.0.0.1:16686      0.0.0.0:*    users:(("docker-proxy",pid=72943,fd=7))  
LISTEN 0      200       172.17.0.1:5432       0.0.0.0:*    users:(("postgres",pid=1366480,fd=7))    
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=72783,fd=7))  
LISTEN 0      2048       127.0.0.1:8000       0.0.0.0:*    users:(("python",pid=214532,fd=13))      
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=72880,fd=7))  
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=72860,fd=7))  
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=72733,fd=7))  
LISTEN 0      4096               *:9001             *:*    users:(("caddy",pid=9230,fd=20))         
LISTEN 0      200            [::1]:5432          [::]:*    users:(("postgres",pid=1366480,fd=6))    

D1) .env (SANITIZED KEYS ONLY)
------------------------------
DATABASE_URL=REDACTED
L9_API_KEY=REDACTED
L9_ENABLE_LEGACY_SLACK_ROUTER=REDACTED
L9_EXECUTOR_API_KEY=REDACTED
L_SLACK_USER_ID=REDACTED
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
291:  neo4j_data:
293:    name: l9-neo4j-data
294:  neo4j_logs:
296:    name: l9-neo4j-logs

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
E2) L9 API WORLD MODEL HEALTH
-----------------------------
{"detail":"Not Found"}{"detail":"Not Found"}
E3) MCP / CADDY FRONT DOOR HEALTH (9001)
----------------------------------------
HTTP → expect 'Client sent an HTTP request to an HTTPS server' if TLS-only:
Client sent an HTTP request to an HTTPS server.

HTTPS → /health:
curl: (35) OpenSSL/3.0.13: error:0A000438:SSL routines::tlsv1 alert internal error
HTTPS /health on 9001 not responding (check Caddy and certs)

E4) PUBLIC HEALTH VIA DOMAIN (IF DNS CONFIGURED)
-----------------------------------------------
Public API health (443):
{"status":"healthy","service":"L9 Phase 2 Memory System","version":"0.3.0","database":"connected","memory_system":"operational"}Public world model state-version (443):
curl: (22) The requested URL returned error: 404
Public worldmodel state-version failed

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
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=72733,fd=7))  
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
CONTAINER ID   IMAGE               STATUS                 PORTS
8f00855f4472   neo4j:5-community   Up 3 hours (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp

Neo4j ports:
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=72880,fd=7))  
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=72860,fd=7))  

F3) NEO4J BOLT CONNECTIVITY (IF PASSWORD SET)
--------------------------------------------
Attempting Neo4j driver smoke test via python...
Neo4j Python driver test failed (driver not installed or auth error)

F4) REDIS STATUS (IF USED)
--------------------------
CONTAINER ID   IMAGE            STATUS                 PORTS
5713abddbcba   redis:7-alpine   Up 3 hours (healthy)   127.0.0.1:6379->6379/tcp

LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=72783,fd=7))  

G1) MEMORY SUBSTRATE STATS
--------------------------
{"detail":"Not Found"}
Memory healthcheck:
{"detail":"Not Found"}
G2) WORLD MODEL SNAPSHOT
------------------------
World model health (via /healthneo4j if present):
{"detail":"Not Found"}World model entities (first page via API):
{"detail":"Not Found"}
H1) PROMETHEUS STATUS
---------------------
CONTAINER ID   IMAGE                     STATUS                 PORTS
2e40135c11e0   prom/prometheus:v2.48.0   Up 3 hours (healthy)   127.0.0.1:9090->9090/tcp
Prometheus Server is Healthy.

H2) GRAFANA STATUS
------------------
CONTAINER ID   IMAGE                    STATUS                 PORTS
a1f178431ac3   grafana/grafana:10.2.0   Up 3 hours (healthy)   127.0.0.1:3000->3000/tcp
{
  "commit": "895fbafb7a",
  "database": "ok",
  "version": "10.2.0"
}
H3) JAEGER STATUS
-----------------
CONTAINER ID   IMAGE                           STATUS                 PORTS
1ea229e1998c   jaegertracing/all-in-one:1.52   Up 3 hours (healthy)   4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

===== MRI SUMMARY HINTS (READ OUTPUT ABOVE) =====
- If l9-api is unhealthy or degraded in docker compose ps, check /health payload and logs for failing optional backends (Neo4j, observability).
- If Postgres 5432 is not listening, memory + world model will be broken.
- If Neo4j container is up but NEO4J_* vars missing in .env, graph features are effectively OFF.
- If Caddy on 9001 responds with 'HTTP request to HTTPS server' over HTTP, that is expected (TLS only).
- If DNS for l9.quantumaipartners.com fails, public HTTPS access will fail; use IP or fix DNS.

===== END OF L9 VPS MRI =====