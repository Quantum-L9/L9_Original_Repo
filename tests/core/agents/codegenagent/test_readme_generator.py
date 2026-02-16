"""
Tests for CodeGenAgent readme_generator module.
"""

import sys
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # noqa: ADR-0001 - internal path
sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from core.agents.codegenagent.readme_generator import (
    GeneratedReadme,
    ReadmeGenerator,
    ReadmeMetadata,
    generate_readme_for_module,
)


class TestReadmeGenerator:
    """Test ReadmeGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create generator instance."""
        return ReadmeGenerator()

    def test_generate_module_readme_basic(self, generator):
        """Test basic module README generation."""
        readme = generator.generate_module_readme(
            module_name="TestModule",
            overview="A test module for unit testing.",
        )

        assert readme.filename == "README.md"
        assert "# TestModule" in readme.content
        assert "A test module for unit testing." in readme.content
        assert "## Overview" in readme.content
        assert "## API Reference" in readme.content
        assert "## AI Usage Rules" in readme.content

    def test_generate_module_readme_with_api(self, generator):
        """Test README with API functions."""
        readme = generator.generate_module_readme(
            module_name="ComputeEngine",
            overview="Computation engine.",
            api_functions=[
                {
                    "name": "compute",
                    "signature": "async def compute(expr: str, values: dict) -> float",
                    "description": "Evaluates an expression.",
                    "example": "result = await engine.compute('x+1', {'x': 2})",
                },
                {
                    "name": "generate_code",
                    "signature": "async def generate_code(expr: str) -> str",
                    "description": "Generates code from expression.",
                },
            ],
        )

        assert "### `compute`" in readme.content
        assert "### `generate_code`" in readme.content
        assert "async def compute" in readme.content
        assert "Evaluates an expression." in readme.content

    def test_generate_module_readme_with_config(self, generator):
        """Test README with configuration."""
        readme = generator.generate_module_readme(
            module_name="ConfigModule",
            overview="Module with config.",
            configuration={
                "CACHE_SIZE": {
                    "type": "int",
                    "default": 128,
                    "description": "LRU cache size",
                },
                "BACKEND": {
                    "type": "str",
                    "default": "numpy",
                    "description": "Compute backend",
                },
            },
        )

        assert "| Variable | Type | Default | Description |" in readme.content
        assert "CACHE_SIZE" in readme.content
        assert "BACKEND" in readme.content

    def test_generate_module_readme_with_data_models(self, generator):
        """Test README with data models."""
        readme = generator.generate_module_readme(
            module_name="ModelModule",
            overview="Module with models.",
            data_models=[
                {
                    "name": "ComputeRequest",
                    "description": "Request for computation.",
                    "fields": [
                        {
                            "name": "expression",
                            "type": "str",
                            "description": "Math expression",
                        },
                        {
                            "name": "values",
                            "type": "dict",
                            "description": "Variable values",
                        },
                    ],
                },
            ],
        )

        assert "### `ComputeRequest`" in readme.content
        assert "| Field | Type | Description |" in readme.content
        assert "expression" in readme.content

    def test_generate_module_readme_with_ai_scopes(self, generator):
        """Test README with AI usage rules."""
        readme = generator.generate_module_readme(
            module_name="ScopedModule",
            overview="Module with scopes.",
            allowed_scopes=["- `core/*.py` — Application logic"],
            restricted_scopes=["- Schema changes"],
            forbidden_scopes=["- `kernel.py` — Entry point"],
        )

        assert "✅ Allowed Scope" in readme.content
        assert "`core/*.py`" in readme.content
        assert "⚠️ Restricted Scope" in readme.content
        assert "❌ Forbidden Scope" in readme.content
        assert "`kernel.py`" in readme.content

    def test_generate_module_readme_metadata(self, generator):
        """Test that metadata is generated."""
        readme = generator.generate_module_readme(
            module_name="MetaModule",
            overview="Module for metadata test.",
            version="2.0.0",
        )

        assert readme.metadata is not None
        assert readme.metadata.type == "module_readme"
        assert readme.metadata.subsystem == "metamodule"
        assert readme.metadata.version == "2.0.0"
        assert readme.metadata_yaml is not None
        assert 'location: "/metamodule/README.md"' in readme.metadata_yaml

    def test_generate_subsystem_readme_basic(self, generator):
        """Test subsystem README generation."""
        readme = generator.generate_subsystem_readme(
            subsystem_name="AgentKernel",
            overview="Agent execution kernel.",
            owns=["Agent lifecycle", "Task execution"],
            does_not_own=["Memory storage", "Tool dispatch"],
        )

        assert "# AgentKernel" in readme.content
        assert "## Subsystem Overview" in readme.content
        assert "## Responsibilities and Boundaries" in readme.content
        assert "Agent lifecycle" in readme.content
        assert "Memory storage" in readme.content

    def test_generate_subsystem_readme_with_components(self, generator):
        """Test subsystem README with components."""
        readme = generator.generate_subsystem_readme(
            subsystem_name="ToolRegistry",
            overview="Tool registration and dispatch.",
            components=[
                {"name": "Registry", "role": "Tool storage", "file": "registry.py"},
                {
                    "name": "Dispatcher",
                    "role": "Tool execution",
                    "file": "dispatcher.py",
                },
            ],
        )

        assert "### `Registry`" in readme.content
        assert "### `Dispatcher`" in readme.content
        assert "registry.py" in readme.content

    def test_generate_from_meta(self, generator):
        """Test README generation from meta specification."""
        meta = {
            "name": "MathEngine",
            "description": "Mathematical computation engine.",
            "version": "1.5.0",
            "code": [
                {
                    "function_name": "evaluate",
                    "description": "Evaluates expression",
                },
                {
                    "function_name": "generate",
                    "description": "Generates code",
                },
            ],
            "dependencies": ["sympy", "numpy"],
        }

        readme = generator.generate_from_meta(meta)

        assert "# MathEngine" in readme.content
        assert "Mathematical computation engine." in readme.content
        assert "### `evaluate`" in readme.content
        assert "### `generate`" in readme.content
        assert "sympy" in readme.content


