"""
Artifact Memory (AM) Engine: Compile human knowledge into machine-enforceable law.

Transforms:
  Raw Artifacts (MD, PDF, TXT) → Classified → Extracted → YAML Law

Never modifies existing law (idempotent). Never invents rules (conservative).
Always preserves provenance (source hashes).
"""

__version__ = "1.0.0"

from dev_layer.am_engine import classify, compile, validate

__all__ = ["classify", "compile", "validate"]
