"""
ADR Enforcement Validator - Comprehensive ADR compliance checking

Enforces key Accepted ADRs across the L9 codebase by detecting violations in:
- ADR-0001: Path safety
- ADR-0002: Circular imports
- ADR-0003: Documentation standards
- ADR-0006: PacketEnvelope audit trails
- ADR-0010: Async patterns
- ADR-0022: Registry patterns
- ADR-0026: Protocol-based abstractions
- ADR-0055: Fail-loudly enforcement
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
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

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

    def to_dict(self) -> Dict:
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

    def to_dict(self) -> Dict:
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
        "ADR-0001": "CRITICAL",  # Path safety
        "ADR-0002": "CRITICAL",  # Circular imports
        "ADR-0003": "HIGH",  # Documentation
        "ADR-0006": "CRITICAL",  # PacketEnvelope audit
        "ADR-0010": "HIGH",  # Async patterns
        "ADR-0022": "HIGH",  # Registry pattern
        "ADR-0026": "MEDIUM",  # Protocol-based abstractions
        "ADR-0055": "CRITICAL",  # Fail-loudly
    }

    SKIP_PARTS = {
        # Version control & IDE
        ".git",
        ".idea",
        ".vscode",
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
        # Self-exclusion (checker contains patterns it checks for)
        "adr",
    }

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or Path.cwd()
        self._file_cache: dict[Path, str] = {}

    # ===== Helper methods =====

    def _read(self, path: Path) -> str:
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
        parts = set(path.parts)
        return any(skip in parts for skip in self.SKIP_PARTS)

    @staticmethod
    def _call_name(node: ast.Call) -> str:
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return ""

    # ===== ADR-0001: Path safety =====

    def check_adr_0001(self, path: Path) -> list[Violation]:
        """Sandboxed path resolution."""
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
        if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
            return True
        return False

    def _detect_cycles(self, graph: dict[str, set[str]]) -> list[list[str]]:
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

        for node in graph.keys():
            if node not in visited:
                dfs(node)

        return cycles

    def check_adr_0002(self) -> list[Violation]:
        """Circular import prevention."""
        violations: list[Violation] = []
        graph = self._build_import_graph()
        cycles = self._detect_cycles(graph)

        for cycle in cycles:
            cycle_str = " -> ".join(cycle + [cycle[0]])
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
        if not path.name == "__init__.py" and not ast.get_docstring(tree):
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
        """Async functions must not contain blocking calls.

        Only flags specific blocking patterns like time.sleep, requests.*
        Does NOT flag dict.get(), router.post(), asyncio.sleep(), etc.
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
        """Encourage Protocol-based abstractions instead of only ABC."""
        violations: list[Violation] = []
        text = self._read(path)
        lines = text.splitlines()

        uses_abc = any("from abc import" in l or "import abc" in l for l in lines)
        uses_protocol = "Protocol" in text

        if uses_abc and not uses_protocol:
            for lineno, line in enumerate(lines, start=1):
                if "from abc import" in line or "import abc" in line:
                    violations.append(
                        Violation(
                            adr="ADR-0026",
                            severity="MEDIUM",
                            file=str(path),
                            line=lineno,
                            issue="Using ABC without Protocol-based abstractions.",
                            fix="Consider using typing.Protocol for structural contracts (ADR-0026).",
                            code_snippet=line.strip(),
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
        violations.extend(self.check_adr_0001(path))
        violations.extend(self.check_adr_0003(path))
        violations.extend(self.check_adr_0006(path))
        violations.extend(self.check_adr_0010(path))
        violations.extend(self.check_adr_0022(path))
        violations.extend(self.check_adr_0026(path))
        violations.extend(self.check_adr_0055(path))
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

        all_violations.extend(self.check_adr_0002())

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
