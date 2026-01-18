"""
Code File Extractor

Extracts Python, JavaScript, YAML, and other code files from chat logs.
Output goes directly to Extracted Files/{filepath_from_chat}
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Code Extractor",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "code_extractor",
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
from pathlib import Path
from typing import Dict, List, Tuple
from .base_extractor import BaseExtractor


class CodeExtractor(BaseExtractor):
    """Extracts code files from chat logs."""

    PATTERNS = [
        # Pattern 1: Comment-based path headers
        # # api/mcp/mcp_auth.py
        (
            r"^#\s+([\w/\-\.]+\.(?:py|js|ts|yaml|yml|json|jsx|tsx))\s*$",
            "comment_header",
        ),
        # Pattern 2: Numbered file lists
        # 1) mcp_auth.py
        (r"^\d+\)\s+([\w/\-\.]+\.(?:py|js|ts|yaml|yml|json|jsx|tsx))", "numbered_list"),
        # Pattern 3: Emoji markers
        # 🔥 agent.py – Description
        (
            r"^[🔥📁📄✨💡]\s+([\w/\-\.]+\.(?:py|js|ts|yaml|yml|json|jsx|tsx))",
            "emoji_marker",
        ),
        # Pattern 4: Triple backticks with filename
        # ```python:path/to/file.py
        (
            r"```(?:python|javascript|typescript|yaml|json)?:([\w/\-\.]+\.(?:py|js|ts|yaml|yml|json|jsx|tsx))",
            "code_block_with_path",
        ),
    ]

    def extract(self, input_path: Path, output_root: Path) -> Dict:
        """Extract code files from input."""
        self.logger.info(f"CodeExtractor: Processing {input_path.name}")

        content = input_path.read_text(encoding="utf-8", errors="ignore")
        files_extracted = {}
        errors = []

        # Find all code blocks
        code_blocks = self.find_code_blocks(content)

        self.logger.info(f"Found {len(code_blocks)} potential code blocks")

        for file_path, code_content in code_blocks:
            try:
                # Create full output path: Extracted Files/{filepath}
                output_file = output_root / file_path
                output_file.parent.mkdir(parents=True, exist_ok=True)

                # Write file
                output_file.write_text(code_content, encoding="utf-8")
                files_extracted[str(file_path)] = str(output_file)

                self.logger.debug(f"  ✅ Extracted: {file_path}")

            except Exception as e:
                error_msg = f"Failed to extract {file_path}: {e}"
                self.logger.error(f"  ❌ {error_msg}")
                errors.append(error_msg)

        return {
            "success": len(files_extracted) > 0,
            "files_extracted": len(files_extracted),
            "output_path": str(output_root),
            "files": files_extracted,
            "errors": errors,
        }

    def find_code_blocks(self, content: str) -> List[Tuple[str, str]]:
        """
        Find all code blocks with file paths in content.

        Returns:
            List of (file_path, code_content) tuples
        """
        code_blocks = []
        lines = content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check all patterns
            for pattern, pattern_type in self.PATTERNS:
                match = re.match(pattern, line.strip())
                if match:
                    file_path = match.group(1)

                    # Extract code content
                    code_start = i + 1
                    code_content = self.extract_code_content(
                        lines, code_start, pattern_type
                    )

                    if code_content:
                        code_blocks.append((file_path, code_content))
                        self.logger.debug(f"  Found {pattern_type}: {file_path}")

                    break

            i += 1

        return code_blocks

    def extract_code_content(
        self, lines: List[str], start_idx: int, pattern_type: str
    ) -> str:
        """Extract code content starting from start_idx."""
        code_lines = []
        i = start_idx
        in_code_block = False

        while i < len(lines):
            line = lines[i]

            # Check for code block markers
            if line.strip().startswith("```"):
                if not in_code_block:
                    in_code_block = True
                    i += 1
                    continue
                else:
                    # End of code block
                    break

            # If we're in a code block, add the line
            if in_code_block or (i == start_idx and not line.strip().startswith("#")):
                code_lines.append(line)

            # Stop conditions
            if not in_code_block and (
                line.strip() == ""
                or line.strip().startswith("#")
                and not line.strip().startswith("# ")
                or any(re.match(p[0], line.strip()) for p in self.PATTERNS)
            ):
                if len(code_lines) > 3:  # Minimum 3 lines for valid code
                    break

            i += 1

            # Safety: max 1000 lines per file
            if len(code_lines) > 1000:
                break

        return "\n".join(code_lines).strip()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-055",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "auth", "collector", "debugging", "filesystem", "learning", "memory-substrate"],
    "keywords": ["blocks", "extract", "extractor", "files", "find"],
    "business_value": "Implements CodeExtractor for code extractor functionality",
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
