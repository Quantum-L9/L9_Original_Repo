#!/usr/bin/env python3
"""
DORA Complete Block Injection Script (Contract-Compliant)
==========================================================
Injects all THREE required blocks per dora-contract.yaml:
  1. Header Meta (TOP) - 14 mandatory fields
  2. Footer Meta (BOTTOM) - Extended metadata
  3. DORA Block (VERY END) - __l9_trace__ runtime trace

Usage:
    python scripts/audit/inject_dora_complete.py --repo /path/to/L9 --dry-run
    python scripts/audit/inject_dora_complete.py --repo /path/to/L9 --execute
    python scripts/audit/inject_dora_complete.py --repo /path/to/L9 --execute --file path/to/file.py
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Inject Dora Complete",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-18T02:10:54Z",
    "updated_at": "2026-01-25T14:59:57Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "inject_dora_complete",
    "type": "router",
    "status": "deprecated",
    "integrates_with": {
        "api_endpoints": ["GET /path", "POST /path"],
        "datasources": [
            "Anthropic API",
            "Gmail API",
            "HTTP API",
            "Neo4j",
            "OpenAI API",
            "Perplexity API",
            "PostgreSQL",
            "Redis",
            "S3",
            "Slack API",
        ],
        "memory_layers": ["working_memory", "episodic_memory", "semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ============================================================================
# DATA MODELS


@dataclass
class ClassInfo:
    """Information about a discovered class."""

    name: str
    file_path: str
    line_number: int
    module_path: str
    bases: list[str] = field(default_factory=list)  # Base class names


@dataclass
class HeaderMeta:
    """Header Meta - 14 mandatory fields per contract."""

    component_id: str
    component_name: str
    module_version: str
    created_at: str
    created_by: str
    layer: str
    domain: str
    type: str
    status: str
    governance_level: str
    compliance_required: bool
    audit_trail: bool
    purpose: str
    dependencies: list[str]


@dataclass
class FooterMeta:
    """Footer Meta - Extended metadata that header references."""

    component_id: str
    security_classification: str = "internal"
    execution_mode: str = "on-demand"
    timeout_seconds: int = 30
    performance_tier: str = "realtime"
    last_modified: str = ""
    modified_by: str = ""
    change_summary: str = "Initial generation"


@dataclass
class DoraTraceBlock:
    """DORA Block - L9_TRACE_TEMPLATE (runtime trace)."""

    trace_id: str = ""
    task: str = ""
    timestamp: str = ""
    patterns_used: list[str] = field(default_factory=list)
    graph: dict = field(default_factory=lambda: {"nodes": [], "edges": []})
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    metrics: dict = field(
        default_factory=lambda: {
            "confidence": "",
            "errors_detected": [],
            "stability_score": "",
        }
    )


# ============================================================================
# INJECTOR ENGINE


class DoraCompleteInjector:
    """Contract-compliant DORA block injection engine."""

    # Layer mapping based on directory structure
    LAYER_MAP = {
        "core": "foundation",
        "agents": "intelligence",
        "api": "operations",
        "memory": "learning",
        "runtime": "operations",
        "services": "operations",
        "orchestration": "intelligence",
        "orchestrators": "intelligence",
        "world_model": "learning",
        "simulation": "learning",
        "governance": "security",
        "compliance": "security",
        "security": "security",
        "config": "foundation",
        "schemas": "foundation",
        "scripts": "operations",
        "tests": "operations",
        # Agent-specific folders
        "email_agent": "integration",
        "mac_agent": "integration",
        "slack_agent": "integration",
        "mcp_memory": "integration",
        "clients": "integration",
        # Additional folders
        "workers": "operations",
        "telemetry": "operations",
        "ir_engine": "intelligence",
        "graph_adapter": "integration",
        "collaborative_cells": "intelligence",
        "dev": "operations",
        "codegen": "foundation",
    }

    # Domain mapping
    DOMAIN_MAP = {
        "agents": "agent_execution",
        "memory": "memory_substrate",
        "governance": "governance",
        "core/agents": "agent_execution",
        "core/governance": "governance",
        "core/memory": "memory_substrate",
        "core/tools": "tool_registry",
        "core/worldmodel": "world_model",
        "services/symbolic_computation": "symbolic_computation",
        "orchestrators": "orchestration",
        "api": "api_gateway",
        "runtime": "runtime_operations",
        "config": "configuration",
        # Agent integrations
        "email_agent": "email_integration",
        "mac_agent": "mac_integration",
        "slack_agent": "slack_integration",
        "mcp_memory": "mcp_integration",
        "clients": "external_clients",
        # Additional domains
        "workers": "background_workers",
        "telemetry": "observability",
        "ir_engine": "ir_compilation",
        "graph_adapter": "graph_integration",
        "collaborative_cells": "collaborative_reasoning",
        "dev": "development_tools",
        "codegen": "code_generation",
        "services/research": "research_services",
    }

    # Type mapping based on filename patterns (order matters - first match wins)
    TYPE_PATTERNS = {
        "client": ["client", "api_client", "sdk"],
        "adapter": ["adapter", "bridge", "wrapper", "compatibility"],
        "service": ["service", "svc"],
        "engine": ["engine", "executor", "processor", "compiler"],
        "collector": ["collector", "extractor", "loader", "ingest"],
        "tracker": ["tracker", "monitor", "observer", "metrics"],
        "router": ["router", "routes", "handler"],
        "schema": ["schema", "model", "types"],
        "config": ["config", "settings", "constants"],
        "utility": ["helper", "util", "tool", "utils"],
        "factory": ["factory", "builder", "generator"],
        "repository": ["repository", "repo", "store", "dao"],
        "controller": ["controller", "orchestrator"],
        "validator": ["validator", "checker", "verifier"],
    }

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.classes_found: list[ClassInfo] = []
        self.files_to_process: dict[str, list[ClassInfo]] = {}
        self.component_id_counter: dict[str, int] = {}

    def scan_repository(
        self, single_file: str | None = None, force: bool = False
    ) -> None:
        """Scan repository for Python and YAML files."""
        if single_file:
            file_path = Path(single_file)
            if not file_path.is_absolute():
                file_path = self.repo_path / file_path
            if file_path.exists() and file_path.suffix in (".py", ".yaml", ".yml"):
                if file_path.suffix == ".py":
                    classes = self._extract_classes(file_path)
                else:
                    classes = []  # YAML files don't have classes
                # Process file even if no classes (function-only modules or YAML)
                self.files_to_process[str(file_path)] = classes
                self.classes_found.extend(classes)
            print(f"🔍 Processing single file: {single_file}")
            return

        print(f"🔍 Scanning repository: {self.repo_path}")

        skip_dirs = [
            "_archived",
            "__pycache__",
            ".venv",
            "venv",
            "node_modules",
            ".git",
            "tests",
        ]

        # Scan Python files
        for py_file in self.repo_path.rglob("*.py"):
            if any(skip in str(py_file) for skip in skip_dirs):
                continue
            classes = self._extract_classes(py_file)
            if classes:
                self.files_to_process[str(py_file)] = classes
                self.classes_found.extend(classes)

        # Scan YAML files
        for yaml_file in self.repo_path.rglob("*.yaml"):
            if any(skip in str(yaml_file) for skip in skip_dirs):
                continue
            self.files_to_process[str(yaml_file)] = []

        for yml_file in self.repo_path.rglob("*.yml"):
            if any(skip in str(yml_file) for skip in skip_dirs):
                continue
            self.files_to_process[str(yml_file)] = []

        py_count = sum(1 for f in self.files_to_process if f.endswith(".py"))
        yaml_count = len(self.files_to_process) - py_count
        print(
            f"✅ Found {len(self.classes_found)} classes in {py_count} Python files, {yaml_count} YAML files"
        )

    def _extract_classes(self, file_path: Path) -> list[ClassInfo]:
        """Extract class definitions from a Python file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            classes = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    module_path = self._get_module_path(file_path)
                    # Extract base class names
                    bases = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            bases.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            bases.append(base.attr)
                    classes.append(
                        ClassInfo(
                            name=node.name,
                            file_path=str(file_path),
                            line_number=node.lineno,
                            module_path=module_path,
                            bases=bases,
                        )
                    )

            return classes
        except Exception as e:
            print(f"⚠️  Error parsing {file_path}: {e}")
            return []

    def _get_module_path(self, file_path: Path) -> str:
        """Convert file path to Python module path."""
        try:
            rel_path = file_path.relative_to(self.repo_path)
            module_parts = [*list(rel_path.parts[:-1]), rel_path.stem]
            return ".".join(module_parts)
        except ValueError:
            return file_path.stem

    def _generate_component_id(self, file_path: str, layer: str) -> str:
        """Generate unique component ID per contract format."""
        try:
            parts = Path(file_path).relative_to(self.repo_path).parts
            domain_abbrev = parts[0][:3].upper() if len(parts) >= 2 else "L9"
        except ValueError:
            domain_abbrev = "L9"

        layer_abbrev = layer[:4].upper()
        prefix = f"{domain_abbrev}-{layer_abbrev}"

        if prefix not in self.component_id_counter:
            self.component_id_counter[prefix] = 1
        else:
            self.component_id_counter[prefix] += 1

        counter = self.component_id_counter[prefix]
        return f"{domain_abbrev}-{layer_abbrev}-{counter:03d}"

    def _infer_layer(self, file_path: str) -> str:
        """Infer layer from file path."""
        try:
            parts = Path(file_path).relative_to(self.repo_path).parts
            for part in parts:
                if part in self.LAYER_MAP:
                    return self.LAYER_MAP[part]
        except ValueError:
            pass
        return "operations"

    def _infer_domain(self, file_path: str) -> str:
        """Infer domain from file path."""
        try:
            parts = Path(file_path).relative_to(self.repo_path).parts

            # Try multi-part matches first
            for i in range(len(parts)):
                path_segment = "/".join(parts[: i + 1])
                if path_segment in self.DOMAIN_MAP:
                    return self.DOMAIN_MAP[path_segment]

            # Try single part matches
            for part in parts:
                if part in self.DOMAIN_MAP:
                    return self.DOMAIN_MAP[part]

            return parts[0] if parts else "general"
        except ValueError:
            return "general"

    def _infer_type(self, file_path: str) -> str:
        """Infer component type from filename."""
        filename = Path(file_path).stem.lower()

        for comp_type, patterns in self.TYPE_PATTERNS.items():
            if any(pattern in filename for pattern in patterns):
                return comp_type

        return "utility"

    def _infer_status(self, file_path: str) -> str:
        """Infer component status from path, content, and markers."""
        path_str = str(file_path).lower()

        # Priority 1: Folder-based detection
        if "_archived" in path_str or "/archived/" in path_str:
            return "archived"
        if "/deprecated/" in path_str or "_deprecated" in path_str:
            return "deprecated"
        if "/experimental/" in path_str or "_experimental" in path_str:
            return "experimental"
        if "/draft/" in path_str or "_draft" in path_str:
            return "draft"
        if "/legacy/" in path_str or "_legacy" in path_str:
            return "deprecated"

        # Priority 2: Content-based detection
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                content_lower = content.lower()

            # Check for deprecation markers
            deprecation_markers = [
                "@deprecated",
                "# deprecated",
                "# todo: deprecate",
                "# todo: remove",
                "warnings.warn.*deprecat",
                "deprecationwarning",
                "this module is deprecated",
                "this class is deprecated",
            ]
            for marker in deprecation_markers:
                if marker in content_lower:
                    return "deprecated"

            # Check for experimental markers
            experimental_markers = [
                "# experimental",
                "# wip",
                "# work in progress",
                "this is experimental",
                "experimental feature",
            ]
            for marker in experimental_markers:
                if marker in content_lower:
                    return "experimental"

            # Check for draft markers
            draft_markers = [
                "# draft",
                "# todo: finish",
                "# incomplete",
                "not yet implemented",
            ]
            for marker in draft_markers:
                if marker in content_lower:
                    return "draft"

            # Check docstring for status indicators
            docstring_match = re.search(r'^"""(.*?)"""', content, re.DOTALL)
            if docstring_match:
                docstring = docstring_match.group(1).lower()
                if "deprecated" in docstring:
                    return "deprecated"
                if "experimental" in docstring:
                    return "experimental"
                if "stable" in docstring:
                    return "stable"
                if "production" in docstring:
                    return "production"

        except (OSError, UnicodeDecodeError):
            pass

        # Default: active
        return "active"

    def _detect_type_from_content(
        self, file_path: str, classes: list[ClassInfo]
    ) -> str | None:
        """Detect file type from decorators, base classes, and content patterns."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return None

        # Priority 1: Decorator patterns (most specific)
        decorator_patterns = {
            "router": [
                r"@router\.",
                r"@app\.(get|post|put|delete|patch)",
                r"@api_router",
            ],
            "worker": [r"@celery", r"@task", r"@background_task", r"@scheduled"],
            "test": [r"@pytest", r"@mock\.", r"def test_"],
            "dataclass": [r"@dataclass"],
            "middleware": [r"@middleware", r"@app\.middleware"],
        }

        for comp_type, patterns in decorator_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content):
                    return comp_type

        # Priority 2: Base class inheritance
        base_class_mapping = {
            "BaseModel": "schema",
            "BaseAgent": "agent",
            "BaseService": "service",
            "APIRouter": "router",
            "TestCase": "test",
            "Exception": "exception",
            "Enum": "enum",
        }

        for cls in classes:
            for base in cls.bases:
                if base in base_class_mapping:
                    return base_class_mapping[base]

        # Priority 3: Docstring-based type detection
        docstring_match = re.search(r'^"""(.*?)"""', content, re.DOTALL)
        if docstring_match:
            docstring = docstring_match.group(1).lower()
            docstring_type_hints = {
                "adapter": ["compatibility layer", "wrapper", "adapter", "bridge"],
                "client": ["client for", "api client", "sdk client", "http client"],
                "service": ["service for", "provides service", "backend service"],
                "utility": ["utility", "helper functions", "common functions"],
                "router": ["api routes", "endpoints", "rest api"],
                "schema": ["pydantic", "data model", "schema definition"],
                "engine": ["engine for", "processor", "compiler", "executor"],
            }
            for comp_type, hints in docstring_type_hints.items():
                if any(hint in docstring for hint in hints):
                    return comp_type

        # Priority 4: Content patterns
        content_patterns = {
            "router": ["APIRouter()", "from fastapi import APIRouter"],
            "schema": ["class Config:", "model_validator", "field_validator"],
            "service": ["async def ", "self.repository", "self.client"],
            "cli": ["argparse.ArgumentParser", "@click.command", "if __name__"],
        }

        for comp_type, patterns in content_patterns.items():
            if any(p in content for p in patterns):
                return comp_type

        return None

    def _get_reverse_imports(self, file_path: str) -> list[str]:
        """Find what files import this module using ripgrep."""
        try:
            # Convert file path to module path for import matching
            rel_path = Path(file_path).relative_to(self.repo_path)
            module_parts = [*list(rel_path.parts[:-1]), rel_path.stem]
            module_path = ".".join(module_parts)

            # Also check for partial imports (e.g., "from core.agents import executor")
            parent_module = ".".join(module_parts[:-1])
            module_name = module_parts[-1]

            importers = set()

            # Search for "from module.path import" or "import module.path"
            patterns = [
                f"from {module_path} import",
                f"import {module_path}",
                f"from {parent_module} import.*{module_name}",
            ]

            for pattern in patterns:
                try:
                    result = subprocess.run(
                        ["rg", "-l", pattern, "--type", "py", "."],
                        capture_output=True,
                        text=True,
                        cwd=self.repo_path,
                        timeout=10,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        for f in result.stdout.strip().split("\n"):
                            if f and f != file_path and not f.startswith("tests/"):
                                # Convert to module path
                                try:
                                    imp_rel = Path(f).relative_to(Path("."))
                                    imp_module = ".".join(
                                        [*list(imp_rel.parts[:-1]), imp_rel.stem]
                                    )
                                    importers.add(imp_module)
                                except ValueError:
                                    importers.add(f)
                except subprocess.TimeoutExpired:
                    continue

            return sorted(importers)[:10]  # Limit to top 10
        except Exception:
            return []

    def _detect_datasources_from_content(self, file_path: str) -> list[str]:
        """Detect actual datasource usage from imports and content."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return []

        datasources = set()

        # PostgreSQL indicators
        if any(
            p in content
            for p in ["asyncpg", "psycopg", "databases", "sqlalchemy", "PostgreSQL"]
        ):
            datasources.add("PostgreSQL")

        # Redis indicators
        if any(p in content for p in ["redis", "aioredis", "Redis"]):
            datasources.add("Redis")

        # Neo4j indicators
        if any(p in content for p in ["neo4j", "Neo4j", "graph_client", "GraphClient"]):
            datasources.add("Neo4j")

        # S3/Blob indicators
        if any(p in content for p in ["boto3", "s3", "S3", "blob_store"]):
            datasources.add("S3")

        # Gmail/Google API indicators
        if any(
            p in content for p in ["GmailClient", "gmail_client", "googleapiclient"]
        ):
            datasources.add("Gmail API")

        # Slack API indicators
        if any(
            p in content
            for p in ["SlackClient", "slack_sdk", "WebClient", "slack_client"]
        ):
            datasources.add("Slack API")

        # OpenAI indicators
        if any(p in content for p in ["openai", "OpenAI", "ChatCompletion"]):
            datasources.add("OpenAI API")

        # Anthropic indicators
        if any(p in content for p in ["anthropic", "Anthropic", "Claude"]):
            datasources.add("Anthropic API")

        # HTTP client indicators (external APIs)
        if any(
            p in content for p in ["httpx", "aiohttp", "requests.get", "requests.post"]
        ):
            datasources.add("HTTP API")

        # Perplexity indicators
        if any(p in content for p in ["perplexity", "PerplexityClient"]):
            datasources.add("Perplexity API")

        return sorted(datasources)

    def _analyze_base_classes(self, classes: list[ClassInfo]) -> dict[str, any]:
        """Analyze base classes for enhanced type and domain inference."""
        result = {
            "primary_type": None,
            "domain_hints": [],
            "is_abstract": False,
            "inheritance_chain": [],
        }

        # Base class to type/domain mapping
        base_mappings = {
            # Type mappings
            "BaseModel": {"type": "schema", "domain": "data_models"},
            "BaseAgent": {"type": "agent", "domain": "agent_execution"},
            "BaseService": {"type": "service", "domain": "services"},
            "APIRouter": {"type": "router", "domain": "api_gateway"},
            "TestCase": {"type": "test", "domain": "testing"},
            "Exception": {"type": "exception", "domain": "error_handling"},
            "Enum": {"type": "enum", "domain": "data_models"},
            "ABC": {"type": "abstract", "domain": None},
            # Framework-specific
            "FastAPI": {"type": "app", "domain": "api_gateway"},
            "CeleryTask": {"type": "worker", "domain": "background_jobs"},
            "BaseRepository": {"type": "repository", "domain": "data_access"},
            "BaseOrchestrator": {"type": "orchestrator", "domain": "orchestration"},
            "BaseTool": {"type": "tool", "domain": "tool_registry"},
            # L9-specific
            "PacketEnvelope": {"type": "packet", "domain": "memory_substrate"},
            "KernelBase": {"type": "kernel", "domain": "governance"},
        }

        for cls in classes:
            for base in cls.bases:
                result["inheritance_chain"].append(base)
                if base in base_mappings:
                    mapping = base_mappings[base]
                    if not result["primary_type"]:
                        result["primary_type"] = mapping["type"]
                    if mapping["domain"]:
                        result["domain_hints"].append(mapping["domain"])
                if base == "ABC":
                    result["is_abstract"] = True

        return result

    def _detect_api_endpoints(self, file_path: str) -> list[str]:
        """Extract API endpoint paths from router files."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return []

        endpoints = []
        # Match @router.get("/path"), @router.post("/path"), etc.
        pattern = (
            r'@(?:router|app)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
        )
        for match in re.finditer(pattern, content, re.IGNORECASE):
            method = match.group(1).upper()
            path = match.group(2)
            endpoints.append(f"{method} {path}")

        return endpoints[:10]  # Limit to 10

    def _infer_governance_level(self, domain: str, layer: str) -> str:
        """Infer governance level based on domain and layer."""
        critical_domains = [
            "governance",
            "memory_substrate",
            "agent_execution",
            "security",
            "configuration",
        ]
        critical_layers = ["security", "foundation"]

        if domain in critical_domains or layer in critical_layers:
            return "critical"
        if layer == "intelligence" or layer == "learning":
            return "high"
        return "medium"

    def _parse_module_docstring(self, file_path: str) -> dict[str, any]:
        """Extract metadata from module docstring including structured sections."""
        result = {
            "title": "",
            "purpose": "",
            "version": "1.0.0",
            "status": "active",
            "component_name": "",
            "responsibilities": [],  # NEW: "Key responsibilities:", "This class manages:"
            "exclusions": [],  # NEW: "This class does NOT:", "Does not:"
            "tags_from_docstring": [],  # NEW: Extract implicit tags
        }

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            docstring = ast.get_docstring(tree)

            if not docstring:
                return result

            lines = docstring.strip().split("\n")

            # Extract title (first non-empty line)
            for line in lines:
                line = line.strip()
                if line and not line.startswith("=") and not line.startswith("-"):
                    result["title"] = line
                    # Extract component name from title like "L9 Core Agents - Agent Instance"
                    if " - " in line:
                        result["component_name"] = line.split(" - ")[-1].strip()
                    break

            # Extract version
            for line in lines:
                if line.strip().lower().startswith("version:"):
                    result["version"] = line.split(":", 1)[1].strip()
                    break

            # Parse sections
            current_section = None
            section_content = []

            section_markers = {
                "responsibilities": [
                    "key responsibilities",
                    "this class manages",
                    "responsibilities:",
                    "manages:",
                ],
                "exclusions": [
                    "this class does not",
                    "does not:",
                    "this module does not",
                ],
                "purpose": [
                    "the ",
                    "this ",
                    "provides",
                    "implements",
                    "represents",
                    "handles",
                    "orchestrat",
                ],
            }

            for i, line in enumerate(lines):
                stripped = line.strip()
                stripped_lower = stripped.lower()

                # Skip title and underlines
                if i < 3 and (stripped.startswith("=") or stripped.startswith("-")):
                    continue

                # Detect section start
                for section_name, markers in section_markers.items():
                    if any(
                        stripped_lower.startswith(m)
                        or (
                            stripped_lower.endswith(":")
                            and m.rstrip(":") in stripped_lower
                        )
                        for m in markers
                    ):
                        # Save previous section
                        if current_section and section_content:
                            if current_section == "purpose" and not result["purpose"]:
                                result["purpose"] = " ".join(section_content)[:200]
                            elif current_section == "responsibilities":
                                result["responsibilities"] = section_content[:10]
                            elif current_section == "exclusions":
                                result["exclusions"] = section_content[:10]
                        current_section = section_name
                        section_content = []
                        break

                # Collect bullet points
                if stripped.startswith("-") and current_section:
                    item = stripped[1:].strip()
                    if item:
                        section_content.append(item)
                        # Extract tags from bullet items
                        for word in item.lower().split():
                            if word in [
                                "agent",
                                "tool",
                                "memory",
                                "api",
                                "governance",
                                "task",
                                "execution",
                                "runtime",
                            ]:
                                result["tags_from_docstring"].append(word)

                # Collect paragraph content for purpose
                elif (
                    current_section == "purpose"
                    and stripped
                    and not stripped.endswith(":")
                ):
                    if not any(stripped.startswith(c) for c in ["=", "-", "*"]):
                        section_content.append(stripped)

            # Save final section
            if current_section and section_content:
                if current_section == "purpose" and not result["purpose"]:
                    result["purpose"] = " ".join(section_content)[:200]
                elif current_section == "responsibilities":
                    result["responsibilities"] = section_content[:10]
                elif current_section == "exclusions":
                    result["exclusions"] = section_content[:10]

            # Detect status from keywords in docstring
            docstring_lower = docstring.lower()
            if "deprecated" in docstring_lower:
                result["status"] = "deprecated"
            elif "experimental" in docstring_lower:
                result["status"] = "experimental"
            elif "beta" in docstring_lower:
                result["status"] = "beta"
            elif "alpha" in docstring_lower:
                result["status"] = "alpha"
            elif "stable" in docstring_lower:
                result["status"] = "stable"
            elif "production" in docstring_lower:
                result["status"] = "production"
            else:
                result["status"] = "active"

            # Deduplicate tags
            result["tags_from_docstring"] = list(set(result["tags_from_docstring"]))[:5]

        except Exception:
            pass

        return result

    def _generate_purpose(self, classes: list[ClassInfo], file_path: str) -> str:
        """Generate purpose statement - prefer docstring, fallback to inference."""
        # First try to get from docstring
        doc_meta = self._parse_module_docstring(file_path)
        if doc_meta["purpose"]:
            return doc_meta["purpose"]

        # Fallback to class-based generation
        filename = Path(file_path).stem
        class_names = [c.name for c in classes]

        if len(class_names) == 1:
            return f"Implements {class_names[0]} for {filename.replace('_', ' ')} functionality"
        if len(class_names) > 1:
            return f"Provides {filename.replace('_', ' ')} components including {', '.join(class_names[:3])}"
        return f"Utility module for {filename.replace('_', ' ')}"

    def _extract_dependencies(self, file_path: str) -> list[str]:
        """Extract import dependencies from file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            deps: set[str] = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        # Only track internal L9 imports
                        if any(
                            alias.name.startswith(p)
                            for p in ["core.", "memory.", "runtime.", "api.", "agents."]
                        ):
                            deps.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module and any(
                        node.module.startswith(p)
                        for p in ["core.", "memory.", "runtime.", "api.", "agents."]
                    ):
                        deps.add(node.module)

            return sorted(deps)[:5]
        except Exception:
            return []

    def _get_file_dates(self, file_path: str) -> tuple[str, str]:
        """Get actual file creation and modification dates."""
        try:
            stat = Path(file_path).stat()
            # st_birthtime is creation time on macOS
            # st_mtime is modification time
            created = datetime.fromtimestamp(stat.st_birthtime).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            modified = datetime.fromtimestamp(stat.st_mtime).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            return created, modified
        except (AttributeError, OSError):
            # Fallback if st_birthtime not available (Linux)
            try:
                stat = Path(file_path).stat()
                modified = datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
                return modified, modified  # Use mtime for both
            except OSError:
                timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                return timestamp, timestamp

    def _get_git_author(self, file_path: str) -> str:
        """Get original author from git history."""
        try:
            # Get the author of the first commit that added this file
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--follow",
                    "--diff-filter=A",
                    "--format=%an",
                    "--",
                    file_path,
                ],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                authors = result.stdout.strip().split("\n")
                return authors[0] if authors else "Unknown"
            return "Unknown"
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return "Unknown"

    def _get_git_creation_date(self, file_path: str) -> str | None:
        """Get actual creation date from git history."""
        try:
            # Get the date of the first commit that added this file
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--follow",
                    "--diff-filter=A",
                    "--format=%aI",
                    "--",
                    file_path,
                ],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                dates = result.stdout.strip().split("\n")
                if dates and dates[0]:
                    # Convert ISO format to our format
                    try:
                        dt = datetime.fromisoformat(dates[0].replace("Z", "+00:00"))
                        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                    except ValueError:
                        return None
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    def generate_metadata(
        self, file_path: str, classes: list[ClassInfo]
    ) -> tuple[HeaderMeta, FooterMeta, DoraTraceBlock]:
        """Generate all three metadata blocks for a file."""
        # Parse docstring for accurate metadata
        doc_meta = self._parse_module_docstring(file_path)

        # Analyze base classes for enhanced inference
        base_analysis = self._analyze_base_classes(classes)

        layer = self._infer_layer(file_path)

        # Domain: prefer base class hints, then path inference
        domain = self._infer_domain(file_path)
        if base_analysis["domain_hints"]:
            domain = base_analysis["domain_hints"][0]  # Use first hint

        # Type: priority order - decorator/content > base class > filename
        # (Decorators like @router are more specific than base class inheritance)
        content_type = self._detect_type_from_content(file_path, classes)
        comp_type = (
            content_type  # Decorators first (most specific)
            or base_analysis["primary_type"]  # Then base class
            or self._infer_type(file_path)  # Finally filename
        )

        # Override domain if decorator detection found router type
        if content_type == "router":
            domain = "api_gateway"

        governance_level = self._infer_governance_level(domain, layer)

        # Get dates: prefer git history, fallback to file system
        git_created = self._get_git_creation_date(file_path)
        file_created, modified_at = self._get_file_dates(file_path)
        created_at = git_created or file_created

        # Get author: prefer git history, fallback to placeholder
        created_by = self._get_git_author(file_path)
        if created_by == "Unknown":
            created_by = "L9_Codegen_Engine"  # Only use placeholder if git fails

        component_id = self._generate_component_id(file_path, layer)
        # Prefer docstring component name, fallback to filename
        component_name = (
            doc_meta["component_name"] or Path(file_path).stem.replace("_", " ").title()
        )
        # Prefer docstring purpose
        purpose = doc_meta["purpose"] or self._generate_purpose(classes, file_path)
        # Use docstring version
        module_version = doc_meta["version"]
        # Use comprehensive status detection (folders, decorators, comments, docstring)
        status = self._infer_status(file_path)
        dependencies = self._extract_dependencies(file_path)

        header = HeaderMeta(
            component_id=component_id,
            component_name=component_name,
            module_version=module_version,  # From docstring
            created_at=created_at,  # Git history or file birthtime
            created_by=created_by,  # Git author or fallback
            layer=layer,
            domain=domain,
            type=comp_type,  # Content-based or filename inference
            status=status,  # From docstring keywords
            governance_level=governance_level,
            compliance_required=True,
            audit_trail=True,
            purpose=purpose,  # From docstring
            dependencies=dependencies,
        )

        footer = FooterMeta(
            component_id=component_id,
            security_classification="internal",
            execution_mode="on-demand",
            timeout_seconds=30,
            performance_tier="realtime" if layer == "operations" else "batch",
            last_modified=modified_at,  # Actual file modification date
            modified_by="L9_Codegen_Engine",
            change_summary="Initial generation with DORA compliance",
        )

        trace = DoraTraceBlock()  # Empty trace block - runtime will populate

        return header, footer, trace

    def _check_existing_blocks(self, file_path: str) -> dict[str, bool]:
        """Check which DORA blocks already exist in file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            is_yaml = file_path.endswith((".yaml", ".yml"))

            if is_yaml:
                return {
                    "header": "# DORA META" in content
                    or "# component_name:" in content,
                    "footer": "# DORA FOOTER" in content or "# tags:" in content,
                    "trace": True,  # YAML files don't have trace blocks
                    "legacy": False,
                }
            # Use regex to detect actual variable assignments at line start
            # ONLY detect dict assignments - not string templates or comments
            # This prevents false positives in generator/validator scripts
            return {
                "header": bool(
                    re.search(r"^__dora_meta__\s*=\s*\{", content, re.MULTILINE)
                ),
                "footer": bool(
                    re.search(r"^__dora_footer__\s*=\s*\{", content, re.MULTILINE)
                ),
                "trace": bool(
                    re.search(r"^__l9_trace__\s*=\s*\{", content, re.MULTILINE)
                ),
                # Check for old-style blocks (actual assignment at line start)
                "legacy": bool(
                    re.search(r"^__dora_block__\s*=\s*\{", content, re.MULTILINE)
                ),
            }
        except Exception:
            return {"header": False, "footer": False, "trace": False, "legacy": False}

    def _strip_dict_block(self, content: str, var_name: str) -> str:
        """Remove a dict variable using brace counting for nested dicts."""
        pattern = rf"{var_name}\s*=\s*\{{"
        match = re.search(pattern, content)
        if not match:
            return content

        start_pos = match.start()
        brace_start = match.end() - 1
        brace_count = 0
        end_pos = brace_start

        for i, char in enumerate(content[brace_start:], start=brace_start):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i + 1
                    break

        # Include trailing newlines
        while end_pos < len(content) and content[end_pos] in "\n":
            end_pos += 1

        return content[:start_pos] + content[end_pos:]

    def _strip_existing_blocks(self, content: str) -> str:
        """Remove existing DORA blocks from content for re-injection."""
        # Remove comment blocks with their dict definitions
        # IMPORTANT: Use precise patterns to avoid touching other section headers

        # Header block (76 = signs) - old format with comment lines
        header_pattern = r"# ={76}\n# DORA HEADER META[^\n]*\n(?:# [^\n]*\n)?# ={76}\n"
        content = re.sub(header_pattern, "", content, flags=re.DOTALL)

        # Header block (76 = signs) - new format (just banner + __dora_meta__)
        # Pattern: ={76} line immediately before __dora_meta__
        header_pattern_new = r"# ={76}\n(?=__dora_meta__)"
        content = re.sub(header_pattern_new, "", content)

        # Footer block (76 = signs specifically)
        footer_pattern = r"\n?# ={76}\n# DORA FOOTER META[^\n]*\n# ={76}\n"
        content = re.sub(footer_pattern, "", content, flags=re.DOTALL)

        # Remove dict definitions FIRST using brace counting (before comment patterns)
        content = self._strip_dict_block(content, "__dora_meta__")
        content = self._strip_dict_block(content, "__dora_footer__")
        content = self._strip_dict_block(content, "__l9_trace__")
        content = self._strip_dict_block(content, "__dora_block__")  # Legacy

        # Trace block - full block with dict (76 = signs specifically)
        trace_pattern = (
            r"\n?# ={76}\n# L9 DORA BLOCK[^\n]*\n[^#]*# END L9 DORA BLOCK\n# ={76}\n?"
        )
        content = re.sub(trace_pattern, "", content, flags=re.DOTALL)

        # Trace block - empty/stub blocks (just comments, no dict)
        # These are malformed blocks without __l9_trace__ dict
        stub_trace_pattern = (
            r"\n?# ={76}\n"
            r"# L9 DORA BLOCK[^\n]*\n"
            r"(?:# [^\n]*\n)*"  # Any comment lines
            r"# ={76}\n"
            r"(?:# ={76}\n)?"  # Optional extra separator
            r"# END L9 DORA BLOCK[^\n]*\n?"
            r"(?:# ={76}\n?)?"
        )
        # Apply multiple times to catch all duplicates
        for _ in range(10):
            new_content = re.sub(stub_trace_pattern, "\n", content, flags=re.DOTALL)
            if new_content == content:
                break
            content = new_content

        # Clean up orphaned DORA comment blocks (76 = signs, any format)
        # Pattern: ={76} line followed by DORA-related comment, followed by ={76} line
        orphan_pattern = (
            r"\n?# ={76}\n(?:# (?:DORA|See footer|L9 DORA|END L9)[^\n]*\n)+# ={76}\n?"
        )
        content = re.sub(orphan_pattern, "\n", content)

        # Clean up standalone 76-char banner lines (orphaned after dict removal)
        content = re.sub(r"# ={76}\n(?=\n)", "", content)  # Before blank line
        content = re.sub(
            r"\n# ={76}\n(?=from |import )", "\n", content
        )  # Before imports
        return re.sub(r"\n{3,}", "\n\n", content)

    def _format_header_meta(
        self, header: HeaderMeta, file_path: str, modified_at: str
    ) -> str:
        """Format Header Meta block for Python file (TOP)."""
        Path(file_path).stem

        # Generate integrates_with from actual file analysis
        self._generate_integrates_with(file_path, header.domain, header.layer)

        return """# ============================================================================
