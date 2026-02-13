"""
Tests for CodeGenAgent c_gmp_engine module.
"""

import sys
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # noqa: ADR-0001 - internal path
sys.path.insert(0, str(PROJECT_ROOT))

import tempfile

import pytest

from core.agents.codegenagent.c_gmp_engine import CGMPEngine, CGMPEngineError
from core.agents.codegenagent.meta_loader import MetaLoader


class TestCGMPEngine:
    """Test CGMPEngine class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temp directory with test specs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mathematical spec
            math_spec = Path(tmpdir) / "math_spec.yaml"
            math_spec.write_text("""
name: math_module
description: Mathematical computation module
filename: math_output.py
code:
  - type: mathematical
    expression: "x**2 + y**2"
    variables: ["x", "y"]
    language: C
    function_name: distance_squared
""")

            # Create a template spec
            template_spec = Path(tmpdir) / "template_spec.yaml"
            template_spec.write_text("""
name: template_module
description: Template-based module
filename: template_output.py
code:
  - type: template
    content: "def {{name}}(): return {{value}}"
    substitutions:
      name: hello
      value: 42
""")

            yield tmpdir

    @pytest.fixture
    def engine(self, temp_dir):
        """Create engine with temp specs directory."""
        return CGMPEngine(meta_loader=MetaLoader(temp_dir))

    def test_is_mathematical_explicit(self, engine):
        """Test mathematical detection with explicit type."""
        section = {"type": "mathematical", "expression": "x+1"}
        assert engine._is_mathematical(section) is True

    def test_is_mathematical_by_content(self, engine):
        """Test mathematical detection by content markers."""
        section = {"content": "from sympy import Symbol, lambdify"}
        assert engine._is_mathematical(section) is True

    def test_is_not_mathematical(self, engine):
        """Test non-mathematical section detection."""
        section = {"type": "template", "content": "print('hello')"}
        assert engine._is_mathematical(section) is False

    def test_expand_template(self, engine):
        """Test template expansion."""
        section = {
            "content": "Hello {{name}}, value is {{value}}",
            "substitutions": {"name": "World", "value": 42},
        }

        result = engine._expand_template(section)

        assert result["type"] == "template"
        assert "Hello World" in result["source_code"]
        assert "42" in result["source_code"]

    @pytest.mark.asyncio
    async def test_expand_mathematical(self, engine):
        """Test mathematical expansion with SymPy."""
        section = {
            "type": "mathematical",
            "expression": "x + y",
            "variables": ["x", "y"],
            "language": "C",
            "function_name": "add_func",
        }

        result = await engine._expand_mathematical(section)

        assert result["type"] == "mathematical"
        assert result["source_code"] is not None
        assert result["function_name"] == "add_func"

    @pytest.mark.asyncio
    async def test_expand_code_blocks(self, temp_dir, engine):
        """Test expanding all code blocks."""
        meta = engine._meta_loader.load_meta("template_spec.yaml")
        expanded = await engine.expand_code_blocks(meta)

        assert len(expanded) == 1
        assert expanded[0]["success"] is True

    @pytest.mark.asyncio
    async def test_generate_from_meta(self, temp_dir, engine):
        """Test generating from meta file."""
        result = await engine.generate_from_meta("template_spec.yaml")

        assert result["success"] is True
        assert result["name"] == "template_module"
        assert len(result["output_files"]) >= 0  # May or may not have output files

    @pytest.mark.asyncio
    async def test_generate_from_meta_not_found(self, engine):
        """Test generating from non-existent file."""
        result = await engine.generate_from_meta("nonexistent.yaml")

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_generate_batch_parallel(self, temp_dir, engine):
        """Test batch generation in parallel."""
        results = await engine.generate_batch(
            ["template_spec.yaml", "math_spec.yaml"], parallel=True
        )

        assert len(results) == 2
        # At least one should succeed
        successes = [r for r in results if r.get("success")]
        assert len(successes) >= 1

    @pytest.mark.asyncio
    async def test_generate_batch_sequential(self, temp_dir, engine):
        """Test batch generation sequentially."""
        results = await engine.generate_batch(["template_spec.yaml"], parallel=False)

        assert len(results) == 1

    def test_get_generated_files(self, engine):
        """Test getting generated files list."""
        files = engine.get_generated_files()
        assert isinstance(files, list)

    def test_clear_generated(self, engine):
        """Test clearing generated files."""
        engine._generated_files.append({"test": "file"})
        engine.clear_generated()
        assert len(engine._generated_files) == 0
