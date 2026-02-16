#!/usr/bin/env python3
"""
Shim for /wire command to point to core/codegen/wire_executor.py
"""

import sys
from pathlib import Path

# Add workspace root to path
workspace = Path(__file__).parent.parent
if str(workspace) not in sys.path:
    sys.path.insert(0, str(workspace))

from core.codegen.wire_executor import main

if __name__ == "__main__":
    main()
