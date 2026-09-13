
# codegen/compiler/schemas.py
"""
Schema validation for transcript compiler outputs.

Validates the structure of generated YAML artifacts:
- decisions.yaml
- ial_candidates.yaml
- typed_invariants.yaml
- work_packets.yaml
"""

from typing import Any

# Expected schema structure for each artifact type
ARTIFACT_SCHEMAS = {
    "decisions.yaml": {"decisions": list},
    "ial_candidates.yaml": {"ial_candidates": list},
    "typed_invariants.yaml": {"typed_invariants": list},
    "work_packets.yaml": {"work_packets": list},
}


def validate_schema(artifact_name: str, artifact: dict[str, Any]) -> None:
    """
    Validate artifact structure against expected schema.

    Args:
        artifact_name: Name of the artifact (e.g., "decisions.yaml")
        artifact: The artifact dictionary to validate

    Raises:
        ValueError: If artifact structure is invalid
    """
    if not isinstance(artifact, dict):
        raise ValueError(
            f"{artifact_name}: Expected dict, got {type(artifact).__name__}"
        )

    expected = ARTIFACT_SCHEMAS.get(artifact_name)
    if expected is None:
        # Unknown artifact type - allow it
        return

    for key, expected_type in expected.items():
        if key not in artifact:
            raise ValueError(f"{artifact_name}: Missing required key '{key}'")
        if not isinstance(artifact[key], expected_type):
            raise ValueError(
                f"{artifact_name}: Key '{key}' expected {expected_type.__name__}, "
                f"got {type(artifact[key]).__name__}"
            )


# Runtime execution trace - updated automatically on every execution
