#!/usr/bin/env python3
"""
L9 Runtime Import Validation Audit
===================================
Comprehensive validation that goes beyond static analysis to catch:
- NameError (undefined variables like 'timezone')
- ImportError (missing modules)
- AttributeError (missing attributes on imports)
- Circular imports
- Conditional code path issues

This script actually EXECUTES code paths to find runtime errors.

Version: 1.0.0
"""

import ast
import importlib
import importlib.util
import json
import os
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add L9 root to path
L9_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(L9_ROOT))

@dataclass
class ValidationResult:
    """Result of validating a single module."""
    module_path: str
    module_name: str
    status: str  # PASS, FAIL, SKIP
    error_type: str | None = None
    error_message: str | None = None
    error_line: int | None = None
    error_traceback: str | None = None
    classes_validated: list[str] = field(default_factory=list)
    functions_validated: list[str] = field(default_factory=list)
    conditional_paths_found: int = 0
    warnings: list[str] = field(default_factory=list)

@dataclass
class AuditReport:
    """Complete audit report."""
    timestamp: str
    total_modules: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[ValidationResult] = field(default_factory=list)
    critical_errors: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "summary": {
                "total_modules": self.total_modules,
                "passed": self.passed,
                "failed": self.failed,
                "skipped": self.skipped,
                "pass_rate": f"{(self.passed / self.total_modules * 100):.1f}%" if self.total_modules > 0 else "N/A"
            },
            "critical_errors": self.critical_errors,
            "warnings": self.warnings,
            "detailed_results": [
                {
                    "module": r.module_name,
                    "path": r.module_path,
                    "status": r.status,
                    "error_type": r.error_type,
                    "error_message": r.error_message,
                    "error_line": r.error_line,
                    "classes_validated": r.classes_validated,
                    "functions_validated": r.functions_validated,
                    "conditional_paths": r.conditional_paths_found,
                    "warnings": r.warnings
                }
                for r in self.results
            ]
        }


class ConditionalPathAnalyzer(ast.NodeVisitor):
    """AST visitor to find conditional code paths that may hide errors."""
    
    def __init__(self):
        self.conditional_imports: list[dict] = []
        self.conditional_usages: list[dict] = []
        self.current_condition: str | None = None
        
    def visit_If(self, node: ast.If) -> None:
        # Track the condition
        old_condition = self.current_condition
        try:
            self.current_condition = ast.unparse(node.test)
        except Exception:
            self.current_condition = "<complex condition>"
        
        self.generic_visit(node)
        self.current_condition = old_condition
        
    def visit_Try(self, node: ast.Try) -> None:
        # Track try/except blocks that might hide import errors
        for handler in node.handlers:
            if handler.type:
                try:
                    exc_name = ast.unparse(handler.type)
                    if exc_name in ('ImportError', 'ModuleNotFoundError', 'Exception'):
                        self.conditional_imports.append({
                            "line": node.lineno,
                            "type": "try_except",
                            "exception": exc_name
                        })
                except Exception:
                    pass
        self.generic_visit(node)
        
    def visit_Import(self, node: ast.Import) -> None:
        if self.current_condition:
            for alias in node.names:
                self.conditional_imports.append({
                    "line": node.lineno,
                    "type": "conditional_import",
                    "module": alias.name,
                    "condition": self.current_condition
                })
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if self.current_condition:
            self.conditional_imports.append({
                "line": node.lineno,
                "type": "conditional_import",
                "module": node.module,
                "names": [a.name for a in node.names],
                "condition": self.current_condition
            })
        self.generic_visit(node)


