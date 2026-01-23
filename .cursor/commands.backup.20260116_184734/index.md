---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "2.1.0"
component_id: "CMD-INDEX-001"
component_name: "Index - Repository Index Export + Neo4j Graph Load"
layer: "commands"
domain: "utilities"
type: "slash_command"
status: "active"
created: "2025-12-01T00:00:00Z"
updated: "2026-01-12T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "informational"
compliance_required: false
audit_trail: false
security_classification: "internal"

# === COMMAND METADATA ===
name: index
description: "Export repository indexes (33 files) and optionally load into Neo4j graph"
auto_chain: null
---

# === L9 INDEX: Repository Index Export + Neo4j Graph ===
# Cursor Slash Command: /index
# Version: 2.1.0 (L9-native)
# Updated: 2026-01-12
# Change: Added iCloud export to 00-LLM-00/L9-repo-index

---

## WHAT IT DOES

1. **Exports 33 repository index files** to `readme/repo-index/`
2. **Exports same files to iCloud** at `/Users/ib-mac/Library/Mobile Documents/com~apple~CloudDocs/00-LLM-00/L9-repo-index`
3. **Optionally loads indexes into Neo4j** for graph queries

### Index Files Generated

| Category | Files | Contents |
|----------|-------|----------|
| **Core** | `class_definitions.txt`, `function_signatures.txt` | 1,900+ classes, 4,794 functions |
| **Relationships** | `inheritance_graph.txt`, `method_catalog.txt` | 802 inheritance, 5,288 methods |
| **API** | `route_handlers.txt`, `pydantic_models.txt` | 180 routes, 470 Pydantic models |
| **Analysis** | `file_metrics.txt`, `async_function_map.txt` | Lines/complexity, 2,599 async functions |
| **Structure** | `tree.txt`, `wiring_map.txt`, `imports.txt` | Directory tree, module connections |

### Neo4j Graph Schema

When loaded to Neo4j, creates:

```
(:File {path, name, lines})
(:Class {name, file, docstring})
(:Function {name, file, args, is_async})
(:Method {name, class, args})
(:Route {method, path})
(:PydanticModel {name, file})

Relationships:
(File)-[:CONTAINS]->(Class|Function)
(Class)-[:EXTENDS]->(Class)
(Class)-[:HAS_METHOD]->(Method)
(Route)-[:HANDLED_BY]->(Function)
(File)-[:IMPORTS]->(Module)
```

---

## EXECUTION

### Quick (Indexes Only)

```bash
cd /Users/ib-mac/Projects/L9 && python3 tools/export_repo_indexes.py
```

**What this does:**
1. ✅ Exports 33 index files to `readme/repo-index/`
2. ✅ Copies same 33 files to iCloud: `/Users/ib-mac/Library/Mobile Documents/com~apple~CloudDocs/00-LLM-00/L9-repo-index`

### Full (Indexes + VPS Neo4j + Memory Summary)

**Recommended for session start:**

```bash
cd /Users/ib-mac/Projects/L9 && \
  python3 tools/export_repo_indexes.py && \
  python3 scripts/load_indexes_to_neo4j_vps.py
```

**What this does:**
1. ✅ Exports 33 index files to `readme/repo-index/`
2. ✅ Copies same 33 files to iCloud: `/Users/ib-mac/Library/Mobile Documents/com~apple~CloudDocs/00-LLM-00/L9-repo-index`
3. ✅ Loads repo structure to **L9 Neo4j** via MCP server (PRIMARY) or HTTP API (fallback)
4. ✅ Writes summary to **L9 memory** via MCP server for instant agent context
5. ✅ Efficient: Incremental updates, batched queries

**Legacy (Local Docker - fallback only):**

```bash
cd /Users/ib-mac/Projects/L9 && python3 tools/export_repo_indexes.py && python3 scripts/load_indexes_to_neo4j.py --local
```

### Export Locations

