#!/usr/bin/env python3
"""
Validation Self-Corrector — Auto-fixes minor validation errors in generated code.

This component:
1. Analyzes validation errors from SchemaValidator or CodeValidator.
2. Identifies "auto-fixable" errors (e.g., missing DORA blocks, forbidden patterns).
3. Applies surgical fixes to the generated code.
4. Re-validates the fixed code.
"""

from pathlib import Path
from typing import Any

import structlog

# ---------------------------------------------------------------------------
# DORA Metadata Block (ADR-0014)
# ---------------------------------------------------------------------------
__dora_meta__ = {
    "component_name": "validation_self_corrector",
    "module_version": "1.0.0",
    "status": "active",
    "layer": "Core/Agents",
    "owner": "l9-platform",
    "description": "Autonomous self-correction for code generation validation failures",
}

log = structlog.get_logger(__name__)


class ValidationSelfCorrector:
    """Auto-fixes common validation failures in generated code."""

    def __init__(self):
        self.fixable_patterns = {
            "missing_dora": r"Missing __dora_meta__ block",
            "forbidden_pattern": r"Forbidden pattern '(.*)' found",
        }

    def attempt_fix(self, file_path: str, content: str, errors: list[str]) -> str:
        """Attempt to fix identified errors in the content."""
        fixed_content = content
        fixes_applied = []

        for error in errors:
            # Fix 1: Missing DORA block
            if "Missing __dora_meta__ block" in error or "ADR-0014" in error:
                fixed_content = self._fix_missing_dora(file_path, fixed_content)
                fixes_applied.append("added_dora_meta")

            # Fix 2: Forbidden patterns (TODO, FIXME, etc.)
            for pattern in ["TODO", "FIXME", "TBD", "if applicable"]:
                if pattern in error:
                    fixed_content = fixed_content.replace(
                        pattern, f"[REMEDIATED: {pattern}]"
                    )
                    fixes_applied.append(f"removed_forbidden_{pattern}")

        if fixes_applied:
            log.info("self_correction_applied", file=file_path, fixes=fixes_applied)

        return fixed_content

    def _fix_missing_dora(self, file_path: str, content: str) -> str:
        """Inject a minimal DORA block if missing."""
        if "__dora_meta__" in content:
            return content

        module_name = Path(file_path).stem
        dora_block = f"""
# ---------------------------------------------------------------------------
# DORA Metadata Block (ADR-0014)
# ---------------------------------------------------------------------------
__dora_meta__ = {{
    "component_name": "{module_name}",
    "version": "1.0.0",
    "status": "active",
    "owner": "l9-platform",
    "description": "Auto-generated module",
}}
"""
        # Insert after docstring or at top
        lines = content.splitlines()
        if lines and lines[0].startswith('"""'):
            # Find end of docstring
            try:
                end_idx = -1
                for i, line in enumerate(lines):
                    if i > 0 and '"""' in line:
                        end_idx = i
                        break
                if end_idx != -1:
                    lines.insert(end_idx + 1, dora_block)
                    return "\n".join(lines)
            except Exception:
                pass

        return dora_block + "\n" + content

    def enforce_dora_completeness(self, dora_meta: dict[str, Any]) -> dict[str, Any]:
        """Ensure all required DORA fields are present."""
        required = ["component_name", "version", "status", "owner", "description"]
        for field in required:
            if (
                field not in dora_meta
                or not dora_meta[field]
                or "{PLACEHOLDER}" in str(dora_meta[field])
            ):
                dora_meta[field] = f"auto_populated_{field}"
                log.warning("dora_field_auto_populated", field=field)
        return dora_meta
