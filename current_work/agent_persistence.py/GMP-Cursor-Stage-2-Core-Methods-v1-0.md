# GMP STAGE 2: Core Persistence Methods v1.0

**Inherits from**: GMP-Action-Prompt-Canonical-v1.0.md  
**Stage Purpose**: Implement 7 required checkpoint methods with full serialization and validation  
**Dependencies**: Stage 1 (database schema + models exist)  
**Duration**: ~4 hours  
**Produces**: `memory/agent_persistence.py` with all 7 required methods  

---

## ROLE & AUTHORITY

You are an L9 GMP Stage Executor focused on implementing the AgentPersistence class.

- **Execute**: Phases 0–6 with strict adherence to method signatures
- **Scope**: `memory/agent_persistence.py` (new file), supporting utility modules
- **Quality Bar**: Production code; zero TODOs or placeholders in implementation
- **Report**: 10 sections + final declaration to `reports/GMP-Stage-2-Methods-Report.md`

---

## PURPOSE

Implement production-grade AgentPersistence class with:

1. **create_checkpoint**: Save agent state snapshot with metadata
2. **restore_checkpoint**: Load state from checkpoint by ID or latest
3. **list_checkpoints**: Query checkpoint history with filtering
4. **delete_old_checkpoints**: Retention policy enforcement
5. **serialize_agent_state**: Convert agent object → dict (with schema versioning)
6. **deserialize_agent_state**: Convert dict → agent state (with backward compatibility)
7. **validate_checkpoint_integrity**: Cryptographic checksum validation

All methods must:
- Use async/await
- Emit PacketEnvelope for critical operations
- Handle errors gracefully
- Support distributed deployments
- Include docstrings, type hints, logging

---

## REQUIRED METHOD SIGNATURES

Each method must match this interface (do not modify signatures):

```python
class AgentPersistence:
    async def create_checkpoint(
        self,
        agent_id: str,
        state: Dict[str, Any],
        reason: str,
    ) -> UUID:
        """Save agent state as checkpoint. Returns checkpoint_id."""

    async def restore_checkpoint(
        self,
        agent_id: str,
        checkpoint_id: Optional[UUID] = None,
    ) -> Optional[Dict[str, Any]]:
        """Load agent state from checkpoint. Returns state dict or None."""

    async def list_checkpoints(
        self,
        agent_id: str,
        limit: int = 10,
    ) -> List[Checkpoint]:
        """Get list of checkpoints for an agent."""

    async def delete_old_checkpoints(
        self,
        agent_id: str,
        keep_last: int = 10,
    ) -> int:
        """Delete old checkpoints per retention policy. Returns count deleted."""

    def serialize_agent_state(self, agent: Any) -> Dict[str, Any]:
        """Convert agent object to dict for storage."""

    def deserialize_agent_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Convert dict back to agent state."""

    async def validate_checkpoint_integrity(
        self,
        checkpoint_id: UUID,
    ) -> bool:
        """Verify checkpoint is valid (checksum, schema, etc.)."""
```

---

## PHASE 0 TODO PLAN SHAPE

Example TODOs (you will generate the actual locked list):

```
- **ID**: 2.1
- **File**: /memory/agent_persistence.py
- **Action**: Create new file
- **Target**: AgentPersistence class with 7 methods
- **Expected**: ~500 lines, includes: __init__, all 7 methods with docstrings, logger setup, error handling
- **Imports**: asyncio, uuid, datetime, typing, logging, structlog, sqlalchemy, pydantic

- **ID**: 2.2
- **File**: /memory/models.py
- **Action**: Append new classes
- **Target**: Checkpoint, CheckpointMetadata data models
- **Expected**: 3–4 Pydantic models for checkpoint representation
- **Imports**: pydantic.BaseModel, datetime, uuid, typing

- **ID**: 2.3
- **File**: /memory/agent_persistence.py
- **Action**: Add PacketEnvelope emission
- **Target**: Lines 150–200 (in create_checkpoint method)
- **Expected**: Emit PacketEnvelopeIn(source_id='l9agent.persistence', agent_id=agent_id, kind='CHECKPOINT_CREATED', ...)
- **Imports**: core.schemas.packetenvelope

- **ID**: 2.4
- **File**: /tests/test_agent_persistence.py
- **Action**: Create new test file
- **Target**: Unit tests for all 7 methods
- **Expected**: ~10 test functions, mocked database, parameterized tests
- **Imports**: pytest, pytest_asyncio, unittest.mock
```

