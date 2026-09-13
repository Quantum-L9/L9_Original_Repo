"""
L9 Evolution Orchestrator - Interface
Version: 1.0.0

Applies architectural upgrades to L9 (patch → deploy).
Manages system evolution through controlled upgrades.
"""


from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field

from core.decorators import must_stay_async


class UpgradeType(str, Enum):
    """Types of upgrades that can be applied."""

    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"
    HOTFIX = "hotfix"


class UpgradeStatus(str, Enum):
    """Status of an upgrade."""

    PENDING = "pending"
    VALIDATING = "validating"
    APPLYING = "applying"
    TESTING = "testing"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class Upgrade(BaseModel):
    """An architectural upgrade."""

    id: str = Field(..., description="Unique upgrade ID")
    type: UpgradeType = Field(..., description="Upgrade type")
    version_from: str = Field(..., description="Current version")
    version_to: str = Field(..., description="Target version")
    description: str = Field(..., description="What this upgrade does")
    changes: list[dict[str, Any]] = Field(..., description="List of changes")
    dependencies: list[str] = Field(
        default_factory=list, description="Required upgrades"
    )
    rollback_plan: str | None = Field(default=None, description="How to rollback")


class UpgradeValidation(BaseModel):
    """Validation results for an upgrade."""

    upgrade_id: str = Field(..., description="Upgrade being validated")
    is_valid: bool = Field(..., description="Whether upgrade is valid")
    checks_passed: list[str] = Field(..., description="Validation checks that passed")
    checks_failed: list[str] = Field(..., description="Validation checks that failed")
    warnings: list[str] = Field(
        default_factory=list, description="Non-blocking warnings"
    )
    estimated_downtime: int | None = Field(
        default=None, description="Estimated downtime in seconds"
    )


class UpgradeExecution(BaseModel):
    """Execution record for an upgrade."""

    upgrade_id: str = Field(..., description="Upgrade being executed")
    status: UpgradeStatus = Field(..., description="Current status")
    started_at: datetime = Field(..., description="When execution started")
    completed_at: datetime | None = Field(
        default=None, description="When execution completed"
    )
    steps_completed: list[str] = Field(
        default_factory=list, description="Completed steps"
    )
    steps_remaining: list[str] = Field(
        default_factory=list, description="Remaining steps"
    )
    error: str | None = Field(default=None, description="Error if failed")


class EvolutionOrchestratorRequest(BaseModel):
    """Request to evolution orchestrator."""

    upgrades: list[Upgrade] = Field(..., description="Upgrades to apply")
    validate_only: bool = Field(default=False, description="Only validate, don't apply")
    allow_downtime: bool = Field(
        default=False, description="Allow downtime during upgrade"
    )
    auto_rollback: bool = Field(default=True, description="Auto rollback on failure")


class EvolutionOrchestratorResponse(BaseModel):
    """Response from evolution orchestrator."""

    validations: list[UpgradeValidation] = Field(..., description="Validation results")
    executions: list[UpgradeExecution] = Field(
        default_factory=list, description="Execution records"
    )
    final_version: str = Field(..., description="Final system version")
    success: bool = Field(..., description="Whether all upgrades succeeded")
    message: str = Field(..., description="Summary message")


class IEvolutionOrchestrator(Protocol):
    """Interface for Evolution Orchestrator."""

    @must_stay_async("callers use await")
    async def apply_upgrades(
        self, request: EvolutionOrchestratorRequest
    ) -> EvolutionOrchestratorResponse:
        """Apply architectural upgrades to the system."""
        ...

    @must_stay_async("callers use await")
    async def validate_upgrade(self, upgrade: Upgrade) -> UpgradeValidation:
        """Validate an upgrade before applying."""
        ...

    @must_stay_async("callers use await")
    async def rollback_upgrade(self, upgrade_id: str) -> dict[str, Any]:
        """Rollback a previously applied upgrade."""
        ...

    @must_stay_async("callers use await")
    async def get_upgrade_history(self, limit: int = 10) -> list[UpgradeExecution]:
        """Get history of applied upgrades."""
        ...


# Runtime execution trace - updated automatically on every execution
