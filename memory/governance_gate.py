"""
Memory Governance Gate
======================

Single, non-bypassable governance gate for all memory operations.
Enforces:
- Authenticated caller identity (server-derived)
- Project isolation (project_id)
- Scope restrictions (including l-private protections)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Optional, Sequence
import os


@dataclass(frozen=True)
class MemoryGovernanceContext:
    """Immutable governance context for memory operations."""

    caller_id: str
    role: str
    scope: str
    project_id: str
    allowed_scopes: tuple[str, ...]
    tenant_id: Optional[str] = None
    org_id: Optional[str] = None
    user_id: Optional[str] = None
    creator: Optional[str] = None
    source: Optional[str] = None
    substrate_service: Optional[Any] = None

    def __post_init__(self) -> None:
        if not self.caller_id:
            raise RuntimeError("caller_id is required for governance enforcement")
        if not self.project_id:
            raise RuntimeError("project_id is required for governance enforcement")
        if not self.allowed_scopes:
            raise RuntimeError("allowed_scopes cannot be empty")
        if self.scope not in self.allowed_scopes:
            raise RuntimeError("scope must be included in allowed_scopes")
        if self.caller_id == "C" and "l-private" in self.allowed_scopes:
            raise RuntimeError("Cursor cannot access l-private scope")


_governance_context: ContextVar[Optional[MemoryGovernanceContext]] = ContextVar(
    "memory_governance_context", default=None
)


def build_governance_context(
    *,
    caller_id: str,
    role: str,
    scope: str,
    project_id: str,
    allowed_scopes: Sequence[str],
    tenant_id: Optional[str] = None,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None,
    creator: Optional[str] = None,
    source: Optional[str] = None,
    substrate_service: Optional[Any] = None,
) -> MemoryGovernanceContext:
    """Build a validated governance context (server-derived only)."""
    return MemoryGovernanceContext(
        caller_id=caller_id,
        role=role,
        scope=scope,
        project_id=project_id,
        allowed_scopes=tuple(allowed_scopes),
        tenant_id=tenant_id,
        org_id=org_id,
        user_id=user_id,
        creator=creator,
        source=source,
        substrate_service=substrate_service,
    )


def set_governance_context(ctx: MemoryGovernanceContext):
    """Set governance context in the current contextvar."""
    return _governance_context.set(ctx)


def reset_governance_context(token) -> None:
    """Reset governance context."""
    _governance_context.reset(token)


def require_governance_context(operation: str) -> MemoryGovernanceContext:
    """Require an active governance context or fail closed."""
    ctx = _governance_context.get()
    if ctx is None:
        raise RuntimeError(
            f"Governance context required for memory operation: {operation}"
        )
    return ctx


def _fallback_context() -> MemoryGovernanceContext:
    caller_id = os.getenv("L9_MEMORY_CALLER_ID")
    project_id = os.getenv("L9_PROJECT_ID")
    scope = os.getenv("L9_MEMORY_SCOPE", "shared")
    if not caller_id or not project_id:
        raise RuntimeError("Fallback governance context requires L9_MEMORY_CALLER_ID and L9_PROJECT_ID")
    return build_governance_context(
        caller_id=caller_id,
        role="end_user",
        scope=scope,
        project_id=project_id,
        allowed_scopes=[scope],
    )


@asynccontextmanager
async def ensure_governance_context(
    operation: str,
) -> AsyncGenerator[MemoryGovernanceContext, None]:
    """Ensure governance context is set, with fallback to server identity."""
    ctx = _governance_context.get()
    if ctx is not None:
        yield ctx
        return
    fallback = _fallback_context()
    async with governance_context(fallback):
        yield fallback


@asynccontextmanager
async def governance_context(
    ctx: MemoryGovernanceContext,
) -> AsyncGenerator[MemoryGovernanceContext, None]:
    """Async context manager to enforce governance context."""
    token = set_governance_context(ctx)
    try:
        yield ctx
    finally:
        reset_governance_context(token)


def enforce_packet_governance(packet_in, ctx: MemoryGovernanceContext):
    """Validate/override packet metadata + payload with governance constraints."""
    metadata = dict(packet_in.metadata or {})
    payload = dict(packet_in.payload or {})

    enforced_fields = {
        "caller": ctx.caller_id,
        "project_id": ctx.project_id,
        "scope": ctx.scope,
    }
    if ctx.creator is not None:
        enforced_fields["creator"] = ctx.creator
    if ctx.source is not None:
        enforced_fields["source"] = ctx.source

    for key, value in enforced_fields.items():
        if key in metadata and metadata[key] != value:
            raise RuntimeError(
                f"Client-supplied metadata '{key}' is not allowed"
            )
        metadata[key] = value

    for key in ("scope", "project_id"):
        if key in payload and payload[key] != enforced_fields[key]:
            raise RuntimeError(f"Client-supplied payload '{key}' is not allowed")
        payload[key] = enforced_fields[key]

    return packet_in.model_copy(update={"metadata": metadata, "payload": payload})


def build_scope_project_filter(
    ctx: MemoryGovernanceContext,
    *,
    param_idx: int,
    table_alias: str = "packet_store",
    envelope_column: str = "envelope",
) -> tuple[str, list, int]:
    """Build SQL scope + project filter clause with params."""
    clause = (
        f"AND {table_alias}.scope = ANY(${param_idx}) "
        f"AND COALESCE({table_alias}.{envelope_column}->'metadata'->>'project_id', 'l9') = ${param_idx + 1}"
    )
    params = [list(ctx.allowed_scopes), ctx.project_id]
    return clause, params, param_idx + 2
