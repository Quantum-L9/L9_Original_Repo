# GMP Phase 0 TODO Plan: Dead Code Remediation

**GMP ID:** GMP-63
**Task:** dead_code_remediation
**Risk Level:** Medium
**Generated:** 2026-01-13 18:16 EST

## Summary

- Total TODOs: 302
- Auto-fixable: 0
- Manual review: 0

---

## TODO Plan (LOCKED)

### 🔌 WIRE_UP (302 items)

#### [DC-W001] `Memory.semantic_importance`

- **File:** `core/memory/virtual_context.py`
- **Lines:** 41
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Memory.semantic_importance' to functionality or delete if unnecessary
```

#### [DC-W002] `Context.working_memory`

- **File:** `core/memory/virtual_context.py`
- **Lines:** 50
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Context.working_memory' to functionality or delete if unnecessary
```

#### [DC-W003] `Context.archival_memory`

- **File:** `core/memory/virtual_context.py`
- **Lines:** 51
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Context.archival_memory' to functionality or delete if unnecessary
```

#### [DC-W004] `HydratedAgentContext.all_directives`

- **File:** `core/agents/graph_state/graph_hydrator.py`
- **Lines:** 60
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'HydratedAgentContext.all_directives' to functionality or delete if unnecessary
```

#### [DC-W005] `HydratedAgentContext.safety_constraints`

- **File:** `core/agents/graph_state/graph_hydrator.py`
- **Lines:** 67
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'HydratedAgentContext.safety_constraints' to functionality or delete if unnecessary
```

#### [DC-W006] `AgentGraphState.collaborator_ids`

- **File:** `core/agents/graph_state/agent_graph_loader.py`
- **Lines:** 89
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AgentGraphState.collaborator_ids' to functionality or delete if unnecessary
```

#### [DC-W007] `FixResult.fix_id`

- **File:** `core/governance/quick_fixes.py`
- **Lines:** 58
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'FixResult.fix_id' to functionality or delete if unnecessary
```

#### [DC-W008] `FixResult.original_match`

- **File:** `core/governance/quick_fixes.py`
- **Lines:** 62
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'FixResult.original_match' to functionality or delete if unnecessary
```

#### [DC-W009] `FixResult.fixed_content`

- **File:** `core/governance/quick_fixes.py`
- **Lines:** 63
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'FixResult.fixed_content' to functionality or delete if unnecessary
```

#### [DC-W010] `EscalationResult.overrides`

- **File:** `core/governance/approval_gate.py`
- **Lines:** 36
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EscalationResult.overrides' to functionality or delete if unnecessary
```

#### [DC-W011] `EvaluationExample.expected_output`

- **File:** `core/evaluation/evaluator.py`
- **Lines:** 29
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EvaluationExample.expected_output' to functionality or delete if unnecessary
```

#### [DC-W012] `EvaluationExample.success_criteria`

- **File:** `core/evaluation/evaluator.py`
- **Lines:** 32
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EvaluationExample.success_criteria' to functionality or delete if unnecessary
```

#### [DC-W013] `EvaluationResult.eval_set_name`

- **File:** `core/evaluation/evaluator.py`
- **Lines:** 47
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EvaluationResult.eval_set_name' to functionality or delete if unnecessary
```

#### [DC-W014] `EvaluationResult.avg_latency_ms`

- **File:** `core/evaluation/evaluator.py`
- **Lines:** 52
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EvaluationResult.avg_latency_ms' to functionality or delete if unnecessary
```

#### [DC-W015] `EvaluationResult.max_latency_ms`

- **File:** `core/evaluation/evaluator.py`
- **Lines:** 53
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EvaluationResult.max_latency_ms' to functionality or delete if unnecessary
```

#### [DC-W016] `EvaluationResult.min_latency_ms`

- **File:** `core/evaluation/evaluator.py`
- **Lines:** 54
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EvaluationResult.min_latency_ms' to functionality or delete if unnecessary
```

#### [DC-W017] `EvaluationResult.p95_latency_ms`

- **File:** `core/evaluation/evaluator.py`
- **Lines:** 55
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EvaluationResult.p95_latency_ms' to functionality or delete if unnecessary
```

#### [DC-W018] `EvaluationResult.tool_accuracy`

- **File:** `core/evaluation/evaluator.py`
- **Lines:** 56
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EvaluationResult.tool_accuracy' to functionality or delete if unnecessary
```

#### [DC-W019] `EvaluationResult.llm_as_judge_score`

- **File:** `core/evaluation/evaluator.py`
- **Lines:** 57
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EvaluationResult.llm_as_judge_score' to functionality or delete if unnecessary
```

#### [DC-W020] `CypherTemplate.example_params`

- **File:** `memory/cypher_templates.py`
- **Lines:** 59
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CypherTemplate.example_params' to functionality or delete if unnecessary
```

#### [DC-W021] `TableInfo.schema_name`

- **File:** `memory/schema_introspection.py`
- **Lines:** 46
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'TableInfo.schema_name' to functionality or delete if unnecessary
```

#### [DC-W022] `Neo4jLabelInfo.property_types`

- **File:** `memory/schema_introspection.py`
- **Lines:** 68
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Neo4jLabelInfo.property_types' to functionality or delete if unnecessary
```

#### [DC-W023] `SchemaSnapshot.indexes`

- **File:** `memory/schema_introspection.py`
- **Lines:** 88
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SchemaSnapshot.indexes' to functionality or delete if unnecessary
```

#### [DC-W024] `SchemaSnapshot.relationship_types`

- **File:** `memory/schema_introspection.py`
- **Lines:** 92
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SchemaSnapshot.relationship_types' to functionality or delete if unnecessary
```

#### [DC-W025] `SchemaSnapshot.captured_at`

- **File:** `memory/schema_introspection.py`
- **Lines:** 95
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SchemaSnapshot.captured_at' to functionality or delete if unnecessary
```

#### [DC-W026] `SchemaSnapshot.postgres_version`

- **File:** `memory/schema_introspection.py`
- **Lines:** 96
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SchemaSnapshot.postgres_version' to functionality or delete if unnecessary
```

#### [DC-W027] `SchemaSnapshot.neo4j_version`

- **File:** `memory/schema_introspection.py`
- **Lines:** 97
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SchemaSnapshot.neo4j_version' to functionality or delete if unnecessary
```

#### [DC-W028] `ToolSearchResult.search_time_ms`

- **File:** `memory/tool_router.py`
- **Lines:** 102
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ToolSearchResult.search_time_ms' to functionality or delete if unnecessary
```

#### [DC-W029] `ToolSearchResult.total_tools`

- **File:** `memory/tool_router.py`
- **Lines:** 103
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ToolSearchResult.total_tools' to functionality or delete if unnecessary
```

#### [DC-W030] `GraphEnrichment.relationship_paths`

- **File:** `memory/hybrid_rag.py`
- **Lines:** 73
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'GraphEnrichment.relationship_paths' to functionality or delete if unnecessary
```

#### [DC-W031] `GraphEnrichment.causal_chain`

- **File:** `memory/hybrid_rag.py`
- **Lines:** 76
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'GraphEnrichment.causal_chain' to functionality or delete if unnecessary
```

#### [DC-W032] `HybridResult.vector_hit`

- **File:** `memory/hybrid_rag.py`
- **Lines:** 88
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'HybridResult.vector_hit' to functionality or delete if unnecessary
```

#### [DC-W033] `HybridResult.enrichment`

- **File:** `memory/hybrid_rag.py`
- **Lines:** 91
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'HybridResult.enrichment' to functionality or delete if unnecessary
```

#### [DC-W034] `HybridResult.ranking_factors`

- **File:** `memory/hybrid_rag.py`
- **Lines:** 97
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'HybridResult.ranking_factors' to functionality or delete if unnecessary
```

#### [DC-W035] `HybridSearchResult.vector_search_ms`

- **File:** `memory/hybrid_rag.py`
- **Lines:** 108
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'HybridSearchResult.vector_search_ms' to functionality or delete if unnecessary
```

#### [DC-W036] `HybridSearchResult.entity_extraction_ms`

- **File:** `memory/hybrid_rag.py`
- **Lines:** 109
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'HybridSearchResult.entity_extraction_ms' to functionality or delete if unnecessary
```

#### [DC-W037] `HybridSearchResult.graph_enrichment_ms`

