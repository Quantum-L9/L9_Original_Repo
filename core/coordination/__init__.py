"""
L9 Coordination Layer - Event-Driven Agent Communication

Harvested from: L9-Implementation-Suite-Ready-to-Deploy.md
"""

from __future__ import annotations

from .event_queue import (Event, EventKind, EventQueue, EventRouter,
                          init_event_driven_coordination)

__all__ = [
    "EventQueue",
    "Event",
    "EventKind",
    "EventRouter",
    "init_event_driven_coordination",
]
