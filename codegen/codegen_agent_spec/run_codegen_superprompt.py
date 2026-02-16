#!/usr/bin/env python3
"""
CodeGenAgent Superprompt Runner
===============================

Executes the PERPLEXITY_CODEGEN_AGENT_SUPERPROMPT.md against Perplexity API
to generate the 9 missing CodeGenAgent modules.

Usage:
    python run_codegen_superprompt.py --api-key YOUR_KEY
    python run_codegen_superprompt.py --api-key YOUR_KEY --model sonar-reasoning
    python run_codegen_superprompt.py --api-key YOUR_KEY --dry-run

Output:
    Creates timestamped folder with all generated files:
    - ap_generator.py
    - compliance_auditor.py
    - cursor_context_sync_engine.py
    - cursor_sync.py
    - pipeline_validator.py
    - telemetry_codegen.py
    - rollback_hook.py
    - meta.yaml
    - README.md
    - generation_metadata.json
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Run Codegen Superprompt",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-15T23:13:27Z",
    "updated_at": "2026-01-15T23:13:27Z",
    "layer": "foundation",
    "domain": "code_generation",
    "module_name": "run_codegen_superprompt",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Perplexity API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Check for required dependencies
try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")  # noqa: ADR-0019
    sys.exit(1)

try:
    from tenacity import retry, stop_after_attempt, wait_exponential

    HAS_TENACITY = True
except ImportError:
    HAS_TENACITY = False
    print("Warning: tenacity not installed. Retries disabled.")  # noqa: ADR-0019


# =============================================================================
# CONFIGURATION
# =============================================================================

SUPERPROMPT_FILE = Path(__file__).parent / "PERPLEXITY_CODEGEN_AGENT_SUPERPROMPT.md"  # noqa: ADR-0001 - internal path
OUTPUT_BASE_DIR = Path(__file__).parent / "generated"  # noqa: ADR-0001 - internal path
TARGET_DIR = Path("/Users/ib-mac/Projects/L9/core/agents/codegenagent")

EXPECTED_FILES = [
    "ap_generator.py",
    "compliance_auditor.py",
    "cursor_context_sync_engine.py",
    "cursor_sync.py",
    "pipeline_validator.py",
    "telemetry_codegen.py",
    "rollback_hook.py",
    "meta.yaml",
    "README.md",
]

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
DEFAULT_MODEL = "sonar-pro"  # or "sonar-reasoning" for deeper analysis


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class PerplexityResponse:
    """Response from Perplexity API."""

    content: str
    citations: list[str] = field(default_factory=list)
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedFile:
    """A file extracted from the API response."""

    filename: str
    content: str
    language: str
    line_count: int


@dataclass
class GenerationResult:
    """Result of the generation run."""

    success: bool
    output_dir: str
    files_created: list[str] = field(default_factory=list)
    files_expected: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    api_response: PerplexityResponse | None = None


# =============================================================================
# PERPLEXITY CLIENT
# =============================================================================


class PerplexityClient:
    """
    Async client for Perplexity Research API.

    Handles authentication, retries, and response parsing.
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout: float = 120.0,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 8000,
    ) -> PerplexityResponse:
        """
        Send prompt to Perplexity API and return response.

        Args:
            prompt: The superprompt to send
            temperature: Sampling temperature (lower = more consistent)
            max_tokens: Maximum tokens in response

        Returns:
            PerplexityResponse with content and metadata
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": temperature,
            "top_p": 0.9,
            "return_citations": True,
            "max_tokens": max_tokens,
        }

        print(f"  Calling Perplexity API with model: {self.model}")  # noqa: ADR-0019
        print(f"  Prompt length: {len(prompt):,} characters")  # noqa: ADR-0019
        print(f"  Max tokens: {max_tokens:,}")  # noqa: ADR-0019

        response = await self._client.post(
            PERPLEXITY_API_URL,
            headers=headers,
            json=payload,
        )

        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        citations = data.get("citations", [])
        usage = data.get("usage", {})

        return PerplexityResponse(
            content=content,
            citations=citations,
            model=data.get("model", self.model),
            usage=usage,
            raw=data,
        )


# =============================================================================
# FILE EXTRACTOR
# =============================================================================


class FileExtractor:
    """
    Extracts code files from API response.

    Parses markdown code blocks and identifies file boundaries.
    """

    # Patterns for different code block formats
    PYTHON_BLOCK = re.compile(r"```python\n(.*?)\n```", re.DOTALL)
    YAML_BLOCK = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL)
    MARKDOWN_BLOCK = re.compile(r"```markdown\n(.*?)\n```", re.DOTALL)

    # Pattern to find filename in code comments or headers
    FILENAME_PATTERNS = [
        re.compile(r"#\s*(?:File|Filename):\s*(.+\.py)", re.IGNORECASE),
        re.compile(r"#\s*(.+\.py)\s*$", re.MULTILINE),
        re.compile(r"###\s*MODULE\s*\d+:\s*(.+\.py)", re.IGNORECASE),
        re.compile(r"filename:\s*(.+\.(?:py|yaml|md))", re.IGNORECASE),
    ]

    def extract_files(self, response_text: str) -> list[ExtractedFile]:
        """
        Extract all code files from response text.

        Args:
            response_text: Full API response content

        Returns:
            List of ExtractedFile objects
        """
        files = []

        # Extract Python files
        files.extend(
            self._extract_by_pattern(response_text, self.PYTHON_BLOCK, "python")
        )

        # Extract YAML files
        files.extend(self._extract_by_pattern(response_text, self.YAML_BLOCK, "yaml"))

        # Extract Markdown (for README)
        files.extend(
            self._extract_by_pattern(response_text, self.MARKDOWN_BLOCK, "markdown")
        )

        return files

    def _extract_by_pattern(
        self,
        text: str,
        pattern: re.Pattern,
        language: str,
    ) -> list[ExtractedFile]:
        """Extract files matching a code block pattern."""
        files = []
        matches = pattern.findall(text)

        for i, content in enumerate(matches):
            # Try to find filename in the content
            filename = self._find_filename(content, language, i)

            files.append(
                ExtractedFile(
                    filename=filename,
                    content=content.strip(),
                    language=language,
                    line_count=content.count("\n") + 1,
                )
            )

        return files

    def _find_filename(
        self,
        content: str,
        language: str,
        index: int,
    ) -> str:
        """Try to find filename in code content."""
        for pattern in self.FILENAME_PATTERNS:
            match = pattern.search(content[:500])  # Check first 500 chars
            if match:
                return match.group(1).strip()

        # Default filenames based on language
        extensions = {"python": ".py", "yaml": ".yaml", "markdown": ".md"}
        ext = extensions.get(language, ".txt")
        return f"generated_module_{index}{ext}"


# =============================================================================
# GENERATION RUNNER
# =============================================================================


class CodeGenRunner:
    """
    Main runner for the CodeGenAgent superprompt.

    Orchestrates: Load prompt → Call API → Extract files → Save output
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        output_dir: Path | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.output_dir = output_dir or self._create_output_dir()
        self.extractor = FileExtractor()

    def _create_output_dir(self) -> Path:
        """Create timestamped output directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = OUTPUT_BASE_DIR / f"codegen_agent_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def load_superprompt(self) -> str:
        """Load the superprompt from file."""
        if not SUPERPROMPT_FILE.exists():
            raise FileNotFoundError(f"Superprompt not found: {SUPERPROMPT_FILE}")

        content = SUPERPROMPT_FILE.read_text(encoding="utf-8")

        # Remove the markdown header and instructions, keep the prompt
        # Find where the actual prompt starts
        if "# BEGIN SUPERPROMPT" in content:
            start = content.index("# BEGIN SUPERPROMPT")
            content = content[start:]

        return content

    async def run(self, dry_run: bool = False) -> GenerationResult:
        """
        Execute the full generation pipeline.

        Args:
            dry_run: If True, skip API call and use cached response

        Returns:
            GenerationResult with all details
        """
        start_time = datetime.now()
        result = GenerationResult(
            success=False,
            output_dir=str(self.output_dir),
            files_expected=EXPECTED_FILES.copy(),
        )

        print("=" * 70)  # noqa: ADR-0019
        print("CODEGEN AGENT SUPERPROMPT RUNNER")  # noqa: ADR-0019
        print("=" * 70)  # noqa: ADR-0019

        try:
            # Step 1: Load superprompt
            print("\n[1/5] Loading superprompt...")  # noqa: ADR-0019
            prompt = self.load_superprompt()
            print(f"  ✓ Loaded {len(prompt):,} characters")  # noqa: ADR-0019

            # Step 2: Call API (or skip in dry run)
            if dry_run:
                print("\n[2/5] DRY RUN - Skipping API call")  # noqa: ADR-0019
                response_text = self._get_dry_run_response()
                api_response = PerplexityResponse(content=response_text)
            else:
                print("\n[2/5] Calling Perplexity API...")  # noqa: ADR-0019
                print("  (This may take 60-120 seconds...)")  # noqa: ADR-0019

                async with PerplexityClient(self.api_key, self.model) as client:
                    api_response = await client.generate(prompt)

                print(f"  ✓ Received {len(api_response.content):,} characters")  # noqa: ADR-0019
                print(f"  ✓ Model: {api_response.model}")  # noqa: ADR-0019
                if api_response.usage:
                    print(f"  ✓ Tokens: {api_response.usage}")  # noqa: ADR-0019

            result.api_response = api_response

            # Step 3: Extract files
            print("\n[3/5] Extracting code files...")  # noqa: ADR-0019
            files = self.extractor.extract_files(api_response.content)
            print(f"  ✓ Extracted {len(files)} files")  # noqa: ADR-0019

            # Step 4: Save files
            print("\n[4/5] Saving files...")  # noqa: ADR-0019
            for f in files:
                filepath = self.output_dir / f.filename
                filepath.write_text(f.content, encoding="utf-8")
                result.files_created.append(f.filename)
                print(f"  ✓ {f.filename} ({f.line_count} lines)")  # noqa: ADR-0019

            # Save raw response
            raw_path = self.output_dir / "raw_response.md"
            raw_path.write_text(api_response.content, encoding="utf-8")

            # Save metadata
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "model": self.model,
                "prompt_length": len(prompt),
                "response_length": len(api_response.content),
                "files_extracted": len(files),
                "files_created": result.files_created,
                "files_expected": EXPECTED_FILES,
                "usage": api_response.usage,
                "citations": api_response.citations,
            }
            meta_path = self.output_dir / "generation_metadata.json"
            meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

            # Step 5: Validate
            print("\n[5/5] Validating output...")  # noqa: ADR-0019
            missing = set(EXPECTED_FILES) - set(result.files_created)
            if missing:
                result.errors.append(f"Missing files: {missing}")
                print(f"  ⚠ Missing: {missing}")  # noqa: ADR-0019
            else:
                print("  ✓ All expected files generated")  # noqa: ADR-0019

            result.success = len(result.errors) == 0

        except Exception as e:
            result.errors.append(str(e))
            print(f"\n✗ Error: {e}")  # noqa: ADR-0019

        # Calculate duration
        result.duration_seconds = (datetime.now() - start_time).total_seconds()

        # Print summary
        print("\n" + "=" * 70)  # noqa: ADR-0019
        print("GENERATION COMPLETE")  # noqa: ADR-0019
        print("=" * 70)  # noqa: ADR-0019
        print(f"\nStatus: {'SUCCESS' if result.success else 'PARTIAL'}")  # noqa: ADR-0019
        print(f"Duration: {result.duration_seconds:.1f} seconds")  # noqa: ADR-0019
        print(f"Output: {result.output_dir}")  # noqa: ADR-0019
        print(f"Files: {len(result.files_created)}/{len(EXPECTED_FILES)}")  # noqa: ADR-0019

        if result.errors:
            print("\nErrors:")  # noqa: ADR-0019
            for err in result.errors:
                print(f"  - {err}")  # noqa: ADR-0019

        print("\nNext steps:")  # noqa: ADR-0019
        print(f"  1. Review files in: {result.output_dir}")  # noqa: ADR-0019
        print(f"  2. Copy to target: cp {result.output_dir}/*.py {TARGET_DIR}/")  # noqa: ADR-0019
        print(f"  3. Run tests: pytest {TARGET_DIR}/")  # noqa: ADR-0019

        return result

    def _get_dry_run_response(self) -> str:
        """Return a minimal dry-run response for testing."""
        return """
