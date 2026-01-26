#!/usr/bin/env python3
"""
L9 Spec Generator (L → CA Pipeline)
====================================
Converts text concepts into PLAN_Vn specs that CA (Coding Agent) can execute in Cursor.

Flow:
1. L (Architect) writes concept
2. This tool generates PLAN_Vn YAML spec
3. CA receives spec in Cursor
4. CA writes code governed by DevLayer
5. DevLayer validates, generates diff, creates report

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 Spec Generator",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-20T18:47:58Z",
    "updated_at": "2026-01-20T23:43:16Z",
    "layer": "operations",
    "domain": "current_work",
    "module_name": "l9_spec_generator",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from dataclasses import asdict, dataclass
from datetime import datetime
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
    external_dependencies: list[str] | None = None


@dataclass
class PlanSpec:
    """PLAN_Vn specification for CA."""

    plan_id: str
    type: str
    project_id: str
    task_id: str
    task_description: str
    acceptance_criteria: list[str]
    definition_of_done: list[str]
    agent_rules: dict
    context: dict
    created_at: str
    created_by: str


class L9SpecGenerator:
    """Generates PLAN_Vn specs for CA from concepts."""

    def __init__(self, output_dir: Path = Path("./specs")):
        """
        Initialize the spec generator.

        Args:
            output_dir: Where to output generated specs
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

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
            external_dependencies=data.get("EXTERNAL_DEPENDENCIES", []),
        )

    def generate_plan_spec(
        self, concept: ConceptSpec, project_id: str = "proj_001"
    ) -> PlanSpec:
        """
        Generate a PLAN_Vn spec from a concept.

        Args:
            concept: Parsed concept
            project_id: Project identifier

        Returns:
            PLAN_Vn specification
        """
        # Generate IDs
        task_id = f"task_{concept.name}_{concept.version.replace('.', '_')}"
        plan_id = f"plan_{project_id}_{task_id}_v1"

        # Build task description
        task_description = self._build_task_description(concept)

        # Build acceptance criteria
        acceptance_criteria = self._build_acceptance_criteria(concept)

        # Build definition of done
        definition_of_done = self._build_definition_of_done(concept)

        # Build agent rules
        agent_rules = self._build_agent_rules(concept)

        # Build context
        context = self._build_context(concept)

        # Create PLAN spec
        return PlanSpec(
            plan_id=plan_id,
            type="implementation",
            project_id=project_id,
            task_id=task_id,
            task_description=task_description,
            acceptance_criteria=acceptance_criteria,
            definition_of_done=definition_of_done,
            agent_rules=agent_rules,
            context=context,
            created_at=datetime.utcnow().isoformat() + "Z",
            created_by="L_architect",
        )


    def _build_task_description(self, concept: ConceptSpec) -> str:
        """Build task description from concept."""
        desc = f"{concept.one_sentence}\n\n"
        desc += "## Architecture\n\n"

        if "components" in concept.architecture:
            for comp in concept.architecture["components"]:
                desc += f"- **{comp['name']}**: {comp['role']}\n"
                desc += f"  - Inputs: {', '.join(comp['inputs'])}\n"
                desc += f"  - Outputs: {', '.join(comp['outputs'])}\n"

        desc += "\n## Data Flow\n\n"
        desc += concept.data_flow

        desc += "\n\n## Example Use Case\n\n"
        desc += concept.example_use_case

        return desc

    def _build_acceptance_criteria(self, concept: ConceptSpec) -> list[str]:
        """Build acceptance criteria from concept."""
        criteria = []

        # From architecture components
        if "components" in concept.architecture:
            for comp in concept.architecture["components"]:
                criteria.append(
                    f"{comp['name']} implemented with inputs: {', '.join(comp['inputs'])}"
                )

        # From decision points
        for dp in concept.decision_points:
            criteria.append(f"Decision logic: {dp}")

        # From auditable outputs
        for ao in concept.auditable_outputs:
            criteria.append(f"Auditable output: {ao}")

        # Standard criteria
        criteria.extend(
            [
                "All functions have type hints and docstrings",
                "Test coverage >= 90%",
                "No linting issues (mypy, black, flake8)",
                "All decision points logged with rationale",
            ]
        )

        return criteria

    def _build_definition_of_done(self, concept: ConceptSpec) -> list[str]:
        """Build definition of done."""
        return [
            "All acceptance criteria verified",
            "Tests pass in CI/CD pipeline",
            "Code review: 0 critical or high severity issues",
            f"Git commit with message: feat({concept.name}): {concept.one_sentence}",
            "DevLayer governance checks pass",
            "Diff and report generated",
            "Ready for merge (pending L approval)",
        ]

    def _build_agent_rules(self, concept: ConceptSpec) -> dict:
        """Build agent rules (safety bounds)."""
        # Estimate complexity
        num_components = len(concept.architecture.get("components", []))
        max_files = max(3, num_components * 2)  # 2 files per component (impl + test)
        max_lines = max(150, num_components * 100)  # 100 lines per component

        return {
            "max_files_allowed": max_files,
            "max_lines_allowed": max_lines,
            "max_time_allowed_seconds": 1800,  # 30 minutes
            "allowed_directories": [
                f"core/{concept.name}/",
                f"tests/{concept.name}/",
                f"docs/{concept.name}/",
            ],
            "forbidden_directories": [
                "config/secrets/",
                ".env",
                ".git/",
                "infrastructure/",
            ],
            "must_include": [
                "type_hints",
                "docstrings",
                "unit_tests",
                "git_commit",
                "audit_logging",
            ],
            "test_coverage_minimum": 0.90,
            "linting_profile": "strict",
        }

    def _build_context(self, concept: ConceptSpec) -> dict:
        """Build context information."""
        return {
            "concept_version": concept.version,
            "dependencies": concept.external_dependencies or [],
            "expandability_notes": concept.expandability,
            "risk_notes": "Follow DevLayer governance. All changes must pass constraint validation.",
        }

    def generate_cursor_prompt(self, plan: PlanSpec, concept: ConceptSpec) -> str:
        """
        Generate the complete Cursor prompt for CA.

        Args:
            plan: PLAN_Vn spec
            concept: Original concept

        Returns:
            Complete Cursor prompt
        """
        prompt = f"""# L9 CODING TASK — {plan.task_id}

## ROLE
You are CA (Coding Agent), the implementation specialist in the L9 system.
You receive PLAN specs from L (Architect) and write production-ready code.

## GOVERNANCE
You are governed by the DevLayer. All your code changes will be:
1. Validated against constraints
2. Analyzed for diffs
3. Documented in reports
4. Committed with proper messages

## YOUR TASK

### Task ID: {plan.task_id}
### Plan ID: {plan.plan_id}
### Type: {plan.type}

### Description
{plan.task_description}

### Acceptance Criteria
"""
        for i, criterion in enumerate(plan.acceptance_criteria, 1):
            prompt += f"{i}. {criterion}\n"

        prompt += "\n### Definition of Done\n"
        for i, item in enumerate(plan.definition_of_done, 1):
            prompt += f"{i}. {item}\n"

        prompt += f"""
### Agent Rules (Safety Bounds)

**File Limits:**
- Max files: {plan.agent_rules["max_files_allowed"]}
- Max lines: {plan.agent_rules["max_lines_allowed"]}
- Max time: {plan.agent_rules["max_time_allowed_seconds"]}s

**Allowed Directories:**
"""
        for dir in plan.agent_rules["allowed_directories"]:
            prompt += f"- {dir}\n"

        prompt += "\n**Forbidden Directories:**\n"
        for dir in plan.agent_rules["forbidden_directories"]:
            prompt += f"- {dir}\n"

        prompt += "\n**Must Include:**\n"
        for item in plan.agent_rules["must_include"]:
            prompt += f"- {item}\n"

        prompt += f"""
**Quality Gates:**
- Test coverage: >= {plan.agent_rules["test_coverage_minimum"] * 100}%
- Linting: {plan.agent_rules["linting_profile"]}

### Context
{yaml.dump(plan.context, default_flow_style=False)}

## IMPLEMENTATION INSTRUCTIONS

### Step 1: Plan Your Implementation
Review the architecture and data flow. Identify the files you need to create.

### Step 2: Write Code
Implement each component according to the spec. Follow these patterns:

**For each component:**
```python
from typing import Dict, List
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

class {{ComponentName}}Input(BaseModel):
    \"\"\"Input schema for {{ComponentName}}.\"\"\"
    # Define inputs from spec
    pass

class {{ComponentName}}Output(BaseModel):
    \"\"\"Output schema for {{ComponentName}}.\"\"\"
    # Define outputs from spec
    pass

async def {{component_name}}(input: {{ComponentName}}Input) -> {{ComponentName}}Output:
    \"\"\"
    {{Component description from spec}}.

    Args:
        input: {{Input description}}

    Returns:
        {{Output description}}
    \"\"\"
    logger.info("{{component_name}}_called", input=input.dict())

    # Implementation here

    logger.info("{{component_name}}_completed", output=output.dict())
    return output
```

### Step 3: Write Tests
For each component, write comprehensive tests:

```python
import pytest
from {{module}}.{{component}} import {{component_name}}

@pytest.mark.asyncio
async def test_{{component_name}}_success():
    \"\"\"Test {{component_name}} with valid input.\"\"\"
    input = {{ComponentName}}Input(...)
    output = await {{component_name}}(input)
    assert output.{{field}} == expected_value

@pytest.mark.asyncio
async def test_{{component_name}}_edge_case():
    \"\"\"Test {{component_name}} with edge case.\"\"\"
    # Test edge cases
    pass
```

### Step 4: Verify
Run these commands:
```bash
# Type checking
mypy {concept.name}/

# Linting
black {concept.name}/
flake8 {concept.name}/

# Tests
pytest tests/{concept.name}/ -v --cov={concept.name} --cov-report=term-missing

# Should show >= 90% coverage
```

### Step 5: Commit
```bash
git add {concept.name}/ tests/{concept.name}/
git commit -m "feat({concept.name}): {concept.one_sentence}"
```

## DEVLAYER GOVERNANCE

After you commit, the DevLayer will:
1. Validate your changes against constraints
2. Generate a diff report
3. Create a change report
4. Present to L for approval

**Your job is to write clean, well-tested code that passes governance.**

## BEGIN IMPLEMENTATION

Start by creating the directory structure and implementing the first component.
"""

        return prompt

    def generate_from_file(
        self, concept_file: Path, project_id: str = "proj_001"
    ) -> dict:
        """
        Complete generation pipeline from concept file.

        Args:
            concept_file: Path to concept file
            project_id: Project identifier

        Returns:
            Generation result with file paths
        """
        print("🚀 L9 Spec Generator (L → CA Pipeline)")
        print(f"📄 Reading concept: {concept_file}")

        # Parse concept
        concept = self.parse_concept(concept_file)
        print(f"✅ Parsed concept: {concept.name} v{concept.version}")

        # Generate PLAN spec
        plan = self.generate_plan_spec(concept, project_id)
        print(f"✅ Generated PLAN spec: {plan.plan_id}")

        # Save PLAN spec
        plan_file = self.output_dir / f"{plan.plan_id}.yaml"
        with open(plan_file, "w") as f:
            yaml.dump(asdict(plan), f, default_flow_style=False, sort_keys=False)
        print(f"📝 Saved PLAN spec: {plan_file}")

        # Generate Cursor prompt
        cursor_prompt = self.generate_cursor_prompt(plan, concept)
        prompt_file = self.output_dir / f"{plan.plan_id}_cursor_prompt.md"
        prompt_file.write_text(cursor_prompt)
        print(f"📝 Saved Cursor prompt: {prompt_file}")

        return {
            "plan_file": str(plan_file),
            "prompt_file": str(prompt_file),
            "plan_id": plan.plan_id,
            "task_id": plan.task_id,
        }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="L9 Spec Generator: Convert concepts to CA-executable PLAN specs"
    )

    parser.add_argument("concept_file", type=Path, help="Path to concept file")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./specs"),
        help="Output directory for specs",
    )
    parser.add_argument(
        "--project-id", type=str, default="proj_001", help="Project identifier"
    )

    args = parser.parse_args()

    generator = L9SpecGenerator(output_dir=args.output)
    result = generator.generate_from_file(args.concept_file, args.project_id)

    print("\n✨ Generation complete!")
    print(f"📋 PLAN spec: {result['plan_file']}")
    print(f"📄 Cursor prompt: {result['prompt_file']}")
    print("\n🎯 Next steps:")
    print(f"1. Review the PLAN spec: {result['plan_file']}")
    print(f"2. Open Cursor and load: {result['prompt_file']}")
    print("3. CA will implement the code")
    print("4. DevLayer will validate and generate reports")


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-037",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "auth",
        "cli",
        "config",
        "current-work",
        "dataclass",
        "filesystem",
        "linting",
        "logging",
        "messaging",
    ],
    "keywords": [
        "concept",
        "cursor",
        "generate",
        "generator",
        "parse",
        "plan",
        "prompt",
        "spec",
    ],
    "business_value": "Provides l9 spec generator components including ConceptSpec, PlanSpec, L9SpecGenerator",
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
