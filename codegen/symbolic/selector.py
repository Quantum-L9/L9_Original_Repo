"""
Symbolic Code Selector
======================

Selects the best candidate from verified solutions.

Version: 1.0.0
"""

from __future__ import annotations


from typing import Any

import structlog

logger = structlog.get_logger(__name__)

from codegen.symbolic.spec import SymbolicCandidate, VerificationResult


class CandidateSelector:
    """
    Selects the best candidate from a list of verified candidates.

    Selection criteria:
    1. Must pass verification (equivalent + invariants)
    2. Prefer lower complexity score
    3. Prefer simpler code (shorter string length)
    """

    def __init__(self):
        """Initialize the selector."""
        pass

    def select(
        self,
        verifications: list[VerificationResult],
    ) -> tuple[SymbolicCandidate | None, dict[str, Any]]:
        """
        Select the best candidate from verified results.

        Args:
            verifications: List of verification results

        Returns:
            Tuple of (selected candidate or None, selection metadata)
        """
        metadata = {
            "total_candidates": len(verifications),
            "passed_verification": 0,
            "selection_rationale": "",
        }

        # Filter to passing candidates
        passing = [
            v
            for v in verifications
            if v.is_equivalent and v.all_invariants_pass and v.error is None
        ]

        metadata["passed_verification"] = len(passing)

        if not passing:
            metadata["selection_rationale"] = "No candidates passed verification"
            logger.warning("no_passing_candidates", total=len(verifications))
            return None, metadata

        # Sort by complexity (lower is better)
        passing.sort(
            key=lambda v: (
                v.candidate.complexity_score,
                len(v.candidate.code),
            )
        )

        selected = passing[0]

        metadata["selection_rationale"] = (
            f"Selected candidate with lowest complexity score "
            f"({selected.candidate.complexity_score:.2f})"
        )
        metadata["selected_transform"] = selected.candidate.metadata.get(
            "transform", "unknown"
        )

        logger.info(
            "candidate_selected",
            code=selected.candidate.code[:50],
            complexity=selected.candidate.complexity_score,
            transform=metadata["selected_transform"],
        )

        return selected.candidate, metadata


# Runtime execution trace - updated automatically on every execution
