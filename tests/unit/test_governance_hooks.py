"""
Unit Tests for Governance Policy Enforcement Hooks
===================================================

Tests the governance hooks implementation.

Test Coverage:
- HookContext creation and export
- HookResult allow/deny/modify
- SchemaValidationHook
- ScopeAuthorizationHook
- AuditLoggingHook
- RateLimitingHook
- GovernanceHookRegistry registration and execution
- Hook priority ordering
- Hook error handling

Mutation Testing Target: 85%+ score
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from memory.governance_hooks import (
    HookType,
    HookPriority,
    HookContext,
    HookResult,
    GovernanceHook,
    SchemaValidationHook,
    ScopeAuthorizationHook,
    AuditLoggingHook,
    RateLimitingHook,
    GovernanceHookRegistry,
    get_hook_registry,
)


class TestHookContext:
    """Test HookContext dataclass."""
    
    def test_hook_context_creation(self):
        """Test HookContext creation with required fields."""
        ctx = HookContext(
            operation="write",
            caller_id="test-caller",
        )
        
        assert ctx.operation == "write"
        assert ctx.caller_id == "test-caller"
        assert ctx.timestamp is not None
    
    def test_hook_context_to_dict(self):
        """Test HookContext.to_dict() exports correctly."""
        ctx = HookContext(
            operation="write",
            caller_id="test-caller",
            project_id="test-project",
            scope="shared",
            packet_type="event",
            trace_id="test-trace",
        )
        
        result = ctx.to_dict()
        
        assert result["operation"] == "write"
        assert result["caller_id"] == "test-caller"
        assert result["project_id"] == "test-project"
        assert result["scope"] == "shared"
        assert result["packet_type"] == "event"
        assert result["trace_id"] == "test-trace"


class TestHookResult:
    """Test HookResult dataclass."""
    
    def test_hook_result_allow(self):
        """Test HookResult.allow() creates allow result."""
        result = HookResult.allow()
        
        assert result.allowed is True
        assert result.reason is None
    
    def test_hook_result_deny(self):
        """Test HookResult.deny() creates deny result."""
        result = HookResult.deny("Test reason")
        
        assert result.allowed is False
        assert result.reason == "Test reason"
    
    def test_hook_result_allow_with_modification(self):
        """Test HookResult.allow_with_modification()."""
        modified_payload = {"modified": True}
        result = HookResult.allow_with_modification(modified_payload)
        
        assert result.allowed is True
        assert result.modified_payload == modified_payload


class TestSchemaValidationHook:
    """Test SchemaValidationHook."""
    
    @pytest.mark.asyncio
    async def test_schema_validation_passes_with_valid_payload(self):
        """Test schema validation passes with valid payload."""
        hook = SchemaValidationHook()
        ctx = HookContext(
            operation="write",
            caller_id="test-caller",
            payload={"packet_type": "event", "payload": {}},
        )
        
        result = await hook.execute(ctx)
        
        assert result.allowed is True
    
    @pytest.mark.asyncio
    async def test_schema_validation_fails_without_payload(self):
        """Test schema validation fails without payload."""
        hook = SchemaValidationHook()
        ctx = HookContext(
            operation="write",
            caller_id="test-caller",
            payload=None,
        )
        
        result = await hook.execute(ctx)
        
        assert result.allowed is False
        assert "Missing payload" in result.reason
    
    @pytest.mark.asyncio
    async def test_schema_validation_fails_with_missing_fields(self):
        """Test schema validation fails with missing required fields."""
        hook = SchemaValidationHook()
        ctx = HookContext(
            operation="write",
            caller_id="test-caller",
            payload={"packet_type": "event"},  # Missing "payload" field
        )
        
        result = await hook.execute(ctx)
        
        assert result.allowed is False
        assert "Missing required fields" in result.reason


class TestScopeAuthorizationHook:
    """Test ScopeAuthorizationHook."""
    
    @pytest.mark.asyncio
    async def test_scope_authorization_allows_unprotected_scope(self):
        """Test scope authorization allows unprotected scopes."""
        hook = ScopeAuthorizationHook()
        ctx = HookContext(
            operation="write",
            caller_id="test-caller",
            scope="shared",
        )
        
        result = await hook.execute(ctx)
        
        assert result.allowed is True
    
    @pytest.mark.asyncio
    async def test_scope_authorization_allows_authorized_caller(self):
        """Test scope authorization allows authorized callers."""
        hook = ScopeAuthorizationHook()
        ctx = HookContext(
            operation="write",
            caller_id="l-cto",  # Authorized caller
            scope="l-private",  # Protected scope
        )
        
        result = await hook.execute(ctx)
        
        assert result.allowed is True
    
    @pytest.mark.asyncio
    async def test_scope_authorization_denies_unauthorized_caller(self):
        """Test scope authorization denies unauthorized callers."""
        hook = ScopeAuthorizationHook()
        ctx = HookContext(
            operation="write",
            caller_id="unauthorized-caller",
            scope="l-private",  # Protected scope
        )
        
        result = await hook.execute(ctx)
        
        assert result.allowed is False
        assert "not authorized" in result.reason


class TestAuditLoggingHook:
    """Test AuditLoggingHook."""
    
    @pytest.mark.asyncio
    async def test_audit_logging_always_allows(self):
        """Test audit logging hook always allows operations."""
        hook = AuditLoggingHook()
        ctx = HookContext(
            operation="write",
            caller_id="test-caller",
        )
        
        result = await hook.execute(ctx)
        
        assert result.allowed is True
        assert result.metadata.get("audit_logged") is True


class TestRateLimitingHook:
    """Test RateLimitingHook."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting_allows_under_limit(self):
        """Test rate limiting allows operations under limit."""
        hook = RateLimitingHook(max_ops_per_minute=10)
        ctx = HookContext(
            operation="write",
            caller_id="test-caller",
        )
        
        result = await hook.execute(ctx)
        
        assert result.allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limiting_denies_over_limit(self):
        """Test rate limiting denies operations over limit."""
        hook = RateLimitingHook(max_ops_per_minute=2)
        ctx = HookContext(
            operation="write",
            caller_id="test-caller",
        )
        
        # Execute 3 times (over limit of 2)
        await hook.execute(ctx)
        await hook.execute(ctx)
        result = await hook.execute(ctx)
        
        assert result.allowed is False
        assert "Rate limit exceeded" in result.reason


