
===== 0) Context =====
Sun Feb 15 06:11:58 PM UTC 2026
C1
NAMES                IMAGE                                    STATUS                        PORTS
l9-nginx-1           nginx:alpine                             Up 45 hours                   0.0.0.0:80->80/tcp, 0.0.0.0:30379->30379/tcp, 0.0.0.0:30432->30432/tcp, 0.0.0.0:30474->30474/tcp, 0.0.0.0:30687->30687/tcp
l9-l9-api-1          ghcr.io/cryptoxdog/l9-api:4.1.0          Up 3 minutes (healthy)        127.0.0.1:8000->8000/tcp
l9-grafana           grafana/grafana:10.2.0                   Up 45 hours (healthy)         127.0.0.1:3000->3000/tcp
l9-l9-mcp-memory-1   ghcr.io/cryptoxdog/l9-mcp-memory:4.1.0   Up About a minute (healthy)   127.0.0.1:9002->9002/tcp
l9-prometheus        prom/prometheus:v2.48.0                  Up 45 hours (healthy)         127.0.0.1:9090->9090/tcp
l9-postgres          pgvector/pgvector:pg16                   Up 3 minutes (healthy)        127.0.0.1:5432->5432/tcp
l9-jaeger            jaegertracing/all-in-one:1.52            Up 45 hours (healthy)         4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-redis             redis:7-alpine                           Up 45 hours (healthy)         127.0.0.1:6379->6379/tcp
l9-neo4j             neo4j:5-community                        Up 3 minutes (healthy)        127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp

===== 1) Healthcheck definition + status =====
Healthcheck: {"Test":["CMD","curl","-f","http://localhost:8000/health"],"Interval":10000000000,"Timeout":5000000000,"StartPeriod":20000000000,"Retries":5}
State: {"Status":"healthy","FailingStreak":0,"Log":[{"Start":"2026-02-15T18:11:14.839013633Z","End":"2026-02-15T18:11:14.880110606Z","ExitCode":0,"Output":"  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\r{\"status\":\"ok\",\"service\":\"l9-api\",\"startup_ready\":true}100    55  100    55    0     0  51691      0 --:--:-- --:--:-- --:--:-- 55000\n"},{"Start":"2026-02-15T18:11:24.880575195Z","End":"2026-02-15T18:11:24.970116037Z","ExitCode":0,"Output":"  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\r100    55  100    55    0     0  30777      0 --:--:-- --:--:-- --:--:-- 55000\n{\"status\":\"ok\",\"service\":\"l9-api\",\"startup_ready\":true}"},{"Start":"2026-02-15T18:11:34.971749859Z","End":"2026-02-15T18:11:35.047023242Z","ExitCode":0,"Output":"  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\r100    55  100    55    0     0  48672      0 --:--:-- --:--:-- --:--:-- 55000\n{\"status\":\"ok\",\"service\":\"l9-api\",\"startup_ready\":true}"},{"Start":"2026-02-15T18:11:45.047843266Z","End":"2026-02-15T18:11:45.128558064Z","ExitCode":0,"Output":"  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\r100    55  100    55    0     0  31591      0 --:--:-- --:--:-- --:--:-- 55000\n{\"status\":\"ok\",\"service\":\"l9-api\",\"startup_ready\":true}"},{"Start":"2026-02-15T18:11:55.130279286Z","End":"2026-02-15T18:11:55.180526281Z","ExitCode":0,"Output":"  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\r100    55  100    55    0     0  38705      0 --:--:-- --:--:-- --:--:-- {\"status\":\"ok\",\"service\":\"l9-api\",\"startup_ready\":true}55000\n"}]}

