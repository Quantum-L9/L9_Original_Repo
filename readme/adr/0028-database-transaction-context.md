# ADR 0028: Database Transaction Context

## Status
Accepted

## Pattern
ALL database operations wrapped in `transaction()` context manager with RLS scope.

## Files
- `memory/substrate_repository.py` - Transaction implementation
- `memory/ingestion.py` - Transaction usage
- `memory/governance_gate.py` - RLS context

## Import Block
```python
from memory.substrate_repository import SubstrateRepository, TransactionError
from config.rls_config import get_rls_config
```

## Minimal Implementation
```python
from contextlib import asynccontextmanager
from typing import AsyncIterator, Any
import asyncpg
import structlog

logger = structlog.get_logger(__name__)


class TransactionError(Exception):
    """Raised when transaction fails."""
    pass


class SubstrateRepository:
    """Repository with transaction support and RLS."""
    
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
    
    @asynccontextmanager
    async def transaction(
        self,
        tenant_id: str,
        org_id: str,
        user_id: str,
        role: str = "end_user",
    ) -> AsyncIterator[asyncpg.Connection]:
        """
        Transaction context with RLS scope.
        
        Args:
            tenant_id: RLS tenant UUID
            org_id: RLS organization UUID
            user_id: RLS user UUID
            role: User role for RLS policies
        
        Yields:
            Database connection with RLS configured
        
        Raises:
            TransactionError: If transaction fails
        """
        conn = await self._pool.acquire()
        
        try:
            # Start transaction
            async with conn.transaction():
                # Set RLS session variables
                await conn.execute(
                    "SET app.tenant_id = $1",
                    tenant_id,
                )
                await conn.execute(
                    "SET app.org_id = $1",
                    org_id,
                )
                await conn.execute(
                    "SET app.user_id = $1",
                    user_id,
                )
                await conn.execute(
                    "SET app.role = $1",
                    role,
                )
                
                logger.debug(
                    "transaction.started",
                    tenant_id=tenant_id,
                    org_id=org_id,
                )
                
                yield conn
                
                # Auto-commit on successful exit
                logger.debug("transaction.committed")
                
        except Exception as e:
            # Auto-rollback on exception
            logger.error(
                "transaction.rolled_back",
                error=str(e),
            )
            raise TransactionError(f"Transaction failed: {e}") from e
            
        finally:
            await self._pool.release(conn)
```

## Usage Example
```python
from memory.substrate_repository import SubstrateRepository
from config.rls_config import get_rls_config

async def ingest_packet(packet: dict) -> dict:
    """Ingest packet with transaction."""
    repo = SubstrateRepository(pool)
    rls = get_rls_config()
    
    async with repo.transaction(
        tenant_id=str(rls.tenant_id),
        org_id=str(rls.org_id),
        user_id=str(rls.user_id),
        role="end_user",
    ) as conn:
        # All operations in transaction
        packet_id = await conn.fetchval(
            """
            INSERT INTO packet_store (packet_type, payload, metadata)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            packet["packet_type"],
            packet["payload"],
            packet["metadata"],
        )
        
        # Second operation in same transaction
        await conn.execute(
            """
            INSERT INTO semantic_memory (packet_id, embedding)
            VALUES ($1, $2)
            """,
            packet_id,
            embedding,
        )
        
        # Auto-commit on exit
        return {"packet_id": str(packet_id)}


# With error handling
async def safe_write(data: dict) -> dict | None:
    """Write with explicit error handling."""
    try:
        async with repo.transaction(**rls_params) as conn:
            await conn.execute("INSERT ...")
            return {"status": "ok"}
    except TransactionError as e:
        logger.error("write_failed", error=str(e))
        return None
```

## Anti-Pattern Example
```python
# ❌ WRONG — No transaction wrapper
async def bad_write(packet: dict):
    conn = await pool.acquire()
    await conn.execute("INSERT ...")  # No transaction!
    await pool.release(conn)

# ❌ WRONG — Missing RLS parameters
async with repo.transaction() as conn:  # No tenant_id!
    await conn.execute("INSERT ...")

# ❌ WRONG — Manual commit/rollback
async with repo.transaction(**rls) as conn:
    await conn.execute("INSERT ...")
    await conn.execute("COMMIT")  # Context manager handles this!

# ❌ WRONG — Nested transactions
async with repo.transaction(**rls) as conn1:
    async with repo.transaction(**rls) as conn2:  # Not supported!
        ...

# ✅ CORRECT — Single transaction with RLS
async with repo.transaction(
    tenant_id=tenant_id,
    org_id=org_id,
    user_id=user_id,
    role="end_user",
) as conn:
    await conn.execute("INSERT ...")
    await conn.execute("UPDATE ...")
    # Auto-commit on success, auto-rollback on error
```

## RLS Session Variables
```sql
-- Set by transaction() context manager
SET app.tenant_id = '73350468-3158-5d0f-9b8c-9b193d96fc4b';
SET app.org_id = '14910cef-fea1-51d7-9a28-05579e6c0c18';
SET app.user_id = '2f00c090-3816-51a0-806c-34d32522a070';
SET app.role = 'end_user';

-- RLS policies use these
CREATE POLICY tenant_isolation ON packet_store
USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

## Rules
1. ALL DB operations MUST use `transaction()`
2. Pass RLS params (tenant_id, org_id, user_id, role)
3. Never use raw connection outside transaction
4. Handle `TransactionError` explicitly
5. Never nest transactions (not supported)

## AI Guidance
**DO:**
- Use `transaction()` for all DB operations
- Pass RLS params from governance context
- Let context manager handle commit/rollback
- Log transaction start/end

**DO NOT:**
- Execute queries without transaction
- Skip RLS parameters
- Manually commit/rollback
- Nest transactions
