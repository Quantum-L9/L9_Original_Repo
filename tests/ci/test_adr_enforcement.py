"""
L9 CI Tests - ADR Enforcement Tests (Revised for L9)
======================================================

Enforces compliance with design patterns documented in L9 ADRs.

**Test Categories**:
11. Singleton pattern compliance (ADR-0004) - HIGH
12. Decorator metadata preservation - CRITICAL
13. Direct agent communication (ADR-0060) - HIGH
14. Complex subsystem access (ADR-0061) - MEDIUM
15. Factory function inconsistency - LOW (Informational)
16. Missing singleton registration (ADR-0004) - MEDIUM
17. Observer pattern opportunity - LOW (Informational)

**Reference**: ADRs in readme/adr/

Version: 2.0.0 (Revised for L9 singleton pattern)
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Tuple

import pytest


# ============================================================================
# Configuration
# ============================================================================

# Directories to scan
CORE_MODULES = [
    "core",
    "memory",
    "orchestration",
    "runtime",
    "api",
    "agents",
]

# Allowed exceptions
ALLOWED_EXCEPTIONS = {
    "manual_singleton": [
        "tests/",
        "scripts/",
        "_archived/",
    ],
    "decorator_without_wraps": [
        "tests/",
        "scripts/",
    ],
    "direct_agent_communication": [
        "orchestration/",  # Orchestrators can call agents directly
        "tests/",
        "core/agents/executor",  # Executor calls agents
    ],
    "complex_subsystem_access": [
        "core/",  # Core modules can access subsystems
        "tests/",
        "api/",  # API routes need subsystem access
    ],
    "factory_naming": [
        "tests/",
    ],
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_python_files(directories: List[str]) -> List[Path]:
    """
    Get all Python files in specified directories.
    
    Args:
        directories: List of directory paths to scan
    
    Returns:
        List of Path objects for Python files
    """
    repo_root = Path(__file__).parent.parent.parent
    python_files = []
    
    for directory in directories:
        dir_path = repo_root / directory
        if dir_path.exists():
            python_files.extend(dir_path.rglob("*.py"))
    
    return python_files


def is_allowed_exception(file_path: Path, exception_type: str) -> bool:
    """
    Check if file is in allowed exceptions list.
    
    Args:
        file_path: Path to file
        exception_type: Type of exception
    
    Returns:
        True if file is allowed exception
    """
    file_str = str(file_path)
    allowed = ALLOWED_EXCEPTIONS.get(exception_type, [])
    
    return any(pattern in file_str for pattern in allowed)


def parse_python_file(file_path: Path) -> Tuple[ast.Module | None, str]:
    """
    Parse Python file into AST.
    
    Args:
        file_path: Path to Python file
    
    Returns:
        Tuple of (AST module, file content)
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
        return tree, content
    except (SyntaxError, UnicodeDecodeError):
        # Skip files with syntax errors or encoding issues
        return None, ""


# ============================================================================
# Test 11: Singleton Pattern Compliance (ADR-0004)
# ============================================================================

class ManualSingletonVisitor(ast.NodeVisitor):
    """
    Detect manual singleton implementations.
    
    Anti-pattern:
        class ConfigManager:
            _instance = None
            def __new__(cls):
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                return cls._instance
    
    Correct L9 pattern:
        @register_singleton(category="core", lifecycle=SingletonLifecycle.LAZY, ...)
        async def get_config_manager() -> ConfigManager:
            ...
    """
    
    def __init__(self):
        self.violations = []
    
    def visit_ClassDef(self, node):
        has_instance_var = False
        has_new_method = False
        has_singleton_decorator = False
        
        # Check for @singleton or @register_singleton decorator
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id in ("singleton", "register_singleton"):
                has_singleton_decorator = True
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == "register_singleton":
                    has_singleton_decorator = True
        
        # Check for _instance class variable
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "_instance":
                        has_instance_var = True
            
            # Check for __new__ method
            if isinstance(item, ast.FunctionDef) and item.name == "__new__":
                has_new_method = True
        
        # Violation: Manual singleton without decorator
        if has_instance_var and has_new_method and not has_singleton_decorator:
            self.violations.append({
                "line": node.lineno,
                "class_name": node.name,
                "pattern": "Manual singleton implementation"
            })
        
        self.generic_visit(node)


