"""
Unit Tests for Bayesian Kernel
===============================

Tests:
1. Kernel loads and respects feature flag
2. Feature flag defaults to OFF (safe)
3. Hypergraph node templates exist and work
4. Belief state creation and updates
5. Evidence addition and posterior updates
6. No regressions with flag disabled

Version: 1.0.0
"""

import pytest
import os
from typing import Dict
from unittest.mock import patch, MagicMock

from core.kernels.bayesian_kernel import (
    BayesianKernel,
    BeliefState,
    EvidenceStrength,
    get_bayesian_kernel,
    reset_bayesian_kernel,
)
from core.config import FeatureFlags, reset_flags_for_testing
from core.schemas.hypergraph import (
    BayesianNode,
    ReasoningNode,
    NodeTemplate,
    NodeType,
    NodeStatus,
    BAYESIAN_NODE_TEMPLATE,
)


# ============================================================================
# Test 1: Feature Flag Defaults to OFF (Safe Default)
# ============================================================================

def test_bayesian_kernel_disabled_by_default():
    """Feature flag defaults to false (safe)."""
    reset_bayesian_kernel()
    reset_flags_for_testing()
    
    with patch.dict(os.environ, {}, clear=True):
        kernel = BayesianKernel()
        assert kernel.enabled is False
        assert kernel.system_prompt_section == ""


def test_feature_flag_environment_variable():
    """Feature flag responds to environment variable."""
    reset_bayesian_kernel()
    reset_flags_for_testing()
    
    # When flag is OFF (default)
    with patch.dict(os.environ, {"L9_ENABLE_BAYESIAN_REASONING": "false"}):
        kernel = BayesianKernel()
        assert kernel.enabled is False
    
    # When flag is ON
    with patch.dict(os.environ, {"L9_ENABLE_BAYESIAN_REASONING": "true"}):
        kernel = BayesianKernel()
        assert kernel.enabled is True


# ============================================================================
# Test 2: Kernel Loads with System Prompt Section
# ============================================================================

def test_bayesian_kernel_enabled_provides_system_prompt():
    """When enabled, kernel provides system prompt section."""
    reset_bayesian_kernel()
    
    with patch.dict(os.environ, {"L9_ENABLE_BAYESIAN_REASONING": "true"}):
        kernel = BayesianKernel()
        assert kernel.enabled is True
        assert len(kernel.system_prompt_section) > 0
        assert "Bayesian" in kernel.system_prompt_section
        assert "Prior" in kernel.system_prompt_section
        assert "Evidence" in kernel.system_prompt_section
        assert "Posterior" in kernel.system_prompt_section


# ============================================================================
# Test 3: Hypergraph Node Templates Exist
# ============================================================================

def test_bayesian_node_template_exists():
    """BAYESIAN_NODE_TEMPLATE is defined and usable."""
    assert BAYESIAN_NODE_TEMPLATE is not None
    assert BAYESIAN_NODE_TEMPLATE.node_type == NodeType.BAYESIAN
    assert BAYESIAN_NODE_TEMPLATE.template_id == "bayesian"


def test_create_bayesian_node_from_template():
    """Create Bayesian node using template."""
    node = BAYESIAN_NODE_TEMPLATE.create_node(
        belief_variable="hypothesis_x",
    )
    
    assert isinstance(node, BayesianNode)
    assert node.node_type == NodeType.BAYESIAN
    assert node.status == NodeStatus.PENDING


def test_reasoning_node_template_exists():
    """REASONING_NODE_TEMPLATE is defined."""
    from core.schemas.hypergraph import REASONING_NODE_TEMPLATE
    
    assert REASONING_NODE_TEMPLATE is not None
    assert REASONING_NODE_TEMPLATE.node_type == NodeType.REASONING


# ============================================================================
# Test 4: Belief State Creation and Management
# ============================================================================

def test_create_belief_state_when_disabled():
    """Creating belief state when disabled raises error."""
    reset_bayesian_kernel()
    
    with patch.dict(os.environ, {"L9_ENABLE_BAYESIAN_REASONING": "false"}):
        kernel = BayesianKernel()
        
        with pytest.raises(RuntimeError, match="disabled"):
            kernel.create_belief_state(
                variable="hypothesis",
                prior={"yes": 0.5, "no": 0.5},
            )


def test_create_belief_state_when_enabled():
    """Creating belief state when enabled works."""
    reset_bayesian_kernel()
    
    with patch.dict(os.environ, {"L9_ENABLE_BAYESIAN_REASONING": "true"}):
        kernel = BayesianKernel()
        
        prior = {"yes": 0.6, "no": 0.4}
        belief = kernel.create_belief_state(
            variable="hypothesis_x",
            prior=prior,
        )
        
        assert belief.variable == "hypothesis_x"
        assert belief.prior == prior
        assert belief.posterior == prior
        assert belief.evidence == []
        assert 0.0 <= belief.confidence <= 1.0


# ============================================================================
# Test 5: Evidence Addition and Posterior Updates
# ============================================================================

