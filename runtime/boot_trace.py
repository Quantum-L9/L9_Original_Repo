"""Minimal boot-trace recorder used by api.server lifespan."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class BootTrace:
    """Record named startup steps so readiness can inspect them."""

    def __init__(self) -> None:
        self._steps: list[dict[str, Any]] = []
        self._open: dict[str, datetime] = {}
        self._frozen = False

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    def start(self, name: str) -> None:
        if self._frozen:
            return
        self._open[name] = datetime.now(tz=UTC)

    def ok(self, name: str) -> None:
        self._close(name, "ok")

    def fail(self, name: str, reason: str) -> None:
        self._close(name, "fail", reason=reason)

    def freeze(self) -> None:
        self._frozen = True

    def summary(self) -> dict[str, Any]:
        return {
            "frozen": self._frozen,
            "step_count": len(self._steps),
            "failed": [s["name"] for s in self._steps if s["status"] == "fail"],
        }

    def to_list(self) -> list[dict[str, Any]]:
        return list(self._steps)

    def _close(self, name: str, status: str, reason: str | None = None) -> None:
        if self._frozen:
            return
        started = self._open.pop(name, None)
        entry: dict[str, Any] = {
            "name": name,
            "status": status,
            "started_at": started.isoformat() if started else None,
            "ended_at": datetime.now(tz=UTC).isoformat(),
        }
        if reason:
            entry["reason"] = reason
        self._steps.append(entry)
