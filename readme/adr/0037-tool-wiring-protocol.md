# ADR 0037: Tool Wiring Protocol

## Status

Accepted

## Pattern

Every tool must be fully wired: ToolDefinition + Executor + Export. Placeholder tools must be marked as FUTURE or DEPRECATED in source code.

## Context

L9 tools require multiple integration points to be functional:

1. **ToolDefinition** in `core/tools/tool_graph.py` - Metadata, capabilities, risk level
2. **Executor function** in `runtime/l_tools.py` - Actual implementation
3. **TOOL_EXECUTORS entry** - Registration in dispatch table
4. **Export** in `__all__` if in separate module

Tools missing any component are "loose stitches" - partially wired and unusable.

## Decision

### 1. Wiring Checklist (for /wire command)

Every tool MUST have:

- [ ] Function exists in `runtime/l_tools.py` or linked module
- [ ] Entry in `TOOL_EXECUTORS` dict
- [ ] ToolDefinition in `L_INTERNAL_TOOLS` or `L9_TOOLS`
- [ ] Exported in `__all__` if in separate module
- [ ] Test exists in `tests/`

### 2. Tool Status Categories

| Status         | Meaning                          | Source Code Marker                |
| -------------- | -------------------------------- | --------------------------------- |
| **ACTIVE**     | Fully wired, functional          | `# ACTIVE - Executor: ...`        |
| **FUTURE**     | Definition exists, awaiting impl | `# FUTURE FEATURE - NOT ORPHANED` |
| **DEPRECATED** | Superseded, do not implement     | `# DEPRECATED - DO NOT IMPLEMENT` |

### 3. Source Code Markers

Tools MUST be marked in `core/tools/tool_graph.py`:

```python
# ========================================================================
# FUTURE FEATURE - NOT ORPHANED
# [Tool Category] - Awaiting [integration/implementation]
# ========================================================================

# ========================================================================
# DEPRECATED - DO NOT IMPLEMENT
# Superseded by: [alternative tool names]
# ========================================================================

# ACTIVE - Executor: runtime/l_tools.py::[function_name]
```

### 4. No Orphaned Definitions

- Every ToolDefinition MUST have a status marker
- FUTURE tools must explain what's blocking implementation
- DEPRECATED tools must list the superseding alternatives

## Files

- `core/tools/tool_graph.py` - ToolDefinitions with status markers
- `runtime/l_tools.py` - Executor functions and TOOL_EXECUTORS
- `core/tools/research_tools.py` - Research tool executors
- `core/tools/base_registry.py` - Saga tool implementations

## Consequences

### Positive

- No "loose stitches" - partially wired tools are visible
- Agents know which tools are usable vs planned
- AI agents won't try to use DEPRECATED tools
- Clear path to implement FUTURE tools

### Negative

- More verbose source code with markers
- Requires discipline to maintain markers

## Compliance

### Before Adding a Tool

1. Create ToolDefinition with status marker
2. If ACTIVE: implement executor and wire to TOOL_EXECUTORS
3. If FUTURE: document blocking factor
4. Add to /wire checklist

### Before Deprecating a Tool

1. Identify superseding alternatives
2. Add DEPRECATED marker with alternatives
3. Do NOT remove definition (keep for documentation)
4. Eventually remove in cleanup pass

## Current Tool Status (2026-01-20)

| Category   | Count |
| ---------- | ----- |
| ACTIVE     | 87    |
| FUTURE     | 17    |
| DEPRECATED | 8     |

### FUTURE Features (Not Orphaned)

- `web_search` - Alternative: `run_research_query`
- `email_*` (6) - Awaiting email_agent/ integration
- `calendar_create` - Awaiting Google Calendar API
- `github_*` (3) - Awaiting MCP GitHub server
- `notion_*` (2) - Awaiting MCP Notion server
- `vercel_*` (2) - Awaiting MCP Vercel server
- `godaddy_*` (1) - Awaiting MCP GoDaddy server
- `graph_memory_*` (3) - Convenience wrappers

### DEPRECATED (Do Not Implement)

- `memory_read` → `memory_get_packet`, `memory_search`
- `hybrid_rag_search` → `memory_hybrid_search`
- `tool_router_list` → `tools_list_all`, `tools_list_enabled`
- `graph_memory_store` → `memory_write`, `neo4j_query`
- `cypher_template_*` (2) → `neo4j_query`
- `schema_introspect_*` (2) → Direct queries

## Related ADRs

- ADR-0017: Tool Definition Schema
- ADR-0022: Registry Pattern
- ADR-0034: Agent Capability Scoping
