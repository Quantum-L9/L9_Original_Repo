"""
L9 CA Governance Module
========================
Governance layer for CA (Coding Agent) code changes.

This module provides:
- Diff generation for code changes
- Report generation explaining changes
- Constraint validation
- Code change orchestration

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

from .ca_code_change import CACodeChange, ChangeProposal, ChangeStatus
from .constraint_validator import (
    ConstraintValidator,
    ValidationResult,
    Violation,
    ViolationSeverity,
)
from .diff_generator import BatchDiff, DiffGenerator, FileDiff
from .report_generator import ChangeReport, ChangeType, ReportGenerator

__all__ = [
    # Diff generation
    "DiffGenerator",
    "FileDiff",
    "BatchDiff",
    # Report generation
    "ReportGenerator",
    "ChangeReport",
    "ChangeType",
    # Constraint validation
    "ConstraintValidator",
    "Violation",
    "ViolationSeverity",
    "ValidationResult",
    # Orchestration
    "CACodeChange",
    "ChangeProposal",
    "ChangeStatus",
]
