# L9 Component Wiring Audit — Consolidated (Levels B + C)

**Generated:** 2026-02-14 05:36 UTC

## Level B Summary: File Wiring

| Package | Files | Wired | Partial | Orphan | Entry | Test-Only |
|---------|------:|------:|--------:|-------:|------:|----------:|
| `SDK` | 1 | 0 | 1 | 0 | 0 | 0 |
| `agents` | 6 | 4 | 2 | 0 | 0 | 0 |
| `api` | 19 | 0 | 7 | 9 | 1 | 2 |
| `bootstrap` | 1 | 0 | 0 | 0 | 1 | 0 |
| `ci` | 20 | 0 | 1 | 0 | 19 | 0 |
| `clients` | 2 | 1 | 1 | 0 | 0 | 0 |
| `collaborative_cells` | 6 | 5 | 1 | 0 | 0 | 0 |
| `config` | 10 | 3 | 5 | 0 | 0 | 2 |
| `core` | 10 | 0 | 9 | 1 | 0 | 0 |
| `domain_tensor_bridge` | 22 | 0 | 8 | 14 | 0 | 0 |
| `email_agent` | 8 | 1 | 5 | 1 | 1 | 0 |
| `governance` | 1 | 0 | 1 | 0 | 0 | 0 |
| `graph_adapter` | 1 | 0 | 1 | 0 | 0 | 0 |
| `ir_engine` | 12 | 11 | 1 | 0 | 0 | 0 |
| `mac_agent` | 4 | 0 | 1 | 1 | 2 | 0 |
| `memory` | 72 | 19 | 32 | 9 | 1 | 11 |
| `memory_cache` | 3 | 1 | 2 | 0 | 0 | 0 |
| `motifs` | 3 | 0 | 0 | 3 | 0 | 0 |
| `orchestration` | 11 | 1 | 9 | 1 | 0 | 0 |
| `orchestrators` | 2 | 0 | 2 | 0 | 0 | 0 |
| `runtime` | 33 | 9 | 12 | 9 | 0 | 3 |
| `scripts` | 26 | 0 | 1 | 1 | 24 | 0 |
| `services` | 7 | 0 | 2 | 4 | 0 | 1 |
| `simulation` | 3 | 1 | 2 | 0 | 0 | 0 |
| `telemetry` | 3 | 0 | 2 | 0 | 1 | 0 |
| `tests` | 21 | 0 | 1 | 10 | 10 | 0 |
| `tools` | 3 | 0 | 0 | 1 | 2 | 0 |
| `workers` | 5 | 0 | 5 | 0 | 0 | 0 |
| `workflows` | 10 | 0 | 3 | 0 | 7 | 0 |
| `world_model` | 16 | 4 | 11 | 0 | 1 | 0 |

## Level C Summary: API Instantiation

| Package | API Status | Checked | Used | Test-Only | Unused | Missing Patterns |
|---------|-----------|--------:|-----:|----------:|-------:|-----------------:|
| `SDK` | HAS_API | 21 | 3 | 2 | 16 | 0 |
| `agents` | HAS_API | 16 | 9 | 4 | 3 | 7 |
| `api` | SHOULD_HAVE_API | 135 | 45 | 11 | 79 | 0 |
| `bootstrap` | NO_API_NEEDED | 0 | 0 | 0 | 0 | 0 |
| `ci` | NO_API_NEEDED | 0 | 0 | 0 | 0 | 0 |
| `clients` | HAS_API | 3 | 3 | 0 | 0 | 1 |
| `collaborative_cells` | HAS_API | 8 | 7 | 1 | 0 | 3 |
| `config` | HAS_API | 13 | 6 | 2 | 5 | 23 |
| `core` | SHOULD_HAVE_API | 46 | 22 | 7 | 17 | 0 |
| `domain_tensor_bridge` | HAS_API | 10 | 10 | 0 | 0 | 0 |
| `email_agent` | HAS_API | 9 | 2 | 2 | 5 | 3 |
| `governance` | HAS_API | 3 | 0 | 3 | 0 | 0 |
| `graph_adapter` | HAS_API | 1 | 0 | 0 | 1 | 0 |
| `ir_engine` | HAS_API | 52 | 19 | 17 | 16 | 5 |
| `mac_agent` | HAS_API | 5 | 3 | 0 | 2 | 6 |
| `memory` | HAS_API | 152 | 47 | 74 | 31 | 36 |
| `memory_cache` | HAS_API | 9 | 2 | 4 | 3 | 0 |
| `motifs` | HAS_API | 8 | 0 | 0 | 8 | 0 |
| `orchestration` | HAS_API | 43 | 7 | 9 | 27 | 3 |
| `orchestrators` | HAS_API | 12 | 7 | 1 | 4 | 4 |
| `runtime` | HAS_API | 52 | 37 | 9 | 6 | 23 |
| `scripts` | NO_API_NEEDED | 0 | 0 | 0 | 0 | 0 |
| `services` | SHOULD_HAVE_API | 26 | 11 | 2 | 13 | 0 |
| `simulation` | HAS_API | 10 | 6 | 0 | 4 | 0 |
| `telemetry` | NO_API_NEEDED | 0 | 0 | 0 | 0 | 0 |
| `tests` | NO_API_NEEDED | 0 | 0 | 0 | 0 | 0 |
| `tools` | NO_API_NEEDED | 0 | 0 | 0 | 0 | 0 |
| `workers` | HAS_API | 15 | 7 | 2 | 6 | 5 |
| `workflows` | HAS_API | 17 | 5 | 0 | 12 | 1 |
| `world_model` | HAS_API | 70 | 15 | 1 | 54 | 3 |

