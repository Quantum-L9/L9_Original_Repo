# ADR 0036: Schema Organization Pattern

## Status

Accepted

## Pattern

L9 uses a **hybrid schema organization**: cross-domain infrastructure schemas live in `core/schemas/`, while domain-specific models are colocated as `{domain}/schemas.py`.

## Context

Schema files proliferated organically across the L9 codebase. Analysis of 364 schema imports across 174 files revealed two coexisting patterns that are architecturally sound and should be preserved:

1. **Centralized core schemas** — Shared infrastructure models used by 3+ domains
2. **Domain-colocated schemas** — Domain-specific models kept with their domain code

This hybrid approach balances discoverability with domain cohesion.

## Files

### Core Infrastructure Schemas (`core/schemas/`)

- `core/schemas/__init__.py` - Central exports for all infrastructure schemas
- `core/schemas/packet_envelope.py` - PacketEnvelope v1 (legacy)
- `core/schemas/packet_envelope_v2.py` - PacketEnvelope v2 (current)
- `core/schemas/tasks.py` - TaskStatus, TaskKind, AgentTask, TaskResult
- `core/schemas/capabilities.py` - ToolName, Capability, AgentCapabilities
- `core/schemas/event_stream.py` - SecurityEventType, AgentHandshake
- `core/schemas/ws_event_stream.py` - EventType, EventMessage, AgentHeartbeat
- `core/schemas/research_factory_models.py` - ResearchJobSpec, Query, QueryPlan
- `core/schemas/research_factory_state.py` - ResearchState, PassStatus
- `core/schemas/schema_registry.py` - SchemaRegistry singleton for version management
- `core/schemas/upcaster_registry.py` - Version migration upcasters
- `core/schemas/universal_schema.py` - Schema utilities

### Domain-Colocated Schemas

- `core/agents/schemas.py` - AgentTask, AgentConfig, ToolBinding, ExecutionResult
- `core/kernels/schemas.py` - KernelManifest, KernelInfo, KernelRule, KernelState
- `core/governance/schemas.py` - Policy, EvaluationRequest, EvaluationResult
- `core/commands/schemas.py` - Command, IntentModel, CommandResult
- `core/worldmodel/l9_schema.py` - L9Agent, L9Tool, L9Infrastructure, L9Relationship
- `core/agents/graph_state/schema.py` - Neo4j Cypher query constants
- `ir_engine/ir_schema.py` - IntentNode, ConstraintNode, ActionNode, IRGraph

### YAML Validation Schemas (`config/schemas/`)

- `config/schemas/adr_schema.yaml` - ADR format validation schema
- `config/gmp/phase0-scope-schema.yaml` - GMP Phase 0 scope validation

## Import Block

```python
# Core infrastructure schemas (cross-domain)
from core.schemas import (
    PacketEnvelope,
    PacketKind,
    TaskStatus,
    TaskKind,
    AgentTask,
    AgentCapabilities,
    EventType,
    EventMessage,
)

# Domain-specific schemas (import from domain)
from core.agents.schemas import AgentConfig, ExecutionResult, ToolBinding
from core.kernels.schemas import KernelManifest, KernelState, KernelType
from core.governance.schemas import Policy, EvaluationResult
from core.commands.schemas import Command, IntentModel
from core.worldmodel.l9_schema import L9Agent, L9Tool, EntityType
from ir_engine.ir_schema import IRGraph, IntentNode, ActionNode
```

## Minimal Implementation

```python
# Adding a new domain schema (colocated pattern)
# File: core/newdomain/schemas.py

"""
L9 NewDomain Schemas
====================

Domain-specific Pydantic models for the NewDomain module.
"""

from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class NewDomainStatus(str, Enum):
    """Status values for NewDomain entities."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


class NewDomainEntity(BaseModel):
    """Primary entity for NewDomain operations."""
    
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Entity name")
    status: NewDomainStatus = Field(default=NewDomainStatus.PENDING)
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    model_config = {"extra": "forbid"}


# MUST export __all__ for discoverability
__all__ = [
    "NewDomainStatus",
    "NewDomainEntity",
]
```

