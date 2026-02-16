"""
Test fixtures for tests/unit.

Pre-imports agents.l_cto to ensure module is available for pytest imports.
"""

# Pre-import agents.l_cto for L-CTO bootstrap tests
# (fixes ModuleNotFoundError in test_lcto_bootstrap.py)
try:
    import agents.l_cto  # noqa: F401 — pre-import for pytest
except ImportError:
    pass  # Will be handled as test failure where needed
