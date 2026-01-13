#!/usr/bin/env python3
"""
L9 Dead Code Audit - Phase 2: Cross-Reference Resolution
=========================================================

Eliminates false positives from Phase 1 by checking:
- Dynamic access via getattr() / __dict__
- Registry patterns (@register decorators)
- Protocol/ABC implementations
- Inheritance chains (subclass usage)
- Test fixtures and mocks
- importlib.import_module() dynamic imports
- Serialization (dataclass asdict, Pydantic model_dump, etc.)
- Generated code directories (codegen/, _archived/)
- Pydantic BaseModel subclasses
- FastAPI response models
- Observability fields (*_ms, *_count, *_at)

Version: 1.1.0 (Enhanced false positive detection)
"""

import ast
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional
import structlog

logger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent

# Directories to exclude (generated/archived code)
EXCLUDED_DIRS = {
    "codegen/",
    "_archived/",
    ".venv/",
    "venv/",
    "__pycache__/",
    ".git/",
    "node_modules/",
}

# Observability field patterns (these are used for metrics/logging, not direct access)
OBSERVABILITY_PATTERNS = [
    r"_ms$",           # latency_ms, duration_ms
    r"_count$",        # hit_count, error_count
    r"_at$",           # created_at, updated_at
    r"_timestamp$",    # event_timestamp
    r"_time$",         # start_time, end_time
    r"_duration$",     # call_duration
    r"_bytes$",        # request_bytes
    r"_size$",         # payload_size
]

# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class ResolvedFinding:
    """A finding after false positive resolution."""
    file: str
    line: int
    symbol: str
    symbol_type: str
    confidence: float
    source: str
    message: str
    context: str = ""
    is_false_positive: bool = False
    false_positive_reason: Optional[str] = None
    accessed_via: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResolutionResult:
    """Result of false positive resolution."""
    total_input_findings: int
    resolved_findings: list[ResolvedFinding] = field(default_factory=list)
    false_positives_eliminated: int = 0
    remaining_findings: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_input_findings": self.total_input_findings,
            "false_positives_eliminated": self.false_positives_eliminated,
            "remaining_findings": self.remaining_findings,
            "resolved_findings": [f.to_dict() for f in self.resolved_findings],
        }


# =============================================================================
# FALSE POSITIVE DETECTION
# =============================================================================