### MODULE 1: ap_generator.py

```python
# File: ap_generator.py
# DRY RUN - Placeholder implementation

from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class GMPPromptBlock:
    inputs: List[str]
    responsibilities: List[str]
    output: str

class APGenerator:
    def generate_prompt(self, meta: Dict[str, Any]) -> str:
        return f"[AP Request] for {meta.get('name', 'unknown')}"
```

### MODULE 2: compliance_auditor.py

```python
# File: compliance_auditor.py
# DRY RUN - Placeholder implementation

class ComplianceAuditor:
    def audit_compliance(self, meta, files):
        return {"passed": True, "failures": []}
```
"""


# =============================================================================
# CLI
# =============================================================================


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Generate CodeGenAgent modules using Perplexity API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_codegen_superprompt.py --api-key YOUR_KEY
  python run_codegen_superprompt.py --api-key YOUR_KEY --model sonar-reasoning
  python run_codegen_superprompt.py --api-key YOUR_KEY --dry-run
        """,
    )

    parser.add_argument(
        "--api-key",
        required=True,
        help="Perplexity API key",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=["sonar-pro", "sonar-reasoning", "sonar"],
        help=f"Perplexity model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip API call, use placeholder response",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Custom output directory",
    )

    args = parser.parse_args()

    # Create runner
    runner = CodeGenRunner(
        api_key=args.api_key,
        model=args.model,
        output_dir=args.output_dir,
    )

    # Run async
    import asyncio

    result = asyncio.run(runner.run(dry_run=args.dry_run))

    # Exit code
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-037",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "auth",
        "caching",
        "cli",
        "client",
        "code-generation",
        "dataclass",
        "filesystem",
        "foundation",
    ],
    "keywords": [
        "audit",
        "client",
        "codegen",
        "compliance",
        "extract",
        "extracted",
        "extractor",
        "files",
    ],
    "business_value": "Provides run codegen superprompt components including PerplexityResponse, ExtractedFile, GenerationResult",
    "last_modified": "2026-01-15T23:13:27Z",
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
