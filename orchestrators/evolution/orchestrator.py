"""
L9 Evolution Orchestrator - Implementation
Version: 1.0.0

Concrete implementation of evolution orchestration logic.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Implementation",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "orchestrator",
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

from datetime import UTC, datetime, timezone
from typing import Any

import structlog

from core.decorators import must_stay_async

from .apply_engine import ApplyEngine
from .interface import (
    EvolutionOrchestratorRequest,
    EvolutionOrchestratorResponse,
    IEvolutionOrchestrator,
    Upgrade,
    UpgradeExecution,
    UpgradeStatus,
    UpgradeValidation,
)

logger = structlog.get_logger(__name__)


class EvolutionOrchestrator(IEvolutionOrchestrator):
    """
    Evolution Orchestrator implementation.

    Manages the lifecycle of system upgrades:
    1. Validate upgrades
    2. Check dependencies
    3. Apply changes
    4. Test results
    5. Rollback on failure
    """

    def __init__(self, apply_engine: ApplyEngine):
        """Initialize evolution orchestrator."""
        self._engine = apply_engine
        self._history: list[UpgradeExecution] = []
        logger.info("EvolutionOrchestrator initialized")

    async def apply_upgrades(
        self, request: EvolutionOrchestratorRequest
    ) -> EvolutionOrchestratorResponse:
        """Apply architectural upgrades to the system."""
        logger.info(f"Processing {len(request.upgrades)} upgrades")

        validations = []
        for upgrade in request.upgrades:
            validation = await self.validate_upgrade(upgrade)
            validations.append(validation)

        if any(not v.is_valid for v in validations):
            failed_ids = [v.upgrade_id for v in validations if not v.is_valid]
            return EvolutionOrchestratorResponse(
                validations=validations,
                executions=[],
                final_version=request.upgrades[0].version_from,
                success=False,
                message=f"Validation failed for upgrades: {', '.join(failed_ids)}",
            )

        if request.validate_only:
            return EvolutionOrchestratorResponse(
                validations=validations,
                executions=[],
                final_version=request.upgrades[-1].version_to,
                success=True,
                message="Validation successful (not applied)",
            )

        sorted_upgrades = self._sort_by_dependencies(request.upgrades)
        executions = []
        current_version = sorted_upgrades[0].version_from

        for upgrade in sorted_upgrades:
            execution = await self._apply_single_upgrade(
                upgrade, request.allow_downtime
            )
            executions.append(execution)
            self._history.append(execution)

            if execution.status == UpgradeStatus.FAILED:
                logger.error(f"Upgrade {upgrade.id} failed: {execution.error}")
                if request.auto_rollback:
                    logger.info(f"Auto-rolling back {upgrade.id}")
                    await self.rollback_upgrade(upgrade.id)

                return EvolutionOrchestratorResponse(
                    validations=validations,
                    executions=executions,
                    final_version=current_version,
                    success=False,
                    message=f"Upgrade {upgrade.id} failed: {execution.error}",
                )

            current_version = upgrade.version_to

        return EvolutionOrchestratorResponse(
            validations=validations,
            executions=executions,
            final_version=current_version,
            success=True,
            message=f"Successfully upgraded to {current_version}",
        )

    @must_stay_async("callers use await")
    async def validate_upgrade(self, upgrade: Upgrade) -> UpgradeValidation:
        """Validate an upgrade before applying."""
        logger.info(f"Validating upgrade: {upgrade.id}")

        checks_passed = []
        checks_failed = []
        warnings = []

        if self._is_version_compatible(upgrade.version_from, upgrade.version_to):
            checks_passed.append("Version compatibility")
        else:
            checks_failed.append("Version compatibility: incompatible versions")

        missing_deps = self._check_dependencies(upgrade)
        if not missing_deps:
            checks_passed.append("Dependencies satisfied")
        else:
            checks_failed.append(f"Missing dependencies: {', '.join(missing_deps)}")

        if upgrade.type == "major" and not upgrade.rollback_plan:
            warnings.append("No rollback plan for major upgrade")
        else:
            checks_passed.append("Rollback plan present")

        if self._validate_changes(upgrade.changes):
            checks_passed.append("Changes validated")
        else:
            checks_failed.append("Invalid changes detected")

        estimated_downtime = self._estimate_downtime(upgrade)
        is_valid = len(checks_failed) == 0

        return UpgradeValidation(
            upgrade_id=upgrade.id,
            is_valid=is_valid,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            warnings=warnings,
            estimated_downtime=estimated_downtime,
        )

    async def rollback_upgrade(self, upgrade_id: str) -> dict[str, Any]:
        """Rollback a previously applied upgrade."""
        logger.info(f"Rolling back upgrade: {upgrade_id}")

        execution = next((e for e in self._history if e.upgrade_id == upgrade_id), None)

        if not execution:
            return {
                "success": False,
                "message": f"Upgrade {upgrade_id} not found in history",
            }

        if execution.status != UpgradeStatus.DEPLOYED:
            return {
                "success": False,
                "message": f"Upgrade {upgrade_id} is not deployed (status: {execution.status})",
            }

        rollback_result = await self._engine.rollback(upgrade_id)
        execution.status = UpgradeStatus.ROLLED_BACK
        execution.completed_at = datetime.now(UTC)

        return rollback_result

    @must_stay_async("callers use await")
    async def get_upgrade_history(self, limit: int = 10) -> list[UpgradeExecution]:
        """Get history of applied upgrades."""
        return self._history[-limit:]

    async def _apply_single_upgrade(
        self, upgrade: Upgrade, allow_downtime: bool
    ) -> UpgradeExecution:
        """Apply a single upgrade."""
        execution = UpgradeExecution(
            upgrade_id=upgrade.id,
            status=UpgradeStatus.APPLYING,
            started_at=datetime.now(UTC),
            steps_completed=[],
            steps_remaining=[f"Step {i + 1}" for i in range(len(upgrade.changes))],
        )

        try:
            result = await self._engine.apply(upgrade, allow_downtime)
            if result["success"]:
                execution.status = UpgradeStatus.DEPLOYED
                execution.steps_completed = execution.steps_remaining
                execution.steps_remaining = []
            else:
                execution.status = UpgradeStatus.FAILED
                execution.error = result.get("error", "Unknown error")
        except Exception as e:
            logger.exception(f"Error applying upgrade {upgrade.id}")
            execution.status = UpgradeStatus.FAILED
            execution.error = str(e)

        execution.completed_at = datetime.now(UTC)
        return execution

    def _sort_by_dependencies(self, upgrades: list[Upgrade]) -> list[Upgrade]:
        """Sort upgrades by dependencies (topological sort)."""
        sorted_upgrades = []
        remaining = upgrades.copy()

        while remaining:
            ready = [
                u
                for u in remaining
                if all(dep in [s.id for s in sorted_upgrades] for dep in u.dependencies)
            ]
            if not ready:
                logger.warning("Circular or missing dependencies detected")
                sorted_upgrades.extend(remaining)
                break
            sorted_upgrades.extend(ready)
            for u in ready:
                remaining.remove(u)

        return sorted_upgrades

    def _is_version_compatible(self, version_from: str, version_to: str) -> bool:
        """Check if version upgrade is compatible."""
        try:
            from_parts = [int(x) for x in version_from.split(".")]
            to_parts = [int(x) for x in version_to.split(".")]
            return not to_parts[0] < from_parts[0]
        except (ValueError, IndexError):
            return False

    def _check_dependencies(self, upgrade: Upgrade) -> list[str]:
        """Check if all dependencies are satisfied."""
        missing = []
        for dep_id in upgrade.dependencies:
            if not any(e.upgrade_id == dep_id for e in self._history):
                missing.append(dep_id)
        return missing

    def _validate_changes(self, changes: list[dict[str, Any]]) -> bool:
        """Validate that changes are well-formed."""
        for change in changes:
            if "type" not in change or "target" not in change:
                return False
        return True

    def _estimate_downtime(self, upgrade: Upgrade) -> int:
        """Estimate downtime in seconds."""
        base_time = 10
        per_change_time = 5
        return base_time + (len(upgrade.changes) * per_change_time)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-022",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "async",
        "intelligence",
        "logging",
        "messaging",
        "orchestration",
        "service",
        "testing",
    ],
    "keywords": [
        "apply",
        "evolution",
        "history",
        "implementation",
        "orchestrator",
        "rollback",
        "upgrade",
        "upgrades",
    ],
    "business_value": "Implements EvolutionOrchestrator for orchestrator functionality",
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