===== 2) Last 400 API logs (errors/warnings + startup markers) =====
--- grep: fatal/error/traceback/import/runtimeerror/startup failed ---
{"event": "Redis dequeue failed: Timeout connecting to server", "logger": "runtime.redis_client", "level": "error", "timestamp": "2026-02-15T18:10:15.117785Z"}
{"event": "Redis dequeue failed: Timeout connecting to server", "logger": "runtime.redis_client", "level": "error", "timestamp": "2026-02-15T18:10:15.117937Z"}
{"event": "Redis dequeue failed: Timeout connecting to server", "logger": "runtime.redis_client", "level": "error", "timestamp": "2026-02-15T18:10:15.128279Z"}
{"event": "Redis dequeue failed: Timeout connecting to server", "logger": "runtime.redis_client", "level": "error", "timestamp": "2026-02-15T18:10:15.170314Z"}

===== 3) Probe from host to mapped port =====
*   Trying 127.0.0.1:8000...
* Connected to 127.0.0.1 (127.0.0.1) port 8000
> GET /_echo HTTP/1.1
> Host: 127.0.0.1:8000
> User-Agent: curl/8.5.0
> Accept: */*
> 
< HTTP/1.1 200 OK
< date: Sun, 15 Feb 2026 18:11:58 GMT
< server: uvicorn
< content-length: 153
< content-type: application/json
< 
* Connection #0 to host 127.0.0.1 left intact
{"system":"L9","component":"api-server","status":"alive","version":"0.5.0 (Research Factory Integration)","timestamp":"2026-02-15T18:11:58.965172+00:00"}*   Trying 127.0.0.1:8000...
* Connected to 127.0.0.1 (127.0.0.1) port 8000
> GET /health HTTP/1.1
> Host: 127.0.0.1:8000
> User-Agent: curl/8.5.0
> Accept: */*
> 
< HTTP/1.1 200 OK
< date: Sun, 15 Feb 2026 18:11:58 GMT
< server: uvicorn
< content-length: 55
< content-type: application/json
< 
* Connection #0 to host 127.0.0.1 left intact
{"status":"ok","service":"l9-api","startup_ready":true}*   Trying 127.0.0.1:8000...
* Connected to 127.0.0.1 (127.0.0.1) port 8000
> GET /health/services HTTP/1.1
> Host: 127.0.0.1:8000
> User-Agent: curl/8.5.0
> Accept: */*
> 
< HTTP/1.1 200 OK
< date: Sun, 15 Feb 2026 18:11:58 GMT
< server: uvicorn
< content-length: 283
< content-type: application/json
< 
* Connection #0 to host 127.0.0.1 left intact
{"status":"ok","services":{"housekeeping_engine":{"available":true},"virtual_context_manager":{"available":true},"consolidation_service":{"available":true},"observability_service":{"available":true},"dynamic_tool_discovery":{"synced":true,"tool_count":121,"enabled":true,"top_k":5}}}
===== 4) Probe from inside container namespace =====
inside container:
*   Trying 127.0.0.1:8000...
* Connected to 127.0.0.1 (127.0.0.1) port 8000
* using HTTP/1.x
> GET /_echo HTTP/1.1
> Host: 127.0.0.1:8000
> User-Agent: curl/8.14.1
> Accept: */*
> 
* Request completely sent off
< HTTP/1.1 200 OK
< date: Sun, 15 Feb 2026 18:11:58 GMT
< server: uvicorn
< content-length: 153
< content-type: application/json
< 
{ [153 bytes data]
* Connection #0 to host 127.0.0.1 left intact
{"system":"L9","component":"api-server","status":"alive","version":"0.5.0 (Research Factory Integration)","timestamp":"2026-02-15T18:11:59.100428+00:00"}*   Trying 127.0.0.1:8000...
* Connected to 127.0.0.1 (127.0.0.1) port 8000
* using HTTP/1.x
> GET /health HTTP/1.1
> Host: 127.0.0.1:8000
> User-Agent: curl/8.14.1
> Accept: */*
> 
* Request completely sent off
< HTTP/1.1 200 OK
< date: Sun, 15 Feb 2026 18:11:58 GMT
< server: uvicorn
< content-length: 55
< content-type: application/json
< 
{ [55 bytes data]
* Connection #0 to host 127.0.0.1 left intact
{"status":"ok","service":"l9-api","startup_ready":true}*   Trying 127.0.0.1:8000...
* Connected to 127.0.0.1 (127.0.0.1) port 8000
* using HTTP/1.x
> GET /health/services HTTP/1.1
> Host: 127.0.0.1:8000
> User-Agent: curl/8.14.1
> Accept: */*
> 
* Request completely sent off
< HTTP/1.1 200 OK
< date: Sun, 15 Feb 2026 18:11:58 GMT
< server: uvicorn
< content-length: 283
< content-type: application/json
< 
{ [283 bytes data]
* Connection #0 to host 127.0.0.1 left intact
{"status":"ok","services":{"housekeeping_engine":{"available":true},"virtual_context_manager":{"available":true},"consolidation_service":{"available":true},"observability_service":{"available":true},"dynamic_tool_discovery":{"synced":true,"tool_count":121,"enabled":true,"top_k":5}}}
===== 5) Import-chain smoke tests in running image =====
2026-02-15 18:11:59 [info     ] registry.initialized           allow_duplicates=False registry_name=singleton_services
2026-02-15 18:12:00 [info     ] registry.instance_registered   component=neo4j_client priority=0 registry=singleton_services
2026-02-15 18:12:00 [info     ] singleton_service_registry.registered category=general name=neo4j_client
2026-02-15 18:12:00 [debug    ] singleton_service_registry.closer_registered singleton=neo4j_client
2026-02-15 18:12:00 [info     ] registry.instance_registered   component=memory_substrate_repository priority=0 registry=singleton_services
2026-02-15 18:12:00 [info     ] singleton_service_registry.registered category=general name=memory_substrate_repository
2026-02-15 18:12:00 [debug    ] singleton_service_registry.closer_registered singleton=memory_substrate_repository
2026-02-15 18:12:00 [info     ] registry.instance_registered   component=housekeeping_engine priority=0 registry=singleton_services
2026-02-15 18:12:00 [info     ] singleton_service_registry.registered category=general name=housekeeping_engine
2026-02-15 18:12:00 [debug    ] tool_risk_policy.loaded        high_risk_count=13 igor_required_count=8 path=/app/config/policies/high_risk_tools.yaml safe_count=9
2026-02-15 18:12:00 [info     ] registry.instance_registered   component=memory_substrate_service priority=0 registry=singleton_services
2026-02-15 18:12:00 [info     ] singleton_service_registry.registered category=general name=memory_substrate_service
2026-02-15 18:12:00 [debug    ] singleton_service_registry.closer_registered singleton=memory_substrate_service
2026-02-15 18:12:00 [info     ] registry.instance_registered   component=ingestion_pipeline priority=0 registry=singleton_services
2026-02-15 18:12:00 [info     ] singleton_service_registry.registered category=general name=ingestion_pipeline
2026-02-15 18:12:00 [info     ] registry.instance_registered   component=insight_extraction_pipeline priority=0 registry=singleton_services
2026-02-15 18:12:00 [info     ] singleton_service_registry.registered category=general name=insight_extraction_pipeline
2026-02-15 18:12:05 [info     ] CrossEncoder available from sentence-transformers
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=retrieval_pipeline priority=0 registry=singleton_services
2026-02-15 18:12:05 [info     ] singleton_service_registry.registered category=general name=retrieval_pipeline
2026-02-15 18:12:05 [info     ] registry.initialized           allow_duplicates=False registry_name=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=redis_get priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=redis_set priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=redis_keys priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=redis_delete priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=redis_enqueue_task priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=redis_dequeue_task priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=redis_queue_size priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=redis_get_task_context priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=redis_set_task_context priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=redis_get_rate_limit priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=redis_set_rate_limit priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=redis_increment_rate_limit priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=redis_decrement_rate_limit priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] kernel_config_loader.load_kernel_config action=loading_config environment=production
2026-02-15 18:12:05 [debug    ] kernel_config_loader.load_kernel_config action=applied_env_overrides environment=production
2026-02-15 18:12:05 [info     ] kernel_config_loader.load_kernel_config action=config_loaded environment=production kernel_count=10
2026-02-15 18:12:05 [info     ] kernel_loader.config_loaded    action=loaded_externalized_config kernel_count=10 source=config/kernel_discovery.yaml
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=redis_client priority=0 registry=singleton_services
2026-02-15 18:12:05 [info     ] singleton_service_registry.registered category=general name=redis_client
2026-02-15 18:12:05 [debug    ] singleton_service_registry.closer_registered singleton=redis_client
2026-02-15 18:12:05 [info     ] WebSocketOrchestrator initialized
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=tool_registry priority=0 registry=singleton_services
2026-02-15 18:12:05 [info     ] singleton_service_registry.registered category=general name=tool_registry
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=tool_router_find priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=saga_fetch_and_enrich priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=saga_enrich_entities priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=saga_timeline_correlation priority=10 registry=tool_executors
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=saga_execute_custom priority=10 registry=tool_executors
OK  core.tools.dynamic_discovery
OK  core.agents.dynamic_tool_binding
OK  core.agents.agent_instance
2026-02-15 18:12:05 [debug    ] selfreflection.thresholds_loaded iteration_threshold=8 token_threshold=50000 tool_failure_threshold=3
OK  core.agents.executor
2026-02-15 18:12:05 [info     ] RouterRegistry initialized
2026-02-15 18:12:05 [info     ] Router registered: Agent Task Management module_id=agent_routes prefix=/agent tags=['agent']
2026-02-15 18:12:05 [info     ] registry.initialized           allow_duplicates=False registry_name=event_types
2026-02-15 18:12:05 [info     ] registry.initialized           allow_duplicates=False registry_name=mcp_servers
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=research_memory_adapter priority=0 registry=singleton_services
2026-02-15 18:12:05 [info     ] singleton_service_registry.registered category=general name=research_memory_adapter
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=tool_resolver priority=0 registry=singleton_services
2026-02-15 18:12:05 [info     ] singleton_service_registry.registered category=general name=tool_resolver
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=research_graph_runtime priority=0 registry=singleton_services
2026-02-15 18:12:05 [info     ] singleton_service_registry.registered category=general name=research_graph_runtime
2026-02-15 18:12:05 [info     ] Router registered: Research Factory API module_id=research_factory prefix= tags=['research']
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=world_model_engine priority=0 registry=singleton_services
2026-02-15 18:12:05 [info     ] singleton_service_registry.registered category=general name=world_model_engine
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=world_model_repository priority=0 registry=singleton_services
2026-02-15 18:12:05 [info     ] singleton_service_registry.registered category=general name=world_model_repository
2026-02-15 18:12:05 [info     ] registry.instance_registered   component=world_model_service priority=0 registry=singleton_services
2026-02-15 18:12:05 [info     ] singleton_service_registry.registered category=general name=world_model_service
/app/orchestrators/pattern/interface.py:88: UserWarning: Field name "schema" in "OutputContract" shadows an attribute in parent "BaseModel"
  class OutputContract(BaseModel):
