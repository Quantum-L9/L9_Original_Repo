# ============================================================================
__dora_meta__ = {
    "component_name": "Connection Protocols",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T08:48:24Z",
    "updated_at": "2026-01-25T08:58:45Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "connection_protocols",
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

# core/protocols/connection_protocols.py
"""
L9 Connection Management Protocol Implementation

Production-ready async connection pooling with automatic health checks,
connection recycling, and comprehensive metrics tracking.
"""

import asyncio
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol

import structlog

logger = structlog.get_logger(__name__)


class ConnectionState(Enum):
    """Enumeration of connection lifecycle states."""

    IDLE = "idle"
    ACTIVE = "active"
    CLOSED = "closed"
    ERROR = "error"


class ConnectionProtocol(Protocol):
    """Protocol defining the interface for managed connections."""

    async def execute(self, query: str, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a query against the connection.

        Args:
            query: The query string or command to execute.
            *args: Positional arguments for the query.
            **kwargs: Keyword arguments for the query.

        Returns:
            The result of the query execution.

        Raises:
            Exception: If query execution fails.
        """
        ...

    async def health_check(self) -> bool:
        """
        Verify the connection is healthy and responsive.

        Returns:
            True if the connection is healthy, False otherwise.
        """
        ...

    async def close(self) -> None:
        """Close the connection gracefully."""
        ...


class ConnectionPoolProtocol(Protocol):
    """Protocol defining the interface for connection pools."""

    async def acquire(self) -> AsyncGenerator[ConnectionProtocol, None]:
        """
        Acquire a connection from the pool as an async context manager.

        Yields:
            A managed connection from the pool.

        Raises:
            RuntimeError: If no connections are available after timeout.
        """
        ...

    async def release(self, connection: ConnectionProtocol) -> None:
        """
        Release a connection back to the pool.

        Args:
            connection: The connection to release.
        """
        ...

    async def health_check(self) -> dict[str, int]:
        """
        Perform health checks on all connections in the pool.

        Returns:
            Dictionary with health check metrics.
        """
        ...

    async def close(self) -> None:
        """Close all connections in the pool."""
        ...


@dataclass
class PooledConnection:
    """Internal wrapper for pooled connections with metadata."""

    connection: ConnectionProtocol
    state: ConnectionState = ConnectionState.IDLE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_used_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    use_count: int = 0
    error_count: int = 0

    def mark_active(self) -> None:
        """Mark this connection as active."""
        self.state = ConnectionState.ACTIVE
        self.last_used_at = datetime.now(UTC)
        self.use_count += 1

    def mark_idle(self) -> None:
        """Mark this connection as idle."""
        self.state = ConnectionState.IDLE
        self.last_used_at = datetime.now(UTC)

    def mark_error(self) -> None:
        """Mark this connection as having an error."""
        self.state = ConnectionState.ERROR
        self.error_count += 1

    def age_seconds(self) -> float:
        """Get the age of this connection in seconds."""
        return (datetime.now(UTC) - self.created_at).total_seconds()

    def idle_seconds(self) -> float:
        """Get the idle time of this connection in seconds."""
        return (datetime.now(UTC) - self.last_used_at).total_seconds()


class StandardConnectionPool:
    """
    Production-ready async connection pool with automatic health checks,
    connection recycling, and comprehensive metrics.

    This implementation provides:
    - Efficient connection reuse with FIFO acquisition
    - Automatic background health checks
    - Connection recycling based on age and error rates
    - Thread-safe metrics tracking
    - Graceful shutdown with cleanup
    """

    def __init__(
        self,
        create_connection: Callable[[], Awaitable[ConnectionProtocol]],
        max_size: int = 20,
        min_size: int = 5,
        health_check_interval: int = 60,
        connection_max_age: int = 3600,
        connection_max_idle: int = 300,
        acquire_timeout: float = 30.0,
    ) -> None:
        """
        Initialize the connection pool.

        Args:
            create_connection: Async callable that creates a new connection.
            max_size: Maximum number of connections in the pool. Defaults to 20.
            min_size: Minimum number of connections to maintain. Defaults to 5.
            health_check_interval: Seconds between health checks. Defaults to 60.
            connection_max_age: Maximum age of a connection in seconds. Defaults to 3600.
            connection_max_idle: Maximum idle time for a connection in seconds. Defaults to 300.
            acquire_timeout: Timeout for acquiring a connection in seconds. Defaults to 30.0.

        Raises:
            ValueError: If min_size > max_size or invalid parameters provided.
        """
        if min_size > max_size:
            raise ValueError("min_size must be less than or equal to max_size")
        if min_size < 0 or max_size < 1:
            raise ValueError("min_size and max_size must be positive")
        if health_check_interval < 1:
            raise ValueError("health_check_interval must be at least 1 second")

        self._create_connection = create_connection
        self._max_size = max_size
        self._min_size = min_size
        self._health_check_interval = health_check_interval
        self._connection_max_age = connection_max_age
        self._connection_max_idle = connection_max_idle
        self._acquire_timeout = acquire_timeout

        self._available: asyncio.Queue[PooledConnection] = asyncio.Queue()
        self._in_use: set[PooledConnection] = set()
        self._all_connections: set[PooledConnection] = set()
        self._lock = asyncio.Lock()
        self._initialized = False
        self._closed = False
        self._health_check_task: asyncio.Task[None] | None = None

        logger.info(
            "connection_pool_created",
            max_size=max_size,
            min_size=min_size,
            health_check_interval=health_check_interval,
        )

    async def initialize(self) -> None:
        """
        Initialize the pool by creating minimum required connections.

        This must be called before using the pool. It creates min_size
        connections and starts the background health check task.

        Raises:
            RuntimeError: If already initialized or if connection creation fails.
        """
        async with self._lock:
            if self._initialized:
                raise RuntimeError("Pool already initialized")
            if self._closed:
                raise RuntimeError("Pool has been closed")

            try:
                for _ in range(self._min_size):
                    connection = await self._create_connection()
                    pooled_conn = PooledConnection(connection=connection)
                    self._all_connections.add(pooled_conn)
                    await self._available.put(pooled_conn)

                self._initialized = True
                logger.info(
                    "connection_pool_initialized", connections_created=self._min_size
                )
            except Exception as exc:
                logger.error("pool_initialization_failed", error=str(exc))
                await self._cleanup_all()
                raise

        # Start health check task outside the lock
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[ConnectionProtocol, None]:
        """
        Acquire a connection from the pool as an async context manager.

        This automatically returns the connection to the pool when the
        context manager exits, handling both normal completion and exceptions.

        Yields:
            A connection from the pool.

        Raises:
            RuntimeError: If pool is not initialized or has been closed.
            asyncio.TimeoutError: If no connection is available within timeout.

        Example:
            async with pool.acquire() as conn:
                result = await conn.execute("SELECT 1")
        """
        if not self._initialized:
            raise RuntimeError("Pool not initialized. Call initialize() first.")
        if self._closed:
            raise RuntimeError("Pool has been closed")

        connection = await self._acquire_internal()
        try:
            yield connection.connection
        except Exception as exc:
            logger.warning(
                "connection_error_during_use",
                error=str(exc),
                use_count=connection.use_count,
            )
            connection.mark_error()
            await self.release(connection.connection)
            raise
        else:
            await self.release(connection.connection)

    async def _acquire_internal(self) -> PooledConnection:
        """
        Internal method to acquire a connection from the pool.

        Returns:
            A PooledConnection object.

        Raises:
            asyncio.TimeoutError: If no connection is available within timeout.
        """
        try:
            pooled_conn = await asyncio.wait_for(
                self._available.get(),
                timeout=self._acquire_timeout,
            )
        except TimeoutError:
            logger.error(
                "acquire_timeout",
                timeout=self._acquire_timeout,
                pool_size=len(self._all_connections),
                in_use=len(self._in_use),
            )
            raise

        async with self._lock:
            self._in_use.add(pooled_conn)

        pooled_conn.mark_active()
        logger.debug(
            "connection_acquired",
            use_count=pooled_conn.use_count,
            pool_available=self._available.qsize(),
        )
        return pooled_conn

    async def release(self, connection: ConnectionProtocol) -> None:
        """
        Release a connection back to the pool.

        The connection is returned to the available queue unless it's
        unhealthy or has reached its age limit, in which case it's recycled.

        Args:
            connection: The connection to release.

        Raises:
            RuntimeError: If the connection was not from this pool.
        """
        async with self._lock:
            pooled_conn = self._find_connection(connection)
            if pooled_conn is None:
                raise RuntimeError("Connection not from this pool")

            self._in_use.discard(pooled_conn)

        # Check if connection should be recycled
        should_recycle = (
            pooled_conn.state == ConnectionState.ERROR
            or pooled_conn.age_seconds() > self._connection_max_age
            or pooled_conn.idle_seconds() > self._connection_max_idle
        )

        if should_recycle:
            await self._recycle_connection(pooled_conn)
            logger.debug("connection_recycled", age=pooled_conn.age_seconds())
        else:
            pooled_conn.mark_idle()
            await self._available.put(pooled_conn)
            logger.debug(
                "connection_released",
                idle_time=pooled_conn.idle_seconds(),
                pool_available=self._available.qsize(),
            )

    def _find_connection(
        self, connection: ConnectionProtocol
    ) -> PooledConnection | None:
        """
        Find a PooledConnection wrapper by its inner connection.

        Args:
            connection: The connection to find.

        Returns:
            The PooledConnection wrapper or None if not found.
        """
        for pooled_conn in self._all_connections:
            if pooled_conn.connection is connection:
                return pooled_conn
        return None

    async def _recycle_connection(self, pooled_conn: PooledConnection) -> None:
        """
        Recycle a connection by closing it and creating a new one.

        Args:
            pooled_conn: The connection to recycle.
        """
        try:
            await pooled_conn.connection.close()
        except Exception as exc:
            logger.warning("error_closing_connection", error=str(exc))

        async with self._lock:
            self._all_connections.discard(pooled_conn)

        # Create replacement if we're still above min_size or if pool not closed
        async with self._lock:
            if not self._closed and len(self._all_connections) < self._min_size:
                try:
                    new_connection = await self._create_connection()
                    new_pooled = PooledConnection(connection=new_connection)
                    self._all_connections.add(new_pooled)
                    await self._available.put(new_pooled)
                    logger.debug("replacement_connection_created")
                except Exception as exc:
                    logger.error("replacement_connection_failed", error=str(exc))

    async def health_check(self) -> dict[str, int]:
        """
        Perform health checks on a sample of idle connections.

        This method checks up to 50% of idle connections to verify they're
        responsive without blocking all connection acquisition.

        Returns:
            Dictionary containing:
            - healthy: Number of healthy connections found
            - unhealthy: Number of unhealthy connections found
            - pool_size: Total connections in pool
            - in_use: Connections currently in use
            - available: Connections available for acquisition

        Raises:
            RuntimeError: If pool not initialized.
        """
        if not self._initialized:
            raise RuntimeError("Pool not initialized")

        healthy = 0
        unhealthy = 0
        checked_connections: list[PooledConnection] = []

        # Collect up to 50% of available connections for checking
        available_count = self._available.qsize()
        check_count = max(1, available_count // 2)

        for _ in range(check_count):
            try:
                pooled_conn = self._available.get_nowait()
                checked_connections.append(pooled_conn)
            except asyncio.QueueEmpty:
                break

        # Check health of collected connections
        for pooled_conn in checked_connections:
            try:
                is_healthy = await asyncio.wait_for(
                    pooled_conn.connection.health_check(),
                    timeout=5.0,
                )
                if is_healthy:
                    healthy += 1
                else:
                    unhealthy += 1
                    pooled_conn.mark_error()
            except Exception as exc:
                logger.warning(
                    "health_check_failed",
                    error=str(exc),
                    age=pooled_conn.age_seconds(),
                )
                unhealthy += 1
                pooled_conn.mark_error()

        # Return connections to pool
        for pooled_conn in checked_connections:
            try:
                if pooled_conn.state == ConnectionState.ERROR:
                    await self._recycle_connection(pooled_conn)
                else:
                    await self._available.put(pooled_conn)
            except Exception as exc:
                logger.error("error_returning_checked_connection", error=str(exc))

        metrics = {
            "healthy": healthy,
            "unhealthy": unhealthy,
            "pool_size": len(self._all_connections),
            "in_use": len(self._in_use),
            "available": self._available.qsize(),
        }

        logger.info("health_check_completed", **metrics)
        return metrics

    async def _health_check_loop(self) -> None:
        """
        Background task that periodically performs health checks.

        Runs until the pool is closed, with graceful exception handling.
        """
        logger.info("health_check_loop_started", interval=self._health_check_interval)

        try:
            while not self._closed:
                try:
                    await asyncio.sleep(self._health_check_interval)
                    if not self._closed:
                        await self.health_check()
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.error("health_check_loop_error", error=str(exc))
        finally:
            logger.info("health_check_loop_stopped")

    def metrics(self) -> dict[str, Any]:
        """
        Get current pool metrics.

        Returns:
            Dictionary containing pool metrics:
            - pool_size: Total connections in pool
            - in_use: Connections currently in use
            - available: Connections available for acquisition
            - utilization: Percentage of connections in use (0-100)
            - max_size: Maximum pool size
            - min_size: Minimum pool size
        """
        pool_size = len(self._all_connections)
        in_use = len(self._in_use)
        utilization = (in_use / pool_size * 100) if pool_size > 0 else 0

        return {
            "pool_size": pool_size,
            "in_use": in_use,
            "available": self._available.qsize(),
            "utilization": round(utilization, 2),
            "max_size": self._max_size,
            "min_size": self._min_size,
        }

    async def close(self) -> None:
        """
        Close all connections in the pool and stop background tasks.

        This gracefully shuts down the pool, waiting for all in-use
        connections to be released before closing them. Should be called
        during application shutdown.
        """
        async with self._lock:
            if self._closed:
                return
            self._closed = True

        logger.info("connection_pool_closing")

        # Cancel health check task
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._health_check_task

        # Wait for in-use connections with timeout
        timeout_at = time.time() + 30.0
        while self._in_use and time.time() < timeout_at:
            logger.debug("waiting_for_in_use_connections", count=len(self._in_use))
            await asyncio.sleep(0.1)

        if self._in_use:
            logger.warning(
                "forcing_close_with_active_connections",
                count=len(self._in_use),
            )

        await self._cleanup_all()
        logger.info("connection_pool_closed")

    async def _cleanup_all(self) -> None:
        """Close all connections in the pool."""
        exceptions = []

        for pooled_conn in list(self._all_connections):
            try:
                await pooled_conn.connection.close()
            except Exception as exc:
                exceptions.append(str(exc))
                logger.warning("error_closing_connection_on_cleanup", error=str(exc))

        self._all_connections.clear()
        self._in_use.clear()

        # Clear the available queue
        while not self._available.empty():
            try:
                self._available.get_nowait()
            except asyncio.QueueEmpty:
                break

        if exceptions:
            logger.error("cleanup_completed_with_errors", error_count=len(exceptions))


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-120",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "data-models",
        "dataclass",
        "debugging",
        "foundation",
        "logging",
        "metrics",
        "queue",
    ],
    "keywords": [
        "acquire",
        "active",
        "age",
        "check",
        "close",
        "connection",
        "execute",
        "health",
    ],
    "business_value": "Provides connection protocols components including ConnectionState, ConnectionProtocol, ConnectionPoolProtocol",
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
