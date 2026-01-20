# ADR 0019: structlog Logging Standard

## Status
Accepted

## Pattern
ALL logging via `structlog.get_logger(__name__)`; NEVER use `print()` or stdlib `logging`.

## Files
- 444+ files use `structlog.get_logger`
- `ci/lint_forbidden_imports.py` - Import enforcement
- `config/settings.py` - Logger configuration

## Import Block
```python
import structlog

logger = structlog.get_logger(__name__)
```

## Minimal Implementation
```python
"""Example module with proper logging."""
import structlog

# Module-level logger (use __name__ for automatic module path)
logger = structlog.get_logger(__name__)

class MyService:
    def __init__(self):
        logger.info("service.initialized", service="MyService")
    
    async def process(self, item_id: str) -> dict:
        logger.debug(
            "process.started",
            item_id=item_id,
        )
        
        try:
            result = await self._do_work(item_id)
            logger.info(
                "process.completed",
                item_id=item_id,
                result_size=len(result),
            )
            return result
        except ValueError as e:
            logger.warning(
                "process.validation_failed",
                item_id=item_id,
                error=str(e),
            )
            raise
        except Exception as e:
            logger.error(
                "process.failed",
                item_id=item_id,
                error=str(e),
                exc_info=True,  # Include stack trace
            )
            raise
```

## Usage Example
```python
import structlog

logger = structlog.get_logger(__name__)

# Debug — Verbose info for debugging
logger.debug("cache.lookup", key="user_123", hit=True)

# Info — Normal operations
logger.info("request.processed", endpoint="/api/v1/data", duration_ms=45)

# Warning — Recoverable issues
logger.warning("rate_limit.approaching", current=95, limit=100)

# Error — Failures with context
logger.error(
    "database.connection_failed",
    host="db.example.com",
    error="Connection refused",
    exc_info=True,
)

# With bound context (carries through all logs)
log = logger.bind(request_id="abc-123", user_id="user_456")
log.info("operation.started")
log.info("operation.completed")  # Also has request_id, user_id
```

## Anti-Pattern Example
```python
# ❌ WRONG — Using print()
print(f"Processing item {item_id}")  # No structure, no levels

# ❌ WRONG — Using stdlib logging
import logging
logging.info("Processing")  # Different config, no structure

# ❌ WRONG — String formatting in message
logger.info(f"Processing {item_id}")  # Use kwargs instead

# ❌ WRONG — Generic logger name
logger = structlog.get_logger("mylogger")  # Use __name__

# ✅ CORRECT — Structured logging with kwargs
logger.info("item.processing", item_id=item_id, status="started")
```

## Event Naming Convention
```python
# Format: component.action or component.action_detail
logger.info("service.initialized")       # Component lifecycle
logger.info("request.received")          # Request handling
logger.info("cache.hit")                 # Cache operations
logger.info("database.query_executed")   # Database operations
logger.error("api.call_failed")          # External API
logger.warning("validation.failed")      # Input validation
```

## Rules
1. ALWAYS use `structlog.get_logger(__name__)`
2. ALWAYS use keyword arguments for context (not string formatting)
3. ALWAYS use snake_case event names (`component.action`)
4. NEVER use `print()` in production code
5. NEVER use stdlib `logging` module

## AI Guidance
**DO:**
- Use `structlog.get_logger(__name__)` for all logging
- Include relevant context as kwargs
- Use consistent event naming (`component.action`)
- Add `exc_info=True` for error logging

**DO NOT:**
- Use `print()` for any logging
- Use stdlib `logging` module
- Format strings in log message (use kwargs)
- Use generic logger names