"""

    def _format_header_meta_yaml(
        self, header: HeaderMeta, file_path: str, modified_at: str
    ) -> str:
        """Format Header Meta block for YAML file (TOP)."""
        file_name = Path(file_path).stem

        return f"""
# component_name: "{header.component_name}"
# module_version: "{header.module_version}"
# created_by: "{header.created_by}"
# created_at: "{header.created_at}"
# updated_at: "{modified_at}"
# layer: "{header.layer}"
# domain: "{header.domain}"
# file_name: "{file_name}"
# type: "{header.type}"
# status: "{header.status}"

"""

    def _format_footer_meta_yaml(
        self, footer: FooterMeta, header: HeaderMeta, file_path: str
    ) -> str:
        """Format Footer Meta block for YAML file (BOTTOM)."""
        tags = self._generate_smart_tags_yaml(
            file_path, header.domain, header.type, header.layer
        )
        keywords = self._generate_smart_keywords_yaml(file_path, header.component_name)

        return f"""

# tags: {json.dumps(tags)}
# keywords: {json.dumps(keywords)}
# last_modified: "{footer.last_modified}"
# ============================================================================
"""

    def _generate_smart_tags_yaml(
        self, file_path: str, domain: str, comp_type: str, layer: str
    ) -> list[str]:
        """Generate tags for YAML files."""
        tags = set()
        tags.add(layer)
        tags.add(comp_type)
        tags.add(domain.replace("_", "-"))

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read().lower()

            # YAML-specific tags
            yaml_tags = {
                "agent": "agent-config",
                "schema": "schema",
                "workflow": "workflow",
                "pipeline": "pipeline",
                "config": "configuration",
                "kernel": "kernel",
                "prompt": "prompt",
                "tool": "tool-config",
                "model": "model-config",
                "api": "api-config",
                "database": "database-config",
                "redis": "redis-config",
                "openai": "openai",
                "anthropic": "anthropic",
            }

            for keyword, tag in yaml_tags.items():
                if keyword in content:
                    tags.add(tag)

        except (OSError, UnicodeDecodeError):
            pass

        return sorted(tags)[:8]

    def _generate_smart_keywords_yaml(
        self, file_path: str, component_name: str
    ) -> list[str]:
        """Generate keywords for YAML files."""
        keywords = set()

        # Add component name words
        for word in component_name.lower().replace("_", " ").replace("-", " ").split():
            if len(word) > 2:
                keywords.add(word)

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Extract top-level keys as keywords
            import yaml

            try:
                data = yaml.safe_load(content)
                if isinstance(data, dict):
                    for key in list(data.keys())[:10]:
                        if isinstance(key, str) and len(key) > 2:
                            keywords.add(key.lower())
            except yaml.YAMLError:
                pass

        except (OSError, UnicodeDecodeError):
            pass

        return sorted(keywords)[:6]

    def _generate_integrates_with(
        self, file_path: str, domain: str, layer: str
    ) -> dict:
        """Generate integrates_with from actual file analysis."""
        # Get real data from file analysis
        api_endpoints = self._detect_api_endpoints(file_path)
        datasources = self._detect_datasources_from_content(file_path)
        reverse_imports = self._get_reverse_imports(file_path)

        # Determine memory layers based on actual imports/usage
        memory_layers = []
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Working memory indicators
            if any(
                p in content
                for p in [
                    "working_memory",
                    "WorkingMemory",
                    "session_context",
                    "context_manager",
                    "ContextManager",
                    "short_term",
                ]
            ):
                memory_layers.append("working_memory")

            # Episodic memory indicators
            if any(
                p in content
                for p in [
                    "episodic",
                    "EpisodicMemory",
                    "project_history",
                    "conversation_history",
                    "chat_history",
                    "message_history",
                ]
            ):
                memory_layers.append("episodic_memory")

            # Semantic memory indicators
            if any(
                p in content
                for p in [
                    "semantic",
                    "SemanticSearch",
                    "pgvector",
                    "embedding",
                    "vector_store",
                    "similarity_search",
                    "VectorStore",
                ]
            ):
                memory_layers.append("semantic_memory")

            # Memory substrate indicators (general memory system usage)
            if (
                any(
                    p in content
                    for p in [
                        "memory.substrate",
                        "MemorySubstrate",
                        "substrate_service",
                        "PacketStore",
                        "PacketEnvelope",
                        "ingest_packet",
                    ]
                )
                and "working_memory" not in memory_layers
            ):
                memory_layers.append("working_memory")

        except (OSError, UnicodeDecodeError):
            pass

        return {
            "api_endpoints": api_endpoints,
            "datasources": datasources,
            "memory_layers": memory_layers,
            "imported_by": reverse_imports,  # NEW: What depends on this file
        }

    def _format_footer_meta(
        self,
        footer: FooterMeta,
        header: HeaderMeta,
        file_path: str = "",
        classes: list[ClassInfo] | None = None,
    ) -> str:
        """Format Footer Meta block for Python file (BOTTOM, before trace)."""
        classes = classes or []

        # Generate smart tags from content analysis (or fallback to basic)
        if file_path:
            self._generate_smart_tags(
                file_path, classes, header.domain, header.type, header.layer
            )
            self._generate_smart_keywords(file_path, classes, header.component_name)
        else:
            self._generate_tags(header.domain, header.type, header.layer)
            self._generate_keywords(header.component_name, header.domain)

        return """
