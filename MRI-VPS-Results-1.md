===== L9 VPS MRI – UPDATED FULL DIAGNOSTIC =====
Sat Jan 17 08:25:35 PM UTC 2026


A1) SYSTEM IDENTITY
-------------------
L9
admin
    inet 157.180.73.53/32 metric 100 scope global dynamic eth0
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
    inet 172.18.0.1/16 brd 172.18.255.255 scope global br-5215c69a440d
Linux L9 6.8.0-90-generic #91-Ubuntu SMP PREEMPT_DYNAMIC Tue Nov 18 14:14:30 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux

A2) ALL LISTENING PORTS (TOP 50)
--------------------------------
State  Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess                                   
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=1511691,fd=7))
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=1511593,fd=7))
LISTEN 0      128          0.0.0.0:22         0.0.0.0:*    users:(("sshd",pid=1018,fd=3))           
LISTEN 0      4096       127.0.0.1:2019       0.0.0.0:*    users:(("caddy",pid=964,fd=3))           
LISTEN 0      4096       127.0.0.1:14268      0.0.0.0:*    users:(("docker-proxy",pid=1511647,fd=7))
LISTEN 0      4096       127.0.0.1:8000       0.0.0.0:*    users:(("docker-proxy",pid=1528833,fd=7))
LISTEN 0      128        127.0.0.1:22222      0.0.0.0:*    users:(("sshd",pid=1503755,fd=7))        
LISTEN 0      4096         0.0.0.0:631        0.0.0.0:*    users:(("cupsd",pid=1797,fd=9))          
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=1511720,fd=7))
LISTEN 0      4096       127.0.0.1:16686      0.0.0.0:*    users:(("docker-proxy",pid=1511666,fd=7))
LISTEN 0      4096      127.0.0.54:53         0.0.0.0:*    users:(("systemd-resolve",pid=701,fd=17))
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=1511562,fd=7))
LISTEN 0      4096       127.0.0.1:9090       0.0.0.0:*    users:(("docker-proxy",pid=1511514,fd=7))
LISTEN 0      4096   127.0.0.53%lo:53         0.0.0.0:*    users:(("systemd-resolve",pid=701,fd=15))
LISTEN 0      4096       127.0.0.1:3000       0.0.0.0:*    users:(("docker-proxy",pid=1512260,fd=7))
LISTEN 0      4096       127.0.0.1:9002       0.0.0.0:*    users:(("docker-proxy",pid=1512046,fd=7))
LISTEN 0      4096               *:443              *:*    users:(("caddy",pid=964,fd=7))           
LISTEN 0      4096               *:80               *:*    users:(("caddy",pid=964,fd=11))          
LISTEN 0      128             [::]:22            [::]:*    users:(("sshd",pid=1018,fd=4))           
LISTEN 0      128            [::1]:22222         [::]:*    users:(("sshd",pid=1503755,fd=5))        
LISTEN 0      4096               *:9001             *:*    users:(("caddy",pid=964,fd=9))           
LISTEN 0      4096            [::]:631           [::]:*    users:(("cupsd",pid=1797,fd=10))         

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
/dev/sda1        38G   26G   11G  72% /
/dev/sda1        38G   26G   11G  72% /
/dev/sda1        38G   26G   11G  72% /
/dev/sda1        38G   26G   11G  72% /

A5) MEMORY (RAM)
----------------
               total        used        free      shared  buff/cache   available
Mem:           3.7Gi       1.7Gi       151Mi        23Mi       2.2Gi       2.1Gi
Swap:             0B          0B          0B

