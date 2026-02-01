# ============================================================================
__dora_meta__ = {
    "component_name": "Cursor Working Memory Service",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-28T22:45:42Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "cursor_working_memory_service",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": ["working_memory", "semantic_memory"],
        "imported_by": [
            "agents.cursor.cursor_retrieval_kernel",
            "agents.cursor.cursor_session_hooks",
            "memory_cache.__init__",
            "runtime.redis_client",
        ],
    },
}
# ============================================================================

# memory_cache/cursor_working_memory_service.py
"""
Repo-scoped, TTL-based working memory for Cursor.
No embeddings. No insights. Only ephemeral operational state.
Backing: Redis. TTL: 4 hours (configurable).

Adapted for L9 async architecture.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from runtime.redis_client import RedisClient


class MemoryEventType(str, Enum):
    TOOL_EXECUTED = "tool_executed"
    DECISION_MADE = "decision_made"
    FILE_TOUCHED = "file_touched"
    HYPOTHESIS_FORMED = "hypothesis_formed"
    ERROR_ENCOUNTERED = "error_encountered"


@dataclass
class WorkingMemorySnapshot:
    """Single immutable working memory state."""

    repo_id: str
    branch: str
    intent: str | None = None
    files_touched: list[str] | None = None
    recent_decisions: list[dict[str, Any]] | None = None
    recent_errors: list[dict[str, Any]] | None = None
    open_hypotheses: list[str] | None = None
    last_action_type: str | None = None
    last_action_timestamp: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    repo_state_hash: str | None = None

    def __post_init__(self):
        if self.files_touched is None:
            self.files_touched = []
        if self.recent_decisions is None:
            self.recent_decisions = []
        if self.recent_errors is None:
            self.recent_errors = []
        if self.open_hypotheses is None:
            self.open_hypotheses = []
        if self.created_at is None:
            self.created_at = datetime.now(UTC).isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at


class CursorWorkingMemoryService:
    """
    Manages ephemeral, repo-scoped working memory for Cursor.

    Principles:
    - No auto-promotion (cache must earn permanence)
    - Strict TTL enforcement (natural expiry > manual delete)
    - Scope: repo_id + branch (not cross-repo bleeding)
    - Single writer per repo (no race conditions)

    Async-compatible for L9 architecture.
    """

    DEFAULT_TTL_HOURS = 4
    MAX_ALLOWED_TTL_HOURS = 8
    MIN_FILES_TRACKED = 100
    MAX_FILES_TRACKED = 500

    def __init__(
        self,
        redis_client: RedisClient,
        default_ttl_hours: int = DEFAULT_TTL_HOURS,
    ):
        self.redis = redis_client
        self.ttl_hours = min(default_ttl_hours, self.MAX_ALLOWED_TTL_HOURS)

    def _key(self, repo_id: str, branch: str) -> str:
        """Consistent Redis key generation."""
        return f"wmc:v2:{repo_id}:{branch}"

    def _hash_files(self, files: list[str]) -> str:
        """Deterministic hash of file list for state tracking."""
        content = "|".join(sorted(set(files)))
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    # === PRIMARY OPERATIONS ===

    async def hydrate(
        self,
        repo_id: str,
        branch: str,
    ) -> WorkingMemorySnapshot | None:
        """
        Retrieve working memory for a Cursor session.

        Called: on_session_start()
        Returns: None if expired or never set
        """
        raw = await self.redis.get(self._key(repo_id, branch))
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return WorkingMemorySnapshot(**data)
        except (json.JSONDecodeError, TypeError):
            # Corrupted or stale; return None (will fall through to memory_search)
            return None

    async def update(
        self,
        repo_id: str,
        branch: str,
        intent: str | None = None,
        action: dict[str, Any] | None = None,
        files_touched: list[str] | None = None,
        hypothesis: str | None = None,
        error: dict[str, Any] | None = None,
        repo_state_hash: str | None = None,
    ) -> WorkingMemorySnapshot:
        """
        Update working memory (incremental append).

        Called: on_action() inside agent loop
        Effect: merges new data with existing cache, resets TTL
        Returns: updated snapshot
        """
        # Retrieve current state
        snapshot = await self.hydrate(repo_id, branch)
        if snapshot is None:
            snapshot = WorkingMemorySnapshot(repo_id=repo_id, branch=branch)

        # Merge new data
        if intent:
            snapshot.intent = intent

        if action:
            snapshot.recent_decisions.append(
                {"action": action, "timestamp": datetime.now(UTC).isoformat()}
            )
            snapshot.last_action_type = action.get("type", "unknown")
            snapshot.last_action_timestamp = datetime.now(UTC).isoformat()

        if files_touched:
            snapshot.files_touched.extend(files_touched)
            snapshot.files_touched = sorted(list(set(snapshot.files_touched)))
            # Enforce bounded tracking
            if len(snapshot.files_touched) > self.MAX_FILES_TRACKED:
                snapshot.files_touched = snapshot.files_touched[
                    -self.MAX_FILES_TRACKED :
                ]

        if hypothesis:
            snapshot.open_hypotheses.append(hypothesis)

        if error:
            snapshot.recent_errors.append(
                {"error": error, "timestamp": datetime.now(UTC).isoformat()}
            )

        if repo_state_hash:
            snapshot.repo_state_hash = repo_state_hash

        snapshot.updated_at = datetime.now(UTC).isoformat()

        # Persist with TTL
        ttl_seconds = int(self.ttl_hours * 3600)
        await self.redis.set(
            self._key(repo_id, branch),
            json.dumps(asdict(snapshot)),
            ttl=ttl_seconds,
        )

        return snapshot

    async def clear(self, repo_id: str, branch: str) -> bool:
        """
        Explicitly clear working memory.

        Called: on_session_end() if user requests "forget this session"
        Returns: True if deleted, False if didn't exist
        """
        return await self.redis.delete(self._key(repo_id, branch))

    async def expire_soon(self, repo_id: str, branch: str, seconds: int = 60) -> None:
        """
        Fast-expire a cache entry (for explicit shutdown).

        Used: if session ends gracefully or memory is invalidated
        """
        # Use set with short TTL to expire soon
        raw = await self.redis.get(self._key(repo_id, branch))
        if raw:
            await self.redis.set(self._key(repo_id, branch), raw, ttl=seconds)

    # === DIAGNOSTIC / DEBUG ===

    async def ttl_remaining(self, repo_id: str, branch: str) -> int | None:
        """Seconds until this cache entry expires."""
        # RedisClient doesn't expose ttl directly, check if key exists
        raw = await self.redis.get(self._key(repo_id, branch))
        return None if raw is None else -1  # -1 means exists but TTL unknown

    async def stats(self, repo_id: str, branch: str) -> dict[str, Any]:
        """Debug snapshot of current WMC state."""
        snapshot = await self.hydrate(repo_id, branch)
        if not snapshot:
            return {"status": "empty"}
        return {
            "status": "active",
            "intent": snapshot.intent,
            "files_tracked": len(snapshot.files_touched),
            "decisions_made": len(snapshot.recent_decisions),
            "errors_logged": len(snapshot.recent_errors),
            "hypotheses_open": len(snapshot.open_hypotheses),
            "ttl_remaining_seconds": await self.ttl_remaining(repo_id, branch),
            "last_updated": snapshot.updated_at,
        }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["runtime.redis_client"],
    "tags": [
        "async",
        "cache",
        "caching",
        "data-models",
        "dataclass",
        "debugging",
        "event-driven",
        "operations",
        "security",
        "serialization",
    ],
    "keywords": [
        "clear",
        "cursor",
        "event",
        "expire",
        "hydrate",
        "memory",
        "remaining",
        "service",
    ],
    "business_value": "Provides cursor working memory service components including MemoryEventType, WorkingMemorySnapshot, CursorWorkingMemoryService",
    "last_modified": "2026-01-31T22:27:11Z",
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
