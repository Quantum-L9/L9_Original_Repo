# ADR 0005: RLS Shared Tenant Model

## Status

Accepted

## Pattern

L and Cursor share SAME tenant_id/org_id/user_id; isolation via `scope` field + `creator` metadata.

## Files

- `config/rls_config.py` - UUID generation
- `memory/governance_gate.py` - Context enforcement
- `memory/substrate_repository.py` - `transaction()` with RLS
- `migrations/0008_memory_substrate_10x.sql` - RLS policies

## UUIDs (Deterministic via uuid5)

```
tenant_id  "l9"        → 73350468-3158-5d0f-9b8c-9b193d96fc4b
org_id     "quantumai" → 14910cef-fea1-51d7-9a28-05579e6c0c18
user_id    "l9-shared" → 2f00c090-3816-51a0-806c-34d32522a070
```

## Isolation Model

```
┌─────────────┬────────────────────┬─────────────────┐
│             │ developer scope    │ l-private scope │
├─────────────┼────────────────────┼─────────────────┤
│ Cursor (C)  │ READ/WRITE         │ BLOCKED         │
│ L-CTO       │ READ/WRITE         │ READ/WRITE      │
└─────────────┴────────────────────┴─────────────────┘
```

## Scope Values

| Scope       | Access | Purpose                    |
| ----------- | ------ | -------------------------- |
| `developer` | L + C  | Shared collaboration space |
| `l-private` | L only | L's internal reasoning     |
| `global`    | All    | Cross-project knowledge    |

## Rules

1. L and C ALWAYS share same tenant_id/org_id/user_id
2. Isolation is scope-based, NOT tenant-based
3. `metadata.creator` tracks who wrote the memory
4. Cursor can only UPDATE/DELETE where `creator = 'Cursor-IDE'`
5. UUIDs generated via `uuid5(NAMESPACE_DNS, identifier)`

## PostgreSQL Session Variables

```sql
SET app.tenant_id = '73350468-3158-5d0f-9b8c-9b193d96fc4b';
SET app.org_id = '14910cef-fea1-51d7-9a28-05579e6c0c18';
SET app.user_id = '2f00c090-3816-51a0-806c-34d32522a070';
SET app.role = 'end_user';
```

## AI Guidance

**DO:**

- Use `get_rls_config()` for UUID access
- Use `require_governance_context()` before memory ops
- Pass RLS params to `transaction()` context manager

**DO NOT:**

- Create separate tenants for L and C
- Hardcode UUID values (use `config/rls_config.py`)
- Skip RLS context in memory operations
- Change UUIDs without migration
