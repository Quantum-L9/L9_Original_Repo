# L9 @lru_cache Functions

> **Added:** GMP-59 through GMP-62 (2026-01-13)
> **Total:** 18 cached functions across 17 files

## Overview

These `@lru_cache` decorators improve performance by caching:

- File I/O operations (kernel loading, config parsing)
- Singleton factory functions (settings, pipelines, clients)
- Frequently-accessed lookups (templates, rules)

## All Cached Functions

### File I/O Caching (GMP-59)

| Function                       | File                             | maxsize | Purpose                      |
| ------------------------------ | -------------------------------- | ------- | ---------------------------- |
| `load_kernel_file()`           | `runtime/kernel_loader.py`       | 64      | Cache kernel YAML loads      |
| `get_fallback_prompt()`        | `core/kernels/prompt_builder.py` | 1       | Cache fallback prompt string |
| `_load_kernel_hashes_cached()` | `core/kernels/integrity.py`      | 8       | Cache hash file loads        |
| `get_template_library()`       | `memory/cypher_templates.py`     | 1       | Singleton template library   |
| `get_query_classifier()`       | `memory/query_classifier.py`     | 1       | Singleton classifier         |

### Config Singletons (GMP-60)

| Function                     | File                                  | maxsize | Purpose                        |
| ---------------------------- | ------------------------------------- | ------- | ------------------------------ |
| `get_integration_settings()` | `config/settings.py`                  | 1       | Integration settings singleton |
| `get_settings()`             | `config/memory_substrate_settings.py` | 1       | Memory substrate settings      |
| `get_research_settings()`    | `config/research_settings.py`         | 1       | Research factory settings      |
| `get_upgrade_engine()`       | `api/routes/upgrades.py`              | 1       | Upgrade engine singleton       |
| `get_kernel_stack()`         | `core/kernels/prompt_builder.py`      | 1       | Kernel stack singleton         |

### Memory Pipeline Singletons (GMP-61)

| Function                    | File                           | maxsize | Purpose                     |
| --------------------------- | ------------------------------ | ------- | --------------------------- |
| `get_housekeeping_engine()` | `memory/housekeeping.py`       | 1       | Housekeeping singleton      |
| `get_insight_pipeline()`    | `memory/insight_extraction.py` | 1       | Insight extraction pipeline |
| `get_ingestion_pipeline()`  | `memory/ingestion.py`          | 1       | Ingestion pipeline          |
| `get_retrieval_pipeline()`  | `memory/retrieval.py`          | 1       | Retrieval pipeline          |
| `get_mcp_client()`          | `runtime/mcp_client.py`        | 1       | MCP client singleton        |

### Instance Method Wrappers (GMP-62)

| Function                | File                         | maxsize | Purpose                    |
| ----------------------- | ---------------------------- | ------- | -------------------------- |
| `get_kernel_cached()`   | `runtime/kernel_loader.py`   | 64      | Cached kernel lookup by ID |
| `get_rule_cached()`     | `runtime/kernel_loader.py`   | 256     | Cached rule lookup by path |
| `get_template_cached()` | `memory/cypher_templates.py` | 64      | Cached template lookup     |

## Usage

### Basic Usage

```python
from runtime.kernel_loader import get_kernel_cached, get_rule_cached
from memory.cypher_templates import get_template_cached

# These calls are cached - second call is instant
kernel = get_kernel_cached("safety")
rule = get_rule_cached("cognitive", "reasoning.modes.default")
template = get_template_cached("get_entity")
```

### Cache Inspection

```python
# View cache stats
print(get_kernel_cached.cache_info())
# CacheInfo(hits=5, misses=2, maxsize=64, currsize=2)
```

### Cache Invalidation

```python
# Clear cache after kernel/config changes
get_kernel_cached.cache_clear()
get_rule_cached.cache_clear()

# For settings with reset functions
from config.memory_substrate_settings import reset_settings
reset_settings()  # Calls cache_clear() internally
```

## Benefits

| Benefit         | Description                                      |
| --------------- | ------------------------------------------------ |
| **Performance** | Avoid repeated file I/O and object instantiation |
| **Thread-safe** | `@lru_cache` handles concurrent access correctly |
| **Inspectable** | `.cache_info()` shows hit/miss statistics        |
| **Testable**    | `.cache_clear()` resets state between tests      |

## Notes

- All singleton factories use `maxsize=1` (only one instance)
- Lookup caches use larger sizes (64-256) for variety of keys
- `Path` objects are hashable in Python 3.6+, so file paths work as cache keys
- Reset functions (where they exist) call `.cache_clear()` internally
