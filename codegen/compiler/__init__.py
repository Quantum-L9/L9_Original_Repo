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

from .transcript_compiler import TranscriptCompiler
from .classifier import classify_claim
from .validator_bridge import validate_outputs
from .schemas import validate_schema

__all__ = [
    "TranscriptCompiler",
    "classify_claim",
    "validate_outputs",
    "validate_schema",
]