2026-02-15 18:12:06 [info     ] registry.instance_registered   component=cursor_memory_kernel priority=0 registry=singleton_services
2026-02-15 18:12:06 [info     ] singleton_service_registry.registered category=general name=cursor_memory_kernel
2026-02-15 18:12:06 [info     ] Router wired: Agent Task Management module_id=agent_routes prefix=/agent
2026-02-15 18:12:06 [info     ] Router wired: Research Factory API module_id=research_factory prefix=
2026-02-15 18:12:06 [info     ] ✅ All routers wired successfully: 2 routers
2026-02-15 18:12:06 [info     ] Auto-wired 2 routers via router_registry
2026-02-15 18:12:06 [info     ] Prometheus metrics endpoint registered at /metrics
OK  api.server

===== 6) Check symbol alignment (hotfix validation) =====
2026-02-15 18:12:08 [info     ] registry.initialized           allow_duplicates=False registry_name=singleton_services
2026-02-15 18:12:08 [info     ] registry.instance_registered   component=neo4j_client priority=0 registry=singleton_services
2026-02-15 18:12:08 [info     ] singleton_service_registry.registered category=general name=neo4j_client
2026-02-15 18:12:08 [debug    ] singleton_service_registry.closer_registered singleton=neo4j_client
2026-02-15 18:12:08 [info     ] registry.instance_registered   component=memory_substrate_repository priority=0 registry=singleton_services
2026-02-15 18:12:08 [info     ] singleton_service_registry.registered category=general name=memory_substrate_repository
2026-02-15 18:12:08 [debug    ] singleton_service_registry.closer_registered singleton=memory_substrate_repository
2026-02-15 18:12:08 [info     ] registry.instance_registered   component=housekeeping_engine priority=0 registry=singleton_services
2026-02-15 18:12:08 [info     ] singleton_service_registry.registered category=general name=housekeeping_engine
2026-02-15 18:12:08 [debug    ] tool_risk_policy.loaded        high_risk_count=13 igor_required_count=8 path=/app/config/policies/high_risk_tools.yaml safe_count=9
2026-02-15 18:12:09 [info     ] registry.instance_registered   component=memory_substrate_service priority=0 registry=singleton_services
2026-02-15 18:12:09 [info     ] singleton_service_registry.registered category=general name=memory_substrate_service
2026-02-15 18:12:09 [debug    ] singleton_service_registry.closer_registered singleton=memory_substrate_service
2026-02-15 18:12:09 [info     ] registry.instance_registered   component=ingestion_pipeline priority=0 registry=singleton_services
2026-02-15 18:12:09 [info     ] singleton_service_registry.registered category=general name=ingestion_pipeline
2026-02-15 18:12:09 [info     ] registry.instance_registered   component=insight_extraction_pipeline priority=0 registry=singleton_services
2026-02-15 18:12:09 [info     ] singleton_service_registry.registered category=general name=insight_extraction_pipeline
2026-02-15 18:12:13 [info     ] CrossEncoder available from sentence-transformers
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=retrieval_pipeline priority=0 registry=singleton_services
2026-02-15 18:12:13 [info     ] singleton_service_registry.registered category=general name=retrieval_pipeline
2026-02-15 18:12:13 [info     ] registry.initialized           allow_duplicates=False registry_name=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=redis_get priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=redis_set priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=redis_keys priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=redis_delete priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=redis_enqueue_task priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=redis_dequeue_task priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=redis_queue_size priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=redis_get_task_context priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=redis_set_task_context priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=redis_get_rate_limit priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=redis_set_rate_limit priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=redis_increment_rate_limit priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=redis_decrement_rate_limit priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] kernel_config_loader.load_kernel_config action=loading_config environment=production
2026-02-15 18:12:13 [debug    ] kernel_config_loader.load_kernel_config action=applied_env_overrides environment=production
2026-02-15 18:12:13 [info     ] kernel_config_loader.load_kernel_config action=config_loaded environment=production kernel_count=10
2026-02-15 18:12:13 [info     ] kernel_loader.config_loaded    action=loaded_externalized_config kernel_count=10 source=config/kernel_discovery.yaml
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=redis_client priority=0 registry=singleton_services
2026-02-15 18:12:13 [info     ] singleton_service_registry.registered category=general name=redis_client
2026-02-15 18:12:13 [debug    ] singleton_service_registry.closer_registered singleton=redis_client
2026-02-15 18:12:13 [info     ] WebSocketOrchestrator initialized
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=tool_registry priority=0 registry=singleton_services
2026-02-15 18:12:13 [info     ] singleton_service_registry.registered category=general name=tool_registry
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=tool_router_find priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=saga_fetch_and_enrich priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=saga_enrich_entities priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=saga_timeline_correlation priority=10 registry=tool_executors
2026-02-15 18:12:13 [info     ] registry.instance_registered   component=saga_execute_custom priority=10 registry=tool_executors
has discover_tools_for_task: True
has is_dynamic_discovery_enabled: True

