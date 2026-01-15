"""
L9 Root Test Configuration
==========================

This conftest.py at the project root ensures PYTHONPATH is set correctly
before any test imports happen.
"""

import sys
import os
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

# Pre-import memory.graph_client to ensure it's available for lazy imports
# in core.agents.bootstrap phases (fixes pytest import resolution)
try:
    import memory.graph_client  # noqa: F401
except ImportError:
    pass  # Will be handled as test failure where needed

# Pre-import runtime.kernel_state and runtime.execution_gate for pytest
# (fixes ModuleNotFoundError in kernel runtime tests)
try:
    import runtime.kernel_state  # noqa: F401
    import runtime.execution_gate  # noqa: F401
except ImportError:
    pass  # Will be handled as test failure where needed

# Pre-import agents.l_cto for pytest
# (fixes ModuleNotFoundError in L-CTO bootstrap tests)
# NOTE: tests/core/agents/ renamed to tests/core/bootstrap/ to avoid namespace collision
try:
    import agents.l_cto  # noqa: F401
except ImportError:
    pass  # Will be handled as test failure where needed
