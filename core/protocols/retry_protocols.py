"""
core/protocols/retry_protocols.py

Comprehensive async retry protocol and handler for Python 3.12+ applications.
Supports multiple backoff strategies, configurable exception handling, and
structured logging via structlog.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Retry Protocols",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T08:48:24Z",
    "updated_at": "2026-01-25T08:58:45Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "retry_protocols",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API"],
        "memory_layers": [],
        "imported_by": ["core.protocols.__init__"],
    },
}
# ============================================================================

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import (
    Protocol,
    TypeVar,
    runtime_checkable,
)

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger()

T = TypeVar("T")
P = TypeVar("P")


class BackoffStrategy(str, Enum):
    """
    Enumeration of supported backoff strategies for retry delays.

    - CONSTANT: Fixed delay between retries
    - LINEAR: Delay increases linearly with attempt number
    - EXPONENTIAL: Delay increases exponentially with attempt number
    - JITTER: Exponential with randomized jitter to prevent thundering herd
    """

    CONSTANT = "constant"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    JITTER = "jitter"


@dataclass
class RetryPolicy:
    """
    Configuration for retry behavior across async operations.

    Attributes:
        max_retries: Maximum number of retry attempts (negative = infinite)
        initial_delay: Starting delay in seconds between retries
        max_delay: Maximum delay cap in seconds
        backoff_strategy: Strategy for computing delay between retries
        retry_on: Tuple of exception types to catch and retry on
        timeout: Optional timeout in seconds for the entire retry operation
    """

    max_retries: int = 3
    initial_delay: float = 0.1
    max_delay: float = 30.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    retry_on: tuple[type[Exception], ...] = field(default_factory=lambda: (Exception,))
    timeout: float | None = None

    def __post_init__(self) -> None:
        """Validate policy configuration."""
        if self.initial_delay < 0:
            raise ValueError("initial_delay must be non-negative")
        if self.max_delay < self.initial_delay:
            raise ValueError("max_delay must be >= initial_delay")
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("timeout must be positive")


@runtime_checkable
class RetryProtocol(Protocol):
    """
    Protocol defining the interface for retry handlers.

    Any class implementing this protocol can be used as a retry handler
    for async operations that need resilience against transient failures.
    """

    def __init__(self, policy: RetryPolicy) -> None:
        """
        Initialize the retry handler with a policy.

        Args:
            policy: RetryPolicy instance defining retry behavior
        """
        ...

    @must_stay_async("callers use await")
    async def execute_with_retry(
        self,
        coro_func: Callable[..., Awaitable[T]],
        *args: object,
        **kwargs: object,
    ) -> T:
        """
        Execute an async operation with automatic retry on failure.

        Args:
            coro_func: Async callable to execute
            *args: Positional arguments to pass to coro_func
            **kwargs: Keyword arguments to pass to coro_func

        Returns:
            Return value from successful execution of coro_func

        Raises:
            The last exception caught if all retries are exhausted
        """
        ...

    @must_stay_async("callers use await")
    async def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry attempt.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds before next retry
        """
        ...

    def should_retry(
        self,
        exception: Exception,
        attempt: int,
    ) -> bool:
        """
        Determine whether an exception should trigger a retry.

        Args:
            exception: The exception that was raised
            attempt: Current attempt number (1-indexed)

        Returns:
            True if operation should be retried, False otherwise
        """
        ...