- **File:** `memory/hybrid_rag.py`
- **Lines:** 110
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'HybridSearchResult.graph_enrichment_ms' to functionality or delete if unnecessary
```

#### [DC-W038] `HybridSearchResult.total_ms`

- **File:** `memory/hybrid_rag.py`
- **Lines:** 111
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'HybridSearchResult.total_ms' to functionality or delete if unnecessary
```

#### [DC-W039] `HybridSearchResult.vector_hits_count`

- **File:** `memory/hybrid_rag.py`
- **Lines:** 114
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'HybridSearchResult.vector_hits_count' to functionality or delete if unnecessary
```

#### [DC-W040] `HybridSearchResult.enriched_count`

- **File:** `memory/hybrid_rag.py`
- **Lines:** 115
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'HybridSearchResult.enriched_count' to functionality or delete if unnecessary
```

#### [DC-W041] `HybridSearchResult.total_entities_found`

- **File:** `memory/hybrid_rag.py`
- **Lines:** 116
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'HybridSearchResult.total_entities_found' to functionality or delete if unnecessary
```

#### [DC-W042] `HybridSearchResult.total_relationships_found`

- **File:** `memory/hybrid_rag.py`
- **Lines:** 117
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'HybridSearchResult.total_relationships_found' to functionality or delete if unnecessary
```

#### [DC-W043] `GraphSession.ended_at`

- **File:** `memory/graph_memory.py`
- **Lines:** 94
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'GraphSession.ended_at' to functionality or delete if unnecessary
```

#### [DC-W044] `GraphSession.message_count`

- **File:** `memory/graph_memory.py`
- **Lines:** 99
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'GraphSession.message_count' to functionality or delete if unnecessary
```

#### [DC-W045] `ConversationContext.related_sessions`

- **File:** `memory/graph_memory.py`
- **Lines:** 110
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ConversationContext.related_sessions' to functionality or delete if unnecessary
```

#### [DC-W046] `ConversationContext.time_range_start`

- **File:** `memory/graph_memory.py`
- **Lines:** 116
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ConversationContext.time_range_start' to functionality or delete if unnecessary
```

#### [DC-W047] `ConversationContext.time_range_end`

- **File:** `memory/graph_memory.py`
- **Lines:** 117
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ConversationContext.time_range_end' to functionality or delete if unnecessary
```

#### [DC-W048] `SpecGap.suggestion`

- **File:** `runtime/superprompt_emitter.py`
- **Lines:** 46
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SpecGap.suggestion' to functionality or delete if unnecessary
```

#### [DC-W049] `GapAnalysis.important_gaps`

- **File:** `runtime/superprompt_emitter.py`
- **Lines:** 57
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'GapAnalysis.important_gaps' to functionality or delete if unnecessary
```

#### [DC-W050] `GapAnalysis.optional_gaps`

- **File:** `runtime/superprompt_emitter.py`
- **Lines:** 58
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'GapAnalysis.optional_gaps' to functionality or delete if unnecessary
```

#### [DC-W051] `SuperPrompt.gaps_to_fill`

- **File:** `runtime/superprompt_emitter.py`
- **Lines:** 255
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SuperPrompt.gaps_to_fill' to functionality or delete if unnecessary
```

#### [DC-W052] `SuperPrompt.expected_format`

- **File:** `runtime/superprompt_emitter.py`
- **Lines:** 257
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SuperPrompt.expected_format' to functionality or delete if unnecessary
```

#### [DC-W053] `UpdateResult.affected_ids`

- **File:** `world_model/updater.py`
- **Lines:** 62
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'UpdateResult.affected_ids' to functionality or delete if unnecessary
```

#### [DC-W054] `TwilioAdapterConfig.twilio_adapter_enabled`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.twilio_adapter/config.py`
- **Lines:** 43
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'TwilioAdapterConfig.twilio_adapter_enabled' to functionality or delete if unnecessary
```

#### [DC-W055] `TwilioAdapterConfig.twilio_adapter_log_level`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.twilio_adapter/config.py`
- **Lines:** 44
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'TwilioAdapterConfig.twilio_adapter_log_level' to functionality or delete if unnecessary
```

#### [DC-W056] `TwilioAdapterConfig.default_timeout_seconds`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.twilio_adapter/config.py`
- **Lines:** 52
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'TwilioAdapterConfig.default_timeout_seconds' to functionality or delete if unnecessary
```

#### [DC-W057] `TwilioAdapterConfig.aios_timeout_seconds`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.twilio_adapter/config.py`
- **Lines:** 53
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'TwilioAdapterConfig.aios_timeout_seconds' to functionality or delete if unnecessary
```

#### [DC-W058] `TwilioAdapterConfig.dedupe_cache_ttl_seconds`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.twilio_adapter/config.py`
- **Lines:** 56
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'TwilioAdapterConfig.dedupe_cache_ttl_seconds' to functionality or delete if unnecessary
```

#### [DC-W059] `CalendarAdapterConfig.calendar_adapter_enabled`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.calendar_adapter/config.py`
- **Lines:** 42
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CalendarAdapterConfig.calendar_adapter_enabled' to functionality or delete if unnecessary
```

#### [DC-W060] `CalendarAdapterConfig.calendar_adapter_log_level`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.calendar_adapter/config.py`
- **Lines:** 43
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CalendarAdapterConfig.calendar_adapter_log_level' to functionality or delete if unnecessary
```

#### [DC-W061] `CalendarAdapterConfig.calendar_sync_interval_minutes`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.calendar_adapter/config.py`
- **Lines:** 44
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CalendarAdapterConfig.calendar_sync_interval_minutes' to functionality or delete if unnecessary
```

#### [DC-W062] `CalendarAdapterConfig.default_timeout_seconds`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.calendar_adapter/config.py`
- **Lines:** 52
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CalendarAdapterConfig.default_timeout_seconds' to functionality or delete if unnecessary
```

#### [DC-W063] `CalendarAdapterConfig.aios_timeout_seconds`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.calendar_adapter/config.py`
- **Lines:** 53
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CalendarAdapterConfig.aios_timeout_seconds' to functionality or delete if unnecessary
```

#### [DC-W064] `CalendarAdapterConfig.dedupe_cache_ttl_seconds`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.calendar_adapter/config.py`
- **Lines:** 56
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CalendarAdapterConfig.dedupe_cache_ttl_seconds' to functionality or delete if unnecessary
```

#### [DC-W065] `EmailAdapterConfig.email_adapter_enabled`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.email_adapter/config.py`
- **Lines:** 42
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EmailAdapterConfig.email_adapter_enabled' to functionality or delete if unnecessary
```

#### [DC-W066] `EmailAdapterConfig.email_adapter_log_level`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.email_adapter/config.py`
- **Lines:** 43
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EmailAdapterConfig.email_adapter_log_level' to functionality or delete if unnecessary
```

#### [DC-W067] `EmailAdapterConfig.default_timeout_seconds`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.email_adapter/config.py`
- **Lines:** 51
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EmailAdapterConfig.default_timeout_seconds' to functionality or delete if unnecessary
```

#### [DC-W068] `EmailAdapterConfig.aios_timeout_seconds`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.email_adapter/config.py`
- **Lines:** 52
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EmailAdapterConfig.aios_timeout_seconds' to functionality or delete if unnecessary
```

#### [DC-W069] `EmailAdapterConfig.dedupe_cache_ttl_seconds`

- **File:** `codegen/code-gen-files/Module Production/Module-Pipeline-Complete/module.email_adapter/config.py`
- **Lines:** 55
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EmailAdapterConfig.dedupe_cache_ttl_seconds' to functionality or delete if unnecessary
```

