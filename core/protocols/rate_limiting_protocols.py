"""
Rate limiting protocols and implementation for async-first Python 3.12+ codebases.

This module provides a type-safe, structlog-integrated rate limiting system with
support for multiple limiting strategies (fixed window, sliding window, token bucket,
and leaky bucket algorithms).

Module: core/protocols/rate_limiting_protocols.py
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Rate Limiting Protocols",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T08:48:24Z",
    "updated_at": "2026-01-25T08:58:45Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "rate_limiting_protocols",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.protocols.__init__"],
    },
}
# ============================================================================

import asyncio
import time
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Protocol

import structlog

logger = structlog.get_logger()


class RateLimitStrategy(str, Enum):
    """Rate limiting strategy algorithms.

    Attributes:
        FIXED_WINDOW: Simple fixed time window. Allows max_requests in each window.
        SLIDING_WINDOW: More accurate sliding window counter approach.
        TOKEN_BUCKET: Token bucket algorithm allowing burst capacity.
        LEAKY_BUCKET: Leaky bucket algorithm for smooth rate limiting.
    """

    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitPolicy:
    """Rate limiting configuration policy.

    Attributes:
        max_requests: Maximum number of requests allowed within the window.
        window_seconds: Time window in seconds for the rate limit.
        strategy: The rate limiting strategy to use.
        burst_size: Maximum burst capacity (used by token/leaky bucket algorithms).

    Example:
        >>> policy = RateLimitPolicy(
        ...     max_requests=100,
        ...     window_seconds=60,
        ...     strategy=RateLimitStrategy.TOKEN_BUCKET,
        ...     burst_size=150,
        ... )
    """

    max_requests: int
    window_seconds: float
    strategy: RateLimitStrategy
    burst_size: int = 0

    def __post_init__(self) -> None:
        """Validate policy configuration."""
        if self.max_requests < 1:
            raise ValueError("max_requests must be at least 1")
        if self.window_seconds < 0.001:
            raise ValueError("window_seconds must be greater than 0.001")
        if self.burst_size < 0:
            raise ValueError("burst_size cannot be negative")
        if self.burst_size == 0:
            self.burst_size = self.max_requests


class RateLimitingProtocol(Protocol):
    """Protocol defining the interface for rate limiters.

    This protocol establishes the contract that all rate limiter implementations
    must follow, ensuring type safety and interchangeability.
    """

    async def acquire(self, key: str, amount: int = 1) -> bool:
        """Attempt to acquire tokens for the given key.

        Args:
            key: Unique identifier for the rate limit bucket.
            amount: Number of tokens to acquire (default: 1).

        Returns:
            True if tokens were acquired, False if rate limit exceeded.

        Example:
            >>> limiter: RateLimitingProtocol = StandardRateLimiter(policy)
            >>> acquired = await limiter.acquire("user:123", amount=1)
            >>> if not acquired:
            ...     raise RateLimitExceededError()
        """
        ...

    async def wait_for_token(self, key: str, amount: int = 1) -> None:
        """Wait until tokens are available, then acquire them.

        Blocks asynchronously until the specified number of tokens can be
        acquired for the given key.

        Args:
            key: Unique identifier for the rate limit bucket.
            amount: Number of tokens to acquire (default: 1).

        Raises:
            asyncio.CancelledError: If the wait is cancelled.

        Example:
            >>> await limiter.wait_for_token("user:123")
            >>> await process_request()
        """
        ...

    def get_remaining(self, key: str) -> int:
        """Get the number of remaining tokens for a key.

        Args:
            key: Unique identifier for the rate limit bucket.

        Returns:
            Number of tokens remaining (non-negative integer).

        Example:
            >>> remaining = limiter.get_remaining("user:123")
            >>> logger.info("requests_remaining", remaining=remaining)
        """
        ...

    def get_reset_time(self, key: str) -> datetime:
        """Get when the rate limit resets for a key.

        Args:
            key: Unique identifier for the rate limit bucket.

        Returns:
            UTC datetime when the current window resets.

        Example:
            >>> reset = limiter.get_reset_time("user:123")
            >>> seconds_until_reset = (
            ...     reset - datetime.now(timezone.utc)
            ... ).total_seconds()
        """
        ...


class StandardRateLimiter:
    """Thread-safe, in-memory rate limiter with multiple strategy support.

    Implements the RateLimitingProtocol using asyncio-safe in-memory storage
    with support for fixed window, sliding window, token bucket, and leaky
    bucket algorithms.

    Attributes:
        policy: The RateLimitPolicy governing this limiter.

    Example:
        >>> from datetime import timezone
        >>> policy = RateLimitPolicy(
        ...     max_requests=100,
        ...     window_seconds=60,
        ...     strategy=RateLimitStrategy.TOKEN_BUCKET,
        ...     burst_size=150,
        ... )
        >>> limiter = StandardRateLimiter(policy)
        >>> # Acquire tokens without waiting
        >>> if await limiter.acquire("api_key:user123", amount=5):
        ...     await process_request()
        >>> else:
        ...     raise RateLimitExceededError()
        >>> # Or wait for tokens to become available
        >>> await limiter.wait_for_token("api_key:user123", amount=1)
        >>> await process_request()
    """

    def __init__(self, policy: RateLimitPolicy) -> None:
        """Initialize the rate limiter.

        Args:
            policy: The RateLimitPolicy to enforce.
        """
        self.policy = policy
        self._lock = asyncio.Lock()

        # Strategy-specific state storage
        self._fixed_window_state: dict[str, tuple[int, float]] = defaultdict(
            lambda: (0, time.monotonic())
        )
        self._sliding_window_state: dict[str, list[float]] = defaultdict(list)
        self._token_bucket_state: dict[str, tuple[float, float]] = defaultdict(
            lambda: (
                float(self.policy.burst_size),
                time.monotonic(),
            )  # nosemgrep: l9-float-requires-try-except
        )
        self._leaky_bucket_state: dict[str, tuple[float, float]] = defaultdict(
            lambda: (0.0, time.monotonic())
        )

    async def acquire(self, key: str, amount: int = 1) -> bool:
        """Attempt to acquire tokens without waiting.

        Args:
            key: Unique identifier for the rate limit bucket.
            amount: Number of tokens to acquire (default: 1).

        Returns:
            True if tokens were acquired, False if rate limit exceeded.
        """
        async with self._lock:
            if self.policy.strategy == RateLimitStrategy.FIXED_WINDOW:
                return self._acquire_fixed_window(key, amount)
            if self.policy.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return self._acquire_sliding_window(key, amount)
            if self.policy.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return self._acquire_token_bucket(key, amount)
            if self.policy.strategy == RateLimitStrategy.LEAKY_BUCKET:
                return self._acquire_leaky_bucket(key, amount)
            msg = f"Unknown strategy: {self.policy.strategy}"
            raise ValueError(msg)

    async def wait_for_token(self, key: str, amount: int = 1) -> None:
        """Wait until tokens are available, then acquire them.

        Args:
            key: Unique identifier for the rate limit bucket.
            amount: Number of tokens to acquire (default: 1).
        """
        logger.debug(
            "wait_for_token_start",
            key=key,
            amount=amount,
            strategy=self.policy.strategy.value,
        )

        while not await self.acquire(key, amount):
            wait_time = self._calculate_wait_time(key)
            logger.debug(
                "rate_limit_waiting",
                key=key,
                wait_seconds=wait_time,
            )
            await asyncio.sleep(wait_time)

        logger.debug("wait_for_token_acquired", key=key, amount=amount)

    def get_remaining(self, key: str) -> int:
        """Get the number of remaining tokens for a key.

        Args:
            key: Unique identifier for the rate limit bucket.

        Returns:
            Number of tokens remaining (non-negative integer).
        """
        if self.policy.strategy == RateLimitStrategy.FIXED_WINDOW:
            count, window_start = self._fixed_window_state[key]
            elapsed = time.monotonic() - window_start
            if elapsed >= self.policy.window_seconds:
                return self.policy.max_requests
            return max(0, self.policy.max_requests - count)

        if self.policy.strategy == RateLimitStrategy.SLIDING_WINDOW:
            now = time.monotonic()
            cutoff = now - self.policy.window_seconds
            request_times = self._sliding_window_state[key]
            valid_requests = [t for t in request_times if t > cutoff]
            return max(0, self.policy.max_requests - len(valid_requests))

        if self.policy.strategy == RateLimitStrategy.TOKEN_BUCKET:
            tokens, last_update = self._token_bucket_state[key]
            elapsed = time.monotonic() - last_update
            refill_rate = self.policy.max_requests / self.policy.window_seconds
            tokens = min(
                self.policy.burst_size,
                tokens + elapsed * refill_rate,
            )
            return int(tokens)

        if self.policy.strategy == RateLimitStrategy.LEAKY_BUCKET:
            water, last_leak = self._leaky_bucket_state[key]
            elapsed = time.monotonic() - last_leak
            leak_rate = self.policy.max_requests / self.policy.window_seconds
            water = max(0.0, water - elapsed * leak_rate)
            return max(0, int(self.policy.burst_size - water))

        return 0

    def get_reset_time(self, key: str) -> datetime:
        """Get when the rate limit resets for a key.

        Args:
            key: Unique identifier for the rate limit bucket.

        Returns:
            UTC datetime when the current window resets.
        """
        if self.policy.strategy == RateLimitStrategy.FIXED_WINDOW:
            _, window_start = self._fixed_window_state[key]
            reset_timestamp = window_start + self.policy.window_seconds

        elif self.policy.strategy == RateLimitStrategy.SLIDING_WINDOW:
            request_times = self._sliding_window_state[key]
            if request_times:
                oldest_request = min(request_times)
                reset_timestamp = oldest_request + self.policy.window_seconds
            else:
                reset_timestamp = time.monotonic() + self.policy.window_seconds

        elif self.policy.strategy == RateLimitStrategy.TOKEN_BUCKET:
            _, last_update = self._token_bucket_state[key]
            reset_timestamp = last_update + self.policy.window_seconds

        elif self.policy.strategy == RateLimitStrategy.LEAKY_BUCKET:
            _, last_leak = self._leaky_bucket_state[key]
            reset_timestamp = last_leak + self.policy.window_seconds

        else:
            reset_timestamp = time.monotonic() + self.policy.window_seconds

        return datetime.fromtimestamp(reset_timestamp)

    def _acquire_fixed_window(self, key: str, amount: int) -> bool:
        """Acquire tokens using fixed window strategy.

        Args:
            key: Unique identifier for the rate limit bucket.
            amount: Number of tokens to acquire.

        Returns:
            True if acquisition succeeded, False otherwise.
        """
        count, window_start = self._fixed_window_state[key]
        elapsed = time.monotonic() - window_start

        if elapsed >= self.policy.window_seconds:
            self._fixed_window_state[key] = (amount, time.monotonic())
            return amount <= self.policy.max_requests

        if count + amount <= self.policy.max_requests:
            self._fixed_window_state[key] = (count + amount, window_start)
            return True

        return False

    def _acquire_sliding_window(self, key: str, amount: int) -> bool:
        """Acquire tokens using sliding window strategy.

        Args:
            key: Unique identifier for the rate limit bucket.
            amount: Number of tokens to acquire.

        Returns:
            True if acquisition succeeded, False otherwise.
        """
        now = time.monotonic()
        cutoff = now - self.policy.window_seconds
        request_times = self._sliding_window_state[key]

        valid_requests = [t for t in request_times if t > cutoff]

        if len(valid_requests) + amount <= self.policy.max_requests:
            valid_requests.extend([now] * amount)
            self._sliding_window_state[key] = valid_requests
            return True

        return False

    def _acquire_token_bucket(self, key: str, amount: int) -> bool:
        """Acquire tokens using token bucket strategy.

        Allows for burst capacity while maintaining a sustainable rate.

        Args:
            key: Unique identifier for the rate limit bucket.
            amount: Number of tokens to acquire.

        Returns:
            True if acquisition succeeded, False otherwise.
        """
        tokens, last_update = self._token_bucket_state[key]
        now = time.monotonic()
        elapsed = now - last_update

        refill_rate = self.policy.max_requests / self.policy.window_seconds
        tokens = min(self.policy.burst_size, tokens + elapsed * refill_rate)

        if tokens >= amount:
            tokens -= amount
            self._token_bucket_state[key] = (tokens, now)
            return True

        self._token_bucket_state[key] = (tokens, now)
        return False

    def _acquire_leaky_bucket(self, key: str, amount: int) -> bool:
        """Acquire tokens using leaky bucket strategy.

        Ensures smooth rate limiting with capacity limits.

        Args:
            key: Unique identifier for the rate limit bucket.
            amount: Number of tokens to acquire.

        Returns:
            True if acquisition succeeded, False otherwise.
        """
        water, last_leak = self._leaky_bucket_state[key]
        now = time.monotonic()
        elapsed = now - last_leak

        leak_rate = self.policy.max_requests / self.policy.window_seconds
        water = max(0.0, water - elapsed * leak_rate)

        if water + amount <= self.policy.burst_size:
            water += amount
            self._leaky_bucket_state[key] = (water, now)
            return True

        self._leaky_bucket_state[key] = (water, now)
        return False

    def _calculate_wait_time(self, key: str) -> float:
        """Calculate optimal wait time before next token availability.

        Args:
            key: Unique identifier for the rate limit bucket.

        Returns:
            Seconds to wait before retrying (minimum 0.01).
        """
        if self.policy.strategy == RateLimitStrategy.TOKEN_BUCKET:
            tokens, _last_update = self._token_bucket_state[key]
            refill_rate = self.policy.max_requests / self.policy.window_seconds
            if refill_rate > 0:
                tokens_needed = 1 - tokens
                wait = tokens_needed / refill_rate
                return max(0.01, wait)

        return min(0.1, self.policy.window_seconds / self.policy.max_requests)


def rate_limited(
    key_func: Callable[..., str],
    policy: RateLimitPolicy,
) -> Callable[
    [Callable[..., Coroutine[Any, Any, Any]]], Callable[..., Coroutine[Any, Any, Any]]
]:
    """Decorator for applying rate limiting to async functions.

    Applies rate limiting to async functions with customizable key extraction
    and policy application. Returns HTTP 429 status context information.

    Args:
        key_func: Function that extracts the rate limit key from function args.
                 Receives the same *args and **kwargs as the decorated function.
        policy: The RateLimitPolicy to enforce.

    Returns:
        Decorated async function with rate limiting applied.

    Raises:
        RateLimitExceededError: If rate limit is exceeded.

    Example:
        >>> def extract_user_key(request, *args, **kwargs) -> str:
        ...     return f"user:{request.user_id}"
        >>> policy = RateLimitPolicy(
        ...     max_requests=100,
        ...     window_seconds=60,
        ...     strategy=RateLimitStrategy.TOKEN_BUCKET,
        ...     burst_size=150,
        ... )
        >>> @rate_limited(extract_user_key, policy)
        >>> async def handle_api_request(request):
        ...     return await process_request(request)
    """
    limiter = StandardRateLimiter(policy)

    def decorator(
        func: Callable[..., Coroutine[Any, Any, Any]],
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        """Inner decorator wrapping the async function.

        Args:
            func: The async function to decorate.

        Returns:
            Wrapped async function with rate limiting.
        """

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Rate-limited function wrapper.

            Args:
                *args: Positional arguments for the decorated function.
                **kwargs: Keyword arguments for the decorated function.

            Returns:
                Return value from the decorated function.

            Raises:
                RateLimitExceededError: If rate limit exceeded.
            """
            key = key_func(*args, **kwargs)

            logger.debug(
                "rate_limit_check",
                function=func.__name__,
                key=key,
            )

            if not await limiter.acquire(key):
                remaining = limiter.get_remaining(key)
                reset_time = limiter.get_reset_time(key)

                logger.warning(
                    "rate_limit_exceeded",
                    function=func.__name__,
                    key=key,
                    remaining=remaining,
                    reset_time=reset_time.isoformat(),
                )

                msg = f"Rate limit exceeded for key: {key}"
                raise RateLimitExceededError(
                    message=msg,
                    remaining=remaining,
                    reset_time=reset_time,
                )

            try:
                result = await func(*args, **kwargs)
                logger.debug(
                    "rate_limited_function_executed",
                    function=func.__name__,
                    key=key,
                    remaining=limiter.get_remaining(key),
                )
                return result
            except Exception as exc:
                logger.exception(
                    "rate_limited_function_error",
                    function=func.__name__,
                    key=key,
                    error=str(exc),
                )
                raise

        return wrapper

    return decorator


