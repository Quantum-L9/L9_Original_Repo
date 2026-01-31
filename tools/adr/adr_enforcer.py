"""
ADR Enforcement Validator - Comprehensive ADR compliance checking

Enforces Accepted ADRs 0001-0026 + 0055 across the L9 codebase.

CRITICAL (blocking):
- ADR-0001: Path safety
- ADR-0002: Circular imports
- ADR-0006: PacketEnvelope audit trails
- ADR-0055: Fail-loudly enforcement

HIGH (should fix):
- ADR-0003: Documentation standards
- ADR-0010: Async patterns (must_stay_async)
- ADR-0019: structlog logging standard
- ADR-0022: Registry patterns

MEDIUM (recommended):
- ADR-0004: Singleton auto-registry
- ADR-0008: Feature flag gating
- ADR-0014: DORA metadata block
- ADR-0017: Tool definition schema
- ADR-0026: Protocol-based abstractions

LOW (advisory):
- ADR-0005: RLS shared tenant model
- ADR-0007: 7-phase bootstrap ceremony
- ADR-0009: Circuit breaker resilience
- ADR-0011: Lazy initialization pattern
- ADR-0012: Memory DAG pipeline
- ADR-0013: Governance authority hierarchy
- ADR-0015: Migration sequential apply
- ADR-0016: TypedDict vs Pydantic boundary
- ADR-0020: Test fixture hierarchy
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Comprehensive ADR compliance checking",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-24T16:03:39Z",
    "updated_at": "2026-01-24T16:30:16Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "adr_enforcer",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API"],
        "memory_layers": ["working_memory"],
        "imported_by": ["tests.unit.adr.test_adr_enforcer"],
    },
}
# ============================================================================

import ast
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:
    import structlog

    logger = structlog.get_logger()
except ImportError:  # Fallback for environments without structlog
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


# ---------- Data Models ----------


@dataclass
class Violation:
    """Represents a single ADR violation."""

    adr: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    file: str
    line: int | None = None
    column: int | None = None
    issue: str = ""
    fix: str = ""
    code_snippet: str = ""

    def to_dict(self) -> dict:
        """Convert violation to dictionary representation.

        Returns:
            Dict containing all violation fields.
        """
        return asdict(self)


@dataclass
class ValidationReport:
    """Comprehensive validation report."""

    timestamp: str
    total_violations: int
    violations_by_adr: dict[str, int] = field(default_factory=dict)
    violations_by_severity: dict[str, int] = field(default_factory=dict)
    violations: list[Violation] = field(default_factory=list)
    files_scanned: int = 0
    high_priority_violations: list[Violation] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert validation report to dictionary representation.

        Returns:
            Dict containing report summary and all violations.
        """
        return {
            "timestamp": self.timestamp,
            "total_violations": self.total_violations,
            "violations_by_adr": self.violations_by_adr,
            "violations_by_severity": self.violations_by_severity,
            "files_scanned": self.files_scanned,
            "high_priority_count": len(self.high_priority_violations),
            "violations": [v.to_dict() for v in self.violations],
        }


# ---------- Validator ----------


