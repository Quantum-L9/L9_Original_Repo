"""
Query Classifier Tests
======================

Tests for memory.query_classifier.QueryClassifier.
Verifies query pattern classification and weight overrides.
"""

from memory.query_classifier import QueryClassifier, get_query_classifier


class TestQueryClassifier:
    """Tests for QueryClassifier pattern classification."""

    def test_classifier_initialization(self):
        """Test QueryClassifier can be instantiated."""
        classifier = QueryClassifier()
        assert classifier is not None

    def test_singleton_pattern(self):
        """Test get_query_classifier returns singleton."""
        classifier1 = get_query_classifier()
        classifier2 = get_query_classifier()
        assert classifier1 is classifier2

    def test_classify_entity_lookup(self):
        """Test entity lookup pattern classification."""
        classifier = QueryClassifier()

        queries = [
            "Who is John?",
            "What is the entity X?",
            "Find me the person named Alice",
            "Lookup for user 123",
        ]

        for query in queries:
            pattern = classifier.classify_query(query)
            assert pattern == "entity_lookup", f"Expected entity_lookup for: {query}"

    def test_classify_reasoning_trace(self):
        """Test reasoning trace pattern classification."""
        classifier = QueryClassifier()

        queries = [
            "Why did the agent decide X?",
            "Show me the reasoning for packet abc-123",
            "Explain the decision chain",
            "Trace the reasoning path",
        ]

        for query in queries:
            pattern = classifier.classify_query(query)
            assert (
                pattern == "reasoning_trace"
            ), f"Expected reasoning_trace for: {query}"

    def test_classify_temporal(self):
        """Test temporal pattern classification."""
        classifier = QueryClassifier()

        queries = [
            "What happened last week?",
            "Recent changes to the system",
            "What happened yesterday?",
            "Latest updates",
        ]

        for query in queries:
            pattern = classifier.classify_query(query)
            assert pattern == "temporal", f"Expected temporal for: {query}"

    def test_classify_exploratory(self):
        """Test exploratory pattern classification."""
        classifier = QueryClassifier()

        queries = [
            "Tell me about X",
            "Explore the Y system",
            "What do we know about Z?",
            "Overview of the project",
        ]

        for query in queries:
            pattern = classifier.classify_query(query)
            assert pattern == "exploratory", f"Expected exploratory for: {query}"

    def test_classify_factual(self):
        """Test factual pattern classification."""
        classifier = QueryClassifier()

        queries = [
            "Get the value of X",
            "What is the fact about Y?",
            "Retrieve the data for Z",
            "Fetch the fact about status",
        ]

        for query in queries:
            pattern = classifier.classify_query(query)
            assert pattern == "factual", f"Expected factual for: {query}"

    def test_classify_default(self):
        """Test default pattern for unrecognized queries."""
        classifier = QueryClassifier()

        queries = [
            "Hello world",
            "Random text",
            "",
        ]

        for query in queries:
            pattern = classifier.classify_query(query)
            assert pattern == "default", f"Expected default for: {query}"

    def test_get_weight_overrides_entity_lookup(self):
        """Test weight overrides for entity_lookup pattern."""
        classifier = QueryClassifier()
        overrides = classifier.get_weight_overrides("entity_lookup")

        assert "graph_context" in overrides
        assert "semantic_hits" in overrides
        assert "recent" in overrides
        assert "facts" in overrides
        assert overrides["graph_context"] == 0.5  # Higher weight for entity lookups

    def test_get_weight_overrides_reasoning_trace(self):
        """Test weight overrides for reasoning_trace pattern."""
        classifier = QueryClassifier()
        overrides = classifier.get_weight_overrides("reasoning_trace")

        assert overrides["recent"] == 0.6  # Higher weight for recent reasoning

    def test_get_weight_overrides_temporal(self):
        """Test weight overrides for temporal pattern."""
        classifier = QueryClassifier()
        overrides = classifier.get_weight_overrides("temporal")

        assert overrides["recent"] == 0.6  # Temporal queries favor recent

    def test_get_weight_overrides_exploratory(self):
        """Test weight overrides for exploratory pattern."""
        classifier = QueryClassifier()
        overrides = classifier.get_weight_overrides("exploratory")

        assert overrides["semantic_hits"] == 0.5  # Exploratory favors semantic

    def test_get_weight_overrides_factual(self):
        """Test weight overrides for factual pattern."""
        classifier = QueryClassifier()
        overrides = classifier.get_weight_overrides("factual")

        assert overrides["facts"] == 0.4  # Factual queries favor facts

    def test_get_weight_overrides_default(self):
        """Test weight overrides for default pattern."""
        classifier = QueryClassifier()
        overrides = classifier.get_weight_overrides("default")

        assert "semantic_hits" in overrides
        assert "recent" in overrides
        assert "graph_context" in overrides
        assert "facts" in overrides

    def test_get_weight_overrides_unknown_pattern(self):
        """Test weight overrides fallback for unknown pattern."""
        classifier = QueryClassifier()
        overrides = classifier.get_weight_overrides("unknown_pattern")

        # Should return default overrides
        assert "semantic_hits" in overrides
        assert overrides == classifier.get_weight_overrides("default")
