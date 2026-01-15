===== L9 VPS MRI – UPDATED FULL DIAGNOSTIC =====
Wed Jan 14 08:49:14 PM UTC 2026


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
State  Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess                                   
LISTEN 0      4096       127.0.0.1:3000       0.0.0.0:*    users:(("docker-proxy",pid=263681,fd=7)) 
LISTEN 0      4096      127.0.0.54:53         0.0.0.0:*    users:(("systemd-resolve",pid=656,fd=17))
LISTEN 0      4096       127.0.0.1:9090       0.0.0.0:*    users:(("docker-proxy",pid=263292,fd=7)) 
LISTEN 0      4096       127.0.0.1:16686      0.0.0.0:*    users:(("docker-proxy",pid=263270,fd=7)) 
LISTEN 0      200       172.17.0.1:5432       0.0.0.0:*    users:(("postgres",pid=1366480,fd=7))    
LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=254331,fd=7)) 
LISTEN 0      4096       127.0.0.1:8000       0.0.0.0:*    users:(("docker-proxy",pid=323420,fd=7)) 
LISTEN 0      4096       127.0.0.1:2019       0.0.0.0:*    users:(("caddy",pid=9230,fd=15))         
LISTEN 0      4096       127.0.0.1:14268      0.0.0.0:*    users:(("docker-proxy",pid=263254,fd=7)) 
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=254300,fd=7)) 
LISTEN 0      128          0.0.0.0:22         0.0.0.0:*    users:(("sshd",pid=954,fd=3))            
LISTEN 0      128        127.0.0.1:22222      0.0.0.0:*    users:(("sshd",pid=290448,fd=7))         
LISTEN 0      4096   127.0.0.53%lo:53         0.0.0.0:*    users:(("systemd-resolve",pid=656,fd=15))
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=254283,fd=7)) 
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=254257,fd=7)) 
LISTEN 0      4096         0.0.0.0:631        0.0.0.0:*    users:(("cupsd",pid=1349,fd=9))          
LISTEN 0      4096               *:443              *:*    users:(("caddy",pid=9230,fd=19))         
LISTEN 0      128            [::1]:22222         [::]:*    users:(("sshd",pid=290448,fd=5))         
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
/dev/sda1        38G   28G  8.4G  77% /
/dev/sda1        38G   28G  8.4G  77% /
/dev/sda1        38G   28G  8.4G  77% /
/dev/sda1        38G   28G  8.4G  77% /

A5) MEMORY (RAM)
----------------
               total        used        free      shared  buff/cache   available
Mem:           3.7Gi       1.6Gi       142Mi        47Mi       2.3Gi       2.1Gi
Swap:             0B          0B          0B

