#!/usr/bin/env python3
"""
L9 Dead Code Audit - Phase 1: Baseline Static Analysis
=======================================================

Detects unused code using:
- Vulture (--min-confidence=80)
- Ruff (F401, F841, ARG rules)
- Custom AST for dataclass/config fields
- Parallel scanning for performance

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Phase 1: Baseline Static Analysis",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-13T18:30:12Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "find_dead_code",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Perplexity API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import ast
import json
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

REPO_ROOT = Path(__file__).parent.parent.parent
EXCLUDE_DIRS = {
    "tests",
    "_archived",
    "__pycache__",
    ".venv",
    "venv",
    ".git",
    "node_modules",
    "docs",  # Non-Python files with .py extension
    "codegen",  # Generated specs, not production code
    "igor",  # Audit tools, not production code
    "Perplexity-Search-Pack",  # External package
    "current_work",  # Work-in-progress files
}
EXCLUDE_FILES = {"conftest.py"}  # Test fixtures
MIN_VULTURE_CONFIDENCE = 80

# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class DeadCodeFinding:
    """A single dead code finding."""

    file: str
    line: int
    symbol: str
    symbol_type: str  # import, variable, function, method, class, dataclass_field, class_attribute
    confidence: float
    source: str  # vulture, ruff, ast_dataclass
    message: str
    context: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert finding to dictionary."""
        return asdict(self)


@dataclass
class DataclassFieldInfo:
    """Information about a dataclass field."""

    class_name: str
    field_name: str
    file: str
    line: int
    has_default: bool
    type_annotation: str


