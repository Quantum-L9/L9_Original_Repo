# L9 World Model - Architecture & Usage

## Overview

The L9 World Model is the **central semantic state store** for the L9 system. It maintains a persistent representation of entities, their attributes, and relationships derived from memory insights.

**Key Capabilities:**

- **Entity Management**: CRUD operations for world model entities
- **Insight Integration**: Updates from memory substrate's insight pipeline
- **Persistence**: PostgreSQL-backed storage with asyncpg
- **Snapshots**: Point-in-time state backups and restore
- **Audit Trail**: Full history of all updates
- **API Access**: RESTful endpoints for external integration
- **LangGraph Nodes**: Native integration with LangGraph DAGs

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        L9 World Model                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐ │
│  │   Memory    │    │   World     │    │      PostgreSQL         │ │
│  │  Substrate  │───▶│   Model     │───▶│  world_model_entities   │ │
│  │  (insights) │    │   Service   │    │  world_model_updates    │ │
│  └─────────────┘    └─────────────┘    │  world_model_snapshots  │ │
│                            │           └─────────────────────────┘ │
│                            ▼                                        │
│  ┌─────────────┐    ┌─────────────┐                                │
│  │  LangGraph  │◀───│ Repository  │                                │
│  │   Nodes     │    │   Layer     │                                │
│  └─────────────┘    └─────────────┘                                │
│                            │                                        │
│                            ▼                                        │
│  ┌─────────────┐    ┌─────────────┐                                │
│  │   HTTP      │◀───│    API      │                                │
│  │   Client    │    │   Routes    │                                │
│  └─────────────┘    └─────────────┘                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Components

| Component       | File                            | Purpose                 |
| --------------- | ------------------------------- | ----------------------- |
| Repository      | `world_model/repository.py`     | DB operations (asyncpg) |
| Service         | `world_model/service.py`        | Business logic layer    |
| API             | `api/world_model_api.py`        | HTTP endpoints          |
| Client SDK      | `clients/world_model_client.py` | Async HTTP client       |
| LangGraph Nodes | `world_model/nodes.py`          | DAG integration         |

## Database Layout

### `world_model_entities`

Primary entity storage.

| Column        | Type      | Description             |
| ------------- | --------- | ----------------------- |
| `entity_id`   | TEXT      | Primary key             |
| `entity_type` | TEXT      | Classification          |
| `attributes`  | JSONB     | Entity properties       |
| `confidence`  | FLOAT     | Confidence score (0-1)  |
| `created_at`  | TIMESTAMP | Creation time           |
| `updated_at`  | TIMESTAMP | Last update             |
| `version`     | INT       | Optimistic lock version |

### `world_model_updates`

Audit log of all updates.

| Column                 | Type      | Description         |
| ---------------------- | --------- | ------------------- |
| `update_id`            | UUID      | Primary key         |
| `insight_id`           | UUID      | Source insight      |
| `insight_type`         | TEXT      | Type of insight     |
| `entities`             | JSONB     | Affected entity IDs |
| `content`              | JSONB     | Update payload      |
| `confidence`           | FLOAT     | Update confidence   |
| `applied_at`           | TIMESTAMP | When applied        |
| `state_version_before` | INT       | Version before      |
| `state_version_after`  | INT       | Version after       |

### `world_model_snapshots`

Point-in-time state backups.

| Column          | Type      | Description              |
| --------------- | --------- | ------------------------ |
| `snapshot_id`   | UUID      | Primary key              |
| `snapshot`      | JSONB     | Full state serialization |
| `state_version` | INT       | Version at snapshot      |
| `entity_count`  | INT       | Entity count             |
| `created_at`    | TIMESTAMP | Creation time            |
| `description`   | TEXT      | Optional description     |

## Lifecycle: Insights → Updates → Entities

```
Memory Substrate              World Model Service              Database
     │                              │                              │
     │  [ExtractedInsight]          │                              │
     │  trigger_world_model=True    │                              │
     │─────────────────────────────▶│                              │
     │                              │                              │
     │                              │  1. Filter triggering        │
     │                              │     insights                 │
     │                              │                              │
     │                              │  2. For each insight:        │
     │                              │     - Extract entities       │
     │                              │     - Build attributes       │
     │                              │                              │
     │                              │  upsert_entity()             │
     │                              │─────────────────────────────▶│
     │                              │                              │ world_model_entities
     │                              │                              │
     │                              │  record_update()             │
     │                              │─────────────────────────────▶│
     │                              │                              │ world_model_updates
     │                              │                              │
     │                              │  3. Bump state_version       │
     │                              │                              │
     │  {status, entities_affected} │                              │
     │◀─────────────────────────────│                              │
```

## API Reference

### Base URL

```
/world-model
```

### Endpoints

#### Health Check

```
GET /world-model/health

Response: {
  "status": "healthy",
  "state_version": 42,
  "entity_count": 156
}
```

#### Get Entity

```
GET /world-model/entities/{entity_id}

Response: {
  "entity_id": "user-123",
  "entity_type": "user",
  "attributes": {"name": "Alice", "role": "admin"},
  "confidence": 0.95,
  "version": 3
}
```

#### List Entities

```
GET /world-model/entities?entity_type=user&min_confidence=0.8&limit=50

Response: {
  "entities": [...],
  "total": 50,
  "limit": 50,
  "offset": 0
}
```

#### Get State Version

```
GET /world-model/state-version

Response: {
  "state_version": 42,
  "entity_count": 156
}
```

