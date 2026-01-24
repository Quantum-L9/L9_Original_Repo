"""
L9 CI Tests - ADR Enforcement Tests
====================================

Enforces compliance with design patterns documented in ADRs 0056-0062.

**Test Categories**:
11. Singleton pattern compliance (ADR-0056) - HIGH
12. Decorator metadata preservation (ADR-0057) - CRITICAL
13. Direct agent communication (ADR-0058) - HIGH
14. Complex subsystem access (ADR-0059) - MEDIUM
15. Factory function inconsistency (ADR-0062) - MEDIUM
16. Missing singleton registration (ADR-0056) - MEDIUM
17. Observer pattern opportunity (ADR-0060) - LOW (Informational)

**Reference**: ADRs 0056-0062 in docs/architecture/decisions/

Version: 1.0.0
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
    ],
    "decorator_without_wraps": [
        "tests/",
        "scripts/",
    ],
    "direct_agent_communication": [
        "orchestration/",  # Orchestrators can call agents directly
        "tests/",
    ],
    "complex_subsystem_access": [
        "core/",  # Core modules can access subsystems
        "tests/",
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


def parse_python_file(file_path: Path) -> Tuple[ast.Module, str]:
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
# Test 11: Singleton Pattern Compliance (ADR-0056)
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
    
    Correct pattern:
        @singleton
        class ConfigManager:
            ...
    """
    
    def __init__(self):
        self.violations = []
    
    def visit_ClassDef(self, node):
        has_instance_var = False
        has_new_method = False
        has_singleton_decorator = False
        
        # Check for @singleton decorator
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "singleton":
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
        
        # Violation: Manual singleton without @singleton decorator
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
    ADR: ADR-0056 (Singleton Class Decorator Pattern)
    
    Anti-pattern:
        class ConfigManager:
            _instance = None
            def __new__(cls): ...
    
    Fix:
        from core.patterns.singleton import singleton
        
        @singleton
        class ConfigManager:
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
        error_msg = "🟠 HIGH: Manual singleton implementation detected (ADR-0056)\n\n"
        for item in violations:
            error_msg += f"File: {item['file']}\n"
            for v in item['violations']:
                error_msg += f"  Line {v['line']}: {v['class_name']} - {v['pattern']}\n"
        error_msg += "\nFix: Use @singleton decorator from core.patterns.singleton\n"
        error_msg += "See: ADR-0056 (Singleton Class Decorator Pattern)\n"
        pytest.fail(error_msg)


# ============================================================================
# Test 12: Decorator Metadata Preservation (ADR-0057)
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
        # Check if function returns another function (decorator pattern)
        returns_function = False
        inner_functions = []
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
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
        
        self.generic_visit(node)