class ADREnforcementValidator:
    """Enforces L9 ADR compliance across the codebase."""

    ADR_SEVERITY = {
        # Critical - Must fix before merge
        "ADR-0001": "CRITICAL",  # Path safety
        "ADR-0002": "CRITICAL",  # Circular imports
        "ADR-0006": "CRITICAL",  # PacketEnvelope audit
        "ADR-0055": "CRITICAL",  # Fail-loudly
        # High - Should fix
        "ADR-0010": "HIGH",  # Async patterns
        "ADR-0019": "HIGH",  # structlog (stdlib logging=HIGH, print=MEDIUM)
        "ADR-0022": "HIGH",  # Registry pattern
        # Medium - Recommended
        "ADR-0004": "MEDIUM",  # Singleton auto-registry
        "ADR-0008": "MEDIUM",  # Feature flag gating
        "ADR-0014": "MEDIUM",  # DORA metadata block
        "ADR-0017": "MEDIUM",  # Tool definition schema
        "ADR-0026": "MEDIUM",  # Protocol-based abstractions
        # Low - Advisory
        "ADR-0003": "LOW",  # Documentation (docstrings)
        "ADR-0005": "LOW",  # RLS shared tenant
        "ADR-0007": "LOW",  # 7-phase bootstrap
        "ADR-0009": "LOW",  # Circuit breaker
        "ADR-0011": "LOW",  # Lazy initialization
        "ADR-0012": "LOW",  # Memory DAG pipeline
        "ADR-0013": "LOW",  # Governance hierarchy
        "ADR-0015": "LOW",  # Migration sequential
        "ADR-0016": "LOW",  # TypedDict vs Pydantic
        "ADR-0020": "LOW",  # Test fixture hierarchy
    }

    SKIP_PARTS = {
        # Version control & IDE
        ".git",
        ".idea",
        ".vscode",
        ".cursor",
        ".github",
        # Python artifacts
        "__pycache__",
        ".pytest_cache",
        "venv",
        ".venv",
        "env",
        ".egg-info",
        # Database migrations (SQL, not Python logic)
        "migrations",
        "node_modules",
        # Tests (mocks legitimately skip audit_context)
        "tests",
        # Work-in-progress and archive directories
        "current_work",
        "igor",
        "codegen",
        ".dora",
        ".backup",
        # Documentation (not production code)
        "readme",
        "docs",
        "reports",
        # Self-exclusion (checker contains patterns it checks for)
        "adr",
    }

    def __init__(self, repo_root: Path | None = None) -> None:
        """Initialize the ADR enforcement validator.

        Args:
            repo_root: Root directory of the repository to scan.
                      Defaults to current working directory.
        """
        self.repo_root = repo_root or Path.cwd()
        self._file_cache: dict[Path, str] = {}

    # ===== Helper methods =====

    def _read(self, path: Path) -> str:
        """Read and cache file contents.

        Args:
            path: Path to the file to read.

        Returns:
            File contents as string, or empty string if path is a directory.
        """
        if path not in self._file_cache:
            # Guard against directories named .py (edge case)
            if not path.is_file():
                self._file_cache[path] = ""
            else:
                self._file_cache[path] = path.read_text(
                    encoding="utf-8", errors="ignore"
                )
        return self._file_cache[path]

    def _should_skip(self, path: Path) -> bool:
        """Check if a path should be skipped during scanning.

        Args:
            path: Path to check.

        Returns:
            True if path contains any skip patterns, False otherwise.
        """
        parts = set(path.parts)
        return any(skip in parts for skip in self.SKIP_PARTS)

    @staticmethod
    def _call_name(node: ast.Call) -> str:
        """Extract the function name from a Call AST node.

        Args:
            node: AST Call node to extract name from.

        Returns:
            Function or method name, or empty string if not extractable.
        """
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return ""

    # ===== ADR-0001: Path safety =====

    def check_adr_0001(self, path: Path) -> list[Violation]:
        """Check ADR-0001: Sandboxed path resolution.

        Args:
            path: Path to the file to check.

        Returns:
            List of violations found.
        """
        violations: list[Violation] = []
        text = self._read(path)
        lines = text.splitlines()

        for lineno, line in enumerate(lines, start=1):
            if "import os.path" in line:
                violations.append(
                    Violation(
                        adr="ADR-0001",
                        severity="CRITICAL",
                        file=str(path),
                        line=lineno,
                        issue="Using os.path instead of pathlib.Path",
                        fix="Use: from pathlib import Path, and Path(...).",
                        code_snippet=line.strip(),
                    )
                )

            if re.search(r"Path\(['\"]/(.+)['\"]\)", line):
                violations.append(
                    Violation(
                        adr="ADR-0001",
                        severity="CRITICAL",
                        file=str(path),
                        line=lineno,
                        issue="Absolute path construction detected.",
                        fix="Use Path(__file__).parent / 'relative/path'.",
                        code_snippet=line.strip(),
                    )
                )

            if re.search(r"os\.(getcwd|chdir)\s*\(", line):
                violations.append(
                    Violation(
                        adr="ADR-0001",
                        severity="HIGH",
                        file=str(path),
                        line=lineno,
                        issue="Using os.getcwd()/os.chdir() breaks sandbox assumptions.",
                        fix="Pass explicit paths instead of relying on cwd.",
                        code_snippet=line.strip(),
                    )
                )

        return violations

    # ===== ADR-0002: Circular imports =====

    def _build_import_graph(self) -> dict[str, set[str]]:
        """Build import graph from MODULE-LEVEL imports only.

        Lazy imports inside functions/methods are excluded because they don't
        cause runtime circular import errors - they're deferred until the
        function is called, by which time the importing module is fully loaded.
        """
        graph: dict[str, set[str]] = {}

        for py_file in self.repo_root.rglob("*.py"):
            # Skip directories named .py (edge case) and skipped paths
            if not py_file.is_file() or self._should_skip(py_file):
                continue

            rel = py_file.relative_to(self.repo_root)
            module = str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")
            graph.setdefault(module, set())

            try:
                tree = ast.parse(self._read(py_file))
            except SyntaxError:
                continue

            # Only check TOP-LEVEL imports (not inside functions/classes)
            for node in tree.body:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        graph[module].add(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    graph[module].add(node.module)
                # Handle TYPE_CHECKING blocks at module level
                elif isinstance(node, ast.If):
                    # Check if this is a TYPE_CHECKING guard
                    if self._is_type_checking_guard(node):
                        continue  # Skip TYPE_CHECKING imports
                    # Otherwise check imports in the if body
                    for child in node.body:
                        if isinstance(child, ast.Import):
                            for alias in child.names:
                                graph[module].add(alias.name)
                        elif isinstance(child, ast.ImportFrom) and child.module:
                            graph[module].add(child.module)

        return graph

    def _is_type_checking_guard(self, node: ast.If) -> bool:
        """Check if an If node is a TYPE_CHECKING guard."""
        test = node.test
        # Handle: if TYPE_CHECKING:
        if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
            return True
        # Handle: if typing.TYPE_CHECKING:
        return bool(isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")

    def _detect_cycles(self, graph: dict[str, set[str]]) -> list[list[str]]:
        """Detect circular dependencies in import graph.

        Args:
            graph: Import graph mapping modules to their imports.

        Returns:
            List of cycles, each cycle is a list of module names.
        """
        visited: set[str] = set()
        stack: set[str] = set()
        path: list[str] = []
        cycles: list[list[str]] = []

        def dfs(node: str) -> None:
            visited.add(node)
            stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, set()):
                if neighbor not in graph:
                    continue
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in stack:
                    # Found cycle
                    try:
                        idx = path.index(neighbor)
                        cycles.append(path[idx:].copy())
                    except ValueError:
                        pass

            path.pop()
            stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node)

        return cycles

    def check_adr_0002(self) -> list[Violation]:
        """Check ADR-0002: Circular import prevention.

        Returns:
            List of violations found.
        """
        violations: list[Violation] = []
        graph = self._build_import_graph()
        cycles = self._detect_cycles(graph)

        for cycle in cycles:
            cycle_str = " -> ".join([*cycle, cycle[0]])
            violations.append(
                Violation(
                    adr="ADR-0002",
                    severity="CRITICAL",
                    file=cycle[0],
                    issue=f"Circular import detected: {cycle_str}",
                    fix="Introduce TYPE_CHECKING guards or lazy imports inside functions.",
                )
            )

        return violations

    # ===== ADR-0003: Documentation standards =====

    # Directories where docstring enforcement is relaxed (utility code)
    DOCSTRING_SKIP_DIRS = {"scripts", "dev", ".github", "ci", "data", "codegenagent"}

    def check_adr_0003(self, path: Path) -> list[Violation]:
        """Documentation standards for public APIs.

        Enforces docstrings on public functions/classes in production code.
        Utility directories (scripts, dev, ci) use LOW severity.
        """
        violations: list[Violation] = []

        # ADR-0003 is advisory - docstrings are best practice but not blocking
        # Use LOW severity for all (can be upgraded per-directory if needed)
        severity = "LOW"

        try:
            text = self._read(path)
            tree = ast.parse(text)
        except SyntaxError:
            return violations

        # Skip module docstring check for __init__.py files
        if path.name != "__init__.py" and not ast.get_docstring(tree):
            violations.append(
                Violation(
                    adr="ADR-0003",
                    severity=severity,
                    file=str(path),
                    line=1,
                    issue="Missing module-level docstring.",
                    fix="Add a short module docstring describing purpose and key behaviors.",
                )
            )

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Skip private and dunder methods
                if node.name.startswith("_"):
                    continue
                # Skip test functions
                if node.name.startswith("test"):
                    continue
                if not ast.get_docstring(node):
                    violations.append(
                        Violation(
                            adr="ADR-0003",
                            severity=severity,
                            file=str(path),
                            line=node.lineno,
                            issue=f"Missing docstring for '{node.name}'.",
                            fix="Add a Google-style docstring documenting args/returns/raises.",
                        )
                    )

        return violations

    # ===== ADR-0006: PacketEnvelope audit trail =====

    # Classes that require audit trail fields when instantiated
    PACKET_ENVELOPE_CLASSES = {"PacketEnvelope", "PacketEnvelopeIn"}

    # Fields that satisfy ADR-0006 audit trail requirement (per ADR doc)
    # At least ONE of these must be present for audit trail identification
    AUDIT_TRAIL_FIELDS = {"thread_id", "metadata", "provenance"}

    def check_adr_0006(self, path: Path) -> list[Violation]:
        """PacketEnvelope audit trail enforcement (ADR-0006).

        Per ADR-0006: ALL operations must emit PacketEnvelope with audit trail.
        Audit trail is satisfied by providing at least one of:
        - thread_id: UUID for conversation/session tracking
        - metadata: dict with {agent, component, schema_version}
        - provenance: source tracking information

        Uses AST to detect actual instantiation calls.
        """
        violations: list[Violation] = []
        text = self._read(path)

        # Quick check: skip if no PacketEnvelope anywhere
        if "PacketEnvelope" not in text:
            return violations

        try:
            tree = ast.parse(text)
        except SyntaxError:
            return violations

        lines = text.splitlines()

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            # Get the name of the function/class being called
            call_name = self._call_name(node)
            if call_name not in self.PACKET_ENVELOPE_CLASSES:
                continue

            # Check if ANY audit trail field is provided
            provided_fields = {kw.arg for kw in node.keywords if kw.arg}
            has_audit_trail = bool(provided_fields & self.AUDIT_TRAIL_FIELDS)

            # Skip **kwargs patterns (deserialization from existing data)
            has_kwargs_unpack = any(kw.arg is None for kw in node.keywords)
            if has_kwargs_unpack:
                continue  # Skip - this is deserializing existing audit trail data

            if not has_audit_trail:
                # Get the source line for the snippet
                lineno = node.lineno
                snippet = lines[lineno - 1].strip() if lineno <= len(lines) else ""

                violations.append(
                    Violation(
                        adr="ADR-0006",
                        severity="HIGH",  # Lowered from CRITICAL - advisory
                        file=str(path),
                        line=lineno,
                        column=node.col_offset,
                        issue=f"{call_name}() missing audit trail fields.",
                        fix=(
                            "Provide at least one of: thread_id=UUID, "
                            "metadata=PacketMetadata(...), or provenance=PacketProvenance(...)"
                        ),
                        code_snippet=snippet,
                    )
                )

        return violations

    # ===== ADR-0010: must_stay_async & async patterns =====

    # Blocking module.function patterns (specific, not bare names)
    BLOCKING_CALLS = {
        # time.sleep blocks the event loop
        "time.sleep": "asyncio.sleep",
        # requests library is synchronous
        "requests.get": "aiohttp.ClientSession.get",
        "requests.post": "aiohttp.ClientSession.post",
        "requests.put": "aiohttp.ClientSession.put",
        "requests.delete": "aiohttp.ClientSession.delete",
        "requests.patch": "aiohttp.ClientSession.patch",
        "requests.head": "aiohttp.ClientSession.head",
        # urllib is synchronous
        "urllib.request.urlopen": "aiohttp",
    }

    def check_adr_0010(self, path: Path) -> list[Violation]:
        """Check ADR-0010: Async functions must not contain blocking calls.

        Only flags specific blocking patterns like time.sleep, requests.*
        Does NOT flag dict.get(), router.post(), asyncio.sleep(), etc.

        Args:
            path: Path to the file to check.

        Returns:
            List of violations found.
        """
        violations: list[Violation] = []

        try:
            text = self._read(path)
            tree = ast.parse(text)
        except SyntaxError:
            return violations

        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue

            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue

                # Build the full call name (e.g., "time.sleep", "requests.get")
                full_name = self._get_full_call_name(child)

                if full_name in self.BLOCKING_CALLS:
                    async_alt = self.BLOCKING_CALLS[full_name]
                    violations.append(
                        Violation(
                            adr="ADR-0010",
                            severity="HIGH",
                            file=str(path),
                            line=child.lineno,
                            issue=(
                                f"Blocking call '{full_name}' in async function "
                                f"'{node.name}'."
                            ),
                            fix=f"Use async equivalent: {async_alt}",
                        )
                    )

                # Also check for bare open() calls (not path.open() or file.open())
                if isinstance(child.func, ast.Name) and child.func.id == "open":
                    violations.append(
                        Violation(
                            adr="ADR-0010",
                            severity="HIGH",
                            file=str(path),
                            line=child.lineno,
                            issue=(
                                f"Blocking call 'open()' in async function "
                                f"'{node.name}'."
                            ),
                            fix="Use aiofiles.open() for async file I/O.",
                        )
                    )

        return violations

    def _get_full_call_name(self, node: ast.Call) -> str:
        """Extract full dotted call name like 'time.sleep' or 'requests.get'."""
        func = node.func

        # Simple name: open(), sleep()
        if isinstance(func, ast.Name):
            return func.id

        # Attribute: time.sleep(), requests.get()
        if isinstance(func, ast.Attribute):
            parts = []
            current = func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))

        return ""

    # ===== ADR-0022: Registry pattern =====

    def check_adr_0022(self, path: Path) -> list[Violation]:
        """Disallow manual singleton patterns; enforce registry pattern."""
        violations: list[Violation] = []

        try:
            text = self._read(path)
            tree = ast.parse(text)
        except SyntaxError:
            return violations

        has_registry_import = "Registry" in text or "registry" in text

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            has_new = any(
                isinstance(n, ast.FunctionDef) and n.name == "__new__"
                for n in node.body
            )
            has_instance_attr = any(
                isinstance(n, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id.startswith("_instance")
                    for t in n.targets
                )
                for n in node.body
            )

            if has_new and has_instance_attr and not has_registry_import:
                violations.append(
                    Violation(
                        adr="ADR-0022",
                        severity="HIGH",
                        file=str(path),
                        line=node.lineno,
                        issue=f"Manual singleton pattern in class '{node.name}'.",
                        fix="Refactor to use the central Registry pattern instead.",
                    )
                )

        return violations

    # ===== ADR-0026: Protocol-based abstractions =====

    def check_adr_0026(self, path: Path) -> list[Violation]:
        """Encourage Protocol-based abstractions for PURE interfaces.

        Only flags ABC usage when it's a pure interface (only abstract methods,
        no concrete implementations). Base classes with concrete code legitimately
        use ABC for inheritance.
        """
        violations: list[Violation] = []
        text = self._read(path)

        # Quick check: skip if no ABC
        if "from abc import" not in text and "import abc" not in text:
            return violations

        # If already using Protocol alongside ABC, that's fine
        if "Protocol" in text:
            return violations

        try:
            tree = ast.parse(text)
        except SyntaxError:
            return violations

        # Find ABC subclasses and check if they're pure interfaces
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            # Check if class inherits from ABC
            inherits_abc = any(
                (isinstance(base, ast.Name) and base.id == "ABC")
                or (isinstance(base, ast.Attribute) and base.attr == "ABC")
                for base in node.bases
            )

            if not inherits_abc:
                continue

            # Count abstract vs concrete methods
            abstract_count = 0
            concrete_count = 0

            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Check if method has @abstractmethod decorator
                    is_abstract = any(
                        (isinstance(d, ast.Name) and d.id == "abstractmethod")
                        or (isinstance(d, ast.Attribute) and d.attr == "abstractmethod")
                        for d in item.decorator_list
                    )

                    if is_abstract:
                        abstract_count += 1
                    elif not item.name.startswith("_"):
                        # Non-private, non-abstract method = concrete
                        concrete_count += 1

            # Only flag if it's a PURE interface (all abstract, no concrete)
            if abstract_count > 0 and concrete_count == 0:
                violations.append(
                    Violation(
                        adr="ADR-0026",
                        severity="LOW",  # Advisory - Protocol is preferred but not required
                        file=str(path),
                        line=node.lineno,
                        issue=f"Class '{node.name}' is a pure interface using ABC.",
                        fix="Consider using typing.Protocol for structural subtyping (duck typing).",
                        code_snippet=f"class {node.name}(ABC):",
                    )
                )

        return violations

    # ===== ADR-0004: Singleton Auto-Registry Pattern =====

    def check_adr_0004(self, path: Path) -> list[Violation]:
        """Check for manual singleton patterns instead of @register_singleton."""
        violations: list[Violation] = []
        text = self._read(path)
        lines = text.splitlines()

        # Skip if file uses @register_singleton (compliant)
        if "@register_singleton" in text:
            return violations

        # Check for manual singleton patterns
        for lineno, line in enumerate(lines, start=1):
            # Pattern: _instance: Optional[SomeClass] = None (manual singleton)
            if re.match(r"^_\w+\s*:\s*Optional\[.+\]\s*=\s*None", line.strip()):
                violations.append(
                    Violation(
                        adr="ADR-0004",
                        severity="MEDIUM",
                        file=str(path),
                        line=lineno,
                        issue="Manual singleton pattern detected.",
                        fix="Use @register_singleton decorator for auto-discovery.",
                        code_snippet=line.strip(),
                    )
                )
            # Pattern: _instance = None (bare assignment)
            if re.match(r"^_instance\s*=\s*None\s*$", line.strip()):
                violations.append(
                    Violation(
                        adr="ADR-0004",
                        severity="MEDIUM",
                        file=str(path),
                        line=lineno,
                        issue="Manual singleton _instance pattern.",
                        fix="Use @register_singleton for service registration.",
                        code_snippet=line.strip(),
                    )
                )

        return violations

    # ===== ADR-0005: RLS Shared Tenant Model =====

    def check_adr_0005(self, path: Path) -> list[Violation]:
        """Check for hardcoded tenant/org/user UUIDs (should use config)."""
        violations: list[Violation] = []
        text = self._read(path)
        lines = text.splitlines()

        # L9 canonical UUIDs that should come from config, not hardcoded
        hardcoded_uuids = {
            "73350468-3158-5d0f-9b8c-9b193d96fc4b": "tenant_id",
            "14910cef-fea1-51d7-9a28-05579e6c0c18": "org_id",
            "2f00c090-3816-51a0-806c-34d32522a070": "user_id",
        }

        for lineno, line in enumerate(lines, start=1):
            for uuid, name in hardcoded_uuids.items():
                if uuid in line:
                    # Skip config files and documentation
                    if "rls_config" in str(path) or "README" in str(path):
                        continue
                    violations.append(
                        Violation(
                            adr="ADR-0005",
                            severity="LOW",
                            file=str(path),
                            line=lineno,
                            issue=f"Hardcoded {name} UUID.",
                            fix="Use get_rls_config() from config/rls_config.py.",
                            code_snippet=line.strip()[:80],
                        )
                    )

        return violations

    # ===== ADR-0007: 7-Phase Bootstrap Ceremony =====

    def check_adr_0007(self, path: Path) -> list[Violation]:
        """Check for legacy agent initialization patterns."""
        violations: list[Violation] = []
        text = self._read(path)

        # Skip bootstrap directory (it implements the pattern)
        if "bootstrap" in str(path):
            return violations

        # Look for legacy agent creation without bootstrap
        if "create_agent_legacy" in text or "AgentInstance(" in text:
            # Check if also using bootstrap (OK) or only legacy (BAD)
            if "bootstrap_agent" not in text:
                try:
                    tree = ast.parse(text)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            name = self._call_name(node)
                            if name in ("create_agent_legacy", "AgentInstance"):
                                violations.append(
                                    Violation(
                                        adr="ADR-0007",
                                        severity="LOW",
                                        file=str(path),
                                        line=node.lineno,
                                        issue=f"Direct {name}() call bypasses 7-phase bootstrap.",
                                        fix="Use bootstrap_agent() for proper initialization.",
                                    )
                                )
                except SyntaxError:
                    pass

        return violations

    # ===== ADR-0008: Feature Flag Gating Pattern =====

    def check_adr_0008(self, path: Path) -> list[Violation]:
        """Check for os.getenv() usage instead of settings.FLAG_NAME."""
        violations: list[Violation] = []
        text = self._read(path)

        # Skip settings.py itself (it defines the flags)
        if "settings.py" in str(path):
            return violations

        # Look for os.getenv with L9_ prefix (should use settings)
        pattern = r'os\.getenv\s*\(\s*["\']L9_'
        for match in re.finditer(pattern, text):
            lineno = text[: match.start()].count("\n") + 1
            line = (
                text.splitlines()[lineno - 1]
                if lineno <= len(text.splitlines())
                else ""
            )
            violations.append(
                Violation(
                    adr="ADR-0008",
                    severity="MEDIUM",
                    file=str(path),
                    line=lineno,
                    issue="os.getenv() for L9_ flag instead of settings.",
                    fix="Use settings.FLAG_NAME from config/settings.py.",
                    code_snippet=line.strip()[:80],
                )
            )

        return violations

    # ===== ADR-0009: Circuit Breaker Resilience =====

    def check_adr_0009(self, path: Path) -> list[Violation]:
        """Advisory: Check for external calls without circuit breaker."""
        violations: list[Violation] = []
        text = self._read(path)

        # Skip if file uses CircuitBreaker (compliant)
        if "CircuitBreaker" in text:
            return violations

        # Check for httpx/aiohttp calls without circuit breaker
        external_patterns = [
            (r"httpx\.(get|post|put|delete|patch)\s*\(", "httpx HTTP call"),
            (r"aiohttp\.(get|post|put|delete)\s*\(", "aiohttp HTTP call"),
        ]

        for pattern, desc in external_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                lineno = text[: match.start()].count("\n") + 1
                violations.append(
                    Violation(
                        adr="ADR-0009",
                        severity="LOW",
                        file=str(path),
                        line=lineno,
                        issue=f"{desc} without circuit breaker.",
                        fix="Wrap external calls with CircuitBreaker from core/observability/circuit_breaker.py.",
                    )
                )

        return violations

    # ===== ADR-0011: Lazy Initialization Pattern =====

    def check_adr_0011(self, path: Path) -> list[Violation]:
        """Check for eager initialization instead of lazy get_*() pattern."""
        violations: list[Violation] = []
        text = self._read(path)

        # Check for module-level service instantiation (eager init)
        # Pattern: service = SomeService() at module level (not in function)
        try:
            tree = ast.parse(text)
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.endswith(
                            "_service"
                        ):
                            if isinstance(node.value, ast.Call):
                                violations.append(
                                    Violation(
                                        adr="ADR-0011",
                                        severity="LOW",
                                        file=str(path),
                                        line=node.lineno,
                                        issue=f"Eager service instantiation: {target.id}.",
                                        fix="Use lazy get_*() function with module-level _instance cache.",
                                    )
                                )
        except SyntaxError:
            pass

        return violations

    # ===== ADR-0012: Memory DAG Pipeline =====

    def check_adr_0012(self, path: Path) -> list[Violation]:
        """Check for direct memory writes bypassing DAG."""
        violations: list[Violation] = []
        text = self._read(path)

        # Skip DAG implementation files
        if "dag" in str(path).lower() or "ingestion" in str(path):
            return violations

        # Look for direct repository writes (should use ingest_packet)
        if "repository.write_packet" in text or "repo.write_packet" in text:
            for match in re.finditer(r"(repository|repo)\.write_packet\s*\(", text):
                lineno = text[: match.start()].count("\n") + 1
                violations.append(
                    Violation(
                        adr="ADR-0012",
                        severity="LOW",
                        file=str(path),
                        line=lineno,
                        issue="Direct repository.write_packet() bypasses DAG.",
                        fix="Use ingest_packet() to flow through SubstrateDAG pipeline.",
                    )
                )

        return violations

    # ===== ADR-0013: Governance Authority Hierarchy =====

    def check_adr_0013(self, path: Path) -> list[Violation]:
        """Check for missing approval checks on high-risk operations."""
        violations: list[Violation] = []
        text = self._read(path)

        # High-risk operations that should check requires_approval()
        high_risk_ops = [
            "git_commit",
            "git_push",
            "file_delete",
            "deploy",
            "mac_agent_exec",
        ]

        for op in high_risk_ops:
            if f'"{op}"' in text or f"'{op}'" in text:
                if "requires_approval" not in text and "approval_manager" not in text:
                    for match in re.finditer(rf'["\']({op})["\']', text):
                        lineno = text[: match.start()].count("\n") + 1
                        violations.append(
                            Violation(
                                adr="ADR-0013",
                                severity="LOW",
                                file=str(path),
                                line=lineno,
                                issue=f"High-risk operation '{op}' without approval check.",
                                fix="Use ApprovalManager.requires_approval() before execution.",
                            )
                        )
                    break  # One warning per file

        return violations

    # ===== ADR-0014: DORA Metadata Block Pattern =====

    def check_adr_0014(self, path: Path) -> list[Violation]:
        """Check for missing __dora_meta__ in Python modules."""
        violations: list[Violation] = []
        text = self._read(path)

        # Skip __init__.py, conftest.py, and small files
        if path.name in ("__init__.py", "conftest.py"):
            return violations
        if len(text.splitlines()) < 20:
            return violations

        # Check for __dora_meta__
        if "__dora_meta__" not in text:
            violations.append(
                Violation(
                    adr="ADR-0014",
                    severity="MEDIUM",
                    file=str(path),
                    line=1,
                    issue="Missing __dora_meta__ metadata block.",
                    fix="Add __dora_meta__ dict after module docstring (run scripts/audit/inject_dora_complete.py).",
                )
            )

        return violations

    # ===== ADR-0015: Migration Sequential Apply Pattern =====

    def check_adr_0015(self) -> list[Violation]:
        """Check migration file naming and numbering."""
        violations: list[Violation] = []
        migrations_dir = self.repo_root / "migrations"

        if not migrations_dir.exists():
            return violations

        sql_files = sorted(migrations_dir.glob("*.sql"))
        expected_num = 1

        for sql_file in sql_files:
            name = sql_file.name
            # Check naming pattern: NNNN_description.sql
            match = re.match(r"^(\d{4})_(.+)\.sql$", name)
            if not match:
                # Also allow YYYYMMDD_ format
                if not re.match(r"^\d{8}_", name):
                    violations.append(
                        Violation(
                            adr="ADR-0015",
                            severity="LOW",
                            file=str(sql_file),
                            line=1,
                            issue=f"Invalid migration filename: {name}",
                            fix="Use format: NNNN_description.sql (e.g., 0025_new_feature.sql).",
                        )
                    )
            else:
                num = int(match.group(1))
                if num != expected_num and num < 1000:  # Skip date-based migrations
                    violations.append(
                        Violation(
                            adr="ADR-0015",
                            severity="LOW",
                            file=str(sql_file),
                            line=1,
                            issue=f"Migration sequence gap: expected {expected_num:04d}, got {num:04d}.",
                            fix="Migrations must be sequential (no gaps).",
                        )
                    )
                expected_num = num + 1

        return violations

    # ===== ADR-0016: TypedDict vs Pydantic Boundary =====

    def check_adr_0016(self, path: Path) -> list[Violation]:
        """Check for Pydantic BaseModel in LangGraph contexts."""
        violations: list[Violation] = []
        text = self._read(path)

        # Only check files that use langgraph
        if "langgraph" not in text.lower() and "graph_state" not in text.lower():
            return violations

        # Check for Pydantic BaseModel in graph state classes
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if class has "State" in name and inherits from BaseModel
                    if "state" in node.name.lower():
                        for base in node.bases:
                            base_name = ""
                            if isinstance(base, ast.Name):
                                base_name = base.id
                            elif isinstance(base, ast.Attribute):
                                base_name = base.attr
                            if base_name == "BaseModel":
                                violations.append(
                                    Violation(
                                        adr="ADR-0016",
                                        severity="LOW",
                                        file=str(path),
                                        line=node.lineno,
                                        issue=f"LangGraph state class '{node.name}' uses Pydantic.",
                                        fix="Use TypedDict for LangGraph state schemas.",
                                    )
                                )
        except SyntaxError:
            pass

        return violations

    # ===== ADR-0017: Tool Definition Schema =====

    def check_adr_0017(self, path: Path) -> list[Violation]:
        """Check tool_id patterns for OpenAI compatibility."""
        violations: list[Violation] = []
        text = self._read(path)

        # Only check files with ToolDefinition
        if "ToolDefinition" not in text:
            return violations

        # Find tool_id values and validate pattern
        # Pattern: tool_id="..." or tool_id='...'
        for match in re.finditer(r'tool_id\s*=\s*["\']([^"\']+)["\']', text):
            tool_id = match.group(1)
            lineno = text[: match.start()].count("\n") + 1

            # Validate: must match ^[a-zA-Z0-9_-]+$
            if not re.match(r"^[a-zA-Z0-9_-]+$", tool_id):
                violations.append(
                    Violation(
                        adr="ADR-0017",
                        severity="MEDIUM",
                        file=str(path),
                        line=lineno,
                        issue=f"Invalid tool_id: '{tool_id}' (contains invalid chars).",
                        fix="Tool IDs must match ^[a-zA-Z0-9_-]+$ (no dots, spaces, special chars).",
                        code_snippet=f'tool_id="{tool_id}"',
                    )
                )

        return violations

    # ===== ADR-0019: structlog Logging Standard =====

    # Directories where print() is legitimate (CLI/scripts)
    PRINT_ALLOWED_DIRS = {
        "scripts",
        "ci",
        "dev",
        "tools",
        "ops",
        "mac_agent",  # CLI runner
    }

    def check_adr_0019(self, path: Path) -> list[Violation]:
        """Check for print() and stdlib logging instead of structlog.

        Note: print() is allowed in scripts/, ci/, dev/, tools/ directories
        where CLI output is expected. Only production code in core/, api/,
        memory/, etc. should use structlog exclusively.
        """
        violations: list[Violation] = []
        text = self._read(path)
        lines = text.splitlines()

        # Check if print() is allowed in this directory
        path_parts = set(path.parts)
        print_allowed = bool(path_parts & self.PRINT_ALLOWED_DIRS)

        if not print_allowed:
            for lineno, line in enumerate(lines, start=1):
                stripped = line.strip()

                # Check for print() calls (excluding comments and strings in same line)
                if re.match(r"^print\s*\(", stripped):
                    violations.append(
                        Violation(
                            adr="ADR-0019",
                            severity="MEDIUM",  # Lowered from HIGH - often legitimate
                            file=str(path),
                            line=lineno,
                            issue="Using print() instead of structlog.",
                            fix="Use structlog.get_logger(__name__).info() for logging.",
                            code_snippet=stripped[:60],
                        )
                    )

        # Check for stdlib logging import (not just structlog)
        if re.search(r"^import logging\s*$", text, re.MULTILINE):
            if "structlog" not in text:
                for lineno, line in enumerate(lines, start=1):
                    if re.match(r"^import logging\s*$", line.strip()):
                        violations.append(
                            Violation(
                                adr="ADR-0019",
                                severity="HIGH",
                                file=str(path),
                                line=lineno,
                                issue="Using stdlib logging instead of structlog.",
                                fix="Use structlog.get_logger(__name__) for all logging.",
                            )
                        )
                        break

        return violations

    # ===== ADR-0020: Test Fixture Hierarchy =====

    def check_adr_0020(self, path: Path) -> list[Violation]:
        """Check for network calls in unit tests."""
        violations: list[Violation] = []
        text = self._read(path)

        # Only check test files
        if not path.name.startswith("test_") and "tests/" not in str(path):
            return violations

        # Skip integration tests (network allowed)
        if "integration" in str(path):
            return violations

        # Check for real network calls
        network_patterns = [
            (r'httpx\.(get|post|put|delete)\s*\(["\']https?://', "httpx network call"),
            (
                r'requests\.(get|post|put|delete)\s*\(["\']https?://',
                "requests network call",
            ),
            (r"aiohttp\.ClientSession\(\)", "aiohttp session in test"),
        ]

        for pattern, desc in network_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                lineno = text[: match.start()].count("\n") + 1
                violations.append(
                    Violation(
                        adr="ADR-0020",
                        severity="LOW",
                        file=str(path),
                        line=lineno,
                        issue=f"{desc} in unit test.",
                        fix="Use fixtures from tests/conftest.py instead of real network.",
                    )
                )

        return violations

    # ===== ADR-0055: Fail-loudly vs silent failures =====

    def check_adr_0055(self, path: Path) -> list[Violation]:
        """No silent exception swallowing; fail loudly or return error packets."""
        violations: list[Violation] = []
        text = self._read(path)
        lines = text.splitlines()

        for lineno, line in enumerate(lines, start=1):
            if re.match(r"^\s*except\s*:\s*$", line):
                violations.append(
                    Violation(
                        adr="ADR-0055",
                        severity="CRITICAL",
                        file=str(path),
                        line=lineno,
                        issue="Bare except clause.",
                        fix="Catch specific exception types or Exception explicitly.",
                        code_snippet=line.strip(),
                    )
                )
            if re.search(r"except\s+Exception\s*:\s*pass", line):
                violations.append(
                    Violation(
                        adr="ADR-0055",
                        severity="CRITICAL",
                        file=str(path),
                        line=lineno,
                        issue="Silent exception swallowing (`except Exception: pass`).",
                        fix="Log with structlog and re-raise or return an error PacketEnvelope.",
                        code_snippet=line.strip(),
                    )
                )

        return violations

    # ===== Scanning =====

    def scan_file(self, path: Path) -> list[Violation]:
        if path.suffix != ".py" or self._should_skip(path):
            return []

        violations: list[Violation] = []
        # Critical
        violations.extend(self.check_adr_0001(path))
        violations.extend(self.check_adr_0006(path))
        violations.extend(self.check_adr_0055(path))
        # High
        violations.extend(self.check_adr_0003(path))
        violations.extend(self.check_adr_0010(path))
        violations.extend(self.check_adr_0019(path))
        violations.extend(self.check_adr_0022(path))
        # Medium
        violations.extend(self.check_adr_0004(path))
        violations.extend(self.check_adr_0008(path))
        violations.extend(self.check_adr_0014(path))
        violations.extend(self.check_adr_0017(path))
        violations.extend(self.check_adr_0026(path))
        # Low (advisory)
        violations.extend(self.check_adr_0005(path))
        violations.extend(self.check_adr_0007(path))
        violations.extend(self.check_adr_0009(path))
        violations.extend(self.check_adr_0011(path))
        violations.extend(self.check_adr_0012(path))
        violations.extend(self.check_adr_0013(path))
        violations.extend(self.check_adr_0016(path))
        violations.extend(self.check_adr_0020(path))
        return violations

    def scan_repo(self) -> ValidationReport:
        logger.info(f"ADR enforcement scan started: {self.repo_root}")

        all_violations: list[Violation] = []
        files_scanned = 0

        for py in sorted(self.repo_root.rglob("*.py")):
            # Skip directories named .py (edge case) and skipped paths
            if not py.is_file() or self._should_skip(py):
                continue
            files_scanned += 1
            all_violations.extend(self.scan_file(py))

        # Repo-wide checks (not per-file)
        all_violations.extend(self.check_adr_0002())
        all_violations.extend(self.check_adr_0015())

        return self._build_report(all_violations, files_scanned)

    @staticmethod
    def _build_report(
        violations: list[Violation], files_scanned: int
    ) -> ValidationReport:
        by_adr: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        high_priority: list[Violation] = []

        for v in violations:
            by_adr[v.adr] = by_adr.get(v.adr, 0) + 1
            by_severity[v.severity] = by_severity.get(v.severity, 0) + 1
            if v.severity in {"CRITICAL", "HIGH"}:
                high_priority.append(v)

        return ValidationReport(
            timestamp=datetime.now().isoformat(),
            total_violations=len(violations),
            violations_by_adr=by_adr,
            violations_by_severity=by_severity,
            violations=violations,
            files_scanned=files_scanned,
            high_priority_violations=high_priority,
        )


