# governance/__init__.py
"""
Governance Module - Enforcement and rejection recording.

Provides tools for recording governance violations, test failures,
and other negative memory (patterns to NOT repeat).
"""

from governance.rejection_recorder import (
    record_governance_violation,
    record_rejection,
    record_test_failure,
)

__all__ = [
    "record_governance_violation",
    "record_rejection",
    "record_test_failure",
]
