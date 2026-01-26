"""
L9 Input Segmenter
==================

Harvested from igor/01-09-2025/tokenizer/core/tokenizer - Segmentation concept only.

Converts multi-part user directives into atomic task segments that can be
routed individually through TaskRouter.

Pipeline Position:
    User Input → InputSegmenter.segment() → TaskRouter.route() × N

Handles:
- Comma-separated directives: "Deploy RIL, test ToT, sync DB"
- Sequential directives: "Deploy RIL then test ToT"
- Multi-line input
- Basic normalization (lowercase, abbreviation expansion)

Usage:
    segmenter = InputSegmenter()
    segments = segmenter.segment("Deploy RIL, test ToT, sync Supabase")
    # ["deploy ril", "test tot", "sync supabase"]

Version: 1.0.0
Harvested: 2026-01-19 from tokenizer/core/tokenizer/tokenizer.py
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Input Segmenter",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-20T14:03:16Z",
    "updated_at": "2026-01-24T13:02:52Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "input_segmenter",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "api.agent_routes",
            "memory.slack_ingest",
            "orchestration.__init__",
            "orchestration.unified_controller",
            "runtime.websocket_orchestrator",
            "tests.orchestration.test_input_segmenter",
        ],
    },
}
# ============================================================================

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class SegmenterConfig:
    """Configuration for input segmentation."""

    # Separators for splitting directives
    separators: List[str] = field(
        default_factory=lambda: [
            r",\s*",  # Comma with optional whitespace
            r"\s+then\s+",  # "then" keyword
            r"\s+and\s+then\s+",  # "and then"
            r";\s*",  # Semicolon
        ]
    )

    # Abbreviations to expand (from tokenizer)
    abbreviations: Dict[str, str] = field(
        default_factory=lambda: {
            "db": "database",
            "sync'd": "synced",
            "gen": "generate",
            "impl": "implement",
            "auth": "authentication",
            "config": "configuration",
            "env": "environment",
        }
    )

    # Minimum segment length to keep (filter noise)
    min_segment_length: int = 2

    # Whether to normalize to lowercase
    normalize_case: bool = True

    # Whether to expand abbreviations
    expand_abbreviations: bool = True


# =============================================================================
# Segment Result
# =============================================================================


@dataclass
class SegmentResult:
    """Result of segmentation with metadata."""

    segments: List[str]
    raw_input: str
    segment_count: int
    was_multi_part: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __iter__(self):
        return iter(self.segments)

    def __len__(self):
        return len(self.segments)


# =============================================================================
# Input Segmenter
# =============================================================================


class InputSegmenter:
    """
    Segments multi-part user input into atomic directives.

    Harvested from tokenizer pipeline - this is the nervous system preprocessing
    that allows L9 to handle compound instructions like:

        "Deploy RIL, test ToT, sync Supabase, then generate plan v3"

    Which becomes 4 separate tasks that can be routed and executed independently.
    """

    def __init__(self, config: Optional[SegmenterConfig] = None):
        """
        Initialize segmenter.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or SegmenterConfig()

        # Compile separator patterns
        self._separator_pattern = re.compile(
            "|".join(f"({sep})" for sep in self.config.separators), re.IGNORECASE
        )

        logger.info(
            "InputSegmenter initialized",
            separators=len(self.config.separators),
            abbreviations=len(self.config.abbreviations),
        )

    # =========================================================================
    # Main Entry Point
    # =========================================================================

    def segment(
        self, input_text: str, context: Optional[Dict[str, Any]] = None
    ) -> SegmentResult:
        """
        Segment input into atomic directives.

        Pipeline:
        1. Split on newlines (multi-line handling)
        2. Split on separators (comma, then, semicolon)
        3. Normalize each segment
        4. Filter empty/short segments

        Args:
            input_text: Raw user input text
            context: Optional context for conditional logic

        Returns:
            SegmentResult with list of normalized segments
        """
        if not input_text or not input_text.strip():
            return SegmentResult(
                segments=[],
                raw_input=input_text or "",
                segment_count=0,
                was_multi_part=False,
            )

        # Step 1: Handle multi-line
        lines = input_text.strip().split("\n")

        # Step 2: Split each line on separators
        segments = []
        for line in lines:
            parts = self._split_on_separators(line)
            segments.extend(parts)

        # Step 3: Normalize
        normalized = [self._normalize(seg) for seg in segments]

        # Step 4: Filter
        filtered = [
            seg
            for seg in normalized
            if seg and len(seg) >= self.config.min_segment_length
        ]

        result = SegmentResult(
            segments=filtered,
            raw_input=input_text,
            segment_count=len(filtered),
            was_multi_part=len(filtered) > 1,
            metadata={
                "original_lines": len(lines),
                "pre_filter_count": len(normalized),
            },
        )

        logger.info(
            "Segmented input",
            segment_count=result.segment_count,
            was_multi_part=result.was_multi_part,
            input_preview=(
                input_text[:50] + "..." if len(input_text) > 50 else input_text
            ),
        )

        return result

    # =========================================================================
    # Segmentation Logic (Harvested from tokenizer._segment)
    # =========================================================================

    def _split_on_separators(self, line: str) -> List[str]:
        """
        Split a line on configured separators.

        Handles:
        - "Deploy RIL, test ToT" → ["Deploy RIL", "test ToT"]
        - "Deploy RIL then test ToT" → ["Deploy RIL", "test ToT"]
        - "A; B; C" → ["A", "B", "C"]

        Args:
            line: Single line of input

        Returns:
            List of segments
        """
        # Split on pattern
        parts = self._separator_pattern.split(line)

        # Filter out separator matches and empty strings
        segments = [
            p.strip() for p in parts if p and p.strip() and not self._is_separator(p)
        ]

        return segments

    def _is_separator(self, text: str) -> bool:
        """Check if text is just a separator."""
        normalized = text.strip().lower()
        return normalized in ["then", "and then", ",", ";", ""]

    # =========================================================================
    # Normalization Logic (Harvested from tokenizer._normalize)
    # =========================================================================

    def _normalize(self, segment: str) -> str:
        """
        Normalize a segment.

        - Lowercase (optional)
        - Remove extra whitespace
        - Expand abbreviations (optional)

        Args:
            segment: Segment to normalize

        Returns:
            Normalized segment
        """
        if not segment:
            return ""

        normalized = segment

        # Lowercase
        if self.config.normalize_case:
            normalized = normalized.lower()

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        # Expand abbreviations
        if self.config.expand_abbreviations:
            for abbr, full in self.config.abbreviations.items():
                # Word boundary matching to avoid partial replacements
                pattern = rf"\b{re.escape(abbr)}\b"
                normalized = re.sub(pattern, full, normalized, flags=re.IGNORECASE)

        return normalized

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def segment_to_tasks(
        self, input_text: str, base_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Segment input and return task dicts ready for TaskRouter.

        Convenience method that wraps segment() and produces task dicts
        with proper structure for TaskRouter.route().

        Args:
            input_text: Raw user input
            base_context: Context to include in all tasks

        Returns:
            List of task dicts ready for TaskRouter
        """
        result = self.segment(input_text)

        tasks = []
        for i, segment in enumerate(result.segments):
            task = {
                "text": segment,
                "sequence_index": i,
                "total_in_sequence": result.segment_count,
                "from_multi_part": result.was_multi_part,
                "raw_input": result.raw_input,
            }
            if base_context:
                task["context"] = base_context
            tasks.append(task)

        return tasks

    def is_multi_part(self, input_text: str) -> bool:
        """
        Quick check if input contains multiple directives.

        Args:
            input_text: Input to check

        Returns:
            True if input would segment into multiple parts
        """
        return self._separator_pattern.search(input_text) is not None


# =============================================================================
# Module-Level Convenience Functions
# =============================================================================

# Singleton instance for simple usage
_default_segmenter: Optional[InputSegmenter] = None


def get_segmenter() -> InputSegmenter:
    """Get or create the default segmenter instance."""
    global _default_segmenter
    if _default_segmenter is None:
        _default_segmenter = InputSegmenter()
    return _default_segmenter


def segment_input(input_text: str) -> SegmentResult:
    """
    Segment input using default segmenter.

    Convenience function for quick segmentation.

    Args:
        input_text: Raw input text

    Returns:
        SegmentResult with segments
    """
    return get_segmenter().segment(input_text)


def segment_to_tasks(
    input_text: str, context: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Segment input to task dicts using default segmenter.

    Args:
        input_text: Raw input text
        context: Optional context

    Returns:
        List of task dicts for TaskRouter
    """
    return get_segmenter().segment_to_tasks(input_text, context)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "InputSegmenter",
    "SegmenterConfig",
    "SegmentResult",
    "get_segmenter",
    "segment_input",
    "segment_to_tasks",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-003",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "dataclass",
        "intelligence",
        "logging",
        "orchestration",
        "testing",
    ],
    "keywords": [
        "core",
        "deploy",
        "directives",
        "harvested",
        "inputsegmenter",
        "multi",
        "part",
        "segment",
    ],
    "business_value": "Segments multi-part user directives into atomic tasks for independent routing and execution. Handles comma-separated commands ('Deploy RIL, test ToT'), sequential directives ('Deploy then test'), multi-line input, and normalization with abbreviation expansion. Critical preprocessing layer for compound instruction handling.",
    "last_modified": "2026-01-24T13:02:52Z",
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
