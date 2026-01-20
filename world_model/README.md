# World Model Module

**Path:** `world_model/`  
**Purpose:** System-wide knowledge representation and world state management  
**Files:** 30 Python files  
**Last Updated:** 2026-01-18

---

## Overview

The `world_model` module maintains a unified representation of the system's knowledge about the world, including facts, entities, relationships, and temporal state.

## Key Components

- **`knowledge_ingestor.py`** - Ingests and processes knowledge (1,183 lines)
- **`world_model_engine.py`** - Core world model engine
- **`entity_tracker.py`** - Tracks entities and relationships
- **`fact_store.py`** - Stores and retrieves facts
- **`temporal_manager.py`** - Manages time-based knowledge

## Usage

### Storing Knowledge

```python
from core.singleton_registry import SingletonRegistry

world_model = await SingletonRegistry.get_world_model_engine()

# Store a fact
await world_model.store_fact({
    "subject": "L9",
    "predicate": "is",
    "object": "agentic platform"
})
```

### Querying Knowledge

```python
# Query facts
facts = await world_model.query({
    "subject": "L9",
    "predicate": "is"
})

# Get entity relationships
relationships = await world_model.get_relationships("L9")
```

## Architecture

**Knowledge Flow:**
1. Ingestion (from agents, APIs, users)
2. Entity extraction
3. Fact validation
4. Deduplication (SHA256 hashing)
5. Storage in graph database
6. Indexing for retrieval

## Subdirectories

- **`extractors/`** - Knowledge extraction from various sources

## Testing

```bash
pytest tests/world_model/
```

## Related Modules

- **`memory/`** - Memory substrate
- **`agents/`** - Knowledge-consuming agents
- **`core/`** - Core infrastructure

---

**Status:** Production  
**Maintainer:** L-CTO Agent
