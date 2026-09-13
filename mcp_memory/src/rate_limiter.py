"""Async-safe, versioned rate limiter for in-memory request tracking."""

from __future__ import annotations

from core.decorators import must_stay_async


import asyncio
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class RateLimitBucket:
    """Mutable bucket for a single IP, tracked with a version counter."""

    request_timestamps: deque[float] = field(default_factory=deque)
    failed_auth_timestamps: deque[float] = field(default_factory=deque)
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
        """
        Initializes a RateLimiter instance with specified limits for request rate and failed authentication blocking, ensuring thread-safe in-memory request tracking.

        Args:
            request_limit: Maximum number of requests allowed within the request window.
            request_window_seconds: Duration in seconds for the request rate window.
            failed_auth_limit: Allowed number of failed auth attempts before blocking.
            failed_auth_block_seconds: Duration in seconds to block after exceeding failed auth limit.
        """
        self._request_limit = request_limit
        self._request_window_seconds = request_window_seconds
        self._failed_auth_limit = failed_auth_limit
        self._failed_auth_block_seconds = failed_auth_block_seconds
        self._lock = asyncio.Lock()
        self._buckets: dict[str, RateLimitBucket] = {}

    @must_stay_async("callers use await")
    async def is_rate_limited(self, ip: str, now: float | None = None) -> bool:
        """Return True if the IP has exceeded the request limit."""
        current_time = now if now is not None else time.time()
        async with self._lock:
            bucket = self._get_bucket(ip)
            self._prune(bucket, current_time, self._request_window_seconds, "request")
            return len(bucket.request_timestamps) >= self._request_limit

    @must_stay_async("callers use await")
    async def is_auth_blocked(self, ip: str, now: float | None = None) -> bool:
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

    @must_stay_async("callers use await")
    async def record_request(self, ip: str, now: float | None = None) -> int:
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

    @must_stay_async("callers use await")
    async def record_failed_auth(self, ip: str, now: float | None = None) -> int:
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

    @must_stay_async("callers use await")
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
        """Get or create a rate limit bucket for an IP.

        Args:
            ip: IP address to get bucket for.

        Returns:
            RateLimitBucket for the IP.
        """
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
        """Remove expired timestamps from a bucket.

        Args:
            bucket: RateLimitBucket to prune.
            now: Current timestamp.
            window_seconds: Window duration in seconds.
            bucket_type: 'request' or 'failed_auth'.
        """
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
        """Assert bucket version matches expected to detect concurrent mutation.

        Args:
            bucket: RateLimitBucket to check.
            expected_version: Expected version number.

        Raises:
            RuntimeError: If version mismatch detected.
        """
        if bucket.version != expected_version:
            raise RuntimeError(
                "Rate limiter bucket version mismatch; concurrent mutation detected."
            )


# Runtime execution trace - updated automatically on every execution