A6) SYSTEM LOAD
---------------
 20:49:14 up 30 days, 17:49,  9 users,  load average: 0.33, 0.52, 0.47

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
NAME            IMAGE                           COMMAND                  SERVICE       CREATED             STATUS                       PORTS
l9-api          l9-l9-api                       "uvicorn api.server:…"   l9-api        35 seconds ago      Up 34 seconds (healthy)      127.0.0.1:8000->8000/tcp
l9-grafana      grafana/grafana:10.2.0          "/run.sh"                grafana       About an hour ago   Up About an hour (healthy)   127.0.0.1:3000->3000/tcp
l9-jaeger       jaegertracing/all-in-one:1.52   "/go/bin/all-in-one-…"   jaeger        About an hour ago   Up About an hour (healthy)   4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-neo4j        neo4j:5-community               "tini -g -- /startup…"   neo4j         About an hour ago   Up About an hour (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-postgres     pgvector/pgvector:pg16          "docker-entrypoint.s…"   l9-postgres   About an hour ago   Up About an hour (healthy)   127.0.0.1:5432->5432/tcp
l9-prometheus   prom/prometheus:v2.48.0         "/bin/prometheus --c…"   prometheus    About an hour ago   Up About an hour (healthy)   127.0.0.1:9090->9090/tcp
l9-redis        redis:7-alpine                  "docker-entrypoint.s…"   redis         About an hour ago   Up About an hour (healthy)   127.0.0.1:6379->6379/tcp

C3) CONTAINER LOGS (l9-api last 80 lines)
-----------------------------------------
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "memory_hybrid_search"}, "event": "Neo4j unavailable - tool graph disabled for 'memory_hybrid_search'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.422588Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "memory_fetch_lineage"}, "event": "Neo4j unavailable - tool graph disabled for 'memory_fetch_lineage'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.422834Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "memory_fetch_thread"}, "event": "Neo4j unavailable - tool graph disabled for 'memory_fetch_thread'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.423082Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "memory_fetch_facts_api"}, "event": "Neo4j unavailable - tool graph disabled for 'memory_fetch_facts_api'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.423360Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "memory_fetch_insights"}, "event": "Neo4j unavailable - tool graph disabled for 'memory_fetch_insights'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.423611Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "memory_gc_stats"}, "event": "Neo4j unavailable - tool graph disabled for 'memory_gc_stats'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.423864Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "gmp_run"}, "event": "Neo4j unavailable - tool graph disabled for 'gmp_run'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.424115Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "git_commit"}, "event": "Neo4j unavailable - tool graph disabled for 'git_commit'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.424390Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "mac_agent_exec_task"}, "event": "Neo4j unavailable - tool graph disabled for 'mac_agent_exec_task'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.424642Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "mcp_list_servers"}, "event": "Neo4j unavailable - tool graph disabled for 'mcp_list_servers'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.424888Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "mcp_list_tools"}, "event": "Neo4j unavailable - tool graph disabled for 'mcp_list_tools'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.425153Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "mcp_call_tool"}, "event": "Neo4j unavailable - tool graph disabled for 'mcp_call_tool'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.425426Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "mcp_discover_and_register"}, "event": "Neo4j unavailable - tool graph disabled for 'mcp_discover_and_register'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.425710Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "world_model_query"}, "event": "Neo4j unavailable - tool graph disabled for 'world_model_query'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.425962Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "kernel_read"}, "event": "Neo4j unavailable - tool graph disabled for 'kernel_read'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.426203Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "long_plan_execute"}, "event": "Neo4j unavailable - tool graph disabled for 'long_plan_execute'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.426568Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "long_plan_simulate"}, "event": "Neo4j unavailable - tool graph disabled for 'long_plan_simulate'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.426834Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "neo4j_query"}, "event": "Neo4j unavailable - tool graph disabled for 'neo4j_query'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.427092Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "redis_get"}, "event": "Neo4j unavailable - tool graph disabled for 'redis_get'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.427419Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "redis_set"}, "event": "Neo4j unavailable - tool graph disabled for 'redis_set'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.427667Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "redis_keys"}, "event": "Neo4j unavailable - tool graph disabled for 'redis_keys'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.427911Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "redis_delete"}, "event": "Neo4j unavailable - tool graph disabled for 'redis_delete'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.428150Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "redis_enqueue_task"}, "event": "Neo4j unavailable - tool graph disabled for 'redis_enqueue_task'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.428488Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "redis_dequeue_task"}, "event": "Neo4j unavailable - tool graph disabled for 'redis_dequeue_task'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.428748Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "redis_queue_size"}, "event": "Neo4j unavailable - tool graph disabled for 'redis_queue_size'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.429035Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "redis_get_task_context"}, "event": "Neo4j unavailable - tool graph disabled for 'redis_get_task_context'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.429324Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "redis_set_task_context"}, "event": "Neo4j unavailable - tool graph disabled for 'redis_set_task_context'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.429577Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "tools_list_all"}, "event": "Neo4j unavailable - tool graph disabled for 'tools_list_all'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.429874Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "tools_list_enabled"}, "event": "Neo4j unavailable - tool graph disabled for 'tools_list_enabled'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.430272Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "tools_get_metadata"}, "event": "Neo4j unavailable - tool graph disabled for 'tools_get_metadata'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.430616Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "tools_get_schema"}, "event": "Neo4j unavailable - tool graph disabled for 'tools_get_schema'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.430984Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "tools_get_by_type"}, "event": "Neo4j unavailable - tool graph disabled for 'tools_get_by_type'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.431312Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "tools_get_for_role"}, "event": "Neo4j unavailable - tool graph disabled for 'tools_get_for_role'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.431572Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "world_model_get_entity"}, "event": "Neo4j unavailable - tool graph disabled for 'world_model_get_entity'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.431818Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "world_model_list_entities"}, "event": "Neo4j unavailable - tool graph disabled for 'world_model_list_entities'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.432063Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "world_model_snapshot"}, "event": "Neo4j unavailable - tool graph disabled for 'world_model_snapshot'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.432334Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "world_model_list_snapshots"}, "event": "Neo4j unavailable - tool graph disabled for 'world_model_list_snapshots'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.432665Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "world_model_send_insights"}, "event": "Neo4j unavailable - tool graph disabled for 'world_model_send_insights'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.433055Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "world_model_get_state_version"}, "event": "Neo4j unavailable - tool graph disabled for 'world_model_get_state_version'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.433479Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "symbolic_compute"}, "event": "Neo4j unavailable - tool graph disabled for 'symbolic_compute'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.433856Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "symbolic_codegen"}, "event": "Neo4j unavailable - tool graph disabled for 'symbolic_codegen'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.434281Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "symbolic_optimize"}, "event": "Neo4j unavailable - tool graph disabled for 'symbolic_optimize'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.434673Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "simulation"}, "event": "Neo4j unavailable - tool graph disabled for 'simulation'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.435072Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "mcp_start_server"}, "event": "Neo4j unavailable - tool graph disabled for 'mcp_start_server'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.435497Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "mcp_stop_server"}, "event": "Neo4j unavailable - tool graph disabled for 'mcp_stop_server'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.435851Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "mcp_stop_all_servers"}, "event": "Neo4j unavailable - tool graph disabled for 'mcp_stop_all_servers'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.436132Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "redis_get_rate_limit"}, "event": "Neo4j unavailable - tool graph disabled for 'redis_get_rate_limit'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.436420Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "redis_set_rate_limit"}, "event": "Neo4j unavailable - tool graph disabled for 'redis_set_rate_limit'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.436714Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "redis_increment_rate_limit"}, "event": "Neo4j unavailable - tool graph disabled for 'redis_increment_rate_limit'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.436959Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "redis_decrement_rate_limit"}, "event": "Neo4j unavailable - tool graph disabled for 'redis_decrement_rate_limit'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.437198Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "memory_get_checkpoint"}, "event": "Neo4j unavailable - tool graph disabled for 'memory_get_checkpoint'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.437465Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "memory_trigger_world_model_update"}, "event": "Neo4j unavailable - tool graph disabled for 'memory_trigger_world_model_update'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.437770Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "memory_health_check"}, "event": "Neo4j unavailable - tool graph disabled for 'memory_health_check'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.438043Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "tools_get_api_dependents"}, "event": "Neo4j unavailable - tool graph disabled for 'tools_get_api_dependents'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.438326Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "tools_get_dependencies"}, "event": "Neo4j unavailable - tool graph disabled for 'tools_get_dependencies'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.438630Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "tools_get_blast_radius"}, "event": "Neo4j unavailable - tool graph disabled for 'tools_get_blast_radius'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.438965Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "tools_detect_circular_deps"}, "event": "Neo4j unavailable - tool graph disabled for 'tools_detect_circular_deps'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.439462Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "tools_get_catalog"}, "event": "Neo4j unavailable - tool graph disabled for 'tools_get_catalog'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.439754Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "world_model_restore"}, "event": "Neo4j unavailable - tool graph disabled for 'world_model_restore'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.440016Z"}
l9-api  | {"extra": {"alert": "neo4j_unavailable", "tool_name": "world_model_list_updates"}, "event": "Neo4j unavailable - tool graph disabled for 'world_model_list_updates'. Governance queries (blast radius, dependencies) unavailable.", "logger": "core.tools.tool_graph", "level": "warning", "timestamp": "2026-01-14T20:48:47.440300Z"}
l9-api  | {"event": "\u26a0\ufe0f Stage 5 not started: neo4j_client not available", "logger": "api.server", "level": "warning", "timestamp": "2026-01-14T20:48:47.444815Z"}
l9-api  | {"event": "Neo4j driver not configured for GraphToWorldModelSync", "logger": "core.integration.graph_to_wm_sync", "level": "warning", "timestamp": "2026-01-14T20:48:47.452048Z"}
l9-api  | {"event": "No graph state found for agent L", "logger": "core.integration.graph_to_wm_sync", "level": "warning", "timestamp": "2026-01-14T20:48:47.452172Z"}
l9-api  | INFO:     Application startup complete.
l9-api  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
l9-api  | INFO:     127.0.0.1:36358 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.6:37618 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.6:37618 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.1:55702 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     127.0.0.1:53360 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.1:43034 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.1:43048 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.1:43050 - "GET /openapi.json HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.1:43052 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.6:52082 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.6:52082 - "GET /metrics/ HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.1:43048 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     127.0.0.1:50404 - "GET /health HTTP/1.1" 200 OK
l9-api  | INFO:     172.18.0.6:57722 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api  | INFO:     172.18.0.6:57722 - "GET /metrics/ HTTP/1.1" 200 OK

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
LISTEN 0      4096       127.0.0.1:8000       0.0.0.0:*    users:(("docker-proxy",pid=323420,fd=7)) 
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=254300,fd=7)) 
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=254283,fd=7)) 
LISTEN 0      4096       127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=254257,fd=7)) 
LISTEN 0      4096               *:9001             *:*    users:(("caddy",pid=9230,fd=20))         
LISTEN 0      200            [::1]:5432          [::]:*    users:(("postgres",pid=1366480,fd=6))    

