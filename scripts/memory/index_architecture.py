#!/usr/bin/env python3
"""
index_architecture.py - Index Architectural Decisions to Memory Graph
======================================================================

Parses code comments with "ARCHITECTURE:" or "DECISION:" markers, extracts from GMP reports
architectural choices, creates knowledge facts (subject=component, predicate=designed_as, object=rationale),
and links components via ARCHITECTED_BY relationship in Neo4j.

Created: 2026-01-09
Version: 1.0.0

Usage:
    python3 scripts/index_architecture.py [--dry-run] [--verbose]

Features:
- Parses code comments with ARCHITECTURE:/DECISION: markers
- Extracts architectural decisions from GMP reports
- Creates knowledge facts for design rationale
- Creates Neo4j ARCHITECTED_BY relationships
- Uses memory substrate APIs and Neo4j API
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Index Architectural Decisions to Memory Graph",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "index_architecture",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Neo4j"],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import os
import sys
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
import asyncio
import structlog
import httpx
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
load_dotenv()

logger = structlog.get_logger(__name__)

# Configuration
REPO_DIR = PROJECT_ROOT
REPORTS_DIR = REPO_DIR / "reports"
VPS_URL = os.getenv("VPS_MEMORY_URL", "https://157.180.73.53:9001")
API_KEY = os.getenv("L9_EXECUTOR_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")

# File extensions to scan for architecture comments
CODE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".cpp",
    ".c",
}


def extract_architecture_from_code(file_path: Path) -> List[Dict[str, Any]]:
    """
    Extract architecture decisions from code comments.

    Looks for patterns:
    - ARCHITECTURE: description
    - DECISION: description
    - # ARCHITECTURE: description
    - // ARCHITECTURE: description
    """
    try:
        content = file_path.read_text()
    except Exception as e:
        logger.debug(f"Failed to read {file_path}: {e}")
        return []

    decisions = []

    # Pattern for architecture/decision comments
    patterns = [
        (r"(?:#|//)\s*ARCHITECTURE:\s*(.+?)(?:\n|$)", "architecture"),
        (r"(?:#|//)\s*DECISION:\s*(.+?)(?:\n|$)", "decision"),
        (r'"""\s*ARCHITECTURE:\s*(.+?)(?:"""|$)', "architecture"),
        (r'"""\s*DECISION:\s*(.+?)(?:"""|$)', "decision"),
    ]

    for pattern, decision_type in patterns:
        matches = re.finditer(
            pattern, content, re.MULTILINE | re.DOTALL | re.IGNORECASE
        )
        for match in matches:
            description = match.group(1).strip()
            if len(description) > 20:
                # Try to extract component name from context
                lines = content[: match.start()].split("\n")
                component = None
                for line in reversed(lines[-10:]):  # Look back 10 lines
                    # Look for class/function definitions
                    class_match = re.search(r"class\s+(\w+)", line)
                    func_match = re.search(r"def\s+(\w+)", line)
                    if class_match:
                        component = class_match.group(1)
                        break
                    elif func_match:
                        component = func_match.group(1)
                        break

                decisions.append(
                    {
                        "component": component or file_path.stem,
                        "file_path": str(file_path.relative_to(REPO_DIR)),
                        "decision_type": decision_type,
                        "rationale": description,
                        "source": "code_comment",
                    }
                )

    return decisions


def extract_architecture_from_gmp_reports() -> List[Dict[str, Any]]:
    """Extract architectural decisions from GMP reports."""
    decisions = []

    gmp_files = list(REPORTS_DIR.glob("GMP_Report_*.md"))
    for gmp_file in gmp_files:
        try:
            content = gmp_file.read_text()

            # Extract GMP ID
            gmp_id_match = re.search(r"GMP-(\d+)", gmp_file.name)
            gmp_id = f"GMP-{gmp_id_match.group(1)}" if gmp_id_match else None

            # Look for architectural decisions in SYNTHESIZED PLAN or TODO → CHANGE MAP
            sections = [
                (r"## SYNTHESIZED PLAN(.*?)(?=##|\Z)", "synthesized_plan"),
                (r"## TODO → CHANGE MAP(.*?)(?=##|\Z)", "change_map"),
                (r"## ARCHITECTURAL DECISIONS(.*?)(?=##|\Z)", "arch_decisions"),
            ]

            for pattern, section_type in sections:
                match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                if match:
                    section_content = match.group(1)

                    # Extract component names and decisions
                    # Look for file paths and component names
                    file_matches = re.finditer(r"`([^`]+\.py)`", section_content)
                    for file_match in file_matches:
                        file_path = file_match.group(1)
                        component = Path(file_path).stem

                        # Extract decision text near this file reference
                        start = max(0, file_match.start() - 200)
                        end = min(len(section_content), file_match.end() + 200)
                        context = section_content[start:end]

                        # Look for decision keywords
                        decision_keywords = [
                            r"Replace\s+`([^`]+)`\s+→\s+`([^`]+)`",
                            r"Add\s+([^\.]+)",
                            r"Implement\s+([^\.]+)",
                            r"Refactor\s+([^\.]+)",
                        ]

                        for keyword_pattern in decision_keywords:
                            keyword_match = re.search(
                                keyword_pattern, context, re.IGNORECASE
                            )
                            if keyword_match:
                                rationale = keyword_match.group(0)
                                decisions.append(
                                    {
                                        "component": component,
                                        "file_path": file_path,
                                        "decision_type": "architectural",
                                        "rationale": rationale,
                                        "source": f"gmp_report_{gmp_id}",
                                        "gmp_id": gmp_id,
                                    }
                                )
                                break

        except Exception as e:
            logger.debug(f"Failed to parse {gmp_file}: {e}")

    return decisions


async def api_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make authenticated API request to VPS."""
    if not API_KEY:
        return {"error": "L9_EXECUTOR_API_KEY not set", "success": False}

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    url = f"{VPS_URL}{endpoint}"

    async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
        try:
            if method.upper() == "POST":
                response = await client.post(url, headers=headers, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"API request failed: {e}")
            return {"error": str(e), "success": False}


async def execute_cypher(
    query: str, parameters: Optional[Dict] = None
) -> Dict[str, Any]:
    """Execute Cypher query via VPS API."""
    return await api_request(
        "POST",
        "/api/v1/memory/graph/query",
        json={"query": query, "parameters": parameters or {}},
    )


async def index_architecture_decisions(
    decisions: List[Dict[str, Any]],
    substrate_service: Any,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Index architectural decisions to memory substrate and Neo4j.

    Creates:
    - Knowledge facts (subject=component, predicate=designed_as, object=rationale)
    - Neo4j ARCHITECTED_BY relationships
    """
    if dry_run:
        logger.info(f"DRY RUN - would index {len(decisions)} architectural decisions")
        return {"decisions_indexed": len(decisions), "dry_run": True}

    facts_created = 0
    relationships_created = 0
    errors = []

    # Group decisions by component
    components = {}
    for decision in decisions:
        component = decision["component"]
        if component not in components:
            components[component] = []
        components[component].append(decision)

    # Index each component's decisions
    for component, comp_decisions in components.items():
        try:
            # Create knowledge facts
            for decision in comp_decisions[:5]:  # Limit to 5 per component
                try:
                    await substrate_service._repository.insert_knowledge_fact(
                        subject=component,
                        predicate="designed_as",
                        object_value={
                            "rationale": decision["rationale"],
                            "decision_type": decision["decision_type"],
                            "source": decision["source"],
                            "file_path": decision.get("file_path"),
                            "gmp_id": decision.get("gmp_id"),
                        },
                        confidence=0.9,
                        source_packet=None,
                    )
                    facts_created += 1
                except Exception as e:
                    logger.debug(f"Failed to create fact for {component}: {e}")

            # Create Neo4j ARCHITECTED_BY relationship (component → GMP or system)
            if comp_decisions[0].get("gmp_id"):
                gmp_id = comp_decisions[0]["gmp_id"]
                query = """
                MERGE (c:Component {name: $component})
                SET c.updated_at = datetime()
                WITH c
                MERGE (g:GMP {id: $gmp_id})
                SET g.updated_at = datetime()
                WITH c, g
                MERGE (c)-[r:ARCHITECTED_BY]->(g)
                SET r.updated_at = datetime()
                RETURN count(r) as relationships_created
                """

                try:
                    result = await execute_cypher(
                        query,
                        {
                            "component": component,
                            "gmp_id": gmp_id,
                        },
                    )
                    if result.get("success"):
                        relationships_created += 1
                except Exception as e:
                    logger.debug(f"Failed to create Neo4j relationship: {e}")

        except Exception as e:
            errors.append(f"Component {component}: {str(e)}")
            logger.debug(f"Failed to index {component}: {e}")

    return {
        "decisions_indexed": len(decisions),
        "facts_created": facts_created,
        "relationships_created": relationships_created,
        "errors": errors,
        "status": "success" if not errors else "partial",
    }


async def main(dry_run: bool = False, verbose: bool = False):
    """Main indexing function."""
    logger.info("Starting architectural decisions indexing", dry_run=dry_run)

    # Extract from code comments
    logger.info("Scanning code files for ARCHITECTURE:/DECISION: comments...")
    code_decisions = []

    # Scan core directories
    scan_dirs = [
        REPO_DIR / "core",
        REPO_DIR / "memory",
        REPO_DIR / "api",
        REPO_DIR / "orchestration",
    ]

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        for code_file in scan_dir.rglob("*"):
            if code_file.suffix in CODE_EXTENSIONS:
                decisions = extract_architecture_from_code(code_file)
                code_decisions.extend(decisions)

    logger.info(f"Found {len(code_decisions)} architectural decisions in code")

    # Extract from GMP reports
    logger.info("Extracting architectural decisions from GMP reports...")
    gmp_decisions = extract_architecture_from_gmp_reports()
    logger.info(f"Found {len(gmp_decisions)} architectural decisions in GMP reports")

    all_decisions = code_decisions + gmp_decisions
    logger.info(f"Total architectural decisions: {len(all_decisions)}")

    if not all_decisions:
        logger.warning("No architectural decisions found")
        return

    if verbose:
        logger.info("Sample decisions:")
        for decision in all_decisions[:5]:
            logger.info(f"  {decision['component']}: {decision['rationale'][:50]}...")

    # Initialize memory substrate service
    if not DATABASE_URL:
        logger.error("DATABASE_URL or TEST_DATABASE_URL not set")
        return

    try:
        from memory.substrate_service import init_service, close_service

        service = await init_service(DATABASE_URL)
        logger.info("Memory substrate service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize memory substrate: {e}", exc_info=True)
        return

    try:
        # Index architectural decisions
        result = await index_architecture_decisions(
            all_decisions, service, dry_run=dry_run
        )

        # Summary
        logger.info("=" * 60)
        logger.info("ARCHITECTURAL DECISIONS INDEXING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  Decisions found: {len(all_decisions)}")
        logger.info(f"  From code: {len(code_decisions)}")
        logger.info(f"  From GMP reports: {len(gmp_decisions)}")
        logger.info(f"  Decisions indexed: {result.get('decisions_indexed', 0)}")
        logger.info(f"  Facts created: {result.get('facts_created', 0)}")
        logger.info(
            f"  Relationships created: {result.get('relationships_created', 0)}"
        )
        if result.get("errors"):
            logger.warning(f"  Errors: {len(result['errors'])}")
            for error in result["errors"][:5]:
                logger.warning(f"    - {error}")
        logger.info("=" * 60)

    finally:
        await close_service()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Index architectural decisions to memory graph"
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no writes)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run, verbose=args.verbose))

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.substrate_service"],
    "tags": [
        "api",
        "async",
        "auth",
        "cli",
        "debugging",
        "filesystem",
        "http-client",
        "logging",
        "memory-substrate",
        "operations",
    ],
    "keywords": [
        "api",
        "architectural",
        "architecture",
        "cypher",
        "decisions",
        "execute",
        "extract",
        "gmp",
    ],
    "business_value": "Utility module for index architecture",
    "last_modified": "2026-01-14T15:03:00Z",
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
