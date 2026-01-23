"""
L9 Base Cell Tests
==================

Tests for base cell class.
No external services required - uses mocks.

Version: 1.0.0
"""

import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from collaborative_cells.base_cell import (BaseCell, CellConfig,
                                               ConsensusStrategy)
except ImportError as e:
    pytest.skip(
        f"Could not import collaborative_cells.base_cell: {e}", allow_module_level=True
    )


# =============================================================================
# Test: Base cell initialization
# =============================================================================


def test_base_cell_initialization():
    """
    Contract: BaseCell cannot be instantiated directly (abstract class).
    """
    with pytest.raises(TypeError):
        # BaseCell is abstract, should raise TypeError
        BaseCell()


# =============================================================================
# Test: Cell state management
# =============================================================================


def test_cell_state_management():
    """
    Contract: CellConfig can be created and manages state.
    """
    config = CellConfig(
        max_rounds=10,
        consensus_threshold=0.9,
        consensus_strategy=ConsensusStrategy.MAJORITY,
    )

    assert config.max_rounds == 10
    assert config.consensus_threshold == 0.9
    assert config.consensus_strategy == ConsensusStrategy.MAJORITY
    assert config.require_validation is True
    assert config.store_packets is True


# =============================================================================
# Test: ConsensusStrategy enum
# =============================================================================


def test_consensus_strategy_enum():
    """
    Contract: ConsensusStrategy enum has expected values.
    """
    assert ConsensusStrategy.UNANIMOUS == "unanimous"
    assert ConsensusStrategy.MAJORITY == "majority"
    assert ConsensusStrategy.THRESHOLD == "threshold"
    assert ConsensusStrategy.LEADER == "leader"
