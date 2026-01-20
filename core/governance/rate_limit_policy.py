"""
L9 Unified Rate Limit Policy
=============================

Config-driven rate limiting across all L9 components.

Provides:
- @rate_limit("llm.openai") decorator
- RateLimitDep("memory.ingest") FastAPI dependency
- rate_limit_context("tools.high_risk") context manager
- Centralized config from config/policies/rate_limits.yaml

Usage:
    # Decorator
    @rate_limit("llm.openai")
    async def call_openai(prompt: str):
        ...

    # FastAPI Dependency
    @router.post("/ingest")
    async def ingest(_: None = Depends(RateLimitDep("memory.ingest"))):
        ...

    # Context Manager
    async with rate_limit_context("tools.high_risk", key="git_commit"):
        await execute_tool(...)

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Rate Limit Policy",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-20T01:00:00Z",
    "updated_at": "2026-01-20T01:00:00Z",
    "layer": "governance",
    "domain": "policy",
    "module_name": "rate_limit_policy",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["*"],
        "datasources": ["Redis", "config/policies/rate_limits.yaml"],
        "memory_layers": [],
        "imported_by": ["core.governance.__init__"],
    },
}
# ============================================================================

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

import structlog
import yaml
from fastapi import HTTPException, Request

logger = structlog.get_logger(__name__)

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


# =============================================================================
# Models
# =============================================================================


@dataclass
class RateLimitConfig:
    """Configuration for a single rate limit."""

    key: str
    limit: int
    window_seconds: int
    description: str = ""
    # Optional fields for specific limit types
    daily_limit: Optional[int] = None
    hourly_limit: Optional[int] = None
    requires_approval_after: Optional[int] = None


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    current_count: int
    limit: int
    remaining: int
    retry_after_seconds: Optional[int] = None
    key: str = ""


@dataclass
class RateLimitSettings:
    """Global rate limit settings."""

    default_window_seconds: int = 60
    enable_redis: bool = True
    fallback_to_memory: bool = True
    log_violations: bool = True
    emit_metrics: bool = True
    exempted_ips: list[str] = field(default_factory=list)
    exempted_caller_ids: list[str] = field(default_factory=list)


# =============================================================================
# Rate Limit Policy Service
# =============================================================================


class RateLimitPolicy:
    """
    Unified rate limit policy service.

    Loads configuration from YAML and provides rate limiting primitives.
    """

    _instance: Optional["RateLimitPolicy"] = None
    _config_path: str = "config/policies/rate_limits.yaml"

    def __init__(self) -> None:
        """Initialize the rate limit policy."""
        self._config: dict[str, Any] = {}
        self._settings = RateLimitSettings()
        self._limiter: Optional[Any] = None
        self._loaded = False

    @classmethod
    def get_instance(cls) -> "RateLimitPolicy":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_loaded(self) -> None:
        """Ensure configuration is loaded."""
        if self._loaded:
            return

        config_path = Path(self._config_path)
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f)
                self._config = data.get("rate_limits", {})
                settings_data = data.get("settings", {})
                exemptions = data.get("exemptions", {})

                self._settings = RateLimitSettings(
                    default_window_seconds=settings_data.get(
                        "default_window_seconds", 60
                    ),
                    enable_redis=settings_data.get("enable_redis", True),
                    fallback_to_memory=settings_data.get("fallback_to_memory", True),
                    log_violations=settings_data.get("log_violations", True),
                    emit_metrics=settings_data.get("emit_metrics", True),
                    exempted_ips=exemptions.get("ips", []),
                    exempted_caller_ids=exemptions.get("caller_ids", []),
                )

            logger.info(
                "RateLimitPolicy loaded",
                categories=list(self._config.keys()),
            )
        else:
            logger.warning(f"Rate limit config not found: {config_path}")

        self._loaded = True

    def _get_limiter(self) -> Any:
        """Get or create the underlying rate limiter."""
        if self._limiter is None:
            try:
                from runtime.rate_limiter import RateLimiter

                self._limiter = RateLimiter(
                    window_seconds=self._settings.default_window_seconds,
                    use_redis=self._settings.enable_redis,
                )
            except ImportError:
                logger.warning("RateLimiter not available, using stub")
                self._limiter = _StubRateLimiter()

        return self._limiter

    def get_config(self, policy_key: str) -> Optional[RateLimitConfig]:
        """
        Get rate limit configuration for a policy key.

        Args:
            policy_key: Dot-separated key (e.g., "llm.openai", "memory.ingest")

        Returns:
            RateLimitConfig or None if not found
        """
        self._ensure_loaded()

        parts = policy_key.split(".")
        config = self._config

        for part in parts:
            if isinstance(config, dict) and part in config:
                config = config[part]
            else:
                return None

        if not isinstance(config, dict):
            return None

        # Extract limit and window
        # Check per-minute limits first, then per-hour, then per-day
        limit = (
            config.get("requests_per_minute")
            or config.get("calls_per_minute")
            or config.get("packets_per_minute")
            or config.get("queries_per_minute")
            or config.get("messages_per_minute")
            or config.get("tasks_per_minute")
            or config.get("max_failures_per_ip")
            or config.get("max_failures_per_user")
            or config.get("max_connections")
            or config.get("max_concurrent")
        )

        # If no per-minute limit, check per-hour
        if limit is None:
            limit = config.get("calls_per_hour") or config.get("requests_per_hour")

        # Default
        if limit is None:
            limit = 100

        window = config.get("window_seconds", self._settings.default_window_seconds)

        return RateLimitConfig(
            key=policy_key,
            limit=limit,
            window_seconds=window,
            description=config.get("description", ""),
            daily_limit=config.get("calls_per_day") or config.get("requests_per_day"),
            hourly_limit=config.get("calls_per_hour")
            or config.get("requests_per_hour"),
            requires_approval_after=config.get("requires_approval_after"),
        )

    def is_exempted(
        self,
        ip_address: Optional[str] = None,
        caller_id: Optional[str] = None,
    ) -> bool:
        """Check if request is exempted from rate limiting."""
        self._ensure_loaded()

        if ip_address and ip_address in self._settings.exempted_ips:
            return True

        if caller_id and caller_id in self._settings.exempted_caller_ids:
            return True

        return False

    async def check(
        self,
        policy_key: str,
        unique_key: Optional[str] = None,
    ) -> RateLimitResult:
        """
        Check if request is within rate limit.

        Args:
            policy_key: Policy key (e.g., "llm.openai")
            unique_key: Optional unique key for tracking (e.g., user_id, ip)

        Returns:
            RateLimitResult with allowed status
        """
        config = self.get_config(policy_key)
        if not config:
            # No config = allow
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=0,
                remaining=0,
                key=policy_key,
            )

        # Build rate limit key
        rate_key = f"policy:{policy_key}"
        if unique_key:
            rate_key = f"{rate_key}:{unique_key}"

        limiter = self._get_limiter()
        current = await limiter.get_usage(rate_key)
        remaining = max(0, config.limit - current)

        if current >= config.limit:
            if self._settings.log_violations:
                logger.warning(
                    "Rate limit exceeded",
                    policy=policy_key,
                    current=current,
                    limit=config.limit,
                    unique_key=unique_key,
                )

            return RateLimitResult(
                allowed=False,
                current_count=current,
                limit=config.limit,
                remaining=0,
                retry_after_seconds=config.window_seconds,
                key=policy_key,
            )

        return RateLimitResult(
            allowed=True,
            current_count=current,
            limit=config.limit,
            remaining=remaining,
            key=policy_key,
        )

    async def increment(
        self,
        policy_key: str,
        unique_key: Optional[str] = None,
    ) -> bool:
        """
        Increment the rate limit counter.

        Args:
            policy_key: Policy key
            unique_key: Optional unique key

        Returns:
            True if allowed, False if rate limited
        """
        config = self.get_config(policy_key)
        if not config:
            return True

        rate_key = f"policy:{policy_key}"
        if unique_key:
            rate_key = f"{rate_key}:{unique_key}"

        limiter = self._get_limiter()
        return await limiter.check_and_increment(rate_key, config.limit)

    async def check_and_increment(
        self,
        policy_key: str,
        unique_key: Optional[str] = None,
    ) -> RateLimitResult:
        """
        Check rate limit and increment if allowed.

        Args:
            policy_key: Policy key
            unique_key: Optional unique key

        Returns:
            RateLimitResult with status
        """
        result = await self.check(policy_key, unique_key)
        if result.allowed:
            await self.increment(policy_key, unique_key)
            result.current_count += 1
            result.remaining -= 1

        return result


class _StubRateLimiter:
    """Stub rate limiter when real one isn't available."""

    async def get_usage(self, key: str) -> int:
        return 0

    async def check_and_increment(self, key: str, limit: int) -> bool:
        return True


