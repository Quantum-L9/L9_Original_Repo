# L9 Runtime

The `runtime/` package provides execution-time infrastructure for L9. It contains the kernel loader and execution gate, Redis-backed services with controlled fallbacks, task and background-task coordination, rate limiting, tool-package discovery, and WebSocket coordination.

Runtime decision evidence is produced by active L9 systems rather than by mutating source code. Governance decisions emit structured substrate packets, while operational telemetry is emitted through the observability service and its configured exporters.

| Area | Primary modules | Responsibility |
|---|---|---|
| Kernel lifecycle | `kernel_loader.py`, `kernel_state.py` | Load, validate, and activate the configured kernel stack. |
| Execution authorization | `execution_gate.py` | Apply authorization and escalation controls to tool execution. |
| Task execution | `task_queue.py`, `background_tasks.py` | Queue and coordinate asynchronous work. |
| Shared services | `redis_client.py`, `redis_tools.py`, `rate_limiter.py` | Provide resilient shared infrastructure. |
| Connectivity | `websocket_orchestrator.py`, `tool_packages.py` | Coordinate connected agents and discover tool packages. |

Runtime changes must preserve explicit failure behavior, structured logging, PacketEnvelope-based audit evidence where applicable, and the repository’s active governance controls.
