"""
L9 ActionTool Orchestrator - Validator
Version: 1.0.0

Specialized component for action_tool orchestration.
Handles tool validation and safety checks.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Validator",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "validator",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from typing import Any, Dict, List, Optional, Set

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# GMP-104: Tool risk classification loaded from config/policies/high_risk_tools.yaml
from core.governance.tool_risk_policy import (  # noqa: E402
    get_high_risk_tools, get_igor_approval_tools, get_safe_tools)

HIGH_RISK_TOOLS: Set[str] = get_high_risk_tools()
IGOR_APPROVAL_REQUIRED: Set[str] = get_igor_approval_tools()
SAFE_TOOLS: Set[str] = get_safe_tools()


class ValidationResult:
    """Result of tool validation."""

    def __init__(
        self,
        valid: bool,
        tool_id: str,
        safety_level: str = "safe",
        requires_approval: bool = False,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ):
        self.valid = valid
        self.tool_id = tool_id
        self.safety_level = safety_level
        self.requires_approval = requires_approval
        self.errors = errors or []
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "tool_id": self.tool_id,
            "safety_level": self.safety_level,
            "requires_approval": self.requires_approval,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class Validator:
    """
    Validator for ActionTool Orchestrator.

    Validates tools and checks safety constraints:
    - Tool existence in registry
    - Safety level assessment
    - Governance approval requirements
    - Argument validation
    """

    def __init__(self, tool_registry: Optional[Any] = None):
        """
        Initialize validator.

        Args:
            tool_registry: Optional ExecutorToolRegistry instance.
        """
        self._registry = tool_registry
        logger.info("Validator initialized")

    @must_stay_async("callers use await")
    async def _get_registry(self) -> Optional[Any]:
        """Get or lazily load the tool registry."""
        if self._registry is None:
            try:
                from core.tools.registry_adapter import \
                    get_executor_tool_registry

                self._registry = get_executor_tool_registry()
            except ImportError:
                logger.warning("Tool registry not available")
                return None
        return self._registry

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process validation request.

        Legacy interface - validates tool_id from data.
        """
        tool_id = data.get("tool_id", "")
        arguments = data.get("arguments", {})

        result = await self.validate_tool(tool_id, arguments)
        return result.to_dict()

    async def validate_tool(
        self,
        tool_id: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Validate a tool call.

        Args:
            tool_id: Canonical tool identity
            arguments: Tool arguments
            context: Optional execution context

        Returns:
            ValidationResult with validity, safety level, and any errors
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Basic validation
        if not tool_id:
            return ValidationResult(
                valid=False,
                tool_id=tool_id,
                errors=["Tool ID is required"],
            )

        # Determine safety level
        safety_level = self._assess_safety_level(tool_id)
        requires_approval = self._requires_approval(tool_id, context)

        # Check if tool exists in registry
        registry = await self._get_registry()
        if registry:
            tool_list = registry.list_tools() if hasattr(registry, "list_tools") else []
            tool_ids = [t.get("id", "") for t in tool_list]

            if tool_id not in tool_ids:
                # Not a hard error - tool might be dynamically registered
                warnings.append(f"Tool '{tool_id}' not found in registry")

        # Check governance if available
        if context and context.get("governance_engine"):
            gov_result = await self._check_governance(tool_id, arguments, context)
            if not gov_result.get("allowed", True):
                errors.append(gov_result.get("reason", "Governance denied"))

        # Validate arguments if schema available
        arg_errors = await self._validate_arguments(tool_id, arguments)
        errors.extend(arg_errors)

        return ValidationResult(
            valid=len(errors) == 0,
            tool_id=tool_id,
            safety_level=safety_level,
            requires_approval=requires_approval,
            errors=errors,
            warnings=warnings,
        )

    def _assess_safety_level(self, tool_id: str) -> str:
        """Assess the safety level of a tool."""
        if tool_id in HIGH_RISK_TOOLS:
            return "dangerous"
        if tool_id in IGOR_APPROVAL_REQUIRED:
            return "requires_approval"
        if tool_id in SAFE_TOOLS:
            return "safe"
        return "requires_approval"  # Default to requiring approval

    def _requires_approval(
        self,
        tool_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if tool requires human approval."""
        if tool_id in IGOR_APPROVAL_REQUIRED:
            return True
        if tool_id in HIGH_RISK_TOOLS:
            return True
        if context and context.get("require_all_approvals"):
            return True
        return False

    async def _check_governance(
        self,
        tool_id: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check governance policies for tool execution."""
        gov_engine = context.get("governance_engine")
        if not gov_engine:
            return {"allowed": True}

        try:
            # Check policy if governance engine supports it
            if hasattr(gov_engine, "evaluate_tool_call"):
                return await gov_engine.evaluate_tool_call(tool_id, arguments, context)
            return {"allowed": True}
        except Exception as e:
            logger.warning(f"Governance check failed: {e}")
            return {"allowed": True}  # Fail open for now

    async def _validate_arguments(
        self,
        tool_id: str,
        arguments: Dict[str, Any],
    ) -> List[str]:
        """Validate tool arguments against schema."""
        errors = []

        # Get schema from registry if available
        registry = await self._get_registry()
        if registry and hasattr(registry, "_get_tool_schema"):
            schema = registry._get_tool_schema(tool_id)

            # Check required properties
            required = schema.get("required", [])
            for prop in required:
                if prop not in arguments:
                    errors.append(f"Missing required argument: {prop}")

        return errors


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-002",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "core.tools.registry_adapter"],
    "tags": [
        "async",
        "intelligence",
        "logging",
        "orchestration",
        "service",
        "validation",
    ],
    "keywords": [
        "orchestrator",
        "process",
        "tool",
        "validate",
        "validation",
        "validator",
    ],
    "business_value": "Handles tool validation and safety checks.",
    "last_modified": "2026-01-17T23:47:56Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
