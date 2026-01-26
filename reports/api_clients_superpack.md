# API & CLIENTS SUPERPACK

**Risk Tier:** T2 (Reversible) | **Auto-Generated**

---

## Purpose

Map HTTP/RPC routes, client libraries, adapter protocols, and agent entry points.

---

## API Routes (AST Scanned)

| Method | Path | Handler | Module |
|--------|------|---------|--------|
| GET | `/health` | `os_health()` | `api.os_routes` |
| GET | `/status` | `os_status()` | `api.os_routes` |
| GET | `/` | `root()` | `api.server` |
| GET | `/health` | `health()` | `api.server` |
| GET | `/health/startup` | `startup_health()` | `api.server` |
| POST | `/kernels/reload` | `reload_kernels_endpoint()` | `api.server` |
| GET | `/health/neo4j` | `neo4j_health()` | `api.server` |
| GET | `/health/services` | `services_health()` | `api.server` |
| GET | `/health/checkpoint` | `checkpoint_health()` | `api.server` |
| POST | `/lchat` | `lchat()` | `api.server` |
| WEBSOCKET | `/ws/agent` | `agent_ws_endpoint()` | `api.server` |
| WEBSOCKET | `/lws` | `l_ws()` | `api.server` |
| POST | `/twilio/webhook` | `twilio_webhook()` | `api.webhook_twilio` |
| GET | `/tasks/next` | `get_next_mac_task()` | `api.webhook_mac_agent` |
| POST | `/tasks/{task_id}/result` | `submit_task_result()` | `api.webhook_mac_agent` |
| GET | `/tasks` | `list_mac_tasks()` | `api.webhook_mac_agent` |
| GET | `/health` | `world_model_health()` | `api.world_model_api` |
| GET | `/entities/{entity_id}` | `get_entity()` | `api.world_model_api` |
| GET | `/entities` | `list_entities()` | `api.world_model_api` |
| GET | `/state-version` | `get_state_version()` | `api.world_model_api` |
| POST | `/snapshot` | `create_snapshot()` | `api.world_model_api` |
| POST | `/restore` | `restore_from_snapshot()` | `api.world_model_api` |
| GET | `/snapshots` | `list_snapshots()` | `api.world_model_api` |
| POST | `/insights` | `submit_insights()` | `api.world_model_api` |
| GET | `/updates` | `list_updates()` | `api.world_model_api` |
| GET | `/` | `root()` | `api.server_memory` |
| GET | `/health` | `health()` | `api.server_memory` |
| POST | `/chat` | `chat()` | `api.server_memory` |
| GET | `/waba/webhook` | `verify_waba_webhook()` | `api.webhook_waba` |
| POST | `/waba/webhook` | `waba_webhook()` | `api.webhook_waba` |
| GET | `/health` | `agent_health()` | `api.agent_routes` |
| GET | `/status` | `agent_status()` | `api.agent_routes` |
| POST | `/task` | `submit_task()` | `api.agent_routes` |
| POST | `/execute` | `execute_task()` | `api.agent_routes` |
| POST | `/segment` | `segment_preview()` | `api.agent_routes` |
| GET | `/agent/health` | `agent_health()` | `api.vps_executor` |
| POST | `/agent/exec` | `agent_exec()` | `api.vps_executor` |
| POST | `/test` | `tools_test()` | `api.tools.router` |
| POST | `/execute` | `execute_tool()` | `api.tools.router` |
| GET | `/health` | `tool_graph_health()` | `api.tools.router` |
| GET | `/health` | `graph_health()` | `api.memory.graph` |
| POST | `/entity` | `create_entity()` | `api.memory.graph` |
| GET | `/entity/{entity_type}/{entity_id}` | `get_entity()` | `api.memory.graph` |
| DELETE | `/entity/{entity_type}/{entity_id}` | `delete_entity()` | `api.memory.graph` |
| POST | `/relationship` | `create_relationship()` | `api.memory.graph` |
| GET | `/relationships/{entity_type}/{entity_id}` | `get_relationships()` | `api.memory.graph` |
| POST | `/query` | `run_query()` | `api.memory.graph` |
| GET | `/context/{domain}` | `get_domain_context()` | `api.memory.graph` |
| GET | `/session-graph/{session_id}` | `get_session_graph()` | `api.memory.graph` |
| GET | `/health` | `cache_health()` | `api.memory.cache` |
| GET | `/get/{key}` | `cache_get()` | `api.memory.cache` |
| POST | `/set` | `cache_set()` | `api.memory.cache` |
| DELETE | `/delete/{key}` | `cache_delete()` | `api.memory.cache` |
| GET | `/keys/{pattern}` | `cache_keys()` | `api.memory.cache` |
| POST | `/session/context` | `set_session_context()` | `api.memory.cache` |
| GET | `/session/context/{session_id}` | `get_session_context()` | `api.memory.cache` |
| GET | `/session/list` | `list_sessions()` | `api.memory.cache` |
| GET | `/rate-limit/{key}` | `get_rate_limit()` | `api.memory.cache` |
| POST | `/rate-limit/{key}/increment` | `increment_rate_limit()` | `api.memory.cache` |
| POST | `/task/context/{task_id}` | `set_task_context()` | `api.memory.cache` |
| GET | `/task/context/{task_id}` | `get_task_context()` | `api.memory.cache` |
| POST | `/test` | `memory_test()` | `api.memory.router` |
| POST | `/packet` | `create_packet()` | `api.memory.router` |
| POST | `/semantic/search` | `semantic_search()` | `api.memory.router` |
| GET | `/stats` | `get_stats()` | `api.memory.router` |
| GET | `/packet/{packet_id}` | `get_packet()` | `api.memory.router` |
| GET | `/thread/{thread_id}` | `get_thread()` | `api.memory.router` |
| GET | `/lineage/{packet_id}` | `get_lineage()` | `api.memory.router` |
| POST | `/hybrid/search` | `hybrid_search()` | `api.memory.router` |
| GET | `/facts` | `get_facts()` | `api.memory.router` |
| GET | `/insights` | `get_insights()` | `api.memory.router` |
| POST | `/gc/run` | `run_gc()` | `api.memory.router` |
| GET | `/gc/stats` | `get_gc_stats()` | `api.memory.router` |
| GET | `/health` | `health_check()` | `api.memory.router` |
| POST | `/batch` | `batch_write()` | `api.memory.router` |
| POST | `/compact` | `compact_storage()` | `api.memory.router` |
| POST | `/reasoning/replay` | `reasoning_replay()` | `api.memory.router` |
| POST | `/consolidation/run` | `run_consolidation()` | `api.memory.router` |
| POST | `/saga/fetch-and-enrich` | `saga_fetch_and_enrich()` | `api.memory.router` |
| POST | `/saga/enrich-entities` | `saga_enrich_entities()` | `api.memory.router` |
| POST | `/saga/correlate-timeline` | `saga_correlate_timeline()` | `api.memory.router` |
| POST | `/warm` | `warm_memory_for_query()` | `api.memory.router` |
| GET | `/warm/metrics` | `get_warming_metrics()` | `api.memory.router` |
| POST | `/run` | `run_simulation()` | `api.routes.simulation` |
| GET | `/{run_id}` | `get_simulation_run()` | `api.routes.simulation` |
| GET | `/graph/{graph_id}` | `get_runs_for_graph()` | `api.routes.simulation` |
| GET | `/health` | `simulation_health()` | `api.routes.simulation` |
| GET | `/test` | `research_test()` | `api.routes.research` |
| GET | `/status` | `research_status()` | `api.routes.research` |
| POST | `/execute` | `execute_research()` | `api.routes.research` |
| GET | `/report/daily` | `get_daily_compliance_report()` | `api.routes.compliance` |
| GET | `/report` | `get_compliance_report()` | `api.routes.compliance` |
| GET | `/audit-log` | `export_audit_log()` | `api.routes.compliance` |
| GET | `/status` | `reflection_agent_status()` | `api.routes.reflection_agent` |
| POST | `/reflect` | `reflect()` | `api.routes.reflection_agent` |
| POST | `/analyze-failure` | `analyze_failure()` | `api.routes.reflection_agent` |
| POST | `/compare` | `compare_approaches()` | `api.routes.reflection_agent` |
| POST | `/extract-patterns` | `extract_patterns()` | `api.routes.reflection_agent` |
| POST | `/generate-improvements` | `generate_improvements()` | `api.routes.reflection_agent` |
| GET | `/lessons-learned` | `get_lessons_learned()` | `api.routes.reflection_agent` |
| DELETE | `/lessons-learned` | `clear_lessons_learned()` | `api.routes.reflection_agent` |
| GET | `/autonomy-level` | `get_autonomy_level()` | `api.routes.gmp_learning` |
| GET | `/graduation-status` | `get_graduation_status()` | `api.routes.gmp_learning` |
| POST | `/graduate` | `graduate_to_next_level()` | `api.routes.gmp_learning` |
| GET | `/heuristics` | `get_heuristics()` | `api.routes.gmp_learning` |
| GET | `/analytics` | `get_analytics()` | `api.routes.gmp_learning` |
| POST | `/log-execution` | `log_execution()` | `api.routes.gmp_learning` |
| POST | `/generate-heuristics` | `trigger_heuristic_generation()` | `api.routes.gmp_learning` |
| GET | `/test` | `pattern_test()` | `api.routes.pattern` |
| GET | `/config` | `get_pattern_config()` | `api.routes.pattern` |
| POST | `/execute` | `execute_pattern()` | `api.routes.pattern` |
| POST | `/validate` | `validate_pattern_config()` | `api.routes.pattern` |
| POST | `/execute-all` | `execute_all_subsystems()` | `api.routes.pattern` |
| GET | `/metrics` | `get_metrics()` | `api.routes.observability` |
| GET | `/failures` | `get_failures()` | `api.routes.observability` |
| GET | `/spans` | `get_spans()` | `api.routes.observability` |
| GET | `/health` | `get_health()` | `api.routes.observability` |
| GET | `/circuit-breakers` | `get_circuit_breakers()` | `api.routes.observability` |
| GET | `/agent/{agent_id}/capabilities` | `get_agent_capabilities()` | `api.routes.worldmodel` |
| GET | `/infrastructure/status` | `get_infrastructure_status()` | `api.routes.worldmodel` |
| GET | `/approvals/summary` | `get_approvals_summary()` | `api.routes.worldmodel` |
| GET | `/integrations` | `get_integrations()` | `api.routes.worldmodel` |
| GET | `/context/{agent_id}` | `get_world_model_context()` | `api.routes.worldmodel` |
| GET | `/health` | `factory_health()` | `api.routes.factory` |
| POST | `/validate` | `validate_schema()` | `api.routes.factory` |
| POST | `/extract` | `extract_agent()` | `api.routes.factory` |
| POST | `/extract-file` | `extract_agent_file()` | `api.routes.factory` |
| GET | `/templates` | `list_templates()` | `api.routes.factory` |
| GET | `/templates/{template_name}` | `get_template()` | `api.routes.factory` |
| GET | `/mcp/tools` | `list_tools()` | `api.routes.mcp` |
| POST | `/mcp/call` | `call_tool()` | `api.routes.mcp` |
| GET | `/mcp/health` | `mcp_health_check()` | `api.routes.mcp` |
| GET | `/status` | `research_agent_status()` | `api.routes.research_agent` |
| POST | `/synthesize` | `synthesize()` | `api.routes.research_agent` |
| POST | `/discover` | `discover()` | `api.routes.research_agent` |
| POST | `/generate-spec` | `generate_spec()` | `api.routes.research_agent` |
| POST | `/research-to-code` | `research_to_code()` | `api.routes.research_agent` |
| GET | `/test` | `reasoning_test()` | `api.routes.reasoning` |
| GET | `/modes` | `get_reasoning_modes()` | `api.routes.reasoning` |
| POST | `/execute` | `execute_reasoning()` | `api.routes.reasoning` |
| GET | `/status` | `get_modules_status()` | `api.routes.modules` |
| POST | `/violations/scan` | `scan_for_violations()` | `api.routes.workers` |
| GET | `/violations/counts` | `get_violation_counts()` | `api.routes.workers` |
| POST | `/violations/reset/{lesson_id}` | `reset_violation_count()` | `api.routes.workers` |
| POST | `/anomaly/process` | `process_anomalies()` | `api.routes.workers` |
| GET | `/health` | `get_workers_health()` | `api.routes.workers` |
| GET | `/packet-envelope/status` | `get_upgrade_status()` | `api.routes.upgrades` |
| GET | `/packet-envelope/features` | `get_enabled_features()` | `api.routes.upgrades` |
| GET | `/packet-envelope/validate` | `validate_upgrade_deployment()` | `api.routes.upgrades` |
| POST | `/packet-envelope/activate/phase-2` | `activate_phase_2()` | `api.routes.upgrades` |
| POST | `/packet-envelope/activate/phase-3` | `activate_phase_3()` | `api.routes.upgrades` |
| POST | `/packet-envelope/activate/phase-4` | `activate_phase_4()` | `api.routes.upgrades` |
| POST | `/packet-envelope/activate/phase-5` | `activate_phase_5()` | `api.routes.upgrades` |
| POST | `/packet-envelope/activate/all` | `activate_all_phases()` | `api.routes.upgrades` |
| GET | `/health` | `upgrade_health()` | `api.routes.upgrades` |
| POST | `/execute` | `execute_command()` | `api.routes.commands` |
| POST | `/parse` | `parse_command_endpoint()` | `api.routes.commands` |
| POST | `/intent` | `extract_intent_endpoint()` | `api.routes.commands` |
| GET | `/help` | `get_help()` | `api.routes.commands` |
| POST | `/governance/feedback` | `record_approval_feedback()` | `api.routes.commands` |
| POST | `/events` | `slack_events()` | `api.routes.slack` |
| POST | `/commands` | `slack_commands()` | `api.routes.slack` |
| GET | `/test` | `cursor_test()` | `api.routes.cursor` |
| POST | `/task` | `cursor_task()` | `api.routes.cursor` |
| POST | `/resume` | `cursor_resume()` | `api.routes.cursor` |