#### [DC-W070] `ProcessedEmbedding.original_dim`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/embedding_processor.py`
- **Lines:** 37
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ProcessedEmbedding.original_dim' to functionality or delete if unnecessary
```

#### [DC-W071] `ProcessedEmbedding.processed_dim`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/embedding_processor.py`
- **Lines:** 38
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ProcessedEmbedding.processed_dim' to functionality or delete if unnecessary
```

#### [DC-W072] `ProcessedEmbedding.normalized`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/embedding_processor.py`
- **Lines:** 40
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ProcessedEmbedding.normalized' to functionality or delete if unnecessary
```

#### [DC-W073] `Rule.rule_type`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/compliance_checker.py`
- **Lines:** 38
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Rule.rule_type' to functionality or delete if unnecessary
```

#### [DC-W074] `ComplianceResult.compliant`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/compliance_checker.py`
- **Lines:** 46
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ComplianceResult.compliant' to functionality or delete if unnecessary
```

#### [DC-W075] `ComplianceResult.rules_checked`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/compliance_checker.py`
- **Lines:** 47
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ComplianceResult.rules_checked' to functionality or delete if unnecessary
```

#### [DC-W076] `Analogy.source_domain`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/analogical_reasoner.py`
- **Lines:** 37
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Analogy.source_domain' to functionality or delete if unnecessary
```

#### [DC-W077] `Analogy.target_domain`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/analogical_reasoner.py`
- **Lines:** 38
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Analogy.target_domain' to functionality or delete if unnecessary
```

#### [DC-W078] `Analogy.mapping`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/analogical_reasoner.py`
- **Lines:** 41
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Analogy.mapping' to functionality or delete if unnecessary
```

#### [DC-W079] `ReasoningResult.modes_applied`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/reasoning_engine.py`
- **Lines:** 43
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ReasoningResult.modes_applied' to functionality or delete if unnecessary
```

#### [DC-W080] `CausalFactor.factor_id`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/world_model_bridge.py`
- **Lines:** 38
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CausalFactor.factor_id' to functionality or delete if unnecessary
```

#### [DC-W081] `CausalFactor.factor_type`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/world_model_bridge.py`
- **Lines:** 39
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CausalFactor.factor_type' to functionality or delete if unnecessary
```

#### [DC-W082] `CausalFactor.direction`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/world_model_bridge.py`
- **Lines:** 41
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CausalFactor.direction' to functionality or delete if unnecessary
```

#### [DC-W083] `Pattern.pattern_type`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/world_model_bridge.py`
- **Lines:** 48
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Pattern.pattern_type' to functionality or delete if unnecessary
```

#### [DC-W084] `Pattern.window_days`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/world_model_bridge.py`
- **Lines:** 50
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Pattern.window_days' to functionality or delete if unnecessary
```

#### [DC-W085] `AnomalyResponse.handled`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/anomaly_handler.py`
- **Lines:** 57
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AnomalyResponse.handled' to functionality or delete if unnecessary
```

#### [DC-W086] `AnomalyResponse.action_taken`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/anomaly_handler.py`
- **Lines:** 58
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AnomalyResponse.action_taken' to functionality or delete if unnecessary
```

#### [DC-W087] `AnomalyResponse.escalated`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/anomaly_handler.py`
- **Lines:** 59
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AnomalyResponse.escalated' to functionality or delete if unnecessary
```

#### [DC-W088] `AuditResult.audit_passed`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/reflective_auditor.py`
- **Lines:** 37
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AuditResult.audit_passed' to functionality or delete if unnecessary
```

#### [DC-W089] `AuditResult.issues_found`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/reflective_auditor.py`
- **Lines:** 38
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AuditResult.issues_found' to functionality or delete if unnecessary
```

#### [DC-W090] `AuditResult.suggestions`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/reflective_auditor.py`
- **Lines:** 40
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AuditResult.suggestions' to functionality or delete if unnecessary
```

#### [DC-W091] `Decision.reasoning_summary`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/decision_synthesizer.py`
- **Lines:** 41
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Decision.reasoning_summary' to functionality or delete if unnecessary
```

#### [DC-W092] `Decision.contributing_modes`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/decision_synthesizer.py`
- **Lines:** 42
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Decision.contributing_modes' to functionality or delete if unnecessary
```

#### [DC-W093] `Decision.conflicts_resolved`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/decision_synthesizer.py`
- **Lines:** 43
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Decision.conflicts_resolved' to functionality or delete if unnecessary
```

#### [DC-W094] `RoutingResult.handler_name`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/packet_router.py`
- **Lines:** 41
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RoutingResult.handler_name' to functionality or delete if unnecessary
```

#### [DC-W095] `RoutingResult.route_confidence`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/packet_router.py`
- **Lines:** 43
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RoutingResult.route_confidence' to functionality or delete if unnecessary
```

#### [DC-W096] `RoutingResult.fallback_used`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/packet_router.py`
- **Lines:** 44
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RoutingResult.fallback_used' to functionality or delete if unnecessary
```

#### [DC-W097] `CausalResult.causal_chain`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/causal_reasoner.py`
- **Lines:** 37
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CausalResult.causal_chain' to functionality or delete if unnecessary
```

#### [DC-W098] `CausalResult.intervention_points`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/causal_reasoner.py`
- **Lines:** 38
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CausalResult.intervention_points' to functionality or delete if unnecessary
```

#### [DC-W099] `CausalResult.causal_confidence`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/causal_reasoner.py`
- **Lines:** 39
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CausalResult.causal_confidence' to functionality or delete if unnecessary
```

#### [DC-W100] `RuleResult.rules_applied`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/symbolic_reasoner.py`
- **Lines:** 37
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RuleResult.rules_applied' to functionality or delete if unnecessary
```

#### [DC-W101] `RuleResult.rule_confidence`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/symbolic_reasoner.py`
- **Lines:** 38
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RuleResult.rule_confidence' to functionality or delete if unnecessary
```

#### [DC-W102] `DomainContext.entity_data`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/domain_context_builder.py`
- **Lines:** 40
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DomainContext.entity_data' to functionality or delete if unnecessary
```

#### [DC-W103] `DomainContext.domain_rules`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/domain_context_builder.py`
- **Lines:** 41
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DomainContext.domain_rules' to functionality or delete if unnecessary
```

#### [DC-W104] `EscalationResult.escalated`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/escalation_handler.py`
- **Lines:** 55
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EscalationResult.escalated' to functionality or delete if unnecessary
```

#### [DC-W105] `EscalationResult.anchor`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/escalation_handler.py`
- **Lines:** 56
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EscalationResult.anchor' to functionality or delete if unnecessary
```

#### [DC-W106] `GovernanceResult.escalation_level`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/governance_bridge.py`
- **Lines:** 56
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'GovernanceResult.escalation_level' to functionality or delete if unnecessary
```

#### [DC-W107] `GovernanceResult.audit_id`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/governance_bridge.py`
- **Lines:** 57
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'GovernanceResult.audit_id' to functionality or delete if unnecessary
```

#### [DC-W108] `EscalationResult.escalated`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/governance_bridge.py`
- **Lines:** 65
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EscalationResult.escalated' to functionality or delete if unnecessary
```

#### [DC-W109] `EscalationResult.anchor`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/governance_bridge.py`
- **Lines:** 66
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EscalationResult.anchor' to functionality or delete if unnecessary
```

#### [DC-W110] `EnrichedContext.original_payload`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/context_enricher.py`
- **Lines:** 41
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EnrichedContext.original_payload' to functionality or delete if unnecessary
```

#### [DC-W111] `EnrichedContext.world_model_data`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/context_enricher.py`
- **Lines:** 42
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EnrichedContext.world_model_data' to functionality or delete if unnecessary
```

#### [DC-W112] `EnrichedContext.semantic_entities`

- **File:** `codegen/extractions/domain_tensor_bridge_v6_20260102/domain_tensor_bridge/context_enricher.py`
- **Lines:** 44
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EnrichedContext.semantic_entities' to functionality or delete if unnecessary
```

#### [DC-W113] `ServiceProbe.expected_response`

- **File:** `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_infrastructure_health.py`
- **Lines:** 66
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ServiceProbe.expected_response' to functionality or delete if unnecessary
```

#### [DC-W114] `ConfigValidationError.actual_type`

- **File:** `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_infrastructure_health.py`
- **Lines:** 92
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ConfigValidationError.actual_type' to functionality or delete if unnecessary
```

#### [DC-W115] `HealthReport.performance_baseline`

- **File:** `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_infrastructure_health.py`
- **Lines:** 106
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'HealthReport.performance_baseline' to functionality or delete if unnecessary
```

#### [DC-W116] `FunctionDef.has_params`

- **File:** `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py`
- **Lines:** 94
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'FunctionDef.has_params' to functionality or delete if unnecessary
```

#### [DC-W117] `FunctionDef.is_private`