#### Create Snapshot

```
POST /world-model/snapshot
{
  "description": "Before migration",
  "created_by": "admin"
}

Response: {
  "snapshot_id": "abc123...",
  "state_version": 42,
  "entity_count": 156,
  "created_at": "2025-01-15T12:00:00Z"
}
```

#### Restore from Snapshot

```
POST /world-model/restore
{
  "snapshot_id": "abc123..."
}

Response: {
  "status": "ok",
  "entities_restored": 156,
  "state_version": 42
}
```

#### Submit Insights

```
POST /world-model/insights
{
  "insights": [
    {
      "insight_type": "conclusion",
      "content": "User Alice completed onboarding",
      "entities": ["user-123"],
      "confidence": 0.9,
      "trigger_world_model": true
    }
  ]
}

Response: {
  "status": "ok",
  "updates_applied": 1,
  "entities_affected": 1,
  "state_version": 43
}
```

#### List Updates

```
GET /world-model/updates?insight_type=conclusion&limit=100

Response: {
  "updates": [...],
  "total": 100
}
```

## Client SDK Usage

### Basic Operations

```python
from clients.world_model_client import get_world_model_client

async def example():
    client = get_world_model_client()

    # Get entity
    entity = await client.get_entity("user-123")
    if entity:
        print(f"Found: {entity.entity_id}, type={entity.entity_type}")

    # List entities
    users = await client.list_entities(entity_type="user", limit=50)
    print(f"Found {len(users)} users")

    # Get state version
    state = await client.get_state_version()
    print(f"Version: {state.state_version}, Entities: {state.entity_count}")

    # Submit insights
    result = await client.send_insights_for_update([
        {
            "insight_type": "conclusion",
            "content": "User completed task",
            "entities": ["user-123", "task-456"],
            "confidence": 0.85,
        }
    ])
    print(f"Applied {result.updates_applied} updates")

    # Create snapshot
    snapshot = await client.snapshot(description="Daily backup")
    print(f"Snapshot: {snapshot.snapshot_id}")

    # Cleanup
    await client.close()
```

### Context Manager Pattern

```python
async def with_context_manager():
    async with get_world_model_client() as client:
        entity = await client.get_entity("user-123")
        # Auto-closes on exit
```

## LangGraph Integration

### Update Node

```python
from langgraph.graph import StateGraph
from world_model.nodes import world_model_update_node

# In your graph builder:
graph = StateGraph(YourState)

graph.add_node("world_model_update", world_model_update_node)
graph.add_edge("extract_insights", "world_model_update")
```

### Snapshot Node

```python
from world_model.nodes import world_model_snapshot_node

# Add checkpoint capability:
graph.add_node("world_model_snapshot", world_model_snapshot_node)
graph.add_edge("critical_operation", "world_model_snapshot")
```

### State Schema

```python
from world_model.nodes import WorldModelGraphState

class MyGraphState(WorldModelGraphState):
    # Your custom fields
    custom_data: dict
```

## Integration Points

### Memory Substrate

The world model receives updates via `world_model_trigger_node` in the memory substrate DAG:

```
extract_insights → store_insights → world_model_trigger → checkpoint
```

When an insight has `trigger_world_model=True`, it flows to:

1. `WorldModelService.update_from_insights()`
2. Entity upsert via repository
3. Update audit log

### Orchestrators

Orchestrators can use the client SDK:

```python
from clients.world_model_client import get_world_model_client

class MyOrchestrator:
    def __init__(self):
        self.world_model = get_world_model_client()

    async def get_context(self, entity_id: str):
        return await self.world_model.get_entity(entity_id)
```

## Example: Full Integration

```python
"""
Complete example: Memory packet → World model update
"""
from memory.substrate_service import SubstrateService
from clients.world_model_client import get_world_model_client

async def process_user_action(user_id: str, action: str):
    # 1. Write to memory substrate
    memory = SubstrateService()
    result = await memory.write_packet({
        "packet_type": "user_action",
        "payload": {
            "user_id": user_id,
            "action": action,
            "timestamp": "2025-01-15T12:00:00Z"
        },
        "metadata": {"agent": "user_tracker"}
    })

    # Memory substrate DAG automatically:
    # - Extracts insights
    # - Triggers world model if insight.trigger_world_model=True

    # 2. Query updated world model
    wm = get_world_model_client()
    entity = await wm.get_entity(user_id)
    print(f"User {user_id} updated: {entity.attributes}")

    # 3. Get current state version
    state = await wm.get_state_version()
    print(f"World model at version {state.state_version}")
```

## Migration Files

Apply in order:

1. `0004_init_world_model_entities.sql` - Entity storage
2. `0005_init_world_model_updates.sql` - Update audit log
3. `0006_init_world_model_snapshots.sql` - Snapshot storage

```bash
# Apply migrations
psql $DATABASE_URL -f L9/migrations/0004_init_world_model_entities.sql
psql $DATABASE_URL -f L9/migrations/0005_init_world_model_updates.sql
psql $DATABASE_URL -f L9/migrations/0006_init_world_model_snapshots.sql
```

## Version History

| Version | Date       | Changes                    |
| ------- | ---------- | -------------------------- |
| 1.0.0   | 2025-01-15 | Initial production release |
| -       | -          | PostgreSQL persistence     |
| -       | -          | API endpoints              |
| -       | -          | Client SDK                 |
| -       | -          | LangGraph nodes            |