@dataclass
class AuditResult:
    """Result of the dead code audit."""

    total_files_scanned: int
    findings: list[DeadCodeFinding] = field(default_factory=list)
    dataclass_fields: list[DataclassFieldInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert audit result to dictionary."""
        return {
            "total_files_scanned": self.total_files_scanned,
            "total_findings": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
            "dataclass_fields_analyzed": len(self.dataclass_fields),
            "errors": self.errors,
        }


# =============================================================================
# VULTURE SCANNER
# =============================================================================


def run_vulture(
    files: list[Path], min_confidence: int = MIN_VULTURE_CONFIDENCE
) -> list[DeadCodeFinding]:
    """Run vulture on files and parse results."""
    findings = []

    # Use python -m vulture to avoid PATH issues
    try:
        result = subprocess.run(  # noqa: S603 — trusted cmd, no shell
            [sys.executable, "-m", "vulture", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning("Vulture not installed. Install with: pip install vulture")
            return findings
    except Exception:
        logger.warning("Vulture not installed. Install with: pip install vulture")
        return findings

    # Run vulture with min-confidence
    file_paths = [str(f) for f in files]

    try:
        result = subprocess.run(  # noqa: S603 — trusted cmd, no shell
            [
                sys.executable,
                "-m",
                "vulture",
                "--min-confidence",
                str(min_confidence),
                *file_paths,
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

        # Parse vulture output: file.py:10: unused function 'foo' (60% confidence)
        pattern = re.compile(r"(.+):(\d+): (.+) \((\d+)% confidence\)")

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            match = pattern.match(line)
            if match:
                filepath, line_num, message, confidence = match.groups()

                # Parse symbol type and name from message
                symbol_type, symbol = _parse_vulture_message(message)

                findings.append(
                    DeadCodeFinding(
                        file=filepath,
                        line=int(line_num),
                        symbol=symbol,
                        symbol_type=symbol_type,
                        confidence=int(confidence) / 100.0,
                        source="vulture",
                        message=message,
                    )
                )

    except Exception as e:
        logger.error(f"Vulture scan failed: {e}")

    return findings


def _parse_vulture_message(message: str) -> tuple[str, str]:
    """Parse vulture message to extract symbol type and name."""
    patterns = [
        (r"unused function '(.+)'", "function"),
        (r"unused method '(.+)'", "method"),
        (r"unused class '(.+)'", "class"),
        (r"unused variable '(.+)'", "variable"),
        (r"unused import '(.+)'", "import"),
        (r"unused attribute '(.+)'", "class_attribute"),
        (r"unreachable code after '(.+)'", "dead_branch"),
    ]

    for pattern, symbol_type in patterns:
        match = re.search(pattern, message)
        if match:
            return symbol_type, match.group(1)

    return "unknown", message


# =============================================================================
# RUFF SCANNER
# =============================================================================


def run_ruff(files: list[Path]) -> list[DeadCodeFinding]:
    """Run ruff with unused code rules."""
    findings = []

    # Use python -m ruff to avoid PATH issues
    try:
        result = subprocess.run(  # noqa: S603 — trusted cmd, no shell
            [sys.executable, "-m", "ruff", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning("Ruff not installed. Install with: pip install ruff")
            return findings
    except Exception:
        logger.warning("Ruff not installed. Install with: pip install ruff")
        return findings

    # Run ruff with specific rules for unused code
    # F401: unused import
    # F841: local variable assigned but never used
    # ARG001-ARG005: unused arguments
    file_paths = [str(f) for f in files]

    try:
        result = subprocess.run(  # noqa: S603 — trusted cmd, no shell
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--select=F401,F841,ARG",
                "--output-format=json",
                *file_paths,
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

        if result.stdout:
            ruff_results = json.loads(result.stdout)

            for item in ruff_results:
                symbol_type = _ruff_code_to_type(item.get("code", ""))

                findings.append(
                    DeadCodeFinding(
                        file=item.get("filename", ""),
                        line=item.get("location", {}).get("row", 0),
                        symbol=(
                            item.get("message", "").split("'")[1]
                            if "'" in item.get("message", "")
                            else ""
                        ),
                        symbol_type=symbol_type,
                        confidence=0.98 if symbol_type == "import" else 0.95,
                        source="ruff",
                        message=item.get("message", ""),
                        context=item.get("code", ""),
                    )
                )

    except json.JSONDecodeError:
        logger.warning("Could not parse ruff JSON output")
    except Exception as e:
        logger.error(f"Ruff scan failed: {e}")

    return findings


def _ruff_code_to_type(code: str) -> str:
    """Convert ruff error code to symbol type."""
    if code == "F401":
        return "import"
    if code == "F841":
        return "variable"
    if code.startswith("ARG"):
        return "argument"
    return "unknown"


# =============================================================================
# DATACLASS FIELD ANALYZER (AST-based)
# =============================================================================


class DataclassFieldVisitor(ast.NodeVisitor):
    """Extract dataclass fields from Python AST."""

    def __init__(self, filepath: str) -> None:
        """Initialize dataclass field visitor."""
        self.filepath = filepath
        self.fields: list[DataclassFieldInfo] = []
        self.current_class: str | None = None
        self.in_dataclass = False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition node."""
        # Check if decorated with @dataclass
        is_dataclass = any(
            (isinstance(d, ast.Name) and d.id == "dataclass")
            or (
                isinstance(d, ast.Call)
                and isinstance(d.func, ast.Name)
                and d.func.id == "dataclass"
            )
            or (isinstance(d, ast.Attribute) and d.attr == "dataclass")
            for d in node.decorator_list
        )

        if is_dataclass:
            old_class = self.current_class
            old_in_dataclass = self.in_dataclass
            self.current_class = node.name
            self.in_dataclass = True

            # Extract fields from class body
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(
                    item.target, ast.Name
                ):
                    field_name = item.target.id
                    type_annotation = (
                        ast.unparse(item.annotation) if item.annotation else "Any"
                    )
                    has_default = item.value is not None

                    self.fields.append(
                        DataclassFieldInfo(
                            class_name=node.name,
                            field_name=field_name,
                            file=self.filepath,
                            line=item.lineno,
                            has_default=has_default,
                            type_annotation=type_annotation,
                        )
                    )

            self.generic_visit(node)
            self.current_class = old_class
            self.in_dataclass = old_in_dataclass
        else:
            self.generic_visit(node)


def extract_dataclass_fields(filepath: Path) -> list[DataclassFieldInfo]:
    """Extract all dataclass fields from a file."""
    try:
        source = filepath.read_text()
        tree = ast.parse(source)
        visitor = DataclassFieldVisitor(str(filepath.relative_to(REPO_ROOT)))
        visitor.visit(tree)
        return visitor.fields
    except Exception as e:
        logger.debug(f"Could not parse {filepath}: {e}")
        return []


def find_field_usages(field: DataclassFieldInfo, all_files: list[Path]) -> list[str]:
    """
    Search for usages of a dataclass field across the codebase.

    Patterns to check:
    - self.field_name
    - obj.field_name
    - ['field_name'] / ["field_name"]
    - getattr(..., 'field_name')
    - asdict(...) usage
    - __dict__['field_name']
    """
    patterns = [
        rf"\.{field.field_name}\b",  # Direct attribute access
        rf"\['{field.field_name}'\]",  # Dict-like access single quote
        rf'\["{field.field_name}"\]',  # Dict-like access double quote
        rf"getattr\([^,]+,\s*['\"]?{field.field_name}['\"]?\)",  # getattr
    ]

    usages = []
    combined_pattern = "|".join(patterns)
    regex = re.compile(combined_pattern)

    for filepath in all_files:
        try:
            content = filepath.read_text()
            # Skip the file where the field is defined (within the class definition)
            rel_path = str(filepath.relative_to(REPO_ROOT))

            for i, line in enumerate(content.split("\n"), 1):
                # Skip comments
                if line.strip().startswith("#"):
                    continue

                if regex.search(line):
                    # Skip the definition line itself
                    if rel_path == field.file and i == field.line:
                        continue
                    usages.append(f"{rel_path}:{i}")

        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    return usages


def analyze_dataclass_fields(
    all_fields: list[DataclassFieldInfo], all_files: list[Path]
) -> list[DeadCodeFinding]:
    """Find dataclass fields that are never used."""
    findings = []

    for field_info in all_fields:
        usages = find_field_usages(field_info, all_files)

        if not usages:
            findings.append(
                DeadCodeFinding(
                    file=field_info.file,
                    line=field_info.line,
                    symbol=f"{field_info.class_name}.{field_info.field_name}",
                    symbol_type="dataclass_field",
                    confidence=0.95,
                    source="ast_dataclass",
                    message=f"Dataclass field '{field_info.field_name}' in class '{field_info.class_name}' is never accessed",
                    context=f"type={field_info.type_annotation}, has_default={field_info.has_default}",
                )
            )

    return findings


# =============================================================================
# WIRING INTEGRITY SCANNER (from perplexity audit concept)
# =============================================================================


def find_unwired_routers(repo_root: Path) -> list[DeadCodeFinding]:
    """
    Find FastAPI routers that are defined but not mounted in main.py.

    Detects patterns like:
    - router = APIRouter() in a file
    - But no app.include_router(router) in main.py or equivalent
    """
    findings = []

    # Find all router definitions
    router_files: dict[str, list[tuple[int, str]]] = {}  # file -> [(line, var_name)]
    router_pattern = re.compile(r"^(\w+)\s*=\s*APIRouter\(")

    api_dir = repo_root / "api"
    if not api_dir.exists():
        return findings

    for filepath in api_dir.rglob("*.py"):
        try:
            content = filepath.read_text()
            rel_path = str(filepath.relative_to(repo_root))

            for i, line in enumerate(content.split("\n"), 1):
                match = router_pattern.match(line.strip())
                if match:
                    var_name = match.group(1)
                    if rel_path not in router_files:
                        router_files[rel_path] = []
                    router_files[rel_path].append((i, var_name))
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Check if routers are mounted (search for include_router calls)
    main_files = [
        "main.py",
        "api/main.py",
        "api/__init__.py",
        "app.py",
        "api/server.py",
    ]
    mounted_routers: set[str] = set()

    include_pattern = re.compile(r"include_router\s*\(\s*(\w+)")
    import_pattern = re.compile(r"from\s+([\w.]+)\s+import\s+(\w+)")

    for main_file in main_files:
        main_path = repo_root / main_file
        if main_path.exists():
            try:
                content = main_path.read_text()
                # Find all include_router calls
                for match in include_pattern.finditer(content):
                    mounted_routers.add(match.group(1))
                # Also track imports to resolve names
                for match in import_pattern.finditer(content):
                    mounted_routers.add(match.group(2))
            except Exception as e:
                logger.debug("audit.file_skipped", error=str(e))
                continue

    # Report unmounted routers
    for rel_path, routers in router_files.items():
        for line_num, var_name in routers:
            # Simple heuristic: check if router name appears in mounted set
            if (
                var_name not in mounted_routers
                and f"{var_name}_router" not in mounted_routers
            ):
                findings.append(
                    DeadCodeFinding(
                        file=rel_path,
                        line=line_num,
                        symbol=var_name,
                        symbol_type="unwired_router",
                        confidence=0.75,  # Lower confidence - may be mounted dynamically
                        source="wiring_scan",
                        message=f"Router '{var_name}' defined but may not be mounted in main.py",
                        context="Check app.include_router() calls",
                    )
                )

    return findings


def find_unwired_services(repo_root: Path) -> list[DeadCodeFinding]:
    """
    Find service classes that are defined but never instantiated.

    Looks for classes ending in 'Service', 'Executor', 'Pipeline', 'Handler'
    and checks if they're instantiated anywhere.

    Skips:
    - Protocol classes (typing.Protocol) - used for duck typing, not instantiation
    - Abstract base classes (ABC) - implemented by subclasses
    - Classes whose subclasses ARE instantiated
    """
    findings = []

    # Service class patterns
    service_classes: dict[
        str, tuple[str, int, str]
    ] = {}  # class_name -> (file, line, parent_class)

    # Enhanced pattern to capture parent class
    class_pattern = re.compile(
        r"^class\s+(\w+(?:Service|Executor|Pipeline|Handler|Manager))\s*\(([^)]*)\)"
    )
    class_pattern_no_parent = re.compile(
        r"^class\s+(\w+(?:Service|Executor|Pipeline|Handler|Manager))\s*:"
    )

    python_files = get_python_files(repo_root)

    # Find all service class definitions
    for filepath in python_files:
        try:
            content = filepath.read_text()
            rel_path = str(filepath.relative_to(repo_root))

            for i, line in enumerate(content.split("\n"), 1):
                match = class_pattern.match(line.strip())
                if match:
                    class_name = match.group(1)
                    parent_class = match.group(2).strip()

                    # Skip Protocol classes (typing.Protocol) - they're for type checking only
                    if "Protocol" in parent_class:
                        continue

                    # Skip Abstract Base Classes - they're implemented by subclasses
                    if "ABC" in parent_class or "Abstract" in class_name:
                        continue

                    # Skip Interface classes (I prefix convention)
                    if (
                        class_name.startswith("I")
                        and len(class_name) > 1
                        and class_name[1].isupper()
                    ):
                        continue

                    service_classes[class_name] = (rel_path, i, parent_class)
                else:
                    # Check for class without parentheses
                    match_no_parent = class_pattern_no_parent.match(line.strip())
                    if match_no_parent:
                        class_name = match_no_parent.group(1)
                        service_classes[class_name] = (rel_path, i, "")
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Build inheritance map: parent -> [child classes]
    inheritance_map: dict[str, list[str]] = {}
    for class_name, (_, _, parent) in service_classes.items():
        if parent:
            # Extract first parent class name
            first_parent = parent.split(",")[0].strip().split("(")[0].strip()
            if first_parent not in inheritance_map:
                inheritance_map[first_parent] = []
            inheritance_map[first_parent].append(class_name)

    # Search for instantiations
    for class_name, (def_file, def_line, parent_class) in service_classes.items():
        instantiation_found = False

        # Patterns: ClassName(), ClassName.create(), get_instance(ClassName), app.state.X = ClassName()
        inst_patterns = [
            re.compile(rf"\b{class_name}\s*\("),  # Direct instantiation
            re.compile(rf"\b{class_name}\."),  # Static method call
            re.compile(rf":\s*{class_name}\b"),  # Type hint (dependency injection)
            re.compile(
                rf"app\.state\.\w+\s*=\s*{class_name}"
            ),  # FastAPI lifespan wiring
            re.compile(rf"state\.\w+\s*=\s*{class_name}"),  # Generic state assignment
            re.compile(
                rf",\s*{class_name}\s*\)"
            ),  # Class passed as parameter (e.g., HTTPServer(..., Handler))
            re.compile(rf"\(\s*{class_name}\s*,"),  # Class as first parameter
        ]

        for filepath in python_files:
            if instantiation_found:
                break
            try:
                content = filepath.read_text()
                rel_path = str(filepath.relative_to(repo_root))

                for i, line in enumerate(content.split("\n"), 1):
                    # Skip the definition line itself
                    if rel_path == def_file and i == def_line:
                        continue
                    # Skip import lines
                    if line.strip().startswith(("from ", "import ")):
                        continue

                    for pattern in inst_patterns:
                        if pattern.search(line):
                            instantiation_found = True
                            break
                    if instantiation_found:
                        break
            except Exception as e:
                logger.debug("audit.file_skipped", error=str(e))
                continue

        # If base class not instantiated, check if ANY subclass is instantiated
        if not instantiation_found and class_name in inheritance_map:
            for subclass in inheritance_map[class_name]:
                # Check if subclass is instantiated
                subclass_pattern = re.compile(rf"\b{subclass}\s*\(")
                for filepath in python_files:
                    if instantiation_found:
                        break
                    try:
                        content = filepath.read_text()
                        if subclass_pattern.search(content):
                            instantiation_found = True
                            break
                    except Exception as e:
                        logger.debug("audit.file_skipped", error=str(e))
                        continue

        if not instantiation_found:
            # Lower confidence for classes that have subclasses (may be base class pattern)
            confidence = 0.60 if class_name in inheritance_map else 0.70

            findings.append(
                DeadCodeFinding(
                    file=def_file,
                    line=def_line,
                    symbol=class_name,
                    symbol_type="unwired_service",
                    confidence=confidence,
                    source="wiring_scan",
                    message=f"Service '{class_name}' defined but no instantiation found",
                    context="May be wired via dependency injection or dynamic loading",
                )
            )

    return findings


# =============================================================================
# TIER 1: HIGH PRIORITY WIRING CHECKS
# =============================================================================


def find_unwired_tools(repo_root: Path) -> list[DeadCodeFinding]:
    """
    Find tool definitions not registered in ToolGraph.

    Detects patterns like:
    - TOOL_DEFINITIONS = [...] or L9_TOOLS = [...] defined
    - But tools never registered via ToolGraph.register_tool()
    """
    findings = []

    tools_dir = repo_root / "core" / "tools"
    if not tools_dir.exists():
        return findings

    # Patterns for tool definition arrays
    tool_def_patterns = [
        re.compile(r"^(\w*TOOL_DEFINITIONS\w*)\s*=\s*\["),
        re.compile(r"^(L9_TOOLS|L_TOOLS|L_INTERNAL_TOOLS)\s*=\s*\["),
    ]

    # Find all tool definition arrays
    tool_arrays: dict[str, list[tuple[int, str]]] = {}  # file -> [(line, var_name)]

    for filepath in tools_dir.rglob("*.py"):
        try:
            content = filepath.read_text()
            rel_path = str(filepath.relative_to(repo_root))

            for i, line in enumerate(content.split("\n"), 1):
                for pattern in tool_def_patterns:
                    match = pattern.match(line.strip())
                    if match:
                        var_name = match.group(1)
                        if rel_path not in tool_arrays:
                            tool_arrays[rel_path] = []
                        tool_arrays[rel_path].append((i, var_name))
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Check if tools are registered (search for register_tool calls referencing these arrays)
    [
        re.compile(r"register_tool\s*\("),
        re.compile(r"for\s+tool\s+in\s+(\w+)"),
        re.compile(r"ToolGraph\.register_tool"),
    ]

    registered_arrays: set[str] = set()

    python_files = get_python_files(repo_root)
    for filepath in python_files:
        try:
            content = filepath.read_text()

            # Check if any tool array is iterated over for registration
            for var_name in [v for arrs in tool_arrays.values() for _, v in arrs]:
                if re.search(rf"for\s+\w+\s+in\s+{var_name}", content):
                    registered_arrays.add(var_name)
                if re.search(rf"register.*{var_name}", content, re.IGNORECASE):
                    registered_arrays.add(var_name)
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Report unregistered tool arrays
    for rel_path, tools in tool_arrays.items():
        for line_num, var_name in tools:
            if var_name not in registered_arrays:
                # Check if marked as LEGITIMATE in source
                filepath = repo_root / rel_path
                is_legitimate = False
                try:
                    content = filepath.read_text()
                    lines = content.split("\n")
                    # Check surrounding lines for LEGITIMATE comment
                    start = max(0, line_num - 5)
                    end = min(len(lines), line_num + 1)
                    for line in lines[start:end]:
                        if "LEGITIMATE:" in line:
                            is_legitimate = True
                            break
                except Exception:
                    logger.debug("find_dead_code.legitimate_check_failed")

                if not is_legitimate:
                    findings.append(
                        DeadCodeFinding(
                            file=rel_path,
                            line=line_num,
                            symbol=var_name,
                            symbol_type="unwired_tool",
                            confidence=0.85,
                            source="wiring_scan",
                            message=f"Tool array '{var_name}' defined but may not be registered",
                            context="Check for ToolGraph.register_tool() or register_*_tools() calls",
                        )
                    )

    return findings


def find_unwired_pydantic_models(repo_root: Path) -> list[DeadCodeFinding]:
    """
    Find Pydantic models (BaseModel subclasses) never used in route signatures.

    Detects Request/Response models defined but never:
    - Used as route parameter type hints
    - Used in response_model= decorator arguments
    """
    findings = []

    # Directories to scan for model definitions
    model_dirs = [
        repo_root / "api",
        repo_root / "core" / "schemas",
    ]

    # Pattern for Pydantic model definitions
    model_pattern = re.compile(
        r"^class\s+(\w+(?:Request|Response|Model|Schema|Payload|Input|Output))\s*\(\s*(?:BaseModel|Base\w*Model)"
    )

    # Find all Pydantic model definitions
    pydantic_models: dict[str, tuple[str, int]] = {}  # model_name -> (file, line)

    for model_dir in model_dirs:
        if not model_dir.exists():
            continue
        for filepath in model_dir.rglob("*.py"):
            try:
                content = filepath.read_text()
                rel_path = str(filepath.relative_to(repo_root))

                for i, line in enumerate(content.split("\n"), 1):
                    match = model_pattern.match(line.strip())
                    if match:
                        model_name = match.group(1)
                        pydantic_models[model_name] = (rel_path, i)
            except Exception as e:
                logger.debug("audit.file_skipped", error=str(e))
                continue

    # Search for usages in route definitions and type hints
    python_files = get_python_files(repo_root)

    for model_name, (def_file, def_line) in list(pydantic_models.items()):
        usage_found = False

        # Patterns for model usage (routes, tools, internal)
        usage_patterns = [
            re.compile(rf":\s*{model_name}\b"),  # Type hint
            re.compile(rf"response_model\s*=\s*{model_name}"),  # Response model
            re.compile(rf"List\[{model_name}\]"),  # List type hint
            re.compile(rf"Optional\[{model_name}\]"),  # Optional type hint
            re.compile(rf"\b{model_name}\s*\("),  # Instantiation
            re.compile(rf"->\s*{model_name}\b"),  # Return type hint
            re.compile(rf'"{model_name}"'),  # String reference (tool defs)
            re.compile(rf"'{model_name}'"),  # String reference (tool defs)
            re.compile(rf"Union\[.*{model_name}"),  # Union type hint
            re.compile(rf"dict\[.*{model_name}"),  # Dict type hint
        ]

        for filepath in python_files:
            if usage_found:
                break
            try:
                content = filepath.read_text()
                rel_path = str(filepath.relative_to(repo_root))

                for i, line in enumerate(content.split("\n"), 1):
                    # Skip the definition line
                    if rel_path == def_file and i == def_line:
                        continue
                    # Skip import lines
                    if line.strip().startswith(("from ", "import ")):
                        continue

                    for pattern in usage_patterns:
                        if pattern.search(line):
                            usage_found = True
                            break
                    if usage_found:
                        break
            except Exception as e:
                logger.debug("audit.file_skipped", error=str(e))
                continue

        if not usage_found:
            # Lower confidence for Input/Output models in schemas (often used by tools)
            confidence = (
                0.60 if "Input" in model_name or "Output" in model_name else 0.80
            )
            # Lower confidence for models in l_tools.py (internal tool schemas)
            if "l_tools.py" in def_file:
                confidence = 0.50
            findings.append(
                DeadCodeFinding(
                    file=def_file,
                    line=def_line,
                    symbol=model_name,
                    symbol_type="unwired_pydantic",
                    confidence=confidence,
                    source="wiring_scan",
                    message=f"Pydantic model '{model_name}' defined but never used in routes",
                    context="Check route parameter types and response_model= arguments (may be internal tool schema)",
                )
            )

    return findings


def find_unwired_dependencies(repo_root: Path) -> list[DeadCodeFinding]:
    """
    Find FastAPI dependency functions never injected via Depends().

    Detects functions in dependencies.py that are never used with Depends().
    """
    findings = []

    # Find dependency provider files
    dep_files = [
        repo_root / "api" / "dependencies.py",
        repo_root / "api" / "deps.py",
    ]

    # Pattern for dependency function definitions
    dep_func_pattern = re.compile(
        r"^(?:async\s+)?def\s+(get_\w+|require_\w+|verify_\w+)\s*\("
    )

    # Find all dependency functions
    dep_functions: dict[str, tuple[str, int]] = {}  # func_name -> (file, line)

    for dep_file in dep_files:
        if not dep_file.exists():
            continue
        try:
            content = dep_file.read_text()
            rel_path = str(dep_file.relative_to(repo_root))

            for i, line in enumerate(content.split("\n"), 1):
                match = dep_func_pattern.match(line.strip())
                if match:
                    func_name = match.group(1)
                    dep_functions[func_name] = (rel_path, i)
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Search for Depends() usage
    depends_pattern = re.compile(r"Depends\s*\(\s*(\w+)")
    used_deps: set[str] = set()

    python_files = get_python_files(repo_root)
    for filepath in python_files:
        try:
            content = filepath.read_text()
            for match in depends_pattern.finditer(content):
                used_deps.add(match.group(1))
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Report unused dependency functions
    for func_name, (def_file, def_line) in dep_functions.items():
        if func_name not in used_deps:
            # Very low confidence for dependencies - they're scaffolding for future routes
            findings.append(
                DeadCodeFinding(
                    file=def_file,
                    line=def_line,
                    symbol=func_name,
                    symbol_type="unwired_dependency",
                    confidence=0.40,  # Very low: known scaffolding pattern in dependencies.py
                    source="wiring_scan",
                    message=f"Dependency '{func_name}' defined but never used with Depends()",
                    context="LIKELY SCAFFOLDING: Future route integration (dependencies.py pattern)",
                )
            )

    return findings


def find_unwired_app_state(repo_root: Path) -> list[DeadCodeFinding]:
    """
    Find app.state.X assignments that are never accessed elsewhere.

    Detects patterns like:
        app.state.consolidation = Consolidation(...)
    where app.state.consolidation is assigned but never accessed outside the assignment file.
    """
    findings = []

    # Primary files where app.state is typically assigned
    state_assignment_files = [
        repo_root / "api" / "server.py",
        repo_root / "api" / "main.py",
        repo_root / "main.py",
    ]

    # Pattern for app.state.X = ... assignments
    assignment_pattern = re.compile(r"app\.state\.(\w+)\s*=")

    # Find all app.state assignments
    state_vars: dict[str, tuple[str, int]] = {}  # var_name -> (file, line)

    for state_file in state_assignment_files:
        if not state_file.exists():
            continue
        try:
            content = state_file.read_text()
            rel_path = str(state_file.relative_to(repo_root))

            for i, line in enumerate(content.split("\n"), 1):
                # Skip comments
                if line.strip().startswith("#"):
                    continue

                match = assignment_pattern.search(line)
                if match:
                    var_name = match.group(1)

                    # Skip internal state (underscore prefix = Python private convention)
                    if var_name.startswith("_"):
                        continue

                    # Skip feature flags and status indicators (read via settings, not direct access)
                    if var_name.endswith(
                        ("_enabled", "_initialized", "_ready", "_error", "_loaded")
                    ):
                        continue

                    state_vars[var_name] = (rel_path, i)
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Search for usages of each app.state variable across the codebase
    python_files = get_python_files(repo_root)

    # Pre-scan for module-level globals and singleton getters to detect false positives
    # Pattern 1: Module-level global (e.g., "gmp_learning_engine = None" at module level)
    module_globals: set[str] = set()
    # Pattern 2: Singleton getter function (e.g., "def get_housekeeping_engine()")
    singleton_getters: set[str] = set()

    for state_file in state_assignment_files:
        if not state_file.exists():
            continue
        try:
            content = state_file.read_text()
            # Find module-level globals: "var_name = None" at start of line (no indent)
            for line in content.split("\n"):
                # Module-level: starts at column 0, not inside function/class
                if line and not line[0].isspace():
                    global_match = re.match(r"^(\w+)\s*=\s*None", line)
                    if global_match:
                        module_globals.add(global_match.group(1))
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Search for singleton getter functions like get_housekeeping_engine()
    for filepath in python_files:
        try:
            content = filepath.read_text()
            # Find function definitions like "def get_X():" or "def get_X_service():"
            for match in re.finditer(r"def\s+get_(\w+)\s*\(", content):
                getter_name = match.group(1)
                # Normalize: get_housekeeping_engine -> housekeeping_engine
                singleton_getters.add(getter_name)
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    for var_name, (def_file, def_line) in list(state_vars.items()):
        usage_found = False

        # FALSE POSITIVE CHECK 1: Module-level global with same name
        # If var_name exists as a module-level global, it's accessed via import, not app.state
        if var_name in module_globals:
            continue  # Skip - accessed via "from api.server import var_name"

        # FALSE POSITIVE CHECK 2: Singleton getter function exists
        # If get_var_name() exists, the service is accessed via the getter, not app.state
        if var_name in singleton_getters:
            continue  # Skip - accessed via get_var_name() singleton

        # Pattern to find app.state.X access (not assignment)
        access_pattern = re.compile(rf"app\.state\.{var_name}(?!\s*=)")
        # Also check for request.app.state.X (FastAPI dependency injection pattern)
        request_pattern = re.compile(rf"request\.app\.state\.{var_name}")
        # Also check for getattr(request.app.state, "var_name", ...) pattern (common in FastAPI)
        getattr_pattern = re.compile(
            rf'getattr\s*\([^,]*app\.state\s*,\s*["\']?{var_name}["\']?'
        )

        for filepath in python_files:
            if usage_found:
                break
            try:
                content = filepath.read_text()
                rel_path = str(filepath.relative_to(repo_root))

                for i, line in enumerate(content.split("\n"), 1):
                    # Skip the definition line itself
                    if rel_path == def_file and i == def_line:
                        continue
                    # Skip comments
                    if line.strip().startswith("#"):
                        continue

                    if (
                        access_pattern.search(line)
                        or request_pattern.search(line)
                        or getattr_pattern.search(line)
                    ):
                        usage_found = True
                        break
            except Exception as e:
                logger.debug("audit.file_skipped", error=str(e))
                continue

        if not usage_found:
            findings.append(
                DeadCodeFinding(
                    file=def_file,
                    line=def_line,
                    symbol=f"app.state.{var_name}",
                    symbol_type="unwired_app_state",
                    confidence=0.80,
                    source="wiring_scan",
                    message=f"app.state.{var_name} assigned but never accessed elsewhere",
                    context="Check for app.state.X or request.app.state.X usage in routes/dependencies",
                )
            )

    return findings


def find_export_discrepancies(repo_root: Path) -> list[DeadCodeFinding]:
    """
    Find modules where __all__ exports aren't re-exported in parent __init__.py.

    Detects:
    - Module has symbol in __all__, but parent __init__.py doesn't re-export it
    - Symbol exported but never consumed anywhere in codebase (orphan export)

    This catches wiring issues like:
        runtime/redis_client.py: __all__ = ["RedisClient", "get_cursor_wmc", ...]
        runtime/__init__.py: only re-exports ["RedisClient", ...] (missing get_cursor_wmc)
    """
    findings = []

    # Directories to scan for export discrepancies
    scan_dirs = [
        "api",
        "core",
        "runtime",
        "memory",
        "orchestrators",
        "services",
        "agents",
        "tools",
        "workers",
        "workflows",
    ]

    python_files = get_python_files(repo_root)

    # Build full content for usage checking
    all_content = ""
    for filepath in python_files:
        try:
            all_content += filepath.read_text(encoding="utf-8", errors="ignore") + "\n"
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    for scan_dir in scan_dirs:
        dir_path = repo_root / scan_dir
        if not dir_path.exists():
            continue

        # Find all Python modules (not __init__.py)
        for module_path in dir_path.rglob("*.py"):
            if module_path.name == "__init__.py":
                continue
            if "__pycache__" in str(module_path):
                continue

            try:
                module_content = module_path.read_text(
                    encoding="utf-8", errors="ignore"
                )
            except Exception as e:
                logger.debug("audit.file_skipped", error=str(e))
                continue

            # Extract __all__ from module
            module_all = _extract_all_list(module_content)
            if not module_all:
                continue

            # Find parent __init__.py
            init_path = module_path.parent / "__init__.py"
            if not init_path.exists():
                continue

            try:
                init_content = init_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                logger.debug("audit.file_skipped", error=str(e))
                continue

            # Extract __all__ from __init__.py
            init_all = _extract_all_list(init_content)

            # Also check for direct imports in __init__.py
            # Pattern: from .module import X or from .module import X, Y, Z
            module_name = module_path.stem
            import_pattern = re.compile(
                rf"from\s+\.{re.escape(module_name)}\s+import\s+([^#\n]+)"
            )
            imported_symbols: set[str] = set()
            for match in import_pattern.finditer(init_content):
                imports_str = match.group(1)
                # Handle parenthesized imports
                imports_str = imports_str.replace("(", "").replace(")", "")
                for sym in imports_str.split(","):
                    sym = sym.strip()
                    if " as " in sym:
                        sym = sym.split(" as ")[0].strip()
                    if sym:
                        imported_symbols.add(sym)

            # Combine init_all and imported_symbols for "what's re-exported"
            reexported = set(init_all) | imported_symbols

            rel_module_path = str(module_path.relative_to(repo_root))
            rel_init_path = str(init_path.relative_to(repo_root))

            # Find line number of __all__ in module
            all_line = 1
            for i, line in enumerate(module_content.split("\n"), 1):
                if "__all__" in line and "=" in line:
                    all_line = i
                    break

            # Check each exported symbol
            for symbol in module_all:
                # Issue 1: Not re-exported in __init__.py
                if symbol not in reexported:
                    findings.append(
                        DeadCodeFinding(
                            file=rel_module_path,
                            line=all_line,
                            symbol=symbol,
                            symbol_type="export_not_reexported",
                            confidence=0.85,
                            source="wiring_scan",
                            message=f"'{symbol}' in {module_path.name}.__all__ but not re-exported in {rel_init_path}",
                            context=f"Add to {rel_init_path} __all__ or import from .{module_name}",
                        )
                    )

                # Issue 2: Orphan export (defined but never consumed)
                # Count occurrences (subtract 1 for definition, 1 for __all__ entry)
                usage_pattern = rf"\b{re.escape(symbol)}\b"
                usage_count = len(re.findall(usage_pattern, all_content))

                # Symbol appears in: definition, __all__, possibly __init__.py import
                # If only 2-3 occurrences, likely not actually used
                if usage_count <= 3:
                    # Verify it's actually unused by checking for call/instantiation patterns
                    call_pattern = rf"\b{re.escape(symbol)}\s*\("
                    type_hint_pattern = rf":\s*{re.escape(symbol)}\b"
                    inherit_pattern = rf"\({re.escape(symbol)}\)"

                    has_call = bool(re.search(call_pattern, all_content))
                    has_type_hint = bool(re.search(type_hint_pattern, all_content))
                    has_inherit = bool(re.search(inherit_pattern, all_content))

                    if not (has_call or has_type_hint or has_inherit):
                        findings.append(
                            DeadCodeFinding(
                                file=rel_module_path,
                                line=all_line,
                                symbol=symbol,
                                symbol_type="orphan_export",
                                confidence=0.75,
                                source="wiring_scan",
                                message=f"'{symbol}' exported in __all__ but never consumed in codebase",
                                context=f"Consider removing from {module_path.name}.__all__ or implementing usage",
                            )
                        )

    return findings


def _extract_all_list(content: str) -> list[str]:
    """
    Extract __all__ list from Python source code.

    Handles:
    - __all__ = ["a", "b", "c"]
    - __all__ = [
          "a",
          "b",
      ]
    - __all__: list[str] = [...]
    """
    # Try AST parsing first (most reliable)
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, ast.List):
                            return [
                                elt.value
                                for elt in node.value.elts
                                if isinstance(elt, ast.Constant)
                                and isinstance(elt.value, str)
                            ]
            # Handle annotated assignment: __all__: list[str] = [...]
            if isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.target.id == "__all__":
                    if node.value and isinstance(node.value, ast.List):
                        return [
                            elt.value
                            for elt in node.value.elts
                            if isinstance(elt, ast.Constant)
                            and isinstance(elt.value, str)
                        ]
    except SyntaxError:
        pass

    # Fallback to regex for files with syntax errors
    pattern = re.compile(r"__all__\s*(?::\s*[^=]+)?\s*=\s*\[(.*?)\]", re.DOTALL)
    match = pattern.search(content)
    if match:
        items_str = match.group(1)
        # Extract quoted strings
        return re.findall(r'["\']([^"\']+)["\']', items_str)

    return []


