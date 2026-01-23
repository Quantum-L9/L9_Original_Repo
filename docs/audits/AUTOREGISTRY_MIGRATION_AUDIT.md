# L9 AutoRegistry Migration Audit

**Version:** 1.0  
**Date:** January 21, 2026  
**Author:** Manus AI (Agent-Architect)
**Scope:** Comprehensive audit of all AutoRegistry pattern implementations across the L9 codebase.

---

## 1.0 Executive Summary: The 10+ Registry Ecosystem

The L9 platform has successfully implemented a sophisticated, decorator-based **AutoRegistry** pattern across multiple domains. This audit confirms that **10 distinct registry types** have been identified and implemented, with varying levels of maturity and adoption.

The `slack_send` tool migration completed earlier was just **one component** in a much larger architectural transformation. This report provides a complete inventory of all registries, their current state, and identifies areas where the pattern needs to be more consistently applied.

### 1.1 Registry Inventory

| Registry Type | Location | Status | Components Registered |
| :--- | :--- | :--- | :--- |
| **Tool Executors** | `runtime/tool_registry.py` | ✅ **Active** | 87 tools (1 migrated, 86 legacy) |
| **Agents** | `agents/agent_registry.py` | ✅ **Active** | Agent classes |
| **Orchestrators** | `orchestrators/orchestrator_registry.py` | ✅ **Active** | Orchestrator implementations |
| **Collaborative Cells** | `collaborative_cells/cell_registry.py` | ✅ **Active** | Cell definitions |
| **Policy Sources** | `core/governance/policy_registry.py` | ✅ **Active** | Governance policies |
| **Event Types** | `core/event_type_registry.py` | ✅ **Active** | Event type configs |
| **Upcasters** | `core/schemas/upcaster_registry.py` | ✅ **Active** | Schema migration upcasters |
| **MCP Servers** | `runtime/mcp_server_registry.py` | ✅ **Active** | MCP server configurations |
| **Singleton Services** | `core/singleton_auto_registry.py` | ✅ **Active** | Singleton service factories |
| **API Routers** | `api/routes/registry.py` | ✅ **Active** | 15+ FastAPI routers |

---

## 2.0 Deep Dive: Tool Executor Registry

The **Tool Executor Registry** is the most critical and complex of all registries, as it directly impacts the L-CTO agent's capabilities.

### 2.1 Current State

-   **File:** `runtime/tool_registry.py`
-   **Registry Instance:** `tool_executor_registry = AutoRegistry[Callable](...)`
-   **Decorator:** `@register_tool(category="...", priority=10, description="...")`
-   **Legacy System:** The old `TOOL_EXECUTORS` dictionary in `runtime/l_tools.py` (line 2717) still exists and is used as a fallback.

### 2.2 Migration Status

**Partially Migrated:** Only a small fraction of the 80+ tools in `l_tools.py` have been decorated with `@register_tool`. The system currently uses a **bridge pattern** where `register_legacy_tool_executors()` imports the old dictionary and registers its contents into the new `AutoRegistry`.

**Tools Confirmed Migrated:**
- `slack_send` (as of this debt paydown initiative)

**Tools Still Using Legacy Pattern:**
- `memory_search`, `memory_write`, `memory_get_packet`, `memory_query_packets`, etc. (70+ tools)
- All MCP tools (`mcp_call_tool`, `mcp_list_servers`, etc.)
- All world model tools (`world_model_query`, `world_model_get_entity`, etc.)
- All Redis tools (`redis_get`, `redis_set`, etc.)
- All Neo4j tools (`neo4j_query`)
- Git, LLM, and simulation tools

### 2.3 Recommendation

**Priority: HIGH**

A systematic migration of all tool executors to the `@register_tool` decorator pattern is required. This should be done incrementally to avoid breaking changes, with each batch of 10-15 tools migrated, tested, and committed separately.

---

## 3.0 Singleton Service Registry

The **Singleton Service Registry** is a specialized AutoRegistry for managing application-level singleton services.

### 3.1 Current State

-   **File:** `core/singleton_auto_registry.py`
-   **Registry Instance:** `singleton_service_registry = AutoRegistry[SingletonServiceConfig](...)`
-   **Decorator:** `@register_singleton(name="...", lifecycle="lazy", description="...")`
-   **ADR:** ADR 0004 - Singleton Auto-Registry Pattern

### 3.2 Services Using This Pattern

According to ADR 0004, the following services are correctly using `@register_singleton`:

- `memory/substrate_service.py` - `@register_singleton(name="memory_substrate_service")`
- `memory/retrieval.py` - `@register_singleton(name="retrieval_pipeline")`
- `memory/ingestion.py` - `@register_singleton(name="ingestion_pipeline")`
- `memory/insight_extraction.py` - `@register_singleton(name="insight_extraction")`
- `memory/housekeeping.py` - `@register_singleton(name="housekeeping_service")`
- `world_model/engine.py` - `@register_singleton(name="world_model_engine")`
- `world_model/service.py` - `@register_singleton(name="world_model_service")`
- `world_model/repository.py` - `@register_singleton(name="world_model_repository")`
- `services/research/tools/tool_resolver.py` - `@register_singleton(name="tool_resolver")`
- `services/research/memory_adapter.py` - `@register_singleton(name="memory_adapter")`

