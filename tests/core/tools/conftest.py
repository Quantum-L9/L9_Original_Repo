"""
L9 Core Tools Tests - Configuration
====================================

Ensures proper path setup for tool graph imports.
"""

import sys
from pathlib import Path

# Add project root to path BEFORE any imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