- **File:** `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py`
- **Lines:** 96
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'FunctionDef.is_private' to functionality or delete if unnecessary
```

#### [DC-W118] `ClassDef.base_classes`

- **File:** `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py`
- **Lines:** 104
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ClassDef.base_classes' to functionality or delete if unnecessary
```

#### [DC-W119] `CallGraphEdge.callee`

- **File:** `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py`
- **Lines:** 113
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CallGraphEdge.callee' to functionality or delete if unnecessary
```

#### [DC-W120] `CallGraphEdge.caller_file`

- **File:** `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py`
- **Lines:** 114
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CallGraphEdge.caller_file' to functionality or delete if unnecessary
```

#### [DC-W121] `IntegrityIssue.issue_type`

- **File:** `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py`
- **Lines:** 120
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'IntegrityIssue.issue_type' to functionality or delete if unnecessary
```

#### [DC-W122] `IntegrityIssue.suggestion`

- **File:** `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py`
- **Lines:** 126
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'IntegrityIssue.suggestion' to functionality or delete if unnecessary
```

#### [DC-W123] `IntegrityReport.duplicate_classes`

- **File:** `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py`
- **Lines:** 135
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'IntegrityReport.duplicate_classes' to functionality or delete if unnecessary
```

#### [DC-W124] `IntegrityReport.dead_code_patterns`

- **File:** `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py`
- **Lines:** 136
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'IntegrityReport.dead_code_patterns' to functionality or delete if unnecessary
```

#### [DC-W125] `IntegrityReport.call_graph`

- **File:** `scripts/audit/L9_AUDIT_SUITE_EXPANSION/audit_code_integrity.py`
- **Lines:** 137
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'IntegrityReport.call_graph' to functionality or delete if unnecessary
```

#### [DC-W126] `CalendarAdapterConfig.calendar_adapter_enabled`

- **File:** `api/adapters/calendar_adapter/config.py`
- **Lines:** 46
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CalendarAdapterConfig.calendar_adapter_enabled' to functionality or delete if unnecessary
```

#### [DC-W127] `CalendarAdapterConfig.calendar_adapter_log_level`

- **File:** `api/adapters/calendar_adapter/config.py`
- **Lines:** 49
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CalendarAdapterConfig.calendar_adapter_log_level' to functionality or delete if unnecessary
```

#### [DC-W128] `CalendarAdapterConfig.calendar_sync_interval_minutes`

- **File:** `api/adapters/calendar_adapter/config.py`
- **Lines:** 52
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CalendarAdapterConfig.calendar_sync_interval_minutes' to functionality or delete if unnecessary
```

#### [DC-W129] `CalendarAdapterConfig.default_timeout_seconds`

- **File:** `api/adapters/calendar_adapter/config.py`
- **Lines:** 62
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CalendarAdapterConfig.default_timeout_seconds' to functionality or delete if unnecessary
```

#### [DC-W130] `CalendarAdapterConfig.aios_timeout_seconds`

- **File:** `api/adapters/calendar_adapter/config.py`
- **Lines:** 63
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CalendarAdapterConfig.aios_timeout_seconds' to functionality or delete if unnecessary
```

#### [DC-W131] `CalendarAdapterConfig.dedupe_cache_ttl_seconds`

- **File:** `api/adapters/calendar_adapter/config.py`
- **Lines:** 66
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CalendarAdapterConfig.dedupe_cache_ttl_seconds' to functionality or delete if unnecessary
```

#### [DC-W132] `EmailAdapterConfig.email_adapter_log_level`

- **File:** `api/adapters/email_adapter/config.py`
- **Lines:** 49
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EmailAdapterConfig.email_adapter_log_level' to functionality or delete if unnecessary
```

#### [DC-W133] `EmailAdapterConfig.default_timeout_seconds`

- **File:** `api/adapters/email_adapter/config.py`
- **Lines:** 59
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EmailAdapterConfig.default_timeout_seconds' to functionality or delete if unnecessary
```

#### [DC-W134] `EmailAdapterConfig.aios_timeout_seconds`

- **File:** `api/adapters/email_adapter/config.py`
- **Lines:** 60
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EmailAdapterConfig.aios_timeout_seconds' to functionality or delete if unnecessary
```

#### [DC-W135] `EmailAdapterConfig.dedupe_cache_ttl_seconds`

- **File:** `api/adapters/email_adapter/config.py`
- **Lines:** 63
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EmailAdapterConfig.dedupe_cache_ttl_seconds' to functionality or delete if unnecessary
```

#### [DC-W136] `TwilioAdapterConfig.twilio_whatsapp_number`

- **File:** `api/adapters/twilio_adapter/config.py`
- **Lines:** 52
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'TwilioAdapterConfig.twilio_whatsapp_number' to functionality or delete if unnecessary
```

#### [DC-W137] `TwilioAdapterConfig.twilio_adapter_log_level`

- **File:** `api/adapters/twilio_adapter/config.py`
- **Lines:** 55
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'TwilioAdapterConfig.twilio_adapter_log_level' to functionality or delete if unnecessary
```

#### [DC-W138] `TwilioAdapterConfig.default_timeout_seconds`

- **File:** `api/adapters/twilio_adapter/config.py`
- **Lines:** 65
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'TwilioAdapterConfig.default_timeout_seconds' to functionality or delete if unnecessary
```

#### [DC-W139] `TwilioAdapterConfig.aios_timeout_seconds`

- **File:** `api/adapters/twilio_adapter/config.py`
- **Lines:** 66
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'TwilioAdapterConfig.aios_timeout_seconds' to functionality or delete if unnecessary
```

#### [DC-W140] `TwilioAdapterConfig.dedupe_cache_ttl_seconds`

- **File:** `api/adapters/twilio_adapter/config.py`
- **Lines:** 69
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'TwilioAdapterConfig.dedupe_cache_ttl_seconds' to functionality or delete if unnecessary
```

#### [DC-W141] `JaegerConfig.sample_rate`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 53
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'JaegerConfig.sample_rate' to functionality or delete if unnecessary
```

#### [DC-W142] `JaegerConfig.max_tag_length`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 54
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'JaegerConfig.max_tag_length' to functionality or delete if unnecessary
```

#### [DC-W143] `PrometheusConfig.namespace`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 62
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'PrometheusConfig.namespace' to functionality or delete if unnecessary
```

#### [DC-W144] `ObservabilityPhaseConfig.trace_internal_calls`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 73
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ObservabilityPhaseConfig.trace_internal_calls' to functionality or delete if unnecessary
```

#### [DC-W145] `ObservabilityPhaseConfig.trace_cache_ops`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 74
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ObservabilityPhaseConfig.trace_cache_ops' to functionality or delete if unnecessary
```

#### [DC-W146] `ObservabilityPhaseConfig.trace_serialization`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 75
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ObservabilityPhaseConfig.trace_serialization' to functionality or delete if unnecessary
```

#### [DC-W147] `CloudEventsConfig.spec_version`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 87
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CloudEventsConfig.spec_version' to functionality or delete if unnecessary
```

#### [DC-W148] `CloudEventsConfig.source_prefix`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 88
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CloudEventsConfig.source_prefix' to functionality or delete if unnecessary
```

#### [DC-W149] `CloudEventsConfig.default_content_type`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 89
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CloudEventsConfig.default_content_type' to functionality or delete if unnecessary
```

#### [DC-W150] `CloudEventsConfig.max_event_size_bytes`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 90
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CloudEventsConfig.max_event_size_bytes' to functionality or delete if unnecessary
```

#### [DC-W151] `CloudEventsConfig.schema_validation_enabled`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 91
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CloudEventsConfig.schema_validation_enabled' to functionality or delete if unnecessary
```

#### [DC-W152] `BatchIngestionConfig.idempotency_cache_ttl_seconds`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 109
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'BatchIngestionConfig.idempotency_cache_ttl_seconds' to functionality or delete if unnecessary
```

#### [DC-W153] `EventStoreConfig.max_events_per_aggregate`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 117
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EventStoreConfig.max_events_per_aggregate' to functionality or delete if unnecessary
```

#### [DC-W154] `EventStoreConfig.enable_compression`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 118
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EventStoreConfig.enable_compression' to functionality or delete if unnecessary
```