class FalsePositiveDetector:
    """Detect and filter false positive dead code findings."""
    
    def __init__(self, repo_root: Path = REPO_ROOT):
        self.repo_root = repo_root
        self._codebase_content: Optional[str] = None
        self._registry_patterns: set[str] = set()
        self._protocol_implementations: set[str] = set()
        self._inheritance_map: dict[str, list[str]] = {}
        self._pydantic_models: set[str] = set()
        self._response_models: set[str] = set()
    
    def _load_codebase_content(self, files: list[Path]) -> str:
        """Load all codebase content for pattern matching."""
        if self._codebase_content is None:
            content_parts = []
            for filepath in files:
                try:
                    content_parts.append(filepath.read_text())
                except Exception:
                    continue
            self._codebase_content = "\n".join(content_parts)
        return self._codebase_content
    
    def _scan_registry_patterns(self, files: list[Path]):
        """Find symbols registered via decorator patterns."""
        patterns = [
            r"@register\(['\"](\w+)['\"]\)",
            r"@register_(\w+)",
            r"@(\w+)\.register",
            r"registry\.add\(['\"](\w+)['\"]\)",
            r"REGISTRY\[['\"](\w+)['\"]\]",
        ]
        
        for filepath in files:
            try:
                content = filepath.read_text()
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    self._registry_patterns.update(matches)
            except Exception:
                continue
    
    def _scan_protocol_implementations(self, files: list[Path]):
        """Find Protocol/ABC implementations."""
        for filepath in files:
            try:
                content = filepath.read_text()
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Check for Protocol or ABC inheritance
                        for base in node.bases:
                            base_name = ast.unparse(base) if base else ""
                            if "Protocol" in base_name or "ABC" in base_name:
                                # All methods in this class are protocol implementations
                                for item in node.body:
                                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                        self._protocol_implementations.add(item.name)
            except Exception:
                continue
    
    def _build_inheritance_map(self, files: list[Path]):
        """Build map of class inheritance relationships."""
        for filepath in files:
            try:
                content = filepath.read_text()
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for base in node.bases:
                            base_name = ""
                            if isinstance(base, ast.Name):
                                base_name = base.id
                            elif isinstance(base, ast.Attribute):
                                base_name = base.attr
                            
                            if base_name:
                                if base_name not in self._inheritance_map:
                                    self._inheritance_map[base_name] = []
                                self._inheritance_map[base_name].append(node.name)
            except Exception:
                continue
    
    def check_dynamic_access(self, symbol: str, content: str) -> Optional[str]:
        """Check if symbol is accessed dynamically via getattr, __dict__, etc."""
        patterns = [
            (rf"getattr\([^,]+,\s*['\"]?{re.escape(symbol)}['\"]?\)", "getattr()"),
            (rf"__dict__\[['\"]?{re.escape(symbol)}['\"]?\]", "__dict__ access"),
            (rf"setattr\([^,]+,\s*['\"]?{re.escape(symbol)}['\"]?\)", "setattr()"),
            (rf"hasattr\([^,]+,\s*['\"]?{re.escape(symbol)}['\"]?\)", "hasattr()"),
        ]
        
        for pattern, reason in patterns:
            if re.search(pattern, content):
                return reason
        return None
    
    def check_registry_pattern(self, symbol: str) -> bool:
        """Check if symbol is registered via decorator/registry."""
        return symbol in self._registry_patterns
    
    def check_protocol_implementation(self, symbol: str) -> bool:
        """Check if symbol is a Protocol/ABC method."""
        return symbol in self._protocol_implementations
    
    def check_inheritance_usage(self, symbol: str, class_name: Optional[str] = None) -> Optional[str]:
        """Check if symbol is used in subclasses."""
        if class_name and class_name in self._inheritance_map:
            subclasses = self._inheritance_map[class_name]
            if subclasses:
                return f"Used in subclasses: {', '.join(subclasses[:3])}"
        return None
    
    def check_test_fixture(self, filepath: str, symbol: str) -> bool:
        """Check if symbol is a test fixture or mock."""
        # Check if in test file
        if "/tests/" in filepath or "test_" in filepath or "_test.py" in filepath:
            return True
        
        # Check for common fixture patterns
        fixture_patterns = ["fixture", "mock", "fake", "stub", "dummy"]
        symbol_lower = symbol.lower()
        return any(p in symbol_lower for p in fixture_patterns)
    
    def check_dynamic_import(self, symbol: str, content: str) -> Optional[str]:
        """Check if symbol might be loaded via importlib."""
        patterns = [
            rf"import_module\(['\"].*{re.escape(symbol)}",
            rf"__import__\(['\"].*{re.escape(symbol)}",
        ]
        
        for pattern in patterns:
            if re.search(pattern, content):
                return "dynamic import"
        return None
    
    def check_serialization_usage(self, symbol: str, content: str) -> Optional[str]:
        """Check if symbol might be used in serialization (JSON, dataclass_json, etc.)."""
        # Dataclass fields often accessed via asdict, model_dump, etc.
        patterns = [
            (r"asdict\(", "asdict()"),
            (r"model_dump\(", "model_dump()"),
            (r"model_dump_json\(", "model_dump_json()"),
            (r"\.dict\(", ".dict()"),
            (r"json\.dumps\(", "json.dumps()"),
            (r"to_dict\(", "to_dict()"),
            (r"from_dict\(", "from_dict()"),
            (r"jsonable_encoder\(", "jsonable_encoder()"),
            (r"model_validate\(", "model_validate()"),
            (r"TypeAdapter.*validate_python", "TypeAdapter"),
        ]
        
        # If the symbol is a dataclass field, check for serialization patterns in the file
        for pattern, reason in patterns:
            if re.search(pattern, content):
                return reason
        return None
    
    def check_excluded_directory(self, filepath: str) -> Optional[str]:
        """Check if file is in an excluded directory (generated code, archives, etc.)."""
        for excluded in EXCLUDED_DIRS:
            if excluded in filepath:
                return f"Excluded directory: {excluded}"
        return None
    
    def check_observability_field(self, symbol: str) -> bool:
        """Check if symbol matches observability field patterns (metrics, timestamps)."""
        simple_name = symbol.split(".")[-1] if "." in symbol else symbol
        for pattern in OBSERVABILITY_PATTERNS:
            if re.search(pattern, simple_name):
                return True
        return False
    
    def _scan_pydantic_models(self, files: list[Path]):
        """Find all Pydantic BaseModel subclasses."""
        for filepath in files:
            try:
                content = filepath.read_text()
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for base in node.bases:
                            base_name = ""
                            if isinstance(base, ast.Name):
                                base_name = base.id
                            elif isinstance(base, ast.Attribute):
                                base_name = base.attr
                            
                            if base_name in ("BaseModel", "BaseSettings"):
                                self._pydantic_models.add(node.name)
            except Exception:
                continue
    
    def _scan_response_models(self, files: list[Path]):
        """Find models used as FastAPI response_model."""
        for filepath in files:
            try:
                content = filepath.read_text()
                # Look for response_model=ClassName patterns
                matches = re.findall(r"response_model\s*=\s*(\w+)", content)
                self._response_models.update(matches)
                
                # Also look for -> ClassName in route handlers
                matches = re.findall(r"async def \w+\([^)]*\)\s*->\s*(\w+)", content)
                self._response_models.update(matches)
            except Exception:
                continue
    
    def check_pydantic_model(self, class_name: Optional[str]) -> bool:
        """Check if class is a Pydantic model (fields auto-serialized)."""
        if class_name:
            return class_name in self._pydantic_models
        return False
    
    def check_response_model(self, class_name: Optional[str]) -> bool:
        """Check if class is used as FastAPI response_model."""
        if class_name:
            return class_name in self._response_models
        return False
    
    def resolve_finding(
        self,
        finding: dict[str, Any],
        all_content: str,
        files: list[Path],
    ) -> ResolvedFinding:
        """Resolve a single finding for false positives."""
        resolved = ResolvedFinding(
            file=finding.get("file", ""),
            line=finding.get("line", 0),
            symbol=finding.get("symbol", ""),
            symbol_type=finding.get("symbol_type", ""),
            confidence=finding.get("confidence", 0.0),
            source=finding.get("source", ""),
            message=finding.get("message", ""),
            context=finding.get("context", ""),
        )
        
        symbol = resolved.symbol
        # Extract simple symbol name (e.g., "ClassName.field_name" -> "field_name")
        simple_symbol = symbol.split(".")[-1] if "." in symbol else symbol
        class_name = symbol.split(".")[0] if "." in symbol else None
        
        # Check 0: Excluded directory (generated code, archives)
        excluded_reason = self.check_excluded_directory(resolved.file)
        if excluded_reason:
            resolved.is_false_positive = True
            resolved.false_positive_reason = excluded_reason
            return resolved
        
        # Check 1: Dynamic access
        dynamic_reason = self.check_dynamic_access(simple_symbol, all_content)
        if dynamic_reason:
            resolved.is_false_positive = True
            resolved.false_positive_reason = f"Dynamic access via {dynamic_reason}"
            resolved.accessed_via.append(dynamic_reason)
            return resolved
        
        # Check 2: Registry pattern
        if self.check_registry_pattern(simple_symbol):
            resolved.is_false_positive = True
            resolved.false_positive_reason = "Registered via decorator/registry"
            return resolved
        
        # Check 3: Protocol implementation
        if self.check_protocol_implementation(simple_symbol):
            resolved.is_false_positive = True
            resolved.false_positive_reason = "Protocol/ABC implementation"
            return resolved
        
        # Check 4: Inheritance usage
        inheritance_reason = self.check_inheritance_usage(simple_symbol, class_name)
        if inheritance_reason:
            resolved.is_false_positive = True
            resolved.false_positive_reason = inheritance_reason
            return resolved
        
        # Check 5: Test fixture
        if self.check_test_fixture(resolved.file, simple_symbol):
            resolved.is_false_positive = True
            resolved.false_positive_reason = "Test fixture or mock"
            return resolved
        
        # Check 6: Dynamic import
        import_reason = self.check_dynamic_import(simple_symbol, all_content)
        if import_reason:
            resolved.is_false_positive = True
            resolved.false_positive_reason = import_reason
            return resolved
        
        # Check 7: Pydantic model (fields auto-serialized)
        if self.check_pydantic_model(class_name):
            resolved.is_false_positive = True
            resolved.false_positive_reason = f"Pydantic model field (auto-serialized)"
            return resolved
        
        # Check 8: FastAPI response model
        if self.check_response_model(class_name):
            resolved.is_false_positive = True
            resolved.false_positive_reason = f"FastAPI response model field"
            return resolved
        
        # Check 9: Observability field (metrics, timestamps)
        if self.check_observability_field(simple_symbol):
            resolved.is_false_positive = True
            resolved.false_positive_reason = "Observability/metrics field"
            return resolved
        
        # Check 10: Serialization (for dataclass fields) - MARK AS FALSE POSITIVE
        if resolved.symbol_type == "dataclass_field":
            try:
                file_content = (REPO_ROOT / resolved.file).read_text()
                serial_reason = self.check_serialization_usage(simple_symbol, file_content)
                if serial_reason:
                    resolved.is_false_positive = True
                    resolved.false_positive_reason = f"Serialization via {serial_reason}"
                    return resolved
            except Exception:
                pass
        
        return resolved


