# STAGE 2: TODO PLAN TEMPLATE
# Hierarchical Memory Consolidation Engine

## PHASE 0 TODO PLAN LOCK

**Stage**: 2 - Hierarchical Memory Consolidation  
**Timestamp**: {YYYY-MM-DD HH:MM:SS UTC}  
**Executor**: Cursor AI Agent  
**Plan Hash**: {SHA-256 of TODO list below}

---

### TODO FORMAT SPECIFICATION

Each TODO must follow this structure:

```

TODO {STAGE}.{ID}
├─ File: {absolute_path_from_repo_root}
├─ Lines: {start_line}-{end_line} OR "NEW FILE"
├─ Action: {Replace|Insert|Delete|Wrap|Move|Create}
├─ Target: {function|class|block|file}
├─ Behavior: {One sentence describing expected outcome}
├─ Imports: {List of new imports} OR "NONE"
└─ Gate: {Feature flag or condition} OR "NONE"

```

---

### LOCKED TODO PLAN (8 items)

#### **TODO 2.1**
- **File**: `memory/consolidation.py`
- **Lines**: 190-209
- **Action**: Replace
- **Target**: `deduplicate_packets()` method stub
- **Behavior**: Implement cosine similarity deduplication with threshold 0.95, merge by keeping highest confidence packet
- **Imports**: `from typing import List, Tuple; import numpy as np`
- **Gate**: NONE

#### **TODO 2.2**
- **File**: `memory/consolidation.py`
- **Lines**: 263-285
- **Action**: Replace
- **Target**: `summarize_packets()` method stub
- **Behavior**: Implement LLM-based summarization calling new HierarchicalSummarizer
- **Imports**: `from memory.consolidation.hierarchical_summarizer import HierarchicalSummarizer`
- **Gate**: `L9_ENABLE_HIERARCHICAL_CONSOLIDATION`

#### **TODO 2.3**
- **File**: `memory/consolidation/hierarchical_summarizer.py`
- **Lines**: NEW FILE
- **Action**: Create
- **Target**: New module
- **Behavior**: Implement HierarchicalSummarizer class with 20min→daily→weekly cascade and neural decay scoring
- **Imports**: `asyncio, datetime, logging, anthropic, dataclasses, from memory.substrate_repository import PacketStore`
- **Gate**: NONE

#### **TODO 2.4**
- **File**: `memory/consolidation/neural_decay_scheduler.py`
- **Lines**: NEW FILE
- **Action**: Create
- **Target**: New module
- **Behavior**: Implement NeuralDecayScheduler with exponential decay formula S(m,t) = I(m) * exp(-λt) * R(m)
- **Imports**: `math, datetime, asyncio, logging, from memory.substrate_repository import PacketStore`
- **Gate**: NONE

#### **TODO 2.5**
- **File**: `memory/consolidation/__init__.py`
- **Lines**: NEW FILE
- **Action**: Create
- **Target**: Package init file
- **Behavior**: Export HierarchicalSummarizer and NeuralDecayScheduler classes
- **Imports**: NONE
- **Gate**: NONE

#### **TODO 2.6**
- **File**: `memory/__init__.py`
- **Lines**: 45-60 (approximate, verify in Phase 0)
- **Action**: Insert
- **Target**: Module exports section
- **Behavior**: Add exports for new consolidation submodule classes
- **Imports**: NONE
- **Gate**: NONE

#### **TODO 2.7**
- **File**: `tests/memory/test_hierarchical_consolidation.py`
- **Lines**: NEW FILE
- **Action**: Create
- **Target**: Test suite
- **Behavior**: Create 12+ test cases covering decay curves, summarization compression, cascade scheduling, error handling
- **Imports**: `pytest, pytest_asyncio, unittest.mock, memory.consolidation.hierarchical_summarizer, memory.consolidation.neural_decay_scheduler`
- **Gate**: NONE

#### **TODO 2.8**
- **File**: `k8s/cronjobs/decay-scheduler.yaml`
- **Lines**: NEW FILE
- **Action**: Create
- **Target**: Kubernetes CronJob manifest
- **Behavior**: Schedule NeuralDecayScheduler to run daily at 2 AM UTC
- **Imports**: NONE
- **Gate**: NONE

---

### TODO VALIDITY CHECKLIST

- [ ] All file paths are absolute from L9 repo root
- [ ] All line ranges reference existing code (verified in Phase 0)
- [ ] All imports are valid and available in L9
- [ ] No TODO speculates about files that don't exist
- [ ] No TODO modifies protected systems (websocket_orchestrator, kernel_loader)
- [ ] All feature flags follow L9_ENABLE_* pattern
- [ ] All new files include comprehensive docstrings
- [ ] All behavior statements are outcome-focused (not implementation details)

---

### PHASE 0 VERIFICATION COMMANDS

Run these before proceeding to Phase 1:

```bash
# Verify base file exists
test -f memory/consolidation.py || echo "ERROR: Base file missing"

# Check TODO stub at line 190
sed -n '190,209p' memory/consolidation.py | grep -q "TODO" || echo "ERROR: TODO 2.1 target not found"

# Check TODO stub at line 263
sed -n '263,285p' memory/consolidation.py | grep -q "TODO" || echo "ERROR: TODO 2.2 target not found"

# Verify dependencies exist
python3 -c "from memory.substrate_repository import PacketStore; print('✅ PacketStore available')"
python3 -c "import anthropic; print('✅ Anthropic SDK available')"

# Verify protected systems are NOT in TODO plan
! grep -q "websocket_orchestrator\|kernel_loader" <<< "$(cat stage-2-todo-template.md)" || echo "ERROR: Protected system in TODO plan"
```


---

### EXPECTED OUTPUTS (Phase 6)

1. **New Files Created**: 5
    - `memory/consolidation/hierarchical_summarizer.py` (~250 lines)
    - `memory/consolidation/neural_decay_scheduler.py` (~180 lines)
    - `memory/consolidation/__init__.py` (~15 lines)
    - `tests/memory/test_hierarchical_consolidation.py` (~350 lines)
    - `k8s/cronjobs/decay-scheduler.yaml` (~45 lines)
2. **Files Modified**: 2
    - `memory/consolidation.py` (2 sections replaced)
    - `memory/__init__.py` (1 export block added)
3. **Test Results**:
    - Total tests: >= 12
    - Coverage: >= 85%
    - All tests passing
4. **Performance Benchmarks**:
    - Decay calculation: < 5ms per 1000 packets
    - Summarization: < 2s per 50-packet batch
    - Memory overhead: < 50MB for 10k packets

---

## STOP RULES

**STOP and request human intervention if:**

1. ❌ Any TODO target (file, line range) does not exist in Phase 0 verification
2. ❌ Any import listed in TODO plan is not available in the environment
3. ❌ Any protected system appears in diff output during Phase 4
4. ❌ Test coverage falls below 80% in Phase 5
5. ❌ Performance benchmarks exceed thresholds by >20%
6. ❌ Governance gate (`governance_gate.py`) raises RLS violation

---

**END OF TODO PLAN TEMPLATE**

