#!/usr/bin/env python3
"""
L9 Document Compiler
====================
Converts human-authored artifacts into machine-enforceable runtime law.

This is the AM Engine (Artifact → Memory/Module Engine) - a compiler that:
- Takes markdown/text documents as input
- Classifies them by schema type
- Extracts structured information
- Emits canonical YAML artifacts
- Preserves provenance and traceability

Usage:
    python l9_doc_compiler.py <input_dir> <output_dir>

Example:
    python l9_doc_compiler.py artifacts/raw artifacts/compiled
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 Doc Compiler",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-20T18:07:27Z",
    "updated_at": "2026-01-20T23:43:16Z",
    "layer": "operations",
    "domain": "current_work",
    "module_name": "l9_doc_compiler",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SourceMetadata:
    """Metadata about the source document."""

    document: str
    hash: str
    confidence: float
    extracted_at: str


@dataclass
class Schema:
    """Schema definition for artifact classification."""

    schema_id: str
    required_fields: list[str]
    optional_fields: list[str]
    classification_hints: dict[str, list[str]]
    output_category: str


class DocumentClassifier:
    """Classifies documents based on schema hints."""

    def __init__(self, schemas: list[Schema]) -> None:
        """Initialize classifier with schemas."""
        self.schemas = schemas

    def classify(self, text: str) -> Schema | None:
        """Classify a document by scoring against all schemas."""
        scores = {}
        text_lower = text.lower()

        for schema in self.schemas:
            score = 0
            keywords = schema.classification_hints.get("keywords", [])
            for keyword in keywords:
                score += text_lower.count(keyword.lower())
            scores[schema.schema_id] = score

        if not scores or max(scores.values()) == 0:
            return None

        best_schema_id = max(scores, key=scores.get)
        return next(s for s in self.schemas if s.schema_id == best_schema_id)


class ArtifactExtractor:
    """Base class for extracting structured data from documents."""

    def extract(self, text: str, schema: Schema) -> dict[str, Any]:
        """Extract structured data based on schema. Override in subclasses."""
        raise NotImplementedError


class ConstraintExtractor(ArtifactExtractor):
    """Extracts constraint definitions from documents."""

    def extract(self, text: str, schema: Schema) -> dict[str, Any]:
        result = {
            "constraint_id": self._extract_id(text, "constraint"),
            "rule": self._extract_rule(text),
            "scope": self._extract_scope(text),
            "severity": self._extract_severity(text),
            "rationale": self._extract_rationale(text),
        }
        return {k: v for k, v in result.items() if v is not None}

    def _extract_id(self, text: str, prefix: str) -> str | None:
        """Extract constraint ID from text."""
        # Look for explicit IDs or generate from content
        match = re.search(
            r"(?:constraint[_\s]?id|id):\s*([A-Z0-9\-]+)", text, re.IGNORECASE
        )
        if match:
            return match.group(1)
        return None

    def _extract_rule(self, text: str) -> str | None:
        """Extract rule definition from text."""
        # Look for rule definitions
        match = re.search(r"(?:rule|constraint):\s*([^\n]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_scope(self, text: str) -> str | None:
        """Extract scope from text."""
        match = re.search(r"scope:\s*([^\n]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "code"

    def _extract_severity(self, text: str) -> str:
        """Extract severity level from text."""
        if re.search(r"\b(blocking|critical|must)\b", text, re.IGNORECASE):
            return "blocking"
        if re.search(r"\b(warning|should)\b", text, re.IGNORECASE):
            return "warning"
        return "info"

    def _extract_rationale(self, text: str) -> str | None:
        """Extract rationale from text."""
        match = re.search(r"(?:rationale|why|reason):\s*([^\n]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None


class ProtocolExtractor(ArtifactExtractor):
    """Extracts protocol/workflow definitions."""

    def extract(self, text: str, schema: Schema) -> dict[str, Any]:
        """Extract protocol data from text."""
        result = {
            "protocol_id": self._extract_id(text),
            "name": self._extract_name(text),
            "steps": self._extract_steps(text),
            "enforcement": self._extract_enforcement(text),
        }
        return {k: v for k, v in result.items() if v is not None}

    def _extract_id(self, text: str) -> str | None:
        """Extract protocol ID from text."""
        match = re.search(
            r"(?:protocol[_\s]?id|id):\s*([A-Z0-9\-]+)", text, re.IGNORECASE
        )
        if match:
            return match.group(1)
        return None

    def _extract_name(self, text: str) -> str | None:
        """Extract protocol name from text."""
        match = re.search(r"(?:name|protocol):\s*([^\n]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_steps(self, text: str) -> list[str]:
        """Extract protocol steps from text."""
        steps = []
        # Look for numbered lists or bullet points
        for match in re.finditer(r"(?:^|\n)\s*(?:\d+\.|\-|\*)\s*([^\n]+)", text):
            step = match.group(1).strip()
            if len(step) > 3:  # Filter out noise
                steps.append(step)
        return steps if steps else []

    def _extract_enforcement(self, text: str) -> str:
        """Extract enforcement level from text."""
        if re.search(r"\b(required|must|mandatory)\b", text, re.IGNORECASE):
            return "required"
        return "recommended"


class PatternExtractor(ArtifactExtractor):
    """Extracts architectural pattern definitions."""

    def extract(self, text: str, schema: Schema) -> dict[str, Any]:
        """Extract pattern data from text."""
        result = {
            "pattern_id": self._extract_id(text),
            "name": self._extract_name(text),
            "intent": self._extract_intent(text),
            "applicability": self._extract_applicability(text),
            "constraints": self._extract_constraints(text),
            "failure_modes": self._extract_failure_modes(text),
        }
        return {k: v for k, v in result.items() if v is not None}

    def _extract_id(self, text: str) -> str | None:
        """Extract pattern ID from text."""
        # Look for common pattern names
        patterns = ["MVC", "CQRS", "Hexagonal", "Event-Driven", "Microservices"]
        for pattern in patterns:
            if pattern.lower() in text.lower():
                return pattern.upper().replace(" ", "_")
        return None

    def _extract_name(self, text: str) -> str | None:
        """Extract pattern name from text."""
        match = re.search(r"(?:pattern|name):\s*([^\n]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_intent(self, text: str) -> str | None:
        """Extract pattern intent from text."""
        match = re.search(r"(?:intent|purpose|goal):\s*([^\n]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_applicability(self, text: str) -> str | None:
        """Extract applicability from text."""
        match = re.search(
            r"(?:when to use|applicability):\s*([^\n]+)", text, re.IGNORECASE
        )
        if match:
            return match.group(1).strip()
        return None

    def _extract_constraints(self, text: str) -> list[str]:
        """Extract constraints from text."""
        constraints = []
        for match in re.finditer(
            r"(?:constraint|rule):\s*([^\n]+)", text, re.IGNORECASE
        ):
            constraints.append(match.group(1).strip())
        return constraints

    def _extract_failure_modes(self, text: str) -> list[str]:
        """Extract failure modes from text."""
        modes = []
        for match in re.finditer(
            r"(?:failure|anti-pattern|avoid):\s*([^\n]+)", text, re.IGNORECASE
        ):
            modes.append(match.group(1).strip())
        return modes


class HeuristicExtractor(ArtifactExtractor):
    """Extracts heuristic/judgment rules."""

    def extract(self, text: str, schema: Schema) -> dict[str, Any]:
        """Extract heuristic data from text."""
        result = {
            "heuristic_id": self._extract_id(text),
            "rule": self._extract_rule(text),
            "rationale": self._extract_rationale(text),
            "violation_signals": self._extract_violations(text),
            "severity": self._extract_severity(text),
        }
        return {k: v for k, v in result.items() if v is not None}

    def _extract_id(self, text: str) -> str | None:
        """Extract heuristic ID from text."""
        match = re.search(
            r"(?:heuristic[_\s]?id|id):\s*([A-Z0-9\-]+)", text, re.IGNORECASE
        )
        if match:
            return match.group(1)
        return None

    def _extract_rule(self, text: str) -> str | None:
        """Extract heuristic rule from text."""
        match = re.search(r"(?:rule|heuristic):\s*([^\n]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_rationale(self, text: str) -> str | None:
        """Extract rationale from text."""
        match = re.search(r"(?:rationale|why):\s*([^\n]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_violations(self, text: str) -> list[str]:
        """Extract violation signals from text."""
        violations = []
        for match in re.finditer(
            r"(?:violation|signal|indicator):\s*([^\n]+)", text, re.IGNORECASE
        ):
            violations.append(match.group(1).strip())
        return violations

    def _extract_severity(self, text: str) -> str:
        """Extract severity level from text."""
        if re.search(r"\b(critical|blocking)\b", text, re.IGNORECASE):
            return "critical"
        if re.search(r"\b(warning|important)\b", text, re.IGNORECASE):
            return "warning"
        return "info"


class L9Compiler:
    """Main compiler that orchestrates the compilation process."""

    def __init__(self):
        self.schemas = self._load_schemas()
        self.classifier = DocumentClassifier(self.schemas)
        self.extractors = {
            "constraint": ConstraintExtractor(),
            "protocol": ProtocolExtractor(),
            "pattern": PatternExtractor(),
            "heuristic": HeuristicExtractor(),
        }

    def _load_schemas(self) -> list[Schema]:
        """Load schema definitions."""
        return [
            Schema(
                schema_id="constraint",
                required_fields=["constraint_id", "rule", "scope", "severity"],
                optional_fields=["rationale", "examples"],
                classification_hints={
                    "keywords": [
                        "constraint",
                        "must",
                        "forbidden",
                        "required",
                        "blocking",
                    ]
                },
                output_category="constraints",
            ),
            Schema(
                schema_id="protocol",
                required_fields=["protocol_id", "steps"],
                optional_fields=["name", "enforcement"],
                classification_hints={
                    "keywords": ["protocol", "workflow", "sequence", "steps", "process"]
                },
                output_category="protocols",
            ),
            Schema(
                schema_id="pattern",
                required_fields=["pattern_id", "intent"],
                optional_fields=["applicability", "constraints", "failure_modes"],
                classification_hints={
                    "keywords": ["pattern", "architecture", "design", "structure"]
                },
                output_category="patterns",
            ),
            Schema(
                schema_id="heuristic",
                required_fields=["heuristic_id", "rule"],
                optional_fields=["rationale", "violation_signals", "severity"],
                classification_hints={
                    "keywords": ["heuristic", "judgment", "guideline", "best practice"]
                },
                output_category="heuristics",
            ),
        ]

    def compile_document(self, doc_path: Path, output_dir: Path) -> Path | None:
        """Compile a single document into YAML artifact(s)."""
        try:
            text = doc_path.read_text(encoding="utf-8")

            # Classify the document
            schema = self.classifier.classify(text)
            if not schema:
                print(f"⚠️  Could not classify: {doc_path.name}")
                return None

            print(f"📄 Processing {doc_path.name} as {schema.schema_id}")

            # Extract structured data
            extractor = self.extractors.get(schema.schema_id)
            if not extractor:
                print(f"⚠️  No extractor for schema: {schema.schema_id}")
                return None

            data = extractor.extract(text, schema)

            # Add source metadata
            data["source"] = {
                "document": doc_path.name,
                "hash": self._hash_file(doc_path),
                "confidence": self._calculate_confidence(data, schema),
            }

            # Determine output path
            category_dir = output_dir / schema.output_category
            category_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            artifact_id = data.get(f"{schema.schema_id}_id", doc_path.stem)
            output_path = category_dir / f"{artifact_id}.yaml"

            # Write YAML (never overwrite existing)
            if output_path.exists():
                print(f"⏭️  Skipping (exists): {output_path}")
                return None

            with open(output_path, "w") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

            print(f"✅ Created: {output_path}")
            return output_path

        except Exception as e:
            print(f"❌ Error processing {doc_path.name}: {e}")
            return None

    def _hash_file(self, path: Path) -> str:
        """Generate hash of file content."""
        return hashlib.md5(path.read_bytes()).hexdigest()[:8]

    def _calculate_confidence(self, data: dict, schema: Schema) -> float:
        """Calculate extraction confidence based on required fields."""
        required_present = sum(1 for field in schema.required_fields if data.get(field))
        return round(required_present / len(schema.required_fields), 2)

    def compile_directory(self, input_dir: Path, output_dir: Path):
        """Compile all documents in a directory."""
        print("\n🔧 L9 Document Compiler")
        print(f"📂 Input:  {input_dir}")
        print(f"📂 Output: {output_dir}\n")

        # Find all markdown and text files
        files = list(input_dir.glob("*.md")) + list(input_dir.glob("*.txt"))

        if not files:
            print("⚠️  No documents found to compile")
            return

        compiled = []
        for doc_path in files:
            result = self.compile_document(doc_path, output_dir)
            if result:
                compiled.append(result)

        print(f"\n✨ Compilation complete: {len(compiled)} artifacts created")


def main():
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python l9_doc_compiler.py <input_dir> <output_dir>")
        print("Example: python l9_doc_compiler.py artifacts/raw artifacts/compiled")
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    if not input_dir.exists():
        print(f"❌ Input directory does not exist: {input_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    compiler = L9Compiler()
    compiler.compile_directory(input_dir, output_dir)


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-038",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "auth",
        "config",
        "current-work",
        "dataclass",
        "event-driven",
        "filesystem",
        "operations",
        "security",
        "tracing",
    ],
    "keywords": [
        "artifact",
        "classifier",
        "classify",
        "compile",
        "compiler",
        "constraint",
        "directory",
        "doc",
    ],
    "business_value": "Takes markdown/text documents as input Classifies them by schema type Extracts structured information Emits canonical YAML artifacts Preserves provenance and traceability python l9_doc_compiler.py <in",
    "last_modified": "2026-01-20T23:43:16Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