A6) SYSTEM LOAD
---------------
 20:25:35 up 1 day,  4:15,  4 users,  load average: 0.68, 0.74, 6.70

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
NAME            IMAGE                           COMMAND                  SERVICE         CREATED              STATUS                        PORTS
l9-api          l9-l9-api                       "uvicorn api.server:…"   l9-api          About a minute ago   Up About a minute (healthy)   127.0.0.1:8000->8000/tcp
l9-grafana      grafana/grafana:10.2.0          "/run.sh"                grafana         15 minutes ago       Up 15 minutes (healthy)       127.0.0.1:3000->3000/tcp
l9-jaeger       jaegertracing/all-in-one:1.52   "/go/bin/all-in-one-…"   jaeger          15 minutes ago       Up 15 minutes (healthy)       4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-mcp-memory   l9-l9-mcp-memory                "uvicorn mcp_memory.…"   l9-mcp-memory   15 minutes ago       Up 15 minutes (healthy)       127.0.0.1:9002->9002/tcp
l9-neo4j        neo4j:5-community               "tini -g -- /startup…"   neo4j           15 minutes ago       Up 15 minutes (healthy)       127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-postgres     pgvector/pgvector:pg16          "docker-entrypoint.s…"   l9-postgres     15 minutes ago       Up 15 minutes (healthy)       127.0.0.1:5432->5432/tcp
l9-prometheus   prom/prometheus:v2.48.0         "/bin/prometheus --c…"   prometheus      15 minutes ago       Up 15 minutes (healthy)       127.0.0.1:9090->9090/tcp
l9-redis        redis:7-alpine                  "docker-entrypoint.s…"   redis           15 minutes ago       Up 15 minutes (healthy)       127.0.0.1:6379->6379/tcp

