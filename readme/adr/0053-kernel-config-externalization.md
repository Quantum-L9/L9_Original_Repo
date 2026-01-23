# ADR 0053: Kernel Configuration Externalization

## Status
Accepted

## Pattern
Externalize kernel loading configuration to YAML files with environment-specific overrides and feature flag gating.

## Files
- `config/kernel_discovery.yaml` — Kernel configuration
- `runtime/kernel_config_loader.py` — Config loader with validation
- `runtime/kernel_loader.py` — Modified to use external config

## Import Block
```python
from runtime.kernel_config_loader import (
    load_kernel_config,
    get_kernel_order,
    validate_kernel_config,
)
```

## Minimal Implementation
```yaml
# config/kernel_discovery.yaml
kernel_order:
  - "00_system"
  - "01_memory"
  - "02_cognitive"
  - "03_reasoning"
  - "04_planning"

required_kernels:
  - "00_system"
  - "01_memory"

minimum_kernel_count: 2

environments:
  dev:
    kernel_order: ["00_system"]  # Minimal for fast iteration
  test:
    kernel_order: ["00_system", "01_memory"]
  staging:
    kernel_order: null  # Use default
  production:
    kernel_order: null  # Use default
    strict_validation: true
```

```python
# runtime/kernel_config_loader.py
import os
import yaml
from pathlib import Path

def load_kernel_config() -> dict:
    """Load kernel config with environment override."""
    config_path = Path("config/kernel_discovery.yaml")
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    env = os.getenv("L9_ENV", "production")
    env_config = config.get("environments", {}).get(env, {})
    
    # Apply environment override
    if env_config.get("kernel_order"):
        config["kernel_order"] = env_config["kernel_order"]
    
    return config

def get_kernel_order() -> list[str]:
    """Get kernel order for current environment."""
    if os.getenv("L9_USE_KERNEL_CONFIG", "true").lower() != "true":
        # Fallback to hard-coded order
        return ["00_system", "01_memory", "02_cognitive", ...]
    
    config = load_kernel_config()
    return config["kernel_order"]
```

## Usage Example
```python
# In kernel_loader.py
from runtime.kernel_config_loader import get_kernel_order

def load_kernels():
    kernel_order = get_kernel_order()
    
    for kernel_name in kernel_order:
        kernel_path = Path(f"config/kernels/{kernel_name}.yaml")
        kernel = load_kernel(kernel_path)
        register_kernel(kernel)
```

## Anti-Pattern Example
```python
# ❌ WRONG — Hard-coded kernel order
KERNEL_ORDER = [
    "00_system",
    "01_memory",
    "02_cognitive",
]

def load_kernels():
    for name in KERNEL_ORDER:  # No env-specific config!
        ...

# ✅ CORRECT — Externalized config
def load_kernels():
    kernel_order = get_kernel_order()  # From YAML, env-aware
    for name in kernel_order:
        ...
```

## Rules
1. **Config in YAML** — Kernel order lives in `config/kernel_discovery.yaml`
2. **Environment overrides** — Use `environments:` section for env-specific config
3. **Feature flag gating** — `L9_USE_KERNEL_CONFIG` controls config loading
4. **Fallback required** — Always have hard-coded fallback if config fails
5. **Validation** — Validate required kernels and minimum count

## Environment Variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `L9_ENV` | `production` | Environment name (dev/test/staging/production) |
| `L9_USE_KERNEL_CONFIG` | `true` | Enable external config loading |

## Rollback Strategy
```bash
# Disable external config, use hard-coded fallback
export L9_USE_KERNEL_CONFIG=false
```

## AI Guidance
**DO:**
- Modify `config/kernel_discovery.yaml` for kernel order changes
- Add environment-specific overrides in `environments:` section
- Use feature flag for gradual rollout
- Add validation for new config fields

**DO NOT:**
- Modify hard-coded `KERNEL_ORDER` in `kernel_loader.py`
- Skip validation for production config
- Deploy kernel changes without testing in dev/staging first
- Remove the fallback mechanism

## Related ADRs
- [ADR-0030: Kernel YAML Schema](./0030-kernel-yaml-schema.md)
- [ADR-0052: DI/DIP Foundation](./0052-di-dip-foundation.md)
