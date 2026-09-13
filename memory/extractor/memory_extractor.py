"""
Memory Database Extractor

Extracts structured memory (JSON) for Supabase from markdown documents.
Output: Extracted Files/memory_db/*.json
"""


import json
import re
from pathlib import Path

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

    def extract(self, input_path: Path, output_root: Path) -> dict:
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

    def extract_memory_entries(self, content: str) -> list[dict]:
        """Extract memory entries from content."""
        entries = []

        # Extract explicit markers
        entries.extend(self.extract_lessons(content))
        entries.extend(self.extract_directives(content))
        entries.extend(self.extract_sops(content))

        return entries

    def extract_lessons(self, content: str) -> list[dict]:
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

    def extract_directives(self, content: str) -> list[dict]:
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

    def extract_sops(self, content: str) -> list[dict]:
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


# Runtime execution trace - updated automatically on every execution
