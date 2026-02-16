"""
Workers Test Configuration
==========================

Fixtures for testing workers package.
"""

import sys
from pathlib import Path

# Ensure project root is in path BEFORE any other imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Now verify the import works
try:
    import workers  # noqa: F401 — pre-import for pytest
except ImportError as e:
    print(f"WARNING: Failed to import workers: {e}")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"sys.path: {sys.path[:5]}")