# =============================================================================
# MAIN RESOLUTION FUNCTION
# =============================================================================

def resolve_dead_code_refs(
    baseline_file: Path,
    repo_root: Path = REPO_ROOT,
    output_file: Optional[Path] = None,
) -> ResolutionResult:
    """
    Resolve false positives from Phase 1 baseline.
    
    Args:
        baseline_file: Path to Phase 1 JSON output
        repo_root: Repository root path
        output_file: Optional output file for JSON results
    
    Returns:
        ResolutionResult with resolved findings
    """
    logger.info(f"Loading baseline from {baseline_file}...")
    
    with open(baseline_file) as f:
        baseline_data = json.load(f)
    
    findings = baseline_data.get("findings", [])
    logger.info(f"Loaded {len(findings)} findings from baseline")
    
    result = ResolutionResult(total_input_findings=len(findings))
    
    # Get all Python files
    from find_dead_code import get_python_files
    all_files = get_python_files(repo_root)
    
    # Initialize detector
    detector = FalsePositiveDetector(repo_root)
    
    # Pre-scan for patterns
    logger.info("Scanning for registry patterns...")
    detector._scan_registry_patterns(all_files)
    logger.info(f"Found {len(detector._registry_patterns)} registered symbols")
    
    logger.info("Scanning for Protocol implementations...")
    detector._scan_protocol_implementations(all_files)
    logger.info(f"Found {len(detector._protocol_implementations)} protocol methods")
    
    logger.info("Building inheritance map...")
    detector._build_inheritance_map(all_files)
    logger.info(f"Found {len(detector._inheritance_map)} base classes with subclasses")
    
    logger.info("Scanning for Pydantic models...")
    detector._scan_pydantic_models(all_files)
    logger.info(f"Found {len(detector._pydantic_models)} Pydantic models")
    
    logger.info("Scanning for FastAPI response models...")
    detector._scan_response_models(all_files)
    logger.info(f"Found {len(detector._response_models)} response models")
    
    # Load all content for pattern matching
    logger.info("Loading codebase content...")
    all_content = detector._load_codebase_content(all_files)
    
    # Resolve each finding
    logger.info("Resolving findings...")
    for finding in findings:
        resolved = detector.resolve_finding(finding, all_content, all_files)
        result.resolved_findings.append(resolved)
        
        if resolved.is_false_positive:
            result.false_positives_eliminated += 1
        else:
            result.remaining_findings += 1
    
    logger.info(f"False positives eliminated: {result.false_positives_eliminated}")
    logger.info(f"Remaining findings: {result.remaining_findings}")
    
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
    
    parser = argparse.ArgumentParser(description="L9 Dead Code Audit - Phase 2: Resolution")
    parser.add_argument(
        "--input",
        type=str,
        default="reports/dead_code_baseline.json",
        help="Input file from Phase 1",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/dead_code_resolved.json",
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
    
    input_file = REPO_ROOT / args.input
    output_file = REPO_ROOT / args.output
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        print("Run Phase 1 first: python scripts/audit/find_dead_code.py")
        return 1
    
    result = resolve_dead_code_refs(
        baseline_file=input_file,
        repo_root=REPO_ROOT,
        output_file=output_file,
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("DEAD CODE AUDIT - PHASE 2 RESOLUTION")
    print("=" * 60)
    print(f"Input findings: {result.total_input_findings}")
    print(f"False positives eliminated: {result.false_positives_eliminated}")
    print(f"Remaining findings: {result.remaining_findings}")
    
    # Breakdown by false positive reason
    fp_reasons: dict[str, int] = {}
    for finding in result.resolved_findings:
        if finding.is_false_positive and finding.false_positive_reason:
            reason = finding.false_positive_reason.split(":")[0]  # Truncate details
            fp_reasons[reason] = fp_reasons.get(reason, 0) + 1
    
    if fp_reasons:
        print("\nFalse positives by reason:")
        for reason, count in sorted(fp_reasons.items(), key=lambda x: -x[1]):
            print(f"  {reason}: {count}")
    
    print(f"\nOutput: {output_file}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