# =============================================================================
# TIER 2: MEDIUM PRIORITY WIRING CHECKS (L9-specific)
# =============================================================================


def find_unwired_kernels(repo_root: Path) -> list[DeadCodeFinding]:
    """
    Find YAML kernel files not listed in KERNEL_ORDER.

    Detects kernel YAML files that exist but aren't in the load sequence.
    """
    findings = []

    # Kernel directories
    kernel_dirs = [
        repo_root / "private" / "kernels",
        repo_root / "config" / "kernels",
    ]

    # Find all kernel YAML files
    kernel_files: set[str] = set()
    for kernel_dir in kernel_dirs:
        if not kernel_dir.exists():
            continue
        for filepath in kernel_dir.rglob("*.yaml"):
            # Skip archived kernels (intentionally not in KERNEL_ORDER)
            if "_archived" in str(filepath):
                continue
            # Skip bootstrap directory (manifest loaded separately)
            if "bootstrap" in str(filepath):
                continue
            rel_path = str(filepath.relative_to(repo_root))
            kernel_files.add(rel_path)
        for filepath in kernel_dir.rglob("*.yml"):
            if "_archived" in str(filepath):
                continue
            if "bootstrap" in str(filepath):
                continue
            rel_path = str(filepath.relative_to(repo_root))
            kernel_files.add(rel_path)

    # Read KERNEL_ORDER from kernelloader.py
    kernelloader_path = repo_root / "core" / "kernels" / "kernelloader.py"
    registered_kernels: set[str] = set()

    if kernelloader_path.exists():
        try:
            content = kernelloader_path.read_text()
            # Extract KERNEL_ORDER list
            kernel_order_match = re.search(
                r"KERNEL_ORDER\s*=\s*\[(.*?)\]", content, re.DOTALL
            )
            if kernel_order_match:
                order_content = kernel_order_match.group(1)
                # Extract quoted strings
                for match in re.finditer(r'["\']([^"\']+\.ya?ml)["\']', order_content):
                    registered_kernels.add(match.group(1))
        except Exception:
            logger.debug("find_dead_code.kernel_order_parse_failed")

    # Report unregistered kernel files
    for kernel_file in kernel_files:
        # Check if this kernel is in the registered set
        is_registered = any(
            kernel_file.endswith(reg) or reg in kernel_file
            for reg in registered_kernels
        )

        if not is_registered:
            # Get line number (first line of file)
            findings.append(
                DeadCodeFinding(
                    file=kernel_file,
                    line=1,
                    symbol=Path(kernel_file).stem,
                    symbol_type="unwired_kernel",
                    confidence=0.95,
                    source="wiring_scan",
                    message=f"Kernel '{kernel_file}' not in KERNEL_ORDER",
                    context="Add to KERNEL_ORDER in core/kernels/kernelloader.py",
                )
            )

    return findings


