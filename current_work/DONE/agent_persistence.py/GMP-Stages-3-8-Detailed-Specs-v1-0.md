# GMP STAGE 3-8: DETAILED SPECIFICATIONS v1.0

This file provides detailed specifications for Stages 3-8. Each stage GMP file in `prompts/` should inherit these sections and customize for its specific scope.

---

## STAGE 3: Integration Wiring v1.0

**Purpose**: Wire AgentPersistence to 6 system integration points
**Scope**: Modify 6 files (executor, server, approval_manager, ingestion, agent_instance)
**Produces**: Hooked save/restore operations in all 6 locations

### Phase 0 TODOs (Template)

```
- **ID**: 3.1
- **File**: /core/agents/executor.py
- **Action**: Add method hook to shutdown()
- **Target**: Lines ~150–160 (method body end)
- **Expected**: Call to agent_persistence.create_checkpoint(agent_id, state, "on_agent_shutdown")
- **Imports**: from memory.agent_persistence import AgentPersistence

- **ID**: 3.2
- **File**: /core/agents/agent_instance.py
- **Action**: Add method restore_state()
- **Target**: Lines ~50–70 (post-init)
- **Expected**: Call to agent_persistence.restore_checkpoint(agent_id) and restore state dict
- **Imports**: from memory.agent_persistence import AgentPersistence

- **ID**: 3.3
- **File**: /api/server.py
- **Action**: Add startup phase checkpoint restore
- **Target**: Inside lifespan() context manager, startup section (~line 80–100)
- **Expected**: Loop through agent IDs, restore each via agent_persistence.restore_checkpoint()
- **Imports**: from memory.agent_persistence import AgentPersistence

- **ID**: 3.4
- **File**: /memory/ingestion.py
- **Action**: Add critical decision checkpointing
- **Target**: Lines ~200–220 (in _store_packet method, after critical_decision check)
- **Expected**: If packet_type == "critical_decision", call agent_persistence.create_checkpoint()
- **Imports**: from memory.agent_persistence import AgentPersistence

- **ID**: 3.5
- **File**: /core/governance/approval_manager.py
- **Action**: Add post-approval checkpointing
- **Target**: Lines ~150–170 (in approve() method, after decision created)
- **Expected**: Call agent_persistence.create_checkpoint() with reason="on_critical_decision"
- **Imports**: from memory.agent_persistence import AgentPersistence

- **ID**: 3.6
- **File**: /api/server.py
- **Action**: Add shutdown phase checkpoint save
- **Target**: Inside lifespan() context manager, shutdown section (~line 180–200)
- **Expected**: Loop through agents, call agent_persistence.create_checkpoint() for final state save
- **Imports**: from memory.agent_persistence import AgentPersistence
```

### Success Indicators

- [ ] All 6 integration points inject correctly
- [ ] No import errors after wiring
- [ ] Integration tests pass (all 6 points execute successfully)
- [ ] Checkpoint lifecycle: create → restore → validate works end-to-end

---

## STAGE 4: Retention & Lifecycle v1.0

**Purpose**: Add retention policies, cleanup automation, lifecycle coordination
**Scope**: New files (retention_engine.py, lifecycle_coordinator.py)
**Produces**: Automated cleanup and retention policy management

### Key Features to Implement

1. **Retention Policy Rules**
   ```python
   retention_rules = [
       {"age_hours": 1, "keep_every": "5min"},      # Last hour: 5-min granularity
       {"age_days": 7, "keep_every": "1hour"},      # Last week: 1-hr granularity
       {"age_days": 30, "keep_every": "1day"},      # Last month: 1-day granularity
   ]
   ```

2. **Cleanup Scheduler**
   - Run daily at off-peak time (configurable)
   - Call `agent_persistence.delete_old_checkpoints()` for each agent
   - Log deletions and storage reclaimed

3. **Lifecycle Hooks**
   - `on_agent_activated`: Initialize retention context for new agent
   - `on_agent_deactivated`: Trigger final checkpoint + retention check

