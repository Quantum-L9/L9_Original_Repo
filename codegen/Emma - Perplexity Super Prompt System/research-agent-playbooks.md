# 🎯 RESEARCH AGENT TACTICAL PLAYBOOKS
## L9 Execution Workflows | Perplexity API Integration

**Version:** 1.0.0  
**Companion to:** L9-god-mode-prompt.md  
**Status:** Operational Guide

---

## PLAYBOOK 1: GRAPH DECAY + CONFIDENCE ENGINEERING

### Objective
Generate production-grade graph service with temporal decay, confidence intervals, and provenance tracking.

### Prerequisites
- Emma Schema v6.4 reference
- L9 Memory Substrate access (Neo4j, PostgreSQL)
- Perplexity API key (authenticated)

### Execution Steps

#### Step 1: Research frontier decay models
```
Perplexity Query:
"What are production graph decay models used in:
 - DeepSeek reasoning chains
 - Anthropic constitutional AI graphs
 - Meta's recommendation systems
 
Include: exponential decay, learned half-life, confidence intervals,
Bayesian update patterns, trade-offs (latency vs accuracy)."
```

**Expected Output:**
- 3-5 concrete implementations
- Benchmarks (latency, accuracy, resource cost)
- Failure modes and mitigations

#### Step 2: Map to Emma Schema
```yaml
metadata:
  module_id: "execassistos/emma/graph/decay_confidence"
  version: "1.0.0"
  owner: "Igor"
  dependencies:
    - "services.memory_substrate"
    - "core.orchestrators.neo4j"

contract:
  purpose: "Temporal graph accuracy via decay + confidence"
  responsibilities:
    - "Exponential decay application (hourly)"
    - "Confidence interval updates (Bayesian)"
    - "Provenance audit trails"
    - "Memory substrate DAO integration"
  
  i_o:
    inputs:
      - name: "graph_packet"
        type: "PacketEnvelope[HabitGraph]"
      - name: "decay_config"
        type: "GraphDecayConfig"
    
    outputs:
      - name: "decayed_graph"
        type: "HabitGraph"
      - name: "audit_log"
        type: "list[ProvenanceRecord]"

ai_scopes:
  allowed:
    - "execassistos/emma/graph/decay_*.py"
    - "tests/graph_decay/"
  restricted:
    - "Memory Substrate DAO modifications"
    - "Feature flag changes"
  forbidden:
    - "Orchestrator logic changes"
    - "Governance policy modifications"
```

#### Step 3: Generate Python modules
```
Expected File Structure:
execassistos/emma/graph/
├── __init__.py
├── decay_engine.py          # Core decay logic
├── confidence_model.py       # Bayesian updates
├── provenance_tracker.py    # Audit trails
├── models.py                # Pydantic schemas
├── memory_dao.py            # PostgreSQL/Neo4j DAOs
└── feature_flags.py         # L9 feature gates

tests/graph_decay/
├── test_decay_engine.py
├── test_confidence_model.py
├── test_integration.py
```

#### Step 4: Implement core decay_engine.py
```python
# TEMPLATE STRUCTURE (fill via Perplexity research)
"""Graph Decay Engine - Temporal accuracy for habit graphs."""

import structlog
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import asyncio
from numpy import exp

logger = structlog.get_logger(__name__)

class GraphDecayConfig(BaseModel):
    """Configuration for decay calculations."""
    half_life_hours: float = Field(default=168.0, description="Hours for 50% decay")
    confidence_model: str = Field(default="bayesian")
    min_confidence: float = Field(default=0.05)
    audit_enabled: bool = True

class ProvenanceRecord(BaseModel):
    """Immutable audit trail for graph mutations."""
    timestamp: datetime
    principal: str  # who (agent/user)
    operation: str  # what (decay|update)
    edge_id: str
    old_confidence: float
    new_confidence: float
    source: str  # why (scheduled|manual|learning)

class DecayEngine:
    """Apply temporal decay to graph edges."""
    
    def __init__(self, config: GraphDecayConfig, memory_dao):
        self.config = config
        self.memory = memory_dao
    
    async def decay_edge(
        self, 
        edge: Dict, 
        last_update: datetime
    ) -> Dict:
        """Apply exponential decay formula."""
        hours_elapsed = (datetime.utcnow() - last_update).total_seconds() / 3600
        decay_factor = exp(-0.693 * hours_elapsed / self.config.half_life_hours)
        
        old_confidence = edge.get("confidence", 1.0)
        new_confidence = max(
            old_confidence * decay_factor,
            self.config.min_confidence
        )
        
        provenance = ProvenanceRecord(
            timestamp=datetime.utcnow(),
            principal="decay_engine",
            operation="decay",
            edge_id=edge["id"],
            old_confidence=old_confidence,
            new_confidence=new_confidence,
            source="scheduled"
        )
        
        logger.info(
            "edge_decayed",
            edge_id=edge["id"],
            old_conf=old_confidence,
            new_conf=new_confidence,
            hours_elapsed=hours_elapsed,
        )
        
        # Persist to audit trail
        if self.config.audit_enabled:
            await self.memory.append_provenance(provenance)
        
        return {**edge, "confidence": new_confidence, "last_decay": datetime.utcnow()}
    
    async def decay_graph(self, graph: Dict) -> Dict:
        """Apply decay to all edges in graph."""
        tasks = [
            self.decay_edge(edge, graph.get("last_updated", datetime.utcnow()))
            for edge in graph.get("edges", [])
        ]
        decayed_edges = await asyncio.gather(*tasks)
        
        return {
            **graph,
            "edges": decayed_edges,
            "last_updated": datetime.utcnow()
        }

# Feature flag wrapper
L9_ENABLE_GRAPH_DECAY = True

async def apply_decay_if_enabled(engine: DecayEngine, graph: Dict) -> Dict:
    """Conditional decay application."""
    if not L9_ENABLE_GRAPH_DECAY:
        logger.debug("graph_decay_disabled")
        return graph
    return await engine.decay_graph(graph)
```

