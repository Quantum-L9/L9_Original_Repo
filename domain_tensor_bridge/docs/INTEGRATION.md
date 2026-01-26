# Integration Guide

## Registering Domain Agents

### Step 1: Create Domain Handler

```python
from domain_tensor_bridge import DomainPacketHandler

class MyDomainHandler(DomainPacketHandler):
    async def handle_mydomain_packet(self, packet):
        enriched = self._enrich_mydomain_payload(packet.payload)
        return PacketEnvelope(
            source_id="domain_tensor_bridge",
            kind=PacketKind.REASONING,
            payload=enriched,
        )
```

### Step 2: Register Handler

```python
router = PacketRouter()
router.register_domain_handler("mydomain", handler.handle_mydomain_packet)
```

### Step 3: Send Packets

```python
packet = PacketEnvelope(
    source_id="mydomain_agent",
    kind=PacketKind.REASONING,
    payload={"entity_id": "123", "data": {...}},
)

result = await controller.process_packet(packet)
```

## Memory Integration

Access shared memory layers:

```python
from domain_tensor_bridge import MemoryBridge

memory = MemoryBridge()
await memory.initialize()

# Working memory (Redis)
await memory.set_working_memory("session:123", {"state": "active"})

# Episodic memory (Postgres)
events = await memory.query_episodic_memory({"entity_id": "123"})
```

## Governance Integration

Decisions are automatically checked against governance policy. For custom governance:

```python
from domain_tensor_bridge import GovernanceBridge

governance = GovernanceBridge()
result = await governance.check_governance(decision)
if not result.approved:
    # Handle escalation
    pass
```
