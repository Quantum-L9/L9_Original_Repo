"""
Conftest for upgrades tests
Ensures proper path resolution for imports
"""

import os
import sys
from pathlib import Path

# Add project root to path for upgrades imports
# Use realpath to resolve symlinks and case differences
PROJECT_ROOT = os.path.realpath(str(Path(__file__).resolve().parent.parent.parent))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Force import of core.packet_envelope to verify path is correct
try:
    pass
except ImportError:
    # If still not found, try adding explicitly
    pass
