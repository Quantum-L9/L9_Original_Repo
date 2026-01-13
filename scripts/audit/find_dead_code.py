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

import ast
import json
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional
import structlog

logger = structlog.get_logger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

REPO_ROOT = Path(__file__).parent.parent.parent
EXCLUDE_DIRS = {"tests", "_archived", "__pycache__", ".venv", "venv", ".git", "node_modules"}
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

def run_vulture(files: list[Path], min_confidence: int = MIN_VULTURE_CONFIDENCE) -> list[DeadCodeFinding]:
    """Run vulture on files and parse results."""
    findings = []
    
    try:
        # Check if vulture is installed
        result = subprocess.run(
            ["vulture", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning("Vulture not installed, skipping vulture scan")
            return findings
    except FileNotFoundError:
        logger.warning("Vulture not installed, skipping vulture scan")
        return findings
    
    # Run vulture with min-confidence
    file_paths = [str(f) for f in files]
    
    try:
        result = subprocess.run(
            ["vulture", "--min-confidence", str(min_confidence)] + file_paths,
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
                
                findings.append(DeadCodeFinding(
                    file=filepath,
                    line=int(line_num),
                    symbol=symbol,
                    symbol_type=symbol_type,
                    confidence=int(confidence) / 100.0,
                    source="vulture",
                    message=message,
                ))
                
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
    
    try:
        # Check if ruff is installed
        result = subprocess.run(
            ["ruff", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning("Ruff not installed, skipping ruff scan")
            return findings
    except FileNotFoundError:
        logger.warning("Ruff not installed, skipping ruff scan")
        return findings
    
    # Run ruff with specific rules for unused code
    # F401: unused import
    # F841: local variable assigned but never used
    # ARG001-ARG005: unused arguments
    file_paths = [str(f) for f in files]
    
    try:
        result = subprocess.run(
            ["ruff", "check", "--select=F401,F841,ARG", "--output-format=json"] + file_paths,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        
        if result.stdout:
            ruff_results = json.loads(result.stdout)
            
            for item in ruff_results:
                symbol_type = _ruff_code_to_type(item.get("code", ""))
                
                findings.append(DeadCodeFinding(
                    file=item.get("filename", ""),
                    line=item.get("location", {}).get("row", 0),
                    symbol=item.get("message", "").split("'")[1] if "'" in item.get("message", "") else "",
                    symbol_type=symbol_type,
                    confidence=0.98 if symbol_type == "import" else 0.95,
                    source="ruff",
                    message=item.get("message", ""),
                    context=item.get("code", ""),
                ))
                
    except json.JSONDecodeError:
        logger.warning("Could not parse ruff JSON output")
    except Exception as e:
        logger.error(f"Ruff scan failed: {e}")
    
    return findings


def _ruff_code_to_type(code: str) -> str:
    """Convert ruff error code to symbol type."""
    if code == "F401":
        return "import"
    elif code == "F841":
        return "variable"
    elif code.startswith("ARG"):
        return "argument"
    return "unknown"


# =============================================================================
# DATACLASS FIELD ANALYZER (AST-based)
# =============================================================================

class DataclassFieldVisitor(ast.NodeVisitor):
    """Extract dataclass fields from Python AST."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.fields: list[DataclassFieldInfo] = []
        self.current_class: Optional[str] = None
        self.in_dataclass = False
    
    def visit_ClassDef(self, node: ast.ClassDef):
        # Check if decorated with @dataclass
        is_dataclass = any(
            (isinstance(d, ast.Name) and d.id == "dataclass") or
            (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass") or
            (isinstance(d, ast.Attribute) and d.attr == "dataclass")
            for d in node.decorator_list
        )
        
        if is_dataclass:
            old_class = self.current_class
            old_in_dataclass = self.in_dataclass
            self.current_class = node.name
            self.in_dataclass = True
            
            # Extract fields from class body
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    field_name = item.target.id
                    type_annotation = ast.unparse(item.annotation) if item.annotation else "Any"
                    has_default = item.value is not None
                    
                    self.fields.append(DataclassFieldInfo(
                        class_name=node.name,
                        field_name=field_name,
                        file=self.filepath,
                        line=item.lineno,
                        has_default=has_default,
                        type_annotation=type_annotation,
                    ))
            
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
        rf"\.{field.field_name}\b",              # Direct attribute access
        rf"\['{field.field_name}'\]",            # Dict-like access single quote
        rf'\["{field.field_name}"\]',            # Dict-like access double quote
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
                    
        except Exception:
            continue
    
    return usages


def analyze_dataclass_fields(all_fields: list[DataclassFieldInfo], all_files: list[Path]) -> list[DeadCodeFinding]:
    """Find dataclass fields that are never used."""
    findings = []
    
    for field_info in all_fields:
        usages = find_field_usages(field_info, all_files)
        
        if not usages:
            findings.append(DeadCodeFinding(
                file=field_info.file,
                line=field_info.line,
                symbol=f"{field_info.class_name}.{field_info.field_name}",
                symbol_type="dataclass_field",
                confidence=0.95,
                source="ast_dataclass",
                message=f"Dataclass field '{field_info.field_name}' in class '{field_info.class_name}' is never accessed",
                context=f"type={field_info.type_annotation}, has_default={field_info.has_default}",
            ))
    
    return findings


# =============================================================================
# PARALLEL SCANNER
# =============================================================================

def scan_file_for_dataclass_fields(filepath: Path) -> list[DataclassFieldInfo]:
    """Scan a single file for dataclass fields (for parallel execution)."""
    return extract_dataclass_fields(filepath)


def get_python_files(repo_root: Path, exclude_dirs: set[str] = None) -> list[Path]:
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
    exclude_dirs: set[str] = None,
    parallel_workers: int = 8,
    output_file: Optional[Path] = None,
) -> AuditResult:
    """
    Run comprehensive dead code audit.
    
    Args:
        repo_root: Repository root path
        min_vulture_confidence: Minimum vulture confidence (0-100)
        exclude_dirs: Directories to exclude
        parallel_workers: Number of parallel workers for AST scanning
        output_file: Optional output file for JSON results
    
    Returns:
        AuditResult with all findings
    """
    logger.info("Starting dead code audit...")
    
    exclude_dirs = exclude_dirs or EXCLUDE_DIRS
    all_files = get_python_files(repo_root, exclude_dirs)
    logger.info(f"Found {len(all_files)} Python files to scan")
    
    result = AuditResult(total_files_scanned=len(all_files))
    
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
        futures = {executor.submit(scan_file_for_dataclass_fields, f): f for f in all_files}
        
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
    
    # Deduplicate findings (vulture and ruff may overlap)
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
# CLI
# =============================================================================

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="L9 Dead Code Audit - Phase 1")
    parser.add_argument(
        "--min-vulture-confidence",
        type=int,
        default=MIN_VULTURE_CONFIDENCE,
        help=f"Minimum vulture confidence (default: {MIN_VULTURE_CONFIDENCE})",
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
    parser.add_argument(
        "--output",
        type=str,
        default="reports/dead_code_baseline.json",
        help="Output file path",
    )
    parser.add_argument(
        "--verbose", "-v",
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
    
    result = run_dead_code_audit(
        repo_root=REPO_ROOT,
        min_vulture_confidence=args.min_vulture_confidence,
        exclude_dirs=exclude_dirs,
        parallel_workers=args.parallel,
        output_file=output_file,
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("DEAD CODE AUDIT - PHASE 1 BASELINE")
    print("=" * 60)
    print(f"Files scanned: {result.total_files_scanned}")
    print(f"Total findings: {len(result.findings)}")
    print(f"Dataclass fields analyzed: {len(result.dataclass_fields)}")
    
    # Breakdown by type
    by_type: dict[str, int] = {}
    for finding in result.findings:
        by_type[finding.symbol_type] = by_type.get(finding.symbol_type, 0) + 1
    
    print("\nFindings by type:")
    for symbol_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {symbol_type}: {count}")
    
    # Breakdown by source
    by_source: dict[str, int] = {}
    for finding in result.findings:
        by_source[finding.source] = by_source.get(finding.source, 0) + 1
    
    print("\nFindings by source:")
    for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {source}: {count}")
    
    if result.errors:
        print(f"\nErrors: {len(result.errors)}")
    
    print(f"\nOutput: {output_file}")
    print("=" * 60)
    
    return 0 if not result.errors else 1


if __name__ == "__main__":
    sys.exit(main())
