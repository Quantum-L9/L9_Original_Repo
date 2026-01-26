# RLS Tenant ID Implementation Status

**Last Updated:** 2026-01-15 (GMP-80)
**Status:** ✅ PARTIALLY INSTANTIATED

---

## Current Architecture: Shared Tenant, Scope-Based Isolation

L and C intentionally share the **SAME tenant_id/org_id/user_id** to preserve collaboration.

The L9 memory architecture uses a **unified tenant with scope-based isolation**, not separate tenants:

| Isolation Layer | Mechanism                                    | Purpose                                                 |
| --------------- | -------------------------------------------- | ------------------------------------------------------- |
| **Tenant**      | `RLS_TENANT_ID=l9`                           | Top-level organization isolation (single L9 deployment) |
| **Scope**       | `developer`, `l-private`, `global`           | Access control between L and C                          |
| **Creator**     | `metadata.creator` = "L-CTO" or "Cursor-IDE" | Ownership for write/delete permissions                  |
| **Project**     | `project_id`                                 | Multi-project isolation (l9, future-x, etc.)            |

---

## GMP-80: RLS Full Instantiation (2026-01-15)

### What Was Implemented

1. **Deterministic UUID Generation** (`config/rls_config.py`)

   - Uses `uuid5(NAMESPACE_DNS, identifier)` for consistent UUIDs
   - Same identifier always produces same UUID
   - Valid PostgreSQL UUIDs

2. **Generated UUIDs**

   ```
   tenant_id "l9" → 73350468-3158-5d0f-9b8c-9b193d96fc4b
   org_id "quantumai" → 14910cef-fea1-51d7-9a28-05579e6c0c18
   user_id "l9-shared" → 2f00c090-3816-51a0-806c-34d32522a070
   ```

3. **Governance Gate Integration** (`memory/governance_gate.py`)

   - `_fallback_context()` now populates tenant_id, org_id, user_id
   - UUIDs derived from `config/rls_config.py`

4. **Ingestion Pipeline Wiring** (`memory/ingestion.py`)
   - `transaction()` now passes RLS parameters from governance context

### What's Pending (GMP-81)

- `memory/substrate_service.py` — Protected file, requires separate GMP
- Write_packet() validation and RLS scope block wiring

---

## How RLS_TENANT_ID is Used

From `config/rls_config.py`:

```python
from config.rls_config import get_rls_config

config = get_rls_config()
print(config.tenant_uuid)  # 73350468-3158-5d0f-9b8c-9b193d96fc4b
print(config.org_uuid)     # 14910cef-fea1-51d7-9a28-05579e6c0c18
print(config.user_uuid)    # 2f00c090-3816-51a0-806c-34d32522a070
```

From `.env.example`:

```bash
# PostgreSQL RLS Context (GMP-80: deterministic UUIDs)
# These string identifiers are converted to UUIDs via uuid5 for PostgreSQL RLS.
# L and C share the same tenant/org/user to preserve collaboration.
RLS_TENANT_ID=l9
RLS_ORG_ID=quantumai
RLS_USER_ID=l9-shared
```

The PostgreSQL RLS policies use session variables:

```sql
SET app.tenant_id = '73350468-3158-5d0f-9b8c-9b193d96fc4b';
SET app.org_id = '14910cef-fea1-51d7-9a28-05579e6c0c18';
SET app.user_id = '2f00c090-3816-51a0-806c-34d32522a070';
SET app.role = 'end_user';
```

---

## Why L and C Share a Tenant

From `mcp_memory/memory-setup-instructions.md`:

```
L and Cursor share the SAME tables with scope-based access control.
NO separate tenants - single source of truth.

ACCESS MATRIX:
┌─────────────┬────────────────────────────────┬─────────────────────────┐
│             │  developer (all projects)      │  l-private              │
├─────────────┼────────────────────────────────┼─────────────────────────┤
│ Cursor (C)  │  READ/WRITE (global access)    │       BLOCKED           │
│ L-CTO       │  READ/WRITE                    │       READ/WRITE        │
└─────────────┴────────────────────────────────┴─────────────────────────┘
```

**Key insight:** L and C collaborate in the same semantic space. Cursor can read L's memories (in `developer` scope) and L can read Cursor's. The isolation is:

1. **Scope-based:** Cursor cannot access `l-private` (L's internal reasoning)
2. **Creator-based:** Cursor can only UPDATE/DELETE memories where `metadata.creator = 'Cursor-IDE'`

---

## Summary

| Variable           | Value                      | UUID                                   | Shared?                 |
| ------------------ | -------------------------- | -------------------------------------- | ----------------------- |
| `RLS_TENANT_ID`    | `l9`                       | `73350468-3158-5d0f-9b8c-9b193d96fc4b` | Yes                     |
| `RLS_ORG_ID`       | `quantumai`                | `14910cef-fea1-51d7-9a28-05579e6c0c18` | Yes                     |
| `RLS_USER_ID`      | `l9-shared`                | `2f00c090-3816-51a0-806c-34d32522a070` | Yes                     |
| `caller_id`        | "L" or "C"                 | N/A                                    | No - API key determines |
| `metadata.creator` | "L-CTO" or "Cursor-IDE"    | N/A                                    | No - server-enforced    |
| `scope`            | developer/l-private/global | N/A                                    | Access differs          |

---

## Related Files

- `config/rls_config.py` — UUID generation and configuration
- `memory/governance_gate.py` — Governance context with RLS
- `memory/ingestion.py` — Transaction wiring
- `memory/substrate_repository.py` — `transaction()` with RLS session scope
- `migrations/0008_memory_substrate_10x.sql` — RLS policies and functions
