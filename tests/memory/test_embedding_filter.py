"""
Test embedding skip filter (GMP-42).

Verifies that low-value content patterns are correctly filtered from semantic embedding.
"""

import sys
from pathlib import Path

# Ensure project root is in path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from memory.substrate_dag import (SKIP_EMBEDDING_PATTERNS,
                                  _should_skip_embedding)


class TestShouldSkipEmbedding:
    """Tests for _should_skip_embedding filter function."""

    def test_skip_exact_error_patterns(self):
        """Known error messages should be skipped."""
        for pattern in SKIP_EMBEDDING_PATTERNS:
            assert _should_skip_embedding(pattern) is True, f"Should skip: {pattern}"

    def test_skip_error_pattern_with_whitespace(self):
        """Patterns with leading/trailing whitespace should still be skipped."""
        assert (
            _should_skip_embedding(
                "  Sorry, I encountered a temporary error. Please try again.  "
            )
            is True
        )

    def test_skip_error_prefix_variants(self):
        """Error messages starting with known prefixes should be skipped."""
        assert (
            _should_skip_embedding("Sorry, I encountered an unexpected issue.") is True
        )
        assert _should_skip_embedding("❌ Mac command error: timeout") is True
        assert (
            _should_skip_embedding("❌ Please provide a command after `!mac`") is True
        )

    def test_skip_empty_content(self):
        """Empty or None content should be skipped."""
        assert _should_skip_embedding("") is True
        assert _should_skip_embedding(None) is True
        assert _should_skip_embedding("   ") is True

    def test_skip_very_short_content(self):
        """Content under 10 chars should be skipped."""
        assert _should_skip_embedding("hi") is True
        assert _should_skip_embedding("ok") is True
        assert _should_skip_embedding("123456789") is True  # 9 chars

    def test_allow_valid_content(self):
        """Legitimate content should NOT be skipped."""
        # Normal user messages
        assert _should_skip_embedding("What is the status of the deployment?") is False
        assert (
            _should_skip_embedding("Please analyze the memory substrate performance.")
            is False
        )

        # Agent responses with actual content
        assert (
            _should_skip_embedding(
                "The deployment completed successfully at 14:32 EST."
            )
            is False
        )
        assert (
            _should_skip_embedding(
                "I found 3 relevant documents in the knowledge base."
            )
            is False
        )

        # Technical content
        assert (
            _should_skip_embedding(
                "ERROR: Connection timeout to database l9-postgres:5432"
            )
            is False
        )
        assert (
            _should_skip_embedding(
                "def process_packet(envelope): return envelope.payload"
            )
            is False
        )

    def test_allow_content_at_boundary(self):
        """Content at exactly 10 chars should be allowed."""
        assert _should_skip_embedding("1234567890") is False  # 10 chars - allowed
        assert _should_skip_embedding("Hello Igor") is False  # 10 chars - allowed

    def test_skip_patterns_list_not_empty(self):
        """SKIP_EMBEDDING_PATTERNS should contain patterns."""
        assert len(SKIP_EMBEDDING_PATTERNS) >= 4, "Should have at least 4 skip patterns"

    def test_skip_patterns_are_strings(self):
        """All skip patterns should be non-empty strings."""
        for pattern in SKIP_EMBEDDING_PATTERNS:
            assert isinstance(pattern, str), f"Pattern should be string: {pattern}"
            assert len(pattern) > 0, "Pattern should not be empty"
