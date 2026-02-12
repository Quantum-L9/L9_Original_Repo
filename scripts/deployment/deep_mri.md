═══════════════════════════════════════════════════════════════════════════
L9 Deep MRI - C1 Production VPS
Timestamp: 2026-02-12T17:27:11Z
═══════════════════════════════════════════════════════════════════════════

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. SYSTEM OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Hostname: C1
Uptime: up 2 weeks, 6 days, 21 hours, 4 minutes
Kernel: 6.8.0-90-generic
Load Average:  0.27, 0.39, 0.99

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. DOCKER INFRASTRUCTURE (9 Containers)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NAME                STATUS  <no  value>             
l9-grafana          Up      26   hours   (healthy)  healthy
l9-jaeger           Up      27   hours   (healthy)  healthy
l9-l9-api-1         Up      12   hours   (healthy)  healthy
l9-l9-mcp-memory-1  Up      22   hours   (healthy)  healthy
l9-neo4j            Up      27   hours   (healthy)  healthy
l9-nginx-1          Up      26   hours              
l9-postgres         Up      27   hours   (healthy)  healthy
l9-prometheus       Up      27   hours   (healthy)  healthy
l9-redis            Up      27   hours   (healthy)  healthy

Docker Daemon Status:
     Active: active (running) since Mon 2026-02-02 18:29:22 UTC; 1 week 2 days ago
      Tasks: 164
     Memory: 1.4G (peak: 4.6G)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. CONTAINER RESOURCE USAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NAME                 CPU %     MEM USAGE / LIMIT     NET I/O
l9-l9-api-1          1.10%     2.01GiB / 4GiB        8.52GB / 26.7GB
l9-l9-mcp-memory-1   0.50%     252.9MiB / 1GiB       4.86MB / 12.4MB
l9-nginx-1           0.00%     4.039MiB / 7.564GiB   1.57MB / 1.58MB
l9-grafana           2.91%     96.85MiB / 7.564GiB   2.15MB / 478kB
l9-postgres          0.00%     218.6MiB / 7.564GiB   54.9GB / 6.13GB
l9-prometheus        0.00%     51.98MiB / 7.564GiB   320MB / 15.9MB
l9-jaeger            0.03%     15.69MiB / 7.564GiB   5.89MB / 270MB
l9-redis             0.68%     5.473MiB / 7.564GiB   34.5MB / 13.1MB
l9-neo4j             0.74%     1.13GiB / 7.564GiB    37.3MB / 34.6MB

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. NETWORK CONNECTIVITY (127.0.0.1 Ports)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Port 8000 OPEN
✓ Port 5432 OPEN
✓ Port 6379 OPEN
✓ Port 7474 OPEN
✓ Port 7687 OPEN
✓ Port 9090 OPEN
✓ Port 3000 OPEN
✓ Port 16686 OPEN
✓ Port 9002 OPEN

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5. DATABASE SUBSTRATE HEALTH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PostgreSQL:
✗ Query failed
✗ Table count failed

Redis:
NOAUTH Authentication required.

✗ Stats failed

Neo4j:
✗ HTTP endpoint failed

MCP Memory Server:
healthy

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. L9 API HEALTH (Core Endpoints)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GET /
L9 Phase 2 AI OS
GET /health
ok
GET /health/startup
unknown
GET /health/neo4j
healthy
GET /health/services
ok
POST /kernels/reload (requires auth)
true
POST /lchat (requires auth)
completed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7. GIT STATE (/opt/l9)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Branch: main
Commit: 04a3f200
Commit Date: 2026-02-12 01:12:00 -0400
Status:
 M scripts/e2e_test_GODMODE.sh
?? scripts/deployment/deep_mri.sh

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8. DISK USAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/dev/sda1       150G   46G   99G  32% /

Docker Volumes:
l9-grafana-data                                                    local     N/A
l9-grafana-data-prod                                               local     N/A
l9-jaeger-data-prod                                                local     N/A
l9-neo4j-data                                                      local     N/A
l9-neo4j-data-prod                                                 local     N/A
l9-neo4j-logs                                                      local     N/A
l9-neo4j-logs-prod                                                 local     N/A
l9-postgres-data                                                   local     N/A
l9-postgres-data-prod                                              local     N/A
l9-prometheus-data                                                 local     N/A
l9-prometheus-data-prod                                            local     N/A
l9-redis-data                                                      local     N/A
l9-redis-data-prod                                                 local     N/A

Docker System Usage:
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          35        9         10.16GB   7.404GB (72%)
Containers      10        9         137.1MB   0B (0%)
Local Volumes   33        7         25.3GB    614.4MB (2%)
Build Cache     94        0         6.217GB   39.08MB

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
9. RECENT LOGS (Last 10 lines per critical service)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

