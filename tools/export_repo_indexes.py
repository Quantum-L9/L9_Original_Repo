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
    "module_version": "3.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-02-11T00:00:00Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "export_repo_indexes",
    "type": "tool",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import ast
import fnmatch
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import structlog
import yaml

# Configuration
logger = structlog.get_logger(__name__)

# Script version for meta headers
SCRIPT_VERSION = "3.0.0"

# Use L9_REPO_ROOT env var if set, otherwise fall back to default paths
_HOME = str(Path.home())
_REPO_ROOT = os.getenv("L9_REPO_ROOT", os.path.join(_HOME, "Projects", "L9"))
REPO_DIR = _REPO_ROOT
REPO_NAME = os.path.basename(os.path.abspath(REPO_DIR))
REPO_INDEX_DIR = os.path.join(_REPO_ROOT, "reports/repo-index")
DROPBOX_EXPORT_DIR = os.getenv(
    "L9_DROPBOX_EXPORT_DIR",
    os.path.join(_HOME, "Dropbox", "Repo_Dropbox_IB", "L9-index-export"),
)
ICLOUD_EXPORT_DIR = os.getenv(
    "L9_ICLOUD_EXPORT_DIR",
    os.path.join(
        _HOME,
        "Library",
        "Mobile Documents",
        "com~apple~CloudDocs",
        "00-LLM-00",
        "L9-repo-index",
    ),
)

# Directories to skip
SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".cursor",
    ".dora",
    ".secrets",
    "l9/venv",
    "secrets",
    ".DS_Store",
    "node_modules",
    ".pytest_cache",
}


def load_gitignore_patterns():
    """Load and parse .gitignore patterns."""
    gitignore_path = os.path.join(REPO_DIR, ".gitignore")
    patterns = []
    if not os.path.exists(gitignore_path):
        return patterns
    try:
        with open(gitignore_path, encoding="utf-8") as f:
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


def _get_git_branch() -> str:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPO_DIR,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _get_git_short_sha() -> str:
    """Get current git short SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPO_DIR,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def generate_meta_header(index_name: str) -> str:
    """Generate a standard meta header for every index file."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    branch = _get_git_branch()
    sha = _get_git_short_sha()
    return (
        f"# ================================================================\n"
        f"# {index_name}\n"
        f"# ================================================================\n"
        f"# Repo:      {REPO_NAME}\n"
        f"# Generated: {now}\n"
        f"# Branch:    {branch} ({sha})\n"
        f"# Generator: export_repo_indexes.py v{SCRIPT_VERSION}\n"
        f"# ================================================================\n"
    )


# Cached gitignore patterns (loaded once, reused by all generators)
_GITIGNORE_PATTERNS: list | None = None


def _get_gitignore_patterns() -> list:
    """Return cached gitignore patterns."""
    global _GITIGNORE_PATTERNS
    if _GITIGNORE_PATTERNS is None:
        _GITIGNORE_PATTERNS = load_gitignore_patterns()
    return _GITIGNORE_PATTERNS


def walk_python_files():
    """Walk repo yielding (fpath, rel_path) for every non-ignored .py file.

    This is the single source of truth for which files get indexed.
    All generators should use this instead of rolling their own os.walk.
    """
    gitignore_patterns = _get_gitignore_patterns()
    for root, dirs, files in os.walk(REPO_DIR):
        # Filter dirs in-place
        dirs[:] = [
            d
            for d in dirs
            if d not in SKIP_DIRS
            and not is_ignored(
                os.path.relpath(os.path.join(root, d), REPO_DIR),
                gitignore_patterns,
                is_dir=True,
            )
        ]
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, REPO_DIR)
            if is_ignored(rel_path, gitignore_patterns, is_dir=False):
                continue
            yield fpath, rel_path


def walk_all_files():
    """Walk repo yielding (fpath, rel_path, is_dir) for every non-ignored file.

    Use for generators that need non-.py files (configs, migrations, etc.).
    """
    gitignore_patterns = _get_gitignore_patterns()
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [
            d
            for d in dirs
            if d not in SKIP_DIRS
            and not is_ignored(
                os.path.relpath(os.path.join(root, d), REPO_DIR),
                gitignore_patterns,
                is_dir=True,
            )
        ]
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, REPO_DIR)
            if is_ignored(rel_path, gitignore_patterns, is_dir=False):
                continue
            yield fpath, rel_path


# =============================================================================
# ORIGINAL GENERATORS (kept for compatibility)
# =============================================================================


def generate_tree():
    """Generate tree.txt using actual directory structure, respecting .gitignore."""
    lines = []
    gitignore_patterns = load_gitignore_patterns()

    def walk_dir(path, prefix="", max_depth=3, current_depth=0, rel_path_prefix=""):
        """
        Performs a recursive directory traversal to generate repository index files for LLM context understanding.

        Args:
            path: The directory path to start traversal.
            prefix: String prefix for indexing or naming conventions.
            max_depth: Maximum depth for recursion to limit traversal scope.
            current_depth: Current recursion depth, used internally.
            rel_path_prefix: Relative path prefix for maintaining directory structure.

        Returns:
            A list of file paths or index data collected during traversal.
        """
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
        for f in files:
            lines.append(f"{prefix}├── {f}")
        for i, d in enumerate(dirs):
            is_last = i == len(dirs) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{d}/")
            extension = "    " if is_last else "│   "
            new_rel_prefix = os.path.join(rel_path_prefix, d) if rel_path_prefix else d
            walk_dir(
                os.path.join(path, d),
                prefix + extension,
                max_depth,
                current_depth + 1,
                new_rel_prefix,
            )

    lines.append("L9/")
    walk_dir(REPO_DIR, "", max_depth=4, current_depth=0, rel_path_prefix="")
    return "\n".join(lines)


def generate_api_surfaces():
    """Map all callable interfaces across different API surface types."""
    api_surfaces = defaultdict(list)
    router_pattern = re.compile(r"(\w+)\s*=\s*(?:APIRouter|Router)\(")
    callable_pattern = re.compile(r"(?:def|async def)\s+(\w+)\s*\(")
    surface_dirs = {
        "memory",
        "agents",
        "api",
        "services",
        "orchestration",
        "orchestrators",
    }
    for fpath, rel_path in walk_python_files():
        # Determine which surface this file belongs to
        top_dir = rel_path.split(os.sep)[0]
        if top_dir not in surface_dirs:
            continue
        surface_name = top_dir
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                content = f.read()
                routers = router_pattern.findall(content)
                if routers:
                    for router in routers:
                        api_surfaces[surface_name].append(f"  {rel_path}::{router}")
                callables = callable_pattern.findall(content)
                if callables and (
                    "handler" in os.path.basename(fpath)
                    or "interface" in os.path.basename(fpath)
                ):
                    for callable_name in callables:
                        api_surfaces[surface_name].append(
                            f"  {rel_path}::{callable_name}()"
                        )
        except Exception:
            pass
    if api_surfaces:
        lines = []
        for surface_type in sorted(api_surfaces.keys()):
            lines.append(f"\n# {surface_type.upper()} Surface:")
            lines.extend(sorted(set(api_surfaces[surface_type])))
        return "\n".join(lines)
    return "No API surfaces found."