**Total Routes:** 165

## API Modules (AST Scanned)

| Module | Classes | Functions | LOC |
|--------|---------|-----------|-----|
| `adapters.__init__` | 0 | 0 | 0 |
| `adapters.tensorglobe_bridge.__init__` | 0 | 0 | 0 |
| `adapters.tensorglobe_bridge.adapter` | 1 | 0 | 229 |
| `adapters.tensorglobe_bridge.anomaly_guard` | 4 | 0 | 272 |
| `adapters.tensorglobe_bridge.schemas` | 7 | 0 | 152 |
| `adapters.tensorglobe_bridge.security` | 1 | 0 | 137 |
| `api.__init__` | 0 | 0 | 4 |
| `api.agent_routes` | 5 | 7 | 525 |
| `api.auth` | 1 | 3 | 211 |
| `api.db` | 0 | 2 | 95 |
| `api.dependencies` | 0 | 16 | 386 |
| `api.e2e_slack_audit` | 1 | 9 | 834 |
| `api.llm` | 0 | 3 | 215 |
| `api.memory.__init__` | 0 | 0 | 1 |
| `api.memory.cache` | 3 | 13 | 471 |
| `api.memory.graph` | 4 | 10 | 462 |
| `api.memory.router` | 15 | 25 | 1137 |
| `api.middleware.__init__` | 0 | 0 | 0 |
| `api.middleware.websocket_tracing` | 2 | 2 | 318 |
| `api.openapi_config` | 0 | 2 | 356 |
| `api.os_routes` | 0 | 2 | 97 |
| `api.routes.__init__` | 0 | 0 | 1 |
| `api.routes.commands` | 5 | 5 | 573 |
| `api.routes.compliance` | 2 | 3 | 339 |
| `api.routes.cursor` | 3 | 4 | 281 |
| `api.routes.factory` | 8 | 9 | 540 |
| `api.routes.gmp_learning` | 4 | 8 | 337 |
| `api.routes.mcp` | 0 | 4 | 285 |
| `api.routes.modules` | 0 | 2 | 178 |
| `api.routes.observability` | 8 | 5 | 412 |
| `api.routes.pattern` | 6 | 6 | 513 |
| `api.routes.reasoning` | 2 | 4 | 263 |
| `api.routes.reflection_agent` | 11 | 9 | 628 |
| `api.routes.registry` | 2 | 2 | 366 |
| `api.routes.research` | 2 | 4 | 240 |
| `api.routes.research_agent` | 8 | 6 | 490 |
| `api.routes.simulation` | 3 | 5 | 320 |
| `api.routes.slack` | 0 | 3 | 496 |
| `api.routes.upgrades` | 0 | 10 | 290 |
| `api.routes.workers` | 6 | 8 | 376 |
| `api.routes.worldmodel` | 0 | 6 | 210 |
| `api.server` | 6 | 15 | 3643 |
| `api.server_memory` | 2 | 3 | 312 |
| `api.slack_adapter` | 3 | 0 | 382 |
| `api.slack_client` | 2 | 1 | 662 |
| `api.tools.__init__` | 0 | 0 | 10 |
| `api.tools.router` | 2 | 4 | 261 |
| `api.vps_executor` | 3 | 7 | 295 |
| `api.webhook_mac_agent` | 1 | 3 | 265 |
| `api.webhook_twilio` | 0 | 2 | 163 |
| `api.webhook_waba` | 0 | 5 | 300 |
| `api.whatsapp` | 0 | 2 | 96 |
| `api.world_model_api` | 12 | 10 | 515 |
| `clients.__init__` | 0 | 0 | 8 |
| `clients.memory_client` | 6 | 2 | 701 |
| `clients.world_model_client` | 7 | 2 | 538 |

## Adapter Classes

- `api.slack_client.SlackClientError` (Exception)
- `api.slack_client.SlackAPIClient` (object)
- `clients.memory_client.MemoryClient` (object)
- `clients.world_model_client.WorldModelClient` (object)
- `adapters.tensorglobe_bridge.adapter.TensorGlobeBridgeAdapter` (object)

## Change Checklist

Before modifying API modules:

1. [ ] Update API documentation if routes change
2. [ ] Verify auth requirements
3. [ ] Update client SDK if breaking changes
4. [ ] Add integration tests for new routes

---

*Auto-generated by `tools/superpack_reports/` | Regenerate: `make superpacks`*