def test_no_manual_singleton_implementation():
    """
    Test 11: Detect manual singleton implementations.
    
    Severity: 🟠 HIGH
    ADR: ADR-0004 (Singleton Auto-Registry Pattern)
    
    Anti-pattern:
        class ConfigManager:
            _instance = None
            def __new__(cls): ...
    
    L9 Fix:
        from core.singleton_auto_registry import register_singleton
        from core.singleton_registry import SingletonLifecycle
        
        @register_singleton(
            category="core",
            lifecycle=SingletonLifecycle.LAZY,
            description="Configuration manager"
        )
        async def get_config_manager() -> ConfigManager:
            ...
    """
    python_files = get_python_files(CORE_MODULES)
    violations = []
    
    for file_path in python_files:
        if is_allowed_exception(file_path, "manual_singleton"):
            continue
        
        tree, content = parse_python_file(file_path)
        if tree is None:
            continue
        
        visitor = ManualSingletonVisitor()
        visitor.visit(tree)
        
        if visitor.violations:
            violations.append({
                "file": str(file_path),
                "violations": visitor.violations
            })
    
    if violations:
        error_msg = "🟠 HIGH: Manual singleton implementation detected (ADR-0004)\n\n"
        for item in violations:
            error_msg += f"File: {item['file']}\n"
            for v in item['violations']:
                error_msg += f"  Line {v['line']}: {v['class_name']} - {v['pattern']}\n"
        error_msg += "\nFix: Use @register_singleton decorator from core.singleton_auto_registry\n"
        error_msg += "See: ADR-0004 (Singleton Auto-Registry Pattern)\n"
        pytest.fail(error_msg)


# ============================================================================
# Test 12: Decorator Metadata Preservation
# ============================================================================