#### Step 5: Integration Guide
```yaml
memory_substrate_integration:
  neo4j:
    queries:
      - name: "fetch_habit_edges"
        cypher: |
          MATCH (h:Habit)-[r:FOLLOWS]->(h2:Habit)
          WHERE r.last_decayed < datetime() - duration({PT1H})
          RETURN h, r, h2
      
      - name: "update_edge_confidence"
        cypher: |
          MATCH (h:Habit)-[r:FOLLOWS]->(h2:Habit)
          WHERE r.id = $edge_id
          SET r.confidence = $new_confidence, r.last_updated = datetime()
          RETURN r
  
  postgresql:
    tables:
      - name: "habit_graph_provenance"
        columns:
          - "id SERIAL PRIMARY KEY"
          - "edge_id UUID NOT NULL"
          - "operation VARCHAR(50)"
          - "principal VARCHAR(255)"
          - "old_confidence FLOAT"
          - "new_confidence FLOAT"
          - "timestamp TIMESTAMP DEFAULT now()"
          - "source VARCHAR(100)"

orchestrator_integration:
  memory_router:
    hook: "pre_habit_query"
    action: "apply_decay_if_enabled(graph)"
  
  evidence_router:
    hook: "post_evidence_update"
    action: "trigger_confidence_update(evidence_bundle)"

feature_flags:
  - name: "L9_ENABLE_GRAPH_DECAY"
    default: true
    purpose: "Enable temporal decay on habit graphs"
  
  - name: "L9_ENABLE_CONFIDENCE_UPDATES"
    default: true
    purpose: "Enable Bayesian confidence interval updates"
  
  - name: "L9_AUDIT_PROVENANCE"
    default: true
    purpose: "Log all graph mutations to provenance"

testing_checklist:
  - [ ] "Unit: decay_factor calculation matches exponential formula"
  - [ ] "Unit: confidence floor respected (min_confidence)"
  - [ ] "Integration: PostgreSQL provenance writes"
  - [ ] "Integration: Neo4j query performance <100ms"
  - [ ] "E2E: Full graph decay cycle with audit trail"
  - [ ] "Rollback: Restore graph from provenance audit"
```

---

## PLAYBOOK 2: WORKFLOW SIMILARITY + APPROVAL INHERITANCE

### Objective
Build deterministic approval inheritance engine for task/workflow matching.

### Execution Steps

#### Step 1: Research similarity algorithms
```
Perplexity Query:
"What are production similarity metrics for workflow matching?
 Include:
 - Embedding-based similarity (task descriptions)
 - Structural similarity (DAG isomorphism)
 - Risk signature matching
 - Semantic workflow clustering
 
 Reference: Apache Airflow, Prefect, Temporal, Anthropic agentic systems."
```

