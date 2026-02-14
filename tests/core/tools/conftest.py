"""
L9 Core Tools Tests - Configuration
====================================

Ensures proper path setup for tool graph imports.
"""

__dora_meta__ = {
    "component_name": "Conftest",
    "module_version": "1.0.0",
    "created_by": "Auto-fix ADR-0014",
    "created_at": "2026-02-13T23:37:34.997991+00:00",
    "updated_at": "2026-02-13T23:37:34.997991+00:00",
    "layer": "core",
    "domain": "tools",
    "module_name": "tests.core.tools.conftest",
    "type": "module",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}


import sys
from pathlib import Path

# Add project root to path BEFORE any imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
