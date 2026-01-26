# ADR 0015: Migration Sequential Apply Pattern

## Status

Accepted

## Pattern

Database migrations MUST be applied in strict sequential order; each builds on previous schema.

## Files

- `migrations/*.sql` - 24+ PostgreSQL migrations
- `migrations/README.md` - Full documentation
- `memory/migration_runner.py` - Auto-apply at startup

## Import Block

```python
# For migration runner
from memory.migration_runner import MigrationRunner

# For checking applied migrations
from pathlib import Path
MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"
```

## Minimal Implementation

```sql
-- migrations/0025_new_feature.sql
-- Migration: 0025
-- Description: Add new_feature table
-- Depends: 0024
-- Author: Your Name
-- Date: 2026-01-20

-- Idempotent: Safe to re-run
CREATE TABLE IF NOT EXISTS new_feature (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add index if not exists
CREATE INDEX IF NOT EXISTS idx_new_feature_name
ON new_feature(name);

-- RLS policy
ALTER TABLE new_feature ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS new_feature_tenant_isolation
ON new_feature
USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

## Usage Example

```python
# Apply migrations at startup
from memory.migration_runner import MigrationRunner

runner = MigrationRunner(connection_string=DATABASE_URL)
await runner.apply_pending()  # Applies 0001 → 0025 in order

# Check migration status
applied = await runner.get_applied_migrations()
# ['0001', '0002', ..., '0024']
```

## Anti-Pattern Example

```sql
-- ❌ WRONG — Not idempotent (will fail on re-run)
CREATE TABLE new_feature (...);  -- No IF NOT EXISTS

-- ❌ WRONG — Skipping migration number
-- migrations/0027_feature.sql when 0025, 0026 don't exist

-- ❌ WRONG — Modifying applied migration
-- Editing 0020_*.sql after it's been applied

-- ✅ CORRECT — Idempotent with IF NOT EXISTS
CREATE TABLE IF NOT EXISTS new_feature (...);
```

## Naming Convention

```
NNNN_description.sql
│    └── Snake_case description
└── 4-digit sequential number (0001-9999)

Examples:
0001_init_memory_substrate.sql
0008_memory_substrate_10x.sql
0024_cmts_schema.sql
```

## Rules

1. Migrations MUST be applied in numerical order (0001→0024→0025)
2. Each migration MUST be idempotent (safe to re-run)
3. NEVER skip migrations (0008 depends on 0001-0007)
4. NEVER modify applied migrations (create new one instead)
5. Use `IF NOT EXISTS` for CREATE statements
6. Include `-- Migration: NNNN` header comment

## AI Guidance

**DO:**

- Apply migrations in order (0001 → latest)
- Use `IF NOT EXISTS` and `IF EXISTS` guards
- Create new migration for any schema change
- Include RLS policies for new tables

**DO NOT:**

- Skip migrations (breaks dependencies)
- Modify existing migration files after applied
- Apply migrations out of order
- Use raw SQL without migration file
