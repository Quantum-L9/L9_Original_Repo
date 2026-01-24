"""
Tests for CodeGenAgent meta_loader module.
"""

import os
import tempfile
from pathlib import Path

import pytest
import structlog

logger = structlog.get_logger(__name__)

from agents.codegenagent.meta_loader import (MetaLoader, MetaLoaderError,
                                             load_meta)


class TestMetaLoader:
    """Test MetaLoader class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temp directory with test specs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a valid spec file
            spec_path = Path(tmpdir) / "test_spec.yaml"
            spec_path.write_text("""
name: test_module
description: A test module
version: 1.0.0
code:
  - type: template
    content: "logger.info('hello')"
""")

            # Create an invalid YAML file
            invalid_path = Path(tmpdir) / "invalid.yaml"
            invalid_path.write_text("invalid: yaml: content: [")

            yield tmpdir

    def test_load_meta_success(self, temp_dir):
        """Test loading a valid meta file."""
        loader = MetaLoader(temp_dir)
        meta = loader.load_meta("test_spec.yaml")

        assert meta["name"] == "test_module"
        assert meta["description"] == "A test module"
        assert "code" in meta

    def test_load_meta_not_found(self, temp_dir):
        """Test loading non-existent file."""
        loader = MetaLoader(temp_dir)

        with pytest.raises(MetaLoaderError) as exc_info:
            loader.load_meta("nonexistent.yaml")

        assert "not found" in str(exc_info.value)

    def test_load_meta_invalid_yaml(self, temp_dir):
        """Test loading invalid YAML."""
        loader = MetaLoader(temp_dir)

        with pytest.raises(MetaLoaderError) as exc_info:
            loader.load_meta("invalid.yaml")

        assert "YAML" in str(exc_info.value) or "parse" in str(exc_info.value).lower()

    def test_validate_meta_valid(self, temp_dir):
        """Test meta validation with valid spec."""
        loader = MetaLoader(temp_dir)
        meta = loader.load_meta("test_spec.yaml")

        assert loader.validate_meta(meta) is True

    def test_validate_meta_missing_fields(self):
        """Test meta validation with missing fields."""
        loader = MetaLoader()

        assert loader.validate_meta({}) is False
        assert loader.validate_meta({"name": "test"}) is False
        assert loader.validate_meta({"description": "test"}) is False

    def test_get_code_sections(self, temp_dir):
        """Test extracting code sections."""
        loader = MetaLoader(temp_dir)
        meta = loader.load_meta("test_spec.yaml")

        sections = loader.get_code_sections(meta)

        assert len(sections) == 1
        assert sections[0]["type"] == "template"

    def test_load_all_specs(self, temp_dir):
        """Test loading all specs from directory."""
        loader = MetaLoader(temp_dir)
        specs = loader.load_all_specs()

        # Should load test_spec.yaml, skip invalid.yaml
        assert len(specs) >= 1
        valid_specs = [s for s in specs if s.get("name") == "test_module"]
        assert len(valid_specs) == 1

    def test_convenience_function(self, temp_dir):
        """Test load_meta convenience function."""
        spec_path = os.path.join(temp_dir, "test_spec.yaml")
        meta = load_meta(spec_path)

        assert meta["name"] == "test_module"
