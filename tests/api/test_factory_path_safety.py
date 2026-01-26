from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

from fastapi import FastAPI
from fastapi.testclient import TestClient


class DummySchema:
    class system:
        name = "TestAgent"

    class metadata:
        version = "1.0"

    def get_agent_id(self) -> str:
        return "agent-1"


class DummyFile:
    def __init__(self, path: Path) -> None:
        self.path = path


class DummyManifest:
    def to_dict(self) -> dict[str, bool]:
        return {"ok": True}


class DummyResult:
    def __init__(self, output_dir: Path) -> None:
        self.success = True
        self.schema = DummySchema()
        self.generated_files = [DummyFile(output_dir / "agent.py")]
        self.errors = []
        self.warnings = []
        self.duration_ms = 1
        self.manifest = DummyManifest()


def _install_fake_research_factory(tmp_path: Path) -> None:
    services = ModuleType("services")
    research_factory = ModuleType("services.research_factory")
    extractor_mod = ModuleType("services.research_factory.extractor")
    glue_mod = ModuleType("services.research_factory.glue_resolver")

    class UniversalExtractor:
        def __init__(self, strict_validation: bool = False) -> None:
            self.strict_validation = strict_validation

        async def extract(
            self,
            *,
            schema: str,
            output_dir: str,
            glue: object | None,
            overwrite: bool,
            dry_run: bool,
        ) -> DummyResult:
            return DummyResult(Path(output_dir))

        def list_templates(self) -> list[str]:
            return []

        def get_template_content(self, name: str) -> str:
            return "content"

    class GlueConfig:
        @classmethod
        def model_validate(cls, data: dict) -> GlueConfig:
            return cls()

    extractor_mod.UniversalExtractor = UniversalExtractor
    glue_mod.GlueConfig = GlueConfig
    research_factory.extractor = extractor_mod
    research_factory.glue_resolver = glue_mod
    research_factory.UniversalExtractor = UniversalExtractor
    research_factory.GlueConfig = GlueConfig

    sys.modules["services"] = services
    sys.modules["services.research_factory"] = research_factory
    sys.modules["services.research_factory.extractor"] = extractor_mod
    sys.modules["services.research_factory.glue_resolver"] = glue_mod


def test_factory_extract_sandboxed(tmp_path, monkeypatch):
    monkeypatch.setenv("L9_RESEARCH_FACTORY_BASE_DIR", str(tmp_path))
    _install_fake_research_factory(tmp_path)
    project_root = Path(__file__).resolve().parents[2]
    tests_root = Path(__file__).resolve().parents[1]
    if str(tests_root) in sys.path:
        sys.path.remove(str(tests_root))
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    sys.modules.pop("api", None)
    sys.modules.pop("api.routes", None)

    from api.routes.factory import router as factory_router

    app = FastAPI()
    app.include_router(factory_router)
    client = TestClient(app)

    response = client.post(
        "/factory/extract",
        json={
            "schema_yaml": "schema: test",
            "output_dir": "agent_one",
            "overwrite": False,
            "dry_run": True,
            "strict": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["files"][0].startswith(str(tmp_path))


def test_factory_extract_rejects_escape(tmp_path, monkeypatch):
    monkeypatch.setenv("L9_RESEARCH_FACTORY_BASE_DIR", str(tmp_path))
    _install_fake_research_factory(tmp_path)
    project_root = Path(__file__).resolve().parents[2]
    tests_root = Path(__file__).resolve().parents[1]
    if str(tests_root) in sys.path:
        sys.path.remove(str(tests_root))
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    sys.modules.pop("api", None)
    sys.modules.pop("api.routes", None)

    from api.routes.factory import router as factory_router

    app = FastAPI()
    app.include_router(factory_router)
    client = TestClient(app)

    response = client.post(
        "/factory/extract",
        json={
            "schema_yaml": "schema: test",
            "output_dir": "../etc",
            "overwrite": False,
            "dry_run": True,
            "strict": False,
        },
    )

    assert response.status_code == 400


def test_factory_extract_file_rejects_escape(tmp_path, monkeypatch):
    monkeypatch.setenv("L9_RESEARCH_FACTORY_BASE_DIR", str(tmp_path))
    _install_fake_research_factory(tmp_path)
    project_root = Path(__file__).resolve().parents[2]
    tests_root = Path(__file__).resolve().parents[1]
    if str(tests_root) in sys.path:
        sys.path.remove(str(tests_root))
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    sys.modules.pop("api", None)
    sys.modules.pop("api.routes", None)

    from api.routes.factory import router as factory_router

    app = FastAPI()
    app.include_router(factory_router)
    client = TestClient(app)

    response = client.post(
        "/factory/extract-file",
        data={"output_dir": "..\\escape", "overwrite": "false", "dry_run": "true"},
        files={"schema_file": ("schema.yaml", b"schema: test")},
    )

    assert response.status_code == 400