class RateLimitExceededError(Exception):
    """Exception raised when rate limit is exceeded.

    Attributes:
        message: Human-readable error message.
        remaining: Number of requests remaining in current window.
        reset_time: UTC datetime when the rate limit resets.

    Example:
        >>> try:
        ...     await limiter.wait_for_token("user:123")
        ... except RateLimitExceededError as e:
        ...     logger.info(
        ...         "rate_limit_hit",
        ...         reset_time=e.reset_time.isoformat(),
        ...         remaining=e.remaining,
        ...     )
    """

    def __init__(
        self,
        message: str,
        remaining: int = 0,
        reset_time: datetime | None = None,
    ) -> None:
        """Initialize RateLimitExceededError exception.

        Args:
            message: Error message.
            remaining: Tokens remaining (default: 0).
            reset_time: When limit resets (default: None).
        """
        super().__init__(message)
        self.message = message
        self.remaining = remaining
        self.reset_time = reset_time


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-123",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "data-models",
        "dataclass",
        "debugging",
        "foundation",
        "logging",
        "messaging",
    ],
    "keywords": [
        "acquire",
        "api",
        "bucket",
        "decorator",
        "exceeded",
        "extract",
        "handle",
        "limit",
    ],
    "business_value": "This module provides a type-safe, structlog-integrated rate limiting system with support for multiple limiting strategies (fixed window, sliding window, token bucket, and leaky bucket algorithms). Mod",
    "last_modified": "2026-01-25T08:58:45Z",
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