def generate_entrypoints():
    """Identify app entrypoints with useful metadata."""
    entrypoints = []
    gitignore_patterns = load_gitignore_patterns()
    fastapi_pattern = re.compile(
        r'app\s*=\s*FastAPI\s*\([^)]*title\s*=\s*["\']([^"\']+)["\']', re.DOTALL
    )
    uvicorn_pattern = re.compile(r"uvicorn\.run\s*\([^)]*\)", re.DOTALL)
    main_block_pattern = re.compile(r'if\s+__name__\s*==\s*["\']__main__["\']\s*:')

    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [
            d
            for d in dirs
            if d not in SKIP_DIRS
            and not is_ignored(
                os.path.relpath(os.path.join(root, d), REPO_DIR),
                gitignore_patterns,
                is_dir=True,
            )
        ]
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
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    entry_info = {
                        "path": rel_path,
                        "type": None,
                        "title": None,
                        "port": None,
                        "host": None,
                        "has_main": False,
                        "routes": [],
                    }
                    if re.search(r"\bapp\s*=\s*FastAPI\s*\(", content):
                        entry_info["type"] = "FastAPI"
                        fastapi_match = fastapi_pattern.search(content)
                        if fastapi_match:
                            entry_info["title"] = fastapi_match.group(1)
                        route_pattern = re.compile(
                            r'@(?:app|router)\.(get|post|put|delete|patch|websocket|options|head)\s*\(["\']([^"\']+)["\']'
                        )
                        routes = route_pattern.findall(content)
                        entry_info["routes"] = [
                            f"{method.upper()} {path}" for method, path in routes
                        ]
                        include_pattern = re.compile(
                            r'\.include_router\s*\([^,]+,\s*prefix\s*=\s*["\']([^"\']+)["\']'
                        )
                        includes = include_pattern.findall(content)
                        if includes:
                            entry_info["routes"].extend(
                                [f"ROUTER {prefix}/*" for prefix in includes]
                            )
                    uvicorn_match = uvicorn_pattern.search(content)
                    if uvicorn_match:
                        host_match = re.search(
                            r'host\s*=\s*["\']([^"\']+)["\']', content
                        )
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
                            for route in entry_info["routes"]:
                                lines_out.append(f"    - {route}")
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
    getenv_pattern = re.compile(
        r'os\.(?:getenv|environ)\.get\(["\']([A-Za-z_][A-Za-z0-9_]*)["\']'
    )
    environ_pattern = re.compile(r'os\.environ\[["\']([A-Za-z_][A-Za-z0-9_]*)["\']')
    dotenv_pattern = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=", re.MULTILINE)
    for fpath, rel_path in walk_all_files():
        fname = os.path.basename(fpath)
        if fname.endswith(".py"):
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    env_vars.update(getenv_pattern.findall(content))
                    env_vars.update(environ_pattern.findall(content))
            except Exception:
                pass
        elif fname.startswith(".env"):
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as f:
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
    for fpath, rel_path in walk_python_files():
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
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
            with open(req_file) as f:
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
    for fpath, rel_path in walk_python_files():
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
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
    """Extract ALL function names and signatures (sync + async)."""
    functions = []
    for fpath, rel_path in walk_python_files():
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = [arg.arg for arg in node.args.args]
                        prefix = (
                            "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                        )
                        signature = f"{prefix}{node.name}({', '.join(args)})"
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
    config_patterns = [
        ".yaml",
        ".yml",
        ".json",
        ".toml",
        ".ini",
        ".cfg",
        "Dockerfile",
        "docker-compose",
    ]
    config_files = []
    for fpath, rel_path in walk_all_files():
        fname = os.path.basename(fpath)
        if any(fname.endswith(ext) or fname.startswith(ext) for ext in config_patterns):
            config_files.append(rel_path)
    if config_files:
        return "\n".join(sorted(set(config_files)))
    return "No config files found."


def generate_module_architecture():
    """Map module structure and purposes from __init__.py docstrings."""
    architecture = []
    gitignore_patterns = _get_gitignore_patterns()
    for root, dirs, files in os.walk(REPO_DIR):
        dirs[:] = [
            d
            for d in dirs
            if d not in SKIP_DIRS
            and not is_ignored(
                os.path.relpath(os.path.join(root, d), REPO_DIR),
                gitignore_patterns,
                is_dir=True,
            )
        ]
        if "__init__.py" in files:
            rel_path = os.path.relpath(root, REPO_DIR)
            if rel_path == ".":
                continue
            init_file = os.path.join(root, "__init__.py")
            try:
                with open(init_file, encoding="utf-8", errors="ignore") as f:
                    docstring = f.read(500)
                    docstring = (
                        docstring.split('"""')[1]
                        if '"""' in docstring
                        else "No module docstring"
                    )
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
    """Generate wiring map by scanning actual router registrations and server structure."""
    lines = [
        "# L9 Wiring Map",
        "# ==============",
        "# How components connect: Entrypoint → Routers → Memory → Persistence",
        "# Auto-discovered from router_registry.register() calls and api/server.py",
        "",
        "## ENTRYPOINT",
        "",
        "```",
        "uvicorn api.server:app → FastAPI lifespan() → router auto-wiring",
        "```",
        "",
        "## AUTO-REGISTERED ROUTERS (via router_registry)",
        "",
        "| Prefix | Tags | Module |",
        "|--------|------|--------|",
    ]
    # Scan for router_registry.register() calls across codebase
    routers = []
    reg_re = re.compile(
        r"router_registry\.register\(\s*"
        r"(?:router\s*=\s*\w+\s*,\s*)?"
        r'prefix\s*=\s*["\']([^"\']*)["\']'
        r".*?tags\s*=\s*\[([^\]]*)\]",
        re.DOTALL,
    )
    for fpath, rel_path in walk_python_files():
        if "test" in rel_path.lower() or ".backup" in rel_path:
            continue
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if "router_registry.register" not in content:
                continue
            for match in reg_re.finditer(content):
                prefix = match.group(1)
                tags_raw = match.group(2)
                tags = [
                    t.strip().strip("\"'") for t in tags_raw.split(",") if t.strip()
                ]
                routers.append((prefix or "(root)", ", ".join(tags), rel_path))
        except Exception:
            pass

    for prefix, tags, module in sorted(routers, key=lambda x: x[0]):
        lines.append(f"| `{prefix}` | {tags} | {module} |")

    lines.extend(
        [
            "",
            f"# Total: {len(routers)} auto-registered routers",
            "",
            "## PERSISTENCE LAYER",
            "",
            "| Service | Port | Purpose |",
            "|---------|------|---------|",
        ]
    )

    # Scan docker-compose for services
    compose_file = os.path.join(REPO_DIR, "docker-compose.yml")
    if not os.path.exists(compose_file):
        compose_file = os.path.join(REPO_DIR, "docker-compose.yaml")
    if os.path.exists(compose_file):
        try:
            with open(compose_file, encoding="utf-8") as f:
                compose_data = yaml.safe_load(f)
            if compose_data and "services" in compose_data:
                for svc_name, svc_config in sorted(compose_data["services"].items()):
                    ports = svc_config.get("ports", [])
                    port_str = (
                        ", ".join(str(p).split(":")[0] for p in ports[:3])
                        if ports
                        else "-"
                    )
                    image = svc_config.get("image", svc_config.get("build", "-"))
                    if isinstance(image, dict):
                        image = image.get("context", "-")
                    lines.append(f"| `{svc_name}` | {port_str} | {image} |")
        except Exception:
            lines.append("| (compose parse failed) | - | - |")
    else:
        lines.extend(
            [
                "| PostgreSQL + pgvector | 5432 | Packet store, semantic memory |",
                "| Neo4j Graph DB | 7687 | Entity graph |",
                "| Redis | 6379 | Task queue, cache |",
            ]
        )

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
                    with open(fpath, encoding="utf-8", errors="ignore") as f:
                        content = f.read(2000)
                        class_match = re.search(
                            r'class\s+(\w+).*?(?:"""(.*?)"""|\'\'\'(.*?)\'\'\')',
                            content,
                            re.DOTALL,
                        )
                        if class_match:
                            class_name = class_match.group(1)
                            docstring = (
                                class_match.group(2) or class_match.group(3) or ""
                            ).strip()
                            docstring = (
                                docstring.split("\n")[0][:80]
                                if docstring
                                else "No docstring"
                            )
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
                    with open(fpath, encoding="utf-8") as f:
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
    lines.extend(
        [
            "",
            "## Agent Layers",
            "",
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
        ]
    )
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
                    with open(fpath, encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if data:
                            kernel_id = data.get(
                                "kernel_id", fname.replace(".yaml", "")
                            )
                            name = data.get("name", kernel_id)
                            version = data.get("version", "1.0")
                            purpose = data.get("purpose", data.get("description", ""))
                            if isinstance(purpose, str):
                                purpose = purpose.split("\n")[0][:100]
                            lines.extend(
                                [
                                    f"### {fname}",
                                    f"- **ID**: {kernel_id}",
                                    f"- **Name**: {name}",
                                    f"- **Version**: {version}",
                                    f"- **Purpose**: {purpose}",
                                    "",
                                ]
                            )
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
    """Generate catalog of tools by scanning config/policies/high_risk_tools.yaml."""
    lines = [
        "# L9 Tool Catalog",
        "# ================",
        "# Tools with category, scope, risk level, and approval requirements.",
        "# Auto-discovered from config/policies/high_risk_tools.yaml and core/tools/.",
        "",
    ]
    # Scan canonical policy YAML
    policy_file = os.path.join(REPO_DIR, "config", "policies", "high_risk_tools.yaml")
    if os.path.exists(policy_file):
        try:
            with open(policy_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            classification = data.get("tool_risk_classification", {})

            # High-risk tools
            high_risk = classification.get("high_risk", [])
            if high_risk:
                lines.extend(
                    [
                        "## High-Risk Tools (Require Approval)",
                        "",
                        "| Tool | Description | Risk Level |",
                        "|------|-------------|------------|",
                    ]
                )
                for item in high_risk:
                    if isinstance(item, dict):
                        tid = item.get("tool_id", "?")
                        desc = item.get("description", "-")
                        risk = item.get("risk_level", "-")
                        lines.append(f"| `{tid}` | {desc} | {risk} |")
                    elif isinstance(item, str):
                        lines.append(f"| `{item}` | - | high |")
                lines.append("")

            # Igor approval required
            igor_req = classification.get("igor_approval_required", [])
            if igor_req:
                lines.extend(
                    [
                        "## Igor Approval Required",
                        "",
                    ]
                )
                for tool in igor_req:
                    lines.append(f"- `{tool}`")
                lines.append("")

            # Safe tools
            safe = classification.get("safe", [])
            if safe:
                lines.extend(
                    [
                        "## Safe Tools (No Approval Needed)",
                        "",
                    ]
                )
                for tool in safe:
                    lines.append(f"- `{tool}`")
                lines.append("")

            # Side-effect tools
            side_effect = classification.get("side_effect", [])
            if side_effect:
                lines.extend(
                    [
                        "## Side-Effect Tools",
                        "",
                    ]
                )
                for tool in side_effect:
                    lines.append(f"- `{tool}`")
                lines.append("")
        except Exception:
            lines.append("(policy YAML parse error)")
    else:
        lines.append("(config/policies/high_risk_tools.yaml not found)")

    # Scan core/tools/ for actual tool implementations
    lines.extend(
        [
            "## Tool Implementations (from core/tools/)",
            "",
            "| File | Classes/Functions |",
            "|------|-------------------|",
        ]
    )
    tools_dir = os.path.join(REPO_DIR, "core", "tools")
    if os.path.isdir(tools_dir):
        for fname in sorted(os.listdir(tools_dir)):
            if fname.endswith(".py") and not fname.startswith("__"):
                fpath = os.path.join(tools_dir, fname)
                try:
                    with open(fpath, encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read())
                    items = []
                    for node in ast.walk(tree):
                        if (
                            isinstance(node, ast.ClassDef)
                            and "tool" in node.name.lower()
                        ):
                            items.append(node.name)
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if node.name.startswith("execute_"):
                                items.append(f"{node.name}()")
                    if items:
                        lines.append(
                            f"| `core/tools/{fname}` | {', '.join(items[:5])} |"
                        )
                except Exception:
                    pass

    return "\n".join(lines)


def generate_orchestrator_catalog():
    """Generate catalog of all orchestrators by scanning orchestrators/ directory."""
    lines = [
        "# L9 Orchestrator Catalog",
        "# ========================",
        "# Agent coordination patterns for the L9 platform.",
        "# Auto-discovered from orchestrators/ directory.",
        "",
        "## Available Orchestrators",
        "",
    ]
    orch_root = os.path.join(REPO_DIR, "orchestrators")
    if not os.path.isdir(orch_root):
        return "\n".join(lines + ["No orchestrators/ directory found."])

    for entry in sorted(os.listdir(orch_root)):
        orch_dir = os.path.join(orch_root, entry)
        if (
            not os.path.isdir(orch_dir)
            or entry.startswith("__")
            or entry.startswith(".")
        ):
            continue
        # Get Python files
        py_files = sorted(
            f
            for f in os.listdir(orch_dir)
            if f.endswith(".py") and not f.startswith("__")
        )
        # Try to extract purpose from __init__.py or orchestrator.py docstring
        purpose = ""
        for candidate in ["orchestrator.py", "__init__.py", "interface.py"]:
            candidate_path = os.path.join(orch_dir, candidate)
            if os.path.exists(candidate_path):
                try:
                    with open(candidate_path, encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read())
                    # Try module docstring first
                    mod_doc = ast.get_docstring(tree)
                    if mod_doc:
                        purpose = mod_doc.split("\n")[0][:80]
                        break
                    # Try first class docstring
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            cls_doc = ast.get_docstring(node)
                            if cls_doc:
                                purpose = cls_doc.split("\n")[0][:80]
                                break
                    if purpose:
                        break
                except Exception:
                    pass
        if not purpose:
            purpose = "(no docstring)"

        lines.extend(
            [
                f"### {entry}/",
                f"**Purpose:** {purpose}",
                f"**Files:** {', '.join(py_files)}",
                "",
            ]
        )

    # Also list top-level .py files in orchestrators/
    top_files = sorted(
        f
        for f in os.listdir(orch_root)
        if f.endswith(".py")
        and not f.startswith("__")
        and os.path.isfile(os.path.join(orch_root, f))
    )
    if top_files:
        lines.extend(["## Top-Level Files", ""])
        for f in top_files:
            lines.append(f"- `orchestrators/{f}`")
        lines.append("")

    return "\n".join(lines)


def generate_event_types():
    """Generate catalog of event types and packet kinds by scanning actual source."""
    lines = [
        "# L9 Event Types",
        "# ===============",
        "# PacketEnvelope kinds, event types, and schema information.",
        "",
        "## PacketKind Enum (from core/schemas/packet_envelope_v2.py)",
        "",
        "| Kind | Value |",
        "|------|-------|",
    ]
    # Dynamically scan PacketKind enum from source
    packet_schema = os.path.join(REPO_DIR, "core", "schemas", "packet_envelope_v2.py")
    if os.path.exists(packet_schema):
        try:
            with open(packet_schema, encoding="utf-8") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "PacketKind":
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    value = ""
                                    if isinstance(item.value, ast.Constant):
                                        value = item.value.value
                                    lines.append(f"| `{target.id}` | `{value}` |")
        except Exception:
            lines.append("| (scan failed) | - |")
    else:
        lines.append("| (file not found) | - |")

    # Scan for DAG node functions in memory/substrate_dag.py
    lines.extend(["", "## Memory DAG Pipeline Nodes", ""])
    dag_file = os.path.join(REPO_DIR, "memory", "substrate_dag.py")
    if os.path.exists(dag_file):
        try:
            with open(dag_file, encoding="utf-8") as f:
                tree = ast.parse(f.read())
            stage = 1
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.endswith("_node") or node.name.startswith("run_"):
                        docstring = ast.get_docstring(node) or ""
                        docstring = docstring.split("\n")[0][:60] if docstring else ""
                        lines.append(f"| {stage} | `{node.name}` | {docstring} |")
                        stage += 1
        except Exception:
            pass
    if lines[-1] == "## Memory DAG Pipeline Nodes":
        lines.append("(no DAG nodes found)")

    # Scan for registered event types
    lines.extend(
        ["", "## Registered Event Types (from core/event_type_registry.py)", ""]
    )
    event_registry = os.path.join(REPO_DIR, "core", "event_type_registry.py")
    if os.path.exists(event_registry):
        try:
            with open(event_registry, encoding="utf-8") as f:
                content = f.read()
            # Find register_event_type() calls with name= parameter
            for match in re.finditer(
                r'register_event_type\(\s*name\s*=\s*["\'](\w+)["\'].*?category\s*=\s*["\'](\w+)["\']',
                content,
                re.DOTALL,
            ):
                name, category = match.groups()
                lines.append(f"- `{name}` (category: {category})")
            # Also find batch registrations
            for match in re.finditer(
                r'["\'](\w+)["\']:\s*["\']([^"\']+)["\']',
                content,
            ):
                event_name, desc = match.groups()
                if event_name.islower() and len(event_name) > 3:
                    lines.append(f"- `{event_name}`: {desc}")
        except Exception:
            pass

    return "\n".join(lines)


def generate_singleton_registry():
    """Generate registry of singleton instances by scanning @register_singleton usage."""
    lines = [
        "# L9 Singleton Registry",
        "# ======================",
        "# Auto-discovered singletons using @register_singleton decorator.",
        "# Pattern: core/singleton_auto_registry.py",
        "",
        "## Registered Singletons",
        "",
        "| Singleton | Module | Category | Lifecycle | Description |",
        "|-----------|--------|----------|-----------|-------------|",
    ]
    # Scan for register_singleton() calls
    reg_pattern = re.compile(
        r'register_singleton\(\s*(?:name\s*=\s*)?["\'](\w+)["\']',
    )
    reg_decorator_pattern = re.compile(
        r"@register_singleton\(",
        re.MULTILINE,
    )
    singletons = []
    for fpath, rel_path in walk_python_files():
        # Skip test and backup files
        if "test" in rel_path.lower() or ".backup" in rel_path:
            continue
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if "register_singleton" not in content:
                continue
            # Extract singleton registration details
            # Pattern 1: register_singleton_service(name="...", ...)
            for match in re.finditer(
                r'register_singleton_service\(\s*name\s*=\s*["\'](\w+)["\']',
                content,
            ):
                name = match.group(1)
                # Try to extract category, lifecycle, description from nearby context
                ctx_start = max(0, match.start() - 200)
                ctx_end = min(len(content), match.end() + 500)
                ctx = content[ctx_start:ctx_end]
                cat_m = re.search(r'category\s*=\s*["\'](\w+)["\']', ctx)
                life_m = re.search(
                    r"lifecycle\s*=\s*(?:SingletonLifecycle\.)?(\w+)", ctx
                )
                desc_m = re.search(r'description\s*=\s*["\']([^"\']+)["\']', ctx)
                category = cat_m.group(1) if cat_m else "-"
                lifecycle = life_m.group(1) if life_m else "LAZY"
                description = desc_m.group(1)[:50] if desc_m else "-"
                singletons.append((name, rel_path, category, lifecycle, description))
            # Pattern 2: @register_singleton(...) decorator
            if reg_decorator_pattern.search(content):
                for match in re.finditer(
                    r"@register_singleton\(([^)]*)\)\s*\n\s*(?:async\s+)?def\s+(\w+)",
                    content,
                    re.DOTALL,
                ):
                    kwargs_str, func_name = match.groups()
                    # Extract name from decorator args or infer from function
                    name_m = re.search(r'name\s*=\s*["\'](\w+)["\']', kwargs_str)
                    name = name_m.group(1) if name_m else func_name.replace("get_", "")
                    cat_m = re.search(r'category\s*=\s*["\'](\w+)["\']', kwargs_str)
                    life_m = re.search(
                        r"lifecycle\s*=\s*(?:SingletonLifecycle\.)?(\w+)", kwargs_str
                    )
                    desc_m = re.search(
                        r'description\s*=\s*["\']([^"\']+)["\']', kwargs_str
                    )
                    category = cat_m.group(1) if cat_m else "-"
                    lifecycle = life_m.group(1) if life_m else "LAZY"
                    description = desc_m.group(1)[:50] if desc_m else "-"
                    # Avoid duplicates
                    if not any(s[0] == name for s in singletons):
                        singletons.append(
                            (name, rel_path, category, lifecycle, description)
                        )
        except Exception:
            pass

    for name, module, category, lifecycle, description in sorted(singletons):
        lines.append(
            f"| `{name}` | {module} | {category} | {lifecycle} | {description} |"
        )

    lines.extend(
        [
            "",
            f"# Total: {len(singletons)} registered singletons",
            "",
            "## Registration Pattern",
            "",
            "```python",
            "from core.singleton_auto_registry import register_singleton",
            "",
            "@register_singleton(",
            '    category="memory",',
            "    lifecycle=SingletonLifecycle.LAZY,",
            '    description="Description here"',
            ")",
            "async def get_my_service():",
            "    return MyService()",
            "```",
        ]
    )
    return "\n".join(lines)


# =============================================================================
# NEW GENERATORS (v2.0) - Agent Init, Memory, Governance, Migrations, etc.
# =============================================================================


def generate_bootstrap_phases():
    """Generate catalog of agent bootstrap phases by scanning core/agents/bootstrap/."""
    lines = [
        "# L9 Agent Bootstrap Phases",
        "# ==========================",
        "# Auto-discovered from core/agents/bootstrap/ directory.",
        "",
        "## Phase Files",
        "",
        "| Phase | File | Functions | Purpose |",
        "|-------|------|-----------|---------|",
    ]
    bootstrap_dir = os.path.join(REPO_DIR, "core", "agents", "bootstrap")
    if os.path.isdir(bootstrap_dir):
        for fname in sorted(os.listdir(bootstrap_dir)):
            if not fname.endswith(".py") or fname.startswith("__"):
                continue
            fpath = os.path.join(bootstrap_dir, fname)
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    tree = ast.parse(f.read())
                # Extract phase number from filename
                phase_match = re.search(r"phase_(\d+)", fname)
                phase_num = phase_match.group(1) if phase_match else "-"
                # Get public functions
                funcs = []
                purpose = ""
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not node.name.startswith("_"):
                            funcs.append(node.name)
                            if not purpose:
                                doc = ast.get_docstring(node) or ""
                                purpose = doc.split("\n")[0][:60] if doc else ""
                # Module docstring as fallback purpose
                if not purpose:
                    mod_doc = ast.get_docstring(tree) or ""
                    purpose = mod_doc.split("\n")[0][:60] if mod_doc else fname
                func_str = ", ".join(f"`{f}()`" for f in funcs[:3])
                lines.append(f"| {phase_num} | `{fname}` | {func_str} | {purpose} |")
            except Exception:
                lines.append(f"| - | `{fname}` | (parse error) | - |")

        # List all files in bootstrap dir
        lines.extend(["", "## Directory Contents", ""])
        all_files = sorted(os.listdir(bootstrap_dir))
        for f in all_files:
            if not f.startswith("."):
                lines.append(f"- `core/agents/bootstrap/{f}`")
    else:
        lines.append("(core/agents/bootstrap/ directory not found)")

    return "\n".join(lines)


def generate_memory_architecture():
    """Generate memory architecture by scanning memory/ directory and migrations."""
    lines = [
        "# L9 Memory Architecture",
        "# =======================",
        "# Auto-discovered from memory/ directory and SQL migrations.",
        "",
        "## Memory Components",
        "",
        "| File | Classes | Purpose |",
        "|------|---------|---------|",
    ]
    memory_dir = os.path.join(REPO_DIR, "memory")
    if os.path.isdir(memory_dir):
        for fname in sorted(os.listdir(memory_dir)):
            if not fname.endswith(".py") or fname.startswith("__"):
                continue
            fpath = os.path.join(memory_dir, fname)
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    tree = ast.parse(f.read())
                classes = [
                    n.name
                    for n in ast.walk(tree)
                    if isinstance(n, ast.ClassDef) and not n.name.startswith("_")
                ]
                mod_doc = ast.get_docstring(tree) or ""
                purpose = mod_doc.split("\n")[0][:60] if mod_doc else "-"
                class_str = ", ".join(classes[:4]) if classes else "-"
                lines.append(f"| `memory/{fname}` | {class_str} | {purpose} |")
            except Exception:
                lines.append(f"| `memory/{fname}` | (parse error) | - |")

    # Scan for MemorySegment enum
    lines.extend(["", "## Memory Segments", ""])
    for fpath, rel_path in walk_python_files():
        if "memory" not in rel_path:
            continue
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if "class MemorySegment" not in content:
                continue
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "MemorySegment":
                    lines.append("| Segment | Value |")
                    lines.append("|---------|-------|")
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    val = ""
                                    if isinstance(item.value, ast.Constant):
                                        val = item.value.value
                                    lines.append(f"| `{target.id}` | `{val}` |")
                    break
        except Exception:
            pass

    # Scan for PacketEnvelope fields
    lines.extend(["", "## PacketEnvelope Schema", ""])
    schema_file = os.path.join(REPO_DIR, "core", "schemas", "packet_envelope_v2.py")
    if os.path.exists(schema_file):
        try:
            with open(schema_file, encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ClassDef)
                    and "PacketEnvelope" in node.name
                    and "In" not in node.name
                ):
                    lines.append(f"### {node.name}")
                    lines.append("")
                    lines.append("| Field | Type |")
                    lines.append("|-------|------|")
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign) and isinstance(
                            item.target, ast.Name
                        ):
                            ann = "-"
                            if hasattr(ast, "unparse") and item.annotation:
                                ann = ast.unparse(item.annotation)
                            elif isinstance(item.annotation, ast.Name):
                                ann = item.annotation.id
                            lines.append(f"| `{item.target.id}` | `{ann}` |")
                    lines.append("")
        except Exception:
            lines.append("(schema parse error)")

    # Scan for DAG nodes
    lines.extend(["", "## Ingestion Pipeline Nodes", ""])
    dag_file = os.path.join(REPO_DIR, "memory", "substrate_dag.py")
    if os.path.exists(dag_file):
        try:
            with open(dag_file, encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
            stage = 1
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.endswith("_node") or node.name.startswith("run_"):
                        doc = ast.get_docstring(node) or ""
                        doc = doc.split("\n")[0][:60] if doc else ""
                        lines.append(f"{stage}. `{node.name}()` — {doc}")
                        stage += 1
        except Exception:
            pass

    # Scan PostgreSQL tables from migrations
    lines.extend(["", "## PostgreSQL Tables (from migrations)", ""])
    tables = set()
    migrations_dir = os.path.join(REPO_DIR, "migrations")
    if os.path.isdir(migrations_dir):
        for fname in sorted(os.listdir(migrations_dir)):
            if fname.endswith(".sql"):
                fpath = os.path.join(migrations_dir, fname)
                try:
                    with open(fpath, encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    for match in re.finditer(
                        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)",
                        content,
                        re.IGNORECASE,
                    ):
                        tables.add(match.group(1))
                except Exception:
                    pass
    if tables:
        lines.append("| Table |")
        lines.append("|-------|")
        for table in sorted(tables):
            lines.append(f"| `{table}` |")
    else:
        lines.append("(no tables discovered from migrations)")

    return "\n".join(lines)


def generate_governance_model():
    """Generate governance model by scanning core/governance/ directory."""
    lines = [
        "# L9 Governance Model",
        "# ====================",
        "# Auto-discovered from core/governance/ and policy configs.",
        "",
        "## Governance Components",
        "",
        "| File | Classes | Purpose |",
        "|------|---------|---------|",
    ]
    gov_dir = os.path.join(REPO_DIR, "core", "governance")
    if os.path.isdir(gov_dir):
        for fname in sorted(os.listdir(gov_dir)):
            if not fname.endswith(".py") or fname.startswith("__"):
                continue
            fpath = os.path.join(gov_dir, fname)
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    tree = ast.parse(f.read())
                classes = [
                    n.name
                    for n in ast.walk(tree)
                    if isinstance(n, ast.ClassDef) and not n.name.startswith("_")
                ]
                mod_doc = ast.get_docstring(tree) or ""
                purpose = mod_doc.split("\n")[0][:60] if mod_doc else "-"
                class_str = ", ".join(classes[:3]) if classes else "-"
                lines.append(f"| `core/governance/{fname}` | {class_str} | {purpose} |")
            except Exception:
                pass

    # Scan for high-risk tools from governance policies
    lines.extend(["", "## High-Risk Tools (from governance policies)", ""])
    high_risk = set()
    # Scan Python files in governance for HIGH_RISK patterns
    if os.path.isdir(gov_dir):
        for fname in os.listdir(gov_dir):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(gov_dir, fname)
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                # Look for high_risk_tools lists/sets/dicts
                for match in re.finditer(
                    r"(?:high_risk|HIGH_RISK|requires_approval).*?[\[{(](.*?)[\]})]",
                    content,
                    re.DOTALL,
                ):
                    for tool in re.findall(r'["\'](\w+)["\']', match.group(1)):
                        if tool.islower() and len(tool) > 3:
                            high_risk.add(tool)
            except Exception:
                pass
    # Also scan YAML policies
    policy_dir = os.path.join(REPO_DIR, "config", "policies")
    if os.path.isdir(policy_dir):
        for fname in os.listdir(policy_dir):
            if fname.endswith((".yaml", ".yml")):
                fpath = os.path.join(policy_dir, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if data and isinstance(data, dict):
                        hr = data.get("high_risk_tools", [])
                        if isinstance(hr, list):
                            high_risk.update(t for t in hr if isinstance(t, str))
                        elif isinstance(hr, dict):
                            high_risk.update(hr.keys())
                except Exception:
                    pass

    if high_risk:
        lines.append("| Tool |")
        lines.append("|------|")
        for tool in sorted(high_risk):
            lines.append(f"| `{tool}` |")
    else:
        # Fallback to known list if no governance files found
        lines.extend(
            [
                "| Tool |",
                "|------|",
                "| `gmp_run` |",
                "| `git_commit` |",
                "| `git_push` |",
                "| `file_delete` |",
                "| `deploy` |",
                "| `mac_agent_exec` |",
            ]
        )

    # Scan for approval-related classes
    lines.extend(["", "## Approval Classes", ""])
    for fpath, rel_path in walk_python_files():
        if "governance" not in rel_path and "approval" not in rel_path.lower():
            continue
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and (
                    "approval" in node.name.lower()
                    or "governance" in node.name.lower()
                    or "pattern" in node.name.lower()
                ):
                    doc = ast.get_docstring(node) or ""
                    doc = doc.split("\n")[0][:60] if doc else "-"
                    lines.append(f"- `{node.name}` ({rel_path}) — {doc}")
        except Exception:
            pass

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
                    with open(fpath, encoding="utf-8") as f:
                        first_lines = f.read(500)
                        # Extract comment if exists
                        comment_match = re.search(r"--\s*(.+)", first_lines)
                        purpose = (
                            comment_match.group(1)[:60]
                            if comment_match
                            else "Schema migration"
                        )
                        lines.append(f"| `{fname}` | {purpose} |")
                except Exception:
                    lines.append(f"| `{fname}` | Schema migration |")
    lines.extend(
        [
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
        ]
    )
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
    flag_pattern = re.compile(r"(L9_(?:ENABLE|USE|NEW)_[A-Z_]+)")
    flags_found = set()
    for fpath, rel_path in walk_python_files():
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                content = f.read()
                matches = flag_pattern.findall(content)
                for match in matches:
                    flags_found.add((match, rel_path))
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
        "L9_STAGE3_MODULES": (
            "Tool Audit, Event Queue, Virtual Context, Evaluator",
            "true",
        ),
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
    lines.extend(
        [
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
        ]
    )
    return "\n".join(lines)


def generate_test_catalog():
    """Generate catalog of all tests with coverage stats (auto-discovers all test dirs)."""
    lines = [
        "# L9 Test Catalog",
        "# =================",
        "# All test files with test counts.",
        "",
        "## Test Directory Structure",
        "",
    ]
    total_tests = 0
    total_files = 0
    # Auto-discover: walk all .py files under tests/ directory
    tests_root = os.path.join(REPO_DIR, "tests")
    gitignore_patterns = _get_gitignore_patterns()
    # Collect by subdirectory
    by_dir = defaultdict(list)
    if os.path.isdir(tests_root):
        for root, dirs, files in os.walk(tests_root):
            dirs[:] = [
                d
                for d in dirs
                if d not in SKIP_DIRS
                and not is_ignored(
                    os.path.relpath(os.path.join(root, d), REPO_DIR),
                    gitignore_patterns,
                    is_dir=True,
                )
            ]
            for fname in sorted(files):
                if fname.startswith("test_") and fname.endswith(".py"):
                    fpath = os.path.join(root, fname)
                    rel_path = os.path.relpath(fpath, REPO_DIR)
                    # Group by first two path components (tests/core, tests/memory, etc.)
                    parts = rel_path.split(os.sep)
                    group_key = os.sep.join(parts[:2]) if len(parts) > 2 else parts[0]
                    try:
                        with open(fpath, encoding="utf-8") as f:
                            content = f.read()
                            test_count = len(
                                re.findall(r"(?:def|async def) test_\w+", content)
                            )
                            total_tests += test_count
                            total_files += 1
                            by_dir[group_key].append(
                                f"- `{rel_path}` ({test_count} tests)"
                            )
                    except Exception:
                        by_dir[group_key].append(f"- `{rel_path}` (? tests)")
    # Also scan for test files outside tests/ (e.g., root-level test_*.py)
    for fpath, rel_path in walk_python_files():
        fname = os.path.basename(fpath)
        if fname.startswith("test_") and not rel_path.startswith("tests/"):
            try:
                with open(fpath, encoding="utf-8") as f:
                    content = f.read()
                    test_count = len(re.findall(r"(?:def|async def) test_\w+", content))
                    total_tests += test_count
                    total_files += 1
                    by_dir["other"].append(f"- `{rel_path}` ({test_count} tests)")
            except Exception:
                by_dir["other"].append(f"- `{rel_path}` (? tests)")

    for group_key in sorted(by_dir.keys()):
        lines.append(f"### {group_key}/")
        lines.append("")
        lines.extend(sorted(by_dir[group_key]))
        lines.append("")

    lines.extend(
        [
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
        ]
    )
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
    """Generate deployment manifest by scanning docker-compose and deploy/ configs."""
    lines = [
        "# L9 Deployment Manifest",
        "# ========================",
        "# Auto-discovered from docker-compose and deploy/ directory.",
        "",
        "## Docker Services",
        "",
        "| Service | Image | Ports | Volumes |",
        "|---------|-------|-------|---------|",
    ]
    # Scan docker-compose files
    compose_candidates = [
        os.path.join(REPO_DIR, "docker-compose.yml"),
        os.path.join(REPO_DIR, "docker-compose.yaml"),
        os.path.join(REPO_DIR, "docker-compose.dev.yml"),
        os.path.join(REPO_DIR, "docker-compose.override.yml"),
    ]
    services_found = {}
    for compose_file in compose_candidates:
        if os.path.exists(compose_file):
            try:
                with open(compose_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data and "services" in data:
                    for svc_name, svc_cfg in data["services"].items():
                        if svc_name not in services_found:
                            image = svc_cfg.get("image", "")
                            if not image and "build" in svc_cfg:
                                build = svc_cfg["build"]
                                image = (
                                    f"(build: {build.get('context', '.')})"
                                    if isinstance(build, dict)
                                    else f"(build: {build})"
                                )
                            ports = svc_cfg.get("ports", [])
                            port_str = (
                                ", ".join(str(p) for p in ports[:3]) if ports else "-"
                            )
                            vols = svc_cfg.get("volumes", [])
                            vol_str = str(len(vols)) + " mounts" if vols else "-"
                            services_found[svc_name] = (image, port_str, vol_str)
            except Exception:
                pass

    for svc_name, (image, ports, vols) in sorted(services_found.items()):
        lines.append(f"| `{svc_name}` | {image} | {ports} | {vols} |")

    if not services_found:
        lines.append("| (no docker-compose found) | - | - | - |")

    # Scan deploy/ directory for deployment scripts and configs
    lines.extend(["", "## Deployment Scripts", ""])
    deploy_dir = os.path.join(REPO_DIR, "deploy")
    if os.path.isdir(deploy_dir):
        for root, dirs, files in os.walk(deploy_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in sorted(files):
                if fname.startswith("."):
                    continue
                rel = os.path.relpath(os.path.join(root, fname), REPO_DIR)
                lines.append(f"- `{rel}`")
    else:
        lines.append("(no deploy/ directory found)")

    # Scan .env.example for documented env vars
    lines.extend(["", "## Environment Variables (from .env.example)", ""])
    env_example = os.path.join(REPO_DIR, ".env.example")
    if os.path.exists(env_example):
        try:
            with open(env_example, encoding="utf-8") as f:
                lines.append("| Variable | Default |")
                lines.append("|----------|---------|")
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, val = line.partition("=")
                        key = key.strip()
                        val = val.strip()
                        # Mask sensitive values
                        if any(
                            s in key.lower()
                            for s in ["password", "secret", "key", "token"]
                        ):
                            val = "***"
                        lines.append(f"| `{key}` | `{val}` |")
        except Exception:
            pass
    else:
        lines.append("(no .env.example found)")

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
    for fpath, rel_path in walk_python_files():
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        parents = []
                        for base in node.bases:
                            if isinstance(base, ast.Name):
                                parents.append(base.id)
                            elif isinstance(base, ast.Attribute):
                                parents.append(f"{base.attr}")
                        if parents:
                            inheritance.append(
                                f"{node.name}::{','.join(parents)} @ {rel_path}"
                            )
        except Exception:
            pass
    if inheritance:
        lines.extend(sorted(inheritance))
        lines.extend(
            [
                "",
                f"# Total: {len(inheritance)} classes with inheritance",
            ]
        )
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
    for fpath, rel_path in walk_python_files():
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_name = node.name
                        for item in node.body:
                            if isinstance(
                                item, (ast.FunctionDef, ast.AsyncFunctionDef)
                            ):
                                args = [
                                    arg.arg
                                    for arg in item.args.args
                                    if arg.arg != "self"
                                ]
                                is_async = (
                                    "async "
                                    if isinstance(item, ast.AsyncFunctionDef)
                                    else ""
                                )
                                signature = f"{is_async}{item.name}({', '.join(args)})"
                                methods.append(
                                    f"{class_name}::{signature} @ {rel_path}"
                                )
        except Exception:
            pass
    if methods:
        lines.extend(sorted(methods))
        lines.extend(
            [
                "",
                f"# Total: {len(methods)} class methods",
            ]
        )
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
    route_re = re.compile(
        r'@(?:app|router)\.(get|post|put|delete|patch|websocket|options|head)\s*\(\s*["\']([^"\']+)["\'].*?\n(?:@.*?\n)*\s*(?:async\s+)?def\s+(\w+)',
        re.DOTALL,
    )

    for fpath, rel_path in walk_python_files():
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                content = f.read()
                for match in route_re.finditer(content):
                    method, path, func = match.groups()
                    routes.append(f"{method.upper()} {path} → {func}() @ {rel_path}")
        except Exception:
            pass
    if routes:
        lines.extend(sorted(routes))
        lines.extend(
            [
                "",
                f"# Total: {len(routes)} route handlers",
            ]
        )
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
    for fpath, rel_path in walk_python_files():
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                content = f.read()
                tree = ast.parse(content)
                line_count = len(content.split("\n"))
                class_count = sum(
                    1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
                )
                func_count = sum(
                    1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                )
                async_count = sum(
                    1
                    for node in ast.walk(tree)
                    if isinstance(node, ast.AsyncFunctionDef)
                )
                if line_count > 50:  # Only include substantial files
                    metrics.append(
                        (
                            line_count,
                            f"| `{rel_path}` | {line_count} | {class_count} | {func_count} | {async_count} |",
                        )
                    )
        except Exception:
            pass
    # Sort by line count descending (biggest files first)
    metrics.sort(key=lambda x: x[0], reverse=True)
    lines.extend([m[1] for m in metrics])
    lines.extend(
        [
            "",
            f"# Total: {len(metrics)} Python files (>50 lines)",
            f"# Total lines: {sum(m[0] for m in metrics):,}",
        ]
    )
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
    for fpath, rel_path in walk_python_files():
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for base in node.bases:
                            base_name = ""
                            if isinstance(base, ast.Name):
                                base_name = base.id
                            elif isinstance(base, ast.Attribute):
                                base_name = base.attr
                            if base_name in (
                                "BaseModel",
                                "BaseSettings",
                                "BaseConfig",
                            ):
                                docstring = ast.get_docstring(node) or ""
                                docstring = (
                                    docstring.split("\n")[0][:50] if docstring else ""
                                )
                                models.append(f"{node.name} @ {rel_path} - {docstring}")
                                break
        except Exception:
            pass
    if models:
        lines.extend(sorted(models))
        lines.extend(
            [
                "",
                f"# Total: {len(models)} Pydantic models",
            ]
        )
        return "\n".join(lines)
    return "No Pydantic models found."


def generate_dynamic_tool_catalog():
    """Dynamically scan entire codebase for ToolDefinition(...) registrations."""
    lines = [
        "# L9 Dynamic Tool Catalog",
        "# =========================",
        "# Auto-discovered ToolDefinition(...) instances across entire codebase.",
        "# Includes: core/tools/, runtime/, core/agents/bootstrap/, services/",
        "",
    ]
    # Parse ToolDefinition(...) blocks with full metadata
    tool_def_re = re.compile(
        r"ToolDefinition\(\s*(.*?)\)",
        re.DOTALL,
    )
    tools = {}  # name -> {category, scope, risk_level, requires_igor, description, file}

    for fpath, rel_path in walk_python_files():
        if "test" in rel_path.lower() or ".backup" in rel_path:
            continue
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if "ToolDefinition(" not in content:
                continue
            for match in tool_def_re.finditer(content):
                block = match.group(1)
                # Extract fields from the ToolDefinition kwargs
                name_m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', block)
                if not name_m:
                    continue
                name = name_m.group(1)
                desc_m = re.search(r'description\s*=\s*["\']([^"\']+)["\']', block)
                cat_m = re.search(r'category\s*=\s*["\']([^"\']+)["\']', block)
                scope_m = re.search(r'scope\s*=\s*["\']([^"\']+)["\']', block)
                risk_m = re.search(r'risk_level\s*=\s*["\']([^"\']+)["\']', block)
                igor_m = re.search(r"requires_igor_approval\s*=\s*(True|False)", block)
                desc = desc_m.group(1)[:50] if desc_m else "-"
                category = cat_m.group(1) if cat_m else "-"
                scope = scope_m.group(1) if scope_m else "-"
                risk = risk_m.group(1) if risk_m else "-"
                igor = igor_m.group(1) if igor_m else "-"
                # Keep first occurrence or the one with most metadata
                if name not in tools or tools[name]["description"] == "-":
                    tools[name] = {
                        "description": desc,
                        "category": category,
                        "scope": scope,
                        "risk_level": risk,
                        "requires_igor": igor,
                        "file": rel_path,
                    }
        except Exception:
            pass

    # Also scan for class *Tool patterns and execute_* functions in core/tools/
    tool_classes = []
    for fpath, rel_path in walk_python_files():
        if not rel_path.startswith("core/tools/"):
            continue
        if os.path.basename(fpath).startswith("__"):
            continue
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and "Tool" in node.name:
                    doc = ast.get_docstring(node) or ""
                    doc = doc.split("\n")[0][:50] if doc else "-"
                    tool_classes.append((node.name, rel_path, doc))
        except Exception:
            pass

    # Output ToolDefinition table
    if tools:
        lines.extend(
            [
                "## Registered ToolDefinitions",
                "",
                "| Tool | Category | Scope | Risk | Igor? | Description | File |",
                "|------|----------|-------|------|-------|-------------|------|",
            ]
        )
        for name in sorted(tools.keys()):
            t = tools[name]
            lines.append(
                f"| `{name}` | {t['category']} | {t['scope']} | {t['risk_level']} "
                f"| {t['requires_igor']} | {t['description']} | {t['file']} |"
            )
        lines.extend(["", f"# Total: {len(tools)} unique ToolDefinitions", ""])

    # Output Tool classes
    if tool_classes:
        lines.extend(
            [
                "## Tool Implementation Classes",
                "",
                "| Class | File | Purpose |",
                "|-------|------|---------|",
            ]
        )
        for cls_name, fpath, doc in sorted(tool_classes):
            lines.append(f"| `{cls_name}` | {fpath} | {doc} |")
        lines.append("")

    if not tools and not tool_classes:
        lines.append("No ToolDefinition instances found.")

    return "\n".join(lines)


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
    for fpath, rel_path in walk_python_files():
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.AsyncFunctionDef):
                        args = [arg.arg for arg in node.args.args if arg.arg != "self"]
                        signature = f"async {node.name}({', '.join(args)})"
                        async_funcs.append(f"{signature} @ {rel_path}")
        except Exception:
            pass
    if async_funcs:
        lines.extend(sorted(async_funcs))
        lines.extend(
            [
                "",
                f"# Total: {len(async_funcs)} async functions",
            ]
        )
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
    for fpath, rel_path in walk_python_files():
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(
                        node,
                        (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
                    ):
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
        lines.extend(
            [
                "",
                f"# Total: {len(decorators)} unique decorators",
            ]
        )
        return "\n".join(lines)
    return "No decorators found."


def generate_adr_catalog():
    """Generate catalog of Architecture Decision Records (ADRs)."""
    lines = [
        "# L9 Architecture Decision Record (ADR) Catalog",
        f"# Generated: {datetime.now(UTC).strftime('%Y-%m-%d')}",
    ]

    adr_dir = os.path.join(REPO_DIR, "readme", "adr")
    if not os.path.isdir(adr_dir):
        return "# No ADR directory found at readme/adr/"

    # Collect ADRs
    adrs = []
    do_not_rules = []

    for fname in sorted(os.listdir(adr_dir)):
        if fname.endswith(".md") and fname[0].isdigit():
            fpath = os.path.join(adr_dir, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    content = f.read()

                    # Extract ADR number from filename (e.g., "0024" from "0024-resilience-mixin-pattern.md")
                    adr_num = fname.split("-")[0]

                    # Extract title from first line: "# ADR 0024: <Title>"
                    title = "Unknown"
                    title_match = re.search(
                        r"^#\s+ADR\s+\d+:\s*(.+)$", content, re.MULTILINE
                    )
                    if title_match:
                        title = title_match.group(1).strip()

                    # Extract status from "## Status\n<status>" section
                    status = "Unknown"
                    status_match = re.search(
                        r"##\s*Status\s*\n+([A-Za-z]+)", content, re.MULTILINE
                    )
                    if status_match:
                        status = status_match.group(1).strip()

                    rel_path = f"readme/adr/{fname}"
                    adrs.append((adr_num, status, title, rel_path))

                    # Extract "DO NOT" rules from content for quick reference
                    do_not_matches = re.findall(
                        r"DO NOT[^.!?\n]{10,80}", content, re.IGNORECASE
                    )
                    for rule in do_not_matches[:2]:  # Max 2 per ADR
                        # Clean up the rule text
                        rule_clean = rule.strip()
                        if rule_clean and len(rule_clean) > 15:
                            do_not_rules.append((adr_num, rule_clean))

            except Exception:
                pass

    # Add total count
    lines.append(f"# Total: {len(adrs)} ADRs")
    lines.append("#")
    lines.append("# Format: ADR_NUMBER | STATUS | TITLE | PATH")
    lines.append("# " + "=" * 76)
    lines.append("")

    # Group ADRs by range
    foundation = [(n, s, t, p) for n, s, t, p in adrs if int(n) <= 13]
    core = [(n, s, t, p) for n, s, t, p in adrs if 14 <= int(n) <= 23]
    advanced = [(n, s, t, p) for n, s, t, p in adrs if int(n) >= 24]

    if foundation:
        lines.append("# FOUNDATION (0001-0013)")
        for adr_num, status, title, path in foundation:
            lines.append(f"{adr_num} | {status} | {title} | {path}")
        lines.append("")

    if core:
        lines.append("# CORE PATTERNS (0014-0023)")
        for adr_num, status, title, path in core:
            lines.append(f"{adr_num} | {status} | {title} | {path}")
        lines.append("")

    if advanced:
        lines.append("# ADVANCED PATTERNS (0024+)")
        for adr_num, status, title, path in advanced:
            lines.append(f"{adr_num} | {status} | {title} | {path}")
        lines.append("")

    # Add AI Quick Reference section with DO NOT rules
    if do_not_rules:
        lines.append("# " + "=" * 76)
        lines.append("# AI QUICK REFERENCE - KEY DO NOT's")
        lines.append("# " + "=" * 76)
        lines.append("")

        # Deduplicate and sort by ADR number
        seen = set()
        unique_rules = []
        for adr_num, rule in sorted(do_not_rules, key=lambda x: int(x[0])):
            rule_key = rule.lower()[:50]
            if rule_key not in seen:
                seen.add(rule_key)
                unique_rules.append((adr_num, rule))

        for adr_num, rule in unique_rules:
            lines.append(f"# {rule} (ADR-{adr_num})")

    return "\n".join(lines)


def generate_readme_manifest():
    """Generate manifest of all README.md files with descriptions for AI reference."""
    lines = [
        "# L9 README File Manifest",
        f"# Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}",
        "#",
        "# AI Reference: Quick lookup for module documentation",
        "# Each entry shows: PATH | TITLE | DESCRIPTION",
        "# " + "=" * 76,
        "",
    ]

    gitignore_patterns = load_gitignore_patterns()
    readmes = []

    for root, dirs, files in os.walk(REPO_DIR):
        # Skip ignored directories
        dirs[:] = [
            d
            for d in dirs
            if d not in SKIP_DIRS
            and not is_ignored(
                os.path.relpath(os.path.join(root, d), REPO_DIR),
                gitignore_patterns,
                is_dir=True,
            )
        ]

        for fname in files:
            if fname.lower() == "readme.md":
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, REPO_DIR)

                if is_ignored(rel_path, gitignore_patterns):
                    continue

                try:
                    with open(fpath, encoding="utf-8") as f:
                        content = f.read(4096)  # Read first 4KB for speed

                    # Extract title (first # heading)
                    title = "Untitled"
                    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                    if title_match:
                        title = title_match.group(1).strip()
                        # Clean up common prefixes
                        title = re.sub(r"^(README[:\s-]*)", "", title, flags=re.I)
                        if not title:
                            title = "Untitled"

                    # Extract description (first paragraph after title)
                    description = ""
                    # Find first non-heading, non-empty paragraph
                    paragraphs = re.split(r"\n\s*\n", content)
                    for para in paragraphs:
                        para = para.strip()
                        # Skip headings, badges, empty lines, YAML frontmatter
                        if (
                            para
                            and not para.startswith("#")
                            and not para.startswith("![")
                            and not para.startswith("[![")
                            and not para.startswith("---")
                            and not para.startswith("|")
                            and not para.startswith("```")
                            and len(para) > 20
                        ):
                            # Clean and truncate
                            description = para.replace("\n", " ").strip()
                            description = re.sub(r"\s+", " ", description)
                            if len(description) > 150:
                                description = description[:147] + "..."
                            break

                    if not description:
                        description = "(No description)"

                    # Get top-level directory for grouping
                    parts = rel_path.split(os.sep)
                    top_dir = parts[0] if len(parts) > 1 else "root"

                    readmes.append((top_dir, rel_path, title, description))

                except Exception:
                    pass

    # Sort by path
    readmes.sort(key=lambda x: x[1])

    # Group by top-level directory
    grouped = defaultdict(list)
    for top_dir, rel_path, title, desc in readmes:
        grouped[top_dir].append((rel_path, title, desc))

    # Add summary
    lines.append(
        f"# Total: {len(readmes)} README files across {len(grouped)} directories"
    )
    lines.append("")

    # Output grouped
    for top_dir in sorted(grouped.keys()):
        items = grouped[top_dir]
        lines.append("# " + "=" * 76)
        lines.append(f"# {top_dir.upper()} ({len(items)} files)")
        lines.append("# " + "=" * 76)
        lines.append("")

        for rel_path, title, desc in items:
            lines.append(f"PATH: {rel_path}")
            lines.append(f"TITLE: {title}")
            lines.append(f"DESC: {desc}")
            lines.append("")

    # Add AI quick reference section
    lines.append("# " + "=" * 76)
    lines.append("# AI QUICK REFERENCE - KEY MODULES")
    lines.append("# " + "=" * 76)
    lines.append("")

    # Highlight critical READMEs
    critical_patterns = [
        ("core/", "Core L9 runtime and abstractions"),
        ("memory/", "Memory substrate and packet storage"),
        ("api/", "FastAPI routes and endpoints"),
        ("agents/", "Agent definitions and capabilities"),
        ("orchestration/", "Task routing and orchestration"),
        ("deploy/", "Deployment configurations"),
        ("config/", "YAML configurations and DI"),
    ]

    for pattern, purpose in critical_patterns:
        matches = [r for r in readmes if r[1].startswith(pattern)]
        if matches:
            lines.append(f"# {pattern} - {purpose}")
            for _, path, title, _ in matches[:3]:  # Top 3 per category
                lines.append(f"#   {path}: {title}")
            lines.append("")

    return "\n".join(lines)


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
        "bootstrap_phases.txt": (
            "🚀 Agent bootstrap phases (7-phase)",
            generate_bootstrap_phases,
        ),
        "memory_architecture.txt": (
            "🧠 Memory architecture",
            generate_memory_architecture,
        ),
        "governance_model.txt": (
            "🔐 Governance & approval model",
            generate_governance_model,
        ),
        # Agent/orchestration layer
        "agent_catalog.txt": ("🤖 Agent catalog", generate_agent_catalog),
        "kernel_catalog.txt": (
            "🧬 Kernel catalog (10 kernels)",
            generate_kernel_catalog,
        ),
        "orchestrator_catalog.txt": (
            "🎭 Orchestrator catalog",
            generate_orchestrator_catalog,
        ),
        "tool_catalog.txt": ("🔧 Tool catalog", generate_tool_catalog),
        # Events and schemas
        "event_types.txt": ("📨 Event types & packet kinds", generate_event_types),
        "singleton_registry.txt": (
            "📦 Singleton registry",
            generate_singleton_registry,
        ),
        # NEW: Infrastructure & operations
        "migration_catalog.txt": ("🗄️  Migration catalog", generate_migration_catalog),
        "feature_flags.txt": ("🏳️  Feature flags", generate_feature_flags),
        "test_catalog.txt": ("🧪 Test catalog", generate_test_catalog),
        "telemetry_endpoints.txt": (
            "📈 Telemetry & observability",
            generate_telemetry_endpoints,
        ),
        "deployment_manifest.txt": (
            "🚢 Deployment manifest",
            generate_deployment_manifest,
        ),
        # API and code structure
        "api_surfaces.txt": ("🌐 API surfaces", generate_api_surfaces),
        "entrypoints.txt": ("🚪 Entry points", generate_entrypoints),
        "class_definitions.txt": (
            "📋 Classes & data models",
            generate_class_definitions,
        ),
        "function_signatures.txt": (
            "⚙️  Function signatures (ALL)",
            generate_function_signatures,
        ),
        # Configuration and dependencies
        "config_files.txt": ("⚙️  Configuration files", generate_config_files),
        "dependencies.txt": ("📦 Dependencies", generate_dependencies),
        "env_refs.txt": ("🔐 Environment variables", generate_env_refs),
        "imports.txt": ("📚 Python imports", generate_imports),
        # NEW v2.1: Neo4j Graph Support (relationships for queries)
        "inheritance_graph.txt": (
            "🧬 Inheritance graph (Neo4j EXTENDS)",
            generate_inheritance_graph,
        ),
        "method_catalog.txt": (
            "🔍 Method catalog (Neo4j HAS_METHOD)",
            generate_method_catalog,
        ),
        "route_handlers.txt": (
            "🛤️  Route handlers (Neo4j HANDLED_BY)",
            generate_route_handlers,
        ),
        "file_metrics.txt": (
            "📏 File metrics (lines, complexity)",
            generate_file_metrics,
        ),
        "pydantic_models.txt": (
            "📐 Pydantic models (API schemas)",
            generate_pydantic_models,
        ),
        "dynamic_tool_catalog.txt": (
            "🔧 Dynamic tool catalog (scanned)",
            generate_dynamic_tool_catalog,
        ),
        "async_function_map.txt": (
            "⚡ Async function map",
            generate_async_function_map,
        ),
        "decorator_catalog.txt": ("🏷️  Decorator catalog", generate_decorator_catalog),
        "adr_catalog.txt": ("📜 ADR catalog", generate_adr_catalog),
        "readme_manifest.txt": ("📖 README manifest", generate_readme_manifest),
    }

    logger.info("Generating indexes...")

    results = {}
    for filename, (emoji_desc, generator) in generators.items():
        try:
            content = generator()
            # Prepend meta header to every file
            index_name = filename.replace(".txt", "").replace("_", " ").title()
            header = generate_meta_header(index_name)
            full_content = header + "\n" + content
            size = len(full_content.encode("utf-8"))

            # Write to local repo (required - must succeed)
            repo_file = os.path.join(REPO_INDEX_DIR, filename)
            with open(repo_file, "w", encoding="utf-8") as f:
                f.write(full_content)

            # Write to Dropbox (optional - continue on error)
            try:
                dropbox_file = os.path.join(DROPBOX_EXPORT_DIR, filename)
                with open(dropbox_file, "w", encoding="utf-8") as f:
                    f.write(full_content)
            except Exception as e:
                logger.debug("Dropbox export failed", filename=filename, error=str(e))

            # Write to iCloud (optional - continue on error)
            try:
                icloud_file = os.path.join(ICLOUD_EXPORT_DIR, filename)
                with open(icloud_file, "w", encoding="utf-8") as f:
                    f.write(full_content)
            except Exception as e:
                logger.debug("iCloud export failed", filename=filename, error=str(e))

            results[filename] = size
            logger.info("Generated", file=filename, desc=emoji_desc, bytes=size)
        except Exception as e:
            logger.error("Generation failed", file=filename, error=str(e))
            results[filename] = 0

    total_size = sum(results.values())
    success_count = sum(1 for s in results.values() if s > 0)
    fail_count = len(results) - success_count

    logger.info(
        "Index generation complete",
        total_files=len(results),
        success=success_count,
        failed=fail_count,
        total_bytes=total_size,
        repo_index_dir=REPO_INDEX_DIR,
    )

    # Print summary table to stdout for human readability
    logger.info("\n{'=' * 60}")
    logger.info("  repo index generation complete")
    logger.info("{'=' * 60}")
    logger.info("  repo:    repo name", REPO_NAME=REPO_NAME)
    logger.info("  output:  repo index dir", REPO_INDEX_DIR=REPO_INDEX_DIR)
    logger.error(
        "  files:   {len(results)} (success count ok, fail count failed)",
        success_count=success_count,
        fail_count=fail_count,
    )
    logger.info("  total:   {total_size:,} bytes")
    logger.info("{'=' * 60}")
    for filename, size in sorted(results.items()):
        status = "OK" if size > 0 else "FAIL"
        logger.info("  [{status:>4}] filename {size:>10,} bytes", filename=filename)
    logger.info("{'=' * 60}\n")

    # Phase 2: Ingest to Memory (pgvector)
    logger.info("\n" + "=" * 60)
    logger.info("🧠 PHASE 2: Ingesting indexes to L9 Memory...")
    logger.info("=" * 60)
    try:
        result = subprocess.run(
            [sys.executable, "scripts/memory/ingest_repo_indexes.py", "--verbose"],
            capture_output=True,
            text=True,
            cwd=REPO_DIR,
        )
        if result.returncode == 0:
            logger.info("✅ Memory ingestion complete")
            # Show summary from output
            for line in result.stdout.split("\n"):
                if "Ingested" in line or "📄" in line:
                    logger.info(f"   {line.strip()}")
        else:
            logger.warning(f"⚠️ Memory ingestion failed: {result.stderr[:200]}")
    except Exception as e:
        logger.warning(f"⚠️ Memory ingestion skipped: {e}")

    # Phase 3: Load to Neo4j (graph)
    logger.info("\n" + "=" * 60)
    logger.info("🔷 PHASE 3: Loading indexes to Neo4j graph...")
    logger.info("=" * 60)
    try:
        # Check if Neo4j credentials are available
        # Prefer C1 external URL for local script execution
        neo4j_url = os.getenv("NEO4J_URL") or os.getenv("NEO4J_URI")
        neo4j_password = os.getenv("NEO4J_PASSWORD")

        # If using Docker internal URL, switch to C1 external
        if neo4j_url and "neo4j:7687" in neo4j_url:
            neo4j_url = "bolt://46.62.243.82:30687"
            os.environ["NEO4J_URL"] = neo4j_url
            logger.info(f"   Using C1 external Neo4j: {neo4j_url}")

        if neo4j_url and neo4j_password:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/memory/load_indexes_to_neo4j.py",
                    "--verbose",
                ],
                capture_output=True,
                text=True,
                cwd=REPO_DIR,
            )
            if result.returncode == 0:
                logger.info("✅ Neo4j loading complete")
                for line in result.stdout.split("\n"):
                    if "Loaded" in line or "nodes" in line or "relationships" in line:
                        logger.info(f"   {line.strip()}")
            else:
                logger.warning(f"⚠️ Neo4j loading failed: {result.stderr[:200]}")
        else:
            logger.info("⏭️ Neo4j loading skipped (NEO4J_URL or NEO4J_PASSWORD not set)")
            logger.info("   Set environment variables to enable graph loading")
    except Exception as e:
        logger.warning(f"⚠️ Neo4j loading skipped: {e}")

    logger.info("\n" + "=" * 60)
    logger.info("✨ FULL PIPELINE COMPLETE")
    logger.info("=" * 60)
    logger.info("📂 Files: reports/repo-index/")
    logger.info("🧠 Memory: pgvector embeddings (semantic search)")
    logger.info("🔷 Graph: Neo4j (relationship queries)")


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
    "tags": [
        "api",
        "ast",
        "async",
        "auth",
        "authorization",
        "caching",
        "config",
        "dataclass",
        "debugging",
        "event-driven",
    ],
    "keywords": [
        "agent",
        "api",
        "architecture",
        "async",
        "bootstrap",
        "catalog",
        "decorator",
        "definitions",
    ],
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
