# TODO: A/B Testing Framework for Strategy Memory

**Created:** 2026-01-20
**Priority:** LOW (deferred from GMP-103)
**Status:** PENDING
**Estimated Effort:** 8 hours MVP, 20-40 hours production-grade

---

## Summary

Add an A/B testing framework to Strategy Memory that enables comparing different strategies for the same task type. This allows data-driven decisions about which strategies perform better.

**Goal:** Enable running controlled experiments where some tasks use a "control" strategy and others use a "treatment" strategy, then compare outcomes with statistical rigor.

---

## Why Deferred

This was identified during GMP-103 (Strategy Memory Final Gaps) as requiring **significant new infrastructure** beyond the scope of small fixes:

| What GMP-103 Covers | What A/B Testing Needs |
|---------------------|------------------------|
| ~20 lines for pruning | New data models |
| ~20 lines for drift callback | New database schema |
| Test file creation | New service layer |
| Config additions | API endpoints |
| | Statistical analysis |
| | Experiment lifecycle |

---

## Existing Infrastructure to Use

| Component | Location | Purpose |
|-----------|----------|---------|
| **Neo4jStrategyMemoryService** | `memory/neo4j_strategy_memory.py` | Strategy retrieval + feedback loop |
| **StrategyCandidate** | `memory/strategymemory.py` | Data model for strategies |
| **PlanExecutor** | `orchestration/plan_executor.py` | Integrates strategy selection |

---

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EXPERIMENT SERVICE                        │
│        (assignment, lifecycle, metrics aggregation)          │
└──────────────────────────┬──────────────────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    ▼                      ▼                      ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ EXPERIMENT  │     │ ASSIGNMENT  │     │ METRICS     │
│ REGISTRY    │     │ LOGIC       │     │ COLLECTOR   │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ Create/CRUD │     │ Hash-based  │     │ Per-arm     │
│ experiments │     │ determinism │     │ aggregation │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │ Neo4j Schema           │
              │ :Experiment nodes      │
              │ :ASSIGNED_TO relations │
              │ :ExperimentMetrics     │
              └────────────────────────┘
```

---

## Data Models (Proposed)

```python
class Experiment(BaseModel):
    """A/B test experiment definition."""
    id: str
    name: str
    description: str
    control_strategy_id: str      # Existing strategy
    treatment_strategy_id: str    # Strategy to test
    allocation_percent: float     # % of tasks to treatment (0-100)
    status: Literal["draft", "running", "paused", "concluded"]
    started_at: Optional[datetime]
    concluded_at: Optional[datetime]
    min_sample_size: int = 100    # Before concluding
    
class ExperimentAssignment(BaseModel):
    """Record of which arm a task was assigned to."""
    experiment_id: str
    task_id: str
    arm: Literal["control", "treatment"]
    strategy_id: str
    assigned_at: datetime
    
class ExperimentResults(BaseModel):
    """Aggregated experiment results."""
    experiment_id: str
    control_success_rate: float
    treatment_success_rate: float
    control_sample_size: int
    treatment_sample_size: int
    p_value: Optional[float]      # Statistical significance
    confidence_interval: Optional[Tuple[float, float]]
    winner: Optional[Literal["control", "treatment", "inconclusive"]]
```

---

## Implementation Plan

### Phase 1: Data Model & Schema (1.5 hrs)
- [ ] Create `memory/experiment.py` with Pydantic models
- [ ] Create `migrations/0025_experiment_schema.cypher` for Neo4j
- [ ] Add `:Experiment`, `:ExperimentAssignment` nodes

### Phase 2: Experiment Service (2 hrs)
- [ ] Create `memory/experiment_service.py`
- [ ] Implement CRUD operations
- [ ] Implement hash-based assignment logic:
  ```python
  def assign(self, task_id: str, experiment_id: str) -> str:
      hash_val = hash(f"{task_id}:{experiment_id}") % 100
      if hash_val < experiment.allocation_percent:
          return experiment.treatment_strategy_id
      return experiment.control_strategy_id
  ```

### Phase 3: Integration with Retrieval (1 hr)
- [ ] Add `active_experiment_id` parameter to `retrieve_strategies()`
- [ ] Wire assignment into `PlanExecutor._retrieve_best_strategy()`
- [ ] Record assignments to Neo4j

### Phase 4: Metrics Collection (1.5 hrs)
- [ ] Extend `update_strategy_outcome()` to tag experiment arm
- [ ] Add aggregation query for experiment results
- [ ] Implement `get_experiment_results()`

### Phase 5: API Endpoints (1 hr)
- [ ] `POST /experiments` - create experiment
- [ ] `GET /experiments/{id}` - get experiment details
- [ ] `POST /experiments/{id}/start` - start experiment
- [ ] `POST /experiments/{id}/conclude` - end experiment
- [ ] `GET /experiments/{id}/results` - get results

### Phase 6: Basic Tests (1 hr)
- [ ] Test assignment determinism (same task_id → same arm)
- [ ] Test metrics aggregation
- [ ] Test lifecycle transitions

---

## Production-Grade Additions (Future)

| Feature | Effort | Description |
|---------|--------|-------------|
| **Statistical testing** | 4 hrs | p-values, confidence intervals, significance |
| **Power analysis** | 2 hrs | Calculate required sample size |
| **Auto-stop guardrails** | 2 hrs | Stop if treatment significantly worse |
| **Multi-armed bandit** | 4 hrs | Dynamic allocation based on performance |
| **Dashboard** | 8 hrs | Visualization of experiment progress |
| **Audit trail** | 2 hrs | Full history of experiment changes |

---

## Key Decisions to Make

1. **Where to store experiments?** Neo4j (with strategies) vs PostgreSQL (with packets)
2. **How to handle concurrent experiments?** One per task_kind? Multiple allowed?
3. **What metrics to track?** Success rate only? Also latency, cost?
4. **Statistical approach?** Frequentist (p-values) or Bayesian?

---

## Reference Context

This TODO was created during gap analysis of Strategy Memory spec:

| Feature | Status |
|---------|--------|
| pgvector integration | ✅ Fully implemented |
| Graph edit distance | ✅ Design decision (hash-based) |
| Strategy pruning | ⚠️ GMP-103 (small task) |
| Drift detection | ⚠️ GMP-103 (small task) |
| Perturbation tests | ⚠️ GMP-103 (small task) |
| **A/B testing** | 📋 This TODO (deferred) |

---

## Notes

- Optional[Callable] pattern is sufficient for simple drift alerting
- A/B testing requires proper infrastructure because it needs:
  - Consistent assignment (deterministic hashing)
  - Metrics collection across arms
  - Statistical comparison
  - Experiment lifecycle management
- Consider using existing experiment frameworks if available (e.g., GrowthBook, Eppo)
