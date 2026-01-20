# Orchestration Module

**Path:** `orchestration/`  
**Purpose:** Multi-agent coordination and workflow orchestration  
**Files:** 11 Python files  
**Last Updated:** 2026-01-18

---

## Overview

The `orchestration` module provides infrastructure for coordinating multiple agents, managing complex workflows, and executing multi-step tasks across the L9 platform.

## Key Components

- **`unified_controller.py`** - Central orchestration controller (831 lines)
- **`plan_executor.py`** - Executes multi-step plans (903 lines)
- **`orchestrator_registry.py`** - Registry for orchestrator discovery
- **`task_decomposer.py`** - Breaks complex tasks into subtasks
- **`agent_coordinator.py`** - Coordinates agent interactions

## Usage

```python
from orchestration.unified_controller import UnifiedController

controller = UnifiedController(kernel)
result = await controller.execute_workflow(workflow_spec)
```

## Architecture

**Orchestration Flow:**
1. Task decomposition
2. Agent selection
3. Parallel/sequential execution
4. Result aggregation
5. Error handling and retry

## Related Modules

- **`agents/`** - Agent implementations
- **`runtime/`** - Task queue and execution
- **`core/agents/`** - Agent executor

---

**Status:** Production  
**Maintainer:** L-CTO Agent
