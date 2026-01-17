"""
Example test file - Replace with real tests.
Created by /do-init

DORA-aligned: Tests enable automated validation in CI/CD,
reducing change failure rate and lead time.
"""

import sys


class TestBasicSetup:
    """Verify basic project setup is correct."""

    def test_python_version(self):
        """Verify Python 3.11+ is being used."""
        assert sys.version_info >= (3, 11), "Python 3.11+ required"

    def test_imports_work(self):
        """Verify basic imports don't fail."""
        # Uncomment when src module exists:
        # from src import main
        assert True

    def test_placeholder(self):
        """Placeholder test - replace with real tests."""
        # TODO: Replace with actual tests
        assert 1 + 1 == 2


class TestExample:
    """Example test class - replace with domain-specific tests."""

    def test_example_function(self):
        """Example test method."""
        result = self._example_helper(2, 3)
        assert result == 5

    def _example_helper(self, a: int, b: int) -> int:
        """Helper method for tests."""
        return a + b


# === INTEGRATION TESTS ===
# Mark slow/integration tests with markers

# import pytest
#
# @pytest.mark.slow
# def test_slow_operation():
#     """This test takes a while."""
#     pass
#
# @pytest.mark.integration
# def test_external_service():
#     """This test requires external services."""
#     pass