#### [DC-W155] `ScalabilityPhaseConfig.cqrs_enabled`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 127
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ScalabilityPhaseConfig.cqrs_enabled' to functionality or delete if unnecessary
```

#### [DC-W156] `ScalabilityPhaseConfig.streaming_enabled`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 128
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ScalabilityPhaseConfig.streaming_enabled' to functionality or delete if unnecessary
```

#### [DC-W157] `RetentionConfig.default_ttl_days`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 140
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RetentionConfig.default_ttl_days' to functionality or delete if unnecessary
```

#### [DC-W158] `RetentionConfig.pii_ttl_days`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 141
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RetentionConfig.pii_ttl_days' to functionality or delete if unnecessary
```

#### [DC-W159] `RetentionConfig.audit_log_ttl_days`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 142
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RetentionConfig.audit_log_ttl_days' to functionality or delete if unnecessary
```

#### [DC-W160] `RetentionConfig.enable_auto_cleanup`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 143
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RetentionConfig.enable_auto_cleanup' to functionality or delete if unnecessary
```

#### [DC-W161] `RetentionConfig.cleanup_batch_size`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 144
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RetentionConfig.cleanup_batch_size' to functionality or delete if unnecessary
```

#### [DC-W162] `GDPRConfig.enable_anonymization`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 153
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'GDPRConfig.enable_anonymization' to functionality or delete if unnecessary
```

#### [DC-W163] `GDPRConfig.proof_signature_algorithm`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 154
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'GDPRConfig.proof_signature_algorithm' to functionality or delete if unnecessary
```

#### [DC-W164] `GovernancePhaseConfig.retention`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 161
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'GovernancePhaseConfig.retention' to functionality or delete if unnecessary
```

#### [DC-W165] `GovernancePhaseConfig.compliance_logging_enabled`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 163
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'GovernancePhaseConfig.compliance_logging_enabled' to functionality or delete if unnecessary
```

#### [DC-W166] `PacketEnvelopeUpgradeConfig.phase_2_enabled`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 176
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'PacketEnvelopeUpgradeConfig.phase_2_enabled' to functionality or delete if unnecessary
```

#### [DC-W167] `PacketEnvelopeUpgradeConfig.phase_3_enabled`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 179
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'PacketEnvelopeUpgradeConfig.phase_3_enabled' to functionality or delete if unnecessary
```

#### [DC-W168] `PacketEnvelopeUpgradeConfig.phase_4_enabled`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 182
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'PacketEnvelopeUpgradeConfig.phase_4_enabled' to functionality or delete if unnecessary
```

#### [DC-W169] `PacketEnvelopeUpgradeConfig.phase_5_enabled`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 185
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'PacketEnvelopeUpgradeConfig.phase_5_enabled' to functionality or delete if unnecessary
```

#### [DC-W170] `PacketEnvelopeUpgradeConfig.rollback_enabled`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 199
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'PacketEnvelopeUpgradeConfig.rollback_enabled' to functionality or delete if unnecessary
```

#### [DC-W171] `PacketEnvelopeUpgradeConfig.dry_run_mode`

- **File:** `upgrades/packet_envelope/config.py`
- **Lines:** 200
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'PacketEnvelopeUpgradeConfig.dry_run_mode' to functionality or delete if unnecessary
```

#### [DC-W172] `Snapshot.aggregate_version`

- **File:** `upgrades/packet_envelope/scalability.py`
- **Lines:** 424
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Snapshot.aggregate_version' to functionality or delete if unnecessary
```

#### [DC-W173] `UpgradeState.rollback_available`

- **File:** `upgrades/packet_envelope/integration.py`
- **Lines:** 71
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'UpgradeState.rollback_available' to functionality or delete if unnecessary
```

#### [DC-W174] `AlignmentReport.missing_in_postgres`

- **File:** `igor/01-07-2026/L9 Memory Substrate Audit/substrate_alignment.py`
- **Lines:** 16
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AlignmentReport.missing_in_postgres' to functionality or delete if unnecessary
```

#### [DC-W175] `AlignmentReport.missing_in_qdrant`

- **File:** `igor/01-07-2026/L9 Memory Substrate Audit/substrate_alignment.py`
- **Lines:** 17
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AlignmentReport.missing_in_qdrant' to functionality or delete if unnecessary
```

#### [DC-W176] `AlignmentReport.total_packets_postgres`

- **File:** `igor/01-07-2026/L9 Memory Substrate Audit/substrate_alignment.py`
- **Lines:** 19
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AlignmentReport.total_packets_postgres' to functionality or delete if unnecessary
```

#### [DC-W177] `AlignmentReport.total_nodes_neo4j`

- **File:** `igor/01-07-2026/L9 Memory Substrate Audit/substrate_alignment.py`
- **Lines:** 20
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AlignmentReport.total_nodes_neo4j' to functionality or delete if unnecessary
```

#### [DC-W178] `AlignmentReport.total_vectors_qdrant`

- **File:** `igor/01-07-2026/L9 Memory Substrate Audit/substrate_alignment.py`
- **Lines:** 21
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AlignmentReport.total_vectors_qdrant' to functionality or delete if unnecessary
```

#### [DC-W179] `PerplexityResponse.search_results`

- **File:** `igor/audit-tools/services_research_tools_perplexity_client.py`
- **Lines:** 120
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'PerplexityResponse.search_results' to functionality or delete if unnecessary
```

#### [DC-W180] `PerplexityResponse.search_results`

- **File:** `services/research/tools/perplexity_client.py`
- **Lines:** 132
- **Confidence:** 95%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'PerplexityResponse.search_results' to functionality or delete if unnecessary
```

#### [DC-W181] `ReflectionResult.patterns_observed`

- **File:** `core/agents/selfreflection.py`
- **Lines:** 109
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ReflectionResult.patterns_observed' to functionality or delete if unnecessary
```

#### [DC-W182] `ReflectionResult.analysis_duration_ms`

- **File:** `core/agents/selfreflection.py`
- **Lines:** 112
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ReflectionResult.analysis_duration_ms' to functionality or delete if unnecessary
```

#### [DC-W183] `ReflectionResult.analyzed_at`

- **File:** `core/agents/selfreflection.py`
- **Lines:** 113
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ReflectionResult.analyzed_at' to functionality or delete if unnecessary
```

#### [DC-W184] `SecretPattern.redact_pattern`

- **File:** `core/governance/credentials_policy.py`
- **Lines:** 60
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SecretPattern.redact_pattern' to functionality or delete if unnecessary
```

#### [DC-W185] `SecretViolation.match_preview`

- **File:** `core/governance/credentials_policy.py`
- **Lines:** 71
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SecretViolation.match_preview' to functionality or delete if unnecessary
```

#### [DC-W186] `ModuleMetadata.execution_mode`

- **File:** `.dora/dora.block/python-header-template-enterprise.py`
- **Lines:** 194
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ModuleMetadata.execution_mode' to functionality or delete if unnecessary
```

#### [DC-W187] `CellConfig.store_packets`

- **File:** `collaborative_cells/base_cell.py`
- **Lines:** 44
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CellConfig.store_packets' to functionality or delete if unnecessary
```

#### [DC-W188] `AgentMessage.round_number`

- **File:** `collaborative_cells/base_cell.py`
- **Lines:** 57
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AgentMessage.round_number' to functionality or delete if unnecessary
```

#### [DC-W189] `CellRound.round_number`

- **File:** `collaborative_cells/base_cell.py`
- **Lines:** 64
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CellRound.round_number' to functionality or delete if unnecessary
```

#### [DC-W190] `CellResult.rounds`

- **File:** `collaborative_cells/base_cell.py`
- **Lines:** 83
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CellResult.rounds' to functionality or delete if unnecessary
```

#### [DC-W191] `DoraMetrics.errors_detected`

- **File:** `runtime/dora.py`
- **Lines:** 51
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DoraMetrics.errors_detected' to functionality or delete if unnecessary
```

#### [DC-W192] `DoraMetrics.stability_score`

- **File:** `runtime/dora.py`
- **Lines:** 52
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DoraMetrics.stability_score' to functionality or delete if unnecessary
```

#### [DC-W193] `CriterionResult.weighted_score`

- **File:** `simulation/outcome_evaluator.py`
- **Lines:** 101
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CriterionResult.weighted_score' to functionality or delete if unnecessary
```

#### [DC-W194] `EvaluationResult.evaluated_at`

- **File:** `simulation/outcome_evaluator.py`
- **Lines:** 117
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EvaluationResult.evaluated_at' to functionality or delete if unnecessary
```

