# L9 Agent Checkpoint Operations Runbook

**Version:** 1.0.0
**Last Updated:** 2026-01-14
**Maintainer:** L9 Engineering Team

---

## Overview

This runbook covers operational procedures for the L9 agent checkpoint system, which provides:

- Agent state persistence across restarts
- Checkpoint integrity validation (SHA-256 checksums)
- Retention policy enforcement
- Prometheus observability metrics

---

## 1. Monitoring

### Key Metrics to Watch

| Metric                                             | Description                    | Alert Threshold |
| -------------------------------------------------- | ------------------------------ | --------------- |
| `l9_checkpoint_create_latency_seconds`             | Time to create checkpoint      | p99 > 2s        |
| `l9_checkpoint_restore_latency_seconds`            | Time to restore checkpoint     | p99 > 1s        |
| `l9_checkpoint_corruption_detected_total`          | Corrupted checkpoints detected | Any > 0         |
| `l9_checkpoint_validation_total{status="invalid"}` | Failed validations             | Any > 0         |
| `l9_checkpoint_size_bytes`                         | Checkpoint state size          | p99 > 500KB     |
| `l9_active_checkpoints`                            | Active checkpoints per agent   | > 20 per agent  |

### Prometheus Queries

```promql
# Checkpoint creation rate (5 minute window)
rate(l9_checkpoint_create_total[5m])

# Average checkpoint size by agent
avg(l9_checkpoint_size_bytes) by (agent_id)

# Corruption detection rate
increase(l9_checkpoint_corruption_detected_total[1h])

# Checkpoint latency p99
histogram_quantile(0.99, rate(l9_checkpoint_create_latency_seconds_bucket[5m]))
```

### Grafana Dashboard

Import the checkpoint dashboard from: `grafana/dashboards/l9-checkpoint-ops.json`

---

## 2. Troubleshooting

### Issue: Checkpoint Restore Fails with Integrity Error

**Symptoms:**

- `ValueError: Checkpoint integrity validation failed` in logs
- `l9_checkpoint_corruption_detected_total` counter incremented

**Diagnosis:**

```bash
# Check logs for the specific checkpoint
docker logs l9-api 2>&1 | grep "integrity validation FAILED"

# Query database for checkpoint state
docker exec -it l9-postgres psql -U postgres -d l9_memory -c \
  "SELECT checkpoint_id, agent_id, graph_state->>'_checksum' as checksum
   FROM graph_checkpoints
   WHERE agent_id = 'YOUR_AGENT_ID';"
```

**Resolution:**

1. **If single checkpoint corrupted:** Delete and let agent create new one

   ```sql
   DELETE FROM graph_checkpoints WHERE checkpoint_id = 'CORRUPTED_UUID';
   ```

2. **If multiple checkpoints corrupted:** Check for disk/storage issues, restore from backup

3. **Emergency bypass (not recommended):**
   ```python
   # In Python, restore without validation
   state = await persistence.restore_checkpoint(agent_id, validate_integrity=False)
   ```

### Issue: Checkpoint Creation Taking Too Long

**Symptoms:**

- `l9_checkpoint_create_latency_seconds` p99 > 2s
- Agent shutdown delays

**Diagnosis:**

```bash
# Check checkpoint sizes
docker exec -it l9-postgres psql -U postgres -d l9_memory -c \
  "SELECT agent_id, pg_size_pretty(length(graph_state::text)::bigint) as size
   FROM graph_checkpoints
   ORDER BY length(graph_state::text) DESC LIMIT 10;"
```

**Resolution:**

1. **Large state objects:** Review what's being stored, reduce unnecessary data
2. **Database performance:** Check PostgreSQL connection pool, indexes
3. **Network latency:** Check connection to database server

### Issue: Too Many Checkpoints Accumulating

**Symptoms:**

- `l9_active_checkpoints` gauge increasing
- Disk usage growing

**Diagnosis:**

```sql
-- Count checkpoints per agent
SELECT agent_id, COUNT(*) as checkpoint_count
FROM graph_checkpoints
GROUP BY agent_id
ORDER BY checkpoint_count DESC;
```

**Resolution:**

1. **Manual cleanup:**

   ```python
   # Delete old checkpoints, keep last 5
   await persistence.delete_old_checkpoints(agent_id, keep_last=5)
   ```

2. **Verify retention engine is running:**
   ```bash
   docker logs l9-api 2>&1 | grep "retention_engine"
   ```

---

## 3. Scaling

### Checkpoint Storage Sizing

| Agent Count | Avg Checkpoint Size | Est. Daily Storage | Monthly Storage |
| ----------- | ------------------- | ------------------ | --------------- |
| 10          | 10 KB               | 2.4 MB             | 72 MB           |
| 100         | 10 KB               | 24 MB              | 720 MB          |
| 1000        | 10 KB               | 240 MB             | 7.2 GB          |

### Retention Policy Tuning

Default retention policy:

