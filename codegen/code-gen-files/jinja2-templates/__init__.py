"""
L9 Research Factory - Templates
================================

Jinja2 templates for code generation.

Templates:
- controller.py.j2: Agent controller with lifecycle management
- __init__.py.j2: Module initialization
- test_agent.py.j2: Pytest test suite
- README.md.j2: Agent documentation

Version: 1.0.0
"""

from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent  # noqa: ADR-0001 - internal path

__all__ = ["TEMPLATES_DIR"]
