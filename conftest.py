"""
L9 Root Test Configuration
==========================

This conftest.py at the project root ensures PYTHONPATH is set correctly
before any test imports happen.
"""

import os
import sys
import warnings
from pathlib import Path

# Suppress urllib3 NotOpenSSLWarning (macOS system Python uses LibreSSL)
# Fix: Recreate venv with Homebrew Python (/opt/homebrew/bin/python3)
# Must filter by message BEFORE urllib3 is imported (warning fires at import time)
warnings.filterwarnings("ignore", message=".*urllib3.*OpenSSL.*")

# Add project root to path BEFORE any other imports
# Use realpath to resolve any case sensitivity issues on macOS
PROJECT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT_STR = os.path.realpath(str(PROJECT_ROOT))

# Ensure the path is at the front of sys.path
if PROJECT_ROOT_STR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_STR)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Pre-import core.packet_envelope to ensure it's available
try:
    import core.packet_envelope
except ImportError:
    pass  # Will be reported as test failure

# Pre-import api.routes.registry for pytest router registry tests
try:
    import api.routes.registry  # noqa: F401
except ImportError:
    pass  # Will be handled as test failure where needed

# Pre-import clients.memory_client for pytest research integration tests
try:
    import clients.memory_client  # noqa: F401
except ImportError:
    pass  # Will be handled as test failure where needed

# Pre-import memory.graph_client to ensure it's available for lazy imports
# in core.agents.bootstrap phases (fixes pytest import resolution)
try:
    import memory.graph_client  # noqa: F401
except ImportError:
    pass  # Will be handled as test failure where needed

# Pre-import runtime.kernel_state and runtime.execution_gate for pytest
# (fixes ModuleNotFoundError in kernel runtime tests)
try:
    import runtime.execution_gate  # noqa: F401
    import runtime.kernel_state  # noqa: F401
except ImportError:
    pass  # Will be handled as test failure where needed

# Pre-import agents.l_cto for pytest
# (fixes ModuleNotFoundError in L-CTO bootstrap tests)
# NOTE: tests/core/agents/ renamed to tests/core/bootstrap/ to avoid namespace collision
try:
    import agents.l_cto  # noqa: F401
except ImportError:
    pass  # Will be handled as test failure where needed

# Pre-import ir_engine.meta_ir for pytest
# (fixes ModuleNotFoundError in CodeGenAgent tests)
try:
    import ir_engine.meta_ir  # noqa: F401
except ImportError:
    pass  # Will be handled as test failure where needed

# Pre-import codegen.symbolic for pytest
# (fixes ModuleNotFoundError in symbolic verification tests)
try:
    import codegen.symbolic  # noqa: F401
except ImportError:
    pass  # Will be handled as test failure where needed

# Pre-import auto-wiring registries for pytest
# (fixes ModuleNotFoundError in Phase 3/4 auto-wiring tests)
# Note: Use importlib.util to import directly from files to avoid
# triggering package __init__.py imports which may have other issues
try:
    import importlib.util

    def _import_from_file(module_name: str, file_path: str):
        """Import a module directly from a file path."""
        spec = importlib.util.spec_from_file_location(
            module_name, PROJECT_ROOT / file_path
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

    # Import registries directly from their files
    _import_from_file(
        "collaborative_cells.cell_registry", "collaborative_cells/cell_registry.py"
    )
    _import_from_file(
        "core.schemas.upcaster_registry", "core/schemas/upcaster_registry.py"
    )
    _import_from_file(
        "core.governance.policy_registry", "core/governance/policy_registry.py"
    )
    _import_from_file("runtime.tool_registry", "runtime/tool_registry.py")
    _import_from_file("runtime.mcp_server_registry", "runtime/mcp_server_registry.py")
    _import_from_file("agents.agent_registry", "agents/agent_registry.py")
    _import_from_file(
        "orchestrators.orchestrator_registry", "orchestrators/orchestrator_registry.py"
    )
except Exception:
    pass  # Will be handled as test failure where needed
