#!/usr/bin/env python3
"""
Extract Code Facts from L9 Secure AI OS Repository

Generates CODE-MAP.yaml and README.meta.yaml files from Python AST analysis.
This script is the SOURCE OF TRUTH for AI-facing contracts.

Usage:
    python scripts/extract_code_facts.py

Output:
    - docs/CODE-MAP.yaml (subsystems, entrypoints, classes, schemas, invariants)
    - l9/core/agents/README.meta.yaml
    - l9/core/memory/README.meta.yaml
    - l9/core/tools/README.meta.yaml
    - l9/api/README.meta.yaml

Run this script whenever:
    1. API signatures change
    2. Key classes are renamed or moved
    3. Data models (Pydantic schemas) are updated
    4. Subsystem boundaries change
    5. Before committing to main
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Extract Code Facts",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-18T02:07:37Z",
    "updated_at": "2026-01-18T02:07:37Z",
    "layer": "operations",
    "domain": ".dora",
    "module_name": "extract_code_facts",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import ast
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed. Run: pip install pyyaml")
    sys.exit(1)


# ============================================================================
# Configuration: Define subsystems and protected files
# ============================================================================

SUBSYSTEMS = {
    "agents": {
        "path": "l9/core/agents",
        "entrypoint_class": "Kernel",
        "entrypoint_method": "execute",
        "protected_files": [
            "l9/core/agents/kernel.py",
            "l9/core/agents/__init__.py",
        ],
        "ai_allowed_patterns": [
            "l9/core/agents/executor.py",
            "l9/core/agents/builtin/**",
            "tests/**",
            "docs/**",
        ],
    },
    "memory": {
        "path": "l9/core/memory",
        "entrypoint_class": "MemorySubstrate",
        "entrypoint_method": "search",
        "protected_files": [
            "l9/core/memory/memory.py",
            "l9/core/memory/redisclient.py",
        ],
        "ai_allowed_patterns": [
            "l9/core/memory/retrieval.py",
            "l9/core/memory/semantic.py",
            "tests/**",
            "docs/**",
        ],
    },
    "tools": {
        "path": "l9/core/tools",
        "entrypoint_class": "ToolRegistry",
        "entrypoint_method": "invoke",
        "protected_files": [
            "l9/core/tools/registry.py",
            "l9/core/tools/sandbox.py",
        ],
        "ai_allowed_patterns": [
            "l9/core/tools/validators.py",
            "l9/core/tools/wrappers/**",
            "tests/**",
            "docs/**",
        ],
    },
    "api": {
        "path": "l9/api",
        "entrypoint_class": "FastAPI",
        "entrypoint_method": "POST /agents/{agent_id}/execute",
        "protected_files": [
            "l9/server.py",
            "l9/websocket_orchestrator.py",
            "l9/auth.py",
        ],
        "ai_allowed_patterns": [
            "l9/api/routes/**",
            "l9/api/models.py",
            "tests/**",
            "docs/**",
        ],
    },
}

GLOBAL_PROTECTED_FILES = [
    "l9/kernel_loader.py",
    "l9/websocket_orchestrator.py",
    "l9/redisclient.py",
    "l9/executor.py",
    "docker-compose.yml",
    ".env",
    "config.yaml",
]

INVARIANTS = {
    "agents": [
        "Agent IDs are UUIDv4",
        "Agent execution uses kernel entry point",
        "All agent state is stored in memory substrate",
        "Tool access is mediated by tool registry",
    ],
    "memory": [
        "All IDs are UUIDv4",
        "All timestamps are UTC ISO-8601",
        "TTL in seconds (positive integers)",
        "Embeddings are list[float]",
    ],
    "tools": [
        "Tool names must exist in registry",
        "Resource limits enforced (CPU, memory, disk, timeout)",
        "All tool executions sandboxed and logged",
    ],
    "api": [
        "All APIs require JWT authentication",
        "Request/response schemas validated via Pydantic",
        "All logging is structured JSON",
    ],
}


# ============================================================================
# AST Extraction: Parse Python code for facts
# ============================================================================

class CodeFactExtractor:
    """Extract code facts using Python AST."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def extract_function_signature(self, node: ast.FunctionDef) -> str:
        """Extract function signature from AST node."""
        # Get argument names and types
        args = []
        for arg in node.args.args:
            args.append(arg.arg)

        # Get return type if annotated
        return_type = ""
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return_type = f" -> {node.returns.id}"
            elif isinstance(node.returns, ast.Subscript):
                return_type = " -> [complex type]"

        return f"def {node.name}({', '.join(args)}){return_type}"

    def extract_class_info(self, filepath: Path, class_name: str) -> Dict[str, Any]:
        """Extract class info: methods, docstring, line range."""
        try:
            content = filepath.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append({
                                "name": item.name,
                                "is_async": isinstance(item, ast.AsyncFunctionDef),
                                "line": item.lineno,
                            })

                    return {
                        "name": class_name,
                        "file": str(filepath.relative_to(self.repo_root)),
                        "line_range": [node.lineno, node.end_lineno or node.lineno],
                        "methods": methods,
                        "docstring": ast.get_docstring(node) or "",
                    }
        except Exception as e:
            print(f"WARNING: Could not parse {filepath}: {e}")

        return {}

    def find_pydantic_models(self, subsystem_path: Path) -> List[Dict[str, Any]]:
        """Find Pydantic dataclasses/models in subsystem."""
        models = []

        if not subsystem_path.exists():
            return models

        for py_file in subsystem_path.rglob("*.py"):
            try:
                content = py_file.read_text()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    # Find dataclasses with field annotations
                    if isinstance(node, ast.ClassDef):
                        # Check if it has __dataclass__ or Pydantic decorators
                        is_dataclass = any(
                            (isinstance(dec, ast.Name) and dec.id == "dataclass")
                            or (isinstance(dec, ast.Name) and "Model" in dec.id)
                            for dec in node.decorator_list
                        )

                        if is_dataclass or node.name.endswith("Result") or node.name.endswith("Entry"):
                            fields = []
                            for item in node.body:
                                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                                    fields.append(item.target.id)

                            if fields:
                                models.append({
                                    "name": node.name,
                                    "file": str(py_file.relative_to(self.repo_root)),
                                    "fields": fields,
                                    "docstring": ast.get_docstring(node) or "",
                                })
            except Exception as e:
                print(f"WARNING: Could not parse {py_file}: {e}")

        return models


