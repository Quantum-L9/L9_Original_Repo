"""
Tests for L9 CLI Tool
======================

Production-ready test suite for l9-cli security and debt management tool.

Version: 1.0.0
GMP: security-remediation-phase1
"""

import subprocess



class TestL9CLI:
    """Test suite for l9-cli tool."""

    def test_cli_help(self):
        """Test that CLI help command works."""
        result = subprocess.run(
            ["python", "tools/l9_cli.py", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "L9 CLI Tool" in result.stdout

    def test_scan_secrets_command(self, tmp_path):
        """Test scan-secrets command."""
        # Create a test file with a hardcoded secret
        test_file = tmp_path / "test.py"
        test_file.write_text('api_key = "hardcoded_secret_123"')

        result = subprocess.run(
            ["python", "tools/l9_cli.py", "scan-secrets", "--path", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Scanning for hardcoded secrets" in result.stdout

    def test_scan_quality_command(self, tmp_path):
        """Test scan-quality command."""
        # Create a test file with a bare except clause
        test_file = tmp_path / "test.py"
        test_file.write_text("try:\n    pass\nexcept:\n    pass")

        result = subprocess.run(
            ["python", "tools/l9_cli.py", "scan-quality", "--path", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Analyzing code quality" in result.stdout

    def test_manage_debt_command(self, tmp_path):
        """Test manage-debt command."""
        # Create a test file with TODO markers
        test_file = tmp_path / "test.py"
        test_file.write_text("# TODO: Fix this\n# FIXME: Refactor")

        result = subprocess.run(
            ["python", "tools/l9_cli.py", "manage-debt", "--path", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Scanning for technical debt markers" in result.stdout
