"""
L9 Cursor Agent Integration

Cursor-specific modules for IDE integration, memory management, and LangGraph orchestration.
All cursor-related code is consolidated here for easier maintenance and clear separation.

Includes:
- CursorMemoryKernel: Session state, lessons, TODOs
- CursorClient: API client for Cursor
- GMP Meta-Learning: Execution tracking, heuristics, autonomy graduation
"""

from agents.cursor.cursor_client import CursorClient
from agents.cursor.cursor_memory_kernel import (CursorMemoryKernel, Lesson,
                                                SessionState, TodoItem,
                                                activate_session,
                                                create_cursor_memory_kernel,
                                                get_active_kernel)
# GMP v2.0 Meta-Learning (Cursor-specific)
from agents.cursor.gmp_meta_learning import (AutonomyController,
                                             AutonomyGraduationMetrics,
                                             AutonomyLevel, GMPExecutionResult,
                                             GMPMetaLearningEngine,
                                             LearnedHeuristic)

__all__ = [
    # Kernel
    "CursorMemoryKernel",
    "create_cursor_memory_kernel",
    "activate_session",
    "get_active_kernel",
    "SessionState",
    "Lesson",
    "TodoItem",
    # Client
    "CursorClient",
    # GMP Meta-Learning
    "GMPMetaLearningEngine",
    "AutonomyController",
    "AutonomyLevel",
    "GMPExecutionResult",
    "LearnedHeuristic",
    "AutonomyGraduationMetrics",
]