def find_unwired_agents(repo_root: Path) -> list[DeadCodeFinding]:
    """
    Find agent YAML configs never referenced by AgentRegistry.
    """
    findings = []

    # Agent config directories
    agent_dirs = [
        repo_root / "config" / "agents",
        repo_root / "agents",
    ]

    # Find all agent config files
    agent_configs: set[str] = set()
    for agent_dir in agent_dirs:
        if not agent_dir.exists():
            continue
        for filepath in agent_dir.rglob("*.yaml"):
            # Skip generated spec directories (false positives)
            if "codegen+codegenAgent_specs" in str(filepath):
                continue
            if "codegenagent" in str(filepath).lower():
                continue
            agent_configs.add(filepath.stem)  # e.g., "research-agent-v1"
        for filepath in agent_dir.rglob("*.yml"):
            if "codegen+codegenAgent_specs" in str(filepath):
                continue
            if "codegenagent" in str(filepath).lower():
                continue
            agent_configs.add(filepath.stem)

    # Search for agent references in codebase
    referenced_agents: set[str] = set()
    python_files = get_python_files(repo_root)

    for filepath in python_files:
        try:
            content = filepath.read_text()
            for agent_name in agent_configs:
                # Check for string references
                if f'"{agent_name}"' in content or f"'{agent_name}'" in content:
                    referenced_agents.add(agent_name)
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Report unreferenced agent configs
    for agent_dir in agent_dirs:
        if not agent_dir.exists():
            continue
        for filepath in agent_dir.rglob("*.yaml"):
            # Skip generated spec directories (false positives)
            if "codegen+codegenAgent_specs" in str(filepath):
                continue
            if "codegenagent" in str(filepath).lower():
                continue
            agent_name = filepath.stem
            if agent_name not in referenced_agents:
                rel_path = str(filepath.relative_to(repo_root))
                findings.append(
                    DeadCodeFinding(
                        file=rel_path,
                        line=1,
                        symbol=agent_name,
                        symbol_type="unwired_agent",
                        confidence=0.70,
                        source="wiring_scan",
                        message=f"Agent config '{agent_name}' never referenced",
                        context="May be loaded dynamically or via environment config",
                    )
                )

    return findings