"""

    def _generate_tags(self, domain: str, comp_type: str, layer: str) -> list[str]:
        """Generate tags based on domain, type, and layer."""
        tags = [domain.replace("_", "-"), comp_type, layer]

        # Add domain-specific tags
        domain_tags = {
            "agent_execution": ["agent", "runtime"],
            "memory_substrate": ["memory", "persistence", "audit"],
            "governance": ["governance", "compliance", "security"],
            "tool_registry": ["tools", "dispatch"],
            "orchestration": ["orchestration", "workflow"],
            "api_gateway": ["api", "http", "rest"],
        }
        tags.extend(domain_tags.get(domain, []))

        return list(set(tags))[:6]  # Limit to 6 unique tags

    def _generate_keywords(self, component_name: str, domain: str) -> list[str]:
        """Generate keywords from component name and domain."""
        # Split component name into words
        words = component_name.lower().replace("_", " ").replace("-", " ").split()
        keywords = words[:3]  # First 3 words

        # Add domain-related keywords
        domain_keywords = {
            "agent_execution": ["executor", "runtime", "task"],
            "memory_substrate": ["packet", "envelope", "ingestion"],
            "governance": ["approval", "policy", "compliance"],
            "tool_registry": ["tool", "dispatch", "capability"],
        }
        keywords.extend(domain_keywords.get(domain, [])[:2])

        return list(set(keywords))[:5]  # Limit to 5 unique keywords

    def _generate_smart_tags(
        self,
        file_path: str,
        classes: list[ClassInfo],
        domain: str,
        comp_type: str,
        layer: str,
    ) -> list[str]:
        """Generate tags from actual file content analysis."""
        tags = set()

        # Base tags from classification
        tags.add(layer)
        tags.add(comp_type)
        tags.add(domain.replace("_", "-"))

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return list(tags)[:8]

        # Strip existing DORA blocks to avoid circular detection
        content = self._strip_existing_blocks(content)
        content_lower = content.lower()

        # Technology tags from imports (expanded)
        import_tags = {
            "fastapi": "api",
            "pydantic": "validation",
            "redis": "cache",
            "neo4j": "graph-db",
            "asyncpg": "postgres",
            "structlog": "logging",
            "openai": "llm",
            "anthropic": "llm",
            "langchain": "llm",
            "celery": "async-tasks",
            "pytest": "testing",
            "httpx": "http-client",
            "websocket": "realtime",
            "jwt": "auth",
            "ast": "ast",
            "subprocess": "subprocess",
            "pathlib": "filesystem",
            "yaml": "config",
            "json": "serialization",
            "sqlalchemy": "orm",
            "aiohttp": "http-client",
            "click": "cli",
            "argparse": "cli",
            "typer": "cli",
        }

        for imp, tag in import_tags.items():
            if f"import {imp}" in content_lower or f"from {imp}" in content_lower:
                tags.add(tag)

        # Design pattern tags from class names
        pattern_suffixes = {
            "visitor": "visitor-pattern",
            "factory": "factory-pattern",
            "builder": "builder-pattern",
            "adapter": "adapter-pattern",
            "scanner": "scanner",
            "parser": "parser",
            "analyzer": "analyzer",
            "inspector": "inspector",
            "auditor": "audit-tool",
            "validator": "validation",
            "handler": "handler",
            "middleware": "middleware",
            "service": "service",
            "repository": "data-access",
            "client": "client",
            "engine": "engine",
            "executor": "executor",
            "orchestrator": "orchestration",
            "router": "routing",
            "loader": "loader",
            "exporter": "exporter",
            "importer": "importer",
        }

        for cls in classes:
            name_lower = cls.name.lower()
            for suffix, tag in pattern_suffixes.items():
                if suffix in name_lower:
                    tags.add(tag)

        # Docstring-based semantic tags with context awareness
        # These tags indicate what the file IMPLEMENTS (not what it analyzes)
        implementation_tags = {
            "static analysis": "static-analysis",
            "code quality": "code-quality",
            "lint": "linting",
            "benchmark": "performance",
            "profile": "profiling",
            "debug": "debugging",
            "trace": "tracing",
            "metric": "metrics",
            "monitor": "monitoring",
            "queue": "queue",
            "message": "messaging",
            "event": "event-driven",
            "webhook": "webhooks",
            "rest": "rest-api",
            "graphql": "graphql",
            "grpc": "grpc",
            "websocket": "realtime",
            "stream": "streaming",
            "batch": "batch-processing",
            "schedule": "scheduling",
            "cron": "scheduling",
            "permission": "authorization",
            "encrypt": "security",
            "hash": "security",
            "secret": "security",
        }

        # Tags that need context check (might be "what we detect" vs "what we are")
        context_sensitive_tags = {
            "cache": "caching",
            "api": "api",
            "auth": "auth",
            "migration": "migration",
            "test": "testing",
            "mock": "mocking",
            "fixture": "testing",
        }

        # Analysis verbs that indicate "we detect X" not "we are X"
        analysis_verbs = [
            "scan",
            "detect",
            "find",
            "look for",
            "search",
            "check",
            "analyze",
            "inspect",
            "audit",
            "identify",
            "discover",
            "suspicious",
            "pattern",
            "violation",
            "warn",
        ]

        # Extract docstring for context analysis
        docstring_match = re.search(r'^"""(.*?)"""', content, re.DOTALL)
        docstring = docstring_match.group(1).lower() if docstring_match else ""

        # Check if file is primarily an analysis/detection tool
        is_analysis_tool = any(verb in docstring for verb in analysis_verbs[:8])

        # Add implementation tags (these are safe, no context needed)
        for keyword, tag in implementation_tags.items():
            if keyword in content_lower:
                tags.add(tag)

        # Add context-sensitive tags only if NOT in analysis context
        for keyword, tag in context_sensitive_tags.items():
            if keyword in content_lower:
                # If this is an analysis tool and the keyword is in docstring,
                # it's likely describing what we DETECT, not what we ARE
                if is_analysis_tool and keyword in docstring:
                    # Check if it's mentioned as an implementation (import, class, etc.)
                    if (
                        f"import {keyword}" in content_lower
                        or f"from {keyword}" in content_lower
                    ):
                        tags.add(tag)
                    # Skip - it's what we analyze, not what we implement
                else:
                    tags.add(tag)

        # Action-based tags (what the file DOES as its primary purpose)
        if any(v in docstring for v in ["scan", "scans"]):
            tags.add("scanner")
        if any(v in docstring for v in ["audit", "audits"]):
            tags.add("audit-tool")

        # Decorator-based tags
        if "@router" in content or "@app." in content:
            tags.add("endpoint")
        if "async def" in content:
            tags.add("async")
        if "@dataclass" in content:
            tags.add("dataclass")
        if "BaseModel" in content:
            tags.add("pydantic")

        return sorted(tags)[:10]  # Limit to 10 tags

    def _generate_smart_keywords(
        self, file_path: str, classes: list[ClassInfo], component_name: str
    ) -> list[str]:
        """Generate keywords from actual content analysis."""
        keywords = set()

        # Stop words to filter out (generic, common terms)
        stop_words = {
            "self",
            "none",
            "true",
            "false",
            "return",
            "def",
            "class",
            "import",
            "from",
            "the",
            "and",
            "for",
            "with",
            "this",
            "that",
            "are",
            "was",
            "get",
            "set",
            "has",
            "have",
            "init",
            "main",
            "run",
            "call",
            "make",
            "new",
            "add",
            "del",
            "pop",
            "len",
            "str",
            "int",
            "list",
            "dict",
            "iter",
            "next",
            "item",
            "items",
            "key",
            "keys",
            "value",
            "values",
            "args",
            "kwargs",
            "func",
            "method",
            "attr",
            "name",
            "path",
            "file",
            "data",
            "info",
            "result",
            "output",
            "input",
            "param",
            "params",
            "config",
            "options",
            "settings",
            "context",
            "request",
            "response",
            "error",
            "exception",
            "message",
            "text",
            "content",
            "body",
            "type",
            "base",
            "node",
            "generic",
            "visit",
            "child",
            "children",
            "parent",
            "level",
            "line",
            "lineno",
            "lines",
            "code",
            "source",
            "target",
        }

        def is_valid_keyword(word: str) -> bool:
            """Check if word is a valid keyword (not a stop word, sufficient length)."""
            return len(word) > 2 and word.lower() not in stop_words

        # Add component name words
        for word in component_name.lower().replace("_", " ").replace("-", " ").split():
            if is_valid_keyword(word):
                keywords.add(word)

        # Add class names as keywords
        for cls in classes:
            # Split CamelCase into words
            words = re.findall(r"[A-Z][a-z]+|[a-z]+", cls.name)
            for word in words:
                if is_valid_keyword(word):
                    keywords.add(word.lower())

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Strip existing DORA blocks to avoid circular detection
            content = self._strip_existing_blocks(content)

            # Extract keywords from docstring (highest value)
            docstring_match = re.search(r'^"""(.*?)"""', content, re.DOTALL)
            if docstring_match:
                docstring = docstring_match.group(1).lower()
                # Extract significant words from docstring
                doc_words = re.findall(r"\b([a-z]{4,})\b", docstring)
                # Prioritize nouns and domain terms (appear multiple times or are capitalized originally)
                word_counts = {}
                for w in doc_words:
                    if is_valid_keyword(w):
                        word_counts[w] = word_counts.get(w, 0) + 1
                # Add words that appear multiple times or are domain-specific
                domain_terms = {
                    "mutable",
                    "state",
                    "global",
                    "suspicious",
                    "pattern",
                    "module",
                    "assignment",
                    "analysis",
                    "scan",
                    "audit",
                    "heuristic",
                    "detection",
                    "violation",
                    "compliance",
                    "governance",
                    "trace",
                    "memory",
                    "cache",
                    "queue",
                    "executor",
                    "agent",
                    "kernel",
                    "substrate",
                    "orchestrator",
                    "router",
                    "handler",
                    "middleware",
                    "service",
                    "repository",
                }
                for w, count in word_counts.items():
                    if count >= 2 or w in domain_terms:
                        keywords.add(w)

            # Extract function names as keywords (but filter stop words)
            func_pattern = r"def\s+([a-z_][a-z0-9_]*)\s*\("
            for match in re.finditer(func_pattern, content):
                func_name = match.group(1)
                if not func_name.startswith("_") and len(func_name) > 3:
                    # Split snake_case
                    for word in func_name.split("_"):
                        if is_valid_keyword(word):
                            keywords.add(word)
        except (OSError, UnicodeDecodeError):
            pass

        return sorted(keywords)[:8]  # Limit to 8 keywords

    def _find_test_coverage(self, file_path: str) -> dict[str, any]:
        """Find associated test files and estimate coverage."""
        result = {
            "test_files": [],
            "test_count": 0,
            "has_tests": False,
        }

        try:
            module_name = Path(file_path).stem
            rel_path = Path(file_path).relative_to(self.repo_path)

            # Common test file patterns
            patterns = [
                f"test_{module_name}.py",
                f"test_{module_name}*.py",
                f"{module_name}_test.py",
            ]

            # Also check in tests/ directory mirroring source structure
            test_dir = self.repo_path / "tests"
            source_parts = list(rel_path.parts[:-1])  # e.g., ['core', 'agents']

            for pattern in patterns:
                # Check in tests/<source_path>/
                if source_parts:
                    test_path = test_dir / "/".join(source_parts)
                    if test_path.exists():
                        matches = list(test_path.glob(pattern))
                        for m in matches:
                            result["test_files"].append(
                                str(m.relative_to(self.repo_path))
                            )

                # Check in tests/ root
                matches = list(test_dir.glob(f"**/{pattern}"))
                for m in matches:
                    rel = str(m.relative_to(self.repo_path))
                    if rel not in result["test_files"]:
                        result["test_files"].append(rel)

            # Count test functions in found test files
            for test_file in result["test_files"][:3]:  # Check first 3
                try:
                    test_path = self.repo_path / test_file
                    with open(test_path, encoding="utf-8") as f:
                        test_content = f.read()
                    result["test_count"] += len(re.findall(r"def test_", test_content))
                except (OSError, UnicodeDecodeError):
                    pass

            result["has_tests"] = len(result["test_files"]) > 0
            result["test_files"] = result["test_files"][:5]  # Limit to 5

        except Exception:
            pass

        return result

    def _generate_success_metrics(self, performance_tier: str) -> dict:
        """Generate success metrics based on performance tier."""
        metrics = {
            "realtime": {
                "latency_p95_ms": 50,
                "throughput_ops_per_sec": 1000,
                "availability_percent": 99.99,
                "error_rate_percent": 0.01,
            },
            "batch": {
                "latency_p95_ms": 500,
                "throughput_ops_per_sec": 100,
                "availability_percent": 99.9,
                "error_rate_percent": 0.1,
            },
            "background": {
                "latency_p95_ms": 5000,
                "throughput_ops_per_sec": 10,
                "availability_percent": 99.0,
                "error_rate_percent": 1.0,
            },
        }
        return metrics.get(performance_tier, metrics["batch"])

    def _format_trace_block(self, trace: DoraTraceBlock) -> str:
        """Format DORA Trace Block for Python file (VERY END)."""
        return """