class DecoratorWithoutWrapsVisitor(ast.NodeVisitor):
    """
    Detect decorators without @wraps.
    
    Anti-pattern:
        def my_decorator(func):
            async def wrapper(*args, **kwargs):  # ❌ Missing @wraps
                return await func(*args, **kwargs)
            return wrapper
    
    Correct pattern:
        from functools import wraps
        
        def my_decorator(func):
            @wraps(func)  # ✅
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            return wrapper
    """
    
    def __init__(self):
        self.violations = []
    
    def visit_FunctionDef(self, node):
        self._check_decorator(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        self._check_decorator(node)
        self.generic_visit(node)
    
    def _check_decorator(self, node):
        # Check if function returns another function (decorator pattern)
        returns_function = False
        inner_functions = []
        
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                inner_functions.append(item)
            elif isinstance(item, ast.Return):
                if isinstance(item.value, ast.Name):
                    returns_function = True
        
        # If function has inner function and returns it, it's likely a decorator
        if inner_functions and returns_function:
            for inner in inner_functions:
                # Check if inner function has @wraps decorator
                has_wraps = any(
                    (isinstance(d, ast.Name) and d.id == "wraps") or
                    (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "wraps")
                    for d in inner.decorator_list
                )
                
                if not has_wraps:
                    self.violations.append({
                        "line": node.lineno,
                        "decorator_name": node.name,
                        "inner_function": inner.name,
                        "pattern": "Decorator without @wraps"
                    })


def test_decorator_metadata_preservation():
    """
    Test 12: Detect decorators without @wraps.
    
    Severity: 🔴 CRITICAL
    ADR: ADR-0010 (must_stay_async Decorator) - related pattern
    
    Anti-pattern:
        def my_decorator(func):
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            return wrapper
    
    Fix:
        from functools import wraps
        
        def my_decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            return wrapper
    """
    python_files = get_python_files(CORE_MODULES)
    violations = []
    
    for file_path in python_files:
        if is_allowed_exception(file_path, "decorator_without_wraps"):
            continue
        
        tree, content = parse_python_file(file_path)
        if tree is None:
            continue
        
        visitor = DecoratorWithoutWrapsVisitor()
        visitor.visit(tree)
        
        if visitor.violations:
            violations.append({
                "file": str(file_path),
                "violations": visitor.violations
            })
    
    if violations:
        error_msg = "🔴 CRITICAL: Decorator without @wraps detected\n\n"
        for item in violations:
            error_msg += f"File: {item['file']}\n"
            for v in item['violations']:
                error_msg += f"  Line {v['line']}: {v['decorator_name']}() -> {v['inner_function']}()\n"
        error_msg += "\nFix: Add @wraps(func) to inner function\n"
        pytest.fail(error_msg)


# ============================================================================
# Test 13: Direct Agent Communication (ADR-0060)
# ============================================================================

class DirectAgentCommunicationVisitor(ast.NodeVisitor):
    """
    Detect direct agent-to-agent communication.
    
    Anti-pattern:
        result = await coder_agent.execute(task)  # ❌ Direct coupling
    
    Correct pattern (ADR-0060):
        from core.coordination.agent_mediator import get_agent_mediator
        
        mediator = await get_agent_mediator()
        await mediator.send_message(
            from_agent="research",
            to_agent="coder",
            message={"task": task}
        )
    """
    
    def __init__(self):
        self.violations = []
    
    def visit_Call(self, node):
        # Look for: agent_var.execute() or agent_var.run()
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            
            # Check if calling agent methods
            if method_name in ["execute", "run", "process"]:
                # Check if variable name suggests it's an agent
                if isinstance(node.func.value, ast.Name):
                    var_name = node.func.value.id
                    
                    if "agent" in var_name.lower() and var_name != "self":
                        self.violations.append({
                            "line": node.lineno,
                            "pattern": f"Direct agent call: {var_name}.{method_name}()"
                        })
        
        self.generic_visit(node)


def test_no_direct_agent_communication():
    """
    Test 13: Detect direct agent-to-agent communication.
    
    Severity: 🟠 HIGH
    ADR: ADR-0060 (Mediator Pattern for Agent Communication)
    
    Anti-pattern:
        result = await coder_agent.execute(task)
    
    Fix:
        from core.coordination.agent_mediator import get_agent_mediator
        
        mediator = await get_agent_mediator()
        await mediator.send_message(
            from_agent="research",
            to_agent="coder",
            message={"task": task}
        )
    """
    python_files = get_python_files(CORE_MODULES)
    violations = []
    
    for file_path in python_files:
        if is_allowed_exception(file_path, "direct_agent_communication"):
            continue
        
        tree, content = parse_python_file(file_path)
        if tree is None:
            continue
        
        visitor = DirectAgentCommunicationVisitor()
        visitor.visit(tree)
        
        if visitor.violations:
            violations.append({
                "file": str(file_path),
                "violations": visitor.violations
            })
    
    if violations:
        error_msg = "🟠 HIGH: Direct agent communication detected (ADR-0060)\n\n"
        for item in violations:
            error_msg += f"File: {item['file']}\n"
            for v in item['violations']:
                error_msg += f"  Line {v['line']}: {v['pattern']}\n"
        error_msg += "\nFix: Use AgentMediator for agent-to-agent communication\n"
        error_msg += "See: ADR-0060 (Mediator Pattern for Agent Communication)\n"
        pytest.fail(error_msg)


# ============================================================================
# Test 14: Complex Subsystem Access (ADR-0061)
# ============================================================================

class ComplexSubsystemAccessVisitor(ast.NodeVisitor):
    """
    Detect complex subsystem access without facade (informational).
    
    Note: This is informational only. Internal modules legitimately
    access subsystems directly. The L9Facade is for external/simple use.
    """
    
    def __init__(self):
        self.violations = []
    
    def visit_ImportFrom(self, node):
        # This check is informational only - many legitimate internal uses
        # Just track imports from deep internal modules
        deep_internal = [
            "core.agents.executor_service",
            "memory.substrate_service",
            "orchestration.unified_controller",
        ]
        
        if node.module in deep_internal:
            self.violations.append({
                "line": node.lineno,
                "module": node.module,
                "pattern": "Deep subsystem import (consider L9Facade for simple use cases)"
            })
        
        self.generic_visit(node)


def test_complex_subsystem_access_informational():
    """
    Test 14: Detect complex subsystem access (INFORMATIONAL).
    
    Severity: 🟢 LOW (Informational)
    ADR: ADR-0061 (L9 Facade Pattern for Simplified API)
    
    Note: Many internal modules legitimately access subsystems directly.
    This test is informational to encourage using L9Facade for simple cases.
    
    Simple use case fix:
        from core.facade import get_l9_facade
        
        l9 = await get_l9_facade()
        result = await l9.run_task("Research async patterns")
    """
    python_files = get_python_files(CORE_MODULES)
    suggestions = []
    
    for file_path in python_files:
        if is_allowed_exception(file_path, "complex_subsystem_access"):
            continue
        
        tree, content = parse_python_file(file_path)
        if tree is None:
            continue
        
        visitor = ComplexSubsystemAccessVisitor()
        visitor.visit(tree)
        
        if visitor.violations:
            suggestions.append({
                "file": str(file_path),
                "violations": visitor.violations
            })
    
    if suggestions:
        info_msg = "\n🟢 LOW: Deep subsystem imports detected (consider L9Facade - ADR-0061)\n\n"
        for item in suggestions[:5]:  # Limit to first 5
            info_msg += f"File: {item['file']}\n"
            for v in item['violations']:
                info_msg += f"  Line {v['line']}: {v['module']}\n"
        if len(suggestions) > 5:
            info_msg += f"\n... and {len(suggestions) - 5} more\n"
        info_msg += "\nNote: Internal modules may legitimately need direct access.\n"
        info_msg += "See: ADR-0061 (L9 Facade Pattern for Simplified API)\n"
        
        # Skip test with informational message (not a failure)
        pytest.skip(info_msg)


# ============================================================================
# Test 15: Factory Function Naming (Informational)
# ============================================================================

def test_factory_function_naming_informational():
    """
    Test 15: Report factory function count (INFORMATIONAL).
    
    Severity: 🟢 LOW (Informational)
    
    L9 uses factory functions throughout. This test reports counts
    for visibility but does not fail.
    """
    python_files = get_python_files(CORE_MODULES)
    
    factory_patterns = {
        "create_": [],
        "build_": [],
        "make_": [],
        "get_": []
    }
    
    for file_path in python_files:
        if is_allowed_exception(file_path, "factory_naming"):
            continue
        
        tree, content = parse_python_file(file_path)
        if tree is None:
            continue
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for prefix in factory_patterns.keys():
                    if node.name.startswith(prefix):
                        factory_patterns[prefix].append({
                            "file": str(file_path),
                            "line": node.lineno,
                            "function": node.name
                        })
    
    # Report counts (informational)
    total = sum(len(v) for v in factory_patterns.values())
    
    info_msg = f"\n🟢 LOW: Factory function summary ({total} total)\n\n"
    for prefix, functions in factory_patterns.items():
        if functions:
            info_msg += f"  {prefix}*: {len(functions)} functions\n"
    info_msg += "\nNote: L9 uses DI container for service creation (see ADR-0004)\n"
    
    # Always skip with informational message
    pytest.skip(info_msg)


# ============================================================================
# Test 16: Missing Singleton Registration (ADR-0004)
# ============================================================================

class MissingSingletonVisitor(ast.NodeVisitor):
    """
    Detect classes that should be singletons (heuristic).
    
    Checks for classes with names ending in Manager/Registry/Service/Client
    that have instance state but no @register_singleton getter.
    """
    
    def __init__(self, content: str):
        self.violations = []
        self.content = content
    
    def visit_ClassDef(self, node):
        # Check if class name suggests singleton
        singleton_suffixes = ["Manager", "Registry", "Service", "Client", "Cache"]
        
        should_be_singleton = any(
            node.name.endswith(suffix) for suffix in singleton_suffixes
        )
        
        if not should_be_singleton:
            self.generic_visit(node)
            return
        
        # Check if file has @register_singleton for this class type
        # L9 pattern: @register_singleton on async getter function, not class
        has_register_singleton = f"@register_singleton" in self.content and node.name.lower() in self.content.lower()
        
        if has_register_singleton:
            self.generic_visit(node)
            return
        
        # Check if class has __init__ with instance state
        has_init_with_state = False
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                # Check for self.* assignments
                for subitem in ast.walk(item):
                    if isinstance(subitem, ast.Assign):
                        for target in subitem.targets:
                            if isinstance(target, ast.Attribute):
                                if isinstance(target.value, ast.Name) and target.value.id == "self":
                                    has_init_with_state = True
                                    break
        
        if has_init_with_state:
            self.violations.append({
                "line": node.lineno,
                "class_name": node.name,
                "pattern": "Class should have @register_singleton getter"
            })
        
        self.generic_visit(node)


def test_missing_singleton_registration():
    """
    Test 16: Detect classes that should have singleton getters.
    
    Severity: 🟡 MEDIUM
    ADR: ADR-0004 (Singleton Auto-Registry Pattern)
    
    L9 Pattern:
        class CacheManager:
            def __init__(self):
                self.cache = {}
        
        @register_singleton(
            category="memory",
            lifecycle=SingletonLifecycle.LAZY,
            description="Cache manager singleton"
        )
        async def get_cache_manager() -> CacheManager:
            global _instance
            if _instance is None:
                _instance = CacheManager()
            return _instance
    """
    python_files = get_python_files(CORE_MODULES)
    violations = []
    
    for file_path in python_files:
        if is_allowed_exception(file_path, "manual_singleton"):
            continue
        
        tree, content = parse_python_file(file_path)
        if tree is None:
            continue
        
        visitor = MissingSingletonVisitor(content)
        visitor.visit(tree)
        
        if visitor.violations:
            violations.append({
                "file": str(file_path),
                "violations": visitor.violations
            })
    
    if violations:
        warning_msg = "\n🟡 MEDIUM: Classes that may need @register_singleton getter (ADR-0004)\n\n"
        for item in violations[:10]:  # Limit to first 10
            warning_msg += f"File: {item['file']}\n"
            for v in item['violations']:
                warning_msg += f"  Line {v['line']}: {v['class_name']}\n"
        if len(violations) > 10:
            warning_msg += f"\n... and {len(violations) - 10} more\n"
        warning_msg += "\nFix: Add @register_singleton getter function\n"
        warning_msg += "See: ADR-0004 (Singleton Auto-Registry Pattern)\n"
        
        # Skip with warning (many legitimate non-singletons)
        pytest.skip(warning_msg)


# ============================================================================
# Test 17: Observer Pattern Opportunity (Informational)
# ============================================================================

class PollingPatternVisitor(ast.NodeVisitor):
    """
    Detect polling patterns (suggest Observer pattern).
    
    Anti-pattern:
        while True:
            status = agent.get_status()
            if status == "completed":
                break
            await asyncio.sleep(1)
    """
    
    def __init__(self):
        self.suggestions = []
    
    def visit_While(self, node):
        # Check for while True loops
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            # Check for asyncio.sleep in loop
            has_sleep = False
            has_status_check = False
            
            for item in ast.walk(node):
                if isinstance(item, ast.Call):
                    if isinstance(item.func, ast.Attribute):
                        if item.func.attr == "sleep":
                            has_sleep = True
                        if "status" in item.func.attr.lower() or "state" in item.func.attr.lower():
                            has_status_check = True
            
            if has_sleep and has_status_check:
                self.suggestions.append({
                    "line": node.lineno,
                    "pattern": "Polling loop detected"
                })
        
        self.generic_visit(node)


def test_observer_pattern_opportunity():
    """
    Test 17: Detect polling patterns (INFORMATIONAL).
    
    Severity: 🟢 LOW (Informational)
    
    Anti-pattern:
        while True:
            status = agent.get_status()
            if status == "completed":
                break
            await asyncio.sleep(1)
    
    Future pattern:
        agent.subscribe(observer)
    """
    python_files = get_python_files(CORE_MODULES)
    suggestions = []
    
    for file_path in python_files:
        tree, content = parse_python_file(file_path)
        if tree is None:
            continue
        
        visitor = PollingPatternVisitor()
        visitor.visit(tree)
        
        if visitor.suggestions:
            suggestions.append({
                "file": str(file_path),
                "suggestions": visitor.suggestions
            })
    
    if suggestions:
        info_msg = "\n🟢 LOW: Polling patterns detected (consider Observer pattern)\n\n"
        for item in suggestions:
            info_msg += f"File: {item['file']}\n"
            for s in item['suggestions']:
                info_msg += f"  Line {s['line']}: {s['pattern']}\n"
        info_msg += "\nFuture: Consider Observer pattern for event-driven monitoring\n"
        
        pytest.skip(info_msg)


# ============================================================================
# Summary Test
# ============================================================================

def test_adr_enforcement_summary():
    """
    Summary test: Run all ADR enforcement checks and report counts.
    
    This test always passes but provides visibility into ADR compliance.
    """
    python_files = get_python_files(CORE_MODULES)
    
    # Count violations
    counts = {
        "manual_singleton": 0,
        "decorator_without_wraps": 0,
        "direct_agent_communication": 0,
        "complex_subsystem_access": 0,
        "factory_functions": 0,
        "missing_singleton": 0,
        "polling_patterns": 0,
    }
    
    for file_path in python_files:
        tree, content = parse_python_file(file_path)
        if tree is None or not content:
            continue
        
        # Count manual singletons
        if not is_allowed_exception(file_path, "manual_singleton"):
            visitor = ManualSingletonVisitor()
            visitor.visit(tree)
            counts["manual_singleton"] += len(visitor.violations)
        
        # Count decorators without wraps
        if not is_allowed_exception(file_path, "decorator_without_wraps"):
            visitor = DecoratorWithoutWrapsVisitor()
            visitor.visit(tree)
            counts["decorator_without_wraps"] += len(visitor.violations)
        
        # Count direct agent communication
        if not is_allowed_exception(file_path, "direct_agent_communication"):
            visitor = DirectAgentCommunicationVisitor()
            visitor.visit(tree)
            counts["direct_agent_communication"] += len(visitor.violations)
        
        # Count complex subsystem access
        if not is_allowed_exception(file_path, "complex_subsystem_access"):
            visitor = ComplexSubsystemAccessVisitor()
            visitor.visit(tree)
            counts["complex_subsystem_access"] += len(visitor.violations)
        
        # Count factory functions
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if any(node.name.startswith(p) for p in ["create_", "build_", "make_", "get_"]):
                    counts["factory_functions"] += 1
        
        # Count missing singletons
        if not is_allowed_exception(file_path, "manual_singleton"):
            visitor = MissingSingletonVisitor(content)
            visitor.visit(tree)
            counts["missing_singleton"] += len(visitor.violations)
        
        # Count polling patterns
        visitor = PollingPatternVisitor()
        visitor.visit(tree)
        counts["polling_patterns"] += len(visitor.suggestions)
    
    # Print summary (always passes)
    print("\n" + "=" * 60)
    print("ADR Enforcement Summary (L9 Aligned)")
    print("=" * 60)
    print(f"🟠 Manual singleton impl:      {counts['manual_singleton']} (ADR-0004)")
    print(f"🔴 Decorator without @wraps:   {counts['decorator_without_wraps']}")
    print(f"🟠 Direct agent communication: {counts['direct_agent_communication']} (ADR-0060)")
    print(f"🟢 Complex subsystem access:   {counts['complex_subsystem_access']} (ADR-0061)")
    print(f"🟢 Factory functions:          {counts['factory_functions']} (informational)")
    print(f"🟡 Missing singleton getter:   {counts['missing_singleton']} (ADR-0004)")
    print(f"🟢 Polling patterns:           {counts['polling_patterns']} (informational)")
    print("=" * 60)
    
    # Only count real violations
    real_violations = (
        counts["manual_singleton"] +
        counts["decorator_without_wraps"] +
        counts["direct_agent_communication"]
    )
    print(f"Real violations: {real_violations}")
    print(f"Informational: {sum(counts.values()) - real_violations}")
    print("=" * 60 + "\n")
