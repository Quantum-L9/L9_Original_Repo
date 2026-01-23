"""
Memory Database Extractor

Extracts structured memory (JSON) for Supabase from markdown documents.
Output: Extracted Files/memory_db/*.json
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Memory Extractor",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "memory_extractor",
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
import json
from pathlib import Path
from typing import Dict, List
from .base_extractor import BaseExtractor


class MemoryExtractor(BaseExtractor):
    """Extracts structured memory for Supabase."""

    MEMORY_TYPES = [
        "reasoning_block",
        "directive",
        "upgrade_log",
        "context_snapshot",
        "task_memory",
        "convo_memory",
        "agent_registry",
        "experimental_memory",
        "tool_registry",
        "project_glossary",
        "security_directive",
        "file_memory",
        "memory_index",
        "agent_plan",
    ]

    def extract(self, input_path: Path, output_root: Path) -> Dict:
        """Extract memory entries from input."""
        self.logger.info(f"MemoryExtractor: Processing {input_path.name}")

        content = input_path.read_text(encoding="utf-8", errors="ignore")

        # Extract memory entries
        memory_entries = self.extract_memory_entries(content)

        if not memory_entries:
            self.logger.warning("No memory entries found")
            return {
                "success": False,
                "files_extracted": 0,
                "errors": ["No memory entries found"],
            }

        # Create output directory
        output_dir = self.create_output_dir(output_root, "memory_db")
        output_file = output_dir / f"{input_path.stem}_memory.json"

        # Write JSON output
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(memory_entries, f, indent=2, ensure_ascii=False)

        self.logger.info(f"  ✅ Extracted {len(memory_entries)} memory entries")

        return {
            "success": True,
            "files_extracted": 1,
            "output_path": str(output_file),
            "entries_count": len(memory_entries),
            "errors": [],
        }

    def extract_memory_entries(self, content: str) -> List[Dict]:
        """Extract memory entries from content."""
        entries = []

        # Extract explicit markers
        entries.extend(self.extract_lessons(content))
        entries.extend(self.extract_directives(content))
        entries.extend(self.extract_sops(content))

        return entries

    def extract_lessons(self, content: str) -> List[Dict]:
        """Extract LESSON: markers."""
        lessons = []
        pattern = r"LESSON:\s*(.+?)(?=\n\n|\nLESSON:|\Z)"

        for match in re.finditer(pattern, content, re.DOTALL):
            lesson_text = match.group(1).strip()
            lessons.append(
                {
                    "type": "lesson",
                    "text": lesson_text,
                    "tags": ["extracted"],
                    "confidence": 0.9,
                }
            )

        return lessons

    def extract_directives(self, content: str) -> List[Dict]:
        """Extract Directive: markers."""
        directives = []
        pattern = r"Directive:\s*(.+?)(?=\n(?:Scope|Tags|$))"

        for match in re.finditer(pattern, content, re.MULTILINE):
            directive_text = match.group(1).strip()

            # Try to extract scope
            scope_match = re.search(
                r"Scope:\s*(\w+)", content[match.end() : match.end() + 100]
            )
            scope = scope_match.group(1) if scope_match else "global"

            directives.append(
                {
                    "type": "directive",
                    "directive": directive_text,
                    "scope": scope,
                    "tags": ["extracted"],
                    "enforced_by": "L",
                }
            )

        return directives

    def extract_sops(self, content: str) -> List[Dict]:
        """Extract SOP: markers."""
        sops = []
        pattern = r"SOP:\s*(.+?)(?=\n\n|\nSOP:|\Z)"

        for match in re.finditer(pattern, content, re.DOTALL):
            sop_text = match.group(1).strip()
            sops.append(
                {
                    "type": "directive",
                    "directive": sop_text,
                    "scope": "global",
                    "tags": ["sop", "extracted"],
                }
            )

        return sops


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-054",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "collector",
        "filesystem",
        "learning",
        "memory-substrate",
        "serialization",
    ],
    "keywords": [
        "directives",
        "entries",
        "extract",
        "extractor",
        "json",
        "lessons",
        "memory",
        "sops",
    ],
    "business_value": "Implements MemoryExtractor for memory extractor functionality",
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