---

## IMPLEMENTATION QUALITY REQUIREMENTS

**Serialization Strategy** (Frontier Standard):
- Use JSON-compatible dicts (not pickle)
- Support schema versioning (v1.0, v2.0, etc.)
- Backward-compatible deserialization
- Detect breaking schema changes

**Error Handling**:
- All external calls wrapped in try/except
- Graceful degradation (return defaults, don't crash)
- Structured error logging (agent_id, operation, error_type)
- User-friendly error messages

**Async Best Practices**:
- All I/O operations use async/await
- Database queries async (sqlalchemy async dialect)
- No blocking operations in async functions
- Proper exception propagation

**Logging & Observability**:
- Use structlog (not print)
- Include context: agent_id, checkpoint_id, operation
- Log levels: DEBUG (fine-grained), INFO (operations), WARNING (retries), ERROR (failures)
- Include execution time and result status

**Distributed Deployment**:
- Support concurrent checkpoint saves (idempotency keys)
- Handle clock skew (UTC timestamps)
- Support multiple L9 instances accessing same database

---

## SUCCESS CRITERIA (HUMAN CHECKLIST POST-PHASE-6)

- [ ] All 7 methods implemented with correct signatures
- [ ] All methods async (async def) and properly await'd
- [ ] All methods have docstrings (Args, Returns, Raises)
- [ ] All methods have type hints (-> return type)
- [ ] Error handling: try/except with recovery, no unhandled exceptions
- [ ] Serialization supports schema versioning
- [ ] Deserialization handles backward compatibility
- [ ] CheckpointIntegrity validation uses checksums
- [ ] PacketEnvelope emitted for checkpoint create/restore
- [ ] Unit tests pass (test_agent_persistence.py)
- [ ] Integration tests pass (with real database in Stage 3)
- [ ] No TODOs or "implement later" comments in code
- [ ] Logging uses structlog with context
- [ ] Code follows L9 patterns (similar to other memory modules)

---

## 10-SECTION REPORT STRUCTURE

1. **Stage Purpose & Implementation Goal**
2. **Phase 0 Locked TODO Plan** (all 7 methods + 3 supporting files)
3. **Phase 1 Baseline** (Stage 1 schema + models verified)
4. **Phase 2 Implementation** (code for each method, diffs)
5. **Phase 3 Enforcement** (error handling, logging, validation added)
6. **Phase 4 Validation** (unit test results, method signature validation)
7. **Phase 5 Recursive Verification** (all methods implemented, no scope drift)
8. **Files Modified/Created** (agent_persistence.py, models.py updates, test file)
9. **Risk Assessment** (database connectivity, serialization edge cases)
10. **Ready for Stage 3** (methods tested, ready for integration wiring)

---

## FINAL DECLARATION

```
All phases 0–6 complete. No assumptions. No drift.
Report: reports/GMP-Stage-2-Methods-Report.md
Stage 2 Core Methods complete. AgentPersistence class production-ready.
Ready for Stage 3: Integration Wiring.
```

---

## EXECUTION START: PHASE 0

**BEGIN PHASE 0**

Prerequisites verification:
- [ ] Stage 1 report exists and shows COMPLETE
- [ ] `memory/migrations/` directory created
- [ ] Pydantic models scaffolded in `memory/models.py`
- [ ] Config settings include checkpoint connection string

Tasks:
1. Read Stage 1 report to understand database schema
2. Review Stage 1 migrations to see checkpoint table structure
3. Determine Phase 0 TODO plan (7–10 TODOs covering 7 methods + tests + models)
4. **STOP: AWAIT HUMAN APPROVAL**

After approval, execute Phases 1–6 to complete full implementation.
