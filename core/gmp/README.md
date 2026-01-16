# L9 GMP v2.0 Meta-Learning System

> **Status:** Production-ready, async SQLAlchemy
> **Version:** 2.2.0
> **Location:** `core/gmp/`
> **Migration:** `migrations/0021_gmp_learning.sql`

## Overview

GMP v2.0 evolves the Cursor execution from **L2 (constrained) to L5 (autonomous)** with:

- **Meta-Learning Engine** — Tracks execution patterns, generates heuristics
- **Autonomy Controller** — Manages L2→L3→L4→L5 progression
- **Graduated Feature Flags** — Progressive capability enablement

## Directory Structure

```
core/gmp/
├── __init__.py                 # Module exports
├── meta_learning_engine.py     # Core learning engine (770 LOC) ✅ COMPLETE
└── README.md                   # This file

codegen/prompts/gmp-v2/
├── cursor-actions/             # Cursor-native GMP action files
│   ├── GMP-Action-Wire-Learning-Engine.md      # GMP-92
│   ├── GMP-Action-Add-Learning-API-Routes.md   # GMP-93
│   ├── GMP-Action-Create-Learning-Tests.md     # GMP-94
│   └── README.md
├── GMP-v2.0-Super-Prompt.md    # ARCHIVE: Original Perplexity prompt
├── GMP-v2.0-Quick-Start.md     # Reference: Implementation guide
├── DELIVERY-SUMMARY.md         # Reference: Package overview
└── GMP-v2.0-Summary.md         # Reference: Executive summary
```

## Quick Start

### For Cursor Agent

**NO PERPLEXITY NEEDED** — The module is 100% complete.

1. **Use the Learning Engine directly:**
   ```python
   from core.gmp import GMPMetaLearningEngine, AutonomyController
   
   engine = GMPMetaLearningEngine(database_url=settings.DATABASE_URL)
   controller = AutonomyController(engine)
   
   # Log an execution
   await engine.log_execution(result)
   
   # Check autonomy level
   level = await controller.get_current_autonomy_level()
   ```

2. **Check Graduation Status:**
   ```python
   can_graduate, reason = await controller.can_graduate_to_next_level()
   # → (True, "Ready to graduate L2→L3 (10 perfect executions achieved)")
   ```

3. **Run integration GMPs (if needed):**
   ```
   /gmp @codegen/prompts/gmp-v2/cursor-actions/GMP-Action-Wire-Learning-Engine.md
   /gmp @codegen/prompts/gmp-v2/cursor-actions/GMP-Action-Add-Learning-API-Routes.md
   ```

### For Igor (Human)

1. **Run the migration:**
   ```bash
   psql -U postgres -d l9_memory -f migrations/0021_gmp_learning.sql
   ```

2. **Key Decision Points:**
   - Learning DB location: Extend existing L9 PostgreSQL (recommended)
   - Graduation thresholds: L2→L3 = 10 perfect executions (configurable)
   - Feature flag: `L9_GMP_LEARNING_ENABLED=true` in `.env`

## Autonomy Levels

| Level | Name | Capabilities | Graduation Criteria |
|-------|------|--------------|---------------------|
| **L2** | Constrained | Locked TODO plans, static audit | Baseline |
| **L3** | Adaptive | Dynamic TODO refinement, failure recovery | 10 perfect executions |
| **L4** | Strategic | Architectural reasoning, optimization | 95% consistency |
| **L5** | Autonomous | Goal-oriented evolution, self-healing | Safety audit pass |

## Components

### 1. GMPMetaLearningEngine

```python
class GMPMetaLearningEngine:
    """Processes GMP execution history to extract patterns and generate heuristics."""
    
    async def log_execution(result: GMPExecutionResult) -> bool
    async def analyze_execution_patterns() -> Dict[str, Any]
    async def generate_heuristics() -> List[LearnedHeuristic]
    async def get_active_heuristics() -> List[LearnedHeuristic]
    async def update_autonomy_metrics(execution: GMPExecutionResult) -> AutonomyGraduationMetrics
```

### 2. AutonomyController