## Packages Needing Attention

### `SDK`

**Unused API symbols (16):** `CheckpointsInterface`, `ComplianceInterface`, `GovernanceInterface`, `L9Facade`, `LearningInterface`, `MCPInterface`, `ObservabilityInterface`, `ReasoningInterface`, `TaskQueueInterface`, `WorldModelInterface`, `close_l9`, `close_l9_facade`, `close_l9_sdk`, `get_l9`, `get_l9_facade`
  ... and 1 more

### `agents`

**Unused API symbols (3):** `CoderAgentB`, `create_l_cto_research_agent`, `is_research_mode`
**API-pattern symbols not in `__all__` (7):** `SynthesisEngine`, `create_reflection_agent`, `create_research_agent`, `get_agent_snapshot`, `get_agents_by_category`, `get_agents_by_role`, `get_all_agents`

### `api`

**Orphan files (9):** `api/agent_routes.py`, `api/db.py`, `api/openapi_config.py`, `api/os_routes.py`, `api/webhook_mac_agent.py`, `api/webhook_twilio.py`, `api/webhook_waba.py`, `api/whatsapp.py`, `api/world_model_api.py`
**Unused API symbols (79):** `ExecuteTaskRequest`, `ExecuteTaskResponse`, `agent_health`, `SegmentPreviewRequest`, `SegmentPreviewResponse`, `segment_preview`, `verify_api_key_with_rate_limit`, `insert_embedding`, `get_agent_executor`, `get_governance_engine`, `get_memory_orchestrator`, `get_timeline_service`, `get_memory_state_manager`, `get_consolidation_service`, `get_aios_runtime`
  ... and 64 more
**Recommended `__all__` entries (45):** `AuditResult`, `CallerIdentity`, `SegmentResult`, `SlackAPIClient`, `SlackClientError`, `SlackRequestNormalizer`, `UpdateRecord`, `agent_status`, `chat`, `create_snapshot`

### `clients`

**API-pattern symbols not in `__all__` (1):** `get_world_model_client`

### `collaborative_cells`

**API-pattern symbols not in `__all__` (3):** `get_all_cells`, `get_cell_snapshot`, `get_cells_by_category`

### `config`

**Unused API symbols (5):** `AIEvalSettings`, `ResearchSettings`, `reset_ai_eval_settings`, `reset_integration_settings`, `reset_research_settings`
**API-pattern symbols not in `__all__` (23):** `CursorLangGraphConfig`, `RLSConfig`, `create_kernel_loader`, `create_memory_substrate_service`, `create_neo4j_client`, `create_observability_service`, `create_pgvector_client`, `create_redis_client`, `create_tool_registry`, `create_world_model_service`

### `core`

**Orphan files (1):** `core/fastapi_lifespan.py`
**Unused API symbols (17):** `RegistryError`, `ComponentNotFoundError`, `must_stay_async_route`, `must_stay_async_protocol`, `must_stay_async_interface`, `get_error_chain`, `get_errors_by_type`, `get_error_stats`, `EventTypeConfig`, `discover_event_types`, `get_event_types_by_category`, `validate_event_payload`, `get_event_type_snapshot`, `SingletonServiceConfig`, `get_singleton_services_by_lifecycle`
  ... and 2 more
**Recommended `__all__` entries (22):** `AutoRegistry`, `DuplicateRegistrationError`, `GovernanceIntegration`, `ModuleDefinition`, `ModuleRegistry`, `ModuleStatus`, `SingletonLifecycle`, `ValidationError`, `discover_singleton_services`, `get_all_event_types`

