"""
Agent Configuration Extractor

Extracts preferences, SOPs, roles, signals from conversations.
Uses the recursive_extractor v3.2.0 schema (12 blocks).
Output: Extracted Files/agent_config/*.yaml
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Agent Config Extractor",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "agent_config_extractor",
    "type": "collector",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .base_extractor import BaseExtractor


class AgentConfigExtractor(BaseExtractor):
    """Extracts agent configuration (preferences, SOPs, roles)."""

    def extract(self, input_path: Path, output_root: Path) -> dict:
        """Extract agent configuration from input."""
        self.logger.info(f"AgentConfigExtractor: Processing {input_path.name}")

        content = input_path.read_text(encoding="utf-8", errors="ignore")
        mode = self.get_config("mode") or "full"

        # Extract configuration
        config = self.extract_config(content, mode)

        if not config or not any(config.values()):
            self.logger.warning("No configuration found")
            return {
                "success": False,
                "files_extracted": 0,
                "errors": ["No configuration found"],
            }

        # Create output directory
        output_dir = self.create_output_dir(output_root, "agent_config")
        output_file = output_dir / f"{input_path.stem}_config.yaml"

        # Write YAML output
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(
                config, f, default_flow_style=False, allow_unicode=True, sort_keys=False
            )

        self.logger.info(f"  ✅ Extracted configuration ({mode} mode)")

        return {
            "success": True,
            "files_extracted": 1,
            "output_path": str(output_file),
            "mode": mode,
            "blocks_extracted": list(config.keys()),
            "errors": [],
        }

    def extract_config(self, content: str, mode: str) -> dict:
        """Extract configuration based on mode."""
        config = {
            "schema_meta": {
                "version": "3.2.0",
                "extracted_at": datetime.now().isoformat(),
                "source_type": "conversation",
                "mode": mode,
                "extractor_confidence": 0.85,
            }
        }

        # Extract blocks
        config["user_preferences"] = self.extract_preferences(content)
        config["sops"] = self.extract_sops(content)
        config["signals"] = self.extract_signals(content)
        config["operating_mode"] = self.extract_operating_mode(content)

        if mode == "full":
            config["roles"] = self.extract_roles(content)
            config["structural_patterns"] = self.extract_patterns(content)
            config["known_issues"] = self.extract_issues(content)
            config["lessons"] = self.extract_lessons(content)
            config["conflicts"] = []
            config["dependencies"] = []
            config["integration"] = {
                "trigger_phrases": ["Add to memory", "ATM", "LESSON"],
                "system_prompt_block": True,
                "auto_apply": True,
            }

        return config

    def extract_preferences(self, content: str) -> list[dict]:
        """Extract user preferences."""
        preferences = []

        # Look for preference patterns
        pref_patterns = [
            (r"prefers?\s+(.+?)(?:\n|$)", "preference_verb"),
            (r"User preference:\s*(.+?)(?:\n|$)", "explicit_marker"),
        ]

        for pattern, _pattern_type in pref_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                pref_text = match.group(1).strip()
                preferences.append(
                    {
                        "id": f"pref_{len(preferences)}",
                        "pattern": pref_text[:100],
                        "requirement": "should",
                        "confidence": 0.7,
                    }
                )

        return preferences

    def extract_sops(self, content: str) -> list[dict]:
        """Extract Standard Operating Procedures."""
        sops = []

        # Explicit SOP markers
        for match in re.finditer(r"SOP:\s*(.+?)(?=\n\n|\nSOP:|\Z)", content, re.DOTALL):
            sop_text = match.group(1).strip()
            sops.append(
                {
                    "id": f"sop_{len(sops)}",
                    "who": "LLM",
                    "rule": sop_text,
                    "scope": "global",
                    "severity": "major",
                    "enforcement": "agent_logic",
                    "confidence": 0.9,
                }
            )

        # Always/Never patterns
        for match in re.finditer(
            r"(Always|Never)\s+(.+?)(?:\n|$)", content, re.IGNORECASE
        ):
            directive = match.group(0).strip()
            sops.append(
                {
                    "id": f"sop_{len(sops)}",
                    "who": "LLM",
                    "rule": directive,
                    "scope": "global",
                    "severity": "critical",
                    "enforcement": "system_prompt",
                    "confidence": 0.85,
                }
            )

        return sops

    def extract_signals(self, content: str) -> list[dict]:
        """Extract signal phrases."""
        signals = []

        signal_markers = ["LESSON:", "ATM:", "Add to memory"]

        for marker in signal_markers:
            pattern = re.escape(marker) + r"\s*(.+?)(?=\n\n|\n[A-Z]+:|\Z)"
            for match in re.finditer(pattern, content, re.DOTALL):
                signal_text = match.group(1).strip()
                signals.append(
                    {
                        "id": f"sig_{len(signals)}",
                        "type": marker.lower().replace(":", "").replace(" ", "_"),
                        "phrase": signal_text,
                        "extracted_value": signal_text[:200],
                        "confidence": 0.95,
                    }
                )

        return signals

    def extract_operating_mode(self, content: str) -> dict:
        """Extract operating mode information."""
        return {
            "reasoning": "both",
            "confirmation_policy": "on_change",
            "persona": ["extractor"],
            "delegation": "flexible",
        }

    def extract_roles(self, content: str) -> list[dict]:
        """Extract role definitions."""
        roles = []

        for match in re.finditer(r"Role:\s*(.+?)(?=\n|$)", content, re.IGNORECASE):
            role_name = match.group(1).strip()
            roles.append(
                {
                    "id": f"role_{len(roles)}",
                    "role": role_name,
                    "owned_by": "LLM",
                    "behavior": "To be defined",
                    "restricted": False,
                }
            )

        return roles

    def extract_patterns(self, content: str) -> list[dict]:
        """Extract structural patterns."""
        return []

    def extract_issues(self, content: str) -> list[dict]:
        """Extract known issues."""
        return []

    def extract_lessons(self, content: str) -> list[dict]:
        """Extract lessons."""
        lessons = []

        for match in re.finditer(
            r"LESSON:\s*(.+?)(?=\n\n|\nLESSON:|\Z)", content, re.DOTALL
        ):
            lesson_text = match.group(1).strip()
            lessons.append(
                {
                    "id": f"lesson_{len(lessons)}",
                    "text": lesson_text,
                    "applies_to": "prompting",
                    "category": "do_this",
                    "confidence": 0.9,
                }
            )

        return lessons


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-058",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "collector",
        "config",
        "filesystem",
        "learning",
        "memory-substrate",
        "rest-api",
    ],
    "keywords": [
        "agent",
        "extract",
        "extractor",
        "issues",
        "lessons",
        "mode",
        "operating",
        "patterns",
    ],
    "business_value": "Implements AgentConfigExtractor for agent config extractor functionality",
    "last_modified": "2026-01-07T13:35:57Z",
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