C3) CONTAINER LOGS (l9-api last 80 lines)
-----------------------------------------
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496092Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496140Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496182Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496248Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496324Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496388Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496443Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496489Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496534Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496580Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496644Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496689Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496738Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496784Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496827Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496896Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.496970Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497036Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497082Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497128Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497172Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497224Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497267Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497314Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497364Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497417Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497467Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497514Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497562Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497604Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497670Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497713Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497761Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497803Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497849Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497898Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497945Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.497992Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.498055Z"}
l9-api  | {"event": "Database pool not available", "logger": "core.tools.tool_embeddings", "level": "warning", "timestamp": "2026-01-17T20:24:02.498105Z"}
l9-api  | {"event": "Patterns file not found: /app/seed/architectural_patterns.yaml", "logger": "world_model.seed_loader", "level": "warning", "timestamp": "2026-01-17T20:24:02.635979Z"}
l9-api  | {"event": "Heuristics file not found: /app/seed/coding_heuristics.yaml", "logger": "world_model.seed_loader", "level": "warning", "timestamp": "2026-01-17T20:24:02.636150Z"}
l9-api  | {"event": "Failed to fetch packets from substrate: RLS scope required for MemorySubstratePacketSource (tenant_id, org_id, user_id).", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-01-17T20:24:02.636362Z"}
l9-api  | {"event": "Failed to bootstrap governance schema: No module named 'scripts.bootstrap_neo4j_schema'", "logger": "api.server", "level": "warning", "timestamp": "2026-01-17T20:24:02.646605Z"}
l9-api  | {"agent_id": "l-cto", "error": "RedisClient.set() got an unexpected keyword argument 'ex'", "event": "Failed to initialize Redis working memory, continuing", "logger": "core.agents.bootstrap.phase_2_instantiate", "level": "warning", "timestamp": "2026-01-17T20:24:04.203969Z"}
l9-api  | {"agent_id": "l-cto", "tried_path": "private/agents/identity/l-cto_identity.yaml", "event": "Identity YAML not found, using defaults", "logger": "core.agents.bootstrap.phase_4_load_identity", "level": "warning", "timestamp": "2026-01-17T20:24:04.318238Z"}
l9-api  | {"packet_id": "617931cd-60ef-4a6c-a60f-24df37eb3ebb", "packet_type": "memory_write", "marker_count": 1, "markers": [], "event": "injection_markers_detected", "logger": "memory.audit_utils", "level": "warning", "timestamp": "2026-01-17T20:24:04.409092Z"}
l9-api  | {"event": "Error updating world model from insights: RLS scope required for WorldModelRepository (tenant_id, org_id, user_id).", "logger": "world_model.service", "level": "error", "timestamp": "2026-01-17T20:24:04.537879Z"}
l9-api  | {"event": "STARTUP VALIDATION: SessionStartup result not available", "logger": "api.server", "level": "warning", "timestamp": "2026-01-17T20:24:04.626948Z"}
l9-api  | INFO:     Application startup complete.
l9-api  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
l9-api  | Received notification from DBMS server: <GqlStatusObject gql_status='01N51', status_description='warn: relationship type does not exist. The relationship type `COLLABORATES_WITH` does not exist. Verify that the spelling is correct.', position=<SummaryInputPosition line=8, column=24, offset=330>, raw_classification='UNRECOGNIZED', classification=<NotificationClassification.UNRECOGNIZED: 'UNRECOGNIZED'>, raw_severity='WARNING', severity=<NotificationSeverity.WARNING: 'WARNING'>, diagnostic_record={'_classification': 'UNRECOGNIZED', '_severity': 'WARNING', '_position': {'offset': 330, 'line': 8, 'column': 24}, 'OPERATION': '', 'OPERATION_CODE': '0', 'CURRENT_SCHEMA': '/'}> for query: '\nMATCH (a:Agent {agent_id: $agent_id})\nOPTIONAL MATCH (a)-[r1:HAS_RESPONSIBILITY]->(resp:Responsibility)\nOPTIONAL MATCH (a)-[r2:HAS_DIRECTIVE]->(dir:Directive)\nOPTIONAL MATCH (a)-[r3:HAS_SOP]->(sop:SOP)\nOPTIONAL MATCH (a)-[r4:CAN_EXECUTE]->(tool:Tool)\nOPTIONAL MATCH (a)-[r5:REPORTS_TO]->(supervisor:Agent)\nOPTIONAL MATCH (a)-[r6:COLLABORATES_WITH]->(peer:Agent)\nRETURN a,\n       collect(DISTINCT resp) as responsibilities,\n       collect(DISTINCT dir) as directives,\n       collect(DISTINCT sop) as sops,\n       collect(DISTINCT tool) as tools,\n       supervisor,\n       collect(DISTINCT peer) as collaborators\n'
l9-api  | INFO:     127.0.0.1:38008 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.2:57258 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.2:57258 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | INFO:     127.0.0.1:42024 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.2:34956 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.2:34956 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | INFO:     127.0.0.1:49608 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.2:60394 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.2:60394 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | INFO:     127.0.0.1:53782 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.2:39480 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.2:39480 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | INFO:     127.0.0.1:40026 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.2:43028 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.2:43028 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | INFO:     127.0.0.1:44074 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.2:53630 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.2:53630 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | {"event": "Failed to fetch packets from substrate: RLS scope required for MemorySubstratePacketSource (tenant_id, org_id, user_id).", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-01-17T20:25:02.636874Z"}
l9-api  | INFO:     127.0.0.1:53428 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.2:37814 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.2:37814 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | INFO:     127.0.0.1:60334 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.2:35674 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.2:35674 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | INFO:     127.0.0.1:35588 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.2:42704 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.2:42704 - "GET /metrics/ HTTP/1.1" 200 OK

C4) DOCKER NETWORK + PORTS OF INTEREST
--------------------------------------
docker0 / bridge networks:
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
    inet6 fe80::74b2:4ff:fe14:e7f3/64 scope link 

Explicit port checks (8000, 9001, 5432, 7474, 7687, 6379, 9090, 3000, 16686):
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=1511691,fd=7))
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=1511593,fd=7))
LISTEN 0      4096       127.0.0.1:8000       0.0.0.0:*    users:(("docker-proxy",pid=1528833,fd=7))
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=1511720,fd=7))
LISTEN 0      4096       127.0.0.1:16686      0.0.0.0:*    users:(("docker-proxy",pid=1511666,fd=7))
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=1511562,fd=7))
LISTEN 0      4096       127.0.0.1:9090       0.0.0.0:*    users:(("docker-proxy",pid=1511514,fd=7))
LISTEN 0      4096       127.0.0.1:3000       0.0.0.0:*    users:(("docker-proxy",pid=1512260,fd=7))
LISTEN 0      4096               *:9001             *:*    users:(("caddy",pid=964,fd=9))           

