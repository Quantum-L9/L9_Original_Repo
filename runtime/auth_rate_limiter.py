"""
L9 Runtime - Authentication Rate Limiter
=========================================

Specialized rate limiter for authentication endpoints.

Features:
- Track failed login attempts per IP and per user
- Automatic lockout after N failed attempts
- Configurable lockout duration
- Audit logging for security monitoring

Security best practices:
- OWASP rate limiting guidelines
- Progressive delays on failures
- IP + user combined tracking

Usage:
    from runtime.auth_rate_limiter import get_auth_rate_limiter

    limiter = get_auth_rate_limiter()

    # Before auth attempt
    if not await limiter.check_allowed(ip_address, username):
        raise HTTPException(429, "Too many failed attempts. Try again later.")

    # After failed auth
    await limiter.record_failure(ip_address, username)

    # After successful auth
    await limiter.record_success(ip_address, username)

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Auth Rate Limiter",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-20T00:30:00Z",
    "updated_at": "2026-01-20T00:30:00Z",
    "layer": "operations",
    "domain": "security",
    "module_name": "auth_rate_limiter",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["/api/auth/*"],
        "datasources": ["Redis"],
        "memory_layers": ["audit_log"],
        "imported_by": ["api.auth", "api.dependencies"],
    },
}
# ============================================================================

import structlog
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = structlog.get_logger(__name__)

# Try to import Redis client
try:
    from runtime.redis_client import get_redis_client

    _has_redis_client = True
except ImportError:
    _has_redis_client = False
    logger.debug("Redis client not available - using in-memory auth rate limiting")


@dataclass
class AuthRateLimitConfig:
    """Configuration for auth rate limiting."""

    # Failed attempt thresholds
    max_failures_per_ip: int = 10  # Max failures from single IP
    max_failures_per_user: int = 5  # Max failures for single user
    max_failures_combined: int = 5  # Max failures for IP+user combo

    # Lockout settings
    lockout_duration_seconds: int = 900  # 15 minutes
    window_seconds: int = 300  # 5 minute window for counting failures

    # Progressive delay (optional)
    enable_progressive_delay: bool = True
    base_delay_ms: int = 100  # Base delay after first failure
    max_delay_ms: int = 5000  # Max delay (5 seconds)


@dataclass
class AuthAttemptResult:
    """Result of checking auth rate limit."""

    allowed: bool
    reason: Optional[str] = None
    retry_after_seconds: Optional[int] = None
    failures_count: int = 0
    delay_ms: int = 0


class AuthRateLimiter:
    """
    Authentication-specific rate limiter.

    Tracks failed login attempts and enforces lockouts to prevent
    brute force and credential stuffing attacks.
    """

    def __init__(self, config: Optional[AuthRateLimitConfig] = None) -> None:
        """
        Initialize auth rate limiter.

        Args:
            config: Rate limit configuration (uses defaults if not provided)
        """
        self._config = config or AuthRateLimitConfig()
        self._redis_client = None
        self._redis_available = False

        # In-memory fallback storage
        self._ip_failures: dict[str, list[datetime]] = defaultdict(list)
        self._user_failures: dict[str, list[datetime]] = defaultdict(list)
        self._combined_failures: dict[str, list[datetime]] = defaultdict(list)
        self._lockouts: dict[str, datetime] = {}

        logger.info(
            "AuthRateLimiter initialized",
            max_failures_user=self._config.max_failures_per_user,
            lockout_duration=self._config.lockout_duration_seconds,
        )

    async def _ensure_redis(self) -> bool:
        """Ensure Redis client is connected."""
        if not _has_redis_client:
            return False

        if self._redis_client is None:
            self._redis_client = await get_redis_client()
            self._redis_available = (
                self._redis_client is not None and self._redis_client.is_available()
            )

        return self._redis_available

    async def check_allowed(
        self,
        ip_address: str,
        username: Optional[str] = None,
    ) -> AuthAttemptResult:
        """
        Check if an authentication attempt is allowed.

        Args:
            ip_address: Client IP address
            username: Username being authenticated (if known)

        Returns:
            AuthAttemptResult with allowed status and details
        """
        now = datetime.now(timezone.utc)

        # Check lockout first
        lockout_key = self._get_lockout_key(ip_address, username)
        lockout_until = await self._get_lockout(lockout_key)

        if lockout_until and lockout_until > now:
            retry_after = int((lockout_until - now).total_seconds())
            logger.warning(
                "Auth attempt blocked - lockout active",
                ip=ip_address,
                username=username,
                retry_after=retry_after,
            )
            return AuthAttemptResult(
                allowed=False,
                reason="Too many failed attempts. Account temporarily locked.",
                retry_after_seconds=retry_after,
            )

        # Count failures in window
        failures = await self._count_failures(ip_address, username)

        # Check thresholds
        if failures["ip"] >= self._config.max_failures_per_ip:
            await self._set_lockout(lockout_key)
            return AuthAttemptResult(
                allowed=False,
                reason="Too many failed attempts from this IP.",
                retry_after_seconds=self._config.lockout_duration_seconds,
                failures_count=failures["ip"],
            )

        if username and failures["user"] >= self._config.max_failures_per_user:
            await self._set_lockout(lockout_key)
            return AuthAttemptResult(
                allowed=False,
                reason="Too many failed attempts for this account.",
                retry_after_seconds=self._config.lockout_duration_seconds,
                failures_count=failures["user"],
            )

        if username and failures["combined"] >= self._config.max_failures_combined:
            await self._set_lockout(lockout_key)
            return AuthAttemptResult(
                allowed=False,
                reason="Too many failed attempts. Please try again later.",
                retry_after_seconds=self._config.lockout_duration_seconds,
                failures_count=failures["combined"],
            )

        # Calculate progressive delay
        delay_ms = 0
        if self._config.enable_progressive_delay and failures["combined"] > 0:
            delay_ms = min(
                self._config.base_delay_ms * (2 ** failures["combined"]),
                self._config.max_delay_ms,
            )

        return AuthAttemptResult(
            allowed=True,
            failures_count=failures["combined"],
            delay_ms=delay_ms,
        )

    async def record_failure(
        self,
        ip_address: str,
        username: Optional[str] = None,
    ) -> None:
        """
        Record a failed authentication attempt.

        Args:
            ip_address: Client IP address
            username: Username that failed authentication
        """
        now = datetime.now(timezone.utc)

        # Record to Redis if available
        if await self._ensure_redis():
            try:
                await self._redis_record_failure(ip_address, username, now)
                logger.info(
                    "Auth failure recorded",
                    ip=ip_address,
                    username=username,
                )
                return
            except Exception as e:
                logger.warning(f"Redis record_failure failed: {e}")

        # Fallback to in-memory
        self._ip_failures[ip_address].append(now)
        if username:
            self._user_failures[username].append(now)
            combined_key = f"{ip_address}:{username}"
            self._combined_failures[combined_key].append(now)

        logger.info(
            "Auth failure recorded (in-memory)",
            ip=ip_address,
            username=username,
        )

    async def record_success(
        self,
        ip_address: str,
        username: str,
    ) -> None:
        """
        Record a successful authentication (clears failure count for user).

        Args:
            ip_address: Client IP address
            username: Username that authenticated successfully
        """
        # Clear lockout
        lockout_key = self._get_lockout_key(ip_address, username)
        await self._clear_lockout(lockout_key)

        # Clear user failures (IP failures persist for DDoS protection)
        if await self._ensure_redis():
            try:
                await self._redis_clear_user_failures(username)
            except Exception:
                pass

        self._user_failures[username] = []
        combined_key = f"{ip_address}:{username}"
        self._combined_failures[combined_key] = []

        logger.info(
            "Auth success - cleared failure count",
            ip=ip_address,
            username=username,
        )

    async def _count_failures(
        self,
        ip_address: str,
        username: Optional[str],
    ) -> dict[str, int]:
        """Count failures in the current window."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self._config.window_seconds)

        # Try Redis first
        if await self._ensure_redis():
            try:
                return await self._redis_count_failures(ip_address, username)
            except Exception:
                pass

        # Fallback to in-memory
        ip_count = len([t for t in self._ip_failures[ip_address] if t > cutoff])
        user_count = 0
        combined_count = 0

        if username:
            user_count = len([t for t in self._user_failures[username] if t > cutoff])
            combined_key = f"{ip_address}:{username}"
            combined_count = len(
                [t for t in self._combined_failures[combined_key] if t > cutoff]
            )

        return {
            "ip": ip_count,
            "user": user_count,
            "combined": combined_count,
        }

    def _get_lockout_key(self, ip_address: str, username: Optional[str]) -> str:
        """Generate lockout key."""
        if username:
            return f"auth_lockout:{ip_address}:{username}"
        return f"auth_lockout:{ip_address}"

    async def _get_lockout(self, key: str) -> Optional[datetime]:
        """Get lockout expiry time."""
        if await self._ensure_redis():
            try:
                ttl = await self._redis_client.ttl(key)
                if ttl and ttl > 0:
                    return datetime.now(timezone.utc) + timedelta(seconds=ttl)
            except Exception:
                pass

        return self._lockouts.get(key)

    async def _set_lockout(self, key: str) -> None:
        """Set lockout for key."""
        lockout_until = datetime.now(timezone.utc) + timedelta(
            seconds=self._config.lockout_duration_seconds
        )

        if await self._ensure_redis():
            try:
                await self._redis_client.setex(
                    key,
                    self._config.lockout_duration_seconds,
                    "locked",
                )
            except Exception:
                pass

        self._lockouts[key] = lockout_until

        logger.warning(
            "Auth lockout set",
            key=key,
            duration=self._config.lockout_duration_seconds,
        )

    async def _clear_lockout(self, key: str) -> None:
        """Clear lockout for key."""
        if await self._ensure_redis():
            try:
                await self._redis_client.delete(key)
            except Exception:
                pass

        self._lockouts.pop(key, None)

    # Redis helper methods
    async def _redis_record_failure(
        self,
        ip_address: str,
        username: Optional[str],
        timestamp: datetime,
    ) -> None:
        """Record failure to Redis."""
        ts = timestamp.timestamp()

        # IP failures
        ip_key = f"auth_failures:ip:{ip_address}"
        await self._redis_client.zadd(ip_key, {str(ts): ts})
        await self._redis_client.expire(ip_key, self._config.window_seconds)

        if username:
            # User failures
            user_key = f"auth_failures:user:{username}"
            await self._redis_client.zadd(user_key, {str(ts): ts})
            await self._redis_client.expire(user_key, self._config.window_seconds)

            # Combined failures
            combined_key = f"auth_failures:combined:{ip_address}:{username}"
            await self._redis_client.zadd(combined_key, {str(ts): ts})
            await self._redis_client.expire(combined_key, self._config.window_seconds)

    async def _redis_count_failures(
        self,
        ip_address: str,
        username: Optional[str],
    ) -> dict[str, int]:
        """Count failures from Redis."""
        now = datetime.now(timezone.utc)
        cutoff = (now - timedelta(seconds=self._config.window_seconds)).timestamp()

        ip_key = f"auth_failures:ip:{ip_address}"
        ip_count = await self._redis_client.zcount(ip_key, cutoff, "+inf")

        user_count = 0
        combined_count = 0

        if username:
            user_key = f"auth_failures:user:{username}"
            user_count = await self._redis_client.zcount(user_key, cutoff, "+inf")

            combined_key = f"auth_failures:combined:{ip_address}:{username}"
            combined_count = await self._redis_client.zcount(
                combined_key, cutoff, "+inf"
            )

        return {
            "ip": ip_count or 0,
            "user": user_count or 0,
            "combined": combined_count or 0,
        }

    async def _redis_clear_user_failures(self, username: str) -> None:
        """Clear user failures from Redis."""
        user_key = f"auth_failures:user:{username}"
        await self._redis_client.delete(user_key)


# =============================================================================
# Singleton Instance
# =============================================================================

_auth_limiter_instance: Optional[AuthRateLimiter] = None


def get_auth_rate_limiter() -> AuthRateLimiter:
    """Get or create the auth rate limiter singleton."""
    global _auth_limiter_instance
    if _auth_limiter_instance is None:
        _auth_limiter_instance = AuthRateLimiter()
    return _auth_limiter_instance


__all__ = [
    "AuthRateLimiter",
    "AuthRateLimitConfig",
    "AuthAttemptResult",
    "get_auth_rate_limiter",
]


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-SECU-001",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["runtime.redis_client"],
    "tags": [
        "async",
        "auth",
        "rate-limiting",
        "security",
        "service",
    ],
    "keywords": [
        "auth",
        "brute-force",
        "lockout",
        "rate-limit",
        "security",
    ],
    "business_value": "Prevents brute force and credential stuffing attacks",
    "last_modified": "2026-01-20T00:30:00Z",
    "modified_by": "GMP-108",
    "change_summary": "Initial implementation of auth rate limiting",
}
# ============================================================================