def find_unwired_orchestrators(repo_root: Path) -> list[DeadCodeFinding]:
    """
    Find orchestrator interface classes never instantiated.
    """
    findings = []

    orchestrators_dir = repo_root / "orchestrators"
    if not orchestrators_dir.exists():
        return findings

    # Pattern for orchestrator class definitions
    orch_pattern = re.compile(
        r"^class\s+(\w+(?:Orchestrator|Interface|Controller))\s*[:\(]"
    )

    # Find all orchestrator classes
    orch_classes: dict[str, tuple[str, int]] = {}

    for filepath in orchestrators_dir.rglob("*.py"):
        try:
            content = filepath.read_text()
            rel_path = str(filepath.relative_to(repo_root))

            for i, line in enumerate(content.split("\n"), 1):
                match = orch_pattern.match(line.strip())
                if match:
                    class_name = match.group(1)
                    # Skip interface classes (I prefix followed by uppercase letter)
                    # e.g., IActionToolOrchestrator, IMemoryOrchestrator are abstract
                    if (
                        len(class_name) > 1
                        and class_name[0] == "I"
                        and class_name[1].isupper()
                    ):
                        continue
                    orch_classes[class_name] = (rel_path, i)
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Search for instantiations
    python_files = get_python_files(repo_root)

    for class_name, (def_file, def_line) in list(orch_classes.items()):
        instantiation_found = False

        for filepath in python_files:
            if instantiation_found:
                break
            try:
                content = filepath.read_text()
                rel_path = str(filepath.relative_to(repo_root))

                for i, line in enumerate(content.split("\n"), 1):
                    if rel_path == def_file and i == def_line:
                        continue
                    if line.strip().startswith(("from ", "import ")):
                        continue

                    # Check for instantiation or type hint usage
                    if re.search(rf"\b{class_name}\s*\(", line) or re.search(
                        rf":\s*{class_name}\b", line
                    ):
                        instantiation_found = True
                        break
            except Exception as e:
                logger.debug("audit.file_skipped", error=str(e))
                continue

        if not instantiation_found:
            findings.append(
                DeadCodeFinding(
                    file=def_file,
                    line=def_line,
                    symbol=class_name,
                    symbol_type="unwired_orchestrator",
                    confidence=0.70,
                    source="wiring_scan",
                    message=f"Orchestrator '{class_name}' defined but never instantiated",
                    context="May be wired via factory or dependency injection",
                )
            )

    return findings


