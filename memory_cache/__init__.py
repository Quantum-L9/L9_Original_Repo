# memory_cache/__init__.py
"""
Memory Cache Module - Ephemeral working memory for Cursor sessions.

Provides TTL-based, Redis-backed working memory that expires naturally.
No auto-promotion to long-term memory without explicit signals.
"""

from memory_cache.cursor_working_memory_service import (
    CursorWorkingMemoryService,
    MemoryEventType,
    WorkingMemorySnapshot,
)

__all__ = [
    "CursorWorkingMemoryService",
    "MemoryEventType",
    "WorkingMemorySnapshot",
]
