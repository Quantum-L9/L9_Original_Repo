"""
L9 Kernel Integrity Tests
=========================

Contract-grade tests for core.kernels.integrity.

Goals:
- Hashing is deterministic and stable
- Content-hash registry rejects mutations
- IntegrityError raised on mismatch
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from core.kernels import integrity


def test_compute_hash_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("hello-world")

    first = integrity.compute_hash(path)
    second = integrity.compute_hash(path)

    assert first == second
    assert isinstance(first, str)
    assert len(first) >= 32  # hex digest


def test_compute_hash_changes_when_content_changes(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("version-1")
    h1 = integrity.compute_hash(path)

    path.write_text("version-2")
    h2 = integrity.compute_hash(path)

    assert h1 != h2


def test_register_and_validate_integrity_passes(tmp_path: Path) -> None:
    path = tmp_path / "kernel.yaml"
    path.write_text("kernel: v1")

    expected = integrity.compute_hash(path)
    registry = integrity.IntegrityRegistry()
    registry.register(path, expected)

    # Should not raise
    registry.validate(path)


def test_validate_integrity_raises_on_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "kernel.yaml"
    path.write_text("kernel: v1")

    registry = integrity.IntegrityRegistry()
    # Intentionally wrong hash
    registry.register(path, "deadbeef")

    with pytest.raises(integrity.IntegrityError):
        registry.validate(path)


def test_bulk_validation_reports_all_failures(tmp_path: Path) -> None:
    p1 = tmp_path / "a.yaml"
    p2 = tmp_path / "b.yaml"
    p1.write_text("ok")
    p2.write_text("bad")

    reg = integrity.IntegrityRegistry()
    reg.register(p1, integrity.compute_hash(p1))
    reg.register(p2, "wrong-hash")

    result = reg.validate_all(tmp_path)

    assert result.total == 2
    assert result.ok == 1
    assert result.failed == 1
    assert any(f.path == p2 for f in result.failures)
