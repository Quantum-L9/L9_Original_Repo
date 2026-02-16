"""
Tests for InputSegmenter - Harvested from tokenizer pipeline.
"""

from orchestration.input_segmenter import (
    InputSegmenter,
    SegmenterConfig,
    segment_input,
    segment_to_tasks,
)


class TestInputSegmenter:
    """Test InputSegmenter functionality."""

    def test_basic_segmentation(self):
        """Test single directive passes through."""
        segmenter = InputSegmenter()
        result = segmenter.segment("Deploy RIL")

        assert result.segment_count == 1
        assert result.was_multi_part is False
        assert "deploy ril" in result.segments

    def test_comma_separated(self):
        """Test comma-separated directives."""
        segmenter = InputSegmenter()
        result = segmenter.segment("Deploy RIL, test ToT, sync Substrate")

        assert result.segment_count == 3
        assert result.was_multi_part is True
        assert "deploy ril" in result.segments
        assert "test tot" in result.segments
        assert "sync substrate" in result.segments

    def test_then_separator(self):
        """Test 'then' keyword separates directives."""
        segmenter = InputSegmenter()
        result = segmenter.segment("Deploy RIL then test ToT")

        assert result.segment_count == 2
        assert "deploy ril" in result.segments
        assert "test tot" in result.segments

    def test_multiline(self):
        """Test multi-line input."""
        segmenter = InputSegmenter()
        result = segmenter.segment("""Deploy RIL
Test ToT
Sync DB""")

        assert result.segment_count == 3

    def test_abbreviation_expansion(self):
        """Test abbreviations are expanded."""
        segmenter = InputSegmenter()
        result = segmenter.segment("sync db")

        assert "sync database" in result.segments

    def test_empty_input(self):
        """Test empty input returns empty result."""
        segmenter = InputSegmenter()
        result = segmenter.segment("")

        assert result.segment_count == 0
        assert result.was_multi_part is False

    def test_segment_to_tasks(self):
        """Test task dict generation for TaskRouter."""
        tasks = segment_to_tasks("Deploy RIL, test ToT")

        assert len(tasks) == 2
        assert tasks[0]["text"] == "deploy ril"
        assert tasks[0]["sequence_index"] == 0
        assert tasks[0]["total_in_sequence"] == 2
        assert tasks[0]["from_multi_part"] is True

    def test_segment_result_iteration(self):
        """Test SegmentResult is iterable."""
        result = segment_input("task one, task two, task three")

        segments = list(result)
        assert len(segments) == 3

    def test_custom_config(self):
        """Test custom configuration."""
        config = SegmenterConfig(
            normalize_case=False,
            expand_abbreviations=False,
        )
        segmenter = InputSegmenter(config)
        result = segmenter.segment("Sync DB")

        # Should preserve case and not expand abbreviation
        assert "Sync DB" in result.segments


class TestSegmentIntegration:
    """Test integration with TaskRouter."""

    def test_with_task_router(self):
        """Test segmenter output works with TaskRouter."""
        from orchestration import TaskRouter

        segmenter = InputSegmenter()
        router = TaskRouter()

        tasks = segmenter.segment_to_tasks("Deploy RIL, test ToT")

        for task in tasks:
            decision = router.route(task)
            assert decision is not None
            assert decision.task_type is not None
