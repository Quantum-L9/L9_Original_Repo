# 📋 EMMA META SPECIFICATION TEMPLATES
## Production-Ready YAML Schemas for L9 Code Generation

**Version:** 1.0.0  
**Based on:** Emma-Schema-v6.4  
**Status:** Ready for CodeGenAgent Pipeline

---

## TEMPLATE 1: Graph Decay + Confidence Provenance

### File Location
```
codegen/specs/graph_decay_confidence_provenance.meta.yaml
```

### Content
```yaml
metadata:
  module_id: "execassistos/emma/graph/decay_confidence_provenance"
  version: "1.0.0"
  schema_version: "module-spec-v2.4"
  owner: "Igor"
  created_utc: "2025-12-29T12:00:00Z"
  description: "Temporal graph accuracy via exponential decay, confidence weighting, and provenance tracking"

description: |
  Production-grade graph service implementing frontier patterns from DeepSeek, Anthropic, and Meta.
  
  Maintains accuracy of probabilistic graphs (habit graphs, continuity graphs, stakeholder preferences)
  by applying temporal decay to edges/nodes and weighting updates with confidence intervals.
  
  Every mutation is immutable-logged for audit and rollback.

purpose: |
  **Primary:** Keep probabilistic graphs accurate over time by decaying stale data
  and reinforcing with fresh evidence.
  
  **Secondary:**
  - Prevent wrong learning (decay unvalidated connections)
  - Increase safety (confidence intervals prevent over-commitment)
  - Enable auditability (full provenance chain)
  - Support rollback (restore from audit trail)

responsibilities:
  - "Apply exponential decay to graph edges hourly (configurable half-life)"
  - "Update confidence intervals via Bayesian inference on new evidence"
  - "Emit provenance records for every mutation (who→what→when→why)"
  - "Persist to Memory Substrate (PostgreSQL audit + Neo4j graph mutations)"
  - "Enforce consistency invariants (confidence ∈ [0.0, 1.0])"
  - "Support graph rollback from audit trail"
  - "Integrate with Orchestrator hooks (pre-query decay application)"

dependencies:
  - "services.memory_substrate"
  - "core.orchestrators"
  - "governance.approval_engine"
  - "structlog"
  - "pydantic >= 2.0"
  - "numpy"

ai_allowed_scopes:
  - "execassistos/emma/graph/decay_confidence_provenance/*.py"
  - "tests/graph_decay_confidence_provenance/"
  - "Documentation for the decay service"

ai_restricted_scopes:
  - "Memory Substrate DAO modifications (only CRUD via interface)"
  - "Feature flag implementation details"
  - "Orchestrator hook signatures (must match contract)"

ai_forbidden_scopes:
  - "Kernel entry points (kernel_loader.py, websocket_orchestrator.py)"
  - "Governance policy modifications (approval thresholds, risk models)"
  - "Agent authority hierarchy changes"
  - "Schema version downgrades"

contract:
  module_purpose: "Temporal decay + confidence for probabilistic graphs"
  
  modules:
    - path: "decay_confidence_provenance/models.py"
      purpose: "Pydantic schemas for decay config, provenance records, graph entities"
      exports:
        - "GraphDecayConfig"
        - "ProvenanceRecord"
        - "ConfidenceInterval"
        - "DecayMetadata"
    
    - path: "decay_confidence_provenance/decay_engine.py"
      purpose: "Core exponential decay implementation with configurable half-life"
      async_functions:
        - "decay_edge(edge, half_life_hours) -> DecayedEdge"
        - "decay_graph(graph, config) -> DecayedGraph"
        - "apply_decay_if_enabled(graph) -> DecayedGraph"
    
    - path: "decay_confidence_provenance/confidence_model.py"
      purpose: "Bayesian confidence interval updates"
      async_functions:
        - "update_confidence(old_conf, evidence, prior_strength) -> ConfidenceInterval"
        - "merge_confidences(intervals) -> ConfidenceInterval"
    
    - path: "decay_confidence_provenance/provenance_tracker.py"
      purpose: "Immutable audit trail for all mutations"
      async_functions:
        - "record_decay_event(edge_id, old_conf, new_conf) -> ProvenanceRecord"
        - "record_update_event(edge_id, evidence, source) -> ProvenanceRecord"
        - "fetch_provenance_chain(edge_id, since=None) -> list[ProvenanceRecord]"
        - "rollback_to_timestamp(graph_id, timestamp) -> Graph"
    
    - path: "decay_confidence_provenance/memory_dao.py"
      purpose: "Data access layer for Memory Substrate (PostgreSQL, Neo4j)"
      async_functions:
        - "store_provenance(record) -> None"
        - "query_provenance(edge_id, filters) -> list[ProvenanceRecord]"
        - "update_graph_edges(graph_id, edges) -> None"
        - "fetch_graph_snapshot(graph_id, timestamp) -> Graph"
    
    - path: "decay_confidence_provenance/interface.py"
      purpose: "Public API exposed to Orchestrators"
      functions:
        - "async def apply_decay(graph, config) -> DecayedGraph"
        - "async def update_confidence(edge_id, evidence) -> ConfidenceInterval"
        - "async def get_provenance_audit(edge_id) -> list[ProvenanceRecord]"

  i_o:
    inputs:
      - name: "graph_packet"
        type: "PacketEnvelope[HabitGraph | ContinuityGraph | PreferenceGraph]"
        description: "Incoming graph for decay application"
        required: true
      
      - name: "decay_config"
        type: "GraphDecayConfig"
        description: "Decay parameters (half-life, confidence model, audit settings)"
        required: false
        default: "GraphDecayConfig(half_life_hours=168.0, model='exponential')"
      
      - name: "evidence"
        type: "EvidenceBundle"
        description: "New evidence for confidence updates"
        required: false
    
    outputs:
      - name: "decayed_graph"
        type: "HabitGraph | ContinuityGraph | PreferenceGraph"
        description: "Graph with all edges decayed + confidence updated"
      
      - name: "provenance_trail"
        type: "list[ProvenanceRecord]"
        description: "Immutable audit log of all mutations"
      
      - name: "metadata"
        type: "DecayMetadata"
        description: "Decay operation metadata (timestamp, count of decayed edges, etc.)"

feature_flags:
  - name: "L9_ENABLE_GRAPH_DECAY"
    description: "Master toggle for temporal decay on all graphs"
    default_value: true
    owned_by: "Igor"
    critical: true
  
  - name: "L9_ENABLE_CONFIDENCE_UPDATES"
    description: "Enable Bayesian confidence interval updates"
    default_value: true
    owned_by: "Igor"
  
  - name: "L9_ENABLE_PROVENANCE_AUDIT"
    description: "Enable immutable audit trail logging (PostgreSQL)"
    default_value: true
    owned_by: "Igor"
    critical: true
  
  - name: "L9_GRAPH_DECAY_STRICT_MODE"
    description: "Enforce strict consistency checks on all decay operations"
    default_value: false
    owned_by: "Igor"

governance:
  approval_required: true
  approval_gate: "high-risk"
  risk_level: "high"
  
  rationale: |
    Graph mutations affect decision-making across all agents.
    Incorrect decay could cause silent data loss. Requires Igor approval
    before production deployment.
  
  audit_requirements:
    - "All provenance records immutable (no deletion)"
    - "All mutations logged to PostgreSQL audit table"
    - "Rollback capability verified in tests"
    - "Confidence consistency invariants enforced"
  
  approval_workflow:
    - step: "code_review"
      reviewer: "Critic"
      gates:
        - "Type checking (mypy --strict)"
        - "Test coverage ≥90%"
        - "Integration tests pass"
    
    - step: "governance_review"
      reviewer: "Igor"
      gates:
        - "Audit trail design approved"
        - "Rollback strategy validated"
        - "Decay model correctness verified"
    
    - step: "staging_deployment"
      reviewer: "Igor"
      gates:
        - "Feature flag disabled by default"
        - "Monitoring & alerting in place"
        - "Rollback tested end-to-end"

testing:
  unit_tests:
    - name: "test_decay_factor_calculation"
      description: "Verify exponential decay formula"
      assertions:
        - "After half_life, confidence = 0.5 * original"
        - "After 2*half_life, confidence = 0.25 * original"
        - "Confidence never goes below min_confidence"
    
    - name: "test_confidence_interval_bayesian_update"
      description: "Verify Bayesian update on new evidence"
      assertions:
        - "High-confidence evidence increases interval"
        - "Low-confidence evidence narrows interval"
        - "Posterior mean = weighted average of prior + evidence"
    
    - name: "test_provenance_immutability"
      description: "Ensure audit trail cannot be modified"
      assertions:
        - "Records stored as immutable (DB constraint)"
        - "Deletion attempts raise PermissionError"
        - "Timestamps cannot be backdated"
  
  integration_tests:
    - name: "test_decay_orchestrator_integration"
      description: "Full flow: graph → decay → memory substrate"
      steps:
        - "Create test habit graph"
        - "Inject via Orchestrator hook"
        - "Verify decay applied"
        - "Query provenance from PostgreSQL"
        - "Assert Neo4j graph updated"
    
    - name: "test_rollback_from_provenance"
      description: "Restore graph state from audit trail"
      steps:
        - "Capture baseline graph"
        - "Apply series of decays"
        - "Query provenance at T-1"
        - "Reconstruct graph state"
        - "Assert matches baseline"

  coverage_target: "90%"
  
  performance_benchmarks:
    - metric: "Single edge decay latency"
      target: "<1ms"
      scenario: "Exponential calculation + audit write"
    
    - metric: "Full graph decay (1000 edges)"
      target: "<100ms"
      scenario: "Parallel decay tasks + batch audit"
    
    - metric: "Provenance query latency"
      target: "<50ms"
      scenario: "PostgreSQL full-text search on 100k records"

examples:
  - name: "Apply exponential decay to habit graph"
    description: "Decay a habit graph with default 1-week half-life"
    language: "python"
    code: |
      from execassistos.emma.graph.decay_confidence_provenance import (
          DecayEngine, GraphDecayConfig
      )
      
      async def decay_habit_graph():
          config = GraphDecayConfig(
              half_life_hours=168.0,  # 1 week
              confidence_model="bayesian",
              min_confidence=0.05,
              audit_enabled=True,
          )
          
          engine = DecayEngine(config, memory_dao)
          
          decayed = await engine.decay_graph(habit_graph)
          
          print(f"Decayed {len(decayed.edges)} edges")
          print(f"Provenance trail: {len(decayed.provenance)} records")
  
  - name: "Query provenance chain for audit"
    language: "python"
    code: |
      async def audit_edge_history():
          edge_id = "habit_morning_exercise_to_meditation"
          
          trail = await engine.get_provenance_chain(edge_id)
          
          for record in trail:
              print(f"{record.timestamp}: {record.operation}")
              print(f"  Principal: {record.principal}")
              print(f"  Confidence: {record.old_confidence} → {record.new_confidence}")
  
  - name: "Rollback graph to previous state"
    language: "python"
    code: |
      async def rollback_graph():
          from datetime import datetime, timedelta
          
          # Go back 24 hours
          target_time = datetime.utcnow() - timedelta(hours=24)
          
          restored = await engine.rollback_to_timestamp(
              graph_id="habit_graph_001",
              timestamp=target_time
          )
          
          print(f"Restored to {target_time}: {len(restored.edges)} edges")

deployment:
  docker:
    base_image: "python:3.12-slim"
    dependencies:
      - "structlog"
      - "pydantic"
      - "asyncpg"  # PostgreSQL async
      - "neo4j"    # Neo4j driver
      - "numpy"
  
  env_variables:
    - "POSTGRES_HOST"
    - "POSTGRES_USER"
    - "POSTGRES_PASSWORD"
    - "NEO4J_URI"
    - "NEO4J_USER"
    - "NEO4J_PASSWORD"
    - "L9_ENABLE_GRAPH_DECAY"
    - "L9_ENABLE_PROVENANCE_AUDIT"
  
  rollback_strategy: |
    1. Disable L9_ENABLE_GRAPH_DECAY feature flag
    2. Verify no new decay operations in progress
    3. If data corruption detected, trigger rollback_to_timestamp() for affected graphs
    4. Re-enable feature flag after verification
    5. Run integration tests to confirm

configuration:
  graph_decay:
    half_life_hours: 168.0
    confidence_model: "bayesian"
    min_confidence: 0.05
    update_frequency_hours: 1
  
  audit:
    enabled: true
    retention_days: 365
    batch_writes: true
    batch_size: 1000
  
  performance:
    parallel_decay_workers: 4
    cache_enabled: true
    cache_ttl_seconds: 300
```