## Usage Example

```python
# Discovering schema locations programmatically
from core.schemas import SCHEMA_VERSION  # Infrastructure version

# Domain schema import
from core.agents.schemas import AgentTask, AgentConfig

# Create domain entity
task = AgentTask(
    agent_id="l9-standard-v1",
    payload={"message": "Hello"},
)

# Use with infrastructure schemas
from core.schemas import PacketEnvelope, PacketKind

packet = PacketEnvelope(
    packet_type=PacketKind.TASK,
    payload=task.model_dump(),
)
```

## Anti-Pattern Example

```python
# ❌ WRONG — Consolidating all schemas into one mega-module
# This breaks domain cohesion and creates import cycles
from core.schemas import (
    PacketEnvelope,      # Infrastructure ✓
    AgentConfig,         # Domain - should be in core/agents/schemas.py
    KernelManifest,      # Domain - should be in core/kernels/schemas.py
    Policy,              # Domain - should be in core/governance/schemas.py
)

# ❌ WRONG — Re-exporting domain schemas from core/schemas/__init__.py
# core/schemas/__init__.py
from core.agents.schemas import AgentConfig  # DON'T DO THIS
__all__ = [..., "AgentConfig"]  # Creates confusing dual-import paths

# ❌ WRONG — Creating new schema folders
# core/schemas/agents/  # NO - use core/agents/schemas.py instead
# schemas/governance/   # NO - use core/governance/schemas.py instead

# ✅ CORRECT — Import from canonical location
from core.schemas import PacketEnvelope           # Infrastructure
from core.agents.schemas import AgentConfig       # Domain
from core.kernels.schemas import KernelManifest   # Domain
from core.governance.schemas import Policy        # Domain
```

## Rules

1. **Cross-domain schemas** (used by 3+ domains) MUST go in `core/schemas/`
2. **Domain-specific schemas** MUST be colocated as `{domain}/schemas.py`
3. **YAML validation schemas** (JSON Schema format) MUST go in `config/schemas/`
4. All schema modules MUST export `__all__` for discoverability
5. New schemas MUST follow naming convention: `schemas.py` or `{domain}_schema.py`
6. Schema modules MUST NOT re-export schemas from other domains
7. Infrastructure schemas in `core/schemas/` MUST use SchemaRegistry for versioning
8. Domain schemas SHOULD include `__dora_meta__` header for observability

## AI Guidance

**DO:**

- Check `core/schemas/` first when looking for infrastructure models (PacketEnvelope, Tasks, Events)
- Look for `schemas.py` in the domain folder for domain-specific models
- Import from the canonical location — never re-export between domains
- Use `from core.schemas import X` for cross-domain infrastructure schemas
- Use `from core.{domain}.schemas import Y` for domain-specific schemas
- Add new domain schemas as `{domain}/schemas.py` colocated with domain code
- Include `__all__` exports in every schema module

**DO NOT:**

- Consolidate all schemas into `core/schemas/` — this breaks domain cohesion
- Create new schema directories like `schemas/` or `core/schemas/{domain}/`
- Re-export domain schemas from `core/schemas/__init__.py`
- Duplicate schema definitions across modules
- Skip the `__all__` export list
- Import from non-canonical locations (if two paths exist, use the shorter canonical one)

## Schema Location Decision Tree

```text
Is this schema used by 3+ domains?
├── YES → Put in core/schemas/
└── NO → Is it a YAML validation schema?
    ├── YES → Put in config/schemas/
    └── NO → Colocate as {domain}/schemas.py
```

## Related ADRs

- [ADR-0016: TypedDict vs Pydantic](./0016-typeddict-pydantic-boundary.md) - When to use TypedDict vs Pydantic BaseModel
- [ADR-0022: Registry Pattern](./0022-registry-pattern.md) - SchemaRegistry follows this pattern
- [ADR-0014: DORA Metadata Block](./0014-dora-metadata-block.md) - Schema files should include DORA headers