class TestReadmeMetadata:
    """Test ReadmeMetadata dataclass."""

    def test_metadata_defaults(self):
        """Test metadata default values."""
        metadata = ReadmeMetadata(
            location="/test/README.md",
            type="module_readme",
            subsystem="test",
        )

        assert metadata.owner == "L9 CodeGenAgent"
        assert metadata.version == "1.0.0"
        assert metadata.last_updated  # Should have a date
        assert metadata.invariants == []
        assert metadata.ai_allowed_scopes == []

    def test_metadata_custom_values(self):
        """Test metadata with custom values."""
        metadata = ReadmeMetadata(
            location="/custom/README.md",
            type="subsystem_readme",
            subsystem="custom",
            owner="Igor",
            version="2.0.0",
            invariants=["Data must be valid", "State must be consistent"],
            ai_allowed_scopes=["core/*.py"],
            ai_restricted_scopes=["schema.py"],
            ai_forbidden_scopes=["kernel.py"],
        )

        assert metadata.owner == "Igor"
        assert metadata.version == "2.0.0"
        assert len(metadata.invariants) == 2
        assert "core/*.py" in metadata.ai_allowed_scopes


class TestGeneratedReadme:
    """Test GeneratedReadme dataclass."""

    def test_generated_readme_creation(self):
        """Test creating GeneratedReadme."""
        readme = GeneratedReadme(
            filename="README.md",
            content="# Test",
        )

        assert readme.filename == "README.md"
        assert readme.content == "# Test"
        assert readme.metadata is None
        assert readme.metadata_yaml is None

    def test_generated_readme_with_metadata(self):
        """Test GeneratedReadme with metadata."""
        metadata = ReadmeMetadata(
            location="/test/README.md",
            type="module_readme",
            subsystem="test",
        )

        readme = GeneratedReadme(
            filename="README.md",
            content="# Test",
            metadata=metadata,
            metadata_yaml="location: /test/README.md",
        )

        assert readme.metadata is not None
        assert readme.metadata.subsystem == "test"


class TestConvenienceFunction:
    """Test the convenience function."""

    def test_generate_readme_for_module(self):
        """Test convenience function."""
        readme = generate_readme_for_module(
            module_name="QuickModule",
            overview="A quick test module.",
            version="0.1.0",
        )

        assert readme.filename == "README.md"
        assert "# QuickModule" in readme.content
        assert "A quick test module." in readme.content


class TestReadmeIntegration:
    """Integration tests for README generation."""

    def test_full_readme_generation_workflow(self):
        """Test complete README generation workflow."""
        generator = ReadmeGenerator()

        # Generate module README with all sections
        readme = generator.generate_module_readme(
            module_name="FullModule",
            overview="A complete module with all sections.",
            purpose="Provides full functionality.",
            responsibilities=["Handle requests", "Process data", "Return results"],
            non_goals=["Not for production", "Not for security"],
            install_commands="pip install full-module",
            quickstart_code="from full_module import FullModule\nengine = FullModule()\nresult = await engine.run()",
            api_functions=[
                {
                    "name": "run",
                    "signature": "async def run() -> Result",
                    "description": "Run the module.",
                },
            ],
            configuration={
                "DEBUG": {
                    "type": "bool",
                    "default": False,
                    "description": "Enable debug mode",
                },
            },
            data_models=[
                {
                    "name": "Result",
                    "description": "Operation result.",
                    "fields": [
                        {"name": "value", "type": "Any", "description": "Result value"}
                    ],
                },
            ],
            test_commands="pytest tests/full_module/",
            coverage_target=90,
            dependencies=["pydantic", "structlog"],
            allowed_scopes=["- `full_module/*.py`"],
            restricted_scopes=["- API changes"],
            forbidden_scopes=["- Entry points"],
            owner="TestTeam",
            version="1.2.3",
        )

        # Verify all sections present
        assert "# FullModule" in readme.content
        assert "## Overview" in readme.content
        assert "## Purpose" in readme.content
        assert "Handle requests" in readme.content
        assert "## Installation" in readme.content
        assert "pip install full-module" in readme.content
        assert "## Quick Start" in readme.content
        assert "## API Reference" in readme.content
        assert "### `run`" in readme.content
        assert "## Configuration" in readme.content
        assert "DEBUG" in readme.content
        assert "## Data Models" in readme.content
        assert "### `Result`" in readme.content
        assert "## Testing" in readme.content
        assert "90%" in readme.content
        assert "## Dependencies" in readme.content
        assert "pydantic" in readme.content
        assert "## AI Usage Rules" in readme.content
        assert "## Maintenance" in readme.content
        assert "TestTeam" in readme.content
        assert "1.2.3" in readme.content

        # Verify metadata
        assert readme.metadata is not None
        assert readme.metadata.owner == "TestTeam"
        assert readme.metadata.version == "1.2.3"
        assert readme.metadata_yaml is not None
