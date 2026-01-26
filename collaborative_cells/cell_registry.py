"""
L9 Collaborative Cells - Cell Auto-Discovery System
===================================================

Automatic discovery and registration of collaborative cells.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Collaborative Cell Registry",
    "module_version": "1.0.0",
    "created_by": "L9 Auto-Wiring Team",
    "created_at": "2026-01-18T00:00:00Z",
    "updated_at": "2026-01-18T00:00:00Z",
    "layer": "collaborative",
    "domain": "multi_agent",
    "module_name": "cell_registry",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["collaborative_cells.__init__"],
    },
}
# ============================================================================


import structlog

from core.auto_registry import AutoRegistry

logger = structlog.get_logger(__name__)


# =============================================================================
# Collaborative Cell Registry
# =============================================================================


def _validate_cell(cell_class: type) -> bool:
    """Validate that a class is a valid collaborative cell."""
    # Check if it has required methods (execute is mandatory, name must end with Cell)
    return (
        isinstance(cell_class, type)
        and hasattr(cell_class, "execute")
        and cell_class.__name__.endswith("Cell")
    )


# Global collaborative cell registry
cell_registry = AutoRegistry[type](
    name="collaborative_cells", validator=_validate_cell, allow_duplicates=False
)


def register_cell(
    name: str | None = None, category: str = "general", priority: int = 0, **metadata
):
    """
    Decorator to register a collaborative cell.

    Args:
        name: Cell name (defaults to class name)
        category: Cell category (e.g., "design", "implementation", "review")
        priority: Registration priority
        **metadata: Additional metadata

    Example:
        @register_cell(category="design")
        class ArchitectCell(BaseCell):
            pass
    """

    def decorator(cls: type) -> type:
        cell_name = name or cls.__name__
        cell_registry.register_instance(
            component_id=cell_name,
            component=cls,
            priority=priority,
            tags=[category],
            **metadata,
        )
        logger.info("cell_registry.registered", cell=cell_name, category=category)
        return cls

    return decorator


def discover_cells(package: str = "collaborative_cells") -> int:
    """
    Automatically discover all collaborative cells in the specified package.

    Args:
        package: Python package to scan for cells

    Returns:
        Number of modules discovered
    """
    logger.info("cell_registry.discovering", package=package)
    count = cell_registry.discover(package, recursive=True)
    logger.info("cell_registry.discovered", package=package, count=count)
    return count


def get_all_cells() -> dict[str, type]:
    """
    Get all registered collaborative cells.

    Returns:
        Dictionary mapping cell names to cell classes
    """
    cell_registry.initialize_factories()
    cells: dict[str, type] = {}

    for cell_id in cell_registry.list_ids():
        cell_class = cell_registry.get(cell_id)
        if cell_class:
            cells[cell_id] = cell_class

    logger.info("cell_registry.cells_retrieved", count=len(cells))
    return cells


def get_cells_by_category(category: str) -> dict[str, type]:
    """
    Get all collaborative cells in a specific category.

    Args:
        category: Category to filter by

    Returns:
        Dictionary mapping cell names to cell classes
    """
    cell_registry.initialize_factories()
    cell_classes = cell_registry.get_all(tags=[category])
    cells: dict[str, type] = {}

    for cell_class in cell_classes:
        cells[cell_class.__name__] = cell_class

    return cells


def get_cell_snapshot() -> dict:
    """Get a snapshot of all registered cells for observability."""
    return cell_registry.snapshot()


def register_legacy_cells() -> int:
    """
    Bridge function: Register all cells from collaborative_cells/__init__.py exports.

    This allows existing cell classes to be discovered by the new
    auto-registration system without adding decorators to each class.

    Returns:
        Number of cells registered
    """
    import importlib.util
    from pathlib import Path

    registered = 0

    # Find cells directory
    cells_dir = Path(__file__).parent

    # Define cells to register with their metadata (name, file_path, category, domain)
    cell_specs = [
        ("ArchitectCell", "architect_cell.py", "design", "architecture"),
        ("CoderCell", "coder_cell.py", "implementation", "coding"),
        ("ReviewerCell", "reviewer_cell.py", "quality", "review"),
        ("ReflectionCell", "reflection_cell.py", "meta", "reasoning"),
    ]

    for cell_name, file_path, category, domain in cell_specs:
        try:
            full_path = cells_dir / file_path
            if not full_path.exists():
                logger.debug(
                    "legacy_cell_file_not_found", cell=cell_name, path=str(full_path)
                )
                continue

            # Import directly from file
            spec = importlib.util.spec_from_file_location(cell_name, full_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                cell_cls = getattr(mod, cell_name, None)

                if cell_cls:
                    cell_registry.register_instance(
                        component_id=cell_name,
                        component=cell_cls,
                        priority=5,
                        tags=[category, domain, "legacy"],
                        category=category,
                        domain=domain,
                        source="legacy_bridge",
                    )
                    registered += 1
                    logger.debug(
                        "legacy_cell_registered", cell=cell_name, category=category
                    )
        except Exception as e:
            logger.debug("legacy_cell_skip", cell=cell_name, error=str(e))

    if registered > 0:
        logger.info("legacy_cells_registered", count=registered)

    return registered


# =============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COLLAB-CELL-REG",
    "governance_level": "standard",
    "security_reviewed": True,
    "performance_tested": True,
    "last_audit": "2026-01-18T00:00:00Z",
}
# ============================================================================
