#!/usr/bin/env python3
"""
Gemini Auto-Editor for L9 PR Review
Fetches Gemini suggestions and applies them automatically
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Gemini Auto Editor",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-24T17:18:54Z",
    "updated_at": "2026-01-24T17:18:34Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "gemini_auto_editor",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Neo4j", "PostgreSQL", "Redis"],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import os
import sys
import json
import requests
import subprocess
from pathlib import Path
from typing import Dict, List, Any

PROTECTED_FILES = {
    "api/websocket_orchestrator.py",
    "docker-compose.yml",
    "core/kernel_loader.py",
    "memory/substrate_service.py",
    "core/schemas/packet_envelope.py",
}


class GeminiAutoEditor:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

    def is_protected_file(self, filepath: str) -> bool:
        """Check if file is protected"""
        return (
            any(pf in filepath for pf in PROTECTED_FILES)
            or "private/kernels/" in filepath
        )

    def get_pr_diff(self) -> str:
        """Fetch PR diff using git"""
        base_sha = os.getenv("BASE_SHA")
        head_sha = os.getenv("HEAD_SHA")

        cmd = f"git diff {base_sha}...{head_sha}"
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        return result.stdout

    def get_changed_files(self) -> List[str]:
        """Get list of changed files"""
        base_sha = os.getenv("BASE_SHA")
        head_sha = os.getenv("HEAD_SHA")

        cmd = f"git diff --name-only {base_sha}...{head_sha}"
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        return [f.strip() for f in result.stdout.split("\n") if f.strip()]

    def call_gemini_api(self, diff: str, files: List[str]) -> Dict[str, Any]:
        """Call Gemini API for code improvements"""

        prompt = f"""You are reviewing a pull request for the L9 AI agent system.

**Your Task**: Analyze the diff and suggest concrete code improvements.

**L9 Context**:
- PacketEnvelope protocol for inter-component messaging
- Memory substrates: PostgreSQL, Neo4j, Redis (access via MemorySubstrateService only)
- Governance layer enforces tool usage policies
- Kernel system contains immutable core logic

**Protected Files** (DO NOT suggest changes):
{", ".join(PROTECTED_FILES)}

**Changes**:
```diff
{diff[:15000]}
```

**Output Format** (JSON only):
{{
  "improvements": [
    {{
      "file": "path/to/file.py",
      "original_code": "exact code to replace",
      "improved_code": "improved version",
      "reason": "why this improves the code"
    }}
  ],
  "summary": "Overall assessment"
}}

Focus on:
1. Type hints on public functions
2. Google-style docstrings
3. Async patterns for I/O
4. Error handling (no bare except)
5. L9 architectural patterns

Return ONLY valid JSON.
"""

        response = requests.post(
            f"{self.base_url}?key={self.api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8000},
            },
            timeout=120,
        )

        if response.status_code != 200:
            print(f"❌ Gemini API error: {response.status_code}")
            print(response.text)
            return {"improvements": [], "summary": "API call failed"}

        result = response.json()
        try:
            text = result["candidates"][0]["content"]["parts"][0]["text"]

            # Extract JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            return json.loads(text)
        except Exception as e:
            print(f"❌ Failed to parse Gemini response: {e}")
            return {"improvements": [], "summary": "Parse error"}

    def apply_improvements(self, improvements: List[Dict]) -> int:
        """Apply code improvements to files"""
        applied = 0

        for imp in improvements:
            filepath = imp["file"]

            if self.is_protected_file(filepath):
                print(f"⚠️  Skipping protected file: {filepath}")
                continue

            if not os.path.exists(filepath):
                print(f"⚠️  File not found: {filepath}")
                continue

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                original = imp["original_code"]
                improved = imp["improved_code"]

                if original in content:
                    content = content.replace(original, improved)

                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)

                    print(f"✅ Applied improvement to: {filepath}")
                    print(f"   Reason: {imp.get('reason', 'No reason provided')}")
                    applied += 1
                else:
                    print(f"⚠️  Original code not found in: {filepath}")

            except Exception as e:
                print(f"❌ Failed to apply improvement to {filepath}: {e}")

        return applied

    def run(self):
        """Main execution"""
        print("🤖 Starting Gemini Auto-Editor...")

        diff = self.get_pr_diff()
        files = self.get_changed_files()

        if not diff:
            print("✅ No changes detected")
            return

        print(f"📁 Processing {len(files)} files...")

        # Get improvements from Gemini
        result = self.call_gemini_api(diff, files)

        # Apply improvements
        improvements = result.get("improvements", [])
        if improvements:
            applied = self.apply_improvements(improvements)
            print(f"\n✅ Applied {applied}/{len(improvements)} Gemini improvements")
        else:
            print("✅ No improvements suggested (code already meets standards)")

        print(f"\n📊 Summary: {result.get('summary', 'No summary')}")


if __name__ == "__main__":
    editor = GeminiAutoEditor()
    editor.run()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-013",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "cli",
        "filesystem",
        "operations",
        "realtime",
        "scripts",
        "serialization",
        "subprocess",
    ],
    "keywords": [
        "api",
        "apply",
        "auto",
        "changed",
        "diff",
        "editor",
        "files",
        "gemini",
    ],
    "business_value": "Implements GeminiAutoEditor for gemini auto editor functionality",
    "last_modified": "2026-01-24T17:18:34Z",
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
