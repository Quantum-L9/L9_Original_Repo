"""
L9 Wiring Integrity Test Suite
===============================

Validates that module exports match expected function signatures and names.
Prevents runtime failures from import/naming drift.

Test Categories:
1. Memory substrate service exports
2. Input segmenter metadata validation
3. Cross-module import compatibility

Author: L9 Engineering
Updated: 2026-01-25
"""

import ast
import inspect
import warnings
from pathlib import Path

import pytest

from core.decorators import must_stay_async

# =============================================================================
# Test 1: Memory Substrate Service Exports
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_memory_substrate_service_canonical_export():
    """Verify canonical get_service() function exists and is callable."""
    from memory.substrate_service import get_service

    assert callable(get_service), "get_service must be callable"
    assert inspect.iscoroutinefunction(get_service), "get_service must be async"

    # Verify return type annotation
    sig = inspect.signature(get_service)
    assert sig.return_annotation.__name__ == "MemorySubstrateService", (
        "get_service must return MemorySubstrateService"
    )


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_memory_substrate_service_legacy_alias():
    """Verify deprecated get_memory_substrate_service() alias exists for backward compatibility."""
    from memory.substrate_service import get_memory_substrate_service

    assert callable(get_memory_substrate_service), (
        "get_memory_substrate_service alias must exist"
    )
    assert inspect.iscoroutinefunction(get_memory_substrate_service), (
        "get_memory_substrate_service must be async"
    )


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_memory_substrate_service_signature_compatibility():
    """Verify both function signatures are compatible (same return type)."""
    from memory.substrate_service import get_memory_substrate_service, get_service

    sig_canonical = inspect.signature(get_service)
    sig_legacy = inspect.signature(get_memory_substrate_service)

    assert sig_canonical.return_annotation == sig_legacy.return_annotation, (
        "Both functions must return same type"
    )


@pytest.mark.asyncio
async def test_memory_substrate_service_deprecation_warning():
    """Verify deprecated function emits DeprecationWarning."""
    import os

    from memory.substrate_service import get_memory_substrate_service, init_service

    # Skip if no database URL (CI environment)
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set - skipping runtime test")

    # Initialize service for testing
    await init_service(os.getenv("DATABASE_URL"))

    # Call deprecated function and capture warning
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        await get_memory_substrate_service()

        # Verify warning was raised
        assert len(w) == 1, "Should emit exactly one warning"
        assert issubclass(w[0].category, DeprecationWarning), (
            "Warning must be DeprecationWarning"
        )
        assert "get_service()" in str(w[0].message), (
            "Warning must mention get_service() as replacement"
        )


def test_input_segmenter_file_syntax_valid():
    """Verify input_segmenter.py file is syntactically valid."""
    from orchestration.input_segmenter import InputSegmenter

    # If we can import the class, file compiled successfully
    assert InputSegmenter is not None

    # Double-check by parsing the source file
    file_path = Path("orchestration/input_segmenter.py")
    if file_path.exists():
        with open(file_path) as f:
            source = f.read()
            try:
                ast.parse(source)
            except SyntaxError as e:
                pytest.fail(f"Syntax error in input_segmenter.py: {e}")


# =============================================================================
# Test 3: Cross-Module Import Compatibility
# =============================================================================


def test_memory_substrate_service_imports_from_core():
    """Verify memory substrate can import from core modules."""
    try:
        from core.schemas import PacketEnvelopeIn
        from memory.substrate_service import MemorySubstrateService

        assert MemorySubstrateService is not None
        assert PacketEnvelopeIn is not None
    except ImportError as e:
        pytest.fail(f"Cross-module import failed: {e}")


def test_orchestration_imports_from_core():
    """Verify orchestration can import from core modules."""
    try:
        import structlog

        from orchestration.input_segmenter import InputSegmenter

        assert InputSegmenter is not None
        assert structlog is not None
    except ImportError as e:
        pytest.fail(f"Cross-module import failed: {e}")


# =============================================================================
# Test 4: Dependency Resolution
# =============================================================================


def test_critical_dependencies_importable():
    """Verify all critical dependencies can be imported."""
    critical_deps = [
        "asyncpg",
        "neo4j",
        "structlog",
        "langchain_core",
        "langgraph",
        "pydantic_settings",
        "prometheus_client",
    ]

    missing = []
    for dep in critical_deps:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)

    assert not missing, f"Missing critical dependencies: {', '.join(missing)}"


# =============================================================================
# Test 5: Function Registry Integrity
# =============================================================================


def test_singleton_registry_contains_memory_service():
    """Verify memory substrate service is registered in singleton registry."""
    try:
        from core.singleton_auto_registry import _registry

        # Check if memory_substrate_service is registered
        assert "memory_substrate_service" in _registry, (
            "memory_substrate_service not found in singleton registry"
        )

        service_entry = _registry["memory_substrate_service"]
        assert service_entry["factory"].__name__ == "get_service", (
            "Registry should point to get_service function"
        )

    except ImportError:
        pytest.skip("Singleton registry not available - skipping test")


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_database_url():
    """Provide mock database URL for tests."""
    return "postgresql://test:test@localhost/test_l9"


@pytest.fixture
async def initialized_service(mock_database_url):
    """Provide initialized memory substrate service for tests."""
    from memory.substrate_service import close_service, init_service

    try:
        service = await init_service(mock_database_url)
        yield service
    finally:
        await close_service()
