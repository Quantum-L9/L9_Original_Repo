# ADR-0094: Tool Registry Primary Pipeline Unification

## Status

ACCEPTED

## Context

L9 currently has overlapping tool paths:

1. Runtime auto-registration path in `runtime/tool_registry.py` (`@register_tool`, `tool_executor_registry`, `get_tool_executors()`).
2. Primary dispatch/governance path in `core/tools/registry_adapter.py` (`ExecutorToolRegistry`, `create_executor_tool_registry()`, `app.state.tool_registry`).
3. Dynamic selection path in `core/tools/dynamic_discovery.py` (`discover_tools_for_task()`), which should align with the primary dispatch path.

Recent startup failures showed import drift and symbol mismatch between these paths. This increases fragility, causes startup regressions, and creates duplicate operational surfaces.

## Decision

### Practical Rule

New code MUST depend on:

- `create_executor_tool_registry(...)` and/or `app.state.tool_registry`
- `core.tools.base_registry.get_tool_registry`
- `discover_tools_for_task(...)`

New code MUST NOT depend on:

- `runtime.tool_registry.get_tool_executors()`
- direct `tool_executor_registry` access (except in a temporary bridge layer)

### Naming Rule

- Keep Python naming convention: class `ExecutorToolRegistry`.
- Keep Python naming convention: factory `create_executor_tool_registry`.
- Do not rename factory functions to PascalCase.

## 3-Step Migration Plan

### Step 1: Stabilize Imports and Contracts

Scope:

- Replace invalid/legacy imports that read from `runtime.tool_registry` for base registry access.
- Ensure startup-critical modules use `core.tools.base_registry.get_tool_registry`.

Exit criteria:

- No production import of `get_tool_registry` from `runtime.tool_registry`.
- Agent Executor import chain initializes cleanly.

### Step 2: Add a Bridge for Runtime Auto-Registered Tools

Scope:

- Keep runtime decorators operational short-term.
- Add one bridge that syncs/discovers runtime-registered tool executors into the base/adapter-backed pipeline during startup.
- Constrain all runtime direct access to `tool_executor_registry` to this bridge layer.

Exit criteria:

- API dispatch remains through `ExecutorToolRegistry`.
- Runtime tools are available via primary pipeline without direct secondary access from feature code.

### Step 3: Deprecate Secondary Access in Feature Code

Scope:

- Migrate callers away from `get_tool_executors()` and direct `tool_executor_registry`.
- Keep compatibility shim only where unavoidable and mark deprecated.
- Enforce via lint/check rule to block new dependencies on secondary path.

Exit criteria:

- Feature/runtime paths use a single primary dispatch surface (`ExecutorToolRegistry` + base registry + dynamic discovery).
- Secondary registry is bridge-only and removable.

## Consequences

### Positive

- Single dispatch surface for governance, approval, and observability.
- Lower startup fragility from import drift.
- Clear policy for new code and reviews.

### Negative

- Temporary bridge maintenance while legacy runtime decorators are phased out.
- Requires targeted migration across modules that currently read `get_tool_executors()`.

## Compliance

This ADR is enforced by:

- Code review checks for prohibited imports/usages listed above.
- Startup smoke checks validating `core.agents.executor` import and tool dispatch readiness.
- Future CI gate to reject new `runtime.tool_registry.get_tool_executors()` dependencies outside bridge files.
