"""Async-safe, versioned rate limiter for in-memory request tracking."""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Rate Limiter",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-14T18:12:39Z",
    "updated_at": "2026-01-15T10:53:20Z",
    "layer": "integration",
    "domain": "mcp_integration",
    "module_name": "rate_limiter",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["mcp_memory.tests.test_rate_limiting_enforcement"],
    },
}
# ============================================================================

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional


@dataclass
class RateLimitBucket:
    """Mutable bucket for a single IP, tracked with a version counter."""

    request_timestamps: Deque[float] = field(default_factory=deque)
    failed_auth_timestamps: Deque[float] = field(default_factory=deque)
    version: int = 0


@dataclass(frozen=True)
class RateLimitSnapshot:
    """Immutable snapshot for audit/testing."""

    request_count: int
    failed_auth_count: int
    version: int


class RateLimiter:
    """Async-safe in-memory rate limiter with versioned buckets."""

    def __init__(
        self,
        request_limit: int,
        request_window_seconds: int,
        failed_auth_limit: int,
        failed_auth_block_seconds: int,
    ) -> None:
        self._request_limit = request_limit
        self._request_window_seconds = request_window_seconds
        self._failed_auth_limit = failed_auth_limit
        self._failed_auth_block_seconds = failed_auth_block_seconds
        self._lock = asyncio.Lock()
        self._buckets: Dict[str, RateLimitBucket] = {}

    async def is_rate_limited(self, ip: str, now: Optional[float] = None) -> bool:
        """Return True if the IP has exceeded the request limit."""
        current_time = now if now is not None else time.time()
        async with self._lock:
            bucket = self._get_bucket(ip)
            self._prune(bucket, current_time, self._request_window_seconds, "request")
            return len(bucket.request_timestamps) >= self._request_limit

    async def is_auth_blocked(self, ip: str, now: Optional[float] = None) -> bool:
        """Return True if the IP has exceeded failed auth attempts."""
        current_time = now if now is not None else time.time()
        async with self._lock:
            bucket = self._get_bucket(ip)
            self._prune(
                bucket,
                current_time,
                self._failed_auth_block_seconds,
                "failed_auth",
            )
            return len(bucket.failed_auth_timestamps) >= self._failed_auth_limit

    async def record_request(self, ip: str, now: Optional[float] = None) -> int:
        """Record a request for the IP and return the new bucket version."""
        current_time = now if now is not None else time.time()
        async with self._lock:
            bucket = self._get_bucket(ip)
            self._prune(bucket, current_time, self._request_window_seconds, "request")
            expected_version = bucket.version
            self._assert_version(bucket, expected_version)
            bucket.request_timestamps.append(current_time)
            bucket.version += 1
            return bucket.version

    async def record_failed_auth(self, ip: str, now: Optional[float] = None) -> int:
        """Record a failed auth attempt and return the new bucket version."""
        current_time = now if now is not None else time.time()
        async with self._lock:
            bucket = self._get_bucket(ip)
            self._prune(
                bucket,
                current_time,
                self._failed_auth_block_seconds,
                "failed_auth",
            )
            expected_version = bucket.version
            self._assert_version(bucket, expected_version)
            bucket.failed_auth_timestamps.append(current_time)
            bucket.version += 1
            return bucket.version

    async def snapshot(self, ip: str) -> RateLimitSnapshot:
        """Return a snapshot of the bucket for audits/tests."""
        async with self._lock:
            bucket = self._get_bucket(ip)
            return RateLimitSnapshot(
                request_count=len(bucket.request_timestamps),
                failed_auth_count=len(bucket.failed_auth_timestamps),
                version=bucket.version,
            )

    def _get_bucket(self, ip: str) -> RateLimitBucket:
        bucket = self._buckets.get(ip)
        if bucket is None:
            bucket = RateLimitBucket()
            self._buckets[ip] = bucket
        return bucket

    def _prune(
        self,
        bucket: RateLimitBucket,
        now: float,
        window_seconds: int,
        bucket_type: str,
    ) -> None:
        cutoff = now - window_seconds
        timestamps = (
            bucket.request_timestamps
            if bucket_type == "request"
            else bucket.failed_auth_timestamps
        )
        expected_version = bucket.version
        removed_any = False
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()
            removed_any = True
        if removed_any:
            self._assert_version(bucket, expected_version)
            bucket.version += 1

    @staticmethod
    def _assert_version(bucket: RateLimitBucket, expected_version: int) -> None:
        if bucket.version != expected_version:
            raise RuntimeError(
                "Rate limiter bucket version mismatch; concurrent mutation detected."
            )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-004",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["async", "auth", "dataclass", "integration", "mcp-integration", "testing"],
    "keywords": [
        "auth",
        "blocked",
        "bucket",
        "failed",
        "limit",
        "limited",
        "limiter",
        "memory",
    ],
    "business_value": "Provides rate limiter components including RateLimitBucket, RateLimitSnapshot, RateLimiter",
    "last_modified": "2026-01-15T10:53:20Z",
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