C5) DOCKER IMAGES
-----------------
REPOSITORY                 TAG           SIZE
l9-l9-api                  latest        1.32GB
l9-l9-mcp-memory           latest        828MB
neo4j                      5-community   853MB
pgvector/pgvector          pg16          723MB
redis                      7-alpine      61.2MB
jaegertracing/all-in-one   1.52          109MB
prom/prometheus            v2.48.0       349MB
grafana/grafana            10.2.0        538MB

C6) DOCKER NETWORKS
-------------------
NETWORK ID     NAME            DRIVER    SCOPE
d8bc3be9c6c5   bridge          bridge    local
7fd8092b1eee   host            host      local
5215c69a440d   l9_l9-network   bridge    local
8e2e6b859253   none            null      local

C7) DOCKER CONTAINER ERRORS (RECENT)
------------------------------------
--- l9-api ---
{"event": "Failed to fetch packets from substrate: RLS scope required for MemorySubstratePacketSource (tenant_id, org_id, user_id).", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-01-17T20:24:02.636362Z"}
{"event": "Failed to bootstrap governance schema: No module named 'scripts.bootstrap_neo4j_schema'", "logger": "api.server", "level": "warning", "timestamp": "2026-01-17T20:24:02.646605Z"}
{"agent_id": "l-cto", "error": "RedisClient.set() got an unexpected keyword argument 'ex'", "event": "Failed to initialize Redis working memory, continuing", "logger": "core.agents.bootstrap.phase_2_instantiate", "level": "warning", "timestamp": "2026-01-17T20:24:04.203969Z"}
{"event": "Error updating world model from insights: RLS scope required for WorldModelRepository (tenant_id, org_id, user_id).", "logger": "world_model.service", "level": "error", "timestamp": "2026-01-17T20:24:04.537879Z"}
{"event": "Failed to fetch packets from substrate: RLS scope required for MemorySubstratePacketSource (tenant_id, org_id, user_id).", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-01-17T20:25:02.636874Z"}
--- l9-postgres ---
2026-01-17 20:24:01.807 UTC [1414] ERROR:  column cannot have more than 2000 dimensions for ivfflat index
2026-01-17 20:24:01.819 UTC [1414] ERROR:  there is no unique constraint matching given keys for referenced table "packet_store"
	    -- Temporal information (CRITICAL for episodic memory)
	COMMENT ON COLUMN episodic_events.event_timestamp IS 'When the event occurred (CRITICAL for temporal queries)';
2026-01-17 20:24:01.821 UTC [1414] ERROR:  relation "semantic_facts" does not exist
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
306:  neo4j_data:
308:    name: l9-neo4j-data
309:  neo4j_logs:
311:    name: l9-neo4j-logs

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
{"status":"ok","service":"l9-api","startup_ready":true}
E2) L9 MEMORY ENDPOINTS
-----------------------
{"detail":"Not Found"}{"detail":"Not Found"}
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
2a06:98c1:3121::3 l9.quantumaipartners.com
2a06:98c1:3120::3 l9.quantumaipartners.com

E5) PUBLIC HEALTH VIA DOMAIN (IF DNS CONFIGURED)
-----------------------------------------------
Public API health (443):
{"status":"ok","service":"l9-api","startup_ready":true}Public world model state-version (443):
curl: (22) The requested URL returned error: 404
Public worldmodel state-version failed

E6) API ROUTES AVAILABLE (via OpenAPI)
--------------------------------------
/
/agent/execute
/agent/health
/agent/status
/agent/task
/api/gmp/analytics
/api/gmp/autonomy-level
/api/gmp/generate-heuristics
/api/gmp/graduate
/api/gmp/graduation-status
/api/gmp/heuristics
/api/gmp/log-execution
/api/v1/memory/batch
/api/v1/memory/cache/delete/{key}
/api/v1/memory/cache/get/{key}
/api/v1/memory/cache/health
/api/v1/memory/cache/keys/{pattern}
/api/v1/memory/cache/rate-limit/{key}
/api/v1/memory/cache/rate-limit/{key}/increment
/api/v1/memory/cache/session/context
/api/v1/memory/cache/session/context/{session_id}
/api/v1/memory/cache/session/list
/api/v1/memory/cache/set
/api/v1/memory/cache/task/context/{task_id}
/api/v1/memory/compact