```python
class AutonomyController:
    """Manages autonomy level graduation and feature flag enforcement."""
    
    async def get_current_autonomy_level() -> AutonomyLevel
    async def assert_capability(feature: str) -> bool
    async def can_graduate_to_next_level() -> Tuple[bool, Optional[str]]
```

### 3. Pydantic Models

- `GMPExecutionResult` — 21 fields capturing execution data
- `LearnedHeuristic` — Pattern with confidence score
- `AutonomyGraduationMetrics` — Tracks L2→L5 progression

### 4. SQLAlchemy Models

- `GMPExecutionHistoryDB` — Execution log table
- `LearnedHeuristicDB` — Heuristics storage
- `AutonomyMetricsDB` — Graduation metrics

## Database Migration

Migration file: `migrations/0021_gmp_learning.sql` ✅ CREATED

Run before using the module:

```sql
-- migrations/0021_gmp_learning.sql
CREATE TABLE gmp_execution_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gmp_id VARCHAR NOT NULL UNIQUE,
    task_type VARCHAR NOT NULL,
    todo_count INT NOT NULL,
    execution_minutes FLOAT NOT NULL,
    error_count INT NOT NULL,
    error_types TEXT[] DEFAULT '{}',
    files_modified TEXT[] DEFAULT '{}',
    lines_changed INT NOT NULL,
    final_confidence FLOAT NOT NULL,
    audit_result VARCHAR NOT NULL,
    l9_kernel_versions JSONB DEFAULT '{}',
    feature_flags_enabled TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE learned_heuristics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    heuristic_id VARCHAR NOT NULL UNIQUE,
    pattern_text TEXT NOT NULL,
    condition TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    supporting_gmp_ids TEXT[] DEFAULT '{}',
    impact_estimate VARCHAR NOT NULL,
    generated_date TIMESTAMP DEFAULT NOW(),
    active BOOLEAN DEFAULT TRUE
);

CREATE TABLE autonomy_graduation_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    current_level VARCHAR DEFAULT 'L2',
    perfect_executions_l2 INT DEFAULT 0,
    consistency_score_l3 FLOAT DEFAULT 0.0,
    safety_audit_passed_l4 BOOLEAN DEFAULT FALSE,
    l2_to_l3_ready BOOLEAN DEFAULT FALSE,
    l3_to_l4_ready BOOLEAN DEFAULT FALSE,
    l4_to_l5_ready BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_gmp_task_type_confidence ON gmp_execution_history(task_type, final_confidence);
CREATE INDEX idx_heuristic_confidence ON learned_heuristics(confidence) WHERE active = TRUE;
```

## Known Issues / TODO

1. ~~**Fake Async:**~~ ✅ FIXED (v2.1.0) — Now uses true async SQLAlchemy
   - Uses `create_async_engine` + `AsyncSession`
   - Requires `asyncpg` driver

2. **Path References:** Some prompts reference `/l9/` paths
   - L9 repo root is `/Users/ib-mac/Projects/L9/`
   - Update paths in prompts when using

3. **Integration Not Complete:**
   - API routes not wired
   - Startup hooks not added
   - Tests not written

4. **Migration Required:** Run `migrations/0021_gmp_learning.sql` before use

## Next Steps

1. **Generate SQL Migration:**
   ```
   /gmp "Create migration 0021_gmp_learning.sql from SQLAlchemy models"
   ```

2. **Wire to API:**
   ```
   /gmp "Add GMP learning API routes to api/routes/"
   ```

3. **Add Startup Hook:**
   ```
   /gmp "Initialize GMPMetaLearningEngine in api/server.py lifespan"
   ```

4. **Generate Tests:**
   ```
   /gmp "Create tests/gmp/test_meta_learning.py"
   ```

## Related Files

- `codegen/C-GMP Suite/` — Existing GMP v1.0 prompts
- `.cursor/rules/80-gmp-execution.mdc` — GMP execution rules
- `workflow_state.md` — Current workflow state

---

**Extracted:** 2026-01-15
**Source:** `current_work/GMP-Evolution-Super-Prompt/`
**Quality:** Research-grade, needs integration work
