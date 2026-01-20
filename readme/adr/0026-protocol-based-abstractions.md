# ADR 0026: Protocol-Based Abstractions

## Status
Accepted

## Pattern
Use `typing.Protocol` for interfaces; structural subtyping; no ABC inheritance required.

## Files
- `core/abstractions/memory_protocols.py` - Memory protocols
- `core/abstractions/agent_protocols.py` - Agent protocols
- `core/abstractions/kernel_protocols.py` - Kernel protocols
- `core/abstractions/observability_protocols.py` - Observability protocols

## Import Block
```python
from typing import Protocol, runtime_checkable, TypeVar, Any
from abc import abstractmethod  # Only for @abstractmethod, not ABC inheritance
```

## Minimal Implementation
```python
from typing import Protocol, runtime_checkable, TypeVar, Any
from dataclasses import dataclass

T = TypeVar("T")


@runtime_checkable
class PacketWriter(Protocol):
    """
    Protocol for components that write packets.
    
    Any class with matching method signatures satisfies this protocol
    WITHOUT needing to explicitly inherit from it.
    """
    
    async def write_packet(
        self,
        packet: dict,
        **kwargs: Any,
    ) -> dict:
        """Write packet to storage."""
        ...  # Use ellipsis, not pass


@runtime_checkable
class PacketReader(Protocol):
    """Protocol for components that read packets."""
    
    async def read_packet(self, packet_id: str) -> dict | None:
        """Read packet by ID."""
        ...
    
    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict]:
        """Search packets."""
        ...


# Combining protocols
class PacketStore(PacketWriter, PacketReader, Protocol):
    """Combined read/write protocol."""
    pass


# Implementation (no inheritance needed!)
class MemorySubstrateService:
    """Satisfies PacketWriter and PacketReader via structural typing."""
    
    async def write_packet(self, packet: dict, **kwargs: Any) -> dict:
        # Implementation
        return {"status": "ok", "packet_id": "abc"}
    
    async def read_packet(self, packet_id: str) -> dict | None:
        # Implementation
        return {"packet_id": packet_id, "payload": {}}
    
    async def search(self, query: str, limit: int = 10) -> list[dict]:
        # Implementation
        return []


# Type checker accepts this without explicit inheritance
def process(writer: PacketWriter) -> None:
    """Accepts any class that has write_packet method."""
    pass

# Works because MemorySubstrateService has matching method
service = MemorySubstrateService()
process(service)  # ✅ Type checker accepts this
```

## Usage Example
```python
from typing import Protocol, runtime_checkable
from core.abstractions.memory_protocols import PacketWriter

# Function accepting protocol type
async def emit_packet(
    writer: PacketWriter,
    data: dict,
) -> dict:
    """Emit packet using any PacketWriter implementation."""
    return await writer.write_packet({"payload": data})


# Runtime type checking (requires @runtime_checkable)
def validate_writer(obj: Any) -> bool:
    """Check if object satisfies PacketWriter protocol."""
    return isinstance(obj, PacketWriter)


# Dependency injection with protocols
class DataProcessor:
    def __init__(self, writer: PacketWriter):
        self._writer = writer  # Any PacketWriter implementation
    
    async def process(self, data: dict) -> dict:
        result = transform(data)
        return await self._writer.write_packet(result)
```

## Anti-Pattern Example
```python
# ❌ WRONG — Using ABC for interface
from abc import ABC, abstractmethod

class PacketWriter(ABC):  # Forces inheritance
    @abstractmethod
    async def write_packet(self, packet: dict) -> dict:
        pass

class MyService(PacketWriter):  # Must inherit explicitly
    ...

# ❌ WRONG — Using `pass` instead of `...`
class BadProtocol(Protocol):
    async def method(self) -> None:
        pass  # Use ... instead

# ❌ WRONG — Implementing methods in Protocol
class BadProtocol(Protocol):
    async def method(self) -> None:
        return None  # Protocols shouldn't have implementations

# ✅ CORRECT — Protocol with structural typing
@runtime_checkable
class PacketWriter(Protocol):
    async def write_packet(self, packet: dict) -> dict:
        ...  # Ellipsis, no implementation
```

## Protocol vs ABC
| Feature | Protocol | ABC |
|---------|----------|-----|
| Inheritance | Not required | Required |
| Type checking | Structural | Nominal |
| Runtime check | `@runtime_checkable` | Built-in |
| Duck typing | Yes | No |
| Multiple inheritance | Easy | Complex |

## Rules
1. Use `Protocol` not `ABC` for interfaces
2. Add `@runtime_checkable` if need `isinstance()`
3. Keep protocols in `core/abstractions/`
4. Methods end with `...` (ellipsis) not `pass`
5. Document protocol purpose in docstring

## AI Guidance
**DO:**
- Use `Protocol` for new interfaces
- Add `@runtime_checkable` decorator
- Keep methods abstract (use `...`)
- Type hint all parameters and returns

**DO NOT:**
- Use `ABC` for new abstractions
- Require explicit inheritance
- Implement methods in Protocol
- Create concrete classes in `core/abstractions/`
