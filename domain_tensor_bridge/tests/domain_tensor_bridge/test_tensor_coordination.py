#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for TensorCoordinator - batching and timeout handling.
"""

import pytest
from unittest.mock import AsyncMock

from domain_tensor_bridge.tensor_coordinator import TensorCoordinator, TensorResult


@pytest.fixture
def coordinator():
    """Create tensor coordinator."""
    tensoraios = AsyncMock()
    tensoraios.call_link_prediction = AsyncMock(return_value=0.75)
    
    return TensorCoordinator(tensoraios_bridge=tensoraios, batch_size=5)


class TestBatchTensorCalls:
    """Tests for tensor call batching."""
    
    @pytest.mark.asyncio
    async def test_single_entity(self, coordinator):
        """Test single entity scoring."""
        results = await coordinator.coordinate_tensor_calls(["entity_1"])
        
        assert len(results) == 1
        assert isinstance(results[0], TensorResult)
        assert results[0].entity_id == "entity_1"
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, coordinator):
        """Test batch processing of entities."""
        entities = [f"entity_{i}" for i in range(12)]
        
        results = await coordinator.coordinate_tensor_calls(entities)
        
        assert len(results) == 12
    
    @pytest.mark.asyncio
    async def test_empty_entities(self, coordinator):
        """Test handling of empty entity list."""
        results = await coordinator.coordinate_tensor_calls([])
        
        assert len(results) == 0


class TestTimeoutHandling:
    """Tests for timeout handling."""
    
    @pytest.mark.asyncio
    async def test_mock_results_without_tensoraios(self):
        """Test mock results when tensoraios not configured."""
        coordinator = TensorCoordinator(tensoraios_bridge=None)
        
        results = await coordinator.coordinate_tensor_calls(["entity_1"])
        
        assert len(results) == 1
        assert results[0].metadata.get("mock") is True


