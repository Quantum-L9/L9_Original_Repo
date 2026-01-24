"""
Enhanced Decorators Library for L9 AIOS

Provides standardized decorators with proper metadata preservation using functools.wraps.
All decorators in this module follow best practices for async/sync compatibility.

Usage:
    from core.decorators_enhanced import async_retry, rate_limit, log_execution
    
    @async_retry(max_retries=3)
    @rate_limit(calls_per_minute=60)
    async def my_function():
        ...
"""

import asyncio
import time
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar('T')


def async_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Async retry decorator with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
        
    Example:
        @async_retry(max_retries=3, delay=1.0)
        async def fetch_data():
            return await api.get("/data")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)  # ✅ Preserve function metadata
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries",
                            error=str(e)
                        )
                        raise
                    wait_time = delay * (backoff_factor ** attempt)
                    logger.warning(
                        f"{func.__name__} failed, retrying in {wait_time}s",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=str(e)
                    )
                    await asyncio.sleep(wait_time)
            raise last_exception
        return wrapper
    return decorator


def rate_limit(calls_per_minute: int):
    """
    Rate limiting decorator for async functions.
    
    Args:
        calls_per_minute: Maximum number of calls allowed per minute
        
    Example:
        @rate_limit(calls_per_minute=60)
        async def api_call():
            return await api.get("/endpoint")
    """
    min_interval = 60.0 / calls_per_minute
    last_call_time = {}
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)  # ✅ Preserve function metadata
        async def wrapper(*args, **kwargs):
            func_id = id(func)
            current_time = time.time()
            
            if func_id in last_call_time:
                elapsed = current_time - last_call_time[func_id]
                if elapsed < min_interval:
                    wait_time = min_interval - elapsed
                    logger.debug(
                        f"Rate limit: waiting {wait_time:.2f}s for {func.__name__}"
                    )
                    await asyncio.sleep(wait_time)
            
            last_call_time[func_id] = time.time()
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def log_execution(
    level: str = "info",
    include_args: bool = False,
    include_result: bool = False
):
    """
    Execution logging decorator with configurable verbosity.
    
    Args:
        level: Log level ("debug", "info", "warning", "error")
        include_args: Whether to log function arguments
        include_result: Whether to log function result
        
    Example:
        @log_execution(level="info", include_args=True)
        async def process_data(data: dict):
            return await transform(data)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)  # ✅ Preserve function metadata
        async def wrapper(*args, **kwargs):
            log_func = getattr(logger, level)
            
            log_data = {"function": func.__name__}
            if include_args:
                log_data["args"] = args
                log_data["kwargs"] = kwargs
            
            log_func(f"Executing {func.__name__}", **log_data)
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                result_log_data = {
                    "function": func.__name__,
                    "duration_ms": round(duration * 1000, 2)
                }
                if include_result:
                    result_log_data["result"] = result
                
                log_func(f"Completed {func.__name__}", **result_log_data)
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Failed {func.__name__}",
                    function=func.__name__,
                    duration_ms=round(duration * 1000, 2),
                    error=str(e)
                )
                raise
        return wrapper
    return decorator


def cache_result(ttl: Optional[int] = None):
    """
    Simple in-memory cache decorator with optional TTL.
    
    Args:
        ttl: Time-to-live in seconds (None = cache forever)
        
    Example:
        @cache_result(ttl=300)  # Cache for 5 minutes
        async def expensive_computation(x: int):
            return await heavy_calculation(x)
    """
    cache = {}
    cache_times = {}
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)  # ✅ Preserve function metadata
        async def wrapper(*args, **kwargs):
            # Create cache key from args and kwargs
            cache_key = (args, tuple(sorted(kwargs.items())))
            
            # Check if cached and not expired
            if cache_key in cache:
                if ttl is None or (time.time() - cache_times[cache_key]) < ttl:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cache[cache_key]
                else:
                    # Expired, remove from cache
                    del cache[cache_key]
                    del cache_times[cache_key]
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache[cache_key] = result
            cache_times[cache_key] = time.time()
            logger.debug(f"Cache miss for {func.__name__}, cached result")
            return result
        
        # Add cache management methods
        wrapper.clear_cache = lambda: cache.clear() or cache_times.clear()
        wrapper.cache_size = lambda: len(cache)
        
        return wrapper
    return decorator


def measure_performance(metric_name: Optional[str] = None):
    """
    Performance measurement decorator that logs execution time.
    
    Args:
        metric_name: Custom metric name (defaults to function name)
        
    Example:
        @measure_performance(metric_name="agent.l_cto.execution")
        async def run_agent(task: str):
            return await agent.run(task)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)  # ✅ Preserve function metadata
        async def wrapper(*args, **kwargs):
            name = metric_name or func.__name__
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    f"Performance: {name}",
                    metric=name,
                    duration_ms=round(duration * 1000, 2),
                    status="success"
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Performance: {name} (failed)",
                    metric=name,
                    duration_ms=round(duration * 1000, 2),
                    status="error",
                    error=str(e)
                )
                raise
        return wrapper
    return decorator


def timeout(seconds: float):
    """
    Timeout decorator for async functions.
    
    Args:
        seconds: Timeout duration in seconds
        
    Example:
        @timeout(seconds=30)
        async def long_running_task():
            await asyncio.sleep(60)  # Will timeout after 30s
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)  # ✅ Preserve function metadata
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"{func.__name__} timed out after {seconds}s"
                )
                raise TimeoutError(
                    f"{func.__name__} exceeded timeout of {seconds}s"
                )
        return wrapper
    return decorator


# Sync decorator variants for non-async functions

def sync_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Synchronous version of async_retry decorator."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)  # ✅ Preserve function metadata
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        raise
                    wait_time = delay * (backoff_factor ** attempt)
                    time.sleep(wait_time)
            raise last_exception
        return wrapper
    return decorator


def sync_log_execution(
    level: str = "info",
    include_args: bool = False,
    include_result: bool = False
):
    """Synchronous version of log_execution decorator."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)  # ✅ Preserve function metadata
        def wrapper(*args, **kwargs):
            log_func = getattr(logger, level)
            
            log_data = {"function": func.__name__}
            if include_args:
                log_data["args"] = args
                log_data["kwargs"] = kwargs
            
            log_func(f"Executing {func.__name__}", **log_data)
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                result_log_data = {
                    "function": func.__name__,
                    "duration_ms": round(duration * 1000, 2)
                }
                if include_result:
                    result_log_data["result"] = result
                
                log_func(f"Completed {func.__name__}", **result_log_data)
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Failed {func.__name__}",
                    function=func.__name__,
                    duration_ms=round(duration * 1000, 2),
                    error=str(e)
                )
                raise
        return wrapper
    return decorator