#### [DC-W195] `SimulationConfig.parallel_actions`

- **File:** `simulation/simulation_engine.py`
- **Lines:** 59
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SimulationConfig.parallel_actions' to functionality or delete if unnecessary
```

#### [DC-W196] `SimulationConfig.collect_metrics`

- **File:** `simulation/simulation_engine.py`
- **Lines:** 60
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SimulationConfig.collect_metrics' to functionality or delete if unnecessary
```

#### [DC-W197] `SimulationMetrics.resource_usage`

- **File:** `simulation/simulation_engine.py`
- **Lines:** 71
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SimulationMetrics.resource_usage' to functionality or delete if unnecessary
```

#### [DC-W198] `SimulationStep.action_id`

- **File:** `simulation/simulation_engine.py`
- **Lines:** 82
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SimulationStep.action_id' to functionality or delete if unnecessary
```

#### [DC-W199] `SimulationStep.dependencies_satisfied`

- **File:** `simulation/simulation_engine.py`
- **Lines:** 90
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SimulationStep.dependencies_satisfied' to functionality or delete if unnecessary
```

#### [DC-W200] `PromptVariation.audience`

- **File:** `agents/research_agent.py`
- **Lines:** 57
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'PromptVariation.audience' to functionality or delete if unnecessary
```

#### [DC-W201] `ResearchResponse.raw_response`

- **File:** `agents/research_agent.py`
- **Lines:** 67
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ResearchResponse.raw_response' to functionality or delete if unnecessary
```

#### [DC-W202] `ResearchResponse.code_snippets`

- **File:** `agents/research_agent.py`
- **Lines:** 69
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ResearchResponse.code_snippets' to functionality or delete if unnecessary
```

#### [DC-W203] `ResearchTask.max_sources`

- **File:** `agents/research_agent.py`
- **Lines:** 108
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ResearchTask.max_sources' to functionality or delete if unnecessary
```

#### [DC-W204] `ResearchTask.stages`

- **File:** `agents/research_agent.py`
- **Lines:** 109
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ResearchTask.stages' to functionality or delete if unnecessary
```

#### [DC-W205] `SpecResult.yaml_content`

- **File:** `agents/research_agent.py`
- **Lines:** 118
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'SpecResult.yaml_content' to functionality or delete if unnecessary
```

#### [DC-W206] `CausalEdge.edge_type`

- **File:** `world_model/causal_graph.py`
- **Lines:** 59
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CausalEdge.edge_type' to functionality or delete if unnecessary
```

#### [DC-W207] `EntityTypeSchema.type_name`

- **File:** `world_model/registry.py`
- **Lines:** 39
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EntityTypeSchema.type_name' to functionality or delete if unnecessary
```

#### [DC-W208] `EntityTypeSchema.parent_type`

- **File:** `world_model/registry.py`
- **Lines:** 42
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EntityTypeSchema.parent_type' to functionality or delete if unnecessary
```

#### [DC-W209] `RelationTypeSchema.type_name`

- **File:** `world_model/registry.py`
- **Lines:** 54
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RelationTypeSchema.type_name' to functionality or delete if unnecessary
```

#### [DC-W210] `RelationTypeSchema.source_types`

- **File:** `world_model/registry.py`
- **Lines:** 56
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RelationTypeSchema.source_types' to functionality or delete if unnecessary
```

#### [DC-W211] `RelationTypeSchema.target_types`

- **File:** `world_model/registry.py`
- **Lines:** 57
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RelationTypeSchema.target_types' to functionality or delete if unnecessary
```

#### [DC-W212] `RelationTypeSchema.cardinality`

- **File:** `world_model/registry.py`
- **Lines:** 59
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RelationTypeSchema.cardinality' to functionality or delete if unnecessary
```

#### [DC-W213] `ExtractedFact.fact_type`

- **File:** `world_model/knowledge_ingestor.py`
- **Lines:** 100
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ExtractedFact.fact_type' to functionality or delete if unnecessary
```

#### [DC-W214] `IngestorConfig.validate_entities`

- **File:** `world_model/knowledge_ingestor.py`
- **Lines:** 181
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'IngestorConfig.validate_entities' to functionality or delete if unnecessary
```

#### [DC-W215] `IngestorConfig.extract_relations`

- **File:** `world_model/knowledge_ingestor.py`
- **Lines:** 182
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'IngestorConfig.extract_relations' to functionality or delete if unnecessary
```

#### [DC-W216] `IngestorConfig.normalize_patterns`

- **File:** `world_model/knowledge_ingestor.py`
- **Lines:** 184
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'IngestorConfig.normalize_patterns' to functionality or delete if unnecessary
```

#### [DC-W217] `IngestorConfig.normalize_heuristics`

- **File:** `world_model/knowledge_ingestor.py`
- **Lines:** 185
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'IngestorConfig.normalize_heuristics' to functionality or delete if unnecessary
```

#### [DC-W218] `Pattern.outcomes`

- **File:** `world_model/reflection_memory.py`
- **Lines:** 115
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Pattern.outcomes' to functionality or delete if unnecessary
```

#### [DC-W219] `Pattern.first_seen`

- **File:** `world_model/reflection_memory.py`
- **Lines:** 117
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Pattern.first_seen' to functionality or delete if unnecessary
```

#### [DC-W220] `Improvement.action_required`

- **File:** `world_model/reflection_memory.py`
- **Lines:** 138
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Improvement.action_required' to functionality or delete if unnecessary
```

#### [DC-W221] `Improvement.expected_impact`

- **File:** `world_model/reflection_memory.py`
- **Lines:** 141
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'Improvement.expected_impact' to functionality or delete if unnecessary
```

#### [DC-W222] `RuntimeConfig.enable_validation`

- **File:** `world_model/runtime.py`
- **Lines:** 95
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RuntimeConfig.enable_validation' to functionality or delete if unnecessary
```

#### [DC-W223] `RuntimeConfig.concurrent_reads`

- **File:** `world_model/runtime.py`
- **Lines:** 99
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RuntimeConfig.concurrent_reads' to functionality or delete if unnecessary
```

#### [DC-W224] `UpdateRecord.old_value`

- **File:** `world_model/runtime.py`
- **Lines:** 206
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'UpdateRecord.old_value' to functionality or delete if unnecessary
```

#### [DC-W225] `UpdateRecord.new_value`

- **File:** `world_model/runtime.py`
- **Lines:** 207
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'UpdateRecord.new_value' to functionality or delete if unnecessary
```

#### [DC-W226] `PromptVariation.audience`

- **File:** `codegen/Perplexity-Search-Pack/autonomous-research-agent.py`
- **Lines:** 29
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'PromptVariation.audience' to functionality or delete if unnecessary
```

#### [DC-W227] `ResearchResponse.raw_response`

- **File:** `codegen/Perplexity-Search-Pack/autonomous-research-agent.py`
- **Lines:** 39
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ResearchResponse.raw_response' to functionality or delete if unnecessary
```

#### [DC-W228] `ResearchResponse.code_snippets`

- **File:** `codegen/Perplexity-Search-Pack/autonomous-research-agent.py`
- **Lines:** 41
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ResearchResponse.code_snippets' to functionality or delete if unnecessary
```

#### [DC-W229] `CacheEntry.modified`

- **File:** `scripts/audit/audit_shared_core.py`
- **Lines:** 33
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CacheEntry.modified' to functionality or delete if unnecessary
```

#### [DC-W230] `CallGraphEdge.caller_file`

- **File:** `scripts/audit/audit_shared_core.py`
- **Lines:** 129
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CallGraphEdge.caller_file' to functionality or delete if unnecessary
```

#### [DC-W231] `CallGraphEdge.callee`

- **File:** `scripts/audit/audit_shared_core.py`
- **Lines:** 130
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CallGraphEdge.callee' to functionality or delete if unnecessary
```

#### [DC-W232] `CallGraphEdge.callee_type`

- **File:** `scripts/audit/audit_shared_core.py`
- **Lines:** 131
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CallGraphEdge.callee_type' to functionality or delete if unnecessary
```

#### [DC-W233] `CategorizedFinding.action_reason`

