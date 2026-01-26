# ADR 0023: Error Packet Pattern

## Status

Accepted

## Pattern

ALL errors emit PacketEnvelope with `packet_type="error"` including recovery specification.

## Files

- `core/schemas/packet_envelope_v2.py` - Error packet schema
- `memory/substrate_service.py` - Error packet emission
- `core/resilience/error_handler.py` - Error handler

## Import Block

```python
from memory.substrate_service import get_service
from core.schemas.packet_envelope_v2 import PacketEnvelopeIn
import structlog
import traceback

logger = structlog.get_logger(__name__)
```

## Minimal Implementation

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any
import traceback
import structlog

logger = structlog.get_logger(__name__)

class RecoveryAction(str, Enum):
    """Recovery actions for error packets."""
    RETRY = "retry"           # Transient failure, retry
    ESCALATE = "escalate"     # Needs human intervention
    ROLLBACK = "rollback"     # Undo partial changes
    SKIP = "skip"             # Non-critical, continue
    ABORT = "abort"           # Fatal, stop execution

@dataclass
class ErrorPacket:
    """Error packet for audit trail."""
    error_type: str           # Exception class name
    error_message: str        # str(exception)
    stack_trace: str          # Full traceback
    recovery_action: RecoveryAction
    context: dict[str, Any]   # Operation context
    severity: str = "error"   # error|warning|critical

async def emit_error_packet(
    service,
    error: Exception,
    operation: str,
    recovery: RecoveryAction,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Emit error packet to memory substrate.

    Args:
        service: Memory substrate service
        error: The exception that occurred
        operation: Name of failed operation
        recovery: Recommended recovery action
        context: Additional context (e.g., input params)
    """
    packet = {
        "packet_type": "error",
        "payload": {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
            "operation": operation,
            "recovery_action": recovery.value,
            "context": context or {},
        },
        "metadata": {
            "severity": "error",
            "component": operation.split(".")[0] if "." in operation else "unknown",
        },
        "confidence": {"score": 1.0, "level": "high"},
    }

    await service.write_packet(packet)

    logger.error(
        "error.packet_emitted",
        operation=operation,
        error_type=type(error).__name__,
        recovery=recovery.value,
    )
```

## Usage Example

```python
from core.resilience.error_handler import emit_error_packet, RecoveryAction
from memory.substrate_service import get_service

async def process_data(data: dict) -> dict:
    """Process data with proper error handling."""
    service = await get_service()

    try:
        result = await risky_operation(data)
        return result

    except ValueError as e:
        # Validation error — don't retry
        await emit_error_packet(
            service=service,
            error=e,
            operation="process_data.validation",
            recovery=RecoveryAction.SKIP,
            context={"input_keys": list(data.keys())},
        )
        raise

    except ConnectionError as e:
        # Network error — retry
        await emit_error_packet(
            service=service,
            error=e,
            operation="process_data.connection",
            recovery=RecoveryAction.RETRY,
            context={"endpoint": "api.example.com"},
        )
        raise

    except Exception as e:
        # Unknown error — escalate
        await emit_error_packet(
            service=service,
            error=e,
            operation="process_data.unknown",
            recovery=RecoveryAction.ESCALATE,
            context={"data": str(data)[:100]},
        )
        raise
```

## Anti-Pattern Example

```python
# ❌ WRONG — Silent exception catch
try:
    await risky_operation()
except Exception:
    pass  # Error swallowed, no audit trail!

# ❌ WRONG — Log only, no packet
try:
    await risky_operation()
except Exception as e:
    logger.error("failed", error=str(e))  # No packet!
    raise

# ❌ WRONG — No recovery action
await emit_error_packet(
    service=service,
    error=e,
    operation="op",
    recovery=None,  # Must specify recovery!
)

# ✅ CORRECT — Full error packet with recovery
try:
    await risky_operation()
except Exception as e:
    await emit_error_packet(
        service=service,
        error=e,
        operation="risky_operation",
        recovery=RecoveryAction.RETRY,
        context={"attempt": 1},
    )
    raise
```

## Recovery Actions

| Action     | When                   | Example             |
| ---------- | ---------------------- | ------------------- |
| `RETRY`    | Transient failure      | Network timeout     |
| `ESCALATE` | Needs approval         | Permission denied   |
| `ROLLBACK` | Partial changes made   | Transaction failed  |
| `SKIP`     | Non-critical operation | Optional enrichment |
| `ABORT`    | Fatal, cannot continue | Data corruption     |

## Rules

1. ALL exceptions MUST emit error packet before re-raise
2. Include full `stack_trace` for debugging
3. ALWAYS specify `recovery_action`
4. Include relevant `context` (sanitized, no secrets)
5. Set appropriate `severity` level

## AI Guidance

**DO:**

- Emit error packet before re-raising
- Include full stack trace
- Specify appropriate recovery action
- Add relevant context (sanitized)

**DO NOT:**

- Catch and ignore exceptions silently
- Use bare `except:` without packet
- Skip error packet "for performance"
- Include secrets in context