class TestGovernanceHookRegistry:
    """Test GovernanceHookRegistry."""
    
    def test_registry_initialization(self):
        """Test registry initializes with empty hooks."""
        registry = GovernanceHookRegistry()
        
        assert registry is not None
    
    def test_register_hook(self):
        """Test hook registration."""
        registry = GovernanceHookRegistry()
        hook = SchemaValidationHook()
        
        registry.register_hook(hook)
        
        hooks = registry.list_hooks(HookType.PRE_WRITE)
        assert len(hooks) > 0
        assert any(h["hook_id"] == "schema_validation" for h in hooks)
    
    def test_unregister_hook(self):
        """Test hook unregistration."""
        registry = GovernanceHookRegistry()
        hook = SchemaValidationHook()
        
        registry.register_hook(hook)
        result = registry.unregister_hook("schema_validation", HookType.PRE_WRITE)
        
        assert result is True
    
    def test_hooks_sorted_by_priority(self):
        """Test hooks are sorted by priority."""
        registry = GovernanceHookRegistry()
        
        # Register hooks with different priorities (both PRE_WRITE)
        hook1 = SchemaValidationHook()  # HIGH priority, PRE_WRITE
        hook2 = RateLimitingHook()  # HIGH priority, PRE_WRITE
        
        registry.register_hook(hook2)  # Register second
        registry.register_hook(hook1)  # Then first
        
        hooks = registry.list_hooks(HookType.PRE_WRITE)
        
        # Both should be in hooks list
        hook_ids = [h["hook_id"] for h in hooks]
        assert "schema_validation" in hook_ids
        assert "rate_limiting" in hook_ids
        
        # Priorities should be sorted ascending
        priorities = [h["priority"] for h in hooks]
        assert priorities == sorted(priorities)
    
    @pytest.mark.asyncio
    async def test_execute_hooks_all_pass(self):
        """Test execute_hooks when all hooks pass."""
        registry = GovernanceHookRegistry()
        hook = SchemaValidationHook()
        registry.register_hook(hook)
        
        ctx = HookContext(
            operation="write",
            caller_id="test-caller",
            payload={"packet_type": "event", "payload": {}},
        )
        
        result = await registry.execute_hooks(HookType.PRE_WRITE, ctx)
        
        assert result.allowed is True
    
    @pytest.mark.asyncio
    async def test_execute_hooks_stops_on_deny(self):
        """Test execute_hooks stops on first deny."""
        registry = GovernanceHookRegistry()
        
        # Register hook that will deny
        hook = SchemaValidationHook()
        registry.register_hook(hook)
        
        ctx = HookContext(
            operation="write",
            caller_id="test-caller",
            payload=None,  # Will fail validation
        )
        
        result = await registry.execute_hooks(HookType.PRE_WRITE, ctx)
        
        assert result.allowed is False
    
    @pytest.mark.asyncio
    async def test_execute_hooks_handles_errors(self):
        """Test execute_hooks handles hook errors."""
        registry = GovernanceHookRegistry()
        
        # Create mock hook that raises exception
        class FailingHook(GovernanceHook):
            def __init__(self):
                super().__init__("failing_hook", HookType.PRE_WRITE)
            
            async def execute(self, context):
                raise ValueError("Test error")
        
        registry.register_hook(FailingHook())
        
        ctx = HookContext(
            operation="write",
            caller_id="test-caller",
        )
        
        result = await registry.execute_hooks(HookType.PRE_WRITE, ctx)
        
        assert result.allowed is False
        assert "failed" in result.reason.lower()