"""

    def _find_insertion_point(self, content: str) -> int:
        """Find the correct insertion point for header (after shebang, encoding, docstring, __future__ imports)."""
        lines = content.split("\n")
        insert_line = 0

        # Skip shebang
        if lines and lines[0].startswith("#!"):
            insert_line = 1

        # Skip encoding declaration
        if len(lines) > insert_line and re.match(r"^#.*coding[:=]", lines[insert_line]):
            insert_line += 1

        # Skip blank lines after shebang/encoding
        while insert_line < len(lines) and lines[insert_line].strip() == "":
            insert_line += 1

        # Skip module docstring if present
        if insert_line < len(lines):
            line = lines[insert_line].strip()
            if line.startswith('"""') or line.startswith("'''"):
                quote = line[:3]
                if line.count(quote) >= 2 and len(line) > 6:
                    # Single-line docstring
                    insert_line += 1
                else:
                    # Multi-line docstring
                    insert_line += 1
                    while insert_line < len(lines) and quote not in lines[insert_line]:
                        insert_line += 1
                    insert_line += 1  # Skip closing quote line

        # Skip blank lines after docstring
        while insert_line < len(lines) and lines[insert_line].strip() == "":
            insert_line += 1

        # CRITICAL: Skip 'from __future__' imports (must be first after docstring)
        # PEP 236: __future__ imports must appear before any other imports
        while insert_line < len(lines):
            line = lines[insert_line].strip()
            if line.startswith("from __future__"):
                insert_line += 1
                # Skip any blank lines after __future__ import
                while insert_line < len(lines) and lines[insert_line].strip() == "":
                    insert_line += 1
            else:
                break

        # Calculate character position
        return sum(len(lines[i]) + 1 for i in range(insert_line))

    def inject_blocks(
        self,
        file_path: str,
        header: HeaderMeta,
        footer: FooterMeta,
        trace: DoraTraceBlock,
        classes: list[ClassInfo],
        dry_run: bool = True,
        force: bool = False,
    ) -> dict[str, bool]:
        """Inject DORA blocks into a Python or YAML file."""
        results = {"header": False, "footer": False, "trace": False}
        is_yaml = file_path.endswith((".yaml", ".yml"))

        try:
            existing = self._check_existing_blocks(file_path)

            # Skip files with legacy blocks (need manual migration)
            if existing["legacy"] and not force:
                print(f"⚠️  {file_path} has legacy __dora_block__ - needs migration")
                return results

            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            modified = False
            new_content = content

            # If force mode, remove existing blocks first
            if force:
                new_content = self._strip_existing_blocks(new_content)
                existing = {
                    "header": False,
                    "footer": False,
                    "trace": False,
                    "legacy": False,
                }

            if is_yaml:
                # YAML file injection
                if not existing["header"]:
                    header_block = self._format_header_meta_yaml(
                        header, file_path, footer.last_modified
                    )
                    # Insert at top of YAML file
                    new_content = header_block + new_content.lstrip()
                    results["header"] = True
                    modified = True

                if not existing["footer"]:
                    footer_block = self._format_footer_meta_yaml(
                        footer, header, file_path
                    )
                    new_content = new_content.rstrip() + footer_block
                    results["footer"] = True
                    modified = True

                # YAML files don't get trace blocks (not executable)
                results["trace"] = True  # Mark as done to avoid warnings

            else:
                # Python file injection
                if not existing["header"]:
                    header_block = self._format_header_meta(
                        header, file_path, footer.last_modified
                    )
                    insert_pos = self._find_insertion_point(new_content)
                    new_content = (
                        new_content[:insert_pos]
                        + header_block
                        + "\n"
                        + new_content[insert_pos:]
                    )
                    results["header"] = True
                    modified = True

                if not existing["footer"]:
                    footer_block = self._format_footer_meta(
                        footer, header, file_path, classes
                    )
                    new_content = new_content.rstrip() + footer_block
                    results["footer"] = True
                    modified = True

                if not existing["trace"]:
                    trace_block = self._format_trace_block(trace)
                    new_content = new_content.rstrip() + trace_block
                    results["trace"] = True
                    modified = True

            if modified:
                if not dry_run:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"✅ Injected DORA blocks into {file_path}")
                else:
                    injected = [k for k, v in results.items() if v]
                    print(f"🔍 [DRY RUN] Would inject {injected} into {file_path}")
            else:
                print(f"⏭️  Skipping {file_path} (all blocks exist)")

            return results

        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return results

    def process_all_files(self, dry_run: bool = True, force: bool = False) -> dict:
        """Process all files and inject DORA blocks."""
        mode_str = "🔍 DRY RUN MODE" if dry_run else "🚀 EXECUTION MODE"
        if force:
            mode_str += " (FORCE)"
        print(f"\n{mode_str}")
        print("=" * 80)

        results = {
            "total_files": len(self.files_to_process),
            "header_injected": 0,
            "footer_injected": 0,
            "trace_injected": 0,
            "skipped": 0,
            "failed": 0,
            "legacy_migration_needed": 0,
            "files": [],
        }

        for file_path, classes in self.files_to_process.items():
            header, footer, trace = self.generate_metadata(file_path, classes)
            injection_results = self.inject_blocks(
                file_path, header, footer, trace, classes, dry_run, force
            )

            if injection_results["header"]:
                results["header_injected"] += 1
            if injection_results["footer"]:
                results["footer_injected"] += 1
            if injection_results["trace"]:
                results["trace_injected"] += 1

            if not any(injection_results.values()):
                existing = self._check_existing_blocks(file_path)
                if existing["legacy"]:
                    results["legacy_migration_needed"] += 1
                else:
                    results["skipped"] += 1

            results["files"].append(
                {
                    "file": file_path,
                    "component_id": header.component_id,
                    "injected": injection_results,
                    "classes": [c.name for c in classes],
                }
            )

        return results

    def generate_report(self, results: dict, output_path: str) -> None:
        """Generate injection report."""
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        print("\n📊 INJECTION REPORT")
        print("=" * 80)
        print(f"Total files processed: {results['total_files']}")
        print(f"✅ Header Meta injected: {results['header_injected']}")
        print(f"✅ Footer Meta injected: {results['footer_injected']}")
        print(f"✅ Trace Block injected: {results['trace_injected']}")
        print(f"⏭️  Skipped (all exist): {results['skipped']}")
        print(f"⚠️  Legacy migration needed: {results['legacy_migration_needed']}")
        print(f"\n📄 Full report saved to: {output_path}")


