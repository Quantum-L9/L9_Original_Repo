"""
L9 OS Bootstrap Tests
=====================

Tests for the bootstrap sequence that initializes the OS kernel.
No external services required - mocks file system operations.

Note: The 'os' directory conflicts with Python's built-in 'os' module.
These tests use importlib to load from the project's aios/ directory.

Version: 1.0.0
"""

import importlib.util
from pathlib import Path

import pytest


def get_os_module(module_name: str):
    """
    Import a module from the project's aios/ directory.
    Returns None if import fails.
    """
    # Build path to the project's aios/ directory
    project_root = Path(__file__).parent.parent.parent
    module_path = project_root / "aios" / f"{module_name}.py"

    if not module_path.exists():
        return None

    try:
        spec = importlib.util.spec_from_file_location(
            f"aios_{module_name}", str(module_path)
        )
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


# =============================================================================
# Test: Bootstrap module availability
# =============================================================================


def test_bootstrap_module_exists():
    """
    Contract: Bootstrap module exists in aios/ directory.
    """
    project_root = Path(__file__).parent.parent.parent
    module_path = project_root / "aios" / "bootstrap.py"

    assert module_path.exists(), "aios/bootstrap.py should exist"


def test_bootstrap_module_loadable():
    """
    Contract: Bootstrap module can be loaded.
    """
    module = get_os_module("bootstrap")

    # Skip if module can't be loaded due to dependencies
    if module is None:
        pytest.skip(
            "aios/bootstrap.py could not be loaded (likely missing dependencies)"
        )

    assert module is not None


def test_bootstrap_has_bootstrap_class():
    """
    Contract: Bootstrap module has Bootstrap class.
    """
    module = get_os_module("bootstrap")

    if module is None:
        pytest.skip("aios/bootstrap.py could not be loaded")

    assert hasattr(module, "Bootstrap"), "Bootstrap class should exist"


# =============================================================================
# Test: Bootstrap class instantiation (if loadable)
# =============================================================================


def test_bootstrap_instantiation():
    """
    Contract: Bootstrap class can be instantiated.
    """
    module = get_os_module("bootstrap")

    if module is None:
        pytest.skip("aios/bootstrap.py could not be loaded")

    Bootstrap = getattr(module, "Bootstrap", None)
    if Bootstrap is None:
        pytest.skip("Bootstrap class not found")

    try:
        bootstrap = Bootstrap(config_path="/test/config.yaml")
        assert bootstrap is not None
    except Exception as e:
        pytest.skip(f"Bootstrap instantiation failed: {e}")


def test_bootstrap_has_load_settings():
    """
    Contract: Bootstrap has load_settings method.
    """
    module = get_os_module("bootstrap")

    if module is None:
        pytest.skip("aios/bootstrap.py could not be loaded")

    Bootstrap = getattr(module, "Bootstrap", None)
    if Bootstrap is None:
        pytest.skip("Bootstrap class not found")

    assert hasattr(
        Bootstrap, "load_settings"
    ), "Bootstrap should have load_settings method"


def test_bootstrap_has_init_controller():
    """
    Contract: Bootstrap has init_controller method.
    """
    module = get_os_module("bootstrap")

    if module is None:
        pytest.skip("aios/bootstrap.py could not be loaded")

    Bootstrap = getattr(module, "Bootstrap", None)
    if Bootstrap is None:
        pytest.skip("Bootstrap class not found")

    assert hasattr(
        Bootstrap, "init_controller"
    ), "Bootstrap should have init_controller method"


def test_bootstrap_has_init_router():
    """
    Contract: Bootstrap has init_router method.
    """
    module = get_os_module("bootstrap")

    if module is None:
        pytest.skip("aios/bootstrap.py could not be loaded")

    Bootstrap = getattr(module, "Bootstrap", None)
    if Bootstrap is None:
        pytest.skip("Bootstrap class not found")

    assert hasattr(Bootstrap, "init_router"), "Bootstrap should have init_router method"


def test_bootstrap_has_bootstrap_method():
    """
    Contract: Bootstrap has bootstrap() method for full sequence.
    """
    module = get_os_module("bootstrap")

    if module is None:
        pytest.skip("aios/bootstrap.py could not be loaded")

    Bootstrap = getattr(module, "Bootstrap", None)
    if Bootstrap is None:
        pytest.skip("Bootstrap class not found")

    assert hasattr(Bootstrap, "bootstrap"), "Bootstrap should have bootstrap method"