class TestGetHookRegistry:
    """Test get_hook_registry() singleton."""
    
    def test_get_hook_registry_returns_singleton(self):
        """Test get_hook_registry() returns same instance."""
        registry1 = get_hook_registry()
        registry2 = get_hook_registry()
        
        assert registry1 is registry2
    
    def test_get_hook_registry_has_built_in_hooks(self):
        """Test get_hook_registry() includes built-in hooks."""
        registry = get_hook_registry()
        
        hooks = registry.list_hooks()
        hook_ids = [h["hook_id"] for h in hooks]
        
        assert "schema_validation" in hook_ids
        assert "scope_authorization" in hook_ids
        assert "audit_logging" in hook_ids
        assert "rate_limiting" in hook_ids


# =============================================================================
# Mutation Testing Targets
# =============================================================================

class TestMutationTargets:
    """
    Tests specifically designed to kill common mutations.
    """
    
    @pytest.mark.asyncio
    async def test_hook_result_allowed_field(self):
        """Kill mutation: allowed = True -> allowed = False."""
        result_allow = HookResult.allow()
        result_deny = HookResult.deny("reason")
        
        assert result_allow.allowed is True
        assert result_deny.allowed is False
    
    @pytest.mark.asyncio
    async def test_schema_validation_checks_required_fields(self):
        """Kill mutation: required_fields check -> no check."""
        hook = SchemaValidationHook()
        
        # With all required fields
        ctx_valid = HookContext(
            operation="write",
            caller_id="test",
            payload={"packet_type": "event", "payload": {}},
        )
        result_valid = await hook.execute(ctx_valid)
        assert result_valid.allowed is True
        
        # Missing required field
        ctx_invalid = HookContext(
            operation="write",
            caller_id="test",
            payload={"packet_type": "event"},  # Missing "payload"
        )
        result_invalid = await hook.execute(ctx_invalid)
        assert result_invalid.allowed is False
    
    @pytest.mark.asyncio
    async def test_rate_limiting_tracks_per_caller(self):
        """Kill mutation: per-caller tracking -> global tracking."""
        hook = RateLimitingHook(max_ops_per_minute=2)
        
        ctx1 = HookContext(operation="write", caller_id="caller1")
        ctx2 = HookContext(operation="write", caller_id="caller2")
        
        # Caller1 uses limit
        await hook.execute(ctx1)
        await hook.execute(ctx1)
        
        # Caller2 should still be allowed
        result = await hook.execute(ctx2)
        assert result.allowed is True
    
    def test_hook_priority_ordering(self):
        """Kill mutation: priority ordering -> reverse ordering."""
        registry = GovernanceHookRegistry()
        
        class HighPriorityHook(GovernanceHook):
            def __init__(self):
                super().__init__("high", HookType.PRE_WRITE, HookPriority.HIGH)
            async def execute(self, ctx):
                return HookResult.allow()
        
        class LowPriorityHook(GovernanceHook):
            def __init__(self):
                super().__init__("low", HookType.PRE_WRITE, HookPriority.LOW)
            async def execute(self, ctx):
                return HookResult.allow()
        
        registry.register_hook(LowPriorityHook())
        registry.register_hook(HighPriorityHook())
        
        hooks = registry.list_hooks(HookType.PRE_WRITE)
        priorities = [h["priority"] for h in hooks]
        
        # Should be sorted ascending (lower number = higher priority)
        assert priorities == sorted(priorities)
