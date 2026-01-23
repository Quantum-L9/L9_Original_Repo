import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
sys.path = [p for p in sys.path if not (p and Path(p).resolve().name == "tests")]
sys.modules.pop("memory", None)

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("MEMORY_DSN", "postgresql://user:pass@localhost:5432/test")
os.environ.setdefault("MCP_API_KEY_L", "test-key")

MCP_ROOT = PROJECT_ROOT / "mcp_memory"
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

from src.routes import memory_unified  # noqa: E402


def test_legacy_save_route_disabled() -> None:
    app = FastAPI()
    app.include_router(memory_unified.router, prefix="/memory")
    client = TestClient(app)

    response = client.post("/memory/save", json={})

    assert response.status_code == 410


def test_legacy_search_route_disabled() -> None:
    app = FastAPI()
    app.include_router(memory_unified.router, prefix="/memory")
    client = TestClient(app)

    response = client.post("/memory/search", json={})

    assert response.status_code == 410