### `domain_tensor_bridge`

**Orphan files (14):** `domain_tensor_bridge/analogical_reasoner.py`, `domain_tensor_bridge/anomaly_handler.py`, `domain_tensor_bridge/causal_reasoner.py`, `domain_tensor_bridge/compliance_checker.py`, `domain_tensor_bridge/decision_synthesizer.py`, `domain_tensor_bridge/domain_context_builder.py`, `domain_tensor_bridge/domain_packet_handler.py`, `domain_tensor_bridge/embedding_processor.py`, `domain_tensor_bridge/escalation_handler.py`, `domain_tensor_bridge/packet_formatter.py`, `domain_tensor_bridge/packet_validator.py`, `domain_tensor_bridge/reflective_auditor.py`, `domain_tensor_bridge/symbolic_reasoner.py`, `domain_tensor_bridge/tensoraios_bridge.py`

### `email_agent`

**Orphan files (1):** `email_agent/parser.py`
**Unused API symbols (5):** `create_flow`, `exchange_code_for_tokens`, `load_client_secrets`, `run_daily_digest`, `save_tokens`
**API-pattern symbols not in `__all__` (3):** `AccountConfig`, `get_account_config`, `get_email`

### `graph_adapter`

**Unused API symbols (1):** `PacketNodeAdapter`

### `ir_engine`

**Unused API symbols (16):** `DependencyEdge`, `EnvironmentSpec`, `GenerationTarget`, `GlobalInvariantsAck`, `InterfacesSpec`, `MetaContractValidationError`, `ObservabilitySpec`, `OrchestrationSpec`, `PacketSpec`, `RepoSpec`, `StandardsSpec`, `TestSpec`, `compile_contract_to_ir`, `compile_ir_to_python`, `compile_ir_to_single`
  ... and 1 more
**API-pattern symbols not in `__all__` (5):** `EscalationConfig`, `LogsConfig`, `MetricsConfig`, `RetryConfig`, `TracesConfig`

### `mac_agent`

**Orphan files (1):** `mac_agent/config.py`
**Unused API symbols (2):** `MacAgentClient`, `TaskExecutor`
**API-pattern symbols not in `__all__` (6):** `MacAgentConfig`, `create_error_event`, `create_handshake`, `create_heartbeat`, `create_task_result`, `get_config`

### `memory`

**Orphan files (9):** `memory/blob_store.py`, `memory/checkpoint_manager.py`, `memory/cross_encoder_reranker.py`, `memory/dead_letter_queue.py`, `memory/entity_extraction.py`, `memory/index_syncer.py`, `memory/substrate_repository_cached.py`, `memory/text_utils.py`, `memory/working_memory_adapter.py`
**Unused API symbols (31):** `ActionProposal`, `AlignmentReport`, `AttentionConfig`, `CHECKPOINT_PROMETHEUS_AVAILABLE`, `CheckpointMetrics`, `CheckpointValidator`, `DeduplicationEngineReport`, `GraphSession`, `InsightExtractionPipeline`, `KnowledgeGap`, `Neo4jIntrospector`, `PostgresIntrospector`, `ReasoningPhase`, `RetentionResult`, `SagaStep`
  ... and 16 more
**API-pattern symbols not in `__all__` (36):** `AgentPersistenceService`, `CrossEncoderConfig`, `EntityExtractionService`, `GovernanceHookRegistry`, `IdentityTierService`, `MemorySubstrateService`, `ReasoningReplayPipeline`, `SemanticService`, `TimelineService`, `create_embedding_provider`

### `memory_cache`

**Unused API symbols (3):** `CursorWorkingMemoryService`, `MemoryEventType`, `MemorySnapshot`

### `motifs`

**Orphan files (3):** `motifs/motif_feedback_graph.py`, `motifs/multimodal_plan_ranker.py`, `motifs/tensor_motif_linker.py`
**Unused API symbols (8):** `MotifEvent`, `MotifFeedbackGraph`, `MotifMetadata`, `MotifTrace`, `MultimodalPlanRanker`, `PlanCandidate`, `RankedPlan`, `TensorMotifLinker`

### `orchestration`

**Orphan files (1):** `orchestration/quantum_swarm_loader.py`
**Unused API symbols (27):** `CellOrchestrator`, `CellStep`, `CellWorkflow`, `ChainStatus`, `ChainStep`, `ControllerConfig`, `ControllerPhase`, `ControllerResult`, `ControllerState`, `ExecutionChain`, `ExecutionMode`, `ExecutionTarget`, `IRPipelineResult`, `KernelConfig`, `OrchestratorKernel`
  ... and 12 more