# =============================================================================
# Decorator
# =============================================================================


def rate_limit(
    policy_key: str,
    unique_key_extractor: Optional[Callable[..., str]] = None,
) -> Callable[[F], F]:
    """
    Decorator to apply rate limiting to a function.

    Args:
        policy_key: Policy key from rate_limits.yaml (e.g., "llm.openai")
        unique_key_extractor: Optional function to extract unique key from args

    Usage:
        @rate_limit("llm.openai")
        async def call_openai(prompt: str):
            ...

        @rate_limit("memory.ingest", lambda packet: packet.source_id)
        async def ingest_packet(packet: PacketEnvelope):
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            policy = RateLimitPolicy.get_instance()

            # Extract unique key if extractor provided
            unique_key = None
            if unique_key_extractor:
                try:
                    unique_key = unique_key_extractor(*args, **kwargs)
                except Exception:
                    pass

            # Check rate limit
            result = await policy.check_and_increment(policy_key, unique_key)

            if not result.allowed:
                raise RateLimitExceeded(
                    policy_key=policy_key,
                    retry_after=result.retry_after_seconds or 60,
                )

            return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


# =============================================================================
# FastAPI Dependency
# =============================================================================


class RateLimitDep:
    """
    FastAPI dependency for rate limiting.

    Usage:
        @router.post("/ingest")
        async def ingest(
            request: Request,
            _: None = Depends(RateLimitDep("memory.ingest")),
        ):
            ...
    """

    def __init__(
        self,
        policy_key: str,
        use_ip: bool = True,
        use_caller_id: bool = False,
    ) -> None:
        """
        Initialize rate limit dependency.

        Args:
            policy_key: Policy key from config
            use_ip: Include client IP in unique key
            use_caller_id: Include caller ID in unique key (requires auth)
        """
        self._policy_key = policy_key
        self._use_ip = use_ip
        self._use_caller_id = use_caller_id

    async def __call__(self, request: Request) -> None:
        """Execute rate limit check."""
        policy = RateLimitPolicy.get_instance()

        # Build unique key
        unique_parts = []

        if self._use_ip:
            ip = self._get_client_ip(request)
            if ip:
                # Check exemption
                if policy.is_exempted(ip_address=ip):
                    return
                unique_parts.append(ip)

        if self._use_caller_id:
            caller_id = getattr(request.state, "caller_id", None)
            if caller_id:
                if policy.is_exempted(caller_id=caller_id):
                    return
                unique_parts.append(caller_id)

        unique_key = ":".join(unique_parts) if unique_parts else None

        # Check rate limit
        result = await policy.check_and_increment(self._policy_key, unique_key)

        if not result.allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded for {self._policy_key}",
                headers={"Retry-After": str(result.retry_after_seconds or 60)},
            )

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        if request.client:
            return request.client.host

        return None


# =============================================================================
# Context Manager
# =============================================================================


@asynccontextmanager
async def rate_limit_context(
    policy_key: str,
    unique_key: Optional[str] = None,
):
    """
    Async context manager for rate limiting.

    Usage:
        async with rate_limit_context("tools.high_risk", key="git_commit"):
            await execute_tool(...)

    Raises:
        RateLimitExceeded: If rate limit is exceeded
    """
    policy = RateLimitPolicy.get_instance()
    result = await policy.check_and_increment(policy_key, unique_key)

    if not result.allowed:
        raise RateLimitExceeded(
            policy_key=policy_key,
            retry_after=result.retry_after_seconds or 60,
        )

    try:
        yield result
    finally:
        pass  # Could add cleanup or metrics here


# =============================================================================
# Exceptions
# =============================================================================


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, policy_key: str, retry_after: int) -> None:
        self.policy_key = policy_key
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded for {policy_key}. Retry after {retry_after}s"
        )


# =============================================================================
# Convenience Functions
# =============================================================================


def get_rate_limit_policy() -> RateLimitPolicy:
    """Get the rate limit policy singleton."""
    return RateLimitPolicy.get_instance()


async def check_rate_limit(
    policy_key: str,
    unique_key: Optional[str] = None,
) -> RateLimitResult:
    """
    Check rate limit for a policy.

    Args:
        policy_key: Policy key (e.g., "llm.openai")
        unique_key: Optional unique identifier

    Returns:
        RateLimitResult
    """
    policy = RateLimitPolicy.get_instance()
    return await policy.check(policy_key, unique_key)


__all__ = [
    # Service
    "RateLimitPolicy",
    "get_rate_limit_policy",
    # Models
    "RateLimitConfig",
    "RateLimitResult",
    "RateLimitSettings",
    # Decorator
    "rate_limit",
    # Dependency
    "RateLimitDep",
    # Context Manager
    "rate_limit_context",
    # Functions
    "check_rate_limit",
    # Exceptions
    "RateLimitExceeded",
]


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "GOV-POLI-002",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["runtime.rate_limiter"],
    "tags": [
        "async",
        "config",
        "decorator",
        "fastapi",
        "governance",
        "policy",
        "rate-limiting",
    ],
    "keywords": [
        "config",
        "decorator",
        "dependency",
        "policy",
        "rate-limit",
        "unified",
    ],
    "business_value": "Unified config-driven rate limiting across all L9 components",
    "last_modified": "2026-01-20T01:00:00Z",
    "modified_by": "GMP-109",
    "change_summary": "Initial implementation of unified rate limit policy",
}
# ============================================================================