=== l9-api ===
l9-api-1  | {"event": "ActiveMemoryEncoder initialized", "logger": "memory.active_encoder", "level": "info", "timestamp": "2026-02-12T17:27:18.902591Z"}
l9-api-1  | {"task_id": "4b836998-2312-403c-8227-3c7855d2f192", "task_type": "query", "event": "Processing task completion", "logger": "memory.active_encoder", "level": "info", "timestamp": "2026-02-12T17:27:18.902669Z"}
l9-api-1  | {"facts_created": 0, "facts_updated": 0, "episodes_created": 0, "event": "Task completion processing complete", "logger": "memory.active_encoder", "level": "info", "timestamp": "2026-02-12T17:27:18.902827Z"}
l9-api-1  | {"reflection_id": "562c188a-85a4-43df-b69b-ffbdb53523e9", "task_id": "4b836998-2312-403c-8227-3c7855d2f192", "gaps_count": 0, "kernel_update_needed": false, "duration_ms": 0.017881393432617188, "event": "selfreflection.analysis_complete", "logger": "core.agents.selfreflection", "level": "info", "timestamp": "2026-02-12T17:27:18.903056Z"}
l9-api-1  | {"task_id": "4b836998-2312-403c-8227-3c7855d2f192", "error": "'ReflectionResult' object has no attribute 'summary'", "event": "executor.self_reflection.persist_failed", "logger": "core.agents.executor", "level": "warning", "timestamp": "2026-02-12T17:27:18.903175Z"}
l9-api-1  | {"event": "  \u2713 agent.start_task               4273.19ms  (trace: 9b3cc5ef...)", "logger": "core.observability.exporters", "level": "info", "timestamp": "2026-02-12T17:27:18.903498Z"}
l9-api-1  | INFO:     172.18.0.1:60232 - "POST /lchat HTTP/1.1" 200 OK
l9-api-1  | {"agent": "*", "event": "No subscribers for agent", "logger": "core.coordination.event_queue", "level": "warning", "timestamp": "2026-02-12T17:27:18.904149Z"}
l9-api-1  | INFO:     172.18.0.4:37726 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
l9-api-1  | INFO:     172.18.0.4:37726 - "GET /metrics/ HTTP/1.1" 200 OK

=== postgres ===

=== neo4j ===
l9-neo4j  | 2026-02-11 14:57:07.267+0000 INFO  ======== Neo4j 5.26.20 ========
l9-neo4j  | 2026-02-11 14:57:09.316+0000 INFO  Anonymous Usage Data is being sent to Neo4j, see https://neo4j.com/docs/usage-data/
l9-neo4j  | 2026-02-11 14:57:09.356+0000 INFO  Bolt enabled on 0.0.0.0:7687.
l9-neo4j  | 2026-02-11 14:57:09.899+0000 INFO  HTTP enabled on 0.0.0.0:7474.
l9-neo4j  | 2026-02-11 14:57:09.899+0000 INFO  Remote interface available at http://localhost:7474/
l9-neo4j  | 2026-02-11 14:57:09.901+0000 INFO  id: 27B86261B0CAB781959BA84831057F93AF55C6EB3EC5C2AC09CB3B070FC73986
l9-neo4j  | 2026-02-11 14:57:09.901+0000 INFO  name: system
l9-neo4j  | 2026-02-11 14:57:09.902+0000 INFO  creationDate: 2026-01-29T00:43:49.366Z
l9-neo4j  | 2026-02-11 14:57:09.902+0000 INFO  Started.
l9-neo4j  | 2026-02-12 04:42:38.369+0000 WARN  [bolt-8426] The client is unauthorized due to authentication failure.

=== redis ===
l9-redis  | 1:M 12 Feb 2026 15:45:09.093 * 1 changes in 3600 seconds. Saving...
l9-redis  | 1:M 12 Feb 2026 15:45:09.095 * Background saving started by pid 104268
l9-redis  | 104268:C 12 Feb 2026 15:45:09.099 * DB saved on disk
l9-redis  | 104268:C 12 Feb 2026 15:45:09.100 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
l9-redis  | 1:M 12 Feb 2026 15:45:09.197 * Background saving terminated with success
l9-redis  | 1:M 12 Feb 2026 16:45:10.068 * 1 changes in 3600 seconds. Saving...
l9-redis  | 1:M 12 Feb 2026 16:45:10.069 * Background saving started by pid 108349
l9-redis  | 108349:C 12 Feb 2026 16:45:10.075 * DB saved on disk
l9-redis  | 108349:C 12 Feb 2026 16:45:10.076 * Fork CoW for RDB: current 0 MB, peak 0 MB, average 0 MB
l9-redis  | 1:M 12 Feb 2026 16:45:10.170 * Background saving terminated with success

=== mcp-memory ===

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
10. OBSERVABILITY STACK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Prometheus:
Prometheus Server is Healthy.
✓ Healthy
Grafana:
ok
Jaeger:
✓ UI responsive

═══════════════════════════════════════════════════════════════════════════
MRI COMPLETE
═══════════════════════════════════════════════════════════════════════════
Container Count: 9
Healthy Containers: 8
Open Ports: 9
Timestamp: 2026-02-12T17:27:19Z
═══════════════════════════════════════════════════════════════════════════