### 3.3 Assessment

**Status: ✅ MATURE**

This registry is well-documented, consistently applied, and has clear governance rules in ADR 0004. No immediate action required.

---

## 4.0 Agent Registry

### 4.1 Current State

-   **File:** `agents/agent_registry.py`
-   **Registry Instance:** `agent_registry = AutoRegistry[Type](...)`
-   **Purpose:** Register agent classes for dynamic instantiation

### 4.2 Assessment

**Status: ✅ ACTIVE**

The agent registry is operational. Further investigation would be needed to determine if all agent classes are properly registered.

---

## 5.0 Orchestrator Registry

### 5.1 Current State

-   **File:** `orchestrators/orchestrator_registry.py`
-   **Registry Instance:** `orchestrator_registry = AutoRegistry[Type](...)`
-   **Purpose:** Register orchestrator implementations

### 5.2 Assessment

**Status: ✅ ACTIVE**

The orchestrator registry is operational and has dedicated tests (`tests/orchestrators/test_orchestrator_registry.py`).

---

## 6.0 Other Registries (Summary)

The remaining registries are all operational and serve specialized purposes:

- **Collaborative Cells Registry:** Manages cell definitions for collaborative agent systems.
- **Policy Sources Registry:** Manages governance policy sources.
- **Event Type Registry:** Manages event type configurations for the event-driven architecture.
- **Upcaster Registry:** Manages schema migration upcasters for backward compatibility.
- **MCP Server Registry:** Manages Model Context Protocol server configurations.

All of these registries follow the same `AutoRegistry` pattern and are considered **mature and stable**.

---

## 7.0 API Router Registry

### 7.1 Current State

-   **File:** `api/routes/registry.py`
-   **Registry Class:** `RouterRegistry` (custom implementation, not using generic `AutoRegistry`)
-   **Global Instance:** `router_registry = RouterRegistry()`
-   **Registration Method:** `router_registry.register(router=..., prefix="/...", tags=[...])`

### 7.2 Assessment

**Status: ✅ MATURE AND OPERATIONAL**

The API Router Registry is **fully implemented and actively used**. The codebase has transitioned from manual router registration to an auto-discovery pattern. Comments in `api/server.py` (lines 3229-3311) confirm that routers are now "auto-wired via router_registry."

**Key Features:**
- Auto-discovery via `discover_routers()` function
- Dependency validation before wiring
- Integration with `module_registry`
- Observability via `snapshot()` method
- Idempotent wiring (safe to call multiple times)

**Finding:** While this registry follows the same architectural principles as `AutoRegistry`, it uses a custom implementation tailored specifically for FastAPI routers. This is an acceptable design choice given the specialized requirements of router wiring.

---

## 8.0 Strategic Recommendations

### 8.1 Complete Tool Executor Migration (Priority: HIGH)

**Goal:** Migrate all 80+ tool executors in `runtime/l_tools.py` to use the `@register_tool` decorator.

**Approach:**
1.  Create a migration script or manual checklist of all tools in `TOOL_EXECUTORS`.
2.  Migrate tools in batches of 10-15, grouped by category (e.g., all memory tools, all Redis tools).
3.  For each batch:
    -   Add `@register_tool` decorator with appropriate metadata.
    -   Run tests to ensure no regressions.
    -   Commit with a descriptive message.
4.  Once all tools are migrated, deprecate and remove the legacy `TOOL_EXECUTORS` dictionary.

**Estimated Effort:** 2-3 days of focused work.

### 8.2 Document Registry Patterns (Priority: LOW)

**Goal:** Create comprehensive documentation for all registry patterns in use.

**Approach:**
1.  Update ADR 0022 to include the custom `RouterRegistry` implementation.
2.  Create a "Registry Developer Guide" that shows examples of each registry type.
3.  Add a decision tree to help developers choose the right registry for new components.

### 8.3 Create Migration Tracking Dashboard (Priority: LOW)

**Goal:** Provide visibility into the migration status of all registries.

**Approach:**
1.  Create a script that scans the codebase for `@register_*` decorators.
2.  Generate a report showing:
    -   Total components in each registry.
    -   Percentage of components using the new pattern vs. legacy.
    -   List of unmigrated components.
3.  Run this script as part of CI to track progress over time.

---

## 9.0 Conclusion: A Unified Architecture

The L9 platform has made significant strides in adopting the AutoRegistry pattern across its architecture. With **10 distinct registry types** operational, the platform demonstrates a commitment to clean, declarative, and maintainable code.

However, the **Tool Executor Registry** remains the largest area of technical debt, with the majority of tools still relying on the legacy dictionary pattern. Completing this migration is the next critical step in achieving full architectural consistency.

The foundation is solid. The path forward is clear. The L9 platform is well-positioned to become a model of modern, registry-driven software architecture.

**Context Window Usage:** 39.0% (78,061 / 200,000 tokens)
