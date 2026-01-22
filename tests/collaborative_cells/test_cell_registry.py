"""
Tests for L9 Collaborative Cell Auto-Discovery System

Note: Tests register components manually within each test to avoid
decorator-at-import issues with fixture clearing.
"""

import pytest

from collaborative_cells.cell_registry import (cell_registry, get_all_cells,
                                               get_cells_by_category,
                                               register_cell)


@pytest.fixture(autouse=True)
def clear_registries():
    """Clear all registries before and after each test."""
    cell_registry.clear()
    yield
    cell_registry.clear()


# Test cell class (NOT decorated at module level)
class MyTestCell:
    """Test cell for unit tests."""

    def execute(self):
        pass

    def get_config(self):
        pass


def test_register_cell_decorator():
    """Test that @register_cell decorator registers a cell."""
    # Register within test (after fixture clears registry)
    decorated_cls = register_cell(category="test")(MyTestCell)

    cells = get_all_cells()

    assert "MyTestCell" in cells
    assert cells["MyTestCell"] == decorated_cls


def test_get_cells_by_category():
    """Test filtering cells by category."""
    # Register within test
    register_cell(category="test")(MyTestCell)

    test_cells = get_cells_by_category("test")
    assert "MyTestCell" in test_cells

    general_cells = get_cells_by_category("general")
    assert not general_cells


def test_cell_registry_snapshot():
    """Test registry snapshot for observability."""
    register_cell(category="design", priority=10)(MyTestCell)

    snapshot = cell_registry.snapshot()

    assert snapshot["registry_name"] == "collaborative_cells"
    assert snapshot["component_count"] == 1
    assert len(snapshot["components"]) == 1