F1) POSTGRES STATUS + DB LIST
-----------------------------
○ postgresql.service - PostgreSQL RDBMS
     Loaded: loaded (/usr/lib/systemd/system/postgresql.service; disabled; preset: enabled)
     Active: inactive (dead)
PostgreSQL systemd unit not found or inactive

Port 5432 listeners:
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=1511593,fd=7))

Database list (first 15):
Unable to list databases as postgres user

F2) NEO4J CONTAINER + PORTS
---------------------------
CONTAINER ID   IMAGE               STATUS                    PORTS
1080027de6e1   neo4j:5-community   Up 15 minutes (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp

Neo4j ports:
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=1511691,fd=7))
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=1511720,fd=7))

F3) NEO4J BOLT CONNECTIVITY (IF PASSWORD SET)
--------------------------------------------
Attempting Neo4j driver smoke test via python...
Neo4j Python driver test failed (driver not installed or auth error)

F4) REDIS STATUS (IF USED)
--------------------------
CONTAINER ID   IMAGE            STATUS                    PORTS
a37aecc6381b   redis:7-alpine   Up 15 minutes (healthy)   127.0.0.1:6379->6379/tcp

LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=1511562,fd=7))

G1) MEMORY SUBSTRATE DETAILED
-----------------------------
Memory stats:
{"detail":"Not Found"}
Memory GC stats:
{"detail":"Not Found"}
Semantic search test (empty query):
{"detail":"Not Found"}
G2) SLACK ADAPTER STATUS
------------------------
Slack commands endpoint:
{"detail":"Unauthorized"}Slack events endpoint:
{"detail":"Unauthorized"}
H1) PROMETHEUS STATUS
---------------------
CONTAINER ID   IMAGE                     STATUS                    PORTS
0fdefb77298c   prom/prometheus:v2.48.0   Up 15 minutes (healthy)   127.0.0.1:9090->9090/tcp
Prometheus Server is Healthy.

H2) GRAFANA STATUS
------------------
CONTAINER ID   IMAGE                    STATUS                    PORTS
3008802b6a9a   grafana/grafana:10.2.0   Up 15 minutes (healthy)   127.0.0.1:3000->3000/tcp
{
  "commit": "895fbafb7a",
  "database": "ok",
  "version": "10.2.0"
}
H3) JAEGER STATUS
-----------------
CONTAINER ID   IMAGE                           STATUS                    PORTS
355b1c8c577b   jaegertracing/all-in-one:1.52   Up 15 minutes (healthy)   4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

H4) MCP MEMORY SERVER STATUS (OPTIONAL)
---------------------------------------
CONTAINER ID   IMAGE              STATUS                    PORTS
c87b22a98af2   l9-l9-mcp-memory   Up 15 minutes (healthy)   127.0.0.1:9002->9002/tcp
{"status":"healthy","database":"connected","database_error":null,"mcp_version":"2025-03-26","index_type":"hnsw","compounding_enabled":true,"decay_enabled":true}
H5) PYTHON/UVICORN PROCESSES (OUTSIDE DOCKER)
---------------------------------------------
root        1051  0.0  0.3 109664 12800 ?        Ssl  Jan16   0:00 /usr/bin/python3 /usr/share/unattended-upgrades/unattended-upgrade-shutdown --wait-for-signal
root     1512011  0.4  2.3 401768 92628 ?        Ssl  20:10   0:04 /usr/local/bin/python3.12 /usr/local/bin/uvicorn mcp_memory.src.main:app --host 0.0.0.0 --port 9002
admin    1528798  8.0  6.4 795560 251072 ?       Ssl  20:23   0:08 /usr/local/bin/python /usr/local/bin/uvicorn api.server:app --host 0.0.0.0 --port 8000

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
