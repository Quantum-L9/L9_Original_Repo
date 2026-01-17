"""
L9 Evolution Orchestrator - Interface
Version: 1.0.0

Applies architectural upgrades to L9 (patch → deploy).
Manages system evolution through controlled upgrades.
"""

from typing import Protocol, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
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
    changes: List[Dict[str, Any]] = Field(..., description="List of changes")
    dependencies: List[str] = Field(
        default_factory=list, description="Required upgrades"
    )
    rollback_plan: Optional[str] = Field(default=None, description="How to rollback")


class UpgradeValidation(BaseModel):
    """Validation results for an upgrade."""

    upgrade_id: str = Field(..., description="Upgrade being validated")
    is_valid: bool = Field(..., description="Whether upgrade is valid")
    checks_passed: List[str] = Field(..., description="Validation checks that passed")
    checks_failed: List[str] = Field(..., description="Validation checks that failed")
    warnings: List[str] = Field(
        default_factory=list, description="Non-blocking warnings"
    )
    estimated_downtime: Optional[int] = Field(
        default=None, description="Estimated downtime in seconds"
    )


class UpgradeExecution(BaseModel):
    """Execution record for an upgrade."""

    upgrade_id: str = Field(..., description="Upgrade being executed")
    status: UpgradeStatus = Field(..., description="Current status")
    started_at: datetime = Field(..., description="When execution started")
    completed_at: Optional[datetime] = Field(
        default=None, description="When execution completed"
    )
    steps_completed: List[str] = Field(
        default_factory=list, description="Completed steps"
    )
    steps_remaining: List[str] = Field(
        default_factory=list, description="Remaining steps"
    )
    error: Optional[str] = Field(default=None, description="Error if failed")


class EvolutionOrchestratorRequest(BaseModel):
    """Request to evolution orchestrator."""

    upgrades: List[Upgrade] = Field(..., description="Upgrades to apply")
    validate_only: bool = Field(default=False, description="Only validate, don't apply")
    allow_downtime: bool = Field(
        default=False, description="Allow downtime during upgrade"
    )
    auto_rollback: bool = Field(default=True, description="Auto rollback on failure")


class EvolutionOrchestratorResponse(BaseModel):
    """Response from evolution orchestrator."""

    validations: List[UpgradeValidation] = Field(..., description="Validation results")
    executions: List[UpgradeExecution] = Field(
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
    async def rollback_upgrade(self, upgrade_id: str) -> Dict[str, Any]:
        """Rollback a previously applied upgrade."""
        ...

    @must_stay_async("callers use await")
    async def get_upgrade_history(self, limit: int = 10) -> List[UpgradeExecution]:
        """Get history of applied upgrades."""
        ...
