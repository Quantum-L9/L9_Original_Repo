#!/usr/bin/env python3
"""
L9 Knowledge Harvester
======================
Scans your files and extracts concepts that can become L9 components.

Features:
- Scans Dropbox/Knowledge-Harvesting folder
- Extracts concepts from .md, .yaml, .docx, .pdf files
- Generates structured YAML specs
- Provides summary reports
- QC dashboard for review/approval

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 Knowledge Harvester",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-20T18:47:58Z",
    "updated_at": "2026-01-20T23:43:16Z",
    "layer": "operations",
    "domain": "current_work",
    "module_name": "l9_knowledge_harvester",
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
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import yaml


@dataclass
class ExtractedConcept:
    """A concept extracted from a file."""

    concept_id: str
    source_file: str
    file_type: str
    concept_name: str
    description: str
    category: str  # adapter, pattern, heuristic, constraint, protocol, policy
    confidence: float  # 0.0 - 1.0
    extracted_content: str
    metadata: dict
    created_at: str


@dataclass
class ConceptYAML:
    """Structured YAML representation of a concept."""

    CONCEPT_NAME: str
    VERSION: str
    CATEGORY: str
    ONE_SENTENCE: str
    ARCHITECTURE: dict
    DATA_FLOW: str
    DECISION_POINTS: list[str]
    AUDITABLE_OUTPUTS: list[str]
    EXPANDABILITY: list[str]
    EXAMPLE_USE_CASE: str
    EXTERNAL_DEPENDENCIES: list[str] | None = None
    SOURCE_FILE: str | None = None
    EXTRACTION_CONFIDENCE: float | None = None


class FileScanner:
    """Scans directories and finds processable files."""

    SUPPORTED_EXTENSIONS = {".md", ".yaml", ".yml", ".docx", ".pdf", ".txt"}

    def __init__(self, root_dir: Path):
        """
        Initialize the file scanner.

        Args:
            root_dir: Root directory to scan
        """
        self.root_dir = Path(root_dir).expanduser()

    def scan(self) -> list[Path]:
        """
        Scan directory and return list of processable files.

        Returns:
            List of file paths
        """
        files = []

        if not self.root_dir.exists():
            raise ValueError(f"Directory does not exist: {self.root_dir}")

        for file_path in self.root_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in self.SUPPORTED_EXTENSIONS:
                files.append(file_path)

        return sorted(files)

    def get_file_info(self, file_path: Path) -> dict:
        """
        Get metadata about a file.

        Args:
            file_path: Path to file

        Returns:
            File metadata
        """
        stat = file_path.stat()

        return {
            "path": str(file_path),
            "name": file_path.name,
            "extension": file_path.suffix,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "relative_path": str(file_path.relative_to(self.root_dir)),
        }


class ConceptExtractor:
    """Extracts concepts from files using aggressive pattern matching."""

    # Patterns that indicate a concept
    CONCEPT_PATTERNS = [
        r"(?:CONCEPT|Concept|concept):\s*(.+)",
        r"(?:Module|MODULE|module):\s*(.+)",
        r"(?:Component|COMPONENT|component):\s*(.+)",
        r"(?:Pattern|PATTERN|pattern):\s*(.+)",
        r"(?:Adapter|ADAPTER|adapter):\s*(.+)",
        r"(?:Heuristic|HEURISTIC|heuristic):\s*(.+)",
        r"(?:Constraint|CONSTRAINT|constraint):\s*(.+)",
        r"(?:Protocol|PROTOCOL|protocol):\s*(.+)",
    ]

    # Category keywords
    CATEGORY_KEYWORDS = {
        "adapter": ["adapter", "integration", "api", "client", "connector"],
        "pattern": ["pattern", "architecture", "design", "structure"],
        "heuristic": ["heuristic", "rule", "guideline", "best practice"],
        "constraint": ["constraint", "limit", "boundary", "restriction"],
        "protocol": ["protocol", "workflow", "process", "procedure"],
        "policy": ["policy", "governance", "compliance", "audit"],
    }

    def __init__(self, aggressive: bool = True):
        """
        Initialize the concept extractor.

        Args:
            aggressive: If True, extract aggressively
        """
        self.aggressive = aggressive

    def extract_from_file(self, file_path: Path) -> list[ExtractedConcept]:
        """
        Extract concepts from a file.

        Args:
            file_path: Path to file

        Returns:
            List of extracted concepts
        """
        content = self._read_file(file_path)

        if not content:
            return []

        concepts = []

        # Extract by pattern matching
        for pattern in self.CONCEPT_PATTERNS:
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                concept = self._create_concept_from_match(file_path, content, match)
                if concept:
                    concepts.append(concept)

        # If aggressive, also extract from headers
        if self.aggressive:
            header_concepts = self._extract_from_headers(file_path, content)
            concepts.extend(header_concepts)

        # If aggressive, extract from YAML structure
        if self.aggressive and file_path.suffix in [".yaml", ".yml"]:
            yaml_concepts = self._extract_from_yaml(file_path, content)
            concepts.extend(yaml_concepts)

        return concepts

    def _read_file(self, file_path: Path) -> str | None:
        """Read file content based on type."""
        try:
            if file_path.suffix in [".md", ".txt", ".yaml", ".yml"]:
                return file_path.read_text(encoding="utf-8", errors="ignore")

            if file_path.suffix == ".pdf":
                # Use pdftotext if available
                import subprocess

                try:
                    result = subprocess.run(
                        ["pdftotext", str(file_path), "-"],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    return result.stdout
                except Exception:
                    return None

            elif file_path.suffix == ".docx":
                # Use python-docx if available
                try:
                    import docx

                    doc = docx.Document(file_path)
                    return "\n".join([para.text for para in doc.paragraphs])
                except Exception:
                    return None

            return None

        except Exception as e:
            print(f"⚠️  Error reading {file_path}: {e}")
            return None

    def _create_concept_from_match(
        self, file_path: Path, content: str, match: re.Match
    ) -> ExtractedConcept | None:
        """Create a concept from a regex match."""
        concept_name = match.group(1).strip()

        # Extract surrounding context (500 chars before and after)
        start = max(0, match.start() - 500)
        end = min(len(content), match.end() + 500)
        context = content[start:end]

        # Determine category
        category = self._determine_category(concept_name, context)

        # Calculate confidence
        confidence = self._calculate_confidence(concept_name, context, category)

        # Generate unique ID
        concept_id = self._generate_id(file_path, concept_name)

        # Extract description (first paragraph after match)
        description = self._extract_description(content, match.end())

        return ExtractedConcept(
            concept_id=concept_id,
            source_file=str(file_path),
            file_type=file_path.suffix,
            concept_name=concept_name,
            description=description,
            category=category,
            confidence=confidence,
            extracted_content=context,
            metadata={
                "match_position": match.start(),
                "match_pattern": match.re.pattern,
            },
            created_at=datetime.now(timezone.utc).isoformat() + "Z",
        )

    def _extract_from_headers(
        self, file_path: Path, content: str
    ) -> list[ExtractedConcept]:
        """Extract concepts from markdown headers."""
        concepts = []

        # Find all headers (# Header)
        header_pattern = r"^#+\s+(.+)$"
        matches = re.finditer(header_pattern, content, re.MULTILINE)

        for match in matches:
            header_text = match.group(1).strip()

            # Skip generic headers
            if len(header_text) < 5 or header_text.lower() in [
                "introduction",
                "overview",
                "conclusion",
            ]:
                continue

            # Extract context
            start = max(0, match.start() - 200)
            end = min(len(content), match.end() + 800)
            context = content[start:end]

            category = self._determine_category(header_text, context)
            confidence = (
                self._calculate_confidence(header_text, context, category) * 0.7
            )  # Lower confidence for headers

            if confidence > 0.3:  # Only include if reasonable confidence
                concept_id = self._generate_id(file_path, header_text)
                description = self._extract_description(content, match.end())

                concepts.append(
                    ExtractedConcept(
                        concept_id=concept_id,
                        source_file=str(file_path),
                        file_type=file_path.suffix,
                        concept_name=header_text,
                        description=description,
                        category=category,
                        confidence=confidence,
                        extracted_content=context,
                        metadata={"source": "header"},
                        created_at=datetime.now(timezone.utc).isoformat() + "Z",
                    )
                )

        return concepts

    def _extract_from_yaml(
        self, file_path: Path, content: str
    ) -> list[ExtractedConcept]:
        """Extract concepts from YAML structure."""
        concepts = []

        try:
            data = yaml.safe_load(content)

            if not isinstance(data, dict):
                return concepts

            # Look for concept-like structures
            if "CONCEPT_NAME" in data or "name" in data:
                concept_name = data.get("CONCEPT_NAME") or data.get("name")
                description = data.get("ONE_SENTENCE") or data.get("description") or ""

                concept_id = self._generate_id(file_path, concept_name)
                category = self._determine_category(concept_name, str(data))

                concepts.append(
                    ExtractedConcept(
                        concept_id=concept_id,
                        source_file=str(file_path),
                        file_type=file_path.suffix,
                        concept_name=concept_name,
                        description=description,
                        category=category,
                        confidence=0.9,  # High confidence for structured YAML
                        extracted_content=content,
                        metadata={"source": "yaml_structure"},
                        created_at=datetime.now(timezone.utc).isoformat() + "Z",
                    )
                )

        except Exception:
            pass

        return concepts

    def _determine_category(self, name: str, context: str) -> str:
        """Determine concept category based on keywords."""
        name_lower = name.lower()
        context_lower = context.lower()

        scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in name_lower or kw in context_lower)
            scores[category] = score

        if scores:
            return max(scores, key=scores.get)

        return "pattern"  # Default

    def _calculate_confidence(self, name: str, context: str, category: str) -> float:
        """Calculate extraction confidence."""
        confidence = 0.5  # Base confidence

        # Boost if category keywords present
        if any(
            kw in context.lower() for kw in self.CATEGORY_KEYWORDS.get(category, [])
        ):
            confidence += 0.2

        # Boost if has structured elements
        if "architecture" in context.lower() or "component" in context.lower():
            confidence += 0.1

        # Boost if has example
        if "example" in context.lower() or "use case" in context.lower():
            confidence += 0.1

        # Boost if has data flow
        if "→" in context or "flow" in context.lower():
            confidence += 0.1

        return min(1.0, confidence)

    def _extract_description(self, content: str, start_pos: int) -> str:
        """Extract description (first paragraph after position)."""
        remaining = content[start_pos : start_pos + 500]

        # Find first non-empty line
        lines = remaining.split("\n")
        desc_lines = []

        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                desc_lines.append(line)
                if len(" ".join(desc_lines)) > 200:
                    break

        return " ".join(desc_lines)[:300]

    def _generate_id(self, file_path: Path, concept_name: str) -> str:
        """Generate unique concept ID."""
        content = f"{file_path.name}:{concept_name}"
        hash_obj = hashlib.md5(content.encode())
        return f"concept_{hash_obj.hexdigest()[:12]}"


class YAMLGenerator:
    """Generates structured YAML from extracted concepts."""

    def generate(self, concept: ExtractedConcept) -> ConceptYAML:
        """
        Generate structured YAML from concept.

        Args:
            concept: Extracted concept

        Returns:
            Structured YAML
        """
        # Parse architecture from content
        architecture = self._parse_architecture(concept.extracted_content)

        # Parse data flow
        data_flow = self._parse_data_flow(concept.extracted_content)

        # Parse decision points
        decision_points = self._parse_decision_points(concept.extracted_content)

        # Parse auditable outputs
        auditable_outputs = self._parse_auditable_outputs(concept.extracted_content)

        # Parse expandability
        expandability = self._parse_expandability(concept.extracted_content)

        # Generate example use case
        example = self._generate_example(concept)

        return ConceptYAML(
            CONCEPT_NAME=self._sanitize_name(concept.concept_name),
            VERSION="0.1.0",
            CATEGORY=concept.category,
            ONE_SENTENCE=concept.description
            or f"A {concept.category} for {concept.concept_name}",
            ARCHITECTURE=architecture,
            DATA_FLOW=data_flow,
            DECISION_POINTS=decision_points,
            AUDITABLE_OUTPUTS=auditable_outputs,
            EXPANDABILITY=expandability,
            EXAMPLE_USE_CASE=example,
            EXTERNAL_DEPENDENCIES=[],
            SOURCE_FILE=concept.source_file,
            EXTRACTION_CONFIDENCE=concept.confidence,
        )

    def _sanitize_name(self, name: str) -> str:
        """Sanitize concept name."""
        # Remove special chars, convert to snake_case
        name = re.sub(r"[^\w\s-]", "", name)
        name = re.sub(r"[-\s]+", "_", name)
        return name.lower()

    def _parse_architecture(self, content: str) -> dict:
        """Parse architecture components from content."""
        components = []

        # Look for component patterns
        component_pattern = r"(?:Component|component):\s*(.+?)(?:\n|$)"
        matches = re.finditer(component_pattern, content)

        for match in matches:
            comp_name = match.group(1).strip()
            components.append(
                {
                    "name": comp_name,
                    "role": f"Handles {comp_name}",
                    "inputs": ["input"],
                    "outputs": ["output"],
                }
            )

        if not components:
            # Generate generic component
            components.append(
                {
                    "name": "MainComponent",
                    "role": "Core processing logic",
                    "inputs": ["input"],
                    "outputs": ["output"],
                }
            )

        return {"components": components}

    def _parse_data_flow(self, content: str) -> str:
        """Parse data flow from content."""
        # Look for flow indicators
        if "→" in content:
            flow_match = re.search(r"(.+?→.+?)(?:\n|$)", content)
            if flow_match:
                return flow_match.group(1).strip()

        return "Input → Process → Output"

    def _parse_decision_points(self, content: str) -> list[str]:
        """Parse decision points from content."""
        points = []

        # Look for if/when/decision patterns
        decision_pattern = r"(?:if|when|decision):\s*(.+?)(?:\n|$)"
        matches = re.finditer(decision_pattern, content, re.IGNORECASE)

        for match in matches:
            points.append(match.group(1).strip())

        if not points:
            points.append("Process input and determine output")

        return points

    def _parse_auditable_outputs(self, content: str) -> list[str]:
        """Parse auditable outputs from content."""
        outputs = []

        # Look for output/log/audit patterns
        output_pattern = r"(?:output|log|audit):\s*(.+?)(?:\n|$)"
        matches = re.finditer(output_pattern, content, re.IGNORECASE)

        for match in matches:
            outputs.append(match.group(1).strip())

        if not outputs:
            outputs.append("Processing result with metadata")

        return outputs

    def _parse_expandability(self, content: str) -> list[str]:
        """Parse expandability notes from content."""
        return [
            "Can be extended with additional features",
            "Supports plugin architecture",
            "Configurable via environment variables",
        ]

    def _generate_example(self, concept: ExtractedConcept) -> str:
        """Generate example use case."""
        return f"Use {concept.concept_name} to {concept.description}"


class KnowledgeHarvester:
    """Main orchestrator for knowledge harvesting."""

    def __init__(self, root_dir: Path, output_dir: Path = Path("./harvested")):
        """
        Initialize the knowledge harvester.

        Args:
            root_dir: Root directory to scan
            output_dir: Where to save extracted concepts
        """
        self.root_dir = Path(root_dir).expanduser()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.scanner = FileScanner(self.root_dir)
        self.extractor = ConceptExtractor(aggressive=True)
        self.yaml_generator = YAMLGenerator()

    def harvest(self) -> dict:
        """
        Run the complete harvesting pipeline.

        Returns:
            Harvest results
        """
        print("🌾 L9 Knowledge Harvester")
        print(f"📁 Scanning: {self.root_dir}")

        # Scan files
        files = self.scanner.scan()
        print(f"📄 Found {len(files)} files")

        # Extract concepts
        all_concepts = []
        for file_path in files:
            print(f"  Processing: {file_path.name}...")
            concepts = self.extractor.extract_from_file(file_path)
            all_concepts.extend(concepts)
            print(f"    → Extracted {len(concepts)} concepts")

        print(f"\n✅ Total concepts extracted: {len(all_concepts)}")

        # Generate YAML specs
        yaml_specs = []
        for concept in all_concepts:
            yaml_spec = self.yaml_generator.generate(concept)
            yaml_specs.append((concept, yaml_spec))

        # Save to files
        concepts_dir = self.output_dir / "concepts"
        yaml_dir = self.output_dir / "yaml_specs"
        concepts_dir.mkdir(exist_ok=True)
        yaml_dir.mkdir(exist_ok=True)

        for concept, yaml_spec in yaml_specs:
            # Save concept metadata
            concept_file = concepts_dir / f"{concept.concept_id}.json"
            with open(concept_file, "w") as f:
                json.dump(asdict(concept), f, indent=2)

            # Save YAML spec
            yaml_file = yaml_dir / f"{yaml_spec.CONCEPT_NAME}.yaml"
            with open(yaml_file, "w") as f:
                yaml.dump(
                    asdict(yaml_spec), f, default_flow_style=False, sort_keys=False
                )

        # Generate summary
        summary = self._generate_summary(all_concepts, yaml_specs)
        summary_file = self.output_dir / "HARVEST_SUMMARY.md"
        summary_file.write_text(summary)

        print(f"\n📊 Summary saved to: {summary_file}")
        print(f"📁 Concepts saved to: {concepts_dir}")
        print(f"📁 YAML specs saved to: {yaml_dir}")

        return {
            "total_files": len(files),
            "total_concepts": len(all_concepts),
            "concepts_dir": str(concepts_dir),
            "yaml_dir": str(yaml_dir),
            "summary_file": str(summary_file),
        }

    def _generate_summary(
        self, concepts: list[ExtractedConcept], yaml_specs: list[tuple]
    ) -> str:
        """Generate harvest summary report."""
        summary = "# Knowledge Harvest Summary\n\n"
        summary += f"**Generated:** {datetime.now(timezone.utc).isoformat()}Z\n\n"
        summary += f"**Total Concepts Extracted:** {len(concepts)}\n\n"

        # Category breakdown
        summary += "## By Category\n\n"
        categories = {}
        for concept in concepts:
            categories[concept.category] = categories.get(concept.category, 0) + 1

        summary += "| Category | Count |\n"
        summary += "|----------|-------|\n"
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            summary += f"| {cat.title()} | {count} |\n"

        # Confidence breakdown
        summary += "\n## By Confidence\n\n"
        high_conf = sum(1 for c in concepts if c.confidence >= 0.7)
        med_conf = sum(1 for c in concepts if 0.4 <= c.confidence < 0.7)
        low_conf = sum(1 for c in concepts if c.confidence < 0.4)

        summary += f"- **High (≥0.7):** {high_conf}\n"
        summary += f"- **Medium (0.4-0.7):** {med_conf}\n"
        summary += f"- **Low (<0.4):** {low_conf}\n"

        # Top concepts
        summary += "\n## Top Concepts (by confidence)\n\n"
        top_concepts = sorted(concepts, key=lambda x: -x.confidence)[:10]

        summary += "| Concept | Category | Confidence | Source |\n"
        summary += "|---------|----------|------------|--------|\n"
        for concept in top_concepts:
            source = Path(concept.source_file).name
            summary += f"| {concept.concept_name[:40]} | {concept.category} | {concept.confidence:.2f} | {source} |\n"

        return summary


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="L9 Knowledge Harvester: Extract concepts from your files"
    )

    parser.add_argument(
        "--dir",
        type=Path,
        default=Path("~/Dropbox/Knowledge-Harvesting"),
        help="Directory to scan (default: ~/Dropbox/Knowledge-Harvesting)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./harvested"),
        help="Output directory for harvested concepts",
    )

    args = parser.parse_args()

    harvester = KnowledgeHarvester(root_dir=args.dir, output_dir=args.output)
    result = harvester.harvest()

    print("\n✨ Harvest complete!")
    print(f"📊 Check the summary: {result['summary_file']}")
    print("\n🎯 Next steps:")
    print("1. Review the HARVEST_SUMMARY.md")
    print("2. Use the QC dashboard to approve/reject concepts")
    print("3. Generate PLAN specs for approved concepts")


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-036",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "cli",
        "config",
        "current-work",
        "dataclass",
        "filesystem",
        "operations",
        "rest-api",
        "scanner",
    ],
    "keywords": [
        "concept",
        "extract",
        "extracted",
        "extractor",
        "generate",
        "generator",
        "harvest",
        "harvester",
    ],
    "business_value": "Provides l9 knowledge harvester components including ExtractedConcept, ConceptYAML, FileScanner",
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
