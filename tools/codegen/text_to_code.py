#!/usr/bin/env python3
"""
L9 Text-to-Code Generator
==========================
Unified system that converts text concepts into production Python code with governance.

Flow:
1. Read concept text/markdown
2. Generate Python code using superprompt
3. Extract governance artifacts (constraints, protocols)
4. Package everything together

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 Text To Code",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-20T18:08:19Z",
    "updated_at": "2026-01-20T23:43:16Z",
    "layer": "operations",
    "domain": "current_work",
    "module_name": "l9_text_to_code",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Anthropic API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class ConceptSpec:
    """Parsed concept specification."""

    name: str
    version: str
    one_sentence: str
    architecture: dict
    data_flow: str
    decision_points: list[str]
    auditable_outputs: list[str]
    expandability: list[str]
    example_use_case: str


@dataclass
class GenerationResult:
    """Result of code generation."""

    module_path: Path
    files_generated: list[str]
    governance_artifacts: list[str]
    success: bool
    errors: list[str]


class L9TextToCode:
    """Main text-to-code generator."""

    def __init__(self, output_dir: Path = Path("./generated")):
        """
        Initialize the generator.

        Args:
            output_dir: Where to output generated modules
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Find superprompt
        self.superprompt_path = self._find_superprompt()

        # Find compiler
        self.compiler_path = self._find_compiler()

    def _find_superprompt(self) -> Path | None:
        """Find the superprompt file."""
        search_paths = [
            Path(__file__).parent / "superprompt" / "labs_superprompt_v1.md",
            Path("./superprompt/labs_superprompt_v1.md"),
            Path("./labs_superprompt_v1.md"),
        ]

        for path in search_paths:
            if path.exists():
                return path

        return None

    def _find_compiler(self) -> Path | None:
        """Find the compiler script."""
        search_paths = [
            Path(__file__).parent / "compiler" / "l9_doc_compiler.py",
            Path("./compiler/l9_doc_compiler.py"),
            Path("./l9_doc_compiler.py"),
        ]

        for path in search_paths:
            if path.exists():
                return path

        return None

    def parse_concept(self, concept_file: Path) -> ConceptSpec:
        """
        Parse a concept file (YAML or Markdown).

        Args:
            concept_file: Path to concept file

        Returns:
            Parsed concept specification
        """
        content = concept_file.read_text()

        # Try to parse as YAML
        if concept_file.suffix in [".yaml", ".yml"]:
            data = yaml.safe_load(content)
        else:
            # Extract YAML from markdown code blocks
            import re

            yaml_match = re.search(r"```yaml\n(.*?)\n```", content, re.DOTALL)
            if yaml_match:
                data = yaml.safe_load(yaml_match.group(1))
            else:
                raise ValueError("Could not find YAML concept in file")

        # Parse into ConceptSpec
        return ConceptSpec(
            name=data.get("CONCEPT_NAME", "unnamed"),
            version=data.get("VERSION", "0.1.0"),
            one_sentence=data.get("ONE_SENTENCE", ""),
            architecture=data.get("ARCHITECTURE", {}),
            data_flow=data.get("DATA_FLOW", ""),
            decision_points=data.get("DECISION_POINTS", []),
            auditable_outputs=data.get("AUDITABLE_OUTPUTS", []),
            expandability=data.get("EXPANDABILITY", []),
            example_use_case=data.get("EXAMPLE_USE_CASE", ""),
        )

    def generate_code(self, concept: ConceptSpec) -> GenerationResult:
        """
        Generate Python code from concept using LLM.

        Args:
            concept: Parsed concept specification

        Returns:
            Generation result
        """
        module_dir = self.output_dir / concept.name
        module_dir.mkdir(parents=True, exist_ok=True)

        # Create the generation prompt
        prompt = self._build_generation_prompt(concept)

        # Save prompt for reference
        (module_dir / "generation_prompt.txt").write_text(prompt)

        print(f"📝 Generation prompt saved to: {module_dir}/generation_prompt.txt")
        print("⚠️  Manual step required:")
        print("   1. Copy the prompt to Claude/Cursor")
        print(f"   2. Save generated files to: {module_dir}/")
        print(f"   3. Run: python {sys.argv[0]} compile {module_dir}")

        return GenerationResult(
            module_path=module_dir,
            files_generated=[],
            governance_artifacts=[],
            success=True,
            errors=[],
        )

    def _build_generation_prompt(self, concept: ConceptSpec) -> str:
        """Build the complete generation prompt."""

        # Load superprompt if available
        superprompt_content = ""
        if self.superprompt_path and self.superprompt_path.exists():
            superprompt_content = self.superprompt_path.read_text()

        # Build prompt
        return f"""# CONCEPT SPECIFICATION

```yaml
CONCEPT_NAME: "{concept.name}"
VERSION: "{concept.version}"
ONE_SENTENCE: "{concept.one_sentence}"

ARCHITECTURE:
{yaml.dump(concept.architecture, indent=2)}

DATA_FLOW: |
{concept.data_flow}

DECISION_POINTS:
{yaml.dump(concept.decision_points, indent=2)}

AUDITABLE_OUTPUTS:
{yaml.dump(concept.auditable_outputs, indent=2)}

EXPANDABILITY:
{yaml.dump(concept.expandability, indent=2)}

EXAMPLE_USE_CASE: "{concept.example_use_case}"
```

---

{superprompt_content}

---

# INSTRUCTION

Generate a complete, production-ready Python module for "{concept.name}".

Follow the superprompt rules exactly:
- All code must be async/await
- All decisions must be logged
- All inputs/outputs must use Pydantic models
- Include complete test suite
- Include README.md and requirements.txt
- No TODO comments - complete implementation only

Output all files with their full paths and complete code.
"""


    def compile_governance(self, module_dir: Path) -> list[str]:
        """
        Extract governance artifacts from generated code.

        Args:
            module_dir: Path to generated module

        Returns:
            List of generated governance files
        """
        if not self.compiler_path:
            print("⚠️  Compiler not found, skipping governance extraction")
            return []

        governance_dir = module_dir / "governance"
        governance_dir.mkdir(exist_ok=True)

        # Run compiler on the module directory
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(self.compiler_path),
                    str(module_dir),
                    str(governance_dir),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # List generated files
                governance_files = list(governance_dir.rglob("*.yaml"))
                return [str(f.relative_to(module_dir)) for f in governance_files]
            print(f"⚠️  Compiler error: {result.stderr}")
            return []

        except Exception as e:
            print(f"⚠️  Compilation failed: {e}")
            return []

    def generate_from_file(self, concept_file: Path) -> GenerationResult:
        """
        Complete generation pipeline from concept file.

        Args:
            concept_file: Path to concept file

        Returns:
            Generation result
        """
        print("🚀 L9 Text-to-Code Generator")
        print(f"📄 Reading concept: {concept_file}")

        # Parse concept
        concept = self.parse_concept(concept_file)
        print(f"✅ Parsed concept: {concept.name} v{concept.version}")

        # Generate code
        return self.generate_code(concept)



