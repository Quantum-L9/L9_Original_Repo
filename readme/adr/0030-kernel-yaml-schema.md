# ADR 0030: Kernel YAML Schema

## Status
Accepted

## Pattern
10 governance kernels in YAML format; strict schema; loaded during 7-phase bootstrap.

## Files
- `private/kernels/00_system/*.yaml` - 10 governance kernels
- `runtime/kernel_loader.py` - Loader implementation
- `core/kernels/schemas.py` - Schema validation

## Import Block
```python
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Any
```

## Minimal Implementation
```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml
import hashlib
import structlog

logger = structlog.get_logger(__name__)

KERNEL_DIR = Path("private/kernels/00_system")
REQUIRED_KERNELS = [
    "01_master_kernel",
    "02_identity_kernel",
    "03_cognitive_kernel",
    "04_behavioral_kernel",
    "05_memory_kernel",
    "06_worldmodel_kernel",
    "07_execution_kernel",
    "08_safety_kernel",
    "09_developer_kernel",
    "10_packet_protocol_kernel",
]


@dataclass
class KernelSchema:
    """Schema for kernel YAML files."""
    kernel_id: str
    kernel_name: str
    version: str
    priority: int
    description: str
    rules: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    hash: str = ""


def load_kernel(kernel_name: str) -> KernelSchema:
    """
    Load and validate kernel from YAML.
    
    Args:
        kernel_name: Name of kernel file (without .yaml)
    
    Returns:
        Validated KernelSchema
    
    Raises:
        FileNotFoundError: If kernel file doesn't exist
        ValueError: If kernel fails validation
    """
    path = KERNEL_DIR / f"{kernel_name}.yaml"
    
    if not path.exists():
        raise FileNotFoundError(f"Kernel not found: {path}")
    
    content = path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    
    # Validate required fields
    required_fields = ["kernel_id", "kernel_name", "version", "priority"]
    for field_name in required_fields:
        if field_name not in data:
            raise ValueError(f"Kernel {kernel_name} missing required field: {field_name}")
    
    # Calculate hash for integrity
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    
    kernel = KernelSchema(
        kernel_id=data["kernel_id"],
        kernel_name=data["kernel_name"],
        version=data["version"],
        priority=data["priority"],
        description=data.get("description", ""),
        rules=data.get("rules", []),
        constraints=data.get("constraints", []),
        capabilities=data.get("capabilities", []),
        memory=data.get("memory", {}),
        hash=content_hash,
    )
    
    logger.debug(
        "kernel.loaded",
        kernel_id=kernel.kernel_id,
        version=kernel.version,
        hash=kernel.hash,
    )
    
    return kernel


def load_all_kernels() -> dict[str, KernelSchema]:
    """
    Load all 10 required kernels.
    
    Returns:
        Dict of kernel_name -> KernelSchema
    
    Raises:
        RuntimeError: If any kernel is missing
    """
    kernels = {}
    missing = []
    
    for kernel_name in REQUIRED_KERNELS:
        try:
            kernels[kernel_name] = load_kernel(kernel_name)
        except FileNotFoundError:
            missing.append(kernel_name)
    
    if missing:
        raise RuntimeError(f"Missing required kernels: {missing}")
    
    logger.info(
        "kernels.all_loaded",
        count=len(kernels),
        names=list(kernels.keys()),
    )
    
    return kernels
```

## Usage Example
```python
from runtime.kernel_loader import load_all_kernels, load_kernel

# Load all kernels at bootstrap
kernels = load_all_kernels()
# Returns: {"01_master_kernel": KernelSchema(...), ...}

# Load specific kernel
safety_kernel = load_kernel("08_safety_kernel")
print(safety_kernel.rules)
# ["No destructive operations without approval", ...]

# Use in agent initialization
for name, kernel in sorted(kernels.items(), key=lambda x: x[1].priority):
    await bind_kernel_to_agent(agent, kernel)
```

## Kernel YAML Template
```yaml
# private/kernels/00_system/08_safety_kernel.yaml
kernel_id: "safety-kernel-v1"
kernel_name: "Safety Kernel"
version: "1.0.0"
priority: 8
description: "Engineering safety constraints for L-CTO"

rules:
  - "No destructive operations without explicit Igor approval"
  - "All operations must emit audit packets"
  - "Fail closed on uncertainty"

constraints:
  - "Cannot modify files in private/kernels without GMP"
  - "Cannot execute shell commands without approval"
  - "Must log all tool invocations"

capabilities:
  - "memory_read"
  - "memory_write"
  - "tool_execute_safe"

memory:
  max_in_state_size_kb: 512
  retrieval_limit: 50
  retention_days: 90

created_at: "2026-01-01T00:00:00Z"
updated_at: "2026-01-20T00:00:00Z"
```

## 10 Kernel Files
| # | File | Purpose |
|---|------|---------|
| 01 | master_kernel.yaml | Top-level orchestration |
| 02 | identity_kernel.yaml | L's identity/persona |
| 03 | cognitive_kernel.yaml | Reasoning patterns |
| 04 | behavioral_kernel.yaml | Action constraints |
| 05 | memory_kernel.yaml | Memory access rules |
| 06 | worldmodel_kernel.yaml | World model integration |
| 07 | execution_kernel.yaml | Task execution flow |
| 08 | safety_kernel.yaml | Engineering safety |
| 09 | developer_kernel.yaml | Code quality rules |
| 10 | packet_protocol_kernel.yaml | Packet standards |

## Rules
1. ALL 10 kernels MUST be present
2. Kernels loaded in priority order (1→10)
3. Schema validation on load
4. Integrity hash verified
5. Missing kernel = bootstrap failure

## AI Guidance
**DO:**
- Maintain all 10 kernel files
- Follow schema exactly
- Update version on changes
- Verify hash after edits

**DO NOT:**
- Delete kernel files
- Skip schema validation
- Change priority without analysis
- Modify kernels without GMP
