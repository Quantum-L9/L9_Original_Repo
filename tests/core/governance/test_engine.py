"""
L9 Core Governance - Engine Tests
=================================

Contract-grade tests for GovernanceEngineService.

Acceptance criteria from MODULE_SPEC:
- The engine loads all valid policies from the manifest directory on startup
- A request matching a specific 'allow' policy is approved
- A request matching a specific 'deny' policy is denied
- A request that does not match any policy is denied by default
- The engine correctly evaluates policies with conditions
- An invalid policy file prevents the service from starting

Version: 1.0.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from core.decorators import must_stay_async
from core.governance.engine import GovernanceEngineService
from core.governance.loader import InvalidPolicyError, PolicyLoadError
from core.governance.schemas import (
    Condition,
    ConditionOperator,
    EvaluationRequest,
    PolicyEffect,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_policy_dir(tmp_path: Path) -> Path:
    """Create a temporary policy directory."""
    return tmp_path


@pytest.fixture
def simple_allow_policy() -> dict[str, Any]:
    """A simple allow policy."""
    return {
        "id": "allow-test",
        "name": "Allow Test Policy",
        "effect": "allow",
        "priority": 100,
        "subjects": ["test-agent"],
        "actions": ["test.action"],
        "resources": ["test-resource"],
    }


@pytest.fixture
def simple_deny_policy() -> dict[str, Any]:
    """A simple deny policy."""
    return {
        "id": "deny-test",
        "name": "Deny Test Policy",
        "effect": "deny",
        "priority": 100,
        "subjects": ["blocked-agent"],
        "actions": ["blocked.action"],
        "resources": ["*"],
    }


@pytest.fixture
def conditional_policy() -> dict[str, Any]:
    """A policy with conditions."""
    return {
        "id": "conditional-allow",
        "name": "Conditional Allow",
        "effect": "allow",
        "priority": 100,
        "subjects": ["*"],
        "actions": ["conditional.action"],
        "resources": ["*"],
        "conditions": [
            {
                "field": "hour",
                "operator": "greater_than",
                "value": 8,
            },
            {
                "field": "hour",
                "operator": "less_than",
                "value": 18,
            },
        ],
    }


def create_policy_file(directory: Path, filename: str, policies: list[dict]) -> Path:
    """Helper to create a policy YAML file."""
    file_path = directory / filename
    with open(file_path, "w") as f:
        yaml.dump({"policies": policies}, f)
    return file_path


# =============================================================================
# Test: Engine loads all valid policies from manifests
# =============================================================================


def test_engine_loads_policies_from_manifests(
    temp_policy_dir: Path,
    simple_allow_policy: dict,
    simple_deny_policy: dict,
) -> None:
    """
    Contract: Engine loads all valid policies from the manifest directory on startup.

    Verifies:
    - Both policy files are read
    - All policies from both files are loaded
    - Policy count matches expected
    """
    # Create two policy files
    create_policy_file(temp_policy_dir, "allow.yaml", [simple_allow_policy])
    create_policy_file(temp_policy_dir, "deny.yaml", [simple_deny_policy])

    # Create engine
    engine = GovernanceEngineService(policy_dir=str(temp_policy_dir))

    # Verify both policies loaded
    assert engine.policy_count == 2

    # Verify specific policies exist
    allow_policy = engine.get_policy("allow-test")
    deny_policy = engine.get_policy("deny-test")

    assert allow_policy is not None
    assert allow_policy.name == "Allow Test Policy"
    assert allow_policy.effect == PolicyEffect.ALLOW

    assert deny_policy is not None
    assert deny_policy.name == "Deny Test Policy"
    assert deny_policy.effect == PolicyEffect.DENY


# =============================================================================
# Test: Request matching allow policy is approved
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_request_matching_allow_policy_is_approved(
    temp_policy_dir: Path,
    simple_allow_policy: dict,
) -> None:
    """
    Contract: A request matching a specific 'allow' policy is approved.

    Verifies:
    - Request with matching subject, action, resource is allowed
    - Result includes the matching policy ID
    - Result.allowed is True
    """
    create_policy_file(temp_policy_dir, "policies.yaml", [simple_allow_policy])
    engine = GovernanceEngineService(policy_dir=str(temp_policy_dir))

    request = EvaluationRequest(
        subject="test-agent",
        action="test.action",
        resource="test-resource",
    )

    result = await engine.evaluate(request)

    assert result.allowed is True
    assert result.effect == PolicyEffect.ALLOW
    assert result.policy_id == "allow-test"
    assert "Allowed by policy" in result.reason


# =============================================================================
# Test: Request matching deny policy is denied
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_request_matching_deny_policy_is_denied(
    temp_policy_dir: Path,
    simple_deny_policy: dict,
) -> None:
    """
    Contract: A request matching a specific 'deny' policy is denied.

    Verifies:
    - Request with matching subject, action is denied
    - Result includes the matching policy ID
    - Result.allowed is False
    """
    create_policy_file(temp_policy_dir, "policies.yaml", [simple_deny_policy])
    engine = GovernanceEngineService(policy_dir=str(temp_policy_dir))

    request = EvaluationRequest(
        subject="blocked-agent",
        action="blocked.action",
        resource="any-resource",
    )

    result = await engine.evaluate(request)

    assert result.allowed is False
    assert result.effect == PolicyEffect.DENY
    assert result.policy_id == "deny-test"
    assert "Denied by policy" in result.reason


# =============================================================================
# Test: Unmatched request is denied by default
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_unmatched_request_is_denied_by_default(
    temp_policy_dir: Path,
    simple_allow_policy: dict,
) -> None:
    """
    Contract: A request that does not match any policy is denied by default.

    This is the critical deny-by-default behavior.

    Verifies:
    - Request not matching any policy is denied
    - Result.policy_id is None (no matching policy)
    - Result indicates default deny
    """
    # Create a specific allow policy that won't match our request
    create_policy_file(temp_policy_dir, "policies.yaml", [simple_allow_policy])
    engine = GovernanceEngineService(policy_dir=str(temp_policy_dir))

    # Request with different subject/action that doesn't match
    request = EvaluationRequest(
        subject="unknown-agent",
        action="unknown.action",
        resource="unknown-resource",
    )

    result = await engine.evaluate(request)

    assert result.allowed is False
    assert result.effect == PolicyEffect.DENY
    assert result.policy_id is None  # No matching policy
    assert "No matching policy" in result.reason or "default" in result.reason.lower()


# =============================================================================
# Test: Engine evaluates conditional policies
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_engine_evaluates_conditional_policies(
    temp_policy_dir: Path,
    conditional_policy: dict,
) -> None:
    """
    Contract: The engine correctly evaluates policies with conditions.

    Verifies:
    - Request meeting conditions is allowed
    - Request not meeting conditions is denied (default)
    """
    create_policy_file(temp_policy_dir, "policies.yaml", [conditional_policy])
    engine = GovernanceEngineService(policy_dir=str(temp_policy_dir))

    # Request within business hours (9-17) should be allowed
    request_allowed = EvaluationRequest(
        subject="any-agent",
        action="conditional.action",
        resource="any-resource",
        context={"hour": 12},  # Noon - within 8-18
    )

    result_allowed = await engine.evaluate(request_allowed)
    assert result_allowed.allowed is True
    assert result_allowed.policy_id == "conditional-allow"

    # Request outside business hours should be denied (no match -> default deny)
    request_denied = EvaluationRequest(
        subject="any-agent",
        action="conditional.action",
        resource="any-resource",
        context={"hour": 22},  # 10 PM - outside 8-18
    )

    result_denied = await engine.evaluate(request_denied)
    assert result_denied.allowed is False


# =============================================================================
# Test: Invalid policy file prevents startup
# =============================================================================


def test_invalid_policy_file_prevents_startup(temp_policy_dir: Path) -> None:
    """
    Contract: An invalid policy file prevents the service from starting.

    This is critical for fail-closed security.

    Verifies:
    - InvalidPolicyError is raised
    - Engine does not start with invalid policies
    """
    # Create an invalid policy file (missing required 'id' field)
    invalid_policy = {
        "name": "Missing ID Policy",
        "effect": "allow",
        # 'id' is missing
    }

    file_path = temp_policy_dir / "invalid.yaml"
    with open(file_path, "w") as f:
        yaml.dump({"policies": [invalid_policy]}, f)

    with pytest.raises(InvalidPolicyError):
        GovernanceEngineService(policy_dir=str(temp_policy_dir))


def test_invalid_yaml_prevents_startup(temp_policy_dir: Path) -> None:
    """
    Contract: Malformed YAML prevents the service from starting.

    Verifies:
    - InvalidPolicyError is raised for malformed YAML
    """
    # Create malformed YAML
    file_path = temp_policy_dir / "malformed.yaml"
    with open(file_path, "w") as f:
        f.write("policies:\n  - id: test\n    effect: [invalid yaml structure")

    with pytest.raises(InvalidPolicyError):
        GovernanceEngineService(policy_dir=str(temp_policy_dir))


# =============================================================================
# Test: Policy priority ordering (first-match-wins)
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_policy_priority_ordering(temp_policy_dir: Path) -> None:
    """
    Contract: Higher priority policies are evaluated first (first-match-wins).

    Verifies:
    - High priority allow beats low priority deny
    - First matching policy's effect is applied
    """
    policies = [
        {
            "id": "low-priority-deny",
            "name": "Low Priority Deny",
            "effect": "deny",
            "priority": 10,
            "subjects": ["*"],
            "actions": ["priority.test"],
            "resources": ["*"],
        },
        {
            "id": "high-priority-allow",
            "name": "High Priority Allow",
            "effect": "allow",
            "priority": 100,
            "subjects": ["*"],
            "actions": ["priority.test"],
            "resources": ["*"],
        },
    ]

    create_policy_file(temp_policy_dir, "policies.yaml", policies)
    engine = GovernanceEngineService(policy_dir=str(temp_policy_dir))

    request = EvaluationRequest(
        subject="any-agent",
        action="priority.test",
        resource="any-resource",
    )

    result = await engine.evaluate(request)

    # High priority allow should win
    assert result.allowed is True
    assert result.policy_id == "high-priority-allow"


# =============================================================================
# Test: Wildcard pattern matching
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_wildcard_pattern_matching(temp_policy_dir: Path) -> None:
    """
    Contract: Wildcard patterns match correctly.

    Verifies:
    - "*" matches anything
    - "prefix*" matches strings starting with prefix
    - Exact match works
    """
    policies = [
        {
            "id": "wildcard-allow",
            "name": "Wildcard Allow",
            "effect": "allow",
            "priority": 100,
            "subjects": ["agent:*"],  # Matches any agent:xxx
            "actions": ["tool.*"],  # Matches any tool.xxx
            "resources": ["*"],  # Matches anything
        },
    ]

    create_policy_file(temp_policy_dir, "policies.yaml", policies)
    engine = GovernanceEngineService(policy_dir=str(temp_policy_dir))

    # Should match
    request = EvaluationRequest(
        subject="agent:test-123",
        action="tool.execute",
        resource="any-tool",
    )
    result = await engine.evaluate(request)
    assert result.allowed is True

    # Should not match (different subject prefix)
    request_no_match = EvaluationRequest(
        subject="user:test-123",  # Different prefix
        action="tool.execute",
        resource="any-tool",
    )
    result_no_match = await engine.evaluate(request_no_match)
    assert result_no_match.allowed is False  # Default deny


# =============================================================================
# Test: Sync evaluation method
# =============================================================================


def test_evaluate_sync(temp_policy_dir: Path, simple_allow_policy: dict) -> None:
    """
    Contract: Synchronous evaluation works without tracing.

    Verifies:
    - evaluate_sync returns correct result
    - No async context required
    """
    create_policy_file(temp_policy_dir, "policies.yaml", [simple_allow_policy])
    engine = GovernanceEngineService(policy_dir=str(temp_policy_dir))

    request = EvaluationRequest(
        subject="test-agent",
        action="test.action",
        resource="test-resource",
    )

    result = engine.evaluate_sync(request)

    assert result.allowed is True
    assert result.policy_id == "allow-test"


# =============================================================================
# Test: is_allowed convenience method
# =============================================================================


def test_is_allowed_convenience_method(
    temp_policy_dir: Path,
    simple_allow_policy: dict,
) -> None:
    """
    Contract: is_allowed() provides quick yes/no check.

    Verifies:
    - Returns True for allowed actions
    - Returns False for denied actions
    """
    create_policy_file(temp_policy_dir, "policies.yaml", [simple_allow_policy])
    engine = GovernanceEngineService(policy_dir=str(temp_policy_dir))

    # Should be allowed
    assert (
        engine.is_allowed(
            subject="test-agent",
            action="test.action",
            resource="test-resource",
        )
        is True
    )

    # Should be denied (no matching policy)
    assert (
        engine.is_allowed(
            subject="other-agent",
            action="other.action",
            resource="other-resource",
        )
        is False
    )


# =============================================================================
# Test: Empty policy directory
# =============================================================================


def test_empty_policy_directory(temp_policy_dir: Path) -> None:
    """
    Contract: Empty policy directory results in default deny for everything.

    Verifies:
    - Engine starts with zero policies
    - All requests are denied by default
    """
    # Don't create any policy files
    engine = GovernanceEngineService(policy_dir=str(temp_policy_dir))

    assert engine.policy_count == 0

    # Any request should be denied
    assert (
        engine.is_allowed(
            subject="any",
            action="any",
            resource="any",
        )
        is False
    )


# =============================================================================
# Test: Missing policy directory
# =============================================================================


def test_missing_policy_directory_raises_error() -> None:
    """
    Contract: Missing policy directory raises PolicyLoadError.

    Verifies:
    - PolicyLoadError is raised
    - Engine does not start
    """
    with pytest.raises(PolicyLoadError):
        GovernanceEngineService(policy_dir="/nonexistent/directory")


# =============================================================================
# Test: Condition operators
# =============================================================================


def test_condition_operators() -> None:
    """
    Contract: All condition operators evaluate correctly.

    Verifies:
    - equals, not_equals
    - contains, not_contains
    - in, not_in
    - greater_than, less_than
    """
    context = {
        "role": "admin",
        "permissions": ["read", "write", "delete"],
        "level": 5,
    }

    # EQUALS
    cond_equals = Condition(
        field="role", operator=ConditionOperator.EQUALS, value="admin"
    )
    assert cond_equals.evaluate(context) is True

    cond_equals_fail = Condition(
        field="role", operator=ConditionOperator.EQUALS, value="user"
    )
    assert cond_equals_fail.evaluate(context) is False

    # NOT_EQUALS
    cond_not_equals = Condition(
        field="role", operator=ConditionOperator.NOT_EQUALS, value="user"
    )
    assert cond_not_equals.evaluate(context) is True

    # CONTAINS
    cond_contains = Condition(
        field="permissions", operator=ConditionOperator.CONTAINS, value="write"
    )
    assert cond_contains.evaluate(context) is True

    # IN
    cond_in = Condition(
        field="role", operator=ConditionOperator.IN, value=["admin", "superuser"]
    )
    assert cond_in.evaluate(context) is True

    # GREATER_THAN
    cond_gt = Condition(field="level", operator=ConditionOperator.GREATER_THAN, value=3)
    assert cond_gt.evaluate(context) is True

    # LESS_THAN
    cond_lt = Condition(field="level", operator=ConditionOperator.LESS_THAN, value=10)
    assert cond_lt.evaluate(context) is True


# =============================================================================
# Test: Disabled policies are skipped
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_disabled_policies_are_skipped(temp_policy_dir: Path) -> None:
    """
    Contract: Disabled policies do not match.

    Verifies:
    - Policy with enabled=False is not evaluated
    - Request falls through to next policy or default
    """
    policies = [
        {
            "id": "disabled-allow",
            "name": "Disabled Allow",
            "effect": "allow",
            "priority": 100,
            "subjects": ["*"],
            "actions": ["test.action"],
            "resources": ["*"],
            "enabled": False,  # Disabled
        },
    ]

    create_policy_file(temp_policy_dir, "policies.yaml", policies)
    engine = GovernanceEngineService(policy_dir=str(temp_policy_dir))

    request = EvaluationRequest(
        subject="any",
        action="test.action",
        resource="any",
    )

    result = await engine.evaluate(request)

    # Should be denied (disabled policy skipped, no other match)
    assert result.allowed is False
    assert result.policy_id is None


# =============================================================================
# Public API
# =============================================================================

__all__ = []
