"""
Tests for L9 Collaborative Cell Auto-Discovery System
"""

import pytest
from collaborative_cells.cell_registry import (
    cell_registry,
    register_cell,
    get_all_cells,
    get_cells_by_category,
)


@pytest.fixture(autouse=True)
def clear_registries():
    """Clear all registries before and after each test."""
    cell_registry.clear()
    yield
    cell_registry.clear()


def test_register_cell_decorator():
    """Test that @register_cell decorator registers a cell."""

    # Register a test cell inside the test (not at module level)
    @register_cell(category="test")
    class TestCell:
        def execute(self):
            pass

        def get_config(self):
            pass

    cells = get_all_cells()

    assert "TestCell" in cells
    assert cells["TestCell"] == TestCell


def test_get_cells_by_category():
    """Test filtering cells by category."""

    # Register cells in different categories
    @register_cell(category="design")
    class DesignCell:
        def execute(self):
            pass

        def get_config(self):
            pass

    @register_cell(category="review")
    class ReviewCell:
        def execute(self):
            pass

        def get_config(self):
            pass

    design_cells = get_cells_by_category("design")
    assert "DesignCell" in design_cells

    review_cells = get_cells_by_category("review")
    assert "ReviewCell" in review_cells

    general_cells = get_cells_by_category("general")
    assert not general_cells
