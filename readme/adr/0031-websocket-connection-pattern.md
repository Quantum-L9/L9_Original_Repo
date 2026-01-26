# ADR 0031: WebSocket Connection Pattern

## Status

Accepted

## Pattern

WebSocket connections managed via `ws_orchestrator` singleton; register on connect, unregister in finally.

## Files

- `runtime/websocket_orchestrator.py` - Connection manager
- `api/server.py` - WebSocket endpoint
- `orchestrators/ws_bridge.py` - Message bridge

## Import Block

```python
from fastapi import WebSocket, WebSocketDisconnect
from runtime.websocket_orchestrator import ws_orchestrator
import uuid
import structlog

logger = structlog.get_logger(__name__)
```

## Minimal Implementation

```python
from fastapi import WebSocket
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ConnectionMeta:
    """Metadata for a WebSocket connection."""
    connection_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class WebSocketOrchestrator:
    """
    Manages WebSocket connections lifecycle.

    - Registers connections on accept
    - Unregisters on disconnect
    - Provides broadcast capability
    """

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}
        self._metadata: dict[str, ConnectionMeta] = {}

    async def register(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register a new WebSocket connection."""
        self._connections[connection_id] = websocket
        self._metadata[connection_id] = ConnectionMeta(
            connection_id=connection_id,
            user_id=user_id,
            metadata=metadata or {},
        )

        logger.info(
            "ws.registered",
            connection_id=connection_id,
            user_id=user_id,
            total_connections=len(self._connections),
        )

    async def unregister(self, connection_id: str) -> None:
        """Unregister a WebSocket connection."""
        self._connections.pop(connection_id, None)
        self._metadata.pop(connection_id, None)

        logger.info(
            "ws.unregistered",
            connection_id=connection_id,
            total_connections=len(self._connections),
        )

    async def send(self, connection_id: str, message: dict) -> bool:
        """Send message to specific connection."""
        ws = self._connections.get(connection_id)
        if ws:
            await ws.send_json(message)
            return True
        return False

    async def broadcast(self, message: dict) -> int:
        """Broadcast message to all connections."""
        sent = 0
        for ws in self._connections.values():
            try:
                await ws.send_json(message)
                sent += 1
            except Exception:
                pass  # Connection may be closed
        return sent

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self._connections)


# Singleton instance
ws_orchestrator = WebSocketOrchestrator()
```

## Usage Example

```python
from fastapi import WebSocket, WebSocketDisconnect
from runtime.websocket_orchestrator import ws_orchestrator
import uuid

@app.websocket("/ws/agent")
async def websocket_agent(websocket: WebSocket):
    """WebSocket endpoint for agent communication."""
    await websocket.accept()
    connection_id = str(uuid.uuid4())

    try:
        # Register connection immediately after accept
        await ws_orchestrator.register(
            websocket=websocket,
            connection_id=connection_id,
            user_id="user_123",
            metadata={"client": "cursor"},
        )

        # Message loop
        while True:
            data = await websocket.receive_json()

            # Process message
            response = await process_message(data)

            # Send response
            await websocket.send_json(response)

    except WebSocketDisconnect:
        logger.info("ws.client_disconnected", id=connection_id)

    finally:
        # ALWAYS unregister in finally block
        await ws_orchestrator.unregister(connection_id)


# Broadcast from elsewhere
async def notify_all_clients(event: dict):
    """Broadcast event to all connected clients."""
    sent = await ws_orchestrator.broadcast({
        "type": "notification",
        "payload": event,
    })
    logger.info("ws.broadcast_sent", recipients=sent)
```

## Anti-Pattern Example

```python
# ❌ WRONG — No registration
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_json()
        await websocket.send_json({"ok": True})
    # No registration, no cleanup!

# ❌ WRONG — Missing finally block
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    await ws_orchestrator.register(websocket, connection_id)

    while True:  # If this raises, unregister never called!
        data = await websocket.receive_json()

# ❌ WRONG — Storing WebSocket outside orchestrator
connections = {}  # Global dict instead of orchestrator

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    connections["my_conn"] = websocket  # Not managed!

# ✅ CORRECT — Full lifecycle with finally
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_id = str(uuid.uuid4())

    try:
        await ws_orchestrator.register(websocket, connection_id)
        while True:
            data = await websocket.receive_json()
            await websocket.send_json(await process(data))
    except WebSocketDisconnect:
        pass  # Normal disconnect
    finally:
        await ws_orchestrator.unregister(connection_id)  # ALWAYS runs
```

## Connection Lifecycle

```
Client Connect
    │
    ▼
websocket.accept()
    │
    ▼
ws_orchestrator.register(ws, id)
    │
    ▼
Message Loop (receive/send)
    │
    ├── Normal: Continue loop
    │
    └── Exception/Disconnect
            │
            ▼
        finally: ws_orchestrator.unregister(id)
```

## Rules

1. ALWAYS register after `accept()`
2. ALWAYS unregister in `finally` block
3. Use `ws_orchestrator` singleton
4. Handle `WebSocketDisconnect`
5. Log connection events

## AI Guidance

**DO:**

- Use `ws_orchestrator` for all connections
- Register immediately after `accept()`
- Unregister in `finally` block
- Handle `WebSocketDisconnect` gracefully

**DO NOT:**

- Store WebSocket refs outside orchestrator
- Skip unregister on disconnect
- Use bare WebSocket without registration
- Forget `finally` cleanup