| Location | Path | Purpose |
|----------|------|---------|
| **Local Repo** | `readme/repo-index/` | Agent queries, grep searches |
| **iCloud Drive** | `/Users/ib-mac/Library/Mobile Documents/com~apple~CloudDocs/00-LLM-00/L9-repo-index` | Cross-device access, LLM context |

---

## WHEN TO RUN

| Scenario | Run /index? |
|----------|-------------|
| Session start | ✅ Auto-runs in startup |
| After major refactoring | ✅ Yes |
| After adding new files | ✅ Yes |
| After GMP completion | 🟡 Optional |
| Quick question | ❌ Use cached indexes |

---

## OUTPUT

```
📝 Generating indexes...

  🔌 Wiring map... ✅ (4,533 bytes)
  📋 Classes... ✅ (200,080 bytes)
  ⚙️  Functions (ALL)... ✅ (554,654 bytes)
  🧬 Inheritance graph... ✅ (56,032 bytes)
  🔍 Method catalog... ✅ (549,522 bytes)
  🛤️  Route handlers... ✅ (12,697 bytes)
  ... (33 files total)

📊 Total: 1,978,996 bytes (33 files)

📤 Copying to iCloud...
  ✅ Copied 33 files to /Users/ib-mac/Library/Mobile Documents/com~apple~CloudDocs/00-LLM-00/L9-repo-index

🔗 Loading to Neo4j... (if enabled)
  ✅ 1,921 Class nodes
  ✅ 802 EXTENDS relationships
  ✅ 5,288 HAS_METHOD relationships
  ✅ 180 Route nodes
```

---

## AGENT USAGE

After running `/index`, I can answer instantly:

| Question | Index File | Query |
|----------|------------|-------|
| "Where is class X?" | `class_definitions.txt` | grep |
| "What methods does X have?" | `method_catalog.txt` | grep |
| "What extends BaseAgent?" | `inheritance_graph.txt` | grep |
| "What handles POST /api/memory?" | `route_handlers.txt` | grep |
| "What are the biggest files?" | `file_metrics.txt` | head |

With Neo4j loaded:

```cypher
-- Find all classes that extend BaseAgent
MATCH (c:Class)-[:EXTENDS*]->(parent:Class {name: 'BaseAgent'})
RETURN c.name, c.file

-- Find what imports a module
MATCH (f:File)-[:IMPORTS]->(m:Module {name: 'memory.substrate_service'})
RETURN f.path
```

---

## INTEGRATION

- **Startup**: Runs automatically via `setup-new-workspace.yaml` → Uses VPS version
- **On-demand**: Type `/index` anytime
- **Governance rule**: `03-mcp-memory.mdc` references these indexes

## L9 MEMORY INTEGRATION (MCP Server PRIMARY)

When `/index` runs, it:

1. **Loads to L9 Neo4j Graph** (via MCP server tools or HTTP API fallback)
   - Files, Classes, Functions, Methods, Routes
   - Relationships: EXTENDS, HAS_METHOD, HANDLED_BY
   - Queryable via: MCP `graph_context` tool (PRIMARY) or HTTP `/api/v1/memory/graph/query` (fallback)

2. **Writes Summary to L9 Memory** (via MCP `save_memory` tool - PRIMARY)
   - Repo statistics (files, classes, functions, routes)
   - Relationship counts
   - Index file locations
   - Neo4j query examples
   - **Kind:** `insight` (searchable at session start)
   - **Note:** All writes flow through MCP ingestion pipeline for proper embedding and indexing

**Result:** At session start, agent has instant repo context without reading files.

## EFFICIENCY

- **Incremental:** Only clears/reloads if needed
- **Batched:** Queries in batches of 50-100
- **Minimal Overwrites:** Uses MERGE, not CREATE
- **Memory Summary:** Single write, not per-file
- **Token Efficient:** Summary is concise, not full file dumps
