# Memory Subsystem

## Overview

The **Memory Subsystem** is the Multi-layer memory substrate for L9 Secure AI OS. It Provides PacketEnvelope storage, semantic search, retrieval, and audit trails.

**What depends on it:** `core/agents/executor.py`, `api/memory/router.py`

## Responsibilities and Boundaries

### What This Module Owns

- See key components below for detailed responsibilities

### What This Module Does NOT Do

- Operations handled by other subsystems (see dependencies)

### Dependencies

| Direction | Module | Purpose |
|-----------|--------|---------|
| **Outbound** | `runtime/redis_client.py` | Required dependency |
| **Inbound** | `core/agents/executor.py` | Uses this module |
| **Inbound** | `api/memory/router.py` | Uses this module |

## Directory Layout

```
memory/
├── __init__.py
├── active_encoder.py
├── agent_persistence.py
├── audit_utils.py
├── checkpoint/__init__.py
├── checkpoint/cursor_checkpoint_manager.py
├── checkpoint/postgres_saver.py
├── checkpoint_manager.py
├── checkpoint_metrics.py
├── checkpoint_validator.py
├── consolidation.py
├── context_builder.py
├── cross_encoder_reranker.py
├── cypher_templates.py
├── dead_letter.py
└── ... (53 more files)
```

## Key Components

### `cross_encoder_reranker.py` — CrossEncoderConfig

```python
class CrossEncoderConfig:
    """Configuration for cross-encoder re-ranking."""
```

### `cross_encoder_reranker.py` — RerankingResult

```python
class RerankingResult:
    """Result from cross-encoder re-ranking."""
```

### `cross_encoder_reranker.py` — CrossEncoderReranker

```python
class CrossEncoderReranker:
    """Cross-encoder based neural re-ranker for improved retrieval quality."""
```

**Methods:** `__init__`, `is_available`, `_load_model`, `rerank`, `_extract_text`

### `warming_models.py` — GapSeverity

```python
class GapSeverity:
    """Enumeration of knowledge gap severity levels."""
```

### `warming_models.py` — KnowledgeGap

```python
class KnowledgeGap:
    """Represents a detected knowledge gap with metadata for prioritization."""
```


## Data Models and Contracts

See `schemas.py` or data model files in this subsystem.

### Invariants

- **All packet IDs are UUIDv4**
- **All timestamps are UTC ISO-8601**
- **PacketEnvelope is the canonical data structure for all memory writes**
- **Embeddings are list[float] with dimension 1536 or 3072**
- **Deduplication via dedup_key prevents duplicate ingestion**

## Configuration

### Feature Flags

```yaml
# Subsystem-specific feature flags
L9_ENABLE_MEMORY_TRACING: true
```

### Environment Variables

```bash
MEMORY_LOG_LEVEL=INFO
```

## API Surface (Public)

See key components for public API details.

## Observability

### Logging

Memory operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-18T07:50:15Z",
  "level": "INFO",
  "module": "memory",
  "message": "Operation completed",
  "correlation_id": "corr-xyz789"
}
```

### Metrics

- `memory_operation_duration_ms` — Operation latency (histogram)
- `memory_operation_total` — Total operations (counter)
- `memory_error_rate` — Error percentage (gauge)

## Testing

### Unit Tests

Located in `tests/memory/`:
- `test_memory.py` — Unit tests

## AI Usage Rules

### ✅ Allowed Scopes (AI can modify freely)

- `retrieval.py` — Application logic
- `semantic_search.py` — Application logic
- `context_builder.py` — Application logic
- `insight_extraction.py` — Application logic

### ⚠️ Restricted Scopes (requires human review)

- Schema changes
- Feature flag logic

### ❌ Forbidden Scopes (never modify without approval)

- `substrate_service.py` — PROTECTED
- `substrate_dag.py` — PROTECTED
- `__init__.py` — PROTECTED

### Required Pre-Reading

1. `README-L9_ARCHITECTURE.md` — System architecture
2. `docs/CURSOR-RUNBOOK.md` — AI collaboration rules
3. This file — Subsystem contracts

---

*L9 Secure AI OS — Memory Subsystem*
*Generated: 2026-01-18*