# =============================================================================
# TIER 3: LOWER PRIORITY WIRING CHECKS
# =============================================================================


def find_unwired_event_handlers(repo_root: Path) -> list[DeadCodeFinding]:
    """
    Find startup/shutdown event handlers that may be orphaned.

    Note: Only flags functions explicitly named as event handlers (on_startup, on_shutdown)
    and not used. Functions with startup_/shutdown_ prefix that are routes or called
    directly in lifespan are not flagged.
    """
    findings = []

    # More restrictive pattern - only explicit event handler naming
    # Excludes: startup_health (likely a route), shutdown_runtime (called directly)
    handler_patterns = [
        (re.compile(r"^async\s+def\s+(on_startup|on_shutdown)\s*\("), "startup"),
        (re.compile(r"^def\s+(on_startup|on_shutdown)\s*\("), "shutdown"),
    ]

    # Find all event handler functions
    handlers: dict[
        str, tuple[str, int, str, str]
    ] = {}  # func_name -> (file, line, event_type, content)

    python_files = get_python_files(repo_root)
    for filepath in python_files:
        try:
            content = filepath.read_text()
            rel_path = str(filepath.relative_to(repo_root))
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                for pattern, event_type in handler_patterns:
                    match = pattern.match(line.strip())
                    if match:
                        func_name = match.group(1)
                        # Check if previous line has a route decorator - skip if so
                        if i > 1:
                            prev_line = lines[i - 2].strip()
                            if prev_line.startswith("@") and (
                                ".get" in prev_line
                                or ".post" in prev_line
                                or ".route" in prev_line
                            ):
                                continue  # It's a route handler, not an event handler
                        handlers[func_name] = (rel_path, i, event_type, content)
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Search for on_event registrations AND direct calls
    registered_or_called: set[str] = set()
    event_pattern = re.compile(
        r'on_event\s*\(\s*["\'](?:startup|shutdown)["\']\s*\)\s*\(\s*(\w+)'
    )
    decorator_pattern = re.compile(
        r'@\w+\.on_event\s*\(\s*["\'](?:startup|shutdown)["\']\s*\)'
    )

    for filepath in python_files:
        try:
            content = filepath.read_text()
            lines = content.split("\n")

            for match in event_pattern.finditer(content):
                registered_or_called.add(match.group(1))

            # Check for decorated functions
            for i, line in enumerate(lines):
                if decorator_pattern.search(line):
                    # Next non-empty line should be the function
                    for j in range(i + 1, min(i + 5, len(lines))):
                        func_match = re.match(
                            r"(?:async\s+)?def\s+(\w+)", lines[j].strip()
                        )
                        if func_match:
                            registered_or_called.add(func_match.group(1))
                            break

            # Also check for direct calls (await func_name() or func_name())
            for func_name in handlers:
                if re.search(rf"\bawait\s+{func_name}\s*\(", content):
                    registered_or_called.add(func_name)
                # Check for direct calls (excluding the definition)
                call_matches = list(re.finditer(rf"\b{func_name}\s*\(", content))
                if len(call_matches) > 1:  # More than just definition
                    registered_or_called.add(func_name)
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Report unregistered handlers
    for func_name, (def_file, def_line, event_type, _) in handlers.items():
        if func_name not in registered_or_called:
            findings.append(
                DeadCodeFinding(
                    file=def_file,
                    line=def_line,
                    symbol=func_name,
                    symbol_type="unwired_event",
                    confidence=0.65,
                    source="wiring_scan",
                    message=f"Event handler '{func_name}' ({event_type}) may not be registered",
                    context=f"Check for @app.on_event('{event_type}') decorator or direct call in lifespan",
                )
            )

    return findings


def find_unwired_background_tasks(repo_root: Path) -> list[DeadCodeFinding]:
    """
    Find async functions designed for BackgroundTasks never scheduled.

    Note: Only flags functions that appear to be explicitly designed as background
    tasks (run_X_in_background, process_X_background, bg_X patterns), not general
    async functions that happen to have _task/_async in their name.
    """
    findings = []

    # More restrictive pattern - only explicit background task naming
    # Excludes: get_async (getter), submit_task (route), close_async (cleanup)
    bg_pattern = re.compile(
        r"^async\s+def\s+"
        r"(run_\w+_in_background|"  # run_X_in_background
        r"process_\w+_background|"  # process_X_background
        r"bg_\w+|"  # bg_X
        r"\w+_background_task)"  # X_background_task
        r"\s*\("
    )

    # Find candidate background task functions
    bg_funcs: dict[str, tuple[str, int]] = {}

    python_files = get_python_files(repo_root)
    for filepath in python_files:
        try:
            content = filepath.read_text()
            rel_path = str(filepath.relative_to(repo_root))

            for i, line in enumerate(content.split("\n"), 1):
                match = bg_pattern.match(line.strip())
                if match:
                    func_name = match.group(1)
                    bg_funcs[func_name] = (rel_path, i)
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Search for add_task calls AND regular function calls
    scheduled_or_called: set[str] = set()
    add_task_pattern = re.compile(r"add_task\s*\(\s*(\w+)")
    create_task_pattern = re.compile(r"create_task\s*\(\s*(\w+)")

    for filepath in python_files:
        try:
            content = filepath.read_text()
            for match in add_task_pattern.finditer(content):
                scheduled_or_called.add(match.group(1))
            for match in create_task_pattern.finditer(content):
                scheduled_or_called.add(match.group(1))
            # Also check for regular function calls (await func_name())
            for func_name in bg_funcs:
                if re.search(rf"\bawait\s+{func_name}\s*\(", content):
                    scheduled_or_called.add(func_name)
                if re.search(rf"\b{func_name}\s*\(", content):
                    scheduled_or_called.add(func_name)
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Report unscheduled background tasks
    for func_name, (def_file, def_line) in bg_funcs.items():
        if func_name not in scheduled_or_called:
            findings.append(
                DeadCodeFinding(
                    file=def_file,
                    line=def_line,
                    symbol=func_name,
                    symbol_type="unwired_background",
                    confidence=0.50,  # Lower confidence - naming convention only
                    source="wiring_scan",
                    message=f"Background task '{func_name}' may never be scheduled",
                    context="Check for background_tasks.add_task() or asyncio.create_task()",
                )
            )

    return findings


def find_unwired_middleware(repo_root: Path) -> list[DeadCodeFinding]:
    """
    Find middleware classes never added to the app.
    """
    findings = []

    # Pattern for middleware classes
    middleware_pattern = re.compile(r"^class\s+(\w+Middleware)\s*[:\(]")

    # Find all middleware classes
    middleware_classes: dict[str, tuple[str, int]] = {}

    python_files = get_python_files(repo_root)
    for filepath in python_files:
        try:
            content = filepath.read_text()
            rel_path = str(filepath.relative_to(repo_root))

            for i, line in enumerate(content.split("\n"), 1):
                match = middleware_pattern.match(line.strip())
                if match:
                    class_name = match.group(1)
                    middleware_classes[class_name] = (rel_path, i)
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Search for add_middleware calls
    added: set[str] = set()
    add_middleware_pattern = re.compile(r"add_middleware\s*\(\s*(\w+)")

    for filepath in python_files:
        try:
            content = filepath.read_text()
            for match in add_middleware_pattern.finditer(content):
                added.add(match.group(1))
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Report unadded middleware
    for class_name, (def_file, def_line) in middleware_classes.items():
        if class_name not in added:
            findings.append(
                DeadCodeFinding(
                    file=def_file,
                    line=def_line,
                    symbol=class_name,
                    symbol_type="unwired_middleware",
                    confidence=0.70,
                    source="wiring_scan",
                    message=f"Middleware '{class_name}' defined but never added to app",
                    context="Check for app.add_middleware() calls",
                )
            )

    return findings


def find_unwired_websocket_routes(repo_root: Path) -> list[DeadCodeFinding]:
    """
    Find WebSocket route handlers in unmounted routers.
    """
    findings = []

    # Pattern for websocket routes
    ws_pattern = re.compile(r"@\w+\.websocket\s*\(\s*['\"]([^'\"]+)['\"]")

    # Find all websocket route definitions
    ws_routes: list[tuple[str, int, str]] = []  # (file, line, path)

    api_dir = repo_root / "api"
    if not api_dir.exists():
        return findings

    for filepath in api_dir.rglob("*.py"):
        try:
            content = filepath.read_text()
            rel_path = str(filepath.relative_to(repo_root))

            for i, line in enumerate(content.split("\n"), 1):
                match = ws_pattern.search(line)
                if match:
                    ws_path = match.group(1)
                    ws_routes.append((rel_path, i, ws_path))
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    # Check if the file's router is mounted (reuse router mounting logic)
    # For now, just report all websocket routes with lower confidence
    for rel_path, line_num, ws_path in ws_routes:
        # Skip if in main server file (likely mounted)
        if "server.py" in rel_path or "main.py" in rel_path:
            continue

        findings.append(
            DeadCodeFinding(
                file=rel_path,
                line=line_num,
                symbol=ws_path,
                symbol_type="unwired_websocket",
                confidence=0.75,
                source="wiring_scan",
                message=f"WebSocket route '{ws_path}' - verify router is mounted",
                context="Ensure parent router is included in main app",
            )
        )

    return findings