### Phase 0 TODOs (Template)

```
- **ID**: 4.1
- **File**: /memory/retention_engine.py
- **Action**: Create new file
- **Target**: RetentionPolicy + RetentionEngine classes
- **Expected**: Parse retention rules, compute keep/delete sets, handle edge cases
- **Imports**: dataclasses, datetime, typing, structlog

- **ID**: 4.2
- **File**: /memory/lifecycle_coordinator.py
- **Action**: Create new file
- **Target**: LifecycleCoordinator class with on_agent_activated, on_agent_deactivated
- **Expected**: Schedule cleanup jobs, emit lifecycle packets
- **Imports**: asyncio, structlog, core.schemas.packetenvelope

- **ID**: 4.3
- **File**: /config/settings.py
- **Action**: Append RetentionSettings config class
- **Target**: Append to existing settings
- **Expected**: retention_rules (list), cleanup_schedule (cron), keep_last_checkpoints (int)
- **Imports**: pydantic_settings
```

### Success Indicators

- [ ] Retention policies configurable (not hardcoded)
- [ ] Cleanup scheduler runs at defined intervals
- [ ] Old checkpoints deleted per retention rules
- [ ] Storage reclaimed (can be measured post-cleanup)

---

## STAGE 5: Integrity & Security v1.0

**Purpose**: Add checksums, schema versioning, encrypted storage
**Scope**: New files (checkpoint_validator.py, schema_versioning.py), updates to agent_persistence.py
**Produces**: Cryptographic validation + schema migration support

### Key Features

1. **Checksum Validation**
   - SHA-256 hash of checkpoint state + metadata
   - Stored alongside checkpoint
   - Validated on restore, error if mismatch

2. **Schema Versioning**
   - Version field in checkpoint metadata (e.g., "2.1.0")
   - Migration functions for v1 → v2, v2 → v2.1
   - Backward-compatible deserialization

3. **Encrypted Storage** (optional, configurable)
   - KMS/Vault integration for encryption keys
   - Encrypt state dict before storage
   - Decrypt on restore

### Phase 0 TODOs (Template)

```
- **ID**: 5.1
- **File**: /memory/checkpoint_validator.py
- **Action**: Create new file
- **Target**: CheckpointValidator class with checksum generation + validation
- **Expected**: generate_checksum(), validate_checksum() methods using SHA-256
- **Imports**: hashlib, json

- **ID**: 5.2
- **File**: /memory/schema_versioning.py
- **Action**: Create new file
- **Target**: SchemaVersions enum + migration functions
- **Expected**: Detect schema version, apply migrations for backward compatibility
- **Imports**: enum, typing, structlog

- **ID**: 5.3
- **File**: /memory/agent_persistence.py
- **Action**: Update create_checkpoint() + restore_checkpoint() methods
- **Target**: Lines ~150–180 (in create_checkpoint), ~250–280 (in restore_checkpoint)
- **Expected**: Add checksum generation in create, validation in restore; handle schema versions
- **Imports**: checkpoint_validator, schema_versioning
```

### Success Indicators

- [ ] Checksum validation works (detects corrupted checkpoints)
- [ ] Schema versioning works (v1 → v2 migration successful)
- [ ] Backward compatibility verified (old checkpoints can be restored)
- [ ] Encryption configurable (can be enabled/disabled via config)

---

## STAGE 6: Observability & Metrics v1.0

**Purpose**: Add Prometheus metrics, audit trails, structured logging
**Scope**: New files (metrics_definitions.py, audit_logger.py), updates to agent_persistence.py
**Produces**: Production-grade observability

### Metrics (8–10 key metrics)

```python
metrics = {
    "checkpoint_create_latency_ms": Histogram(buckets=[...]),
    "checkpoint_restore_latency_ms": Histogram(buckets=[...]),
    "checkpoint_restore_success_rate": Gauge(),
    "checkpoint_size_bytes": Histogram(buckets=[...]),
    "checkpoint_corruption_detected": Counter(),
    "checkpoint_delete_total": Counter(),
    "agent_active_checkpoints": Gauge(),
    "storage_used_bytes": Gauge(),
}
```