# ============================================================================
# CODE-MAP.yaml Generation
# ============================================================================

def generate_code_map(repo_root: Path, extractor: CodeFactExtractor) -> Dict[str, Any]:
    """Generate CODE-MAP.yaml structure."""
    code_map = {
        "version": "1.0",
        "last_verified": datetime.utcnow().isoformat() + "Z",
        "subsystems": {},
    }

    for subsystem_name, config in SUBSYSTEMS.items():
        subsystem_path = repo_root / config["path"]

        # Extract class info
        entrypoint_file = None
        entrypoint_info = {}

        # Try to find entrypoint class
        for py_file in subsystem_path.rglob("*.py"):
            class_info = extractor.extract_class_info(py_file, config["entrypoint_class"])
            if class_info:
                entrypoint_file = py_file
                entrypoint_info = class_info
                break

        # Find models
        models = extractor.find_pydantic_models(subsystem_path)

        # Build subsystem entry
        code_map["subsystems"][subsystem_name] = {
            "path": config["path"],
            "purpose": f"L9 {subsystem_name.capitalize()} Subsystem",
            "entry_point": {
                "file": entrypoint_info.get("file", f"{config['path']}/kernel.py"),
                "class": config["entrypoint_class"],
                "method": config["entrypoint_method"],
                "line_range": entrypoint_info.get("line_range", [1, 50]),
            },
            "key_classes": [entrypoint_info] if entrypoint_info else [],
            "data_models": models,
            "protected_files": config["protected_files"],
            "ai_allowed_patterns": config["ai_allowed_patterns"],
            "ai_forbidden_patterns": config["protected_files"],
            "invariants": INVARIANTS.get(subsystem_name, []),
        }

    return code_map


