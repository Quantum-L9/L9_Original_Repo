from pathlib import Path

import pytest

from core.security.path_safety import (
    PathSafetyError,
    safe_resolve_path,
    safe_resolve_path_async,
    validate_filename,
)


@pytest.mark.parametrize(
    "value",
    [
        "..",
        "../etc/passwd",
        "..\\..\\secret",
        "/etc/passwd",
        "\\\\server\\share",
        "C:\\Windows\\System32",
        "%2e%2e/%2e%2e/etc/passwd",
        "..%2f..%2fetc/passwd",
        "~/.ssh/id_rsa",
        "..//..//etc/passwd",
        "..\\..\\etc\\passwd",
        "dir/\u200b../escape",
    ],
)
def test_safe_resolve_path_rejects_traversal(value, tmp_path):
    with pytest.raises(PathSafetyError):
        safe_resolve_path(tmp_path, value)


def test_safe_resolve_path_accepts_normalized(tmp_path):
    resolved = safe_resolve_path(tmp_path, "agents/new_agent")
    assert resolved == (tmp_path / "agents" / "new_agent").resolve()


def test_safe_resolve_path_rejects_symlink(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(PathSafetyError):
        safe_resolve_path(tmp_path, "link/child")


def test_safe_resolve_path_allows_abs_under_root(tmp_path):
    abs_path = tmp_path / "inner"
    resolved = safe_resolve_path(tmp_path, str(abs_path), allow_abs=True)
    assert resolved == abs_path


@pytest.mark.asyncio
async def test_safe_resolve_path_async(tmp_path):
    resolved = await safe_resolve_path_async(tmp_path, "a/b")
    assert resolved == (tmp_path / "a" / "b").resolve()


def test_safe_resolve_path_rejects_nul(tmp_path):
    with pytest.raises(PathSafetyError):
        safe_resolve_path(tmp_path, "good\x00bad")


def test_safe_resolve_path_rejects_surrogate(tmp_path):
    with pytest.raises(PathSafetyError):
        safe_resolve_path(tmp_path, "bad\ud800path")


def test_safe_resolve_path_rejects_control_chars(tmp_path):
    with pytest.raises(PathSafetyError):
        safe_resolve_path(tmp_path, "bad\u0007path")


@pytest.mark.parametrize(
    "name",
    [
        "..",
        "../",
        "..\\",
        "file/name",
        "C:\\boot.ini",
        "",
        "./",
        "CON",
        "LPT1",
        "trailing.",
        "trailing ",
        "bad\u0007name",
    ],
)
def test_validate_filename_rejects_bad(name):
    with pytest.raises(PathSafetyError):
        validate_filename(name)


def test_validate_filename_accepts_safe_name():
    assert validate_filename("agent_config.yaml") == "agent_config.yaml"