**API-pattern symbols not in `__all__` (3):** `get_client`, `get_client`, `get_tools_for_target`

### `orchestrators`

**Unused API symbols (4):** `EvolutionOrchestrator`, `WSBridgeConfig`, `WSEventRouter`, `enqueue_ws_event`
**API-pattern symbols not in `__all__` (4):** `get_all_orchestrators`, `get_orchestrator_snapshot`, `get_orchestrators_by_category`, `get_orchestrators_by_domain`

### `runtime`

**Orphan files (9):** `runtime/construct_enhancer.py`, `runtime/git_tool.py`, `runtime/gmp_approval.py`, `runtime/long_plan_tool.py`, `runtime/mcp_client.py`, `runtime/response_renderer.py`, `runtime/response_tagger.py`, `runtime/superprompt_emitter.py`, `runtime/tool_call_wrapper.py`
**Unused API symbols (6):** `DoraGraph`, `DoraMetrics`, `get_background_task_registry`, `get_empty_dora_block_python`, `get_wmc`, `guarded_execute_v2`
**API-pattern symbols not in `__all__` (23):** `AuthRateLimitConfig`, `MCPServerConfig`, `get_all_mcp_servers`, `get_auth_rate_limiter`, `get_calibration_score`, `get_config_path`, `get_environment`, `get_gmp_task`, `get_kernel_cached`, `get_kernel_order`

### `scripts`

**Orphan files (1):** `scripts/benchmark_standalone.py`

### `services`

**Orphan files (4):** `services/mac_tasks.py`, `services/ocr_engine.py`, `services/pdf_engine.py`, `services/tool_learning_scheduler.py`
**Unused API symbols (13):** `ocr_image`, `ocr_pdf_first_page`, `extract_pdf`, `save_to_s3`, `get_s3_presigned_url`, `download_file`, `save_to_disk`, `save_file`, `build_artifact_record`, `build_artifact_record_legacy`, `process_slack_file`, `ToolHealthSnapshot`, `register_tool_learning_jobs`
**Recommended `__all__` entries (11):** `MacTask`, `ToolFeedbackEntry`, `complete_task`, `enqueue_mac_task`, `enqueue_task`, `get_file_info`, `get_next_task`, `get_tool_feedback_service`, `list_tasks`, `mark_task_completed`

### `simulation`

**Unused API symbols (4):** `OutcomeEvaluator`, `ScenarioLoader`, `ScenarioType`, `SimulationMetrics`

### `tests`

**Orphan files (10):** `tests/test_integration_phase0.py`, `tests/test_memory_adapter.py`, `tests/test_memory_governance_gate.py`, `tests/test_policy_engine.py`, `tests/test_research_graph.py`, `tests/test_retention_refcount.py`, `tests/test_spec_normalizer_v2.py`, `tests/test_tool_registry.py`, `tests/test_violation_tracker_smoke.py`, `tests/test_wiring_integrity.py`

### `tools`

**Orphan files (1):** `tools/mac_protocol.py`

### `workers`

**Unused API symbols (6):** `AnomalyClassifierResponse`, `AnomalyResponseMonitorResponse`, `RemediationEngineRequest`, `RemediationEngineResponse`, `ViolationPatternsRequest`, `ViolationTrackerServiceResponse`
**API-pattern symbols not in `__all__` (5):** `create_anomaly_classifier`, `create_anomaly_response_monitor`, `create_remediation_engine`, `create_violation_patterns`, `create_violation_tracker_service`

### `workflows`

**Unused API symbols (12):** `ExtractionPattern`, `FileMapping`, `GateType`, `SessionDAG`, `SessionEdge`, `SessionNode`, `ValidationCheck`, `WorkflowState`, `get_session_dag`, `list_session_dags`, `register_session_dag`, `session_dag_registry`
**API-pattern symbols not in `__all__` (1):** `create_harvest_deploy_graph`

### `world_model`

**Unused API symbols (54):** `CausalEdge`, `CausalGraph`, `CausalLink`, `CausalPath`, `CausalQuery`, `CausalQueryResult`, `CausalRelationType`, `CausalStrength`, `ConstraintSet`, `ExtractedFact`, `HeuristicMatch`, `IWorldModelEngine`, `IWorldModelState`, `IWorldModelUpdater`, `IngestResult`
  ... and 39 more
**API-pattern symbols not in `__all__` (3):** `create_runtime_with_substrate`, `get_or_create_runtime`, `get_pool`