def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="L9 Text-to-Code Generator: Convert concepts to production Python"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate code from concept")
    gen_parser.add_argument("concept_file", type=Path, help="Path to concept file")
    gen_parser.add_argument(
        "--output", type=Path, default=Path("./generated"), help="Output directory"
    )

    # Compile command
    compile_parser = subparsers.add_parser(
        "compile", help="Extract governance from module"
    )
    compile_parser.add_argument(
        "module_dir", type=Path, help="Path to generated module"
    )

    args = parser.parse_args()

    if args.command == "generate":
        generator = L9TextToCode(output_dir=args.output)
        result = generator.generate_from_file(args.concept_file)

        print("\n✨ Generation complete!")
        print(f"📁 Module directory: {result.module_path}")

    elif args.command == "compile":
        generator = L9TextToCode()
        artifacts = generator.compile_governance(args.module_dir)

        print("\n✨ Compilation complete!")
        print(f"📋 Governance artifacts: {len(artifacts)}")
        for artifact in artifacts:
            print(f"   - {artifact}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-033",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "auth",
        "cli",
        "config",
        "current-work",
        "dataclass",
        "filesystem",
        "operations",
        "serialization",
        "subprocess",
        "testing",
    ],
    "keywords": [
        "compile",
        "concept",
        "generate",
        "generation",
        "governance",
        "parse",
        "spec",
    ],
    "business_value": "Provides l9 text to code components including ConceptSpec, GenerationResult, L9TextToCode",
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
