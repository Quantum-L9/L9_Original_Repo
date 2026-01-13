# Dead Code Audit - Risk Matrix Report

**Total Findings:** 302
**Auto-fixable:** 0
**Manual Review Required:** 0

---

## 🔴 HIGH RISK

| File | Symbol | Type | Confidence | Action | Proposed Fix |
|------|--------|------|------------|--------|--------------|
| `core/memory/virtual_context.py:41` | `Memory.semantic_importance` | dataclass_field | 95% | WIRE_UP | Wire 'Memory.semantic_importance' to functionality... |
| `core/memory/virtual_context.py:50` | `Context.working_memory` | dataclass_field | 95% | WIRE_UP | Wire 'Context.working_memory' to functionality or ... |
| `core/memory/virtual_context.py:51` | `Context.archival_memory` | dataclass_field | 95% | WIRE_UP | Wire 'Context.archival_memory' to functionality or... |
| `core/agents/graph_state/graph_hydrator.py:60` | `HydratedAgentContext.all_directives` | dataclass_field | 95% | WIRE_UP | Wire 'HydratedAgentContext.all_directives' to func... |
| `core/agents/graph_state/graph_hydrator.py:67` | `HydratedAgentContext.safety_constraints` | dataclass_field | 95% | WIRE_UP | Wire 'HydratedAgentContext.safety_constraints' to ... |
| `core/agents/graph_state/agent_graph_loader.py:89` | `AgentGraphState.collaborator_ids` | dataclass_field | 95% | WIRE_UP | Wire 'AgentGraphState.collaborator_ids' to functio... |
| `core/governance/quick_fixes.py:58` | `FixResult.fix_id` | dataclass_field | 95% | WIRE_UP | Wire 'FixResult.fix_id' to functionality or delete... |
| `core/governance/quick_fixes.py:62` | `FixResult.original_match` | dataclass_field | 95% | WIRE_UP | Wire 'FixResult.original_match' to functionality o... |
| `core/governance/quick_fixes.py:63` | `FixResult.fixed_content` | dataclass_field | 95% | WIRE_UP | Wire 'FixResult.fixed_content' to functionality or... |
| `core/governance/approval_gate.py:36` | `EscalationResult.overrides` | dataclass_field | 95% | WIRE_UP | Wire 'EscalationResult.overrides' to functionality... |
| `core/evaluation/evaluator.py:29` | `EvaluationExample.expected_output` | dataclass_field | 95% | WIRE_UP | Wire 'EvaluationExample.expected_output' to functi... |
| `core/evaluation/evaluator.py:32` | `EvaluationExample.success_criteria` | dataclass_field | 95% | WIRE_UP | Wire 'EvaluationExample.success_criteria' to funct... |
| `core/evaluation/evaluator.py:47` | `EvaluationResult.eval_set_name` | dataclass_field | 95% | WIRE_UP | Wire 'EvaluationResult.eval_set_name' to functiona... |
| `core/evaluation/evaluator.py:52` | `EvaluationResult.avg_latency_ms` | dataclass_field | 95% | WIRE_UP | Wire 'EvaluationResult.avg_latency_ms' to function... |
| `core/evaluation/evaluator.py:53` | `EvaluationResult.max_latency_ms` | dataclass_field | 95% | WIRE_UP | Wire 'EvaluationResult.max_latency_ms' to function... |
| `core/evaluation/evaluator.py:54` | `EvaluationResult.min_latency_ms` | dataclass_field | 95% | WIRE_UP | Wire 'EvaluationResult.min_latency_ms' to function... |
| `core/evaluation/evaluator.py:55` | `EvaluationResult.p95_latency_ms` | dataclass_field | 95% | WIRE_UP | Wire 'EvaluationResult.p95_latency_ms' to function... |
| `core/evaluation/evaluator.py:56` | `EvaluationResult.tool_accuracy` | dataclass_field | 95% | WIRE_UP | Wire 'EvaluationResult.tool_accuracy' to functiona... |
| `core/evaluation/evaluator.py:57` | `EvaluationResult.llm_as_judge_score` | dataclass_field | 95% | WIRE_UP | Wire 'EvaluationResult.llm_as_judge_score' to func... |
| `memory/cypher_templates.py:59` | `CypherTemplate.example_params` | dataclass_field | 95% | WIRE_UP | Wire 'CypherTemplate.example_params' to functional... |
| `memory/schema_introspection.py:46` | `TableInfo.schema_name` | dataclass_field | 95% | WIRE_UP | Wire 'TableInfo.schema_name' to functionality or d... |
| `memory/schema_introspection.py:68` | `Neo4jLabelInfo.property_types` | dataclass_field | 95% | WIRE_UP | Wire 'Neo4jLabelInfo.property_types' to functional... |
| `memory/schema_introspection.py:88` | `SchemaSnapshot.indexes` | dataclass_field | 95% | WIRE_UP | Wire 'SchemaSnapshot.indexes' to functionality or ... |
| `memory/schema_introspection.py:92` | `SchemaSnapshot.relationship_types` | dataclass_field | 95% | WIRE_UP | Wire 'SchemaSnapshot.relationship_types' to functi... |
| `memory/schema_introspection.py:95` | `SchemaSnapshot.captured_at` | dataclass_field | 95% | WIRE_UP | Wire 'SchemaSnapshot.captured_at' to functionality... |
| `memory/schema_introspection.py:96` | `SchemaSnapshot.postgres_version` | dataclass_field | 95% | WIRE_UP | Wire 'SchemaSnapshot.postgres_version' to function... |
| `memory/schema_introspection.py:97` | `SchemaSnapshot.neo4j_version` | dataclass_field | 95% | WIRE_UP | Wire 'SchemaSnapshot.neo4j_version' to functionali... |
| `memory/tool_router.py:102` | `ToolSearchResult.search_time_ms` | dataclass_field | 95% | WIRE_UP | Wire 'ToolSearchResult.search_time_ms' to function... |
| `memory/tool_router.py:103` | `ToolSearchResult.total_tools` | dataclass_field | 95% | WIRE_UP | Wire 'ToolSearchResult.total_tools' to functionali... |
| `memory/hybrid_rag.py:73` | `GraphEnrichment.relationship_paths` | dataclass_field | 95% | WIRE_UP | Wire 'GraphEnrichment.relationship_paths' to funct... |
| `memory/hybrid_rag.py:76` | `GraphEnrichment.causal_chain` | dataclass_field | 95% | WIRE_UP | Wire 'GraphEnrichment.causal_chain' to functionali... |
| `memory/hybrid_rag.py:88` | `HybridResult.vector_hit` | dataclass_field | 95% | WIRE_UP | Wire 'HybridResult.vector_hit' to functionality or... |
| `memory/hybrid_rag.py:91` | `HybridResult.enrichment` | dataclass_field | 95% | WIRE_UP | Wire 'HybridResult.enrichment' to functionality or... |
| `memory/hybrid_rag.py:97` | `HybridResult.ranking_factors` | dataclass_field | 95% | WIRE_UP | Wire 'HybridResult.ranking_factors' to functionali... |
| `memory/hybrid_rag.py:108` | `HybridSearchResult.vector_search_ms` | dataclass_field | 95% | WIRE_UP | Wire 'HybridSearchResult.vector_search_ms' to func... |
| `memory/hybrid_rag.py:109` | `HybridSearchResult.entity_extraction_ms` | dataclass_field | 95% | WIRE_UP | Wire 'HybridSearchResult.entity_extraction_ms' to ... |
| `memory/hybrid_rag.py:110` | `HybridSearchResult.graph_enrichment_ms` | dataclass_field | 95% | WIRE_UP | Wire 'HybridSearchResult.graph_enrichment_ms' to f... |
| `memory/hybrid_rag.py:111` | `HybridSearchResult.total_ms` | dataclass_field | 95% | WIRE_UP | Wire 'HybridSearchResult.total_ms' to functionalit... |
| `memory/hybrid_rag.py:114` | `HybridSearchResult.vector_hits_count` | dataclass_field | 95% | WIRE_UP | Wire 'HybridSearchResult.vector_hits_count' to fun... |
| `memory/hybrid_rag.py:115` | `HybridSearchResult.enriched_count` | dataclass_field | 95% | WIRE_UP | Wire 'HybridSearchResult.enriched_count' to functi... |
| `memory/hybrid_rag.py:116` | `HybridSearchResult.total_entities_found` | dataclass_field | 95% | WIRE_UP | Wire 'HybridSearchResult.total_entities_found' to ... |
| `memory/hybrid_rag.py:117` | `HybridSearchResult.total_relationships_found` | dataclass_field | 95% | WIRE_UP | Wire 'HybridSearchResult.total_relationships_found... |
| `memory/graph_memory.py:94` | `GraphSession.ended_at` | dataclass_field | 95% | WIRE_UP | Wire 'GraphSession.ended_at' to functionality or d... |
| `memory/graph_memory.py:99` | `GraphSession.message_count` | dataclass_field | 95% | WIRE_UP | Wire 'GraphSession.message_count' to functionality... |
| `memory/graph_memory.py:110` | `ConversationContext.related_sessions` | dataclass_field | 95% | WIRE_UP | Wire 'ConversationContext.related_sessions' to fun... |
| `memory/graph_memory.py:116` | `ConversationContext.time_range_start` | dataclass_field | 95% | WIRE_UP | Wire 'ConversationContext.time_range_start' to fun... |
| `memory/graph_memory.py:117` | `ConversationContext.time_range_end` | dataclass_field | 95% | WIRE_UP | Wire 'ConversationContext.time_range_end' to funct... |
| `runtime/superprompt_emitter.py:46` | `SpecGap.suggestion` | dataclass_field | 95% | WIRE_UP | Wire 'SpecGap.suggestion' to functionality or dele... |
| `runtime/superprompt_emitter.py:57` | `GapAnalysis.important_gaps` | dataclass_field | 95% | WIRE_UP | Wire 'GapAnalysis.important_gaps' to functionality... |
| `runtime/superprompt_emitter.py:58` | `GapAnalysis.optional_gaps` | dataclass_field | 95% | WIRE_UP | Wire 'GapAnalysis.optional_gaps' to functionality ... |
| `runtime/superprompt_emitter.py:255` | `SuperPrompt.gaps_to_fill` | dataclass_field | 95% | WIRE_UP | Wire 'SuperPrompt.gaps_to_fill' to functionality o... |
| `runtime/superprompt_emitter.py:257` | `SuperPrompt.expected_format` | dataclass_field | 95% | WIRE_UP | Wire 'SuperPrompt.expected_format' to functionalit... |
| `world_model/updater.py:62` | `UpdateResult.affected_ids` | dataclass_field | 95% | WIRE_UP | Wire 'UpdateResult.affected_ids' to functionality ... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.twilio_adapter/config.py:43` | `TwilioAdapterConfig.twilio_adapter_enabled` | dataclass_field | 95% | WIRE_UP | Wire 'TwilioAdapterConfig.twilio_adapter_enabled' ... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.twilio_adapter/config.py:44` | `TwilioAdapterConfig.twilio_adapter_log_level` | dataclass_field | 95% | WIRE_UP | Wire 'TwilioAdapterConfig.twilio_adapter_log_level... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.twilio_adapter/config.py:52` | `TwilioAdapterConfig.default_timeout_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'TwilioAdapterConfig.default_timeout_seconds'... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.twilio_adapter/config.py:53` | `TwilioAdapterConfig.aios_timeout_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'TwilioAdapterConfig.aios_timeout_seconds' to... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.twilio_adapter/config.py:56` | `TwilioAdapterConfig.dedupe_cache_ttl_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'TwilioAdapterConfig.dedupe_cache_ttl_seconds... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.calendar_adapter/config.py:42` | `CalendarAdapterConfig.calendar_adapter_enabled` | dataclass_field | 95% | WIRE_UP | Wire 'CalendarAdapterConfig.calendar_adapter_enabl... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.calendar_adapter/config.py:43` | `CalendarAdapterConfig.calendar_adapter_log_level` | dataclass_field | 95% | WIRE_UP | Wire 'CalendarAdapterConfig.calendar_adapter_log_l... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.calendar_adapter/config.py:44` | `CalendarAdapterConfig.calendar_sync_interval_minutes` | dataclass_field | 95% | WIRE_UP | Wire 'CalendarAdapterConfig.calendar_sync_interval... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.calendar_adapter/config.py:52` | `CalendarAdapterConfig.default_timeout_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'CalendarAdapterConfig.default_timeout_second... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.calendar_adapter/config.py:53` | `CalendarAdapterConfig.aios_timeout_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'CalendarAdapterConfig.aios_timeout_seconds' ... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.calendar_adapter/config.py:56` | `CalendarAdapterConfig.dedupe_cache_ttl_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'CalendarAdapterConfig.dedupe_cache_ttl_secon... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.email_adapter/config.py:42` | `EmailAdapterConfig.email_adapter_enabled` | dataclass_field | 95% | WIRE_UP | Wire 'EmailAdapterConfig.email_adapter_enabled' to... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.email_adapter/config.py:43` | `EmailAdapterConfig.email_adapter_log_level` | dataclass_field | 95% | WIRE_UP | Wire 'EmailAdapterConfig.email_adapter_log_level' ... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.email_adapter/config.py:51` | `EmailAdapterConfig.default_timeout_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'EmailAdapterConfig.default_timeout_seconds' ... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.email_adapter/config.py:52` | `EmailAdapterConfig.aios_timeout_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'EmailAdapterConfig.aios_timeout_seconds' to ... |
| `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.email_adapter/config.py:55` | `EmailAdapterConfig.dedupe_cache_ttl_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'EmailAdapterConfig.dedupe_cache_ttl_seconds'... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/embedding_processor.py:37` | `ProcessedEmbedding.original_dim` | dataclass_field | 95% | WIRE_UP | Wire 'ProcessedEmbedding.original_dim' to function... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/embedding_processor.py:38` | `ProcessedEmbedding.processed_dim` | dataclass_field | 95% | WIRE_UP | Wire 'ProcessedEmbedding.processed_dim' to functio... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/embedding_processor.py:40` | `ProcessedEmbedding.normalized` | dataclass_field | 95% | WIRE_UP | Wire 'ProcessedEmbedding.normalized' to functional... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/compliance_checker.py:38` | `Rule.rule_type` | dataclass_field | 95% | WIRE_UP | Wire 'Rule.rule_type' to functionality or delete i... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/compliance_checker.py:46` | `ComplianceResult.compliant` | dataclass_field | 95% | WIRE_UP | Wire 'ComplianceResult.compliant' to functionality... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/compliance_checker.py:47` | `ComplianceResult.rules_checked` | dataclass_field | 95% | WIRE_UP | Wire 'ComplianceResult.rules_checked' to functiona... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/analogical_reasoner.py:37` | `Analogy.source_domain` | dataclass_field | 95% | WIRE_UP | Wire 'Analogy.source_domain' to functionality or d... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/analogical_reasoner.py:38` | `Analogy.target_domain` | dataclass_field | 95% | WIRE_UP | Wire 'Analogy.target_domain' to functionality or d... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/analogical_reasoner.py:41` | `Analogy.mapping` | dataclass_field | 95% | WIRE_UP | Wire 'Analogy.mapping' to functionality or delete ... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/reasoning_engine.py:43` | `ReasoningResult.modes_applied` | dataclass_field | 95% | WIRE_UP | Wire 'ReasoningResult.modes_applied' to functional... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/world_model_bridge.py:38` | `CausalFactor.factor_id` | dataclass_field | 95% | WIRE_UP | Wire 'CausalFactor.factor_id' to functionality or ... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/world_model_bridge.py:39` | `CausalFactor.factor_type` | dataclass_field | 95% | WIRE_UP | Wire 'CausalFactor.factor_type' to functionality o... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/world_model_bridge.py:41` | `CausalFactor.direction` | dataclass_field | 95% | WIRE_UP | Wire 'CausalFactor.direction' to functionality or ... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/world_model_bridge.py:48` | `Pattern.pattern_type` | dataclass_field | 95% | WIRE_UP | Wire 'Pattern.pattern_type' to functionality or de... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/world_model_bridge.py:50` | `Pattern.window_days` | dataclass_field | 95% | WIRE_UP | Wire 'Pattern.window_days' to functionality or del... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/anomaly_handler.py:57` | `AnomalyResponse.handled` | dataclass_field | 95% | WIRE_UP | Wire 'AnomalyResponse.handled' to functionality or... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/anomaly_handler.py:58` | `AnomalyResponse.action_taken` | dataclass_field | 95% | WIRE_UP | Wire 'AnomalyResponse.action_taken' to functionali... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/anomaly_handler.py:59` | `AnomalyResponse.escalated` | dataclass_field | 95% | WIRE_UP | Wire 'AnomalyResponse.escalated' to functionality ... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/reflective_auditor.py:37` | `AuditResult.audit_passed` | dataclass_field | 95% | WIRE_UP | Wire 'AuditResult.audit_passed' to functionality o... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/reflective_auditor.py:38` | `AuditResult.issues_found` | dataclass_field | 95% | WIRE_UP | Wire 'AuditResult.issues_found' to functionality o... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/reflective_auditor.py:40` | `AuditResult.suggestions` | dataclass_field | 95% | WIRE_UP | Wire 'AuditResult.suggestions' to functionality or... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/decision_synthesizer.py:41` | `Decision.reasoning_summary` | dataclass_field | 95% | WIRE_UP | Wire 'Decision.reasoning_summary' to functionality... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/decision_synthesizer.py:42` | `Decision.contributing_modes` | dataclass_field | 95% | WIRE_UP | Wire 'Decision.contributing_modes' to functionalit... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/decision_synthesizer.py:43` | `Decision.conflicts_resolved` | dataclass_field | 95% | WIRE_UP | Wire 'Decision.conflicts_resolved' to functionalit... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/packet_router.py:41` | `RoutingResult.handler_name` | dataclass_field | 95% | WIRE_UP | Wire 'RoutingResult.handler_name' to functionality... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/packet_router.py:43` | `RoutingResult.route_confidence` | dataclass_field | 95% | WIRE_UP | Wire 'RoutingResult.route_confidence' to functiona... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/packet_router.py:44` | `RoutingResult.fallback_used` | dataclass_field | 95% | WIRE_UP | Wire 'RoutingResult.fallback_used' to functionalit... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/causal_reasoner.py:37` | `CausalResult.causal_chain` | dataclass_field | 95% | WIRE_UP | Wire 'CausalResult.causal_chain' to functionality ... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/causal_reasoner.py:38` | `CausalResult.intervention_points` | dataclass_field | 95% | WIRE_UP | Wire 'CausalResult.intervention_points' to functio... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/causal_reasoner.py:39` | `CausalResult.causal_confidence` | dataclass_field | 95% | WIRE_UP | Wire 'CausalResult.causal_confidence' to functiona... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/symbolic_reasoner.py:37` | `RuleResult.rules_applied` | dataclass_field | 95% | WIRE_UP | Wire 'RuleResult.rules_applied' to functionality o... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/symbolic_reasoner.py:38` | `RuleResult.rule_confidence` | dataclass_field | 95% | WIRE_UP | Wire 'RuleResult.rule_confidence' to functionality... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/domain_context_builder.py:40` | `DomainContext.entity_data` | dataclass_field | 95% | WIRE_UP | Wire 'DomainContext.entity_data' to functionality ... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/domain_context_builder.py:41` | `DomainContext.domain_rules` | dataclass_field | 95% | WIRE_UP | Wire 'DomainContext.domain_rules' to functionality... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/escalation_handler.py:55` | `EscalationResult.escalated` | dataclass_field | 95% | WIRE_UP | Wire 'EscalationResult.escalated' to functionality... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/escalation_handler.py:56` | `EscalationResult.anchor` | dataclass_field | 95% | WIRE_UP | Wire 'EscalationResult.anchor' to functionality or... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/governance_bridge.py:56` | `GovernanceResult.escalation_level` | dataclass_field | 95% | WIRE_UP | Wire 'GovernanceResult.escalation_level' to functi... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/governance_bridge.py:57` | `GovernanceResult.audit_id` | dataclass_field | 95% | WIRE_UP | Wire 'GovernanceResult.audit_id' to functionality ... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/governance_bridge.py:65` | `EscalationResult.escalated` | dataclass_field | 95% | WIRE_UP | Wire 'EscalationResult.escalated' to functionality... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/governance_bridge.py:66` | `EscalationResult.anchor` | dataclass_field | 95% | WIRE_UP | Wire 'EscalationResult.anchor' to functionality or... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/context_enricher.py:41` | `EnrichedContext.original_payload` | dataclass_field | 95% | WIRE_UP | Wire 'EnrichedContext.original_payload' to functio... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/context_enricher.py:42` | `EnrichedContext.world_model_data` | dataclass_field | 95% | WIRE_UP | Wire 'EnrichedContext.world_model_data' to functio... |
| `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/context_enricher.py:44` | `EnrichedContext.semantic_entities` | dataclass_field | 95% | WIRE_UP | Wire 'EnrichedContext.semantic_entities' to functi... |
| `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_infrastructure_health.py:66` | `ServiceProbe.expected_response` | dataclass_field | 95% | WIRE_UP | Wire 'ServiceProbe.expected_response' to functiona... |
| `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_infrastructure_health.py:92` | `ConfigValidationError.actual_type` | dataclass_field | 95% | WIRE_UP | Wire 'ConfigValidationError.actual_type' to functi... |
| `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_infrastructure_health.py:106` | `HealthReport.performance_baseline` | dataclass_field | 95% | WIRE_UP | Wire 'HealthReport.performance_baseline' to functi... |
| `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py:94` | `FunctionDef.has_params` | dataclass_field | 95% | WIRE_UP | Wire 'FunctionDef.has_params' to functionality or ... |
| `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py:96` | `FunctionDef.is_private` | dataclass_field | 95% | WIRE_UP | Wire 'FunctionDef.is_private' to functionality or ... |
| `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py:104` | `ClassDef.base_classes` | dataclass_field | 95% | WIRE_UP | Wire 'ClassDef.base_classes' to functionality or d... |
| `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py:113` | `CallGraphEdge.callee` | dataclass_field | 95% | WIRE_UP | Wire 'CallGraphEdge.callee' to functionality or de... |
| `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py:114` | `CallGraphEdge.caller_file` | dataclass_field | 95% | WIRE_UP | Wire 'CallGraphEdge.caller_file' to functionality ... |
| `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py:120` | `IntegrityIssue.issue_type` | dataclass_field | 95% | WIRE_UP | Wire 'IntegrityIssue.issue_type' to functionality ... |
| `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py:126` | `IntegrityIssue.suggestion` | dataclass_field | 95% | WIRE_UP | Wire 'IntegrityIssue.suggestion' to functionality ... |
| `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py:135` | `IntegrityReport.duplicate_classes` | dataclass_field | 95% | WIRE_UP | Wire 'IntegrityReport.duplicate_classes' to functi... |
| `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py:136` | `IntegrityReport.dead_code_patterns` | dataclass_field | 95% | WIRE_UP | Wire 'IntegrityReport.dead_code_patterns' to funct... |
| `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py:137` | `IntegrityReport.call_graph` | dataclass_field | 95% | WIRE_UP | Wire 'IntegrityReport.call_graph' to functionality... |
| `api/adapters/calendar_adapter/config.py:46` | `CalendarAdapterConfig.calendar_adapter_enabled` | dataclass_field | 95% | WIRE_UP | Wire 'CalendarAdapterConfig.calendar_adapter_enabl... |
| `api/adapters/calendar_adapter/config.py:49` | `CalendarAdapterConfig.calendar_adapter_log_level` | dataclass_field | 95% | WIRE_UP | Wire 'CalendarAdapterConfig.calendar_adapter_log_l... |
| `api/adapters/calendar_adapter/config.py:52` | `CalendarAdapterConfig.calendar_sync_interval_minutes` | dataclass_field | 95% | WIRE_UP | Wire 'CalendarAdapterConfig.calendar_sync_interval... |
| `api/adapters/calendar_adapter/config.py:62` | `CalendarAdapterConfig.default_timeout_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'CalendarAdapterConfig.default_timeout_second... |
| `api/adapters/calendar_adapter/config.py:63` | `CalendarAdapterConfig.aios_timeout_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'CalendarAdapterConfig.aios_timeout_seconds' ... |
| `api/adapters/calendar_adapter/config.py:66` | `CalendarAdapterConfig.dedupe_cache_ttl_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'CalendarAdapterConfig.dedupe_cache_ttl_secon... |
| `api/adapters/email_adapter/config.py:49` | `EmailAdapterConfig.email_adapter_log_level` | dataclass_field | 95% | WIRE_UP | Wire 'EmailAdapterConfig.email_adapter_log_level' ... |
| `api/adapters/email_adapter/config.py:59` | `EmailAdapterConfig.default_timeout_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'EmailAdapterConfig.default_timeout_seconds' ... |
| `api/adapters/email_adapter/config.py:60` | `EmailAdapterConfig.aios_timeout_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'EmailAdapterConfig.aios_timeout_seconds' to ... |
| `api/adapters/email_adapter/config.py:63` | `EmailAdapterConfig.dedupe_cache_ttl_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'EmailAdapterConfig.dedupe_cache_ttl_seconds'... |
| `api/adapters/twilio_adapter/config.py:52` | `TwilioAdapterConfig.twilio_whatsapp_number` | dataclass_field | 95% | WIRE_UP | Wire 'TwilioAdapterConfig.twilio_whatsapp_number' ... |
| `api/adapters/twilio_adapter/config.py:55` | `TwilioAdapterConfig.twilio_adapter_log_level` | dataclass_field | 95% | WIRE_UP | Wire 'TwilioAdapterConfig.twilio_adapter_log_level... |
| `api/adapters/twilio_adapter/config.py:65` | `TwilioAdapterConfig.default_timeout_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'TwilioAdapterConfig.default_timeout_seconds'... |
| `api/adapters/twilio_adapter/config.py:66` | `TwilioAdapterConfig.aios_timeout_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'TwilioAdapterConfig.aios_timeout_seconds' to... |
| `api/adapters/twilio_adapter/config.py:69` | `TwilioAdapterConfig.dedupe_cache_ttl_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'TwilioAdapterConfig.dedupe_cache_ttl_seconds... |
| `upgrades/packet_envelope/config.py:53` | `JaegerConfig.sample_rate` | dataclass_field | 95% | WIRE_UP | Wire 'JaegerConfig.sample_rate' to functionality o... |
| `upgrades/packet_envelope/config.py:54` | `JaegerConfig.max_tag_length` | dataclass_field | 95% | WIRE_UP | Wire 'JaegerConfig.max_tag_length' to functionalit... |
| `upgrades/packet_envelope/config.py:62` | `PrometheusConfig.namespace` | dataclass_field | 95% | WIRE_UP | Wire 'PrometheusConfig.namespace' to functionality... |
| `upgrades/packet_envelope/config.py:73` | `ObservabilityPhaseConfig.trace_internal_calls` | dataclass_field | 95% | WIRE_UP | Wire 'ObservabilityPhaseConfig.trace_internal_call... |
| `upgrades/packet_envelope/config.py:74` | `ObservabilityPhaseConfig.trace_cache_ops` | dataclass_field | 95% | WIRE_UP | Wire 'ObservabilityPhaseConfig.trace_cache_ops' to... |
| `upgrades/packet_envelope/config.py:75` | `ObservabilityPhaseConfig.trace_serialization` | dataclass_field | 95% | WIRE_UP | Wire 'ObservabilityPhaseConfig.trace_serialization... |
| `upgrades/packet_envelope/config.py:87` | `CloudEventsConfig.spec_version` | dataclass_field | 95% | WIRE_UP | Wire 'CloudEventsConfig.spec_version' to functiona... |
| `upgrades/packet_envelope/config.py:88` | `CloudEventsConfig.source_prefix` | dataclass_field | 95% | WIRE_UP | Wire 'CloudEventsConfig.source_prefix' to function... |
| `upgrades/packet_envelope/config.py:89` | `CloudEventsConfig.default_content_type` | dataclass_field | 95% | WIRE_UP | Wire 'CloudEventsConfig.default_content_type' to f... |
| `upgrades/packet_envelope/config.py:90` | `CloudEventsConfig.max_event_size_bytes` | dataclass_field | 95% | WIRE_UP | Wire 'CloudEventsConfig.max_event_size_bytes' to f... |
| `upgrades/packet_envelope/config.py:91` | `CloudEventsConfig.schema_validation_enabled` | dataclass_field | 95% | WIRE_UP | Wire 'CloudEventsConfig.schema_validation_enabled'... |
| `upgrades/packet_envelope/config.py:109` | `BatchIngestionConfig.idempotency_cache_ttl_seconds` | dataclass_field | 95% | WIRE_UP | Wire 'BatchIngestionConfig.idempotency_cache_ttl_s... |
| `upgrades/packet_envelope/config.py:117` | `EventStoreConfig.max_events_per_aggregate` | dataclass_field | 95% | WIRE_UP | Wire 'EventStoreConfig.max_events_per_aggregate' t... |
| `upgrades/packet_envelope/config.py:118` | `EventStoreConfig.enable_compression` | dataclass_field | 95% | WIRE_UP | Wire 'EventStoreConfig.enable_compression' to func... |
| `upgrades/packet_envelope/config.py:127` | `ScalabilityPhaseConfig.cqrs_enabled` | dataclass_field | 95% | WIRE_UP | Wire 'ScalabilityPhaseConfig.cqrs_enabled' to func... |
| `upgrades/packet_envelope/config.py:128` | `ScalabilityPhaseConfig.streaming_enabled` | dataclass_field | 95% | WIRE_UP | Wire 'ScalabilityPhaseConfig.streaming_enabled' to... |
| `upgrades/packet_envelope/config.py:140` | `RetentionConfig.default_ttl_days` | dataclass_field | 95% | WIRE_UP | Wire 'RetentionConfig.default_ttl_days' to functio... |
| `upgrades/packet_envelope/config.py:141` | `RetentionConfig.pii_ttl_days` | dataclass_field | 95% | WIRE_UP | Wire 'RetentionConfig.pii_ttl_days' to functionali... |
| `upgrades/packet_envelope/config.py:142` | `RetentionConfig.audit_log_ttl_days` | dataclass_field | 95% | WIRE_UP | Wire 'RetentionConfig.audit_log_ttl_days' to funct... |
| `upgrades/packet_envelope/config.py:143` | `RetentionConfig.enable_auto_cleanup` | dataclass_field | 95% | WIRE_UP | Wire 'RetentionConfig.enable_auto_cleanup' to func... |
| `upgrades/packet_envelope/config.py:144` | `RetentionConfig.cleanup_batch_size` | dataclass_field | 95% | WIRE_UP | Wire 'RetentionConfig.cleanup_batch_size' to funct... |
| `upgrades/packet_envelope/config.py:153` | `GDPRConfig.enable_anonymization` | dataclass_field | 95% | WIRE_UP | Wire 'GDPRConfig.enable_anonymization' to function... |
| `upgrades/packet_envelope/config.py:154` | `GDPRConfig.proof_signature_algorithm` | dataclass_field | 95% | WIRE_UP | Wire 'GDPRConfig.proof_signature_algorithm' to fun... |
| `upgrades/packet_envelope/config.py:161` | `GovernancePhaseConfig.retention` | dataclass_field | 95% | WIRE_UP | Wire 'GovernancePhaseConfig.retention' to function... |
| `upgrades/packet_envelope/config.py:163` | `GovernancePhaseConfig.compliance_logging_enabled` | dataclass_field | 95% | WIRE_UP | Wire 'GovernancePhaseConfig.compliance_logging_ena... |
| `upgrades/packet_envelope/config.py:176` | `PacketEnvelopeUpgradeConfig.phase_2_enabled` | dataclass_field | 95% | WIRE_UP | Wire 'PacketEnvelopeUpgradeConfig.phase_2_enabled'... |
| `upgrades/packet_envelope/config.py:179` | `PacketEnvelopeUpgradeConfig.phase_3_enabled` | dataclass_field | 95% | WIRE_UP | Wire 'PacketEnvelopeUpgradeConfig.phase_3_enabled'... |
| `upgrades/packet_envelope/config.py:182` | `PacketEnvelopeUpgradeConfig.phase_4_enabled` | dataclass_field | 95% | WIRE_UP | Wire 'PacketEnvelopeUpgradeConfig.phase_4_enabled'... |
| `upgrades/packet_envelope/config.py:185` | `PacketEnvelopeUpgradeConfig.phase_5_enabled` | dataclass_field | 95% | WIRE_UP | Wire 'PacketEnvelopeUpgradeConfig.phase_5_enabled'... |
| `upgrades/packet_envelope/config.py:199` | `PacketEnvelopeUpgradeConfig.rollback_enabled` | dataclass_field | 95% | WIRE_UP | Wire 'PacketEnvelopeUpgradeConfig.rollback_enabled... |
| `upgrades/packet_envelope/config.py:200` | `PacketEnvelopeUpgradeConfig.dry_run_mode` | dataclass_field | 95% | WIRE_UP | Wire 'PacketEnvelopeUpgradeConfig.dry_run_mode' to... |
| `upgrades/packet_envelope/scalability.py:424` | `Snapshot.aggregate_version` | dataclass_field | 95% | WIRE_UP | Wire 'Snapshot.aggregate_version' to functionality... |
| `upgrades/packet_envelope/integration.py:71` | `UpgradeState.rollback_available` | dataclass_field | 95% | WIRE_UP | Wire 'UpgradeState.rollback_available' to function... |
| `igor/01-07-2026/L9 Memory Substrate Audit/substrate_alignment.py:16` | `AlignmentReport.missing_in_postgres` | dataclass_field | 95% | WIRE_UP | Wire 'AlignmentReport.missing_in_postgres' to func... |
| `igor/01-07-2026/L9 Memory Substrate Audit/substrate_alignment.py:17` | `AlignmentReport.missing_in_qdrant` | dataclass_field | 95% | WIRE_UP | Wire 'AlignmentReport.missing_in_qdrant' to functi... |
| `igor/01-07-2026/L9 Memory Substrate Audit/substrate_alignment.py:19` | `AlignmentReport.total_packets_postgres` | dataclass_field | 95% | WIRE_UP | Wire 'AlignmentReport.total_packets_postgres' to f... |
| `igor/01-07-2026/L9 Memory Substrate Audit/substrate_alignment.py:20` | `AlignmentReport.total_nodes_neo4j` | dataclass_field | 95% | WIRE_UP | Wire 'AlignmentReport.total_nodes_neo4j' to functi... |
| `igor/01-07-2026/L9 Memory Substrate Audit/substrate_alignment.py:21` | `AlignmentReport.total_vectors_qdrant` | dataclass_field | 95% | WIRE_UP | Wire 'AlignmentReport.total_vectors_qdrant' to fun... |
| `igor/audit-tools/services_research_tools_perplexity_client.py:120` | `PerplexityResponse.search_results` | dataclass_field | 95% | WIRE_UP | Wire 'PerplexityResponse.search_results' to functi... |
| `services/research/tools/perplexity_client.py:132` | `PerplexityResponse.search_results` | dataclass_field | 95% | WIRE_UP | Wire 'PerplexityResponse.search_results' to functi... |
| `core/agents/selfreflection.py:109` | `ReflectionResult.patterns_observed` | dataclass_field | 65% | WIRE_UP | Wire 'ReflectionResult.patterns_observed' to funct... |
| `core/agents/selfreflection.py:112` | `ReflectionResult.analysis_duration_ms` | dataclass_field | 65% | WIRE_UP | Wire 'ReflectionResult.analysis_duration_ms' to fu... |
| `core/agents/selfreflection.py:113` | `ReflectionResult.analyzed_at` | dataclass_field | 65% | WIRE_UP | Wire 'ReflectionResult.analyzed_at' to functionali... |
| `core/governance/credentials_policy.py:60` | `SecretPattern.redact_pattern` | dataclass_field | 65% | WIRE_UP | Wire 'SecretPattern.redact_pattern' to functionali... |
| `core/governance/credentials_policy.py:71` | `SecretViolation.match_preview` | dataclass_field | 65% | WIRE_UP | Wire 'SecretViolation.match_preview' to functional... |
| `.dora/dora.block/python-header-template-enterprise.py:194` | `ModuleMetadata.execution_mode` | dataclass_field | 65% | WIRE_UP | Wire 'ModuleMetadata.execution_mode' to functional... |
| `collaborative_cells/base_cell.py:44` | `CellConfig.store_packets` | dataclass_field | 65% | WIRE_UP | Wire 'CellConfig.store_packets' to functionality o... |
| `collaborative_cells/base_cell.py:57` | `AgentMessage.round_number` | dataclass_field | 65% | WIRE_UP | Wire 'AgentMessage.round_number' to functionality ... |
| `collaborative_cells/base_cell.py:64` | `CellRound.round_number` | dataclass_field | 65% | WIRE_UP | Wire 'CellRound.round_number' to functionality or ... |
| `collaborative_cells/base_cell.py:83` | `CellResult.rounds` | dataclass_field | 65% | WIRE_UP | Wire 'CellResult.rounds' to functionality or delet... |
| `runtime/dora.py:51` | `DoraMetrics.errors_detected` | dataclass_field | 65% | WIRE_UP | Wire 'DoraMetrics.errors_detected' to functionalit... |
| `runtime/dora.py:52` | `DoraMetrics.stability_score` | dataclass_field | 65% | WIRE_UP | Wire 'DoraMetrics.stability_score' to functionalit... |
| `simulation/outcome_evaluator.py:101` | `CriterionResult.weighted_score` | dataclass_field | 65% | WIRE_UP | Wire 'CriterionResult.weighted_score' to functiona... |
| `simulation/outcome_evaluator.py:117` | `EvaluationResult.evaluated_at` | dataclass_field | 65% | WIRE_UP | Wire 'EvaluationResult.evaluated_at' to functional... |
| `simulation/simulation_engine.py:59` | `SimulationConfig.parallel_actions` | dataclass_field | 65% | WIRE_UP | Wire 'SimulationConfig.parallel_actions' to functi... |
| `simulation/simulation_engine.py:60` | `SimulationConfig.collect_metrics` | dataclass_field | 65% | WIRE_UP | Wire 'SimulationConfig.collect_metrics' to functio... |
| `simulation/simulation_engine.py:71` | `SimulationMetrics.resource_usage` | dataclass_field | 65% | WIRE_UP | Wire 'SimulationMetrics.resource_usage' to functio... |
| `simulation/simulation_engine.py:82` | `SimulationStep.action_id` | dataclass_field | 65% | WIRE_UP | Wire 'SimulationStep.action_id' to functionality o... |
| `simulation/simulation_engine.py:90` | `SimulationStep.dependencies_satisfied` | dataclass_field | 65% | WIRE_UP | Wire 'SimulationStep.dependencies_satisfied' to fu... |
| `agents/research_agent.py:57` | `PromptVariation.audience` | dataclass_field | 65% | WIRE_UP | Wire 'PromptVariation.audience' to functionality o... |
| `agents/research_agent.py:67` | `ResearchResponse.raw_response` | dataclass_field | 65% | WIRE_UP | Wire 'ResearchResponse.raw_response' to functional... |
| `agents/research_agent.py:69` | `ResearchResponse.code_snippets` | dataclass_field | 65% | WIRE_UP | Wire 'ResearchResponse.code_snippets' to functiona... |
| `agents/research_agent.py:108` | `ResearchTask.max_sources` | dataclass_field | 65% | WIRE_UP | Wire 'ResearchTask.max_sources' to functionality o... |
| `agents/research_agent.py:109` | `ResearchTask.stages` | dataclass_field | 65% | WIRE_UP | Wire 'ResearchTask.stages' to functionality or del... |
| `agents/research_agent.py:118` | `SpecResult.yaml_content` | dataclass_field | 65% | WIRE_UP | Wire 'SpecResult.yaml_content' to functionality or... |
| `world_model/causal_graph.py:59` | `CausalEdge.edge_type` | dataclass_field | 65% | WIRE_UP | Wire 'CausalEdge.edge_type' to functionality or de... |
| `world_model/registry.py:39` | `EntityTypeSchema.type_name` | dataclass_field | 65% | WIRE_UP | Wire 'EntityTypeSchema.type_name' to functionality... |
| `world_model/registry.py:42` | `EntityTypeSchema.parent_type` | dataclass_field | 65% | WIRE_UP | Wire 'EntityTypeSchema.parent_type' to functionali... |
| `world_model/registry.py:54` | `RelationTypeSchema.type_name` | dataclass_field | 65% | WIRE_UP | Wire 'RelationTypeSchema.type_name' to functionali... |
| `world_model/registry.py:56` | `RelationTypeSchema.source_types` | dataclass_field | 65% | WIRE_UP | Wire 'RelationTypeSchema.source_types' to function... |
| `world_model/registry.py:57` | `RelationTypeSchema.target_types` | dataclass_field | 65% | WIRE_UP | Wire 'RelationTypeSchema.target_types' to function... |
| `world_model/registry.py:59` | `RelationTypeSchema.cardinality` | dataclass_field | 65% | WIRE_UP | Wire 'RelationTypeSchema.cardinality' to functiona... |
| `world_model/knowledge_ingestor.py:100` | `ExtractedFact.fact_type` | dataclass_field | 65% | WIRE_UP | Wire 'ExtractedFact.fact_type' to functionality or... |
| `world_model/knowledge_ingestor.py:181` | `IngestorConfig.validate_entities` | dataclass_field | 65% | WIRE_UP | Wire 'IngestorConfig.validate_entities' to functio... |
| `world_model/knowledge_ingestor.py:182` | `IngestorConfig.extract_relations` | dataclass_field | 65% | WIRE_UP | Wire 'IngestorConfig.extract_relations' to functio... |
| `world_model/knowledge_ingestor.py:184` | `IngestorConfig.normalize_patterns` | dataclass_field | 65% | WIRE_UP | Wire 'IngestorConfig.normalize_patterns' to functi... |
| `world_model/knowledge_ingestor.py:185` | `IngestorConfig.normalize_heuristics` | dataclass_field | 65% | WIRE_UP | Wire 'IngestorConfig.normalize_heuristics' to func... |
| `world_model/reflection_memory.py:115` | `Pattern.outcomes` | dataclass_field | 65% | WIRE_UP | Wire 'Pattern.outcomes' to functionality or delete... |
| `world_model/reflection_memory.py:117` | `Pattern.first_seen` | dataclass_field | 65% | WIRE_UP | Wire 'Pattern.first_seen' to functionality or dele... |
| `world_model/reflection_memory.py:138` | `Improvement.action_required` | dataclass_field | 65% | WIRE_UP | Wire 'Improvement.action_required' to functionalit... |
| `world_model/reflection_memory.py:141` | `Improvement.expected_impact` | dataclass_field | 65% | WIRE_UP | Wire 'Improvement.expected_impact' to functionalit... |
| `world_model/runtime.py:95` | `RuntimeConfig.enable_validation` | dataclass_field | 65% | WIRE_UP | Wire 'RuntimeConfig.enable_validation' to function... |
| `world_model/runtime.py:99` | `RuntimeConfig.concurrent_reads` | dataclass_field | 65% | WIRE_UP | Wire 'RuntimeConfig.concurrent_reads' to functiona... |
| `world_model/runtime.py:206` | `UpdateRecord.old_value` | dataclass_field | 65% | WIRE_UP | Wire 'UpdateRecord.old_value' to functionality or ... |
| `world_model/runtime.py:207` | `UpdateRecord.new_value` | dataclass_field | 65% | WIRE_UP | Wire 'UpdateRecord.new_value' to functionality or ... |
| `codegen/Perplexity-Search-Pack/autonomous-research-agent.py:29` | `PromptVariation.audience` | dataclass_field | 65% | WIRE_UP | Wire 'PromptVariation.audience' to functionality o... |
| `codegen/Perplexity-Search-Pack/autonomous-research-agent.py:39` | `ResearchResponse.raw_response` | dataclass_field | 65% | WIRE_UP | Wire 'ResearchResponse.raw_response' to functional... |
| `codegen/Perplexity-Search-Pack/autonomous-research-agent.py:41` | `ResearchResponse.code_snippets` | dataclass_field | 65% | WIRE_UP | Wire 'ResearchResponse.code_snippets' to functiona... |
| `scripts/audit/audit_shared_core.py:33` | `CacheEntry.modified` | dataclass_field | 65% | WIRE_UP | Wire 'CacheEntry.modified' to functionality or del... |
| `scripts/audit/audit_shared_core.py:129` | `CallGraphEdge.caller_file` | dataclass_field | 65% | WIRE_UP | Wire 'CallGraphEdge.caller_file' to functionality ... |
| `scripts/audit/audit_shared_core.py:130` | `CallGraphEdge.callee` | dataclass_field | 65% | WIRE_UP | Wire 'CallGraphEdge.callee' to functionality or de... |
| `scripts/audit/audit_shared_core.py:131` | `CallGraphEdge.callee_type` | dataclass_field | 65% | WIRE_UP | Wire 'CallGraphEdge.callee_type' to functionality ... |
| `scripts/audit/categorize_dead_code.py:67` | `CategorizedFinding.action_reason` | dataclass_field | 65% | WIRE_UP | Wire 'CategorizedFinding.action_reason' to functio... |
| `scripts/audit/tier1/audit_infrastructure_health.py:146` | `DependencyCheck.all_available` | dataclass_field | 65% | WIRE_UP | Wire 'DependencyCheck.all_available' to functional... |
| `scripts/audit/tier1/audit_infrastructure_health.py:147` | `DependencyCheck.missing_dependencies` | dataclass_field | 65% | WIRE_UP | Wire 'DependencyCheck.missing_dependencies' to fun... |
| `scripts/audit/tier1/audit_infrastructure_health.py:159` | `InfrastructureReport.health_checks` | dataclass_field | 65% | WIRE_UP | Wire 'InfrastructureReport.health_checks' to funct... |
| `scripts/audit/tier1/audit_infrastructure_health.py:160` | `InfrastructureReport.config_validations` | dataclass_field | 65% | WIRE_UP | Wire 'InfrastructureReport.config_validations' to ... |
| `scripts/audit/tier1/audit_infrastructure_health.py:161` | `InfrastructureReport.dependency_checks` | dataclass_field | 65% | WIRE_UP | Wire 'InfrastructureReport.dependency_checks' to f... |
| `scripts/audit/tier1/audit_infrastructure_health.py:162` | `InfrastructureReport.startup_sequence` | dataclass_field | 65% | WIRE_UP | Wire 'InfrastructureReport.startup_sequence' to fu... |
| `scripts/audit/run_all.py:145` | `AuditResult.file_outputs` | dataclass_field | 65% | WIRE_UP | Wire 'AuditResult.file_outputs' to functionality o... |
| `scripts/audit/tier1/audit_capability_inventory.py:125` | `ParameterSchema.enum_values` | dataclass_field | 65% | WIRE_UP | Wire 'ParameterSchema.enum_values' to functionalit... |
| `scripts/audit/tier1/audit_capability_inventory.py:133` | `MCPSchema.output_schema` | dataclass_field | 65% | WIRE_UP | Wire 'MCPSchema.output_schema' to functionality or... |
| `scripts/audit/tier1/audit_capability_inventory.py:146` | `CapabilityMethod.return_type` | dataclass_field | 65% | WIRE_UP | Wire 'CapabilityMethod.return_type' to functionali... |
| `scripts/audit/tier1/audit_capability_inventory.py:147` | `CapabilityMethod.is_exposed` | dataclass_field | 65% | WIRE_UP | Wire 'CapabilityMethod.is_exposed' to functionalit... |
| `scripts/audit/tier1/audit_capability_inventory.py:149` | `CapabilityMethod.deprecation_reason` | dataclass_field | 65% | WIRE_UP | Wire 'CapabilityMethod.deprecation_reason' to func... |
| `scripts/audit/tier1/audit_capability_inventory.py:150` | `CapabilityMethod.version_added` | dataclass_field | 65% | WIRE_UP | Wire 'CapabilityMethod.version_added' to functiona... |
| `scripts/audit/tier1/audit_capability_inventory.py:151` | `CapabilityMethod.version_deprecated` | dataclass_field | 65% | WIRE_UP | Wire 'CapabilityMethod.version_deprecated' to func... |
| `scripts/audit/tier1/audit_capability_inventory.py:160` | `CapabilityMatrix.value_score` | dataclass_field | 65% | WIRE_UP | Wire 'CapabilityMatrix.value_score' to functionali... |
| `scripts/audit/tier1/audit_capability_inventory.py:166` | `CapabilityReport.exposed_tools` | dataclass_field | 65% | WIRE_UP | Wire 'CapabilityReport.exposed_tools' to functiona... |
| `scripts/audit/tier1/audit_capability_inventory.py:167` | `CapabilityReport.hidden_capabilities` | dataclass_field | 65% | WIRE_UP | Wire 'CapabilityReport.hidden_capabilities' to fun... |
| `scripts/audit/tier1/audit_capability_inventory.py:169` | `CapabilityReport.mcp_schemas` | dataclass_field | 65% | WIRE_UP | Wire 'CapabilityReport.mcp_schemas' to functionali... |
| `scripts/audit/tier1/audit_capability_inventory.py:170` | `CapabilityReport.missing_acl` | dataclass_field | 65% | WIRE_UP | Wire 'CapabilityReport.missing_acl' to functionali... |
| `scripts/audit/tier1/audit_capability_inventory.py:171` | `CapabilityReport.deprecated_methods` | dataclass_field | 65% | WIRE_UP | Wire 'CapabilityReport.deprecated_methods' to func... |
| `scripts/audit/tier1/audit_code_integrity.py:91` | `FileHashEntry.modified` | dataclass_field | 65% | WIRE_UP | Wire 'FileHashEntry.modified' to functionality or ... |
| `scripts/audit/tier1/audit_code_integrity.py:97` | `CallGraphEdge.caller_file` | dataclass_field | 65% | WIRE_UP | Wire 'CallGraphEdge.caller_file' to functionality ... |
| `scripts/audit/tier1/audit_code_integrity.py:98` | `CallGraphEdge.callee` | dataclass_field | 65% | WIRE_UP | Wire 'CallGraphEdge.callee' to functionality or de... |
| `scripts/audit/tier1/audit_code_integrity.py:99` | `CallGraphEdge.callee_type` | dataclass_field | 65% | WIRE_UP | Wire 'CallGraphEdge.callee_type' to functionality ... |
| `scripts/audit/tier1/audit_code_integrity.py:108` | `UncalledFunction.skip_reason` | dataclass_field | 65% | WIRE_UP | Wire 'UncalledFunction.skip_reason' to functionali... |
| `scripts/audit/tier1/audit_code_integrity.py:109` | `UncalledFunction.is_private` | dataclass_field | 65% | WIRE_UP | Wire 'UncalledFunction.is_private' to functionalit... |
| `scripts/audit/tier1/audit_code_integrity.py:117` | `OrphanClass.base_classes` | dataclass_field | 65% | WIRE_UP | Wire 'OrphanClass.base_classes' to functionality o... |
| `scripts/audit/tier1/audit_code_integrity.py:136` | `AuditReport.call_graph_edges` | dataclass_field | 65% | WIRE_UP | Wire 'AuditReport.call_graph_edges' to functionali... |
| `orchestration/task_router.py:151` | `RoutingDecision.decided_at` | dataclass_field | 65% | WIRE_UP | Wire 'RoutingDecision.decided_at' to functionality... |
| `orchestration/cell_orchestrator.py:121` | `WorkflowResult.aggregated_output` | dataclass_field | 65% | WIRE_UP | Wire 'WorkflowResult.aggregated_output' to functio... |
| `orchestration/orchestrator_kernel.py:134` | `KernelConfig.max_chain_steps` | dataclass_field | 65% | WIRE_UP | Wire 'KernelConfig.max_chain_steps' to functionali... |
| `orchestration/orchestrator_kernel.py:135` | `KernelConfig.step_timeout_ms` | dataclass_field | 65% | WIRE_UP | Wire 'KernelConfig.step_timeout_ms' to functionali... |
| `orchestration/orchestrator_kernel.py:136` | `KernelConfig.allow_parallel_chains` | dataclass_field | 65% | WIRE_UP | Wire 'KernelConfig.allow_parallel_chains' to funct... |
| `orchestration/plan_executor.py:155` | `ExecutorConfig.step_timeout_ms` | dataclass_field | 65% | WIRE_UP | Wire 'ExecutorConfig.step_timeout_ms' to functiona... |
| `upgrades/packet_envelope/standardization.py:87` | `CloudEvent._received_at` | dataclass_field | 65% | WIRE_UP | Wire 'CloudEvent._received_at' to functionality or... |
| `upgrades/packet_envelope/standardization.py:88` | `CloudEvent._processed_at` | dataclass_field | 65% | WIRE_UP | Wire 'CloudEvent._processed_at' to functionality o... |
| `upgrades/packet_envelope/standardization.py:328` | `EventSchema.encoding` | dataclass_field | 65% | WIRE_UP | Wire 'EventSchema.encoding' to functionality or de... |
| `upgrades/packet_envelope/standardization.py:331` | `EventSchema.deprecated_at` | dataclass_field | 65% | WIRE_UP | Wire 'EventSchema.deprecated_at' to functionality ... |
| `upgrades/packet_envelope/observability.py:70` | `ObservabilityConfig.sample_rate` | dataclass_field | 65% | WIRE_UP | Wire 'ObservabilityConfig.sample_rate' to function... |
| `upgrades/packet_envelope/observability.py:73` | `ObservabilityConfig.export_timeout_ms` | dataclass_field | 65% | WIRE_UP | Wire 'ObservabilityConfig.export_timeout_ms' to fu... |
| `upgrades/packet_envelope/observability.py:74` | `ObservabilityConfig.prometheus_port` | dataclass_field | 65% | WIRE_UP | Wire 'ObservabilityConfig.prometheus_port' to func... |
| `upgrades/packet_envelope/observability.py:77` | `ObservabilityConfig.trace_internal_calls` | dataclass_field | 65% | WIRE_UP | Wire 'ObservabilityConfig.trace_internal_calls' to... |
| `upgrades/packet_envelope/observability.py:78` | `ObservabilityConfig.trace_cache_ops` | dataclass_field | 65% | WIRE_UP | Wire 'ObservabilityConfig.trace_cache_ops' to func... |
| `upgrades/packet_envelope/observability.py:79` | `ObservabilityConfig.trace_serialization` | dataclass_field | 65% | WIRE_UP | Wire 'ObservabilityConfig.trace_serialization' to ... |
| `upgrades/packet_envelope/observability.py:82` | `ObservabilityConfig.baggage_fields` | dataclass_field | 65% | WIRE_UP | Wire 'ObservabilityConfig.baggage_fields' to funct... |
| `upgrades/packet_envelope/governance.py:63` | `DataRetentionConfig.pii_ttl_days` | dataclass_field | 65% | WIRE_UP | Wire 'DataRetentionConfig.pii_ttl_days' to functio... |
| `upgrades/packet_envelope/governance.py:64` | `DataRetentionConfig.audit_log_ttl_days` | dataclass_field | 65% | WIRE_UP | Wire 'DataRetentionConfig.audit_log_ttl_days' to f... |
| `upgrades/packet_envelope/governance.py:68` | `DataRetentionConfig.enable_anonymization` | dataclass_field | 65% | WIRE_UP | Wire 'DataRetentionConfig.enable_anonymization' to... |
| `upgrades/packet_envelope/governance.py:147` | `DeletionRequest.requested_by` | dataclass_field | 65% | WIRE_UP | Wire 'DeletionRequest.requested_by' to functionali... |
| `upgrades/packet_envelope/governance.py:148` | `DeletionRequest.requested_at` | dataclass_field | 65% | WIRE_UP | Wire 'DeletionRequest.requested_at' to functionali... |
| `upgrades/packet_envelope/governance.py:167` | `DeletionProof.deleted_aggregate_id` | dataclass_field | 65% | WIRE_UP | Wire 'DeletionProof.deleted_aggregate_id' to funct... |
| `upgrades/packet_envelope/governance.py:168` | `DeletionProof.deletion_timestamp` | dataclass_field | 65% | WIRE_UP | Wire 'DeletionProof.deletion_timestamp' to functio... |
| `upgrades/packet_envelope/governance.py:169` | `DeletionProof.data_hash` | dataclass_field | 65% | WIRE_UP | Wire 'DeletionProof.data_hash' to functionality or... |
| `upgrades/packet_envelope/governance.py:170` | `DeletionProof.proof_signature` | dataclass_field | 65% | WIRE_UP | Wire 'DeletionProof.proof_signature' to functional... |
| `upgrades/packet_envelope/governance.py:171` | `DeletionProof.cascading_proofs` | dataclass_field | 65% | WIRE_UP | Wire 'DeletionProof.cascading_proofs' to functiona... |
| `upgrades/packet_envelope/governance.py:331` | `AnonymizationRule.sensitive` | dataclass_field | 65% | WIRE_UP | Wire 'AnonymizationRule.sensitive' to functionalit... |
| `upgrades/packet_envelope/governance.py:460` | `ComplianceReport.report_type` | dataclass_field | 65% | WIRE_UP | Wire 'ComplianceReport.report_type' to functionali... |
| `upgrades/packet_envelope/governance.py:462` | `ComplianceReport.period_start` | dataclass_field | 65% | WIRE_UP | Wire 'ComplianceReport.period_start' to functional... |
| `upgrades/packet_envelope/governance.py:463` | `ComplianceReport.period_end` | dataclass_field | 65% | WIRE_UP | Wire 'ComplianceReport.period_end' to functionalit... |
| `ir_engine/deliberation_cell.py:45` | `DeliberationRound.round_number` | dataclass_field | 65% | WIRE_UP | Wire 'DeliberationRound.round_number' to functiona... |
| `ir_engine/deliberation_cell.py:46` | `DeliberationRound.producer_output` | dataclass_field | 65% | WIRE_UP | Wire 'DeliberationRound.producer_output' to functi... |
| `ir_engine/deliberation_cell.py:47` | `DeliberationRound.critique` | dataclass_field | 65% | WIRE_UP | Wire 'DeliberationRound.critique' to functionality... |
| `ir_engine/deliberation_cell.py:48` | `DeliberationRound.revisions_made` | dataclass_field | 65% | WIRE_UP | Wire 'DeliberationRound.revisions_made' to functio... |
| `ir_engine/deliberation_cell.py:59` | `DeliberationResult.rounds` | dataclass_field | 65% | WIRE_UP | Wire 'DeliberationResult.rounds' to functionality ... |
| `ir_engine/simulation_router.py:73` | `RankedCandidate.rank` | dataclass_field | 65% | WIRE_UP | Wire 'RankedCandidate.rank' to functionality or de... |
| `ir_engine/simulation_router.py:74` | `RankedCandidate.selection_reason` | dataclass_field | 65% | WIRE_UP | Wire 'RankedCandidate.selection_reason' to functio... |
| `ir_engine/compile_meta_to_ir.py:55` | `DependencyEdge.source_module` | dataclass_field | 65% | WIRE_UP | Wire 'DependencyEdge.source_module' to functionali... |
| `ir_engine/compile_meta_to_ir.py:92` | `TestSpec.test_file` | dataclass_field | 65% | WIRE_UP | Wire 'TestSpec.test_file' to functionality or dele... |
| `ir_engine/compile_meta_to_ir.py:108` | `WiringSpec.lifespan_init` | dataclass_field | 65% | WIRE_UP | Wire 'WiringSpec.lifespan_init' to functionality o... |

## 🟡 MEDIUM RISK

*No medium risk findings*

## 🟢 LOW RISK

*No low risk findings*

## 📋 Action Summary

| Action | Count | Description |
|--------|-------|-------------|
| WIRE_UP | 302 | Connect config to functionality |