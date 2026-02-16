from __future__ import annotations

import asyncio
import importlib
import sys
from types import ModuleType
from typing import TYPE_CHECKING

import pytest

from core.decorators import must_stay_async

if TYPE_CHECKING:
    from pathlib import Path


class DummySchema:
    class system:
        name = "TestAgent"

    class metadata:
        version = "1.0"

    def get_agent_id(self) -> str:
        return "agent-1"


class DummyResult:
    def __init__(self) -> None:
        self.success = True
        self.schema = DummySchema()
        self.generated_files = []
        self.errors = []
        self.warnings = []
        self.duration_ms = 1
        self.manifest = None


def _install_fake_research_factory() -> None:
    services = ModuleType("services")
    research_factory = ModuleType("services.research_factory")

    def parse_schema(path: Path) -> DummySchema:
        return DummySchema()

    def validate_schema(schema: DummySchema) -> object:
        class Result:
            valid = True

            def to_dict(self) -> dict[str, bool]:
                return {"valid": True}

        return Result()

    def load_glue_config(path: Path) -> dict[str, str]:
        return {"ok": "true"}

    class UniversalExtractor:
        def __init__(self, strict_validation: bool = False) -> None:
            self.strict_validation = strict_validation

        @must_stay_async("callers use await")
        async def extract(
            self,
            *,
            schema: DummySchema,
            output_dir: str,
            glue: object | None,
            overwrite: bool,
            dry_run: bool,
        ) -> DummyResult:
            return DummyResult()

    research_factory.parse_schema = parse_schema
    research_factory.validate_schema = validate_schema
    research_factory.load_glue_config = load_glue_config
    research_factory.UniversalExtractor = UniversalExtractor
    sys.modules["services"] = services
    sys.modules["services.research_factory"] = research_factory


def test_factory_extract_cli_sandboxed(tmp_path, monkeypatch):
    _install_fake_research_factory()
    monkeypatch.setenv("L9_RESEARCH_FACTORY_BASE_DIR", str(tmp_path))
    schema_file = tmp_path / "schema.yaml"
    schema_file.write_text("schema: test")

    module = importlib.import_module("scripts.research.factory_extract")
    monkeypatch.setattr(
        sys,
        "argv",
        ["factory_extract.py", "--schema", str(schema_file), "--output", "agent_one"],
    )

    with pytest.raises(SystemExit) as exc:
        importlib.reload(module)
        asyncio.run(module.main())
    assert exc.value.code == 0


def test_factory_extract_cli_rejects_escape(tmp_path, monkeypatch):
    _install_fake_research_factory()
    monkeypatch.setenv("L9_RESEARCH_FACTORY_BASE_DIR", str(tmp_path))
    schema_file = tmp_path / "schema.yaml"
    schema_file.write_text("schema: test")

    module = importlib.import_module("scripts.research.factory_extract")
    monkeypatch.setattr(
        sys,
        "argv",
        ["factory_extract.py", "--schema", str(schema_file), "--output", "../etc"],
    )

    with pytest.raises(SystemExit) as exc:
        importlib.reload(module)
        asyncio.run(module.main())
    assert exc.value.code == 2