def test_decorator_metadata_preservation():
    """
    Test 12: Detect decorators without @wraps.
    
    Severity: 🔴 CRITICAL
    ADR: ADR-0057 (Decorator Metadata Preservation)
    
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
        error_msg = "🔴 CRITICAL: Decorator without @wraps detected (ADR-0057)\n\n"
        for item in violations:
            error_msg += f"File: {item['file']}\n"
            for v in item['violations']:
                error_msg += f"  Line {v['line']}: {v['decorator_name']}() -> {v['inner_function']}()\n"
        error_msg += "\nFix: Add @wraps(func) to inner function\n"
        error_msg += "See: ADR-0057 (Decorator Metadata Preservation)\n"
        pytest.fail(error_msg)


# ============================================================================
# Test 13: Direct Agent Communication (ADR-0058)
# ============================================================================

class DirectAgentCommunicationVisitor(ast.NodeVisitor):
    """
    Detect direct agent-to-agent communication.
    
    Anti-pattern:
        result = await coder_agent.execute(task)  # ❌ Direct coupling
    
    Correct pattern:
        await mediator.send_message(
            from_agent="research",
            to_agent="coder",
            message_type="code_request",
            payload={"task": task}
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
    ADR: ADR-0058 (Mediator Pattern for Agent Communication)
    
    Anti-pattern:
        result = await coder_agent.execute(task)
    
    Fix:
        from core.coordination.agent_mediator import AgentMediator
        
        mediator = AgentMediator()
        await mediator.send_message(
            from_agent="research",
            to_agent="coder",
            message_type="code_request",
            payload={"task": task}
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
        error_msg = "🟠 HIGH: Direct agent communication detected (ADR-0058)\n\n"
        for item in violations:
            error_msg += f"File: {item['file']}\n"
            for v in item['violations']:
                error_msg += f"  Line {v['line']}: {v['pattern']}\n"
        error_msg += "\nFix: Use AgentMediator for agent-to-agent communication\n"
        error_msg += "See: ADR-0058 (Mediator Pattern for Agent Communication)\n"
        pytest.fail(error_msg)


# ============================================================================
# Test 14: Complex Subsystem Access (ADR-0059)
# ============================================================================

class ComplexSubsystemAccessVisitor(ast.NodeVisitor):
    """
    Detect complex subsystem access without facade.
    
    Anti-pattern:
        from core.orchestration.graph_engine import GraphEngine
        engine = GraphEngine()
        result = await engine.run(...)
    
    Correct pattern:
        from core.facade.l9_facade import L9
        result = await L9.run_task("Research async patterns")
    """
    
    def __init__(self):
        self.violations = []
    
    def visit_ImportFrom(self, node):
        # Internal subsystems that should use facade
        internal_subsystems = [
            "core.orchestration.graph_engine",
            "core.agents.registry",
            "core.tools.executor",
            "core.memory.substrate_service"
        ]
        
        if node.module in internal_subsystems:
            self.violations.append({
                "line": node.lineno,
                "module": node.module,
                "pattern": "Direct subsystem import"
            })
        
        self.generic_visit(node)


def test_no_complex_subsystem_access():
    """
    Test 14: Detect complex subsystem access without facade.
    
    Severity: 🟡 MEDIUM
    ADR: ADR-0059 (Facade Pattern for Simplified L9 API)
    
    Anti-pattern:
        from core.orchestration.graph_engine import GraphEngine
        engine = GraphEngine()
    
    Fix:
        from core.facade.l9_facade import L9
        result = await L9.run_task("task description")
    """
    python_files = get_python_files(CORE_MODULES)
    violations = []
    
    for file_path in python_files:
        if is_allowed_exception(file_path, "complex_subsystem_access"):
            continue
        
        tree, content = parse_python_file(file_path)
        if tree is None:
            continue
        
        visitor = ComplexSubsystemAccessVisitor()
        visitor.visit(tree)
        
        if visitor.violations:
            violations.append({
                "file": str(file_path),
                "violations": visitor.violations
            })
    
    if violations:
        error_msg = "🟡 MEDIUM: Complex subsystem access detected (ADR-0059)\n\n"
        for item in violations:
            error_msg += f"File: {item['file']}\n"
            for v in item['violations']:
                error_msg += f"  Line {v['line']}: {v['module']}\n"
        error_msg += "\nFix: Use L9 facade for simplified API access\n"
        error_msg += "See: ADR-0059 (Facade Pattern for Simplified L9 API)\n"
        pytest.fail(error_msg)


# ============================================================================
# Test 15: Factory Function Inconsistency (ADR-0062)
# ============================================================================

def test_factory_function_naming_consistency():
    """
    Test 15: Detect inconsistent factory function naming.
    
    Severity: 🟡 MEDIUM
    ADR: ADR-0062 (Factory Pattern Consolidation - Deferred)
    
    Anti-pattern:
        def create_agent(...)  # Inconsistent prefixes
        def build_tool(...)
        def make_orchestrator(...)
    
    Future fix:
        from core.patterns.factory_registry import FactoryRegistry
        
        registry = FactoryRegistry()
        agent = await registry.get_factory("agent").create("research")
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
            if isinstance(node, ast.FunctionDef):
                for prefix in factory_patterns.keys():
                    if node.name.startswith(prefix):
                        factory_patterns[prefix].append({
                            "file": str(file_path),
                            "line": node.lineno,
                            "function": node.name
                        })
    
    # Report inconsistency
    total_factory_functions = sum(len(v) for v in factory_patterns.values())
    
    if total_factory_functions > 20:
        # Warn if too many informal factory functions
        warning_msg = f"\n🟡 MEDIUM: Found {total_factory_functions} factory functions (ADR-0062)\n\n"
        warning_msg += "Factory function prefixes:\n"
        for prefix, functions in factory_patterns.items():
            if functions:
                warning_msg += f"  {prefix}: {len(functions)} functions\n"
        warning_msg += "\nConsider consolidating into Factory classes (ADR-0062)\n"
        warning_msg += "See: ADR-0062 (Factory Pattern Consolidation)\n"
        
        pytest.skip(warning_msg)


# ============================================================================
# Test 16: Missing Singleton Registration (ADR-0056)
# ============================================================================

class MissingSingletonVisitor(ast.NodeVisitor):
    """
    Detect classes that should be singletons.
    
    Heuristic: Classes with names ending in Manager/Registry/Service/Client
    and having instance state should be singletons.
    """
    
    def __init__(self):
        self.violations = []
    
    def visit_ClassDef(self, node):
        # Check if class name suggests singleton
        singleton_suffixes = ["Manager", "Registry", "Service", "Client", "Cache"]
        
        should_be_singleton = any(
            node.name.endswith(suffix) for suffix in singleton_suffixes
        )
        
        if not should_be_singleton:
            self.generic_visit(node)
            return
        
        # Check if already has @singleton decorator
        has_singleton = any(
            isinstance(d, ast.Name) and d.id == "singleton"
            for d in node.decorator_list
        )
        
        if has_singleton:
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
                "pattern": "Class should be singleton (has state + singleton name)"
            })
        
        self.generic_visit(node)


def test_missing_singleton_registration():
    """
    Test 16: Detect classes that should be singletons.
    
    Severity: 🟡 MEDIUM
    ADR: ADR-0056 (Singleton Class Decorator Pattern)
    
    Anti-pattern:
        class CacheManager:  # Should be singleton
            def __init__(self):
                self.cache = {}
    
    Fix:
        from core.patterns.singleton import singleton
        
        @singleton
        class CacheManager:
            def __init__(self):
                self.cache = {}
    """
    python_files = get_python_files(CORE_MODULES)
    violations = []
    
    for file_path in python_files:
        if is_allowed_exception(file_path, "manual_singleton"):
            continue
        
        tree, content = parse_python_file(file_path)
        if tree is None:
            continue
        
        visitor = MissingSingletonVisitor()
        visitor.visit(tree)
        
        if visitor.violations:
            violations.append({
                "file": str(file_path),
                "violations": visitor.violations
            })
    
    if violations:
        error_msg = "🟡 MEDIUM: Classes that should be singletons detected (ADR-0056)\n\n"
        for item in violations:
            error_msg += f"File: {item['file']}\n"
            for v in item['violations']:
                error_msg += f"  Line {v['line']}: {v['class_name']} - {v['pattern']}\n"
        error_msg += "\nFix: Add @singleton decorator to classes with Manager/Registry/Service/Client suffix\n"
        error_msg += "See: ADR-0056 (Singleton Class Decorator Pattern)\n"
        pytest.fail(error_msg)


# ============================================================================
# Test 17: Observer Pattern Opportunity (ADR-0060)
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
    
    Future pattern:
        agent.subscribe(observer)
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
    Test 17: Detect polling patterns (suggest Observer pattern).
    
    Severity: 🟢 LOW (Informational)
    ADR: ADR-0060 (Observer Pattern for Agent Monitoring - Deferred)
    
    Anti-pattern:
        while True:
            status = agent.get_status()
            if status == "completed":
                break
            await asyncio.sleep(1)
    
    Future fix:
        from core.patterns.observer import AgentObserver
        
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
        info_msg = "\n🟢 LOW: Polling patterns detected (consider Observer pattern - ADR-0060)\n\n"
        for item in suggestions:
            info_msg += f"File: {item['file']}\n"
            for s in item['suggestions']:
                info_msg += f"  Line {s['line']}: {s['pattern']}\n"
        info_msg += "\nFuture: Consider implementing Observer pattern for event-driven monitoring\n"
        info_msg += "See: ADR-0060 (Observer Pattern for Agent Monitoring)\n"
        
        # Skip test with informational message
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
            if isinstance(node, ast.FunctionDef):
                if any(node.name.startswith(p) for p in ["create_", "build_", "make_", "get_"]):
                    counts["factory_functions"] += 1
        
        # Count missing singletons
        if not is_allowed_exception(file_path, "manual_singleton"):
            visitor = MissingSingletonVisitor()
            visitor.visit(tree)
            counts["missing_singleton"] += len(visitor.violations)
        
        # Count polling patterns
        visitor = PollingPatternVisitor()
        visitor.visit(tree)
        counts["polling_patterns"] += len(visitor.suggestions)
    
    # Print summary (always passes)
    print("\n" + "="*60)
    print("ADR Enforcement Summary")
    print("="*60)
    print(f"🟠 Manual singleton impl:      {counts['manual_singleton']} (ADR-0056)")
    print(f"🔴 Decorator without @wraps:   {counts['decorator_without_wraps']} (ADR-0057)")
    print(f"🟠 Direct agent communication: {counts['direct_agent_communication']} (ADR-0058)")
    print(f"🟡 Complex subsystem access:   {counts['complex_subsystem_access']} (ADR-0059)")
    print(f"🟡 Factory functions:          {counts['factory_functions']} (ADR-0062)")
    print(f"🟡 Missing singleton:          {counts['missing_singleton']} (ADR-0056)")
    print(f"🟢 Polling patterns:           {counts['polling_patterns']} (ADR-0060)")
    print("="*60)
    print(f"Total violations: {sum(counts.values())}")
    print("="*60 + "\n")
