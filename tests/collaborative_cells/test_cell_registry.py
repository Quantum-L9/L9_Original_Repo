"""
Tests for L9 Collaborative Cell Auto-Discovery System
"""

import pytest
from collaborative_cells.cell_registry import (
    cell_registry,
    register_cell,
    discover_cells,
    get_all_cells,
    get_cells_by_category,
)


@pytest.fixture(autouse=True)
def clear_registries():
    """Clear all registries before and after each test."""
    cell_registry.clear()
    yield
    cell_registry.clear()


@register_cell(category="test")
class MyTestCell:
    def execute(self):
        pass

    def get_config(self):
        pass


def test_register_cell_decorator():
    """Test that @register_cell decorator registers a cell."""
    discover_cells(package="tests.collaborative_cells")
    cells = get_all_cells()

    assert "MyTestCell" in cells
    assert cells["MyTestCell"] == MyTestCell


def test_get_cells_by_category():
    """Test filtering cells by category."""
    discover_cells(package="tests.collaborative_cells")
    test_cells = get_cells_by_category("test")
    assert "MyTestCell" in test_cells

    general_cells = get_cells_by_category("general")
    assert not general_cells