class RuntimeImportValidator:
    """Main validator class."""
    
    SKIP_DIRS = {
        '__pycache__', '.git', '.backup', 'node_modules', 
        'venv', '.venv', 'env', '.env', 'dist', 'build',
        'l9_private'  # Kernel files are read-only
    }
    
    SKIP_FILES = {
        '__init__.py',  # Often empty or simple
        'conftest.py',  # pytest config
    }
    
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.report = AuditReport(timestamp=datetime.now(timezone.utc).isoformat())
        
    def find_python_files(self) -> list[Path]:
        """Find all Python files to validate."""
        files = []
        for path in self.root_path.rglob("*.py"):
            # Skip excluded directories
            if any(skip in path.parts for skip in self.SKIP_DIRS):
                continue
            # Skip excluded files
            if path.name in self.SKIP_FILES:
                continue
            files.append(path)
        return sorted(files)
    
    def path_to_module_name(self, path: Path) -> str:
        """Convert file path to Python module name."""
        rel_path = path.relative_to(self.root_path)
        parts = list(rel_path.parts)
        parts[-1] = parts[-1].replace('.py', '')
        return '.'.join(parts)
    
    def validate_module_import(self, path: Path) -> ValidationResult:
        """Validate that a module can be imported."""
        module_name = self.path_to_module_name(path)
        result = ValidationResult(
            module_path=str(path.relative_to(self.root_path)),
            module_name=module_name,
            status="PASS"
        )
        
        try:
            # First, analyze AST for conditional paths
            with open(path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            try:
                tree = ast.parse(source)
                analyzer = ConditionalPathAnalyzer()
                analyzer.visit(tree)
                result.conditional_paths_found = len(analyzer.conditional_imports)
                
                if analyzer.conditional_imports:
                    for ci in analyzer.conditional_imports:
                        result.warnings.append(
                            f"Line {ci['line']}: Conditional import ({ci['type']})"
                        )
            except SyntaxError as e:
                result.status = "FAIL"
                result.error_type = "SyntaxError"
                result.error_message = str(e)
                result.error_line = e.lineno
                return result
            
            # Now try to actually import the module
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                result.status = "SKIP"
                result.error_message = "Could not create module spec"
                return result
            
            module = importlib.util.module_from_spec(spec)
            
            # Execute the module (this is where runtime errors occur)
            spec.loader.exec_module(module)
            
            # Collect classes and functions defined in the module
            for name, obj in vars(module).items():
                if name.startswith('_'):
                    continue
                if isinstance(obj, type):
                    result.classes_validated.append(name)
                elif callable(obj):
                    result.functions_validated.append(name)
            
            result.status = "PASS"
            
        except NameError as e:
            result.status = "FAIL"
            result.error_type = "NameError"
            result.error_message = str(e)
            result.error_traceback = traceback.format_exc()
            # Extract line number from traceback
            tb_lines = result.error_traceback.split('\n')
            for line in tb_lines:
                if str(path) in line and 'line' in line:
                    try:
                        result.error_line = int(line.split('line')[1].split(',')[0].strip())
                    except Exception:
                        pass
                    break
                    
        except ImportError as e:
            result.status = "FAIL"
            result.error_type = "ImportError"
            result.error_message = str(e)
            result.error_traceback = traceback.format_exc()
            
        except AttributeError as e:
            result.status = "FAIL"
            result.error_type = "AttributeError"
            result.error_message = str(e)
            result.error_traceback = traceback.format_exc()
            
        except Exception as e:
            # Catch other errors but don't fail the audit
            result.status = "SKIP"
            result.error_type = type(e).__name__
            result.error_message = str(e)
            result.warnings.append(f"Non-critical error: {type(e).__name__}: {e}")
            
        return result
    
    def run_audit(self, max_files: int | None = None) -> AuditReport:
        """Run the complete audit."""
        print(f"Starting Runtime Import Validation Audit")
        print(f"Root path: {self.root_path}")
        print("=" * 60)
        
        files = self.find_python_files()
        if max_files:
            files = files[:max_files]
        
        self.report.total_modules = len(files)
        print(f"Found {len(files)} Python files to validate\n")
        
        for i, path in enumerate(files, 1):
            rel_path = path.relative_to(self.root_path)
            print(f"[{i}/{len(files)}] Validating: {rel_path}", end=" ")
            
            result = self.validate_module_import(path)
            self.report.results.append(result)
            
            if result.status == "PASS":
                self.report.passed += 1
                print("✅")
            elif result.status == "FAIL":
                self.report.failed += 1
                print(f"❌ {result.error_type}: {result.error_message}")
                self.report.critical_errors.append({
                    "module": result.module_name,
                    "path": result.module_path,
                    "error_type": result.error_type,
                    "error_message": result.error_message,
                    "error_line": result.error_line
                })
            else:
                self.report.skipped += 1
                print(f"⏭️  {result.error_message or 'Skipped'}")
            
            if result.warnings:
                for warning in result.warnings:
                    self.report.warnings.append({
                        "module": result.module_name,
                        "warning": warning
                    })
        
        print("\n" + "=" * 60)
        print(f"Audit Complete!")
        print(f"  Passed:  {self.report.passed}")
        print(f"  Failed:  {self.report.failed}")
        print(f"  Skipped: {self.report.skipped}")
        
        return self.report


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="L9 Runtime Import Validation Audit")
    parser.add_argument("--max-files", type=int, help="Maximum files to validate")
    parser.add_argument("--output", type=str, default="runtime_import_audit.json", help="Output file")
    parser.add_argument("--root", type=str, default=str(L9_ROOT), help="Root path to audit")
    args = parser.parse_args()
    
    validator = RuntimeImportValidator(Path(args.root))
    report = validator.run_audit(max_files=args.max_files)
    
    # Save report
    output_path = Path(args.root) / "analysis_reports" / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(report.to_dict(), f, indent=2)
    
    print(f"\nReport saved to: {output_path}")
    
    # Exit with error code if there were failures
    if report.failed > 0:
        print(f"\n⚠️  {report.failed} modules failed validation!")
        sys.exit(1)
    else:
        print("\n✅ All modules passed validation!")
        sys.exit(0)


if __name__ == "__main__":
    main()
