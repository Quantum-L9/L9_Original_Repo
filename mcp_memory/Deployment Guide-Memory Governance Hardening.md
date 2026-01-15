# Memory Governance Hardening - Deployment Guide

### Step 3: Enable Log-Only Mode (Monitor)

```bash
# Update environment
export GOVERNANCE_HARDENING_ENABLED=True
export GOVERNANCE_ENFORCEMENT_MODE=log_only

# Restart service
docker-compose restart l9-api

# Monitor logs for auth failures
tail -f /var/log/l9/app.log | grep -E "(auth|governance)"
```

### Step 4: Enable Full Enforcement

```bash
# After confirming no issues in log_only mode
export GOVERNANCE_ENFORCEMENT_MODE=enforce

# Restart service
docker-compose restart l9-api
```

---

## Rollback (If Needed)

```bash
# Instant rollback - no code deployment required
export GOVERNANCE_HARDENING_ENABLED=False
docker-compose restart l9-api
```

---

## Verification Commands

```bash
# Test 1: Unauthenticated request should fail (when enabled)
curl -X POST http://localhost:9002/memory/save \
  -H "Content-Type: application/json" \
  -d '{"content":"x","kind":"fact"}'
# Expected: 401

# Test 2: Cursor cannot access l-private
curl -X POST http://localhost:9002/mcp/call \
  -H "Authorization: Bearer $CURSOR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"query_temporal","arguments":{"since":"2020-01-01"}}'
# Expected: No l-private in results

# Test 3: Check DB constraints applied
psql -c "SELECT conname FROM pg_constraint WHERE conrelid = 'packet_store'::regclass;"
# Expected: packet_store_scope_check, packet_store_project_id_not_null

# Test 4: Check migrations applied
psql -c "SELECT * FROM schema_migrations ORDER BY applied_at DESC LIMIT 5;"
# Expected: 0016_governance... and 0017_governance... listed
```

---

## Files Changed Summary

| File | Type | Purpose |
|------|------|---------|
| `migrations/0016_governance_scope_semantics.sql` | NEW | Scope CHECK constraint, backfill |
| `migrations/0017_governance_project_id.sql` | NEW | Project_id NOT NULL, backfill |
| `mcp_memory/src/config.py` | MOD | Feature flags |
| `mcp_memory/src/main.py` | MOD | Auth middleware |
| `mcp_memory/src/audit.py` | NEW | Mandatory audit logging |
| `mcp_memory/src/mcp_server.py` | MOD | Scope filtering, audit |
| `mcp_memory/src/routes/memory_unified.py` | MOD | Caller enforcement, project filter |
| `tests/memory/conftest_governance.py` | NEW | Test fixtures |
| `tests/memory/test_governance_invariants.py` | NEW | Regression tests |

---

## Governance Invariants Enforced

1. ✅ All memory REST + MCP routes require authentication
2. ✅ Cursor cannot see/write l-private scope  
3. ✅ Project_id isolation at SQL level
4. ✅ Caller identity server-enforced (not from request body)
5. ✅ Audit logging mandatory (fail-closed)
6. ✅ Scope semantics preserved (developer/global/l-private)
7. ✅ No SQL injection vulnerabilities