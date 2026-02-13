
===== 0) Context =====
Fri Feb 13 06:16:45 PM UTC 2026
C1
NAMES                IMAGE                                    STATUS                     PORTS
l9-l9-api-1          ghcr.io/cryptoxdog/l9-api:4.1.0          Up 4 minutes (unhealthy)   127.0.0.1:8000->8000/tcp
l9-l9-mcp-memory-1   ghcr.io/cryptoxdog/l9-mcp-memory:4.1.0   Up 6 hours (healthy)       127.0.0.1:9002->9002/tcp
l9-postgres          pgvector/pgvector:pg16                   Up 6 hours (healthy)       127.0.0.1:5432->5432/tcp
l9-nginx-1           nginx:alpine                             Up 14 hours                0.0.0.0:80->80/tcp, 0.0.0.0:30379->30379/tcp, 0.0.0.0:30432->30432/tcp, 0.0.0.0:30474->30474/tcp, 0.0.0.0:30687->30687/tcp
l9-grafana           grafana/grafana:10.2.0                   Up 14 hours (healthy)      127.0.0.1:3000->3000/tcp
l9-jaeger            jaegertracing/all-in-one:1.52            Up 14 hours (healthy)      4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-redis             redis:7-alpine                           Up 14 hours (healthy)      127.0.0.1:6379->6379/tcp
l9-prometheus        prom/prometheus:v2.48.0                  Up 14 hours (healthy)      127.0.0.1:9090->9090/tcp
l9-neo4j             neo4j:5-community                        Up 14 hours (healthy)      127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp

===== 1) Healthcheck definition + status =====
Healthcheck: {"Test":["CMD","curl","-f","http://localhost:8000/health"],"Interval":10000000000,"Timeout":5000000000,"StartPeriod":20000000000,"Retries":5}
State: {"Status":"unhealthy","FailingStreak":24,"Log":[{"Start":"2026-02-13T18:16:00.273550541Z","End":"2026-02-13T18:16:00.406753273Z","ExitCode":7,"Output":"  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (7) Failed to connect to localhost port 8000 after 0 ms: Could not connect to server\n"},{"Start":"2026-02-13T18:16:10.407712313Z","End":"2026-02-13T18:16:10.570842232Z","ExitCode":7,"Output":"  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (7) Failed to connect to localhost port 8000 after 0 ms: Could not connect to server\n"},{"Start":"2026-02-13T18:16:20.571225979Z","End":"2026-02-13T18:16:20.700579929Z","ExitCode":7,"Output":"  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (7) Failed to connect to localhost port 8000 after 0 ms: Could not connect to server\n"},{"Start":"2026-02-13T18:16:30.701189771Z","End":"2026-02-13T18:16:30.869859562Z","ExitCode":7,"Output":"  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (7) Failed to connect to localhost port 8000 after 0 ms: Could not connect to server\n"},{"Start":"2026-02-13T18:16:40.871415804Z","End":"2026-02-13T18:16:40.995394424Z","ExitCode":7,"Output":"  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n                                 Dload  Upload   Total   Spent    Left  Speed\n\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\ncurl: (7) Failed to connect to localhost port 8000 after 3 ms: Could not connect to server\n"}]}

