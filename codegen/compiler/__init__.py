# codegen/compiler/__init__.py
"""
L9 Transcript Compiler Package

Extracts structured artifacts from conversation transcripts.
Converts natural language into typed YAML for the L9 system.

Usage:
    from codegen.compiler import TranscriptCompiler

    compiler = TranscriptCompiler()
    artifacts = compiler.compile(transcript_text)
"""

from .classifier import classify_claim
from .schemas import validate_schema
from .transcript_compiler import TranscriptCompiler
from .validator_bridge import validate_outputs

__all__ = [
    "TranscriptCompiler",
    "classify_claim",
    "validate_outputs",
    "validate_schema",
]