- **File:** `scripts/audit/categorize_dead_code.py`
- **Lines:** 67
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CategorizedFinding.action_reason' to functionality or delete if unnecessary
```

#### [DC-W234] `DependencyCheck.all_available`

- **File:** `scripts/audit/tier1/audit_infrastructure_health.py`
- **Lines:** 146
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DependencyCheck.all_available' to functionality or delete if unnecessary
```

#### [DC-W235] `DependencyCheck.missing_dependencies`

- **File:** `scripts/audit/tier1/audit_infrastructure_health.py`
- **Lines:** 147
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DependencyCheck.missing_dependencies' to functionality or delete if unnecessary
```

#### [DC-W236] `InfrastructureReport.health_checks`

- **File:** `scripts/audit/tier1/audit_infrastructure_health.py`
- **Lines:** 159
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'InfrastructureReport.health_checks' to functionality or delete if unnecessary
```

#### [DC-W237] `InfrastructureReport.config_validations`

- **File:** `scripts/audit/tier1/audit_infrastructure_health.py`
- **Lines:** 160
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'InfrastructureReport.config_validations' to functionality or delete if unnecessary
```

#### [DC-W238] `InfrastructureReport.dependency_checks`

- **File:** `scripts/audit/tier1/audit_infrastructure_health.py`
- **Lines:** 161
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'InfrastructureReport.dependency_checks' to functionality or delete if unnecessary
```

#### [DC-W239] `InfrastructureReport.startup_sequence`

- **File:** `scripts/audit/tier1/audit_infrastructure_health.py`
- **Lines:** 162
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'InfrastructureReport.startup_sequence' to functionality or delete if unnecessary
```

#### [DC-W240] `AuditResult.file_outputs`

- **File:** `scripts/audit/run_all.py`
- **Lines:** 145
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AuditResult.file_outputs' to functionality or delete if unnecessary
```

#### [DC-W241] `ParameterSchema.enum_values`

- **File:** `scripts/audit/tier1/audit_capability_inventory.py`
- **Lines:** 125
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ParameterSchema.enum_values' to functionality or delete if unnecessary
```

#### [DC-W242] `MCPSchema.output_schema`

- **File:** `scripts/audit/tier1/audit_capability_inventory.py`
- **Lines:** 133
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'MCPSchema.output_schema' to functionality or delete if unnecessary
```

#### [DC-W243] `CapabilityMethod.return_type`

- **File:** `scripts/audit/tier1/audit_capability_inventory.py`
- **Lines:** 146
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CapabilityMethod.return_type' to functionality or delete if unnecessary
```

#### [DC-W244] `CapabilityMethod.is_exposed`

- **File:** `scripts/audit/tier1/audit_capability_inventory.py`
- **Lines:** 147
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CapabilityMethod.is_exposed' to functionality or delete if unnecessary
```

#### [DC-W245] `CapabilityMethod.deprecation_reason`

- **File:** `scripts/audit/tier1/audit_capability_inventory.py`
- **Lines:** 149
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CapabilityMethod.deprecation_reason' to functionality or delete if unnecessary
```

#### [DC-W246] `CapabilityMethod.version_added`

- **File:** `scripts/audit/tier1/audit_capability_inventory.py`
- **Lines:** 150
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CapabilityMethod.version_added' to functionality or delete if unnecessary
```

#### [DC-W247] `CapabilityMethod.version_deprecated`

- **File:** `scripts/audit/tier1/audit_capability_inventory.py`
- **Lines:** 151
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CapabilityMethod.version_deprecated' to functionality or delete if unnecessary
```

#### [DC-W248] `CapabilityMatrix.value_score`

- **File:** `scripts/audit/tier1/audit_capability_inventory.py`
- **Lines:** 160
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CapabilityMatrix.value_score' to functionality or delete if unnecessary
```

#### [DC-W249] `CapabilityReport.exposed_tools`

- **File:** `scripts/audit/tier1/audit_capability_inventory.py`
- **Lines:** 166
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CapabilityReport.exposed_tools' to functionality or delete if unnecessary
```

#### [DC-W250] `CapabilityReport.hidden_capabilities`

- **File:** `scripts/audit/tier1/audit_capability_inventory.py`
- **Lines:** 167
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CapabilityReport.hidden_capabilities' to functionality or delete if unnecessary
```

#### [DC-W251] `CapabilityReport.mcp_schemas`

- **File:** `scripts/audit/tier1/audit_capability_inventory.py`
- **Lines:** 169
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CapabilityReport.mcp_schemas' to functionality or delete if unnecessary
```

#### [DC-W252] `CapabilityReport.missing_acl`

- **File:** `scripts/audit/tier1/audit_capability_inventory.py`
- **Lines:** 170
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CapabilityReport.missing_acl' to functionality or delete if unnecessary
```

#### [DC-W253] `CapabilityReport.deprecated_methods`

- **File:** `scripts/audit/tier1/audit_capability_inventory.py`
- **Lines:** 171
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CapabilityReport.deprecated_methods' to functionality or delete if unnecessary
```

#### [DC-W254] `FileHashEntry.modified`

- **File:** `scripts/audit/tier1/audit_code_integrity.py`
- **Lines:** 91
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'FileHashEntry.modified' to functionality or delete if unnecessary
```

#### [DC-W255] `CallGraphEdge.caller_file`

- **File:** `scripts/audit/tier1/audit_code_integrity.py`
- **Lines:** 97
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CallGraphEdge.caller_file' to functionality or delete if unnecessary
```

#### [DC-W256] `CallGraphEdge.callee`

- **File:** `scripts/audit/tier1/audit_code_integrity.py`
- **Lines:** 98
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CallGraphEdge.callee' to functionality or delete if unnecessary
```

#### [DC-W257] `CallGraphEdge.callee_type`

- **File:** `scripts/audit/tier1/audit_code_integrity.py`
- **Lines:** 99
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CallGraphEdge.callee_type' to functionality or delete if unnecessary
```

#### [DC-W258] `UncalledFunction.skip_reason`

- **File:** `scripts/audit/tier1/audit_code_integrity.py`
- **Lines:** 108
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'UncalledFunction.skip_reason' to functionality or delete if unnecessary
```

#### [DC-W259] `UncalledFunction.is_private`

- **File:** `scripts/audit/tier1/audit_code_integrity.py`
- **Lines:** 109
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'UncalledFunction.is_private' to functionality or delete if unnecessary
```

#### [DC-W260] `OrphanClass.base_classes`

- **File:** `scripts/audit/tier1/audit_code_integrity.py`
- **Lines:** 117
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'OrphanClass.base_classes' to functionality or delete if unnecessary
```

#### [DC-W261] `AuditReport.call_graph_edges`

- **File:** `scripts/audit/tier1/audit_code_integrity.py`
- **Lines:** 136
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AuditReport.call_graph_edges' to functionality or delete if unnecessary
```

#### [DC-W262] `RoutingDecision.decided_at`

- **File:** `orchestration/task_router.py`
- **Lines:** 151
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RoutingDecision.decided_at' to functionality or delete if unnecessary
```

#### [DC-W263] `WorkflowResult.aggregated_output`

- **File:** `orchestration/cell_orchestrator.py`
- **Lines:** 121
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'WorkflowResult.aggregated_output' to functionality or delete if unnecessary
```

#### [DC-W264] `KernelConfig.max_chain_steps`

- **File:** `orchestration/orchestrator_kernel.py`
- **Lines:** 134
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'KernelConfig.max_chain_steps' to functionality or delete if unnecessary
```

#### [DC-W265] `KernelConfig.step_timeout_ms`

- **File:** `orchestration/orchestrator_kernel.py`
- **Lines:** 135
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'KernelConfig.step_timeout_ms' to functionality or delete if unnecessary
```

#### [DC-W266] `KernelConfig.allow_parallel_chains`

- **File:** `orchestration/orchestrator_kernel.py`
- **Lines:** 136
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'KernelConfig.allow_parallel_chains' to functionality or delete if unnecessary
```

#### [DC-W267] `ExecutorConfig.step_timeout_ms`

- **File:** `orchestration/plan_executor.py`
- **Lines:** 155
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ExecutorConfig.step_timeout_ms' to functionality or delete if unnecessary
```

#### [DC-W268] `CloudEvent._received_at`

- **File:** `upgrades/packet_envelope/standardization.py`
- **Lines:** 87
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CloudEvent._received_at' to functionality or delete if unnecessary
```