---

## TEMPLATE 2: Workflow Similarity + Approval Inheritance

### File Location
```
codegen/specs/workflow_similarity_approval_inheritance.meta.yaml
```

### Content
```yaml
metadata:
  module_id: "execassistos/emma/engines/workflow_similarity_inheritance"
  version: "1.0.0"
  schema_version: "module-spec-v2.4"
  owner: "Igor"
  created_utc: "2025-12-29T12:00:00Z"
  description: "Deterministic workflow similarity matching with approval inheritance"

description: |
  Reduce friction and cost by reusing previously-approved workflow templates.
  
  Detects similarity between incoming tasks and existing approved workflows,
  inherits approvals/autonomy when match is strong, and only requests permission
  when material differences exist.
  
  Implements frontier patterns from Apache Airflow, Temporal, Anthropic agentic systems.

purpose: |
  **Primary:** Enable cost-effective task execution via approval inheritance.
  
  When a task matches an approved workflow template above a similarity threshold,
  inherit the previous approval instead of re-planning and re-requesting approval.
  
  **Secondary:**
  - Prevent wrong learning (reuse proven playbooks)
  - Improve quality (reuse tested tool sequences)
  - Increase speed (avoid full planning + tool reasoning)
  - Compound autonomy (approvals unlock broader task classes)

responsibilities:
  - "Compute similarity score (0.0-1.0) between task and workflow templates"
  - "Classify match type (exact | near | partial | none)"
  - "Generate approval_inheritance decision with full audit"
  - "Respect tenant/org autonomy ceiling"
  - "Emit approval_inheritance PacketEnvelope before execution"
  - "Support approval_delta workflows (request only for differences)"
  - "Maintain Template Registry (stored in Memory Substrate)"

dependencies:
  - "services.memory_substrate"
  - "core.orchestrators"
  - "governance.approval_engine"
  - "governance.consent_engine"
  - "structlog"
  - "pydantic >= 2.0"

ai_allowed_scopes:
  - "execassistos/emma/engines/workflow_similarity_inheritance/*.py"
  - "tests/workflow_similarity_inheritance/"

ai_restricted_scopes:
  - "Template Registry schema changes"
  - "Similarity threshold tuning (without approval)"
  - "Risk signature definitions"

ai_forbidden_scopes:
  - "Autonomy ceiling policy changes"
  - "Approval workflow bypasses"
  - "Governance model modifications"

contract:
  module_purpose: "Detect workflow similarity; inherit approvals safely"
  
  modules:
    - path: "workflow_similarity_inheritance/interface.py"
      purpose: "Public API for orchestrators"
      async_functions:
        - "async def resolve_similarity(task, candidates, principal) -> WorkflowInheritanceDecision"
        - "async def get_matching_templates(task, threshold=0.80) -> list[WorkflowTemplate]"
        - "async def compute_similarity(task, template) -> SimilarityResult"
    
    - path: "workflow_similarity_inheritance/fingerprinting.py"
      purpose: "Deterministic workflow signatures for matching"
      functions:
        - "def workflow_hash(workflow) -> str"
        - "def tool_signature(tools) -> str"
        - "def risk_signature(risks) -> str"
        - "def semantic_fingerprint(task_desc) -> list[float]"
    
    - path: "workflow_similarity_inheritance/resolver.py"
      purpose: "Core similarity matching logic"
      async_functions:
        - "async def resolve(task, templates, principal) -> WorkflowInheritanceDecision"
        - "async def compute_risk_delta(task, template) -> float"
    
    - path: "workflow_similarity_inheritance/evaluator.py"
      purpose: "Determine if inheritance is safe"
      async_functions:
        - "async def can_inherit(match, principal, risk_delta) -> bool"
        - "async def compute_approval_delta(old_approvals, new_task) -> list[ApprovalRequest]"
    
    - path: "workflow_similarity_inheritance/policy.py"
      purpose: "Policy enforcement for autonomy ceiling"
      functions:
        - "def check_autonomy_ceiling(principal, new_task) -> bool"
        - "def compute_risk_level(task, tools) -> RiskLevel"

  i_o:
    inputs:
      - name: "task_packet"
        type: "PacketEnvelope"
        description: "Incoming user/client directive"
      
      - name: "principal"
        type: "PrincipalContext"
        description: "Tenant/user/org identity + autonomy ceiling"
      
      - name: "candidate_templates"
        type: "list[WorkflowTemplateRecord]"
        description: "Pulled from Template Registry"
    
    outputs:
      - name: "inheritance_decision"
        type: "WorkflowInheritanceDecision"
        description: "Verdict: inherit | ask | reject with audit trail"
      
      - name: "resolved_dag"
        type: "DagTemplateInstance | None"
        description: "If inherited/patched, executable DAG"
      
      - name: "approval_request"
        type: "ApprovalRequest | None"
        description: "If permission needed, structured request with diff/risk"

feature_flags:
  - name: "L9_ENABLE_APPROVAL_INHERITANCE"
    default: true
  
  - name: "L9_ENABLE_SIMILARITY_MATCHING"
    default: true
  
  - name: "L9_STRICT_APPROVAL_INHERITANCE"
    default: false
    description: "Require explicit approval even for near-exact matches"

governance:
  approval_required: true
  risk_level: "critical"
  
  rationale: "Approval inheritance affects autonomy and cost; requires Igor approval"

testing:
  coverage_target: "90%"
  
  performance_benchmarks:
    - metric: "Similarity computation (1 task vs 100 templates)"
      target: "<500ms"
    
    - metric: "Template Registry query latency"
      target: "<50ms"
```

---

## USAGE: Feeding to CodeGenAgent

### Step 1: Place Spec in Correct Location
```bash
cp graph_decay_confidence_provenance.meta.yaml \
   /path/to/L9/codegen/specs/
```

### Step 2: Invoke CodeGenAgent
```python
from agents.codegenagent import CodeGenAgent

agent = CodeGenAgent(repo_root="/path/to/L9")

# Generate all files (code + tests + README)
result = await agent.generate_from_meta(
    meta_path="codegen/specs/graph_decay_confidence_provenance.meta.yaml",
    dry_run=False  # Actually write
)

print(f"✅ Files created: {len(result.files_created)}")
print(f"📦 Module: {result.ir.module_id}")
print(f"✔️ All governance checks passed" if result.success else f"❌ {result.errors}")
```

### Step 3: Validate Output
```bash
# Type checking
mypy --strict execassistos/emma/graph/decay_confidence_provenance/

# Test coverage
pytest tests/graph_decay_confidence_provenance/ --cov

# Linting
ruff check execassistos/emma/graph/decay_confidence_provenance/
```

---

**Ready for CodeGenAgent Pipeline** ✅  
**Frontier AI Lab Grade** ✅  
**L9 Governance Compliant** ✅