```python
retention_policy = {
    "keep_last_n": 10,           # Always keep 10 most recent
    "keep_daily_for_days": 30,   # Keep daily for 30 days
    "keep_weekly_for_weeks": 12, # Keep weekly for 12 weeks
    "keep_monthly_for_months": 6 # Keep monthly for 6 months
}
```

To adjust, modify `memory/agent_persistence.py` or set via config.

### High-Availability Considerations

- **Database replication:** Ensure PostgreSQL is replicated for checkpoint durability
- **Connection pooling:** Use `asyncpg` connection pool (default: 10 connections)
- **Backup schedule:** Daily backups of `graph_checkpoints` table recommended

---

## 4. Disaster Recovery

### Backup Procedure

```bash
# Backup checkpoints table
docker exec l9-postgres pg_dump -U postgres -d l9_memory \
  -t graph_checkpoints > checkpoints_backup_$(date +%Y%m%d).sql
```

### Restore Procedure

```bash
# Stop application first
docker-compose stop l9-api

# Restore from backup
docker exec -i l9-postgres psql -U postgres -d l9_memory < checkpoints_backup.sql

# Restart application
docker-compose start l9-api
```

### Emergency Recovery (No Backup Available)

If checkpoints are lost:

1. Agents will start with empty state
2. State will rebuild as agents process tasks
3. Monitor for any initialization errors

---

## 5. Performance Tuning

### Database Indexes

Ensure these indexes exist (created by migration 0014):

```sql
CREATE INDEX IF NOT EXISTS idx_graph_checkpoints_agent_updated
  ON graph_checkpoints (agent_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_graph_checkpoints_reason
  ON graph_checkpoints (reason, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_graph_checkpoints_agent_number
  ON graph_checkpoints (agent_id, checkpoint_number DESC);
```

### Connection Pool Settings

In `memory/substrate_repository.py`:

```python
# Recommended pool settings
pool = await asyncpg.create_pool(
    dsn=database_url,
    min_size=5,
    max_size=20,
    max_queries=50000,
    max_inactive_connection_lifetime=300,
)
```

### Checkpoint Size Optimization

Best practices:

- Store only essential agent state (not full conversation history)
- Use references (IDs) instead of embedding large objects
- Compress large payloads if needed

---

## 6. Security

### Checksum Validation

- All checkpoints include SHA-256 checksums (v1.1+ schema)
- Validation occurs automatically on restore
- Corruption detection logged and metrics emitted

### Encryption (Future)

Encryption at rest is planned for v2.0:

- KMS/Vault integration for key management
- AES-256-GCM encryption of state payload
- Key rotation support

### Access Control

- Database access controlled via PostgreSQL roles
- API access requires valid L9 API key
- Audit trail via PacketEnvelope emission

---

## 7. Common Operations

### Force Checkpoint Creation

```python
from memory.agent_persistence import AgentPersistenceService
from memory.substrate_service import init_service

service = await init_service(database_url)
persistence = service.get_agent_persistence()

# Force checkpoint with custom reason
checkpoint_id = await persistence.create_checkpoint(
    agent_id="l-cto",
    state={"manual_backup": True, "timestamp": datetime.utcnow().isoformat()},
    reason="manual",
)
print(f"Created checkpoint: {checkpoint_id}")
```

### List All Checkpoints for Agent

```python
checkpoints = await persistence.list_checkpoints("l-cto", limit=100)
for cp in checkpoints:
    print(f"{cp.checkpoint_id}: {cp.reason} @ {cp.created_at}")
```

### Validate All Checkpoints

```python
import asyncio

async def validate_all():
    checkpoints = await persistence.list_checkpoints("l-cto", limit=1000)
    for cp in checkpoints:
        valid = await persistence.validate_checkpoint_integrity(cp.checkpoint_id)
        print(f"{cp.checkpoint_id}: {'✅' if valid else '❌'}")

asyncio.run(validate_all())
```

---

## 8. Migration Guide

### From v1.0 (No Checksums) to v1.1 (With Checksums)

1. **Deploy new code** with checksum support
2. **Existing checkpoints** will be treated as v1.0 (no checksum)
3. **New checkpoints** will include checksums
4. **Validation** will pass for v1.0 checkpoints (backward compatible)

### Migration Script (Optional)

To add checksums to existing checkpoints:

```python
# scripts/migrate_checkpoint_checksums.py
async def migrate():
    checkpoints = await persistence.list_checkpoints(agent_id, limit=1000)
    for cp in checkpoints:
        if "_checksum" not in cp.state:
            # Re-save with checksum
            await persistence.create_checkpoint(
                agent_id=cp.agent_id,
                state=cp.state,
                reason=cp.reason,
            )
```

---

## Contact & Escalation

- **Primary:** L9 Engineering Team
- **Slack:** #l9-ops
- **PagerDuty:** L9 On-Call

---

_Last reviewed: 2026-01-14_