===== 2) Last 400 API logs (errors/warnings + startup markers) =====
--- grep: fatal/error/traceback/import/runtimeerror/startup failed ---
{"success_count": 12, "error_count": 8, "errors": ["cursor: missing ['cursor_executor']", "eval: missing ['evaluator']", "pattern: missing ['pattern_orchestrator']", "reasoning: missing ['reasoning_orchestrator']", "reflection_agent: missing ['reflection_agent']", "research_agent: missing ['research_agent']", "research_swarm: missing ['research_swarm_orchestrator']", "worldmodel: missing ['world_model_service']"], "event": "Router wiring completed with errors", "logger": "api.routes.registry", "level": "warning", "timestamp": "2026-02-13T18:16:42.166556Z"}
{"event": "Migrations complete: 0 applied, 32 skipped, 0 errors", "logger": "api.server", "level": "info", "timestamp": "2026-02-13T18:16:42.271089Z"}
{"event_type": "checkpoint_restored", "agent_id": "l9-standard-v1", "error": "Governance context required for memory operation: write_packet", "event": "Failed to emit checkpoint packet", "logger": "memory.agent_persistence", "level": "warning", "timestamp": "2026-02-13T18:16:42.380929Z"}
{"success_count": 12, "error_count": 8, "errors": ["cursor: missing ['cursor_executor']", "eval: missing ['evaluator']", "pattern: missing ['pattern_orchestrator']", "reasoning: missing ['reasoning_orchestrator']", "reflection_agent: missing ['reflection_agent']", "research_agent: missing ['research_agent']", "research_swarm: missing ['research_swarm_orchestrator']", "worldmodel: missing ['world_model_service']"], "event": "Router wiring completed with errors", "logger": "api.routes.registry", "level": "warning", "timestamp": "2026-02-13T18:16:42.391268Z"}
{"event": "Migrations complete: 0 applied, 32 skipped, 0 errors", "logger": "api.server", "level": "info", "timestamp": "2026-02-13T18:16:42.489196Z"}
{"event_type": "checkpoint_restored", "agent_id": "l9-standard-v1", "error": "Governance context required for memory operation: write_packet", "event": "Failed to emit checkpoint packet", "logger": "memory.agent_persistence", "level": "warning", "timestamp": "2026-02-13T18:16:42.596306Z"}
ERROR:    Traceback (most recent call last):
    raise RuntimeError(
RuntimeError: Agent Executor required for Slack routing but failed to initialize. Fix initialization or check dependencies. Set L9_MINIMAL_MODE=true to start in minimal mode.
ERROR:    Application startup failed. Exiting.
ERROR:    Traceback (most recent call last):
    raise RuntimeError(
RuntimeError: Agent Executor required for Slack routing but failed to initialize. Fix initialization or check dependencies. Set L9_MINIMAL_MODE=true to start in minimal mode.
ERROR:    Application startup failed. Exiting.

===== 3) Probe from host to mapped port =====
*   Trying 127.0.0.1:8000...
* Connected to 127.0.0.1 (127.0.0.1) port 8000
> GET /_echo HTTP/1.1
> Host: 127.0.0.1:8000
> User-Agent: curl/8.5.0
> Accept: */*
> 
* Recv failure: Connection reset by peer
* Closing connection
*   Trying 127.0.0.1:8000...
* Connected to 127.0.0.1 (127.0.0.1) port 8000
> GET /health HTTP/1.1
> Host: 127.0.0.1:8000
> User-Agent: curl/8.5.0
> Accept: */*
> 
* Recv failure: Connection reset by peer
* Closing connection
*   Trying 127.0.0.1:8000...
* Connected to 127.0.0.1 (127.0.0.1) port 8000
> GET /health/services HTTP/1.1
> Host: 127.0.0.1:8000
> User-Agent: curl/8.5.0
> Accept: */*
> 
* Recv failure: Connection reset by peer
* Closing connection

===== 4) Probe from inside container namespace =====
inside container:
*   Trying 127.0.0.1:8000...
* connect to 127.0.0.1 port 8000 from 127.0.0.1 port 41688 failed: Connection refused
* Failed to connect to 127.0.0.1 port 8000 after 0 ms: Could not connect to server
* closing connection #0
*   Trying 127.0.0.1:8000...
* connect to 127.0.0.1 port 8000 from 127.0.0.1 port 41700 failed: Connection refused
* Failed to connect to 127.0.0.1 port 8000 after 0 ms: Could not connect to server
* closing connection #0
*   Trying 127.0.0.1:8000...
* connect to 127.0.0.1 port 8000 from 127.0.0.1 port 41716 failed: Connection refused
* Failed to connect to 127.0.0.1 port 8000 after 0 ms: Could not connect to server
* closing connection #0

===== 5) Import-chain smoke tests in running image =====
2026-02-13 18:16:46 [info     ] registry.initialized           allow_duplicates=False registry_name=singleton_services
2026-02-13 18:16:47 [info     ] registry.instance_registered   component=neo4j_client priority=0 registry=singleton_services
2026-02-13 18:16:47 [info     ] singleton_service_registry.registered category=general name=neo4j_client
2026-02-13 18:16:47 [debug    ] singleton_service_registry.closer_registered singleton=neo4j_client
2026-02-13 18:16:47 [info     ] registry.instance_registered   component=memory_substrate_repository priority=0 registry=singleton_services
2026-02-13 18:16:47 [info     ] singleton_service_registry.registered category=general name=memory_substrate_repository
2026-02-13 18:16:47 [debug    ] singleton_service_registry.closer_registered singleton=memory_substrate_repository
2026-02-13 18:16:47 [info     ] registry.instance_registered   component=housekeeping_engine priority=0 registry=singleton_services
2026-02-13 18:16:47 [info     ] singleton_service_registry.registered category=general name=housekeeping_engine
2026-02-13 18:16:47 [debug    ] tool_risk_policy.loaded        high_risk_count=13 igor_required_count=8 path=/app/config/policies/high_risk_tools.yaml safe_count=9
2026-02-13 18:16:48 [info     ] registry.instance_registered   component=memory_substrate_service priority=0 registry=singleton_services
2026-02-13 18:16:48 [info     ] singleton_service_registry.registered category=general name=memory_substrate_service
2026-02-13 18:16:48 [debug    ] singleton_service_registry.closer_registered singleton=memory_substrate_service
2026-02-13 18:16:48 [info     ] registry.instance_registered   component=ingestion_pipeline priority=0 registry=singleton_services
2026-02-13 18:16:48 [info     ] singleton_service_registry.registered category=general name=ingestion_pipeline
2026-02-13 18:16:48 [info     ] registry.instance_registered   component=insight_extraction_pipeline priority=0 registry=singleton_services
2026-02-13 18:16:48 [info     ] singleton_service_registry.registered category=general name=insight_extraction_pipeline
2026-02-13 18:16:59 [info     ] CrossEncoder available from sentence-transformers
2026-02-13 18:16:59 [info     ] registry.instance_registered   component=retrieval_pipeline priority=0 registry=singleton_services
2026-02-13 18:16:59 [info     ] singleton_service_registry.registered category=general name=retrieval_pipeline
2026-02-13 18:16:59 [info     ] registry.initialized           allow_duplicates=False registry_name=tool_executors
2026-02-13 18:16:59 [info     ] registry.instance_registered   component=redis_get priority=10 registry=tool_executors
2026-02-13 18:16:59 [info     ] registry.instance_registered   component=redis_set priority=10 registry=tool_executors
2026-02-13 18:16:59 [info     ] registry.instance_registered   component=redis_keys priority=10 registry=tool_executors
2026-02-13 18:16:59 [info     ] registry.instance_registered   component=redis_delete priority=10 registry=tool_executors
2026-02-13 18:16:59 [info     ] registry.instance_registered   component=redis_enqueue_task priority=10 registry=tool_executors
2026-02-13 18:16:59 [info     ] registry.instance_registered   component=redis_dequeue_task priority=10 registry=tool_executors
2026-02-13 18:16:59 [info     ] registry.instance_registered   component=redis_queue_size priority=10 registry=tool_executors
2026-02-13 18:16:59 [info     ] registry.instance_registered   component=redis_get_task_context priority=10 registry=tool_executors
2026-02-13 18:16:59 [info     ] registry.instance_registered   component=redis_set_task_context priority=10 registry=tool_executors
2026-02-13 18:16:59 [info     ] registry.instance_registered   component=redis_get_rate_limit priority=10 registry=tool_executors
2026-02-13 18:16:59 [info     ] registry.instance_registered   component=redis_set_rate_limit priority=10 registry=tool_executors
2026-02-13 18:16:59 [info     ] registry.instance_registered   component=redis_increment_rate_limit priority=10 registry=tool_executors
2026-02-13 18:16:59 [info     ] registry.instance_registered   component=redis_decrement_rate_limit priority=10 registry=tool_executors
2026-02-13 18:16:59 [info     ] kernel_config_loader.load_kernel_config action=loading_config environment=production
2026-02-13 18:16:59 [debug    ] kernel_config_loader.load_kernel_config action=applied_env_overrides environment=production
2026-02-13 18:16:59 [info     ] kernel_config_loader.load_kernel_config action=config_loaded environment=production kernel_count=10
2026-02-13 18:16:59 [info     ] kernel_loader.config_loaded    action=loaded_externalized_config kernel_count=10 source=config/kernel_discovery.yaml
2026-02-13 18:17:00 [info     ] registry.instance_registered   component=redis_client priority=0 registry=singleton_services
2026-02-13 18:17:00 [info     ] singleton_service_registry.registered category=general name=redis_client
2026-02-13 18:17:00 [debug    ] singleton_service_registry.closer_registered singleton=redis_client
2026-02-13 18:17:00 [info     ] WebSocketOrchestrator initialized
2026-02-13 18:17:00 [info     ] registry.instance_registered   component=tool_registry priority=0 registry=singleton_services
2026-02-13 18:17:00 [info     ] singleton_service_registry.registered category=general name=tool_registry
2026-02-13 18:17:00 [info     ] registry.instance_registered   component=tool_router_find priority=10 registry=tool_executors
2026-02-13 18:17:00 [info     ] registry.instance_registered   component=saga_fetch_and_enrich priority=10 registry=tool_executors
2026-02-13 18:17:00 [info     ] registry.instance_registered   component=saga_enrich_entities priority=10 registry=tool_executors
2026-02-13 18:17:00 [info     ] registry.instance_registered   component=saga_timeline_correlation priority=10 registry=tool_executors
2026-02-13 18:17:00 [info     ] registry.instance_registered   component=saga_execute_custom priority=10 registry=tool_executors
FAIL core.tools.dynamic_discovery: cannot import name 'get_tool_registry' from 'runtime.tool_registry' (/app/runtime/tool_registry.py)
Traceback (most recent call last):
  File "<stdin>", line 11, in <module>
  File "/usr/local/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1310, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 999, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "/app/core/tools/__init__.py", line 72, in <module>
    from core.tools.registry_adapter import (
  File "/app/core/tools/registry_adapter.py", line 124, in <module>
    from core.agents.schemas import ToolBinding, ToolCallResult
  File "/app/core/agents/__init__.py", line 43, in <module>
    from core.agents.dynamic_tool_binding import (
  File "/app/core/agents/dynamic_tool_binding.py", line 47, in <module>
    from runtime.tool_registry import get_tool_registry
ImportError: cannot import name 'get_tool_registry' from 'runtime.tool_registry' (/app/runtime/tool_registry.py). Did you mean: 'tool_registry'?
FAIL core.agents.dynamic_tool_binding: cannot import name 'get_tool_registry' from 'runtime.tool_registry' (/app/runtime/tool_registry.py)
Traceback (most recent call last):
  File "<stdin>", line 11, in <module>
  File "/usr/local/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1310, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 999, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "/app/core/agents/__init__.py", line 43, in <module>
    from core.agents.dynamic_tool_binding import (
  File "/app/core/agents/dynamic_tool_binding.py", line 47, in <module>
    from runtime.tool_registry import get_tool_registry
ImportError: cannot import name 'get_tool_registry' from 'runtime.tool_registry' (/app/runtime/tool_registry.py). Did you mean: 'tool_registry'?
OK  core.agents.agent_instance
FAIL core.agents.executor: cannot import name 'get_tool_registry' from 'runtime.tool_registry' (/app/runtime/tool_registry.py)
Traceback (most recent call last):
  File "<stdin>", line 11, in <module>
  File "/usr/local/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1310, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 999, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "/app/core/agents/__init__.py", line 43, in <module>
    from core.agents.dynamic_tool_binding import (
  File "/app/core/agents/dynamic_tool_binding.py", line 47, in <module>
    from runtime.tool_registry import get_tool_registry
ImportError: cannot import name 'get_tool_registry' from 'runtime.tool_registry' (/app/runtime/tool_registry.py). Did you mean: 'tool_registry'?
2026-02-13 18:17:02 [info     ] RouterRegistry initialized
2026-02-13 18:17:02 [info     ] Router registered: Agent Task Management module_id=agent_routes prefix=/agent tags=['agent']
2026-02-13 18:17:02 [info     ] registry.initialized           allow_duplicates=False registry_name=event_types
2026-02-13 18:17:02 [info     ] registry.initialized           allow_duplicates=False registry_name=mcp_servers
2026-02-13 18:17:02 [info     ] registry.instance_registered   component=research_memory_adapter priority=0 registry=singleton_services
2026-02-13 18:17:02 [info     ] singleton_service_registry.registered category=general name=research_memory_adapter
2026-02-13 18:17:02 [info     ] registry.instance_registered   component=tool_resolver priority=0 registry=singleton_services
2026-02-13 18:17:02 [info     ] singleton_service_registry.registered category=general name=tool_resolver
2026-02-13 18:17:02 [info     ] registry.instance_registered   component=research_graph_runtime priority=0 registry=singleton_services
2026-02-13 18:17:02 [info     ] singleton_service_registry.registered category=general name=research_graph_runtime
2026-02-13 18:17:02 [info     ] Router registered: Research Factory API module_id=research_factory prefix= tags=['research']
2026-02-13 18:17:02 [info     ] registry.instance_registered   component=world_model_engine priority=0 registry=singleton_services
2026-02-13 18:17:02 [info     ] singleton_service_registry.registered category=general name=world_model_engine
2026-02-13 18:17:02 [info     ] registry.instance_registered   component=world_model_repository priority=0 registry=singleton_services
2026-02-13 18:17:02 [info     ] singleton_service_registry.registered category=general name=world_model_repository
2026-02-13 18:17:02 [info     ] registry.instance_registered   component=world_model_service priority=0 registry=singleton_services
2026-02-13 18:17:02 [info     ] singleton_service_registry.registered category=general name=world_model_service
2026-02-13 18:17:02 [error    ] Failed to import AgentExecutorService: cannot import name 'get_tool_registry' from 'runtime.tool_registry' (/app/runtime/tool_registry.py)
╭───────────────────── Traceback (most recent call last) ──────────────────────╮
│ /app/api/server.py:172 in <module>                                           │
│                                                                              │
│    169                                                                       │
│    170 # Optional: Agent Executor (v2.2+)                                    │
│    171 try:                                                                  │
│ ❱  172 │   from core.agents.executor import AgentExecutorService             │
│    173 │   from core.agents.schemas import (                                 │
│    174 │   │   AgentConfig,                                                  │
│    175 │   │   AgentTask,                                                    │
│                                                                              │
│ ╭───────────────────────────────── locals ─────────────────────────────────╮ │
│ │          _has_prometheus = True                                          │ │
│ │            _has_research = True                                          │ │
│ │               _has_slack = True                                          │ │
│ │         _has_world_model = True                                          │ │
│ │ _has_world_model_runtime = True                                          │ │
│ │             agent_routes = <module 'api.agent_routes' from               │ │
│ │                            '/app/api/agent_routes.py'>                   │ │
│ │                       db = <module 'api.db' from '/app/api/db.py'>       │ │
│ │                        e = ImportError("cannot import name               │ │
│ │                            'get_tool_registry' from                      │ │
│ │                            'runtime.tool_registry'                       │ │
│ │                            (/app/runtime/tool_registry.py)")             │ │
│ │                    httpx = <module 'httpx' from                          │ │
│ │                            '/usr/local/lib/python3.12/site-packages/htt… │ │
│ │                   logger = <BoundLoggerLazyProxy(logger=None,            │ │
│ │                            wrapper_class=None, processors=None,          │ │
│ │                            context_class=None, initial_values={},        │ │
│ │                            logger_factory_args=('api.server',))>         │ │
│ │                       os = <module 'os' (frozen)>                        │ │
│ │     PROMETHEUS_AVAILABLE = True                                          │ │
│ │          research_router = <fastapi.routing.APIRouter object at          │ │
│ │                            0x7d2ed843ca10>                               │ │
│ │          router_registry = RouterRegistry(total=2, wired=0)              │ │
│ │                 settings = IntegrationSettings(                          │ │
│ │                            │   slack_app_enabled=True,                   │ │
│ │                            │   mac_agent_enabled=True,                   │ │
│ │                            │   email_enabled=False,                      │ │
│ │                            │   email_agent_enabled=True,                 │ │
│ │                            │   inbox_parser_enabled=False,               │ │
│ │                            │   twilio_enabled=False,                     │ │
│ │                            │   waba_enabled=False,                       │ │
│ │                            │   l9_new_agent_init=True,                   │ │
│ │                            │   l9_stage3_modules=True,                   │ │
│ │                            │   l9_graph_agent_state=True,                │ │
│ │                            │   l9_observability=True,                    │ │
│ │                            │   l9_skip_startup_checks=False,             │ │
│ │                            │   l9_stage4_consolidation=True,             │ │
│ │                            │   l9_consolidation_interval_hours=4,        │ │
│ │                            │   l9_graph_wm_sync=True,                    │ │
│ │                            │   l9_tool_pattern_extraction=True,          │ │
│ │                            │   l9_gmp_learning_enabled=False,            │ │
│ │                            │   l9_memory_warming_enabled=True,           │ │
│ │                            │   l9_dynamic_tool_discovery=True,           │ │
│ │                            │   l9_tool_discovery_top_k=5,                │ │
│ │                            │   l9_tool_discovery_min_similarity=0.3,     │ │
│ │                            │   l9_tool_discovery_max_tokens=2000,        │ │
│ │                            │   l9_tool_cache_ttl=300,                    │ │
│ │                            │                                             │ │
│ │                            l9_executor_api_key='9c4753df3b7ee85e2370b0e… │ │
│ │                            │   l9_llm_model='gpt-4o',                    │ │
│ │                            │   l9_project_id='l9-default',               │ │
│ │                            │   l9_use_kernels=True,                      │ │
│ │                            │                                             │ │
│ │                            l9_api_url='http://mcp.quantumaipartners.com… │ │
│ │                            │   l9_memory_scope='user',                   │ │
│ │                            │   l9_repo_root='',                          │ │
│ │                            │   l9_env='development',                     │ │
│ │                            │   l9_tenant_id='l-cto',                     │ │
│ │                            │   l9_tool_feedback_enabled=True,            │ │
│ │                            │   l9_tool_exploration_rate=0.1,             │ │
│ │                            │   l9_tool_feedback_buffer_size=50,          │ │
│ │                            │   l9_tool_feedback_lookback_days=30,        │ │
│ │                            │   l9_tool_success_neutral_prior=0.5,        │ │
│ │                            │   l9_tool_alert_success_threshold=0.5,      │ │
│ │                            │   l9_tool_learning_daily_hour_utc=2,        │ │
│ │                            │   l9_tool_learning_daily_minute_utc=0,      │ │
│ │                            │   l9_secrets_provider='env',                │ │
│ │                            │   aws_region='us-east-1',                   │ │
│ │                            │   aws_secrets_prefix='l9',                  │ │
│ │                            │   aws_secrets_cache_ttl=3600,               │ │
│ │                            │   aws_secrets_fallback_to_env=True,         │ │
│ │                            │   local_dev=False,                          │ │
│ │                            │   l9_data_root='/home/l9user/.l9',          │ │
│ │                            │   slack_files_dir='',                       │ │
│ │                            │   slack_app_id='A0A3MLBJ55Y',               │ │
│ │                            │                                             │ │
│ │                            slack_bot_token='xoxb-5756690555681-10120570… │ │
│ │                            │                                             │ │
│ │                            slack_signing_secret='d88113146f7be4c9c63e08… │ │
│ │                            │                                             │ │
│ │                            slack_client_id='5756690555681.1012369161720… │ │
│ │                            │                                             │ │
│ │                            slack_client_secret='d14377ce8bf1c265f746618… │ │
│ │                            │                                             │ │
│ │                            slack_verification_token='nFrKJ0NVekjgzIpOtp… │ │
│ │                            │   igor_slack_user_id='U05NKNB70V6',         │ │
│ │                            │   l_cto_governance_bypass=False             │ │
│ │                            )                                             │ │
│ │                structlog = <module 'structlog' from                      │ │
│ │                            '/usr/local/lib/python3.12/site-packages/str… │ │
│ │                      UTC = datetime.timezone.utc                         │ │
│ ╰──────────────────────────────────────────────────────────────────────────╯ │
│                                                                              │
│ /app/core/agents/__init__.py:43 in <module>                                  │
│                                                                              │
│    40 from core.agents.agent_instance import AgentInstance                   │
│    41                                                                        │
│    42 # Dynamic Tool Binding (GMP-TS-META: Anthropic Tool Search pattern)    │
│ ❱  43 from core.agents.dynamic_tool_binding import (                         │
│    44 │   bind_tools_to_agent,                                               │
│    45 │   cache_discovered_tools,                                            │
│    46 │   clear_tool_cache,                                                  │
│                                                                              │
│ /app/core/agents/dynamic_tool_binding.py:47 in <module>                      │
│                                                                              │
│    44 │   discover_tools_for_task,                                           │
│    45 │   is_dynamic_discovery_enabled,                                      │
│    46 )                                                                      │
│ ❱  47 from runtime.tool_registry import get_tool_registry                    │
│    48                                                                        │
│    49 logger = structlog.get_logger(__name__)                                │
│    50                                                                        │
│                                                                              │
│ ╭───────────────────────────────── locals ─────────────────────────────────╮ │
│ │ annotations = _Feature((3, 7, 0, 'beta', 1), None, 16777216)             │ │
│ │    settings = IntegrationSettings(                                       │ │
│ │               │   slack_app_enabled=True,                                │ │
│ │               │   mac_agent_enabled=True,                                │ │
│ │               │   email_enabled=False,                                   │ │
│ │               │   email_agent_enabled=True,                              │ │
│ │               │   inbox_parser_enabled=False,                            │ │
│ │               │   twilio_enabled=False,                                  │ │
│ │               │   waba_enabled=False,                                    │ │
│ │               │   l9_new_agent_init=True,                                │ │
│ │               │   l9_stage3_modules=True,                                │ │
│ │               │   l9_graph_agent_state=True,                             │ │
│ │               │   l9_observability=True,                                 │ │
│ │               │   l9_skip_startup_checks=False,                          │ │
│ │               │   l9_stage4_consolidation=True,                          │ │
│ │               │   l9_consolidation_interval_hours=4,                     │ │
│ │               │   l9_graph_wm_sync=True,                                 │ │
│ │               │   l9_tool_pattern_extraction=True,                       │ │
│ │               │   l9_gmp_learning_enabled=False,                         │ │
│ │               │   l9_memory_warming_enabled=True,                        │ │
│ │               │   l9_dynamic_tool_discovery=True,                        │ │
│ │               │   l9_tool_discovery_top_k=5,                             │ │
│ │               │   l9_tool_discovery_min_similarity=0.3,                  │ │
│ │               │   l9_tool_discovery_max_tokens=2000,                     │ │
│ │               │   l9_tool_cache_ttl=300,                                 │ │
│ │               │                                                          │ │
│ │               l9_executor_api_key='9c4753df3b7ee85e2370b0e9a55355e59a9c… │ │
│ │               │   l9_llm_model='gpt-4o',                                 │ │
│ │               │   l9_project_id='l9-default',                            │ │
│ │               │   l9_use_kernels=True,                                   │ │
│ │               │   l9_api_url='http://mcp.quantumaipartners.com:30080',   │ │
│ │               │   l9_memory_scope='user',                                │ │
│ │               │   l9_repo_root='',                                       │ │
│ │               │   l9_env='development',                                  │ │
│ │               │   l9_tenant_id='l-cto',                                  │ │
│ │               │   l9_tool_feedback_enabled=True,                         │ │
│ │               │   l9_tool_exploration_rate=0.1,                          │ │
│ │               │   l9_tool_feedback_buffer_size=50,                       │ │
│ │               │   l9_tool_feedback_lookback_days=30,                     │ │
│ │               │   l9_tool_success_neutral_prior=0.5,                     │ │
│ │               │   l9_tool_alert_success_threshold=0.5,                   │ │
│ │               │   l9_tool_learning_daily_hour_utc=2,                     │ │
│ │               │   l9_tool_learning_daily_minute_utc=0,                   │ │
│ │               │   l9_secrets_provider='env',                             │ │
│ │               │   aws_region='us-east-1',                                │ │
│ │               │   aws_secrets_prefix='l9',                               │ │
│ │               │   aws_secrets_cache_ttl=3600,                            │ │
│ │               │   aws_secrets_fallback_to_env=True,                      │ │
│ │               │   local_dev=False,                                       │ │
│ │               │   l9_data_root='/home/l9user/.l9',                       │ │
│ │               │   slack_files_dir='',                                    │ │
│ │               │   slack_app_id='A0A3MLBJ55Y',                            │ │
│ │               │                                                          │ │
│ │               slack_bot_token='xoxb-5756690555681-10120570028437-0GsjsV… │ │
│ │               │                                                          │ │
│ │               slack_signing_secret='d88113146f7be4c9c63e08fbb6579f9e',   │ │
│ │               │   slack_client_id='5756690555681.10123691617202',        │ │
│ │               │                                                          │ │
│ │               slack_client_secret='d14377ce8bf1c265f7466188791c2034',    │ │
│ │               │   slack_verification_token='nFrKJ0NVekjgzIpOtpyYqUCK',   │ │
│ │               │   igor_slack_user_id='U05NKNB70V6',                      │ │
│ │               │   l_cto_governance_bypass=False                          │ │
│ │               )                                                          │ │
│ │   structlog = <module 'structlog' from                                   │ │
│ │               '/usr/local/lib/python3.12/site-packages/structlog/__init… │ │
│ ╰──────────────────────────────────────────────────────────────────────────╯ │
╰──────────────────────────────────────────────────────────────────────────────╯
ImportError: cannot import name 'get_tool_registry' from 'runtime.tool_registry'
(/app/runtime/tool_registry.py)

/app/orchestrators/pattern/interface.py:88: UserWarning: Field name "schema" in "OutputContract" shadows an attribute in parent "BaseModel"
  class OutputContract(BaseModel):
2026-02-13 18:17:03 [info     ] registry.instance_registered   component=cursor_memory_kernel priority=0 registry=singleton_services
2026-02-13 18:17:03 [info     ] singleton_service_registry.registered category=general name=cursor_memory_kernel
2026-02-13 18:17:03 [debug    ] Kernel Registry not available: cannot import name 'get_tool_registry' from 'runtime.tool_registry' (/app/runtime/tool_registry.py)
2026-02-13 18:17:04 [info     ] Router wired: Agent Task Management module_id=agent_routes prefix=/agent
2026-02-13 18:17:04 [info     ] Router wired: Research Factory API module_id=research_factory prefix=
2026-02-13 18:17:04 [info     ] ✅ All routers wired successfully: 2 routers
2026-02-13 18:17:04 [info     ] Auto-wired 2 routers via router_registry
2026-02-13 18:17:04 [info     ] Prometheus metrics endpoint registered at /metrics
OK  api.server

===== 6) Check symbol alignment (hotfix validation) =====
2026-02-13 18:17:09 [info     ] registry.initialized           allow_duplicates=False registry_name=singleton_services
2026-02-13 18:17:09 [info     ] registry.instance_registered   component=neo4j_client priority=0 registry=singleton_services
2026-02-13 18:17:09 [info     ] singleton_service_registry.registered category=general name=neo4j_client
2026-02-13 18:17:09 [debug    ] singleton_service_registry.closer_registered singleton=neo4j_client
2026-02-13 18:17:10 [info     ] registry.instance_registered   component=memory_substrate_repository priority=0 registry=singleton_services
2026-02-13 18:17:10 [info     ] singleton_service_registry.registered category=general name=memory_substrate_repository
2026-02-13 18:17:10 [debug    ] singleton_service_registry.closer_registered singleton=memory_substrate_repository
2026-02-13 18:17:10 [info     ] registry.instance_registered   component=housekeeping_engine priority=0 registry=singleton_services
2026-02-13 18:17:10 [info     ] singleton_service_registry.registered category=general name=housekeeping_engine
2026-02-13 18:17:10 [debug    ] tool_risk_policy.loaded        high_risk_count=13 igor_required_count=8 path=/app/config/policies/high_risk_tools.yaml safe_count=9
2026-02-13 18:17:11 [info     ] registry.instance_registered   component=memory_substrate_service priority=0 registry=singleton_services
2026-02-13 18:17:11 [info     ] singleton_service_registry.registered category=general name=memory_substrate_service
2026-02-13 18:17:11 [debug    ] singleton_service_registry.closer_registered singleton=memory_substrate_service
2026-02-13 18:17:11 [info     ] registry.instance_registered   component=ingestion_pipeline priority=0 registry=singleton_services
2026-02-13 18:17:11 [info     ] singleton_service_registry.registered category=general name=ingestion_pipeline
2026-02-13 18:17:11 [info     ] registry.instance_registered   component=insight_extraction_pipeline priority=0 registry=singleton_services
2026-02-13 18:17:11 [info     ] singleton_service_registry.registered category=general name=insight_extraction_pipeline
2026-02-13 18:17:21 [info     ] CrossEncoder available from sentence-transformers
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=retrieval_pipeline priority=0 registry=singleton_services
2026-02-13 18:17:21 [info     ] singleton_service_registry.registered category=general name=retrieval_pipeline
2026-02-13 18:17:21 [info     ] registry.initialized           allow_duplicates=False registry_name=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=redis_get priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=redis_set priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=redis_keys priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=redis_delete priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=redis_enqueue_task priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=redis_dequeue_task priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=redis_queue_size priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=redis_get_task_context priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=redis_set_task_context priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=redis_get_rate_limit priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=redis_set_rate_limit priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=redis_increment_rate_limit priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=redis_decrement_rate_limit priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] kernel_config_loader.load_kernel_config action=loading_config environment=production
2026-02-13 18:17:21 [debug    ] kernel_config_loader.load_kernel_config action=applied_env_overrides environment=production
2026-02-13 18:17:21 [info     ] kernel_config_loader.load_kernel_config action=config_loaded environment=production kernel_count=10
2026-02-13 18:17:21 [info     ] kernel_loader.config_loaded    action=loaded_externalized_config kernel_count=10 source=config/kernel_discovery.yaml
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=redis_client priority=0 registry=singleton_services
2026-02-13 18:17:21 [info     ] singleton_service_registry.registered category=general name=redis_client
2026-02-13 18:17:21 [debug    ] singleton_service_registry.closer_registered singleton=redis_client
2026-02-13 18:17:21 [info     ] WebSocketOrchestrator initialized
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=tool_registry priority=0 registry=singleton_services
2026-02-13 18:17:21 [info     ] singleton_service_registry.registered category=general name=tool_registry
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=tool_router_find priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=saga_fetch_and_enrich priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=saga_enrich_entities priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=saga_timeline_correlation priority=10 registry=tool_executors
2026-02-13 18:17:21 [info     ] registry.instance_registered   component=saga_execute_custom priority=10 registry=tool_executors
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/app/core/tools/__init__.py", line 72, in <module>
    from core.tools.registry_adapter import (
  File "/app/core/tools/registry_adapter.py", line 124, in <module>
    from core.agents.schemas import ToolBinding, ToolCallResult
  File "/app/core/agents/__init__.py", line 43, in <module>
    from core.agents.dynamic_tool_binding import (
  File "/app/core/agents/dynamic_tool_binding.py", line 47, in <module>
    from runtime.tool_registry import get_tool_registry
ImportError: cannot import name 'get_tool_registry' from 'runtime.tool_registry' (/app/runtime/tool_registry.py)

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
ImageDigest=sha256:2ddffc1db69b2a5e16f2d082911c0442c6ba10277a8f988752e2cc8f614dd18a
Python 3.12.12
Linux e308755302ce 6.8.0-90-generic #91-Ubuntu SMP PREEMPT_DYNAMIC Tue Nov 18 14:14:30 UTC 2025 x86_64 GNU/Linux

===== 10) One-line diagnosis hint =====
LIKELY ROOT CAUSE: executor init failed, then startup guard aborts due to Slack routing requirement.

Done. Primary log file: /tmp/l9-api-last400.log
