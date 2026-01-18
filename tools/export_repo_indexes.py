#!/usr/bin/env python3
"""
export_repo_indexes.py - Enhanced L9 Repository Index Generator
================================================================

Generates comprehensive repo index files for LLM context understanding.
Version 2.0: Includes agent initialization, memory architecture, governance,
migrations, feature flags, tests, and telemetry catalogs.

Works with distributed API architectures (memory APIs, agent routers, VPS-facing, local-dev).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Enhanced L9 Repository Index Generator",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "export_repo_indexes",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "OpenAI API", "PostgreSQL", "Redis"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import os
import structlog
import sys
import re
import ast
import fnmatch
from collections import defaultdict

# Configuration
logger = structlog.get_logger(__name__)

# Use L9_REPO_ROOT env var if set, otherwise fall back to default paths
_REPO_ROOT = os.getenv("L9_REPO_ROOT", "/Users/ib-mac/Projects/L9")
REPO_DIR = _REPO_ROOT
REPO_INDEX_DIR = os.path.join(_REPO_ROOT, "readme/repo-index")
DROPBOX_EXPORT_DIR = os.getenv(
    "L9_DROPBOX_EXPORT_DIR",
    "/Users/ib-mac/Dropbox/Repo_Dropbox_IB/L9-index-export"
)
ICLOUD_EXPORT_DIR = os.getenv(
    "L9_ICLOUD_EXPORT_DIR",
    "/Users/ib-mac/Library/Mobile Documents/com~apple~CloudDocs/00-LLM-00/L9-repo-index"
)

# Directories to skip
SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", ".cursor", ".dora", ".secrets",
    "l9/venv", "secrets", ".DS_Store", "node_modules", ".pytest_cache",
}

def load_gitignore_patterns():
    """Load and parse .gitignore patterns."""
    gitignore_path = os.path.join(REPO_DIR, ".gitignore")
    patterns = []
    if not os.path.exists(gitignore_path):
        return patterns
    try:
        with open(gitignore_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("!"):
                    continue
                patterns.append(line)
    except Exception:
        pass
    return patterns

def is_ignored(rel_path, patterns, is_dir=False):
    """Check if a path matches any gitignore pattern."""
    path_parts = rel_path.split(os.sep)
    basename = path_parts[-1] if path_parts else rel_path
    for pattern in patterns:
        if pattern.endswith("/"):
            pattern_dir = pattern.rstrip("/")
            if is_dir and (
                fnmatch.fnmatch(basename, pattern_dir)
                or fnmatch.fnmatch(rel_path, pattern_dir)
                or any(fnmatch.fnmatch(part, pattern_dir) for part in path_parts)
            ):
                return True
        else:
            if fnmatch.fnmatch(basename, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return True
            if any(fnmatch.fnmatch(part, pattern) for part in path_parts):
                return True
    return False

# =============================================================================
# ORIGINAL GENERATORS (kept for compatibility)
# =============================================================================

def generate_tree():
    """Generate tree.txt using actual directory structure, respecting .gitignore."""
    lines = []
    gitignore_patterns = load_gitignore_patterns()

    def walk_dir(path, prefix="", max_depth=3, current_depth=0, rel_path_prefix=""):
        if current_depth >= max_depth:
            return
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return
        filtered_entries = []
        for e in entries:
            if e in SKIP_DIRS:
                continue
            rel_path = os.path.join(rel_path_prefix, e) if rel_path_prefix else e
            full_path = os.path.join(path, e)
            is_dir = os.path.isdir(full_path)
            if is_ignored(rel_path, gitignore_patterns, is_dir=is_dir):
                continue
            filtered_entries.append(e)
        dirs = [e for e in filtered_entries if os.path.isdir(os.path.join(path, e))]
        files = [e for e in filtered_entries if os.path.isfile(os.path.join(path, e))]
        for f in files[:10]:
            lines.append(f"{prefix}├── {f}")
        if len(files) > 10:
            lines.append(f"{prefix}├── ... ({len(files) - 10} more files)")
        for i, d in enumerate(dirs):
            is_last = i == len(dirs) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{d}/")
            extension = "    " if is_last else "│   "
            new_rel_prefix = os.path.join(rel_path_prefix, d) if rel_path_prefix else d
            walk_dir(os.path.join(path, d), prefix + extension, max_depth, current_depth + 1, new_rel_prefix)

    lines.append("L9/")
    walk_dir(REPO_DIR, "", max_depth=3, current_depth=0, rel_path_prefix="")
    return "\n".join(lines)

def generate_api_surfaces():
    """Map all callable interfaces across different API surface types."""
    api_surfaces = defaultdict(list)
    router_pattern = re.compile(r"(\w+)\s*=\s*(?:APIRouter|Router)\(")
    callable_pattern = re.compile(r"(?:def|async def)\s+(\w+)\s*\(")
    surface_types = {
        "memory": os.path.join(REPO_DIR, "memory"),
        "agents": os.path.join(REPO_DIR, "agents"),
        "api": os.path.join(REPO_DIR, "api"),
        "services": os.path.join(REPO_DIR, "services"),
        "orchestration": os.path.join(REPO_DIR, "orchestration"),
    }
    for surface_name, search_path in surface_types.items():
        if not os.path.isdir(search_path):
            continue
        for root, dirs, files in os.walk(search_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fname in files:
                if fname.endswith(".py"):
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            routers = router_pattern.findall(content)
                            if routers:
                                rel_path = os.path.relpath(fpath, REPO_DIR)
                                for router in routers:
                                    api_surfaces[surface_name].append(f"  {rel_path}::{router}")
                            callables = callable_pattern.findall(content)
                            if callables and ("handler" in fname or "interface" in fname):
                                rel_path = os.path.relpath(fpath, REPO_DIR)
                                for callable_name in callables[:3]:
                                    api_surfaces[surface_name].append(f"  {rel_path}::{callable_name}()")
                    except Exception:
                        pass
    if api_surfaces:
        lines = []
        for surface_type in ["api", "agents", "services", "memory", "orchestration"]:
            if surface_type in api_surfaces:
                lines.append(f"\n# {surface_type.upper()} Surface:")
                lines.extend(sorted(set(api_surfaces[surface_type]))[:20])
        return "\n".join(lines)
    return "No API surfaces found."

def generate_entrypoints():
    """Identify app entrypoints with useful metadata."""
    entrypoints = []
    gitignore_patterns = load_gitignore_patterns()
    fastapi_pattern = re.compile(r'app\s*=\s*FastAPI\s*\([^)]*title\s*=\s*["\']([^"\']+)["\']', re.DOTALL)
    uvicorn_pattern = re.compile(r"uvicorn\.run\s*\([^)]*\)", re.DOTALL)
    main_block_pattern = re.compile(r'if\s+__name__\s*==\s*["\']__main__["\']\s*:')

    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not is_ignored(
            os.path.relpath(os.path.join(root, d), REPO_DIR), gitignore_patterns, is_dir=True)]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, REPO_DIR)
            if is_ignored(rel_path, gitignore_patterns, is_dir=False):
                continue
            if "test" in fname.lower() or "tests" in root:
                continue
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    entry_info = {"path": rel_path, "type": None, "title": None, "port": None, "host": None, "has_main": False, "routes": []}
                    if re.search(r"\bapp\s*=\s*FastAPI\s*\(", content):
                        entry_info["type"] = "FastAPI"
                        fastapi_match = fastapi_pattern.search(content)
                        if fastapi_match:
                            entry_info["title"] = fastapi_match.group(1)
                        route_pattern = re.compile(r'@(?:app|router)\.(get|post|put|delete|patch|websocket|options|head)\s*\(["\']([^"\']+)["\']')
                        routes = route_pattern.findall(content)
                        entry_info["routes"] = [f"{method.upper()} {path}" for method, path in routes[:15]]
                        include_pattern = re.compile(r'\.include_router\s*\([^,]+,\s*prefix\s*=\s*["\']([^"\']+)["\']')
                        includes = include_pattern.findall(content)
                        if includes:
                            entry_info["routes"].extend([f"ROUTER {prefix}/*" for prefix in includes[:5]])
                    uvicorn_match = uvicorn_pattern.search(content)
                    if uvicorn_match:
                        host_match = re.search(r'host\s*=\s*["\']([^"\']+)["\']', content)
                        port_match = re.search(r"port\s*=\s*(\d+)", content)
                        if host_match:
                            entry_info["host"] = host_match.group(1)
                        if port_match:
                            entry_info["port"] = port_match.group(1)
                        entry_info["type"] = entry_info["type"] or "Uvicorn"
                    if main_block_pattern.search(content):
                        entry_info["has_main"] = True
                        if not entry_info["type"]:
                            entry_info["type"] = "Script"
                    if entry_info["type"] or entry_info["has_main"]:
                        lines_out = [f"{rel_path}"]
                        if entry_info["type"]:
                            lines_out.append(f"  Type: {entry_info['type']}")
                        if entry_info["title"]:
                            lines_out.append(f"  Title: {entry_info['title']}")
                        if entry_info["host"] or entry_info["port"]:
                            addr = f"{entry_info['host'] or 'localhost'}:{entry_info['port'] or '8000'}"
                            lines_out.append(f"  Address: {addr}")
                        if entry_info["routes"]:
                            lines_out.append(f"  Routes ({len(entry_info['routes'])}):")
                            for route in entry_info["routes"][:10]:
                                lines_out.append(f"    - {route}")
                            if len(entry_info["routes"]) > 10:
                                lines_out.append(f"    ... and {len(entry_info['routes']) - 10} more")
                        if entry_info["has_main"] and entry_info["type"] != "FastAPI":
                            lines_out.append("  Has __main__ block: Yes")
                        entrypoints.append("\n".join(lines_out))
            except Exception:
                pass
    if entrypoints:
        lines = ["# Entry Points\n"]
        lines.extend(sorted(set(entrypoints)))
        return "\n".join(lines)
    return "No entrypoints found."

def generate_env_refs():
    """Extract environment variable references."""
    env_vars = set()
    getenv_pattern = re.compile(r'os\.(?:getenv|environ)\.get\(["\']([A-Za-z_][A-Za-z0-9_]*)["\']')
    environ_pattern = re.compile(r'os\.environ\[["\']([A-Za-z_][A-Za-z0-9_]*)["\']')
    dotenv_pattern = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=", re.MULTILINE)
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        env_vars.update(getenv_pattern.findall(content))
                        env_vars.update(environ_pattern.findall(content))
                except Exception:
                    pass
            elif fname.startswith(".env"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        env_vars.update(dotenv_pattern.findall(content))
                except Exception:
                    pass
    if env_vars:
        return "\n".join(sorted(env_vars))
    return "No environment variables found."

def generate_imports():
    """Extract top-level Python imports from source code."""
    imports = defaultdict(set)
    import_pattern = re.compile(r"^(?:import|from)\s+([\w\.]+)", re.MULTILINE)
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        matches = import_pattern.findall(content)
                        for match in matches:
                            top_level = match.split(".")[0]
                            imports[top_level].add(match)
                except Exception:
                    pass
    if imports:
        lines = []
        for top_level in sorted(imports.keys()):
            lines.append(f"# {top_level}")
            for imp in sorted(imports[top_level]):
                lines.append(f"  {imp}")
        return "\n".join(lines)
    return "No imports found."

def generate_dependencies():
    """Parse requirements.txt and show actual vs declared dependencies."""
    lines = ["# Dependencies from requirements.txt\n"]
    req_file = os.path.join(REPO_DIR, "requirements.txt")
    if os.path.exists(req_file):
        try:
            with open(req_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        lines.append(line)
        except Exception:
            pass
    return "\n".join(lines) if len(lines) > 1 else "No requirements.txt found."

def generate_class_definitions():
    """Extract class definitions with docstrings."""
    classes = []
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read())
                        rel_path = os.path.relpath(fpath, REPO_DIR)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                docstring = ast.get_docstring(node) or "No docstring"
                                docstring = docstring.split("\n")[0][:60]
                                classes.append(f"{rel_path}::{node.name} - {docstring}")
                except Exception:
                    pass
    if classes:
        return "\n".join(sorted(classes))
    return "No classes found."

def generate_function_signatures():
    """Extract function names and signatures."""
    functions = []
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read())
                        rel_path = os.path.relpath(fpath, REPO_DIR)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                args = [arg.arg for arg in node.args.args]
                                signature = f"{node.name}({', '.join(args)})"
                                docstring = ast.get_docstring(node) or ""
                                docstring = docstring.split("\n")[0][:40] if docstring else ""
                                functions.append(f"{rel_path}::{signature} - {docstring}")
                except Exception:
                    pass
    if functions:
        return "\n".join(sorted(functions))
    return "No functions found."

def generate_config_files():
    """List all configuration files."""
    config_patterns = [".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", "Dockerfile", "docker-compose"]
    config_files = []
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if any(fname.endswith(ext) or fname.startswith(ext) for ext in config_patterns):
                rel_path = os.path.relpath(os.path.join(root, fname), REPO_DIR)
                config_files.append(rel_path)
    if config_files:
        return "\n".join(sorted(set(config_files)))
    return "No config files found."

def generate_module_architecture():
    """Map module structure and purposes from __init__.py docstrings."""
    architecture = []
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        if "__init__.py" in files:
            rel_path = os.path.relpath(root, REPO_DIR)
            if rel_path == ".":
                continue
            init_file = os.path.join(root, "__init__.py")
            try:
                with open(init_file, "r", encoding="utf-8", errors="ignore") as f:
                    docstring = f.read(500)
                    docstring = docstring.split('"""')[1] if '"""' in docstring else "No module docstring"
                    docstring = docstring.split("\n")[0][:60]
                    architecture.append(f"{rel_path}/ - {docstring}")
            except Exception:
                pass
    if architecture:
        return "\n".join(sorted(architecture))
    return "No module architecture found."

# =============================================================================
# EXISTING WIRING & CATALOG GENERATORS
# =============================================================================

def generate_wiring_map():
    """Generate high-level wiring/execution spine map."""
    lines = [
        "# L9 Wiring Map",
        "# ==============",
        "# How components connect: Entrypoint → Orchestration → Memory → Persistence",
        "",
        "## EXECUTION SPINE",
        "",
        "```",
        "uvicorn api.server:app",
        "    │",
        "    ▼",
        "┌─────────────────────────────────────────────────────────┐",
        "│  api/server.py (FastAPI)                                │",
        "│                                                         │",
        "│  lifespan():                                           │",
        "│    1. run_migrations()  → migrations/*.sql             │",
        "│    2. init_service()    → memory substrate (Postgres)  │",
        "│    3. get_neo4j_client() → Neo4j graph DB              │",
        "│    4. get_redis_client() → Redis cache/queues          │",
        "│    5. bootstrap_agent()  → 7-phase agent init (NEW!)   │",
        "└─────────────────────────────────────────────────────────┘",
        "    │",
        "    ▼ Routers mounted",
        "┌─────────────────────────────────────────────────────────┐",
        "│  ROUTERS                                                │",
        "│                                                         │",
        "│  /os/*        → api/os_routes.py         (health)      │",
        "│  /agent/*     → api/agent_routes.py      (tasks)       │",
        "│  /memory/*    → api/memory/router.py     (packets)     │",
        "│  /world-model/* → api/world_model_api.py (entities)    │",
        "│  /ws/agent    → WebSocket handler        (real-time)   │",
        "│  /metrics     → Prometheus metrics       (telemetry)   │",
        "└─────────────────────────────────────────────────────────┘",
        "```",
        "",
        "## AGENT BOOTSTRAP SPINE (7-Phase Ceremony)",
        "",
        "```",
        "bootstrap_agent(config, substrate)",
        "    │",
        "    ├─ Phase 0: validate_agent_blueprint()   → Validate config",
        "    ├─ Phase 1: load_and_parse_kernels()     → 10 governance kernels",
        "    ├─ Phase 2: instantiate_agent()          → Create AgentInstance",
        "    ├─ Phase 3: bind_kernels_to_agent()      → Attach kernels",
        "    ├─ Phase 4: load_identity_persona()      → Load L identity",
        "    ├─ Phase 5: bind_tools_and_capabilities()→ Wire tools + memory",
        "    ├─ Phase 6: wire_governance_gates()      → Approval gates",
        "    └─ Phase 7: verify_and_lock()            → Lock + signature",
        "```",
        "",
        "## MEMORY DAG PIPELINE",
        "",
        "```",
        "ingest_packet()",
        "    │",
        "    ▼",
        "┌─────────────────────────────────────────────────────────┐",
        "│  SubstrateDAG.run()                                     │",
        "│       │                                                 │",
        "│       ├→ intake_node                                   │",
        "│       ├→ reasoning_node                                │",
        "│       ├→ memory_write_node                             │",
        "│       ├→ semantic_embed_node                           │",
        "│       ├→ extract_insights_node                         │",
        "│       ├→ store_insights_node                           │",
        "│       ├→ world_model_trigger_node                      │",
        "│       └→ checkpoint_node                               │",
        "└─────────────────────────────────────────────────────────┘",
        "```",
        "",
        "## PERSISTENCE LAYER",
        "",
        "| Service | Container | Port | Purpose |",
        "|---------|-----------|------|---------|",
        "| PostgreSQL + pgvector | l9-postgres | 5432 | Packet store, semantic memory |",
        "| Neo4j Graph DB | l9-neo4j | 7687 | Entity graph, tool registry |",
        "| Redis | redis | 6379 | Task queue, rate limiting, cache |",
        "",
        "## KEY SINGLETONS",
        "",
        "| Singleton | Module | Purpose |",
        "|-----------|--------|---------|",
        "| ws_orchestrator | runtime.websocket_orchestrator | WebSocket connection manager |",
        "| _service | memory.substrate_service | Memory substrate singleton |",
        "| _repository | memory.substrate_repository | PostgreSQL connection pool |",
        "| _world_model_engine | world_model.engine | World model singleton |",
        "| _neo4j_client | memory.graph_client | Neo4j graph client |",
        "| _redis_client | runtime.redis_client | Redis cache/queue client |",
    ]
    return "\n".join(lines)

def generate_agent_catalog():
    """Generate catalog of all agents with roles and capabilities."""
    lines = [
        "# L9 Agent Catalog",
        "# =================",
        "# All agents with their roles, models, and tool bindings.",
        "",
    ]
    agents_dir = os.path.join(REPO_DIR, "agents")
    if os.path.isdir(agents_dir):
        lines.append("## Core Agents (agents/)")
        lines.append("")
        for fname in sorted(os.listdir(agents_dir)):
            if fname.endswith(".py") and not fname.startswith("__"):
                fpath = os.path.join(agents_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(2000)
                        class_match = re.search(r'class\s+(\w+).*?(?:"""(.*?)"""|\'\'\'(.*?)\'\'\')', content, re.DOTALL)
                        if class_match:
                            class_name = class_match.group(1)
                            docstring = (class_match.group(2) or class_match.group(3) or "").strip()
                            docstring = docstring.split("\n")[0][:80] if docstring else "No docstring"
                            lines.append(f"- **{class_name}** (`{fname}`)")
                            lines.append(f"  - {docstring}")
                            lines.append("")
                except Exception:
                    pass
    # Parse config/agents/ YAML files
    config_agents_dir = os.path.join(REPO_DIR, "config", "agents")
    if os.path.isdir(config_agents_dir):
        lines.extend(["", "## Configured Agents (config/agents/)", ""])
        for fname in sorted(os.listdir(config_agents_dir)):
            if fname.endswith((".yaml", ".yml")):
                fpath = os.path.join(config_agents_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        import yaml
                        data = yaml.safe_load(f)
                        if data:
                            agent_id = data.get("agent_id") or data.get("id", fname)
                            name = data.get("name", agent_id)
                            model = data.get("model", "gpt-4o")
                            tools = data.get("tools", [])
                            lines.append(f"- **{name}** (id: `{agent_id}`)")
                            lines.append(f"  - Model: {model}")
                            lines.append(f"  - Tools: {len(tools)}")
                            lines.append("")
                except Exception:
                    pass
    lines.extend([
        "", "## Agent Layers", "",
        "```",
        "                    ┌─────────────┐",
        "                    │   IGOR      │  (Human authority)",
        "                    └──────┬──────┘",
        "                           │ escalation",
        "                    ┌──────▼──────┐",
        "                    │   L (CTO)   │  (AI OS core agent)",
        "                    └──────┬──────┘",
        "            ┌──────────────┼──────────────┐",
        "            ▼              ▼              ▼",
        "     ┌────────────┐ ┌────────────┐ ┌────────────┐",
        "     │ Research   │ │ Architect  │ │ Coder      │",
        "     │ Agents     │ │ Agents     │ │ Agents     │",
        "     └────────────┘ └────────────┘ └────────────┘",
        "```",
        "",
        "## Authority Hierarchy",
        "",
        "Igor > L (CTO) > Research agents > Mac agent",
    ])
    return "\n".join(lines)

def generate_kernel_catalog():
    """Generate catalog of the 10 governance kernels."""
    lines = [
        "# L9 Kernel Catalog",
        "# ==================",
        "# 10 governance/identity/behavior kernels that define L's identity and constraints.",
        "",
        "## Kernel Stack (private/kernels/00_system/)",
        "",
    ]
    kernel_dir = os.path.join(REPO_DIR, "private", "kernels", "00_system")
    if os.path.isdir(kernel_dir):
        for fname in sorted(os.listdir(kernel_dir)):
            if fname.endswith((".yaml", ".yml")) and not fname.startswith("_"):
                fpath = os.path.join(kernel_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        import yaml
                        data = yaml.safe_load(f)
                        if data:
                            kernel_id = data.get("kernel_id", fname.replace(".yaml", ""))
                            name = data.get("name", kernel_id)
                            version = data.get("version", "1.0")
                            purpose = data.get("purpose", data.get("description", ""))
                            if isinstance(purpose, str):
                                purpose = purpose.split("\n")[0][:100]
                            lines.extend([
                                f"### {fname}",
                                f"- **ID**: {kernel_id}",
                                f"- **Name**: {name}",
                                f"- **Version**: {version}",
                                f"- **Purpose**: {purpose}",
                                "",
                            ])
                except Exception:
                    pass
    lines.extend(["", "## Kernel Loading (7-Phase Bootstrap)", ""])
    lines.append("| Phase | Function | Purpose |")
    lines.append("|-------|----------|---------|")
    lines.append("| 1 | load_and_parse_kernels() | Load all 10 YAML kernels |")
    lines.append("| 3 | bind_kernels_to_agent() | Attach kernels to AgentInstance |")
    lines.append("| 6 | wire_governance_gates() | Apply safety constraints |")
    return "\n".join(lines)

def generate_tool_catalog():
    """Generate catalog of all tools with metadata."""
    lines = [
        "# L9 Tool Catalog",
        "# ================",
        "# All tools with category, scope, risk level, and approval requirements.",
        "",
        "## High-Risk Tools (Require Igor Approval)",
        "",
        "| Tool | Description |",
        "|------|-------------|",
        "| `gmp_run` | Execute GMP protocol (code changes) |",
        "| `git_commit` | Commit changes to git repository |",
        "| `git_push` | Push changes to remote repository |",
        "| `file_delete` | Delete files from filesystem |",
        "| `database_write` | Write to production database |",
        "| `deploy` | Deploy to production environment |",
        "| `mac_agent_exec` | Execute commands on Mac agent |",
        "",
        "## Memory Tools (Registered in Phase 5)",
        "",
        "| Tool | Purpose |",
        "|------|---------|",
        "| `memory_search` | Search memory substrate (semantic + keyword) |",
        "| `memory_write` | Write packets to memory substrate |",
        "",
        "## Tool Scopes",
        "",
        "| Scope | Description |",
        "|-------|-------------|",
        "| `internal` | L9-internal operations, no external calls |",
        "| `external` | Calls external APIs (GitHub, Notion, etc.) |",
        "| `requires_igor_approval` | High-risk, needs explicit Igor approval |",
    ]
    return "\n".join(lines)

def generate_orchestrator_catalog():
    """Generate catalog of all orchestrators."""
    lines = [
        "# L9 Orchestrator Catalog",
        "# ========================",
        "# Agent coordination patterns for the L9 platform.",
        "",
        "## Available Orchestrators",
        "",
    ]
    orchestrators = [
        ("action_tool", "Tool execution with validation and error handling"),
        ("evolution", "Self-improvement via feedback loops and pattern adaptation"),
        ("memory", "Memory housekeeping, garbage collection, and optimization"),
        ("meta", "Meta-reasoning for strategy selection and reflection"),
        ("reasoning", "Inference chain coordination with confidence tracking"),
        ("research_swarm", "Multi-agent research with convergence and synthesis"),
        ("world_model", "World model updates, scheduling, and causal inference"),
    ]
    for name, description in orchestrators:
        orch_dir = os.path.join(REPO_DIR, "orchestrators", name)
        if os.path.isdir(orch_dir):
            files = [f for f in os.listdir(orch_dir) if f.endswith(".py") and not f.startswith("__")]
            lines.extend([
                f"### {name}/",
                f"**Purpose:** {description}",
                f"**Files:** {', '.join(files)}",
                "",
            ])
    return "\n".join(lines)

def generate_event_types():
    """Generate catalog of event types and packet kinds."""
    lines = [
        "# L9 Event Types",
        "# ===============",
        "# PacketEnvelope kinds, event types, and schema information.",
        "",
        "## PacketKind Enum",
        "",
        "| Kind | Description |",
        "|------|-------------|",
        "| `EVENT` | General event |",
        "| `INSIGHT` | Extracted insight |",
        "| `RESULT` | Execution result |",
        "| `ERROR` | Error event |",
        "| `COMMAND` | Command packet |",
        "| `QUERY` | Query packet |",
        "",
        "## Memory DAG Pipeline Events",
        "",
        "| Stage | Event | Description |",
        "|-------|-------|-------------|",
        "| 1 | `intake` | Packet received and validated |",
        "| 2 | `reasoning` | Reasoning trace extracted |",
        "| 3 | `memory_write` | Packet written to store |",
        "| 4 | `semantic_embed` | Vector embedding generated |",
        "| 5 | `extract_insights` | Insights extracted |",
        "| 6 | `store_insights` | Insights stored |",
        "| 7 | `world_model_trigger` | World model update triggered |",
        "| 8 | `checkpoint` | DAG state checkpointed |",
    ]
    return "\n".join(lines)

def generate_singleton_registry():
    """Generate registry of key singleton instances."""
    lines = [
        "# L9 Singleton Registry",
        "# ======================",
        "# Key singleton instances and their modules.",
        "",
        "## Core Singletons",
        "",
        "| Singleton | Module | Purpose | Init |",
        "|-----------|--------|---------|------|",
        "| `ws_orchestrator` | runtime.websocket_orchestrator | WebSocket connection manager | Startup |",
        "| `_service` | memory.substrate_service | Memory substrate singleton | Lazy |",
        "| `_repository` | memory.substrate_repository | PostgreSQL connection pool | Lazy |",
        "| `_world_model_engine` | world_model.engine | World model singleton | Lazy |",
        "| `_neo4j_client` | memory.graph_client | Neo4j graph database client | Lazy |",
        "| `_redis_client` | runtime.redis_client | Redis cache/queue client | Lazy |",
        "",
        "## Lifecycle",
        "",
        "1. **Startup** (`lifespan()` in api/server.py):",
        "   - `run_migrations()` - Apply SQL migrations",
        "   - `init_service()` - Initialize memory substrate",
        "   - `get_neo4j_client()` - Connect to Neo4j",
        "   - `get_redis_client()` - Connect to Redis",
        "   - `bootstrap_agent()` - Run 7-phase agent init",
        "",
        "2. **Shutdown** (`lifespan()` exit):",
        "   - `close_service()` - Close memory substrate",
        "   - `close_neo4j_client()` - Close Neo4j",
        "   - `close_redis_client()` - Close Redis",
    ]
    return "\n".join(lines)

# =============================================================================
# NEW GENERATORS (v2.0) - Agent Init, Memory, Governance, Migrations, etc.
# =============================================================================

def generate_bootstrap_phases():
    """Generate catalog of 7-phase agent initialization ceremony."""
    lines = [
        "# L9 Agent Bootstrap Phases",
        "# ==========================",
        "# 7-phase atomic agent initialization ceremony.",
        "# All phases must succeed or entire initialization rolls back.",
        "",
        "## Feature Flag",
        "",
        "| Flag | Description | Default |",
        "|------|-------------|---------|",
        "| `L9_NEW_AGENT_INIT` | Enable 7-phase bootstrap | `true` |",
        "",
        "## Phase Breakdown",
        "",
        "| Phase | File | Function | Purpose |",
        "|-------|------|----------|---------|",
        "| 0 | phase_0_validate.py | `validate_agent_blueprint()` | Validate config schema, check agent_id uniqueness |",
        "| 1 | phase_1_load_kernels.py | `load_and_parse_kernels()` | Load 10 governance YAML kernels |",
        "| 2 | phase_2_instantiate.py | `instantiate_agent()` | Create AgentInstance, register in Neo4j |",
        "| 3 | phase_3_bind_kernels.py | `bind_kernels_to_agent()` | Attach kernels via GOVERNED_BY edges |",
        "| 4 | phase_4_load_identity.py | `load_identity_persona()` | Load L identity from 02-identity kernel |",
        "| 5 | phase_5_bind_tools.py | `bind_tools_and_capabilities()` | Wire tools + memory_search + memory_write |",
        "| 6 | phase_6_wire_governance.py | `wire_governance_gates()` | Apply approval gates from safety kernel |",
        "| 7 | phase_7_verify_and_lock.py | `verify_and_lock()` | Verify all phases, generate init signature |",
        "",
        "## Directory Structure",
        "",
        "```",
        "core/agents/bootstrap/",
        "├── __init__.py",
        "├── orchestrator.py         # AgentBootstrapOrchestrator",
        "├── phase_0_validate.py",
        "├── phase_1_load_kernels.py",
        "├── phase_2_instantiate.py",
        "├── phase_3_bind_kernels.py",
        "├── phase_4_load_identity.py",
        "├── phase_5_bind_tools.py",
        "├── phase_6_wire_governance.py",
        "└── phase_7_verify_and_lock.py",
        "```",
        "",
        "## AgentInstance Schema",
        "",
        "```python",
        "@dataclass",
        "class AgentInstance:",
        "    instance_id: str      # UUID",
        "    agent_id: str         # e.g., 'l-cto'",
        "    config: AgentConfig",
        "    identity: dict        # From 02-identity kernel",
        "    tools: List[str]      # Bound tool IDs",
        "    kernels: List[str]    # Bound kernel IDs",
        "    init_signature: str   # SHA256 of init state",
        "    status: str           # 'INITIALIZING' | 'READY' | 'ERROR'",
        "    created_at: datetime",
        "```",
        "",
        "## Rollback on Failure",
        "",
        "If any phase fails:",
        "1. Error logged with phase number",
        "2. Agent node deleted from Neo4j (CASCADE deletes relationships)",
        "3. RuntimeError raised to caller",
    ]
    return "\n".join(lines)

def generate_memory_architecture():
    """Generate comprehensive memory architecture documentation."""
    lines = [
        "# L9 Memory Architecture",
        "# =======================",
        "# Multi-layer memory substrate with semantic search, graph relations, and caching.",
        "",
        "## Memory Segments (MemorySegment Enum)",
        "",
        "| Segment | Purpose | Storage |",
        "|---------|---------|---------|",
        "| `PACKETS` | All incoming packets | PostgreSQL packet_store |",
        "| `REASONING` | Reasoning traces | PostgreSQL reasoning_traces |",
        "| `SEMANTIC` | Vector embeddings | PostgreSQL semantic_memory (pgvector) |",
        "| `FACTS` | Extracted facts | PostgreSQL knowledge_facts |",
        "| `INSIGHTS` | High-level insights | PostgreSQL knowledge_facts |",
        "| `WORLD_MODEL` | Entity graph | Neo4j + PostgreSQL |",
        "| `TOOL_AUDIT` | Tool invocation logs | PostgreSQL tool_audit_log |",
        "| `GOVERNANCE` | Approval patterns | PostgreSQL + Neo4j |",
        "",
        "## Memory DAG Pipeline",
        "",
        "```",
        "ingest_packet(PacketEnvelopeIn)",
        "    │",
        "    ├─→ intake_node()        → Validate & normalize",
        "    ├─→ reasoning_node()     → Extract reasoning traces",
        "    ├─→ memory_write_node()  → Write to packet_store",
        "    ├─→ semantic_embed_node()→ Generate embeddings (pgvector)",
        "    ├─→ extract_insights()   → LLM insight extraction",
        "    ├─→ store_insights()     → Write to knowledge_facts",
        "    ├─→ world_model_trigger()→ Update entity graph",
        "    └─→ checkpoint_node()    → Persist DAG state",
        "```",
        "",
        "## Memory Tools",
        "",
        "| Tool | Function | Description |",
        "|------|----------|-------------|",
        "| `memory_search` | `execute_memory_search()` | Hybrid semantic + keyword search |",
        "| `memory_write` | `execute_memory_write()` | Write packet to substrate |",
        "",
        "## Memory API Endpoints",
        "",
        "| Endpoint | Method | Purpose |",
        "|----------|--------|---------|",
        "| `/memory/ingest` | POST | Ingest new packet |",
        "| `/memory/search` | POST | Semantic search |",
        "| `/memory/packet/{id}` | GET | Get specific packet |",
        "| `/memory/thread/{id}` | GET | Get thread packets |",
        "| `/memory/facts` | GET | Get knowledge facts |",
        "| `/memory/insights` | GET | Get insights |",
        "| `/memory/gc/run` | POST | Run garbage collection |",
        "",
        "## PostgreSQL Tables",
        "",
        "| Table | Purpose |",
        "|-------|---------|",
        "| `packet_store` | All packets with JSON payload |",
        "| `reasoning_traces` | Structured reasoning |",
        "| `semantic_memory` | Vector embeddings (pgvector) |",
        "| `knowledge_facts` | Extracted facts |",
        "| `agent_memory_events` | Agent activity log |",
        "| `tool_audit_log` | Tool invocation audit |",
        "| `tasks` | Task queue persistence |",
        "| `feedback_events` | Feedback for learning |",
        "| `reflection_store` | Reflections with effectiveness |",
    ]
    return "\n".join(lines)

def generate_governance_model():
    """Generate governance and approval model documentation."""
    lines = [
        "# L9 Governance Model",
        "# ====================",
        "# Approval gates, authority hierarchy, and high-risk tool constraints.",
        "",
        "## Authority Hierarchy",
        "",
        "```",
        "IGOR (Human) ──────────────────────────────────",
        "    │  FULL authority. Can approve/reject all.",
        "    │  Only IGOR can:",
        "    │    - Approve high-risk tools",
        "    │    - Grant permanent approvals",
        "    │    - Override safety constraints",
        "    ▼",
        "L (CTO Agent) ────────────────────────────────",
        "    │  Autonomous within safety envelope.",
        "    │  Must request approval for high-risk ops.",
        "    ▼",
        "Research/Coder Agents ────────────────────────",
        "    │  Limited scope. Cannot execute high-risk.",
        "    ▼",
        "Mac Agent ────────────────────────────────────",
        "       Lowest authority. Shell execution only with approval.",
        "```",
        "",
        "## HIGH_RISK_TOOLS",
        "",
        "These tools ALWAYS require Igor approval:",
        "",
        "| Tool | Risk Description |",
        "|------|------------------|",
        "| `gmp_run` | Execute GMP protocol (code changes) |",
        "| `git_commit` | Commit changes to git repository |",
        "| `git_push` | Push changes to remote repository |",
        "| `file_delete` | Delete files from filesystem |",
        "| `database_write` | Write to production database |",
        "| `deploy` | Deploy to production environment |",
        "| `mac_agent_exec` | Execute commands on Mac agent |",
        "",
        "## Approval Flow",
        "",
        "```",
        "Agent requests high-risk tool",
        "    │",
        "    ▼",
        "ApprovalManager.requires_approval(tool_id)",
        "    │",
        "    ├── NO → Execute immediately",
        "    │",
        "    └── YES → request_approval()",
        "              │",
        "              ├── Store approval_request packet",
        "              ├── Notify Igor via Slack",
        "              └── Wait for approve_task() or reject_task()",
        "```",
        "",
        "## Igor Commands (@L syntax)",
        "",
        "| Command | Description |",
        "|---------|-------------|",
        "| `@L propose_gmp <description>` | Propose a GMP |",
        "| `@L analyze <scope>` | Analyze code/files |",
        "| `@L approve <task_id>` | Approve pending task |",
        "| `@L reject <task_id> <reason>` | Reject with reason |",
        "| `@L rollback <task_id>` | Rollback a change |",
        "| `@L status` | Get current status |",
        "| `@L help` | Show available commands |",
        "",
        "## Governance Pattern Learning",
        "",
        "Every approval/rejection creates a `GovernancePattern` for closed-loop learning:",
        "",
        "```python",
        "GovernancePattern(",
        "    task_id=...,",
        "    tool_name=...,",
        "    decision=APPROVED | REJECTED,",
        "    reason=...,",
        "    conditions=[...],  # Extracted from reason",
        ")",
        "```",
    ]
    return "\n".join(lines)

def generate_migration_catalog():
    """Generate catalog of all SQL migrations."""
    lines = [
        "# L9 Migration Catalog",
        "# =====================",
        "# All SQL migrations for memory substrate schema evolution.",
        "",
        "## Migration Files",
        "",
        "| File | Purpose |",
        "|------|---------|",
    ]
    migrations_dir = os.path.join(REPO_DIR, "migrations")
    if os.path.isdir(migrations_dir):
        for fname in sorted(os.listdir(migrations_dir)):
            if fname.endswith(".sql"):
                fpath = os.path.join(migrations_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        first_lines = f.read(500)
                        # Extract comment if exists
                        comment_match = re.search(r"--\s*(.+)", first_lines)
                        purpose = comment_match.group(1)[:60] if comment_match else "Schema migration"
                        lines.append(f"| `{fname}` | {purpose} |")
                except Exception:
                    lines.append(f"| `{fname}` | Schema migration |")
    lines.extend([
        "",
        "## Key Tables Created",
        "",
        "| Migration | Tables |",
        "|-----------|--------|",
        "| 0001 | packet_store, agent_memory_events |",
        "| 0002 | semantic_memory (pgvector), reasoning_traces |",
        "| 0003 | tasks |",
        "| 0004 | world_model_entities |",
        "| 0005 | knowledge_facts |",
        "| 0006 | world_model_updates |",
        "| 0007 | world_model_snapshots |",
        "| 0008 | Enhanced: user_preferences, lessons, sops, rules |",
        "| 0009 | feedback_events, reflection_store enhancements |",
        "| 0011 | tool_audit_log |",
        "",
        "## Running Migrations",
        "",
        "Migrations run automatically in `api/server.py::lifespan()`:",
        "```python",
        "await run_migrations()  # Applies all pending .sql files",
        "```",
    ])
    return "\n".join(lines)

def generate_feature_flags():
    """Generate catalog of all L9 feature flags."""
    lines = [
        "# L9 Feature Flags",
        "# ==================",
        "# Runtime feature flags for L9 capabilities.",
        "",
        "## Active Feature Flags",
        "",
        "| Flag | Purpose | Default | Location |",
        "|------|---------|---------|----------|",
    ]
    # Scan for L9_ENABLE_* and L9_USE_* patterns
    flag_pattern = re.compile(r'(L9_(?:ENABLE|USE|NEW)_[A-Z_]+)')
    flags_found = set()
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        matches = flag_pattern.findall(content)
                        for match in matches:
                            flags_found.add((match, os.path.relpath(fpath, REPO_DIR)))
                except Exception:
                    pass
    flag_descriptions = {
        "L9_NEW_AGENT_INIT": ("Enable 7-phase bootstrap ceremony", "true"),
        "L9_ENABLE_LEGACY_CHAT": ("Gate old apiserver.py POST /chat", "false"),
        "L9_ENABLE_LEGACY_SLACK_ROUTER": ("Gate old webhookslack.py path", "false"),
        "L9_USE_KERNELS": ("Load kernels from files", "true"),
        "L9_ENABLE_WS_ORCHESTRATOR": ("WebSocket routes use wstaskrouter", "true"),
        "L9_GRAPH_AGENT_STATE": ("Neo4j-backed mutable agent state", "true"),
        "L9_GRAPH_WM_SYNC": ("Graph to World Model sync", "true"),
        "L9_TOOL_PATTERN_EXTRACTION": ("Tool pattern extraction job", "true"),
        "L9_OBSERVABILITY": ("Five-tier observability pack", "true"),
        "L9_STAGE3_MODULES": ("Tool Audit, Event Queue, Virtual Context, Evaluator", "true"),
        "L9_STAGE4_CONSOLIDATION": ("Periodic memory consolidation", "true"),
        "SLACK_APP_ENABLED": ("Slack Events API integration", "true"),
        "MAC_AGENT_ENABLED": ("Mac Agent task execution", "true"),
    }
    seen_flags = set()
    for flag, location in sorted(flags_found):
        if flag not in seen_flags:
            desc, default = flag_descriptions.get(flag, ("Feature flag", "false"))
            lines.append(f"| `{flag}` | {desc} | `{default}` | {location} |")
            seen_flags.add(flag)
    lines.extend([
        "",
        "## Flag Usage Pattern",
        "",
        "```python",
        "import os",
        "",
        "if os.getenv('L9_NEW_AGENT_INIT', 'true').lower() == 'true':",
        "    # Use new 7-phase bootstrap",
        "    await bootstrap_agent(config, substrate)",
        "else:",
        "    # Legacy initialization",
        "    agent = create_agent_legacy(config)",
        "```",
    ])
    return "\n".join(lines)

def generate_test_catalog():
    """Generate catalog of all tests with coverage stats."""
    lines = [
        "# L9 Test Catalog",
        "# =================",
        "# All test files with test counts.",
        "",
        "## Test Directory Structure",
        "",
    ]
    test_dirs = ["tests/core", "tests/integration", "tests/memory", "tests/telemetry", "tests/api"]
    total_tests = 0
    total_files = 0
    for test_dir_rel in test_dirs:
        test_dir = os.path.join(REPO_DIR, test_dir_rel)
        if os.path.isdir(test_dir):
            lines.append(f"### {test_dir_rel}/")
            lines.append("")
            for root, dirs, files in os.walk(test_dir):
                for fname in files:
                    if fname.startswith("test_") and fname.endswith(".py"):
                        fpath = os.path.join(root, fname)
                        rel_path = os.path.relpath(fpath, REPO_DIR)
                        try:
                            with open(fpath, "r", encoding="utf-8") as f:
                                content = f.read()
                                test_count = len(re.findall(r"def test_\w+", content))
                                total_tests += test_count
                                total_files += 1
                                lines.append(f"- `{rel_path}` ({test_count} tests)")
                        except Exception:
                            lines.append(f"- `{rel_path}` (? tests)")
            lines.append("")
    lines.extend([
        "## Summary",
        "",
        f"- **Total test files**: {total_files}",
        f"- **Total test functions**: {total_tests}",
        "",
        "## Running Tests",
        "",
        "```bash",
        "# All tests",
        "pytest tests/",
        "",
        "# Specific module",
        "pytest tests/core/agents/test_executor.py",
        "",
        "# With coverage",
        "pytest tests/ --cov=. --cov-report=html",
        "```",
    ])
    return "\n".join(lines)

def generate_telemetry_endpoints():
    """Generate telemetry and observability documentation."""
    lines = [
        "# L9 Telemetry & Observability",
        "# ==============================",
        "# Prometheus metrics, Grafana dashboards, and observability endpoints.",
        "",
        "## Prometheus Metrics",
        "",
        "| Metric | Type | Description |",
        "|--------|------|-------------|",
        "| `l9_tool_invocations_total` | Counter | Total tool invocations |",
        "| `l9_tool_latency_seconds` | Histogram | Tool execution latency |",
        "| `l9_tool_errors_total` | Counter | Tool execution errors |",
        "| `l9_memory_writes_total` | Counter | Memory write operations |",
        "| `l9_memory_searches_total` | Counter | Memory search operations |",
        "| `l9_memory_substrate_health` | Gauge | Memory substrate health (0/1) |",
        "",
        "## Endpoints",
        "",
        "| Endpoint | Purpose |",
        "|----------|---------|",
        "| `/metrics` | Prometheus scrape endpoint |",
        "| `/os/health` | Health check (liveness) |",
        "| `/os/readiness` | Readiness check |",
        "",
        "## Grafana Dashboards",
        "",
        "| Dashboard | Panels |",
        "|-----------|--------|",
        "| `l9-tool-observability.json` | Invocation rate, latency p50/p95/p99, error rate, memory writes |",
        "",
        "## Tool Audit Log",
        "",
        "Every tool invocation logged to `tool_audit_log` table:",
        "",
        "```sql",
        "CREATE TABLE tool_audit_log (",
        "    id SERIAL PRIMARY KEY,",
        "    tool_name VARCHAR(100) NOT NULL,",
        "    agent_id VARCHAR(100),",
        "    task_id VARCHAR(100),",
        "    invocation_id UUID,",
        "    parameters JSONB,",
        "    result_status VARCHAR(20),",
        "    error_message TEXT,",
        "    latency_ms INTEGER,",
        "    cost_usd DECIMAL(10, 6),",
        "    created_at TIMESTAMPTZ DEFAULT NOW()",
        ");",
        "```",
    ]
    return "\n".join(lines)

def generate_deployment_manifest():
    """Generate deployment and infrastructure documentation."""
    lines = [
        "# L9 Deployment Manifest",
        "# ========================",
        "# Docker services, ports, VPS configuration.",
        "",
        "## Docker Services",
        "",
        "| Service | Image | Port | Purpose |",
        "|---------|-------|------|---------|",
        "| `l9-api` | L9 FastAPI | 8000 | Main API server |",
        "| `l9-postgres` | postgres:15-alpine | 5432 | PostgreSQL + pgvector |",
        "| `l9-neo4j` | neo4j:5.14 | 7474, 7687 | Graph database |",
        "| `redis` | redis:7-alpine | 6379 | Cache, task queue |",
        "| `mcp-memory` | MCP Memory | 9001 | Cursor memory server |",
        "",
        "## VPS Configuration",
        "",
        "| Setting | Value |",
        "|---------|-------|",
        "| VPS IP | `157.180.73.53` |",
        "| User | `root` |",
        "| L9 Directory | `/opt/l9` |",
        "| Domain | `l9.quantumaipartners.com` |",
        "",
        "## Cloudflare + Caddy Routing",
        "",
        "```",
        "Internet → Cloudflare (HTTPS) → VPS:443",
        "    │",
        "    └→ Caddy reverse proxy",
        "        ├─ /api/*    → l9-api:8000",
        "        ├─ /slack/*  → l9-api:8000",
        "        ├─ /mcp/*    → mcp-memory:9001",
        "        └─ /metrics  → l9-api:8000",
        "```",
        "",
        "## Environment Variables",
        "",
        "| Variable | Purpose |",
        "|----------|---------|",
        "| `DATABASE_URL` | PostgreSQL connection |",
        "| `MEMORY_DSN` | Memory substrate connection |",
        "| `NEO4J_URI` | Neo4j Bolt URI |",
        "| `NEO4J_PASSWORD` | Neo4j password |",
        "| `REDIS_URL` | Redis connection |",
        "| `OPENAI_API_KEY` | OpenAI API key |",
        "| `SLACK_BOT_TOKEN` | Slack bot token |",
        "| `L9_NEW_AGENT_INIT` | Enable 7-phase bootstrap |",
    ]
    return "\n".join(lines)

# =============================================================================
# NEW GENERATORS (v2.1) - Full Neo4j Graph Support
# =============================================================================

def generate_inheritance_graph():
    """Generate class inheritance relationships for Neo4j (Class)-[:EXTENDS]->(Parent)."""
    lines = [
        "# L9 Class Inheritance Graph",
        "# ============================",
        "# Format: ChildClass::parent1,parent2 @ path/to/file.py",
        "# Load into Neo4j as (Class)-[:EXTENDS]->(ParentClass) relationships",
        "",
    ]
    inheritance = []
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read())
                        rel_path = os.path.relpath(fpath, REPO_DIR)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                parents = []
                                for base in node.bases:
                                    if isinstance(base, ast.Name):
                                        parents.append(base.id)
                                    elif isinstance(base, ast.Attribute):
                                        parents.append(f"{base.attr}")
                                if parents:
                                    inheritance.append(f"{node.name}::{','.join(parents)} @ {rel_path}")
                except Exception:
                    pass
    if inheritance:
        lines.extend(sorted(inheritance))
        lines.extend([
            "",
            f"# Total: {len(inheritance)} classes with inheritance",
        ])
        return "\n".join(lines)
    return "No inheritance relationships found."

def generate_method_catalog():
    """Generate class::method(args) catalog for Neo4j (Class)-[:HAS_METHOD]->(Method)."""
    lines = [
        "# L9 Method Catalog",
        "# ===================",
        "# Format: ClassName::method_name(arg1, arg2) @ path/to/file.py",
        "# Load into Neo4j as (Class)-[:HAS_METHOD]->(Method) relationships",
        "",
    ]
    methods = []
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read())
                        rel_path = os.path.relpath(fpath, REPO_DIR)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                class_name = node.name
                                for item in node.body:
                                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                        args = [arg.arg for arg in item.args.args if arg.arg != 'self']
                                        is_async = "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                                        signature = f"{is_async}{item.name}({', '.join(args)})"
                                        methods.append(f"{class_name}::{signature} @ {rel_path}")
                except Exception:
                    pass
    if methods:
        lines.extend(sorted(methods))
        lines.extend([
            "",
            f"# Total: {len(methods)} class methods",
        ])
        return "\n".join(lines)
    return "No class methods found."

def generate_route_handlers():
    """Generate API route → handler function mapping."""
    lines = [
        "# L9 Route Handlers",
        "# ===================",
        "# Format: METHOD /path → handler_function @ file.py",
        "# Load into Neo4j as (Route)-[:HANDLED_BY]->(Function) relationships",
        "",
    ]
    routes = []
    route_pattern = re.compile(
        r'@(?:app|router)\.(?:api_route|get|post|put|delete|patch|websocket|options|head)\s*\(\s*["\']([^"\']+)["\']',
        re.MULTILINE
    )
    method_pattern = re.compile(r'@(?:app|router)\.(get|post|put|delete|patch|websocket|options|head)')
    func_pattern = re.compile(r'(?:async\s+)?def\s+(\w+)\s*\(')
    
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        rel_path = os.path.relpath(fpath, REPO_DIR)
                        # Find all route decorators
                        for match in re.finditer(r'@(?:app|router)\.(get|post|put|delete|patch|websocket)\s*\(\s*["\']([^"\']+)["\'].*?\n(?:@.*?\n)*\s*(?:async\s+)?def\s+(\w+)', content, re.DOTALL):
                            method, path, func = match.groups()
                            routes.append(f"{method.upper()} {path} → {func}() @ {rel_path}")
                except Exception:
                    pass
    if routes:
        lines.extend(sorted(routes))
        lines.extend([
            "",
            f"# Total: {len(routes)} route handlers",
        ])
        return "\n".join(lines)
    return "No route handlers found."

def generate_file_metrics():
    """Generate file-level metrics: lines, classes, functions, complexity."""
    lines = [
        "# L9 File Metrics",
        "# =================",
        "# Format: path/to/file.py | Lines: N | Classes: N | Functions: N",
        "# Use for: Finding large files, complexity hotspots",
        "",
        "| File | Lines | Classes | Functions | Async |",
        "|------|-------|---------|-----------|-------|",
    ]
    metrics = []
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        tree = ast.parse(content)
                        rel_path = os.path.relpath(fpath, REPO_DIR)
                        line_count = len(content.split('\n'))
                        class_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
                        func_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
                        async_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef))
                        if line_count > 50:  # Only include substantial files
                            metrics.append((line_count, f"| `{rel_path}` | {line_count} | {class_count} | {func_count} | {async_count} |"))
                except Exception:
                    pass
    # Sort by line count descending (biggest files first)
    metrics.sort(key=lambda x: x[0], reverse=True)
    lines.extend([m[1] for m in metrics])
    lines.extend([
        "",
        f"# Total: {len(metrics)} Python files (>50 lines)",
        f"# Total lines: {sum(m[0] for m in metrics):,}",
    ])
    return "\n".join(lines)

def generate_pydantic_models():
    """Generate catalog of Pydantic models (BaseModel subclasses)."""
    lines = [
        "# L9 Pydantic Models",
        "# ====================",
        "# Format: ModelName @ path/to/file.py",
        "# These are API request/response schemas",
        "",
    ]
    models = []
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read())
                        rel_path = os.path.relpath(fpath, REPO_DIR)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                for base in node.bases:
                                    base_name = ""
                                    if isinstance(base, ast.Name):
                                        base_name = base.id
                                    elif isinstance(base, ast.Attribute):
                                        base_name = base.attr
                                    if base_name in ("BaseModel", "BaseSettings", "BaseConfig"):
                                        docstring = ast.get_docstring(node) or ""
                                        docstring = docstring.split("\n")[0][:50] if docstring else ""
                                        models.append(f"{node.name} @ {rel_path} - {docstring}")
                                        break
                except Exception:
                    pass
    if models:
        lines.extend(sorted(models))
        lines.extend([
            "",
            f"# Total: {len(models)} Pydantic models",
        ])
        return "\n".join(lines)
    return "No Pydantic models found."

def generate_dynamic_tool_catalog():
    """Dynamically scan core/tools/ for actual tool definitions."""
    lines = [
        "# L9 Dynamic Tool Catalog",
        "# =========================",
        "# Scanned from actual code (not hardcoded)",
        "# Format: tool_name | Category | Risk | File",
        "",
        "## Tools Found in core/tools/",
        "",
    ]
    tools = []
    tool_dirs = [
        os.path.join(REPO_DIR, "core", "tools"),
        os.path.join(REPO_DIR, "tools"),
    ]
    # Patterns for tool definitions
    tool_patterns = [
        re.compile(r'name\s*[=:]\s*["\'](\w+)["\']'),
        re.compile(r'tool_id\s*[=:]\s*["\'](\w+)["\']'),
        re.compile(r'class\s+(\w+Tool)\s*\('),
        re.compile(r'def\s+(execute_\w+)\s*\('),
    ]
    
    for tool_dir in tool_dirs:
        if os.path.isdir(tool_dir):
            for root, dirs, files in os.walk(tool_dir):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for fname in files:
                    if fname.endswith(".py") and not fname.startswith("__"):
                        fpath = os.path.join(root, fname)
                        try:
                            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                                rel_path = os.path.relpath(fpath, REPO_DIR)
                                for pattern in tool_patterns:
                                    matches = pattern.findall(content)
                                    for match in matches:
                                        if not match.startswith("_"):
                                            # Determine category from path
                                            category = "internal" if "internal" in rel_path else "core"
                                            # Check for risk indicators
                                            risk = "low"
                                            if any(kw in content.lower() for kw in ["delete", "write", "execute", "shell", "git"]):
                                                risk = "high"
                                            elif any(kw in content.lower() for kw in ["create", "update", "modify"]):
                                                risk = "medium"
                                            tools.append(f"| `{match}` | {category} | {risk} | {rel_path} |")
                        except Exception:
                            pass
    
    if tools:
        lines.append("| Tool | Category | Risk | File |")
        lines.append("|------|----------|------|------|")
        lines.extend(sorted(set(tools)))
        lines.extend([
            "",
            f"# Total: {len(set(tools))} tool definitions found",
        ])
        return "\n".join(lines)
    return "No tools found in core/tools/."

def generate_async_function_map():
    """Map all async functions for understanding concurrency patterns."""
    lines = [
        "# L9 Async Function Map",
        "# =======================",
        "# Format: async function_name(args) @ path/to/file.py",
        "# Use for: Understanding concurrency patterns, identifying blocking calls",
        "",
    ]
    async_funcs = []
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read())
                        rel_path = os.path.relpath(fpath, REPO_DIR)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.AsyncFunctionDef):
                                args = [arg.arg for arg in node.args.args if arg.arg != 'self']
                                signature = f"async {node.name}({', '.join(args)})"
                                async_funcs.append(f"{signature} @ {rel_path}")
                except Exception:
                    pass
    if async_funcs:
        lines.extend(sorted(async_funcs))
        lines.extend([
            "",
            f"# Total: {len(async_funcs)} async functions",
        ])
        return "\n".join(lines)
    return "No async functions found."

def generate_decorator_catalog():
    """Catalog all decorators used across the codebase."""
    lines = [
        "# L9 Decorator Catalog",
        "# ======================",
        "# Format: @decorator_name | count | example_file",
        "# Use for: Understanding patterns, finding all routes/tools/traces",
        "",
    ]
    decorators = defaultdict(list)
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read())
                        rel_path = os.path.relpath(fpath, REPO_DIR)
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                                for decorator in node.decorator_list:
                                    dec_name = ""
                                    if isinstance(decorator, ast.Name):
                                        dec_name = f"@{decorator.id}"
                                    elif isinstance(decorator, ast.Attribute):
                                        dec_name = f"@{decorator.attr}"
                                    elif isinstance(decorator, ast.Call):
                                        if isinstance(decorator.func, ast.Name):
                                            dec_name = f"@{decorator.func.id}(...)"
                                        elif isinstance(decorator.func, ast.Attribute):
                                            dec_name = f"@{decorator.func.attr}(...)"
                                    if dec_name:
                                        decorators[dec_name].append(rel_path)
                except Exception:
                    pass
    if decorators:
        lines.append("| Decorator | Count | Example Files |")
        lines.append("|-----------|-------|---------------|")
        for dec_name in sorted(decorators.keys()):
            files_list = decorators[dec_name]
            count = len(files_list)
            examples = ", ".join(sorted(set(files_list))[:3])
            lines.append(f"| `{dec_name}` | {count} | {examples} |")
        lines.extend([
            "",
            f"# Total: {len(decorators)} unique decorators",
        ])
        return "\n".join(lines)
    return "No decorators found."

def main():
    """Generate index files and export them."""
    if not os.path.isdir(REPO_DIR):
        logger.info(f"❌ Repo directory not found: {REPO_DIR}")
        sys.exit(1)

    logger.info(f"📁 Using repo: {REPO_DIR}")
    logger.info("📤 Export destinations:")
    logger.info(f"   - {REPO_INDEX_DIR}")
    logger.info(f"   - {DROPBOX_EXPORT_DIR}")
    logger.info(f"   - {ICLOUD_EXPORT_DIR}")

    try:
        os.makedirs(REPO_INDEX_DIR, exist_ok=True)
        os.makedirs(DROPBOX_EXPORT_DIR, exist_ok=True)
        os.makedirs(ICLOUD_EXPORT_DIR, exist_ok=True)
        logger.info("✅ Export directories ready")
    except Exception as e:
        logger.error(f"❌ Failed to create export directories: {e}")
        sys.exit(1)

    # Define generators - ORDER MATTERS for LLM context efficiency
    generators = {
        # Core architecture (load first for context)
        "wiring_map.txt": ("🔌 Wiring map (execution spine)", generate_wiring_map),
        "architecture.txt": ("🏗️  Module architecture", generate_module_architecture),
        "tree.txt": ("📊 Directory structure", generate_tree),
        # NEW: Agent initialization & memory (critical for understanding)
        "bootstrap_phases.txt": ("🚀 Agent bootstrap phases (7-phase)", generate_bootstrap_phases),
        "memory_architecture.txt": ("🧠 Memory architecture", generate_memory_architecture),
        "governance_model.txt": ("🔐 Governance & approval model", generate_governance_model),
        # Agent/orchestration layer
        "agent_catalog.txt": ("🤖 Agent catalog", generate_agent_catalog),
        "kernel_catalog.txt": ("🧬 Kernel catalog (10 kernels)", generate_kernel_catalog),
        "orchestrator_catalog.txt": ("🎭 Orchestrator catalog", generate_orchestrator_catalog),
        "tool_catalog.txt": ("🔧 Tool catalog", generate_tool_catalog),
        # Events and schemas
        "event_types.txt": ("📨 Event types & packet kinds", generate_event_types),
        "singleton_registry.txt": ("📦 Singleton registry", generate_singleton_registry),
        # NEW: Infrastructure & operations
        "migration_catalog.txt": ("🗄️  Migration catalog", generate_migration_catalog),
        "feature_flags.txt": ("🏳️  Feature flags", generate_feature_flags),
        "test_catalog.txt": ("🧪 Test catalog", generate_test_catalog),
        "telemetry_endpoints.txt": ("📈 Telemetry & observability", generate_telemetry_endpoints),
        "deployment_manifest.txt": ("🚢 Deployment manifest", generate_deployment_manifest),
        # API and code structure
        "api_surfaces.txt": ("🌐 API surfaces", generate_api_surfaces),
        "entrypoints.txt": ("🚪 Entry points", generate_entrypoints),
        "class_definitions.txt": ("📋 Classes & data models", generate_class_definitions),
        "function_signatures.txt": ("⚙️  Function signatures (ALL)", generate_function_signatures),
        # Configuration and dependencies
        "config_files.txt": ("⚙️  Configuration files", generate_config_files),
        "dependencies.txt": ("📦 Dependencies", generate_dependencies),
        "env_refs.txt": ("🔐 Environment variables", generate_env_refs),
        "imports.txt": ("📚 Python imports", generate_imports),
        # NEW v2.1: Neo4j Graph Support (relationships for queries)
        "inheritance_graph.txt": ("🧬 Inheritance graph (Neo4j EXTENDS)", generate_inheritance_graph),
        "method_catalog.txt": ("🔍 Method catalog (Neo4j HAS_METHOD)", generate_method_catalog),
        "route_handlers.txt": ("🛤️  Route handlers (Neo4j HANDLED_BY)", generate_route_handlers),
        "file_metrics.txt": ("📏 File metrics (lines, complexity)", generate_file_metrics),
        "pydantic_models.txt": ("📐 Pydantic models (API schemas)", generate_pydantic_models),
        "dynamic_tool_catalog.txt": ("🔧 Dynamic tool catalog (scanned)", generate_dynamic_tool_catalog),
        "async_function_map.txt": ("⚡ Async function map", generate_async_function_map),
        "decorator_catalog.txt": ("🏷️  Decorator catalog", generate_decorator_catalog),
    }

    logger.info("\n📝 Generating indexes...\n")

    results = {}
    for filename, (emoji_desc, generator) in generators.items():
        logger.info(f"  {emoji_desc}...", end=" ", flush=True)
        try:
            content = generator()
            size = len(content.encode("utf-8"))
            
            # Write to local repo (required - must succeed)
            repo_file = os.path.join(REPO_INDEX_DIR, filename)
            with open(repo_file, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Write to Dropbox (optional - continue on error)
            try:
                dropbox_file = os.path.join(DROPBOX_EXPORT_DIR, filename)
                with open(dropbox_file, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                logger.debug(f"Dropbox export failed for {filename}: {e}")
            
            # Write to iCloud (optional - continue on error)
            try:
                icloud_file = os.path.join(ICLOUD_EXPORT_DIR, filename)
                with open(icloud_file, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                logger.debug(f"iCloud export failed for {filename}: {e}")
            
            results[filename] = size
            logger.info(f"✅ ({size:,} bytes)")
        except Exception as e:
            logger.info(f"❌ {e}")
            results[filename] = 0

    logger.info("\n✨ Done! Files exported to:")
    logger.info(f"   📂 {REPO_INDEX_DIR}")
    logger.info(f"   ☁️  {DROPBOX_EXPORT_DIR}")
    logger.info(f"   ☁️  {ICLOUD_EXPORT_DIR}")
    logger.info("\n📋 Summary:")
    total_size = 0
    for filename, size in sorted(results.items()):
        status = "✅" if size > 0 else "⚠️"
        logger.info(f"   {status} {filename:30} {size:>12,} bytes")
        total_size += size

    logger.info(f"\n   📊 Total: {total_size:,} bytes ({len(results)} files)")
    logger.info("\n💡 Load order for LLMs (most context-critical first):")
    logger.info("   1. wiring_map.txt - execution spine & data flow")
    logger.info("   2. bootstrap_phases.txt - 7-phase agent init ceremony")
    logger.info("   3. memory_architecture.txt - memory segments & DAG")
    logger.info("   4. governance_model.txt - approval gates & authority")
    logger.info("   5. kernel_catalog.txt - 10 governance kernels")
    logger.info("   6. agent_catalog.txt - agent layers & capabilities")
    logger.info("   7. tool_catalog.txt - tools & risk levels")
    logger.info("   8. migration_catalog.txt - schema evolution")
    logger.info("   9. tree.txt - directory structure")
    logger.info("   10. test_catalog.txt - test coverage")

if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "ast", "async", "auth", "authorization", "caching", "config", "dataclass", "debugging", "event-driven"],
    "keywords": ["agent", "api", "architecture", "async", "bootstrap", "catalog", "decorator", "definitions"],
    "business_value": "Utility module for export repo indexes",
    "last_modified": "2026-01-14T15:03:00Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