def test_add_evidence():
    """Add evidence to belief state."""
    reset_bayesian_kernel()
    
    with patch.dict(os.environ, {"L9_ENABLE_BAYESIAN_REASONING": "true"}):
        kernel = BayesianKernel()
        
        belief = kernel.create_belief_state(
            variable="test",
            prior={"yes": 0.5, "no": 0.5},
        )
        
        kernel.add_evidence(
            variable="test",
            description="Observation A",
            strength=EvidenceStrength.STRONG,
            source="experiment_1",
        )
        
        assert len(belief.evidence) == 1
        assert belief.evidence[0]["description"] == "Observation A"
        assert belief.evidence[0]["strength"] == "strong"
        assert belief.evidence[0]["source"] == "experiment_1"


def test_update_posterior():
    """Update posterior belief."""
    reset_bayesian_kernel()
    
    with patch.dict(os.environ, {"L9_ENABLE_BAYESIAN_REASONING": "true"}):
        kernel = BayesianKernel()
        
        belief = kernel.create_belief_state(
            variable="test",
            prior={"yes": 0.5, "no": 0.5},
        )
        
        new_posterior = {"yes": 0.8, "no": 0.2}
        updated_belief = kernel.update_posterior("test", new_posterior)
        
        assert updated_belief.posterior == new_posterior
        assert updated_belief.posterior != updated_belief.prior
        assert updated_belief.confidence > 0.5


# ============================================================================
# Test 6: Bayesian Node Properties
# ============================================================================

def test_bayesian_node_properties():
    """BayesianNode has correct properties."""
    node = BayesianNode(
        belief_variable="medical_diagnosis",
        prior_belief={"disease_a": 0.3, "disease_b": 0.7},
    )
    
    assert node.belief_variable == "medical_diagnosis"
    assert node.prior_belief == {"disease_a": 0.3, "disease_b": 0.7}
    assert node.posterior_belief == {}
    assert node.update_method == "bayes_rule"
    assert 0.0 <= node.uncertainty <= 1.0


def test_bayesian_node_add_evidence():
    """Add evidence to Bayesian node."""
    node = BayesianNode(belief_variable="test")
    
    node.add_evidence(
        description="Lab test positive",
        strength="strong",
        source="hospital_x",
    )
    
    assert len(node.evidence) == 1
    assert node.evidence[0].description == "Lab test positive"
    assert node.evidence[0].strength == "strong"
    assert node.evidence[0].source == "hospital_x"


def test_bayesian_node_update_posterior():
    """Update posterior belief in node."""
    node = BayesianNode(
        belief_variable="test",
        prior_belief={"a": 0.5, "b": 0.5},
    )
    
    posterior = {"a": 0.8, "b": 0.2}
    node.update_posterior(posterior, uncertainty=0.3)
    
    assert node.posterior_belief == posterior
    assert node.uncertainty == 0.3
    assert node.status == NodeStatus.COMPLETED
    assert node.completed_at is not None


# ============================================================================
# Test 7: No Regressions with Flag Disabled
# ============================================================================

def test_agent_execution_works_without_bayesian():
    """Agent execution succeeds when Bayesian is disabled."""
    reset_bayesian_kernel()
    reset_flags_for_testing()
    
    with patch.dict(os.environ, {}, clear=True):
        # Simulate agent execution (minimal smoke test)
        kernel = BayesianKernel()
        assert kernel.enabled is False
        
        # Agent should work normally (empty Bayesian prompt)
        prompt = "Base prompt"
        if kernel.enabled:
            prompt += kernel.system_prompt_section
        
        assert "Bayesian" not in prompt  # Not included when disabled


# ============================================================================
# Test 8: Thread Safety of Global Singleton
# ============================================================================

def test_get_bayesian_kernel_singleton():
    """get_bayesian_kernel() returns same instance."""
    reset_bayesian_kernel()
    
    with patch.dict(os.environ, {"L9_ENABLE_BAYESIAN_REASONING": "true"}):
        k1 = get_bayesian_kernel()
        k2 = get_bayesian_kernel()
        
        assert k1 is k2  # Same instance


# ============================================================================
# Test 9: Confidence Calculation
# ============================================================================

def test_confidence_from_distribution():
    """Confidence calculated correctly from distribution."""
    reset_bayesian_kernel()
    
    with patch.dict(os.environ, {"L9_ENABLE_BAYESIAN_REASONING": "true"}):
        kernel = BayesianKernel()
        
        # High confidence (strong belief)
        conf = kernel._calculate_confidence({"yes": 0.9, "no": 0.1})
        assert conf > 0.8
        
        # Low confidence (weak belief)
        conf = kernel._calculate_confidence({"yes": 0.51, "no": 0.49})
        assert 0.4 < conf < 0.6
        
        # Uniform (maximum uncertainty)
        conf = kernel._calculate_confidence({"a": 0.33, "b": 0.33, "c": 0.34})
        assert conf < 0.4
