# PacketEnvelope Specification

## Overview

All communication uses L9's native PacketEnvelope protocol.

## Structure

```python
@dataclass
class PacketEnvelope:
    source_id: str           # Source agent identifier
    kind: PacketKind         # Packet type
    payload: Dict[str, Any]  # Main data
    metadata: Dict[str, Any] # Optional metadata
    id: Optional[str]        # Unique ID
    timestamp: Optional[str] # ISO timestamp
```

## Packet Kinds

| Kind | Description |
|------|-------------|
| REASONING | Request for reasoning |
| DECISION | Decision result |
| TOOL_CALL | Tool execution request |
| MEMORY_WRITE | Memory operation |
| ESCALATION | Governance escalation |

## Routing

Packets are routed based on:
1. `kind` field (primary)
2. `source_id` prefix (domain)
3. Fallback handler (default)

## Validation

All packets must pass validation:
- Required fields present
- Valid source_id format
- Recognized kind
- Payload < 1MB