# =============================================================================
# PARALLEL SCANNER
# =============================================================================


def scan_file_for_dataclass_fields(filepath: Path) -> list[DataclassFieldInfo]:
    """Scan a single file for dataclass fields (for parallel execution)."""
    return extract_dataclass_fields(filepath)


def get_python_files(
    repo_root: Path, exclude_dirs: set[str] | None = None
) -> list[Path]:
    """Get all Python files in the repo."""
    exclude_dirs = exclude_dirs or EXCLUDE_DIRS
    files = []

    for path in repo_root.rglob("*.py"):
        # Skip excluded directories
        if any(excluded in path.parts for excluded in exclude_dirs):
            continue
        # Skip excluded files
        if path.name in EXCLUDE_FILES:
            continue
        files.append(path)

    return files


# =============================================================================
# MAIN AUDIT FUNCTION
# =============================================================================


def run_dead_code_audit(
    repo_root: Path = REPO_ROOT,
    min_vulture_confidence: int = MIN_VULTURE_CONFIDENCE,
    exclude_dirs: set[str] | None = None,
    parallel_workers: int = 8,
    output_file: Path | None = None,
    wiring_only: bool = False,
) -> AuditResult:
    """
    Run comprehensive dead code audit.

    Args:
        repo_root: Repository root path
        min_vulture_confidence: Minimum vulture confidence (0-100)
        exclude_dirs: Directories to exclude
        parallel_workers: Number of parallel workers for AST scanning
        output_file: Optional output file for JSON results
        wiring_only: If True, only run wiring integrity checks (skip vulture/ruff)

    Returns:
        AuditResult with all findings
    """
    logger.info("Starting dead code audit...")

    exclude_dirs = exclude_dirs or EXCLUDE_DIRS
    all_files = get_python_files(repo_root, exclude_dirs)
    logger.info(f"Found {len(all_files)} Python files to scan")

    result = AuditResult(total_files_scanned=len(all_files))

    if not wiring_only:
        # Phase 1a: Run Vulture
        logger.info("Running Vulture scan...")
        vulture_findings = run_vulture(all_files, min_vulture_confidence)
        result.findings.extend(vulture_findings)
        logger.info(f"Vulture found {len(vulture_findings)} issues")

        # Phase 1b: Run Ruff
        logger.info("Running Ruff scan...")
        ruff_findings = run_ruff(all_files)
        result.findings.extend(ruff_findings)
        logger.info(f"Ruff found {len(ruff_findings)} issues")

        # Phase 1c: Extract dataclass fields (parallel)
        logger.info("Extracting dataclass fields...")
        all_dataclass_fields: list[DataclassFieldInfo] = []

        with ProcessPoolExecutor(max_workers=parallel_workers) as executor:
            futures = {
                executor.submit(scan_file_for_dataclass_fields, f): f for f in all_files
            }

            for future in as_completed(futures):
                try:
                    fields = future.result()
                    all_dataclass_fields.extend(fields)
                except Exception as e:
                    filepath = futures[future]
                    result.errors.append(f"Error scanning {filepath}: {e}")

        result.dataclass_fields = all_dataclass_fields
        logger.info(f"Found {len(all_dataclass_fields)} dataclass fields")

        # Phase 1d: Analyze dataclass field usage
        logger.info("Analyzing dataclass field usage...")
        dataclass_findings = analyze_dataclass_fields(all_dataclass_fields, all_files)
        result.findings.extend(dataclass_findings)
        logger.info(f"Found {len(dataclass_findings)} unused dataclass fields")

    # ==========================================================================
    # WIRING INTEGRITY SCANS (always run, or wiring_only mode)
    # ==========================================================================
    logger.info("Running wiring integrity scans...")

    # Tier 1: HIGH Priority (existing + new)
    router_findings = find_unwired_routers(repo_root)
    result.findings.extend(router_findings)
    logger.info(f"  Unwired routers: {len(router_findings)}")

    service_findings = find_unwired_services(repo_root)
    result.findings.extend(service_findings)
    logger.info(f"  Unwired services: {len(service_findings)}")

    tool_findings = find_unwired_tools(repo_root)
    result.findings.extend(tool_findings)
    logger.info(f"  Unwired tools: {len(tool_findings)}")

    pydantic_findings = find_unwired_pydantic_models(repo_root)
    result.findings.extend(pydantic_findings)
    logger.info(f"  Unwired Pydantic models: {len(pydantic_findings)}")

    dep_findings = find_unwired_dependencies(repo_root)
    result.findings.extend(dep_findings)
    logger.info(f"  Unwired dependencies: {len(dep_findings)}")

    app_state_findings = find_unwired_app_state(repo_root)
    result.findings.extend(app_state_findings)
    logger.info(f"  Unwired app.state: {len(app_state_findings)}")

    export_findings = find_export_discrepancies(repo_root)
    result.findings.extend(export_findings)
    logger.info(f"  Export discrepancies: {len(export_findings)}")

    # Tier 2: MEDIUM Priority (L9-specific)
    kernel_findings = find_unwired_kernels(repo_root)
    result.findings.extend(kernel_findings)
    logger.info(f"  Unwired kernels: {len(kernel_findings)}")

    agent_findings = find_unwired_agents(repo_root)
    result.findings.extend(agent_findings)
    logger.info(f"  Unwired agents: {len(agent_findings)}")

    orch_findings = find_unwired_orchestrators(repo_root)
    result.findings.extend(orch_findings)
    logger.info(f"  Unwired orchestrators: {len(orch_findings)}")

    # Tier 3: LOWER Priority
    event_findings = find_unwired_event_handlers(repo_root)
    result.findings.extend(event_findings)
    logger.info(f"  Unwired event handlers: {len(event_findings)}")

    bg_findings = find_unwired_background_tasks(repo_root)
    result.findings.extend(bg_findings)
    logger.info(f"  Unwired background tasks: {len(bg_findings)}")

    middleware_findings = find_unwired_middleware(repo_root)
    result.findings.extend(middleware_findings)
    logger.info(f"  Unwired middleware: {len(middleware_findings)}")

    ws_findings = find_unwired_websocket_routes(repo_root)
    result.findings.extend(ws_findings)
    logger.info(f"  Unwired WebSocket routes: {len(ws_findings)}")

    # Deduplicate findings
    seen = set()
    unique_findings = []
    for finding in result.findings:
        key = (finding.file, finding.line, finding.symbol)
        if key not in seen:
            seen.add(key)
            unique_findings.append(finding)

    result.findings = unique_findings
    logger.info(f"Total unique findings: {len(result.findings)}")

    # Output results
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(result.to_dict(), indent=2))
        logger.info(f"Results written to {output_file}")

    return result


# =============================================================================
# SARIF OUTPUT FORMAT (GitHub/IDE Integration)
# =============================================================================


