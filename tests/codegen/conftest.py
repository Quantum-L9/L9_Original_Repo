"""
CodeGen Tests Configuration
===========================

Test fixtures specific to CodeGenAgent tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure project root is in path before any other imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
