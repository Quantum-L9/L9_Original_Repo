"""
L9 Collaborative Cells - Multi-Agent Collaboration Framework
============================================================

Cognitive cells that coordinate multiple agents for:
- Architecture design (ArchitectCell)
- Code implementation (CoderCell)
- Quality review (ReviewerCell)
- Meta-reasoning and reflection (ReflectionCell)

Each cell uses 2+ agents in a produce-critique-revise loop
until consensus is reached.
"""

from collaborative_cells.architect_cell import ArchitectCell
from collaborative_cells.base_cell import (
    BaseCell,
    CellConfig,
    CellResult,
    ConsensusStrategy,
)
from collaborative_cells.coder_cell import CoderCell
from collaborative_cells.reflection_cell import ReflectionCell
from collaborative_cells.reviewer_cell import ReviewerCell

__all__ = [
    # Specialized Cells
    "ArchitectCell",
    # Base
    "BaseCell",
    "CellConfig",
    "CellResult",
    "CoderCell",
    "ConsensusStrategy",
    "ReflectionCell",
    "ReviewerCell",
]