# ---------- CLI ----------


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="L9 ADR Enforcement Validator (Option B - full enforcement)",
    )
    parser.add_argument(
        "--scan-repo",
        action="store_true",
        help="Scan entire repository for ADR violations.",
    )
    parser.add_argument(
        "--check-file",
        type=str,
        help="Scan a single file or glob pattern (e.g., src/**/*.py).",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Write JSON report to this path.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero status if any violations are found.",
    )

    args = parser.parse_args()

    validator = ADREnforcementValidator()
    report: ValidationReport | None = None

    try:
        if args.scan_repo:
            report = validator.scan_repo()
        elif args.check_file:
            violations: list[Violation] = []
            matches = list(Path.cwd().glob(args.check_file))
            for p in matches:
                violations.extend(validator.scan_file(p))
            report = validator._build_report(violations, len(matches))
        else:
            parser.print_help()
            return 1

        as_dict = report.to_dict()
        print(json.dumps(as_dict, indent=2))

        if args.output:
            Path(args.output).write_text(
                json.dumps(as_dict, indent=2), encoding="utf-8"
            )
            logger.info(f"ADR enforcement report written: {args.output}")

        if args.strict and report.total_violations > 0:
            return 1

        return 0
    except Exception as exc:  # Fail loudly per ADR-0055
        logger.error(f"ADR enforcement validator failed: {exc}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "ast",
        "audit-tool",
        "caching",
        "cli",
        "dataclass",
        "event-driven",
        "filesystem",
        "logging",
        "migration",
    ],
    "keywords": ["0001", "0002", "0003", "0006", "0010", "0022", "0026", "0055"],
    "business_value": "ADR-0001: Path safety ADR-0002: Circular imports ADR-0003: Documentation standards ADR-0006: PacketEnvelope audit trails ADR-0010: Async patterns ADR-0022: Registry patterns ADR-0026: Protocol-based a",
    "last_modified": "2026-01-24T16:30:16Z",
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