# ============================================================================
# MAIN


def main():
    parser = argparse.ArgumentParser(
        description="Inject contract-compliant DORA blocks into Python files"
    )
    parser.add_argument("--repo", required=True, help="Path to L9 repository")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode")
    parser.add_argument("--execute", action="store_true", help="Execute injection")
    parser.add_argument("--file", help="Process single file only")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-injection (removes existing blocks)",
    )
    parser.add_argument(
        "--report",
        default="dora_complete_injection_report.json",
        help="Output report path",
    )

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("❌ Error: Must specify either --dry-run or --execute")
        sys.exit(1)

    if args.dry_run and args.execute:
        print("❌ Error: Cannot specify both --dry-run and --execute")
        sys.exit(1)

    injector = DoraCompleteInjector(args.repo)
    injector.scan_repository(single_file=args.file, force=args.force)

    if not injector.files_to_process:
        print("❌ No files found to process")
        sys.exit(1)

    results = injector.process_all_files(dry_run=args.dry_run, force=args.force)
    injector.generate_report(results, args.report)

    print("\n✅ DORA complete injection finished!")


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "api-gateway",
        "ast",
        "async",
        "auth",
        "authorization",
        "batch-processing",
        "caching",
        "cli",
        "code-quality",
    ],
    "keywords": [
        "all",
        "block",
        "blocks",
        "complete",
        "dora",
        "files",
        "footer",
        "generate",
    ],
    "business_value": "Provides inject dora complete components including ClassInfo, HeaderMeta, FooterMeta",
    "last_modified": "2026-01-25T14:59:57Z",
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
