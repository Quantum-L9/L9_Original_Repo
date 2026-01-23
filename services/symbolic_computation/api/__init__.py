"""
SymPy Symbolic Computation API
===============================

FastAPI router for symbolic computation endpoints.

Version: 6.0.0
"""

from services.symbolic_computation.api.routes import router

__all__ = ["router"]
