# ADR 0025: FastAPI Dependency Injection

## Status

Accepted

## Pattern

Use `Depends()` for all shared resources; define deps in `api/dependencies.py`; never inline service creation.

## Files

- `api/dependencies.py` - Central dependency definitions
- `api/routes/*.py` - 175+ Depends() usages
- `api/server.py` - Lifespan-scoped dependencies

## Import Block

```python
from fastapi import Depends, HTTPException, status
from typing import Annotated

# Import dependency functions
from api.dependencies import (
    get_substrate_service,
    get_current_user,
    get_rls_context,
)
```

## Minimal Implementation

```python
# === api/dependencies.py ===
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated

from memory.substrate_service import get_service, MemorySubstrateService
from config.rls_config import get_rls_config, RLSConfig

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_substrate_service() -> MemorySubstrateService:
    """Get singleton memory substrate service."""
    return await get_service()


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)]
) -> dict:
    """Validate token and return user info."""
    user = await verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return user


async def get_rls_context(
    user: Annotated[dict, Depends(get_current_user)],
    rls_config: Annotated[RLSConfig, Depends(get_rls_config)],
) -> dict:
    """Get RLS context from user and config."""
    return {
        "tenant_id": rls_config.tenant_id,
        "org_id": rls_config.org_id,
        "user_id": user["user_id"],
        "role": user.get("role", "end_user"),
    }


# === api/routes/memory.py ===
from fastapi import APIRouter, Depends
from typing import Annotated

from api.dependencies import get_substrate_service, get_rls_context
from memory.substrate_service import MemorySubstrateService

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/ingest")
async def ingest_packet(
    packet: PacketEnvelopeIn,
    service: Annotated[MemorySubstrateService, Depends(get_substrate_service)],
    rls: Annotated[dict, Depends(get_rls_context)],
):
    """Ingest packet with dependency injection."""
    return await service.write_packet(packet, **rls)
```

## Usage Example

```python
from fastapi import APIRouter, Depends
from typing import Annotated
from api.dependencies import get_substrate_service

router = APIRouter()

# Type alias for cleaner signatures
SubstrateService = Annotated[MemorySubstrateService, Depends(get_substrate_service)]

@router.get("/search")
async def search_memory(
    query: str,
    service: SubstrateService,  # Injected automatically
    limit: int = 10,
):
    """Search memory with injected service."""
    return await service.search(query, limit=limit)


@router.post("/write")
async def write_packet(
    packet: PacketEnvelopeIn,
    service: SubstrateService,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Write packet with user context."""
    packet.metadata["user_id"] = user["user_id"]
    return await service.write_packet(packet)
```

## Anti-Pattern Example

```python
# ❌ WRONG — Direct instantiation in route
@router.post("/ingest")
async def ingest_packet(packet: PacketEnvelopeIn):
    service = await get_service()  # Direct call, not injected!
    return await service.write_packet(packet)

# ❌ WRONG — Importing service module directly
from memory.substrate_service import MemorySubstrateService

@router.get("/search")
async def search(query: str):
    service = MemorySubstrateService()  # Creates new instance!
    return await service.search(query)

# ❌ WRONG — Dependency defined in route file
# api/routes/memory.py
async def get_service():  # Should be in api/dependencies.py
    return await get_service()

# ✅ CORRECT — Use Depends() with centralized dependency
@router.post("/ingest")
async def ingest_packet(
    packet: PacketEnvelopeIn,
    service: Annotated[MemorySubstrateService, Depends(get_substrate_service)],
):
    return await service.write_packet(packet)
```

## Dependency Chain

```
Route Handler
    │
    ├── Depends(get_current_user)
    │       └── Depends(oauth2_scheme)
    │
    ├── Depends(get_substrate_service)
    │       └── Uses singleton getter
    │
    └── Depends(get_rls_context)
            ├── Depends(get_current_user)
            └── Depends(get_rls_config)
```

## Rules

1. ALL route dependencies via `Depends()`
2. Define shared deps in `api/dependencies.py`
3. Use singleton getters for services
4. Chain dependencies (deps can depend on deps)
5. Use `Annotated[Type, Depends(func)]` syntax

## AI Guidance

**DO:**

- Use `Depends()` for all injected resources
- Define new deps in `api/dependencies.py`
- Chain deps for composed functionality
- Use `Annotated` type hints for clarity

**DO NOT:**

- Instantiate services directly in routes
- Import services and call directly
- Define deps in route files
- Skip `Depends()` "for simplicity"
