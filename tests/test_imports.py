"""
L9 Import Validation Tests
Version: 1.0.0

Verifies that all core modules can be imported without errors.
This catches:
- Missing dependencies
- Circular imports
- Syntax errors
- Module path issues

Run with: pytest tests/test_imports.py -v
"""

import importlib
import sys

import pytest

# Core modules that should always be importable
CORE_MODULES = [
    "api.server",
    "api.server_memory",
    "api.os_routes",
    "api.agent_routes",
    "api.memory.router",
    "api.db",
    "api.auth",
]

# Memory system modules
MEMORY_MODULES = [
    "memory.ingestion",
    "memory.substrate_service",
    "memory.substrate_models",
    "memory.migration_runner",
]

# Optional modules (may not exist in all configurations)
OPTIONAL_MODULES = [
    "core.agents.executor",
    "core.agents.schemas",
    "core.aios.runtime",
    "core.tools.registry_adapter",
    "world_model.repository",
    "services.research.research_api",
]


class TestCoreImports:
    """Verify core modules can be imported."""

    @pytest.mark.parametrize("module_name", CORE_MODULES)
    def test_core_module_imports(self, module_name: str):
        """
        Core modules must import without error.

        If this fails, the application cannot start.
        """
        try:
            module = importlib.import_module(module_name)
            assert module is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestMemoryImports:
    """Verify memory system modules can be imported."""

    @pytest.mark.parametrize("module_name", MEMORY_MODULES)
    def test_memory_module_imports(self, module_name: str):
        """
        Memory modules must import without error.

        Memory substrate is critical infrastructure.
        """
        try:
            module = importlib.import_module(module_name)
            assert module is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestOptionalImports:
    """Verify optional modules import when present."""

    @pytest.mark.parametrize("module_name", OPTIONAL_MODULES)
    def test_optional_module_imports(self, module_name: str):
        """
        Optional modules should import cleanly if they exist.

        These modules may not be present in all configurations,
        so we skip if the module doesn't exist.
        """
        try:
            module = importlib.import_module(module_name)
            assert module is not None
        except ImportError:
            pytest.skip(f"{module_name} not available (optional)")


class TestNoCircularImports:
    """Detect circular import issues."""

    def test_api_server_no_circular(self):
        """
        API server should not have circular imports.

        Circular imports cause subtle bugs and slow startup.
        """
        # Clear any cached imports
        modules_to_clear = [k for k in sys.modules.keys() if k.startswith("api.")]
        for mod in modules_to_clear:
            del sys.modules[mod]

        # Now try to import fresh
        try:
            import api.server

            assert api.server is not None
        except ImportError as e:
            if "circular" in str(e).lower():
                pytest.fail(f"Circular import detected: {e}")
            raise


class TestModuleAttributes:
    """Verify expected attributes exist on modules."""

    def test_server_has_app(self):
        """api.server must have 'app' attribute (FastAPI instance)."""
        import api.server

        assert hasattr(api.server, "app"), "api.server missing 'app' attribute"

    def test_server_memory_has_app(self):
        """api.server_memory must have 'app' attribute."""
        import api.server_memory

        assert hasattr(api.server_memory, "app"), "api.server_memory missing 'app' attribute"

    def test_routers_have_router(self):
        """Router modules must have 'router' attribute."""
        router_modules = [
            "api.os_routes",
            "api.agent_routes",
            "api.memory.router",
        ]

        for module_name in router_modules:
            module = importlib.import_module(module_name)
            assert hasattr(module, "router"), f"{module_name} missing 'router' attribute"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