### Audit Logging

```python
# Log structure
{
    "timestamp": "2025-01-11T23:00:00Z",
    "agent_id": "l-cto",
    "operation": "checkpoint_created",
    "checkpoint_id": "uuid",
    "state_size_bytes": 1024,
    "reason": "on_agent_shutdown",
    "duration_ms": 45,
    "status": "success"
}
```

### Phase 0 TODOs (Template)

```
- **ID**: 6.1
- **File**: /memory/metrics_definitions.py
- **Action**: Create new file
- **Target**: Prometheus metric definitions (8–10 metrics)
- **Expected**: Histograms, gauges, counters for checkpoint operations
- **Imports**: prometheus_client

- **ID**: 6.2
- **File**: /memory/audit_logger.py
- **Action**: Create new file
- **Target**: AuditLogger class for structured audit trails
- **Expected**: log_checkpoint_created(), log_checkpoint_restored(), etc.
- **Imports**: structlog, memory.substratemodels

- **ID**: 6.3
- **File**: /memory/agent_persistence.py
- **Action**: Integrate metrics + audit logging
- **Target**: Throughout (in every public method)
- **Expected**: Emit metrics, log audit entries for all operations
- **Imports**: metrics_definitions, audit_logger
```

### Success Indicators

- [ ] Metrics exported to Prometheus (can scrape /metrics endpoint)
- [ ] Audit logs stored and queryable
- [ ] Structured logging uses structlog (no print statements)
- [ ] Key observability signals: latency, success rate, corruption rate

---

## STAGE 7: Testing & Validation v1.0

**Purpose**: Comprehensive test coverage (unit, integration, chaos)
**Scope**: Test files (test_agent_persistence.py, test_integration.py, test_chaos.py)
**Produces**: >85% code coverage

### Test Coverage

**Unit Tests** (test_agent_persistence.py):
- create_checkpoint: normal, error handling, DB down
- restore_checkpoint: success, not found, corruption detected
- list_checkpoints: filtering, pagination
- delete_old_checkpoints: retention rules work
- serialize_agent_state: schema versioning
- deserialize_agent_state: backward compatibility
- validate_checkpoint_integrity: checksum validation

**Integration Tests** (test_integration.py):
- All 6 integration points wired correctly
- End-to-end: create → restore → delete lifecycle
- Concurrent checkpoints (race condition handling)
- Server startup/shutdown with checkpoint restore

**Chaos Tests** (test_chaos.py):
- Database connection failure (graceful degradation)
- Corrupted checkpoint (detection + recovery)
- Disk full (error handling)
- Concurrent access patterns (thread safety)

### Phase 0 TODOs (Template)

```
- **ID**: 7.1
- **File**: /tests/test_agent_persistence.py
- **Action**: Create new file
- **Target**: Unit tests for all 7 methods
- **Expected**: ~20 test functions, >85% coverage
- **Imports**: pytest, pytest_asyncio, unittest.mock

- **ID**: 7.2
- **File**: /tests/test_integration_persistence.py
- **Action**: Create new file
- **Target**: Integration tests for all 6 wiring points
- **Expected**: ~15 test functions, end-to-end lifecycle tests
- **Imports**: pytest_asyncio, fixtures

- **ID**: 7.3
- **File**: /tests/test_chaos_persistence.py
- **Action**: Create new file
- **Target**: Chaos/failure scenario tests
- **Expected**: ~10 test functions, edge cases + recovery
- **Imports**: pytest, pytest_asyncio, unittest.mock
```

### Success Indicators

- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] All chaos tests passing
- [ ] Code coverage >85%
- [ ] No flaky tests (run 3 times, all pass)

---

## STAGE 8: Deployment & Runbook v1.0

