"""
L9 ADR (Architecture Decision Records) Tooling

This package provides CLI tools for managing ADRs in the L9 repository.

Usage:
    python -m tools.adr new "Use Protocol Buffers for IPC"
    python -m tools.adr list
    python -m tools.adr show 0042
    python -m tools.adr validate
"""

from tools.adr.adr_cli import main
from tools.adr.adr_enforcer import ADREnforcementValidator, Violation, ValidationReport

__all__ = ["main", "ADREnforcementValidator", "Violation", "ValidationReport"]