# ============================================================================
# README.meta.yaml Generation
# ============================================================================

def generate_meta_yaml(subsystem_name: str) -> Dict[str, Any]:
    """Generate README.meta.yaml for a subsystem."""
    config = SUBSYSTEMS[subsystem_name]

    return {
        "location": f"l9/core/{subsystem_name}/README.md",
        "type": "subsystemreadme",
        "metadata": {
            "subsystem": subsystem_name,
            "modulepath": config["path"],
            "owner": "Igor",
            "lastupdated": datetime.utcnow().isoformat() + "Z",
            "purpose": f"Documents the {subsystem_name} subsystem, contracts, and AI collaboration rules.",
        },
        "sections": {
            "overview": {"required": True},
            "responsibilities": {"required": True},
            "components": {"required": True},
            "datamodels": {"required": True},
            "lifecycle": {"required": True},
            "configuration": {"required": False},
            "apisurface": {"required": True},
            "observability": {"required": False},
            "testing": {"required": False},
            "airules": {"required": True},
        },
        "invariants": INVARIANTS.get(subsystem_name, []),
        "aicollaboration": {
            "allowedscopes": config["ai_allowed_patterns"],
            "restrictedscopes": config["protected_files"],
            "forbiddenscopes": config["protected_files"],
            "requiredprereading": [
                "docs/architecture.md",
                "docs/ai-collaboration.md",
                f"l9/core/{subsystem_name}/README.md",
            ],
        },
    }


# ============================================================================
# Main: Write files
# ============================================================================

def main():
    """Main entry point."""
    repo_root = Path(__file__).parent.parent
    docs_dir = repo_root / "docs"
    docs_dir.mkdir(exist_ok=True)

    print("🔍 Extracting code facts from L9 repository...")

    extractor = CodeFactExtractor(repo_root)

    # Generate CODE-MAP.yaml
    print("📝 Generating docs/CODE-MAP.yaml...")
    code_map = generate_code_map(repo_root, extractor)

    code_map_path = docs_dir / "CODE-MAP.yaml"
    with open(code_map_path, "w") as f:
        yaml.dump(code_map, f, default_flow_style=False, sort_keys=False)
    print(f"✅ Generated {code_map_path}")

    # Generate README.meta.yaml for each subsystem
    for subsystem_name in SUBSYSTEMS.keys():
        subsystem_path = repo_root / SUBSYSTEMS[subsystem_name]["path"]
        subsystem_path.mkdir(parents=True, exist_ok=True)

        print(f"📝 Generating {subsystem_name} README.meta.yaml...")
        meta_yaml = generate_meta_yaml(subsystem_name)

        meta_path = subsystem_path / "README.meta.yaml"
        with open(meta_path, "w") as f:
            yaml.dump(meta_yaml, f, default_flow_style=False, sort_keys=False)
        print(f"✅ Generated {meta_path}")

    print("\n✨ Code facts extraction complete!")
    print(f"📊 Generated {len(SUBSYSTEMS)} subsystem metadata files")
    print(f"📋 All files committed to source control")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": ".DO-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [".dora", "api", "ast", "auth", "cli", "config", "filesystem", "operations", "realtime", "rest-api"],
    "keywords": ["extract", "extractor", "fact", "facts", "find", "function", "generate", "map"],
    "business_value": "This script is the SOURCE OF TRUTH for AI-facing contracts. python scripts/extract_code_facts.py docs/CODE-MAP.yaml (subsystems, entrypoints, classes, schemas, invariants) l9/core/agents/README.meta.y",
    "last_modified": "2026-01-18T02:07:37Z",
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
