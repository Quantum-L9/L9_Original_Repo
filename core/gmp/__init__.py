"""
L9 GMP v2.0 Meta-Learning System
================================

Progressive autonomy evolution (L2→L5) with meta-learning capabilities.

Modules:
- meta_learning_engine: Execution pattern analysis and heuristic generation
- (future) autonomy_controller: L2→L5 progression management
- (future) pattern_analyzer: Cross-GMP pattern discovery

Usage:
    from core.gmp import GMPMetaLearningEngine, AutonomyController

    engine = GMPMetaLearningEngine(database_url="postgresql://...")
    controller = AutonomyController(engine)
"""

from core.gmp.meta_learning_engine import (
    AutonomyLevel,
    GMPExecutionResult,
    LearnedHeuristic,
    AutonomyGraduationMetrics,
    GMPMetaLearningEngine,
    AutonomyController,
)

__all__ = [
    "AutonomyLevel",
    "GMPExecutionResult",
    "LearnedHeuristic",
    "AutonomyGraduationMetrics",
    "GMPMetaLearningEngine",
    "AutonomyController",
]

__version__ = "2.0.0"