#### Step 2: Schema template
```yaml
metadata:
  module_id: "execassistos/emma/engines/workflow_similarity"
  version: "1.0.0"

contract:
  purpose: "Detect workflow similarity; inherit approvals for matched tasks"
  
  responsibilities:
    - "Compute similarity score (0.0-1.0)"
    - "Classify match type (exact|near|partial|none)"
    - "Generate approval_inheritance decision"
    - "Emit audit packets for inherited approvals"
  
  i_o:
    inputs:
      - name: "incoming_task"
        type: "PacketEnvelope"
      - name: "workflow_templates"
        type: "list[WorkflowTemplate]"
      - name: "principal_context"
        type: "PrincipalContext"
    
    outputs:
      - name: "inheritance_decision"
        type: "WorkflowInheritanceDecision"
      - name: "confidence_score"
        type: "float (0.0-1.0)"
      - name: "approval_request"
        type: "ApprovalRequest | None"
```

#### Step 3: Fingerprinting module
```python
"""Workflow fingerprinting for similarity matching."""

from hashlib import sha256
from typing import Dict, List
import json

class WorkflowFingerprint:
    """Deterministic signature for workflow matching."""
    
    @staticmethod
    def compute_hash(workflow: Dict) -> str:
        """Canonical hash of workflow DAG."""
        canonical = json.dumps(workflow, sort_keys=True, separators=(',', ':'))
        return sha256(canonical.encode()).hexdigest()
    
    @staticmethod
    def tool_signature(tools: List[str]) -> str:
        """Signature of tool usage pattern."""
        return sha256(
            json.dumps(sorted(tools), separators=(',', ':')).encode()
        ).hexdigest()
    
    @staticmethod
    def risk_signature(risks: Dict) -> str:
        """Signature of risk factors."""
        risk_tuple = tuple(sorted(risks.items()))
        return sha256(str(risk_tuple).encode()).hexdigest()
```

#### Step 4: Similarity resolver
```python
"""Core similarity matching engine."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

class MatchType(str, Enum):
    EXACT = "exact"
    NEAR = "near"
    PARTIAL = "partial"
    NONE = "none"

@dataclass
class SimilarityResult:
    similarity_score: float
    match_type: MatchType
    diff_summary: str
    risk_delta: float
    approvals_inherited: List[str]

class WorkflowResolver:
    """Resolve similarity and inheritance decisions."""
    
    async def resolve(
        self,
        task: Dict,
        candidates: List[Dict],
        principal: Dict
    ) -> SimilarityResult:
        """Find best matching template and compute inheritance."""
        
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            score = await self._compute_similarity(task, candidate)
            if score > best_score:
                best_score = score
                best_match = candidate
        
        if best_score >= 0.95:
            match_type = MatchType.EXACT
        elif best_score >= 0.80:
            match_type = MatchType.NEAR
        elif best_score >= 0.60:
            match_type = MatchType.PARTIAL
        else:
            match_type = MatchType.NONE
        
        # Compute risk delta
        risk_delta = self._compute_risk_delta(task, best_match)
        
        # Determine inherited approvals
        inherited_approvals = []
        if match_type in [MatchType.EXACT, MatchType.NEAR]:
            if risk_delta <= principal.get("risk_tolerance", 0.1):
                inherited_approvals = best_match.get("approvals", [])
        
        return SimilarityResult(
            similarity_score=best_score,
            match_type=match_type,
            diff_summary=f"Matched to {best_match.get('id')} with {match_type}",
            risk_delta=risk_delta,
            approvals_inherited=inherited_approvals
        )
```

---

## PLAYBOOK 3: CODEGEN AGENT INTEGRATION

### Objective
Wire research outputs directly into L9 CodeGenAgent pipeline.

### Execution Steps

#### Step 1: Prepare Meta Spec (Module-Spec-v2.4)
```yaml
# Place in: codegen/specs/[domain].meta.yaml
metadata:
  module_id: "execassistos/emma/[domain]"
  version: "1.0.0"
  schema_version: "module-spec-v2.4"
  owner: "Igor"
  created_utc: "2025-12-29T12:00:00Z"

description: "Research + production implementation for [domain]"

purpose: |
  Frontier AI pattern implementation derived from DeepSeek/Anthropic/OpenAI research.
  Production-grade code aligned to L9 governance model.

responsibilities:
  - "Async-first implementation with Structlog logging"
  - "Pydantic schema validation (v2)"
  - "Memory substrate integration (DAO pattern)"
  - "Feature flag governance"
  - "Comprehensive test suite (≥90% coverage)"

dependencies:
  - "services.memory_substrate"
  - "core.orchestrators"
  - "governance.approval_engine"

ai_allowed_scopes:
  - "execassistos/emma/[domain]/*.py"
  - "tests/[domain]/"

ai_restricted_scopes:
  - "Memory Substrate DAO modifications"
  - "API contract changes"

ai_forbidden_scopes:
  - "Orchestrator logic changes"
  - "Kernel entry points"
  - "Governance policy modifications"
```