===== 7) Config flags that can force startup failure =====
DATABASE_URL=postgresql://postgres:8e4fXWM6Q3M87*b3@l9-postgres:5432/l9_memory
L9_API_KEY=9c4753df3b7ee85e2370b0e9a55355e59a9cf3c15f65791de4ab8cdd656b4304
L9_API_PORT=8000
L9_API_URL=http://mcp.quantumaipartners.com:30080
L9_CONSOLIDATION_INTERVAL_HOURS=4
L9_CONTAINER_ENV=true
L9_EMAIL_MULTI_ACCOUNT=true
L9_ENABLE_LEGACY_CHAT=false
L9_ENABLE_LEGACY_SLACK_ROUTER=false
L9_EXECUTOR_API_KEY=9c4753df3b7ee85e2370b0e9a55355e59a9cf3c15f65791de4ab8cdd656b4304
L9_GRAPH_AGENT_STATE=true
L9_GRAPH_WM_SYNC=true
L9_NEW_AGENT_INIT=true
L9_OBSERVABILITY=true
L9_SKIP_STARTUP_CHECKS=false
L9_STAGE3_MODULES=true
L9_STAGE4_CONSOLIDATION=true
L9_TENANT_ID=l-cto
L9_TOOL_PATTERN_EXTRACTION=true
L9_USE_KERNELS=true
L9_WM_GRAPH_SYNC=true
MEMORY_DSN=postgresql://postgres:8e4fXWM6Q3M87*b3@l9-postgres:5432/l9_memory
NEO4J_PASSWORD=FVmgaD1diPcz41zRbYLLP0UzyGvAi4E
NEO4J_URI=bolt://neo4j:7687
NEO4J_URL=bolt://neo4j:7687
NEO4J_USER=neo4j
REDIS_HOST=redis
REDIS_PASSWORD=bBZZ0JYcr6sDj3lWBK0euSLkeGAR7MT5+3PCR5LK+vM=
REDIS_PORT=6379
REDIS_URL=redis://default:bBZZ0JYcr6sDj3lWBK0euSLkeGAR7MT5+3PCR5LK+vM=@redis:6379
SLACK_APP_ENABLED=true
SLACK_APP_ID=A0A3MLBJ55Y
SLACK_BOT_TOKEN=xoxb-5756690555681-10120570028437-0GsjsVSUP0rsKfxOoHFPrpxc
SLACK_BOT_USER_ID=U0A3JGS0UCV
SLACK_CLIENT_ID=5756690555681.10123691617202
SLACK_CLIENT_SECRET=d14377ce8bf1c265f7466188791c2034
SLACK_SIGNING_SECRET=d88113146f7be4c9c63e08fbb6579f9e
SLACK_VERIFICATION_TOKEN=nFrKJ0NVekjgzIpOtpyYqUCK

===== 8) Dependency quick checks =====
MEMORY_DSN set: True
SLACK_BOT_TOKEN set: True
SLACK_SIGNING_SECRET set: True
L9_MINIMAL_MODE: None

===== 9) Image/version drift =====
ImageRef=ghcr.io/cryptoxdog/l9-api:4.1.0
ImageDigest=sha256:40f4a1c710ec66ea65efa7337ed88c2dba9a93ee21aa797c6a57ff16dfc6dc69
Python 3.12.12
Linux f7b41aeabb68 6.8.0-90-generic #91-Ubuntu SMP PREEMPT_DYNAMIC Tue Nov 18 14:14:30 UTC 2025 x86_64 GNU/Linux

===== 10) One-line diagnosis hint =====
No single obvious root cause from last 400 lines; inspect /tmp/l9-api-last400.log manually.

Done. Primary log file: /tmp/l9-api-last400.log