**Purpose**: Migration guide, ops runbook, final validation
**Scope**: Documentation files (migration_guide.md, ops_runbook.md, pre_prod_checklist.md)
**Produces**: Production-ready deployment artifacts

### Migration Guide

```
1. Backup existing checkpoint data (if any)
2. Apply database migrations: alembic upgrade head
3. Deploy new agent_persistence.py code
4. Warm up cache: python scripts/warm_checkpoint_cache.py
5. Validate: python scripts/validate_checkpoints.py
6. Monitor for 24 hours (no errors in logs/metrics)
7. Rollback procedure if needed
```

### Ops Runbook

Sections:
1. **Monitoring**: Which metrics to watch
2. **Troubleshooting**: Common issues + resolutions
3. **Scaling**: How to handle many agents
4. **Disaster Recovery**: Restore from backup
5. **Performance**: Tuning parameters
6. **Security**: Encryption key rotation

### Pre-Prod Checklist

```
- [ ] All tests passing locally and in CI/CD
- [ ] Metrics configured in monitoring system
- [ ] Alerting rules set (checkpoint failures, corruption detected)
- [ ] Runbook reviewed by ops team
- [ ] Backup procedure tested
- [ ] Rollback procedure documented
- [ ] Load testing completed (concurrent checkpoints)
- [ ] Final audit: no code TODOs, no hardcoded values
```

### Phase 0 TODOs (Template)

```
- **ID**: 8.1
- **File**: /docs/CHECKPOINT-MIGRATION-GUIDE.md
- **Action**: Create new file
- **Target**: Step-by-step migration procedure + rollback
- **Expected**: ~3–5 clear steps, time estimates, success criteria
- **Imports**: None (documentation)

- **ID**: 8.2
- **File**: /docs/CHECKPOINT-OPS-RUNBOOK.md
- **Action**: Create new file
- **Target**: Ops guide for monitoring, troubleshooting, scaling
- **Expected**: 5–6 sections, actionable procedures, runbook links
- **Imports**: None (documentation)

- **ID**: 8.3
- **File**: /scripts/validate_checkpoints.py
- **Action**: Create new file
- **Target**: Pre-production validation script
- **Expected**: Check schema, sample checkpoint create/restore, verify metrics
- **Imports**: agent_persistence, config
```

### Success Indicators

- [ ] Migration guide is clear and tested
- [ ] Ops runbook addresses common scenarios
- [ ] Pre-prod checklist comprehensive
- [ ] All documentation reviewed and approved

---

## UNIVERSAL PATTERNS (All Stages)

### Error Handling Template

```python
async def method(self) -> Result:
    try:
        # Operation
        result = await self.db.query(...)
        self.logger.info("operation_completed", result_id=result.id)
        return result
    except DatabaseConnectionError as e:
        self.logger.error("db_connection_failed", error=str(e))
        # Graceful degradation: return cached value or None
        return self.cache.get() or None
    except Exception as e:
        self.logger.error("unexpected_error", error=str(e), error_type=type(e).__name__)
        raise
```

### Logging Template

```python
self.logger.info(
    "operation_name",
    agent_id=agent_id,
    checkpoint_id=checkpoint_id,
    operation="create",
    state_size=len(state),
    duration_ms=elapsed_ms,
    status="success"
)
```

### Async Best Practice

```python
async def method(self):
    # Never: await inside try without except or context manager
    try:
        result = await self.async_operation()
    except OperationError:
        self.logger.error("operation_failed")
        raise
```

---

## FINAL NOTES

- Each stage GMP file should copy this section relevant to its stage
- All TODOs must be locked in Phase 0 before Phase 1 begins
- No assumptions about L9 repository state (verify everything in Phase 0)
- Report all findings in the 10-section report format
- Final declaration must state "No drift" or stage fails

---

**READY FOR IMPLEMENTATION**: Stages 3–8 detailed specifications complete. Use this file as reference when creating individual stage GMP files.