class StandardRetryHandler:
    """
    Production-ready retry handler implementing RetryProtocol.

    Handles exponential backoff with optional jitter, structured logging,
    timeout enforcement, and configurable exception matching. Designed to
    work seamlessly with asyncio and modern Python 3.12+ syntax.
    """

    def __init__(self, policy: RetryPolicy) -> None:
        """
        Initialize retry handler with policy.

        Args:
            policy: RetryPolicy defining retry behavior
        """
        self.policy = policy
        self._attempt = 0

    @must_stay_async("callers use await")
    async def execute_with_retry(
        self,
        coro_func: Callable[..., Awaitable[T]],
        *args: object,
        **kwargs: object,
    ) -> T:
        """
        Execute async operation with automatic retry on configured exceptions.

        Implements the retry loop with exponential backoff, logging at each stage,
        and timeout enforcement. Respects the policy's max_retries configuration
        and only retries on exceptions in retry_on tuple.

        Args:
            coro_func: Async callable to execute
            *args: Positional arguments to pass to coro_func
            **kwargs: Keyword arguments to pass to coro_func

        Returns:
            Return value from successful execution of coro_func

        Raises:
            The last exception caught if all retries are exhausted or timeout occurs
            asyncio.TimeoutError: If overall operation exceeds timeout
        """
        self._attempt = 0

        async def _execute_with_timeout() -> T:
            """
            Performs an asynchronous execution of a coroutine with an optional timeout based on retry policy.
            Args:
                coro_func: The coroutine function to execute with retry logic.
                args: Positional arguments for the coroutine.
                kwargs: Keyword arguments for the coroutine.
                self: Instance containing the retry policy with timeout settings.
            Returns:
                The result of the coroutine execution if successful within the timeout.
            Raises:
                asyncio.TimeoutError: If the execution exceeds the specified timeout.
            """
            if self.policy.timeout:
                return await asyncio.wait_for(
                    coro_func(*args, **kwargs),
                    timeout=self.policy.timeout,
                )
            return await coro_func(*args, **kwargs)

        while True:
            self._attempt += 1

            try:
                logger.info(
                    "retry.attempt.start",
                    attempt=self._attempt,
                    function=getattr(coro_func, "__qualname__", str(coro_func)),
                )
                result = await _execute_with_timeout()

                if self._attempt > 1:
                    logger.info(
                        "retry.succeeded",
                        attempt=self._attempt,
                        function=getattr(coro_func, "__qualname__", str(coro_func)),
                    )

                return result

            except TimeoutError:
                logger.error(
                    "retry.timeout",
                    attempt=self._attempt,
                    timeout=self.policy.timeout,
                    function=getattr(coro_func, "__qualname__", str(coro_func)),
                )
                raise

            except Exception as e:
                if not self.should_retry(e, self._attempt):
                    logger.error(
                        "retry.not_retryable",
                        attempt=self._attempt,
                        exception_type=type(e).__name__,
                        function=getattr(coro_func, "__qualname__", str(coro_func)),
                    )
                    raise

                if (
                    self.policy.max_retries >= 0
                    and self._attempt > self.policy.max_retries
                ):
                    logger.error(
                        "retry.exhausted",
                        attempt=self._attempt,
                        max_retries=self.policy.max_retries,
                        exception_type=type(e).__name__,
                        function=getattr(coro_func, "__qualname__", str(coro_func)),
                    )
                    raise

                delay = await self.calculate_delay(self._attempt)

                logger.warning(
                    "retry.will_retry",
                    attempt=self._attempt,
                    exception_type=type(e).__name__,
                    delay_seconds=delay,
                    function=getattr(coro_func, "__qualname__", str(coro_func)),
                    exception_message=str(e),
                )

                await asyncio.sleep(delay)

    @must_stay_async("callers use await")
    async def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry using configured backoff strategy.

        Implements four strategies:
        - CONSTANT: Returns initial_delay regardless of attempt
        - LINEAR: Returns initial_delay * attempt (capped at max_delay)
        - EXPONENTIAL: Returns initial_delay * (2 ^ (attempt - 1)) (capped)
        - JITTER: Returns exponential with randomized jitter

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds, bounded by max_delay
        """
        match self.policy.backoff_strategy:
            case BackoffStrategy.CONSTANT:
                delay = self.policy.initial_delay

            case BackoffStrategy.LINEAR:
                delay = self.policy.initial_delay * attempt

            case BackoffStrategy.EXPONENTIAL:
                delay = self.policy.initial_delay * (2 ** (attempt - 1))

            case BackoffStrategy.JITTER:
                base_delay = self.policy.initial_delay * (2 ** (attempt - 1))
                jitter_amount = base_delay * (attempt % 3) / 3
                delay = base_delay + jitter_amount

        return min(delay, self.policy.max_delay)

    def should_retry(
        self,
        exception: Exception,
        attempt: int,
    ) -> bool:
        """
        Determine if exception should trigger retry based on policy.

        Checks if the exception type is in the policy's retry_on tuple.
        This respects exception inheritance, so catching BaseException will
        retry on any exception, while catching OSError will retry on
        ConnectionError, TimeoutError, etc.

        Args:
            exception: Exception instance to evaluate
            attempt: Current attempt number (1-indexed, for future extensibility)

        Returns:
            True if exception type matches retry_on policy
        """
        return isinstance(exception, self.policy.retry_on)


def with_retry(
    policy: RetryPolicy,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator for async functions to add automatic retry behavior.

    Wraps an async function with a StandardRetryHandler using the provided
    retry policy. The decorated function accepts the same arguments as the
    original and returns the same type, but gains retry resilience.

    Args:
        policy: RetryPolicy defining retry behavior

    Returns:
        Decorator function that wraps async callables

    Example:
        ```python
        default_policy = RetryPolicy(
            max_retries=3,
            initial_delay=0.1,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            retry_on=(ConnectionError, TimeoutError),
        )


        @with_retry(policy=default_policy)
        async def fetch_data(url: str) -> dict:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                return response.json()


        # Usage - retries automatically on ConfiguredError:
        data = await fetch_data("https://api.example.com/data")
        ```
    """

    def decorator(
        func: Callable[..., Awaitable[T]],
    ) -> Callable[..., Awaitable[T]]:
        """
        Performs asynchronous retry logic for Python 3.12+ applications using configurable backoff strategies and exception handling.

        Args:
            func: The asynchronous function to be decorated with retry capabilities.

        Returns:
            A wrapped asynchronous function that executes with retry logic applied.
        """

        @wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> T:
            """
            Performs asynchronous retry logic using configurable backoff strategies and exception handling for core protocol operations.

            Args:
                *args: Positional arguments for the wrapped function.
                **kwargs: Keyword arguments for the wrapped function.

            Returns:
                The result of the wrapped function after retry attempts.
            """
            handler = StandardRetryHandler(policy)
            return await handler.execute_with_retry(func, *args, **kwargs)

        # @wraps handles __name__, __qualname__, __doc__, __module__ automatically
        wrapper.__annotations__ = func.__annotations__

        return wrapper

    return decorator


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-115",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "data-models",
        "dataclass",
        "event-driven",
        "foundation",
        "handler",
        "logging",
        "messaging",
    ],
    "keywords": [
        "backoff",
        "calculate",
        "decorator",
        "delay",
        "execute",
        "fetch",
        "handler",
        "policy",
    ],
    "business_value": "Provides retry protocols components including BackoffStrategy, RetryPolicy, RetryProtocol",
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