def generate_sarif_output(
    result: AuditResult, tool_name: str = "l9-dead-code-audit"
) -> dict:
    """
    Generate SARIF (Static Analysis Results Interchange Format) output.

    SARIF is the standard format for static analysis results, supported by:
    - GitHub Code Scanning
    - VS Code SARIF Viewer
    - Azure DevOps
    - Many other IDEs and CI tools
    """
    # Map symbol types to SARIF rule IDs
    rule_map = {
        # Dead code rules
        "import": "L9-DC001",
        "variable": "L9-DC002",
        "function": "L9-DC003",
        "method": "L9-DC004",
        "class": "L9-DC005",
        "argument": "L9-DC006",
        "dataclass_field": "L9-DC007",
        "class_attribute": "L9-DC008",
        "dead_branch": "L9-DC009",
        # Wiring rules
        "unwired_router": "L9-WI001",
        "unwired_service": "L9-WI002",
        "unwired_tool": "L9-WI003",
        "unwired_pydantic": "L9-WI004",
        "unwired_dependency": "L9-WI005",
        "unwired_kernel": "L9-WI006",
        "unwired_agent": "L9-WI007",
        "unwired_orchestrator": "L9-WI008",
        "unwired_event": "L9-WI009",
        "unwired_background": "L9-WI010",
        "unwired_middleware": "L9-WI011",
        "unwired_websocket": "L9-WI012",
        "unwired_app_state": "L9-WI013",
        "export_not_reexported": "L9-WI014",
        "orphan_export": "L9-WI015",
    }

    # Confidence to SARIF level mapping
    def confidence_to_level(conf: float) -> str:
        """
        Returns the confidence level as a string based on the provided confidence score, used in dead code detection thresholds.

        Args:
            conf: A float representing the confidence score for dead code detection.

        Returns:
            A string indicating the confidence level: "error" for high confidence, "warning" for moderate, or "note" for low confidence.
        """
        if conf >= 0.85:
            return "error"
        if conf >= 0.70:
            return "warning"
        return "note"

    # Build rules array
    rules = []
    seen_rules = set()
    for finding in result.findings:
        rule_id = rule_map.get(finding.symbol_type, f"L9-XX-{finding.symbol_type}")
        if rule_id not in seen_rules:
            seen_rules.add(rule_id)
            rules.append(
                {
                    "id": rule_id,
                    "name": finding.symbol_type.replace("_", " ").title(),
                    "shortDescription": {
                        "text": f"Detected {finding.symbol_type.replace('_', ' ')}"
                    },
                    "fullDescription": {
                        "text": f"L9 Dead Code Audit detected a potential {finding.symbol_type.replace('_', ' ')} issue."
                    },
                    "defaultConfiguration": {"level": "warning"},
                    "properties": {
                        "category": (
                            "wiring" if finding.source == "wiring_scan" else "dead_code"
                        )
                    },
                }
            )

    # Build results array
    results = []
    for finding in result.findings:
        rule_id = rule_map.get(finding.symbol_type, f"L9-XX-{finding.symbol_type}")
        results.append(
            {
                "ruleId": rule_id,
                "level": confidence_to_level(finding.confidence),
                "message": {"text": finding.message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": finding.file,
                                "uriBaseId": "%SRCROOT%",
                            },
                            "region": {"startLine": finding.line, "startColumn": 1},
                        }
                    }
                ],
                "properties": {
                    "confidence": finding.confidence,
                    "source": finding.source,
                    "symbol": finding.symbol,
                    "context": finding.context,
                },
            }
        )

    # Build SARIF document
    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": tool_name,
                        "version": "1.0.0",
                        "informationUri": "https://github.com/l9-project/l9",
                        "rules": rules,
                    }
                },
                "results": results,
                "invocations": [
                    {
                        "executionSuccessful": len(result.errors) == 0,
                        "toolExecutionNotifications": [
                            {"message": {"text": err}} for err in result.errors
                        ],
                    }
                ],
            }
        ],
    }


# =============================================================================
# CONFIDENCE TIER HELPERS
# =============================================================================


def get_confidence_tier(confidence: float) -> tuple[str, str]:
    """
    Classify confidence into tiers for display.

    Returns (tier_name, emoji_indicator)
    """
    if confidence >= 0.85:
        return "HIGH", "🔴"
    if confidence >= 0.70:
        return "MEDIUM", "🟡"
    return "LOW", "🟢"


def print_findings_by_confidence_tier(findings: list[DeadCodeFinding]) -> None:
    """Print findings grouped by confidence tier."""
    high = [f for f in findings if f.confidence >= 0.85]
    medium = [f for f in findings if 0.70 <= f.confidence < 0.85]
    low = [f for f in findings if f.confidence < 0.70]

    if high:
        logger.info(
            "\n🔴 high confidence ({len(high)} findings) — almost certainly issues:"
        )
        for f in high[:10]:
            print(
                f"  [{f.confidence:.0%}] {f.symbol} ({f.symbol_type}) @ {f.file}:{f.line}"
            )
        if len(high) > 10:
            logger.info("  ... and {len(high) - 10} more")

    if medium:
        print(
            f"\n🟡 MEDIUM CONFIDENCE ({len(medium)} findings) — Likely issues, verify:"
        )
        for f in medium[:10]:
            print(
                f"  [{f.confidence:.0%}] {f.symbol} ({f.symbol_type}) @ {f.file}:{f.line}"
            )
        if len(medium) > 10:
            logger.info("  ... and {len(medium) - 10} more")

    if low:
        logger.info(
            "\n🟢 low confidence ({len(low)} findings) — possible false positives:"
        )
        for f in low[:5]:
            print(
                f"  [{f.confidence:.0%}] {f.symbol} ({f.symbol_type}) @ {f.file}:{f.line}"
            )
        if len(low) > 5:
            logger.info("  ... and {len(low) - 5} more")


# =============================================================================
# CLI
# =============================================================================


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="L9 Dead Code & Wiring Integrity Audit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full audit (dead code + wiring)
  python find_dead_code.py

  # Wiring checks only (faster)
  python find_dead_code.py --wiring-only

  # Output SARIF for GitHub/IDE integration
  python find_dead_code.py --format sarif --output reports/audit.sarif

  # Filter by confidence
  python find_dead_code.py --min-confidence 0.8
""",
    )
    parser.add_argument(
        "--min-vulture-confidence",
        type=int,
        default=MIN_VULTURE_CONFIDENCE,
        help=f"Minimum vulture confidence 0-100 (default: {MIN_VULTURE_CONFIDENCE})",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default=",".join(EXCLUDE_DIRS),
        help="Comma-separated directories to exclude",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=8,
        help="Number of parallel workers (default: 8)",
    )
    # Generate timestamped default filename
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    default_output = f"reports/dead_code_audit_{timestamp}.json"

    parser.add_argument(
        "--output",
        type=str,
        default=default_output,
        help="Output file path (default: timestamped filename)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "sarif"],
        default="json",
        help="Output format: json (default) or sarif (for GitHub/IDE)",
    )
    parser.add_argument(
        "--wiring-only",
        action="store_true",
        help="Run only wiring integrity checks (skip vulture/ruff/dataclass)",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Only show findings with confidence >= this value (0.0-1.0)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(0),
        )

    exclude_dirs = set(args.exclude.split(","))
    output_file = REPO_ROOT / args.output

    # Adjust output extension for SARIF
    if args.format == "sarif" and output_file.suffix != ".sarif":
        output_file = output_file.with_suffix(".sarif")

    result = run_dead_code_audit(
        repo_root=REPO_ROOT,
        min_vulture_confidence=args.min_vulture_confidence,
        exclude_dirs=exclude_dirs,
        parallel_workers=args.parallel,
        output_file=None,  # We'll write manually based on format
        wiring_only=args.wiring_only,
    )

    # Filter by confidence if specified
    if args.min_confidence > 0:
        result.findings = [
            f for f in result.findings if f.confidence >= args.min_confidence
        ]

    # Write output in requested format
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "sarif":
        sarif_output = generate_sarif_output(result)
        output_file.write_text(json.dumps(sarif_output, indent=2))
    else:
        output_file.write_text(json.dumps(result.to_dict(), indent=2))

    # Print summary
    logger.info("\n" + "=" * 70)
    if args.wiring_only:
        logger.info("l9 wiring integrity audit")
    else:
        logger.info("l9 dead code & wiring integrity audit")
    logger.info("=" * 70)
    logger.info("files scanned: {result.total_files_scanned}")
    logger.info("total findings: {len(result.findings)}")
    if not args.wiring_only:
        logger.info("dataclass fields analyzed: {len(result.dataclass_fields)}")

    # Breakdown by type
    by_type: dict[str, int] = {}
    for finding in result.findings:
        by_type[finding.symbol_type] = by_type.get(finding.symbol_type, 0) + 1

    logger.info("\n📊 findings by type:")
    for symbol_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        logger.info("  symbol type: count", symbol_type=symbol_type, count=count)

    # Breakdown by source
    by_source: dict[str, int] = {}
    for finding in result.findings:
        by_source[finding.source] = by_source.get(finding.source, 0) + 1

    logger.info("\n📦 findings by source:")
    for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
        logger.info("  source: count", source=source, count=count)

    # L9-specific wiring breakdown
    l9_types = [
        "unwired_kernel",
        "unwired_tool",
        "unwired_agent",
        "unwired_orchestrator",
    ]
    l9_findings = [f for f in result.findings if f.symbol_type in l9_types]
    if l9_findings:
        logger.info("\n🎯 l9-specific wiring issues: {len(l9_findings)}")
        for t in l9_types:
            count = len([f for f in l9_findings if f.symbol_type == t])
            if count > 0:
                logger.info("  t: count", t=t, count=count)

    # Confidence tier breakdown
    print_findings_by_confidence_tier(result.findings)

    if result.errors:
        logger.error("\n❌ errors: {len(result.errors)}")
        for err in result.errors[:3]:
            logger.info("  - err", err=err)

    logger.info("\n📄 output: output file", output_file=output_file)
    if args.format == "sarif":
        logger.info("   (sarif format - import into github code scanning or vs code)")
    logger.info("=" * 70)

    return 0 if not result.errors else 1


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-017",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "ast",
        "caching",
        "cli",
        "dataclass",
        "debugging",
        "endpoint",
        "event-driven",
        "filesystem",
        "logging",
    ],
    "keywords": [
        "agents",
        "analysis",
        "analyze",
        "app",
        "audit",
        "background",
        "baseline",
        "confidence",
    ],
    "business_value": "Provides find dead code components including DeadCodeFinding, DataclassFieldInfo, AuditResult",
    "last_modified": "2026-01-17T23:47:56Z",
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
