"""
Memory Governance Gate
======================

Single, non-bypassable governance gate for all memory operations.
Enforces:
- Authenticated caller identity (server-derived)
- Project isolation (project_id)
- Scope restrictions (including l-private protections)
- RLS (Row-Level Security) tenant/org/user isolation

GMP-68: Memory Governance Gate Implementation
GMP-80: RLS Full Instantiation
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Governance Gate",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T12:05:57Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "governance_gate",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "agents.cursor.integrations.cursor_gateway",
            "api.memory.router",
            "api.routes.mcp",
            "core.agents.bootstrap.phase_7_verify_and_lock",
            "mcp_memory.src.db",
            "mcp_memory.src.routes.memory_unified",
            "memory.__init__",
            "memory.ingestion",
            "memory.retrieval",
            "memory.substrate_repository",
        ],
    },
}
# ============================================================================

from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Optional, Sequence
import os

from config.rls_config import get_rls_config
from core.decorators import must_stay_async


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
    )


def set_governance_context(ctx: MemoryGovernanceContext) -> Any:
    """Set governance context in the current contextvar."""
    return _governance_context.set(ctx)


def reset_governance_context(token: Any) -> None:
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
    """Build fallback context from environment variables with RLS UUIDs.

    GMP-80: Added RLS UUID population from rls_config.
    """
    caller_id = os.getenv("L9_MEMORY_CALLER_ID")
    project_id = os.getenv("L9_PROJECT_ID")
    scope = os.getenv("L9_MEMORY_SCOPE", "shared")
    if not caller_id or not project_id:
        raise RuntimeError(
            "Fallback governance context requires L9_MEMORY_CALLER_ID and L9_PROJECT_ID"
        )

    # GMP-80: Get RLS UUIDs from config (deterministic, shared by L and C)
    rls_config = get_rls_config()

    return build_governance_context(
        caller_id=caller_id,
        role="end_user",
        scope=scope,
        project_id=project_id,
        allowed_scopes=[scope],
        tenant_id=rls_config.tenant_uuid,
        org_id=rls_config.org_uuid,
        user_id=rls_config.user_uuid,
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
@must_stay_async("callers use await")
async def governance_context(
    ctx: MemoryGovernanceContext,
) -> AsyncGenerator[MemoryGovernanceContext, None]:
    """Async context manager to enforce governance context."""
    token = set_governance_context(ctx)
    try:
        yield ctx
    finally:
        reset_governance_context(token)


def enforce_packet_governance(packet_in: Any, ctx: MemoryGovernanceContext) -> Any:
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
            raise RuntimeError(f"Client-supplied metadata '{key}' is not allowed")
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
) -> tuple[str, list[Any], int]:
    """Build SQL scope + project filter clause with parameterized queries.

    Returns:
        (clause, params, next_param_idx)
        - clause: SQL fragment like "AND table.scope = ANY($1) AND ..."
        - params: List of parameter values
        - next_param_idx: Next available parameter index
    """
    clause = (
        f"AND {table_alias}.scope = ANY(${param_idx}) "
        f"AND {table_alias}.{envelope_column}->'metadata'->>'project_id' = ${param_idx + 1}"
    )
    params: list[Any] = [list(ctx.allowed_scopes), ctx.project_id]
    return clause, params, param_idx + 2


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-014",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["async", "auth", "dataclass", "learning", "memory-substrate", "rest-api"],
    "keywords": [
        "build",
        "enforce",
        "ensure",
        "filter",
        "gate",
        "governance",
        "isolation",
        "memory",
    ],
    "business_value": "Implements MemoryGovernanceContext for governance gate functionality",
    "last_modified": "2026-01-17T23:47:56Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