C5) DOCKER IMAGES
-----------------
REPOSITORY                 TAG           SIZE
l9-l9-api                  latest        1.31GB
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
2026-01-14 20:48:44 [debug    ] selfreflection.thresholds_loaded iteration_threshold=8 token_threshold=50000 tool_failure_threshold=3
{"event": "Seed loading failed: 'NoneType' object is not iterable", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-01-14T20:48:47.064818Z"}
{"event": "Neo4j connection failed: Couldn't connect to localhost:7687 (resolved to ('[::1]:7687', '127.0.0.1:7687')):\nFailed to establish connection to ResolvedIPv6Address(('::1', 7687, 0, 0)) (reason [Errno 111] Connect call failed ('::1', 7687, 0, 0))\nFailed to establish connection to ResolvedIPv4Address(('127.0.0.1', 7687)) (reason [Errno 111] Connect call failed ('127.0.0.1', 7687))", "logger": "memory.graph_client", "level": "warning", "timestamp": "2026-01-14T20:48:47.066053Z"}
{"event": "store_insights_node: Failed to store: invalid input syntax for type json\nDETAIL:  Token \"audit\" is invalid.", "logger": "memory.substrate_dag", "level": "error", "timestamp": "2026-01-14T20:48:47.252718Z"}
--- l9-postgres ---
2026-01-14 20:48:47.251 UTC [6827] ERROR:  invalid input syntax for type json
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
298:  neo4j_data:
300:    name: l9-neo4j-data
301:  neo4j_logs:
303:    name: l9-neo4j-logs

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
2a06:98c1:3120::3 l9.quantumaipartners.com
2a06:98c1:3121::3 l9.quantumaipartners.com

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
/api/v1/memory/consolidation/run
/api/v1/memory/facts
/api/v1/memory/gc/run
/api/v1/memory/gc/stats
/api/v1/memory/graph/context/{domain}
/api/v1/memory/graph/entity
/api/v1/memory/graph/entity/{entity_type}/{entity_id}

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
CONTAINER ID   IMAGE               STATUS                       PORTS
18f7d5684f9f   neo4j:5-community   Up About an hour (healthy)   127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp

Neo4j ports:
LISTEN 0      4096       127.0.0.1:7687       0.0.0.0:*    users:(("docker-proxy",pid=254300,fd=7)) 
LISTEN 0      4096       127.0.0.1:7474       0.0.0.0:*    users:(("docker-proxy",pid=254283,fd=7)) 

F3) NEO4J BOLT CONNECTIVITY (IF PASSWORD SET)
--------------------------------------------
Attempting Neo4j driver smoke test via python...
Neo4j Python driver test failed (driver not installed or auth error)

