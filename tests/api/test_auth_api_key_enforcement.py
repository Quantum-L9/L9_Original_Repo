import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

auth_path = PROJECT_ROOT / "api" / "auth.py"
spec = importlib.util.spec_from_file_location("l9_api_auth", auth_path)
auth = importlib.util.module_from_spec(spec)
assert spec
assert spec.loader
spec.loader.exec_module(auth)


def test_verify_api_key_rejects_invalid(monkeypatch) -> None:
    monkeypatch.setattr(auth, "EXECUTOR_API_KEY_L", "l-key")
    monkeypatch.setattr(auth, "EXECUTOR_API_KEY_C", "c-key")

    with pytest.raises(HTTPException) as exc:
        auth.verify_api_key("Bearer wrong")

    assert exc.value.status_code == 401


def test_verify_api_key_cursor_scopes(monkeypatch) -> None:
    monkeypatch.setattr(auth, "EXECUTOR_API_KEY_L", "l-key")
    monkeypatch.setattr(auth, "EXECUTOR_API_KEY_C", "c-key")

    caller = auth.verify_api_key("Bearer c-key")

    assert caller.caller_id == "C"
    assert "l-private" not in caller.allowed_scopes