#### [DC-W269] `CloudEvent._processed_at`

- **File:** `upgrades/packet_envelope/standardization.py`
- **Lines:** 88
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'CloudEvent._processed_at' to functionality or delete if unnecessary
```

#### [DC-W270] `EventSchema.encoding`

- **File:** `upgrades/packet_envelope/standardization.py`
- **Lines:** 328
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EventSchema.encoding' to functionality or delete if unnecessary
```

#### [DC-W271] `EventSchema.deprecated_at`

- **File:** `upgrades/packet_envelope/standardization.py`
- **Lines:** 331
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'EventSchema.deprecated_at' to functionality or delete if unnecessary
```

#### [DC-W272] `ObservabilityConfig.sample_rate`

- **File:** `upgrades/packet_envelope/observability.py`
- **Lines:** 70
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ObservabilityConfig.sample_rate' to functionality or delete if unnecessary
```

#### [DC-W273] `ObservabilityConfig.export_timeout_ms`

- **File:** `upgrades/packet_envelope/observability.py`
- **Lines:** 73
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ObservabilityConfig.export_timeout_ms' to functionality or delete if unnecessary
```

#### [DC-W274] `ObservabilityConfig.prometheus_port`

- **File:** `upgrades/packet_envelope/observability.py`
- **Lines:** 74
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ObservabilityConfig.prometheus_port' to functionality or delete if unnecessary
```

#### [DC-W275] `ObservabilityConfig.trace_internal_calls`

- **File:** `upgrades/packet_envelope/observability.py`
- **Lines:** 77
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ObservabilityConfig.trace_internal_calls' to functionality or delete if unnecessary
```

#### [DC-W276] `ObservabilityConfig.trace_cache_ops`

- **File:** `upgrades/packet_envelope/observability.py`
- **Lines:** 78
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ObservabilityConfig.trace_cache_ops' to functionality or delete if unnecessary
```

#### [DC-W277] `ObservabilityConfig.trace_serialization`

- **File:** `upgrades/packet_envelope/observability.py`
- **Lines:** 79
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ObservabilityConfig.trace_serialization' to functionality or delete if unnecessary
```

#### [DC-W278] `ObservabilityConfig.baggage_fields`

- **File:** `upgrades/packet_envelope/observability.py`
- **Lines:** 82
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ObservabilityConfig.baggage_fields' to functionality or delete if unnecessary
```

#### [DC-W279] `DataRetentionConfig.pii_ttl_days`

- **File:** `upgrades/packet_envelope/governance.py`
- **Lines:** 63
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DataRetentionConfig.pii_ttl_days' to functionality or delete if unnecessary
```

#### [DC-W280] `DataRetentionConfig.audit_log_ttl_days`

- **File:** `upgrades/packet_envelope/governance.py`
- **Lines:** 64
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DataRetentionConfig.audit_log_ttl_days' to functionality or delete if unnecessary
```

#### [DC-W281] `DataRetentionConfig.enable_anonymization`

- **File:** `upgrades/packet_envelope/governance.py`
- **Lines:** 68
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DataRetentionConfig.enable_anonymization' to functionality or delete if unnecessary
```

#### [DC-W282] `DeletionRequest.requested_by`

- **File:** `upgrades/packet_envelope/governance.py`
- **Lines:** 147
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DeletionRequest.requested_by' to functionality or delete if unnecessary
```

#### [DC-W283] `DeletionRequest.requested_at`

- **File:** `upgrades/packet_envelope/governance.py`
- **Lines:** 148
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DeletionRequest.requested_at' to functionality or delete if unnecessary
```

#### [DC-W284] `DeletionProof.deleted_aggregate_id`

- **File:** `upgrades/packet_envelope/governance.py`
- **Lines:** 167
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DeletionProof.deleted_aggregate_id' to functionality or delete if unnecessary
```

#### [DC-W285] `DeletionProof.deletion_timestamp`

- **File:** `upgrades/packet_envelope/governance.py`
- **Lines:** 168
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DeletionProof.deletion_timestamp' to functionality or delete if unnecessary
```

#### [DC-W286] `DeletionProof.data_hash`

- **File:** `upgrades/packet_envelope/governance.py`
- **Lines:** 169
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DeletionProof.data_hash' to functionality or delete if unnecessary
```

#### [DC-W287] `DeletionProof.proof_signature`

- **File:** `upgrades/packet_envelope/governance.py`
- **Lines:** 170
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DeletionProof.proof_signature' to functionality or delete if unnecessary
```

#### [DC-W288] `DeletionProof.cascading_proofs`

- **File:** `upgrades/packet_envelope/governance.py`
- **Lines:** 171
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DeletionProof.cascading_proofs' to functionality or delete if unnecessary
```

#### [DC-W289] `AnonymizationRule.sensitive`

- **File:** `upgrades/packet_envelope/governance.py`
- **Lines:** 331
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'AnonymizationRule.sensitive' to functionality or delete if unnecessary
```

#### [DC-W290] `ComplianceReport.report_type`

- **File:** `upgrades/packet_envelope/governance.py`
- **Lines:** 460
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ComplianceReport.report_type' to functionality or delete if unnecessary
```

#### [DC-W291] `ComplianceReport.period_start`

- **File:** `upgrades/packet_envelope/governance.py`
- **Lines:** 462
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ComplianceReport.period_start' to functionality or delete if unnecessary
```

#### [DC-W292] `ComplianceReport.period_end`

- **File:** `upgrades/packet_envelope/governance.py`
- **Lines:** 463
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'ComplianceReport.period_end' to functionality or delete if unnecessary
```

#### [DC-W293] `DeliberationRound.round_number`

- **File:** `ir_engine/deliberation_cell.py`
- **Lines:** 45
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DeliberationRound.round_number' to functionality or delete if unnecessary
```

#### [DC-W294] `DeliberationRound.producer_output`

- **File:** `ir_engine/deliberation_cell.py`
- **Lines:** 46
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DeliberationRound.producer_output' to functionality or delete if unnecessary
```

#### [DC-W295] `DeliberationRound.critique`

- **File:** `ir_engine/deliberation_cell.py`
- **Lines:** 47
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DeliberationRound.critique' to functionality or delete if unnecessary
```

#### [DC-W296] `DeliberationRound.revisions_made`

- **File:** `ir_engine/deliberation_cell.py`
- **Lines:** 48
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DeliberationRound.revisions_made' to functionality or delete if unnecessary
```

#### [DC-W297] `DeliberationResult.rounds`

- **File:** `ir_engine/deliberation_cell.py`
- **Lines:** 59
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DeliberationResult.rounds' to functionality or delete if unnecessary
```

#### [DC-W298] `RankedCandidate.rank`

- **File:** `ir_engine/simulation_router.py`
- **Lines:** 73
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RankedCandidate.rank' to functionality or delete if unnecessary
```

#### [DC-W299] `RankedCandidate.selection_reason`

- **File:** `ir_engine/simulation_router.py`
- **Lines:** 74
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'RankedCandidate.selection_reason' to functionality or delete if unnecessary
```

#### [DC-W300] `DependencyEdge.source_module`

- **File:** `ir_engine/compile_meta_to_ir.py`
- **Lines:** 55
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'DependencyEdge.source_module' to functionality or delete if unnecessary
```

#### [DC-W301] `TestSpec.test_file`

- **File:** `ir_engine/compile_meta_to_ir.py`
- **Lines:** 92
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'TestSpec.test_file' to functionality or delete if unnecessary
```

#### [DC-W302] `WiringSpec.lifespan_init`

- **File:** `ir_engine/compile_meta_to_ir.py`
- **Lines:** 108
- **Confidence:** 65%
- **Reason:** Config field defined but never used—likely bug or needs wiring
- **Test Needed:** Yes

**Proposed Fix:**
```
Wire 'WiringSpec.lifespan_init' to functionality or delete if unnecessary
```

---

## Execution Checklist

- [ ] Review all HIGH risk items manually
- [ ] Run `ruff check --fix` for AUTO_FIX items
- [ ] Execute DELETE actions
- [ ] Wire up config fields (WIRE_UP)
- [ ] Add noqa comments for intentional dead code
- [ ] Re-run audit to verify 0 new findings
- [ ] Run tests to verify no regressions