F4) REDIS STATUS (IF USED)
--------------------------
CONTAINER ID   IMAGE            STATUS                       PORTS
4c5d09fdf245   redis:7-alpine   Up About an hour (healthy)   127.0.0.1:6379->6379/tcp

LISTEN 0      4096       127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=254331,fd=7)) 

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
CONTAINER ID   IMAGE                     STATUS                       PORTS
b8e4d7cf9509   prom/prometheus:v2.48.0   Up About an hour (healthy)   127.0.0.1:9090->9090/tcp
Prometheus Server is Healthy.

H2) GRAFANA STATUS
------------------
CONTAINER ID   IMAGE                    STATUS                       PORTS
0e619ad97f39   grafana/grafana:10.2.0   Up About an hour (healthy)   127.0.0.1:3000->3000/tcp
{
  "commit": "895fbafb7a",
  "database": "ok",
  "version": "10.2.0"
}
H3) JAEGER STATUS
-----------------
CONTAINER ID   IMAGE                           STATUS                       PORTS
027456ea4a1a   jaegertracing/all-in-one:1.52   Up About an hour (healthy)   4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
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
admin     323369 18.2  5.6 763464 219076 ?       Ssl  20:48   0:06 /usr/local/bin/python /usr/local/bin/uvicorn api.server:app --host 0.0.0.0 --port 8000

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
