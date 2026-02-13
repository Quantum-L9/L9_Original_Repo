"""
Dev Layer: Code Engineering Governance Module for L9

Core components:
- AM Engine: Artifact → YAML law compiler
- Runtime: Enforcement + governance gates
- Modules: Code planning, synthesis, verification

Authority: L (CTO)
Executor: CA (Coding Agent)
"""

__version__ = "1.0.0"
__author__ = "L9 Engineering"

from dev_layer import am_engine, runtime, modules

__all__ = [
    "am_engine",
    "runtime",
    "modules",
    "__version__",
]