#### Step 2: Trigger CodeGenAgent
```python
# In L9 orchestrator or Jupyter notebook:
from agents.codegenagent import CodeGenAgent

agent = CodeGenAgent(repo_root="/path/to/L9")

# Generate from meta spec
result = await agent.generate_from_meta(
    meta_path="codegen/specs/graph_decay.meta.yaml",
    dry_run=False  # Actually write files
)

print(f"✅ Generated {len(result.files_created)} files")
print(f"Module ID: {result.ir.module_id}")
```

#### Step 3: Validate generated code
```python
# CodeGenAgent runs validation automatically:
# - Schema compliance (Emma v6.4)
# - Type hints (mypy strict)
# - Imports resolution
# - Async patterns
# - Structlog usage
# - Pydantic models

# Manual validation:
from mypy import api
result = api.run(['--strict', 'execassistos/emma/graph/decay_engine.py'])
assert result[1] == 0, "Type checking failed"
```

#### Step 4: Deploy to L9
```bash
# After CodeGenAgent completes:
$ pytest tests/graph_decay/ -v --cov=execassistos.emma.graph
$ ruff check execassistos/emma/graph/
$ python -m mypy --strict execassistos/emma/graph/

# If all pass:
$ git add execassistos/emma/graph/
$ git commit -m "feat: graph decay + confidence engine (codegen v1.0.0)"
$ git push origin feature/graph-decay
```

---

## PLAYBOOK 4: RESEARCH LOOP AUTOMATION

### Setup Perplexity Agent Runner
```python
"""Automated research → code pipeline."""

import asyncio
import os
from research_agent import PerplexityResearchAgent

async def main():
    agent = PerplexityResearchAgent(
        api_key=os.getenv("PERPLEXITY_API_KEY"),
        god_mode_prompt="L9-god-mode-prompt.md",
        l9_repo="/path/to/L9",
    )
    
    # Research → Schema → Code → Deploy
    result = await agent.execute_workflow(
        domain="graph_decay_confidence",
        frontier_focus=["DeepSeek", "Anthropic", "Meta"],
        output_format="codegen",
        approval_required=True,
    )
    
    if result.success:
        print(f"✅ Generated {result.file_count} production files")
        print(f"📊 Test coverage: {result.test_coverage}%")
        print(f"🔐 Governance: {result.governance_status}")
    else:
        print(f"❌ {result.error}")

asyncio.run(main())
```

---

## CHECKLIST: BEFORE DEPLOYMENT

### Code Quality
- [ ] Type hints: 100% coverage (mypy --strict passes)
- [ ] Tests: ≥90% coverage (pytest + coverage)
- [ ] Docstrings: NumPy format (all functions)
- [ ] Logging: Structlog only (no print statements)
- [ ] Async: All I/O awaitable (no blocking calls)

### L9 Compliance
- [ ] Schema: Emma v6.4 valid YAML
- [ ] Feature flags: All experimental code gated
- [ ] Governance: Approval workflows defined
- [ ] Audit: Provenance tracking implemented
- [ ] Memory: DAO pattern for all persistence

### Integration
- [ ] Memory substrate: PostgreSQL/Neo4j working
- [ ] Orchestrators: Hook points defined
- [ ] Agents: Can invoke via PacketEnvelope
- [ ] Rollback: Plan documented

### Security
- [ ] API keys: Never exposed in code
- [ ] SQL injection: Parameterized queries
- [ ] Authorization: PrincipalContext enforced
- [ ] Audit trail: All mutations logged

---

## SUPPORT & ESCALATION

### If Research Stalls
1. Query Perplexity with different angle (see Playbook 1 alternatives)
2. Check L9 repo for similar patterns
3. Consult with Igor (Boss) for governance exceptions
4. Generate stub implementation; mark as [pending_research]

### If Codegen Fails
1. Check Meta Spec validation (vs v2.4 schema)
2. Verify all imports resolve in L9 environment
3. Test CodeGenAgent on simpler spec first
4. File issue in L9 repo with full error traceback

### If Tests Fail
1. Review test output for specific assertion failures
2. Debug async patterns (use pytest-asyncio)
3. Mock external dependencies (memory substrate, orchestrators)
4. Add verbose logging; re-run with DEBUG level

---

**Version:** 1.0.0 | **Status:** Ready | **Owner:** Igor | **Last Updated:** 2025-12-29
