"""
Ingress Guard Middleware
========================
FastAPI middleware that enforces principal_id on all state-mutating requests.

This is the Tier 1 (AuthN) layer of the L9 two-tier governance model:
  - Tier 1 (here): Extract principal_id, reject anonymous mutations, audit log.
  - Tier 2 (DomainBridgeGateway): Authorization + GovernanceEngine evaluation.

ADR-0092: Domain Bridge Single Ingress.
"""

from __future__ import annotations

import uuid
from typing import ClassVar

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "IngressGuard",
    "module_version": "1.0.0",
    "created_by": "L-CTO Agent",
    "created_at": "2026-02-19T12:00:00Z",
    "updated_at": "2026-02-19T12:00:00Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "ingress_guard",
    "type": "middleware",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["ALL"],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_READ_ONLY_METHODS: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS"})

_STATE_MUTATING_METHODS: frozenset[str] = frozenset({"POST", "PUT", "DELETE", "PATCH"})

# Paths that are exempt from principal_id enforcement (health, liveness, docs).
_EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        "/",
        "/health",
        "/health/startup",
        "/health/neo4j",
        "/health/services",
        "/_echo",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/metrics",
    }
)

# Route prefix → ingress_origin mapping.
_INGRESS_ORIGIN_MAP: dict[str, str] = {
    "/mcp": "mcp",
    "/slack": "slack",
    "/ws": "ws",
}


class IngressGuardMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that enforces principal_id on state-mutating requests.

    Behaviour:
      - GET / HEAD / OPTIONS → always allowed (read-only).
      - Exempt paths (health, docs) → always allowed.
      - POST / PUT / DELETE / PATCH without principal_id → HTTP 403.
      - All requests are stamped with ``request.state`` metadata for
        downstream route handlers.

    Principal extraction order:
      1. ``X-Principal-Id`` header (explicit).
      2. ``request.state.user_id`` (set by upstream auth middleware).
      3. Fail-closed: reject if state-mutating.
    """

    HEADER_NAME: ClassVar[str] = "x-principal-id"
    REQUEST_ID_HEADER: ClassVar[str] = "x-request-id"

    @must_stay_async("FastAPI/ASGI middleware handler")
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Intercept every request, stamp metadata, enforce principal_id."""
        path = request.url.path.rstrip("/") or "/"
        method = request.method.upper()

        # ── Generate or extract request_id ──────────────────────────────
        request_id = request.headers.get(self.REQUEST_ID_HEADER) or str(uuid.uuid4())

        # ── Derive ingress_origin from route prefix ────────────────────
        ingress_origin = "http"
        for prefix, origin in _INGRESS_ORIGIN_MAP.items():
            if path.startswith(prefix):
                ingress_origin = origin
                break

        # ── Derive classification from HTTP method ─────────────────────
        classification = (
            "read_only" if method in _READ_ONLY_METHODS else "state_mutating"
        )

        # ── Extract principal_id (fail-closed for mutations) ───────────
        principal_id = self._extract_principal(request)

        # ── Stamp request.state for downstream handlers ────────────────
        request.state.principal_id = principal_id or ""
        request.state.ingress_origin = ingress_origin
        request.state.classification = classification
        request.state.request_id = request_id

        # ── Exempt paths bypass enforcement ────────────────────────────
        if path in _EXEMPT_PATHS:
            return await call_next(request)

        # ── Enforce: state-mutating + no principal → 403 ───────────────
        if classification == "state_mutating" and not principal_id:
            logger.warning(
                "ingress.request",
                principal_id="anonymous",
                source_ip=self._client_ip(request),
                http_method=method,
                http_path=path,
                user_agent=request.headers.get("user-agent", ""),
                request_id=request_id,
                ingress_origin=ingress_origin,
                classification=classification,
                outcome="rejected_anonymous_mutation",
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "principal_id required for state-mutating requests",
                    "error": "missing_principal",
                    "path": path,
                    "method": method,
                },
            )

        # ── Audit log (all allowed requests) ───────────────────────────
        logger.info(
            "ingress.request",
            principal_id=principal_id or "anonymous",
            source_ip=self._client_ip(request),
            http_method=method,
            http_path=path,
            user_agent=request.headers.get("user-agent", ""),
            request_id=request_id,
            ingress_origin=ingress_origin,
            classification=classification,
            outcome="allowed",
        )

        return await call_next(request)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @classmethod
    def _extract_principal(cls, request: Request) -> str | None:
        """
        Extract principal_id from the request.

        Priority:
          1. X-Principal-Id header (explicit).
          2. request.state.user_id (set by upstream auth middleware).

        Returns None if no principal can be determined.
        """
        header_val = request.headers.get(cls.HEADER_NAME, "").strip()
        if header_val:
            return header_val

        # 2. Upstream auth middleware (e.g., JWT decoder sets user_id)
        user_id = getattr(request.state, "user_id", None)
        if user_id and str(user_id).strip():
            return str(user_id).strip()

        return None

    @staticmethod
    def _client_ip(request: Request) -> str:
        """Extract client IP, preferring X-Forwarded-For."""
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-INGRESS-001",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["starlette", "structlog", "core.decorators"],
    "tags": ["api-gateway", "operations", "middleware", "security"],
    "keywords": ["ingress", "principal_id", "authentication", "fail-closed"],
    "business_value": "Enforces principal_id on all state-mutating API requests",
    "last_modified": "2026-02-19T12:00:00Z",
    "modified_by": "L-CTO Agent",
    "change_summary": "Initial implementation per ADR-0092 Ingress Guard Strategy v3",
}
# ============================================================================
