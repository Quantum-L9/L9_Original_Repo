"""
AM Engine Core: Compile artifacts into canonical YAML law.

Pipeline:
  Artifact → Classify → Extract → Validate → Emit YAML

Properties:
- Idempotent: same input → same output path (no overwrites)
- Conservative: unknown fields preserved, never hallucinated
- Auditable: source hash + provenance in every YAML
- Deterministic: hash-based filenames, canonical JSON for comparison
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Compile",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-15T22:07:09Z",
    "updated_at": "2026-01-15T22:07:09Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "compile",
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

import os
import sys
import yaml
import hashlib
import json
import logging  # noqa: ADR-0019
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class ArtifactCategory(str, Enum):
    """Valid artifact categories (AM output schema types)."""

    CONSTRAINT = "constraints"
    PROTOCOL = "protocols"
    POLICY = "policies"
    PATTERN = "patterns"
    HEURISTIC = "heuristics"
    INTERFACE = "interfaces"
    WORLD_MODEL = "world_model"
    REFLECTION_RULE = "reflection_rules"
    CODEGEN = "codegen"


@dataclass
class ClassificationResult:
    """Result of document classification."""

    category: ArtifactCategory
    confidence: float  # 0.0 - 1.0
    keywords_matched: List[str] = field(default_factory=list)
    extracted_fields: Dict[str, Any] = field(default_factory=dict)


class ArtifactClassifier:
    """Classify documents into artifact categories based on keyword hints."""

    CLASSIFICATION_HINTS = {
        ArtifactCategory.CONSTRAINT: {
            "keywords": [
                "must not",
                "forbidden",
                "hard limit",
                "blocking",
                "constraint",
                "C-",
            ],
            "description": "Hard rules that block operations",
        },
        ArtifactCategory.PROTOCOL: {
            "keywords": ["sequence", "order", "step", "stage", "phase", "flow", "P-"],
            "description": "Required execution sequences",
        },
        ArtifactCategory.POLICY: {
            "keywords": ["if", "then", "conditional", "routing", "escalate", "POL-"],
            "description": "Conditional decision rules",
        },
        ArtifactCategory.PATTERN: {
            "keywords": ["pattern", "structure", "design", "MVC", "CQRS", "Hexagonal"],
            "description": "Architectural patterns and structures",
        },
        ArtifactCategory.HEURISTIC: {
            "keywords": ["never", "always", "avoid", "prefer", "H-", "rule of thumb"],
            "description": "Engineering heuristics and judgment rules",
        },
        ArtifactCategory.INTERFACE: {
            "keywords": ["contract", "input", "output", "schema", "API", "field"],
            "description": "Interface and contract specifications",
        },
        ArtifactCategory.WORLD_MODEL: {
            "keywords": ["service", "component", "dependency", "topology", "entity"],
            "description": "System topology and entity relationships",
        },
        ArtifactCategory.REFLECTION_RULE: {
            "keywords": ["signal", "lesson", "learning", "evidence", "mistake"],
            "description": "Reflection and learning rules",
        },
        ArtifactCategory.CODEGEN: {
            "keywords": ["codegen", "generate", "emit", "diff", "production", "ready"],
            "description": "Code generation and automation rules",
        },
    }

    def classify(self, text: str) -> ClassificationResult:
        """
        Classify document into category with confidence.

        Returns highest-scoring category based on keyword matches.
        """
        text_lower = text.lower()
        scores: Dict[ArtifactCategory, Tuple[float, List[str]]] = {}

        for category, hints in self.CLASSIFICATION_HINTS.items():
            score = 0.0
            matched_keywords: List[str] = []

            # Keyword matching: +0.2 per keyword match
            for keyword in hints["keywords"]:
                if keyword.lower() in text_lower:
                    score += 0.2
                    matched_keywords.append(keyword)

            scores[category] = (score, matched_keywords)

        # Find best match (ties broken by category order)
        best_category = max(scores.keys(), key=lambda c: scores[c][0])
        best_score, best_keywords = scores[best_category]
        confidence = min(best_score, 1.0)  # Cap at 1.0

        logger.info(
            f"Classified as {best_category.value} "
            f"(confidence: {confidence:.2f}, keywords: {best_keywords})"
        )

        return ClassificationResult(
            category=best_category,
            confidence=confidence,
            keywords_matched=best_keywords,
            extracted_fields={},  # TODO: Expand extraction per category
        )


class ArtifactCompiler:
    """Compile artifacts into canonical YAML law."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.classifier = ArtifactClassifier()
        self.compiled_index: Dict[str, Dict[str, Any]] = {}

    def compile_artifact(
        self,
        artifact_text: str,
        source_path: str,
        force_category: Optional[ArtifactCategory] = None,
    ) -> Optional[Path]:
        """
        Compile a single artifact document into YAML.

        Args:
            artifact_text: Raw document content
            source_path: Source file path (for provenance)
            force_category: Override classification if specified

        Returns:
            Path to emitted YAML file, or None if skipped/failed
        """
        # Classify
        if force_category:
            classification = ClassificationResult(
                category=force_category,
                confidence=1.0,
                keywords_matched=[],
                extracted_fields={},
            )
            logger.info(f"Using forced category: {force_category.value}")
        else:
            classification = self.classifier.classify(artifact_text)

        # Skip low-confidence unless forced
        if classification.confidence < 0.5 and not force_category:
            logger.warning(
                f"Low confidence classification ({classification.confidence:.2f}): {source_path}"
            )
            return None

        # Compute source hash for provenance
        source_hash = hashlib.sha256(artifact_text.encode()).hexdigest()[:8]

        # Build canonical YAML structure
        canonical = {
            "metadata": {
                "source_document": source_path,
                "source_hash": source_hash,
                "category": classification.category.value,
                "confidence": float(classification.confidence),
                "compiled_at": datetime.now(timezone.utc).isoformat(),
            },
            "extracted": classification.extracted_fields,
            "raw_text_excerpt": artifact_text[:500],  # Keep snippet for reference
        }

        # Determine output path
        category_dir = self.output_dir / classification.category.value
        category_dir.mkdir(parents=True, exist_ok=True)

        output_path = category_dir / f"{Path(source_path).stem}_{source_hash}.yaml"

        # Skip if already exists (idempotent)
        if output_path.exists():
            logger.info(f"Skipping {output_path.name} (already exists, idempotent)")
            return output_path

        # Emit YAML
        try:
            with open(output_path, "w") as f:
                yaml.dump(canonical, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Emitted {output_path.relative_to(self.output_dir)}")
        except Exception as e:
            logger.error(f"Failed to emit YAML for {source_path}: {e}")
            return None

        # Track in index
        self.compiled_index[source_path] = {
            "output": str(output_path),
            "category": classification.category.value,
            "hash": source_hash,
        }

        return output_path

    def compile_directory(
        self,
        input_dir: Path,
        extensions: List[str] = None,
    ) -> Dict[str, List[Path]]:
        """
        Recursively compile all artifacts in a directory.

        Args:
            input_dir: Input directory containing raw artifacts
            extensions: File extensions to process (default: .md, .txt, .yaml)

        Returns:
            Dict of category → [output paths]
        """
        if extensions is None:
            extensions = [".md", ".txt", ".yaml"]

        results: Dict[str, List[Path]] = {cat.value: [] for cat in ArtifactCategory}

        input_dir = Path(input_dir)
        if not input_dir.exists():
            logger.warning(f"Input directory not found: {input_dir}")
            return results

        for ext in extensions:
            for artifact_file in input_dir.rglob(f"*{ext}"):
                try:
                    with open(artifact_file, "r", encoding="utf-8") as f:
                        text = f.read()

                    output = self.compile_artifact(
                        text,
                        source_path=str(artifact_file.relative_to(input_dir)),
                    )

                    if output:
                        # Determine category from output path
                        category = output.parent.name
                        results[category].append(output)

                except Exception as e:
                    logger.error(f"Failed to process {artifact_file}: {e}")

        # Emit compilation index
        index_file = self.output_dir / "compilation_index.json"
        try:
            with open(index_file, "w") as f:
                json.dump(self.compiled_index, f, indent=2)
            logger.info(f"Compiled index saved to {index_file}")
        except Exception as e:
            logger.error(f"Failed to save compilation index: {e}")

        return results


def load_canonical_yaml(category_dir: Path) -> Dict[str, Any]:
    """
    Load all canonical YAML from a category directory.

    Used at runtime to load compiled law.

    Args:
        category_dir: Directory containing compiled YAML files

    Returns:
        Merged dictionary of all YAML files
    """
    category_dir = Path(category_dir)
    merged = {}

    if not category_dir.exists():
        logger.warning(f"Category directory not found: {category_dir}")
        return merged

    for yaml_file in sorted(category_dir.glob("*.yaml")):
        try:
            with open(yaml_file, "r") as f:
                data = yaml.safe_load(f)
            if data:
                merged[yaml_file.stem] = data
                logger.debug(f"Loaded {yaml_file.stem}")
        except Exception as e:
            logger.error(f"Failed to load {yaml_file}: {e}")

    return merged


def main():
    """CLI entry point for AM Engine compilation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="AM Engine: Compile artifacts into canonical YAML law."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("dev_layer/artifacts/raw"),
        help="Input directory of raw artifacts",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dev_layer/artifacts/compiled"),
        help="Output directory for compiled YAML",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Compile
    compiler = ArtifactCompiler(args.output)
    results = compiler.compile_directory(args.input)

    # Report
    total = sum(len(v) for v in results.values())
    logger.info(f"Compilation complete: {total} artifacts compiled.")

    for category, paths in sorted(results.items()):
        if paths:
            logger.info(f"  {category}: {len(paths)} file(s)")


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-027",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "audit-tool",
        "cli",
        "config",
        "data-models",
        "dataclass",
        "debugging",
        "filesystem",
        "foundation",
        "messaging",
    ],
    "keywords": [
        "artifact",
        "canonical",
        "category",
        "classification",
        "classifier",
        "classify",
        "compile",
        "compiler",
    ],
    "business_value": "Provides compile components including ArtifactCategory, ClassificationResult, ArtifactClassifier",
    "last_modified": "2026-01-15T22:07:09Z",
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
