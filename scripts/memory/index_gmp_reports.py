#!/usr/bin/env python3
"""
index_gmp_reports.py - Index GMP Reports to Memory Graph
========================================================

Parses GMP reports from reports/ directory, extracts decisions and lessons,
and creates knowledge facts + semantic embeddings in memory substrate.

Created: 2026-01-09
Version: 1.0.0

Usage:
    python3 scripts/index_gmp_reports.py [--dry-run] [--verbose]

Features:
- Parses GMP reports (GMP_Report_*.md files)
- Extracts: GMP ID, decisions, lessons learned, files modified
- Creates knowledge facts (subject=GMP-ID, predicate=decided/learned, object=content)
- Creates semantic embeddings for full reports
- Uses memory substrate APIs
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Index GMP Reports to Memory Graph",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "index_gmp_reports",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import os
import sys
import re
from pathlib import Path
from typing import Dict, Any, Optional
import asyncio
import structlog
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


def parse_gmp_report(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Parse a GMP report markdown file and extract structured data.

    Returns:
        Dict with gmp_id, title, date, status, decisions, lessons, files_modified
    """
    try:
        content = file_path.read_text()
    except Exception as e:
        logger.warning(f"Failed to read {file_path}: {e}")
        return None

    # Extract GMP ID from filename or header
    gmp_id_match = re.search(r"GMP-(\d+)", file_path.name)
    if not gmp_id_match:
        # Try from header
        gmp_id_match = re.search(r"\*\*GMP ID:\*\*\s*GMP-(\d+)", content)
    gmp_id = f"GMP-{gmp_id_match.group(1)}" if gmp_id_match else None

    if not gmp_id:
        logger.debug(f"No GMP ID found in {file_path.name}, skipping")
        return None

    # Extract title
    title_match = re.search(r"#\s+[^#]+\s+—\s+(.+?)(?:\n|$)", content)
    title = title_match.group(1).strip() if title_match else file_path.stem

    # Extract date
    date_match = re.search(r"\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})", content)
    date = date_match.group(1) if date_match else None

    # Extract status
    status_match = re.search(r"\*\*Status:\*\*\s*(.+?)(?:\n|$)", content)
    status = status_match.group(1).strip() if status_match else "unknown"

    # Extract decisions (from TODO → CHANGE MAP or SYNTHESIZED PLAN sections)
    decisions = []
    change_map_match = re.search(
        r"## TODO → CHANGE MAP(.*?)(?=##|\Z)", content, re.DOTALL
    )
    if change_map_match:
        # Extract key decisions from change descriptions
        decision_patterns = [
            r"Replace\s+`([^`]+)`\s+→\s+`([^`]+)`",
            r"Add\s+([^\.]+)",
            r"Remove\s+([^\.]+)",
            r"Implement\s+([^\.]+)",
        ]
        for pattern in decision_patterns:
            matches = re.finditer(pattern, change_map_match.group(1), re.IGNORECASE)
            for match in matches:
                decisions.append(match.group(0))

    # Extract lessons (from FINAL DECLARATION or YNP sections)
    lessons = []
    lesson_sections = [
        r"## LESSONS LEARNED(.*?)(?=##|\Z)",
        r"## FINAL DECLARATION(.*?)(?=##|\Z)",
        r"## YNP RECOMMENDATION(.*?)(?=##|\Z)",
    ]
    for pattern in lesson_sections:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            # Extract bullet points or key statements
            bullet_points = re.findall(r"[-*]\s+(.+?)(?:\n|$)", match.group(1))
            lessons.extend([bp.strip() for bp in bullet_points if len(bp.strip()) > 20])

    # Extract files modified
    files_modified = []
    files_section = re.search(
        r"## FILES MODIFIED(.*?)(?=##|\Z)", content, re.DOTALL | re.IGNORECASE
    )
    if files_section:
        # Extract file paths from table or list
        file_patterns = [
            r"`([^`]+\.py)`",
            r"`([^`]+\.yaml)`",
            r"`([^`]+\.md)`",
            r"\|\s*`([^`]+)`\s*\|",
        ]
        for pattern in file_patterns:
            matches = re.finditer(pattern, files_section.group(1))
            for match in matches:
                file_path = match.group(1)
                if file_path not in files_modified:
                    files_modified.append(file_path)

    return {
        "gmp_id": gmp_id,
        "title": title,
        "date": date,
        "status": status,
        "decisions": decisions,
        "lessons": lessons,
        "files_modified": files_modified,
        "content": content,
        "file_path": str(file_path.relative_to(REPO_DIR)),
    }


async def index_gmp_report(
    report_data: Dict[str, Any],
    substrate_service: Any,
) -> Dict[str, Any]:
    """
    Index a single GMP report to memory substrate.

    Creates:
    - Knowledge facts for decisions and lessons
    - Semantic embedding for full report content
    """
    gmp_id = report_data["gmp_id"]
    facts_created = 0
    embedding_created = False

    try:
        # Create knowledge facts for decisions
        for decision in report_data.get("decisions", [])[:10]:  # Limit to 10
            if len(decision.strip()) < 10:
                continue
            try:
                await substrate_service._repository.insert_knowledge_fact(
                    subject=gmp_id,
                    predicate="decided",
                    object_value={
                        "decision": decision,
                        "title": report_data.get("title"),
                    },
                    confidence=0.9,
                    source_packet=None,  # Will be set when we create packet
                )
                facts_created += 1
            except Exception as e:
                logger.warning(f"Failed to create decision fact: {e}")

        # Create knowledge facts for lessons
        for lesson in report_data.get("lessons", [])[:10]:  # Limit to 10
            if len(lesson.strip()) < 20:
                continue
            try:
                await substrate_service._repository.insert_knowledge_fact(
                    subject=gmp_id,
                    predicate="learned",
                    object_value={"lesson": lesson, "title": report_data.get("title")},
                    confidence=0.85,
                    source_packet=None,
                )
                facts_created += 1
            except Exception as e:
                logger.warning(f"Failed to create lesson fact: {e}")

        # Create knowledge fact for files modified
        if report_data.get("files_modified"):
            try:
                await substrate_service._repository.insert_knowledge_fact(
                    subject=gmp_id,
                    predicate="modified_files",
                    object_value={"files": report_data["files_modified"]},
                    confidence=1.0,
                    source_packet=None,
                )
                facts_created += 1
            except Exception as e:
                logger.warning(f"Failed to create files fact: {e}")

        # Create semantic embedding for full report
        report_text = f"""
GMP Report: {gmp_id}
Title: {report_data.get("title")}
Date: {report_data.get("date")}
Status: {report_data.get("status")}

Decisions:
{chr(10).join(report_data.get("decisions", [])[:5])}

Lessons:
{chr(10).join(report_data.get("lessons", [])[:5])}

Files Modified:
{chr(10).join(report_data.get("files_modified", [])[:10])}
"""
        try:
            embedding_id = await substrate_service.embed_text(
                text=report_text,
                payload={
                    "gmp_id": gmp_id,
                    "title": report_data.get("title"),
                    "date": report_data.get("date"),
                    "type": "gmp_report",
                    "file_path": report_data.get("file_path"),
                },
                agent_id="system",
            )
            embedding_created = True
            logger.info(f"Created embedding for {gmp_id}: {embedding_id}")
        except Exception as e:
            logger.warning(f"Failed to create embedding for {gmp_id}: {e}")

        return {
            "gmp_id": gmp_id,
            "facts_created": facts_created,
            "embedding_created": embedding_created,
            "status": "success",
        }
    except Exception as e:
        logger.error(f"Failed to index {gmp_id}: {e}", exc_info=True)
        return {
            "gmp_id": gmp_id,
            "status": "error",
            "error": str(e),
        }


async def main(dry_run: bool = False, verbose: bool = False):
    """Main indexing function."""
    logger.info("Starting GMP reports indexing", dry_run=dry_run)

    # Find all GMP report files
    gmp_files = list(REPORTS_DIR.glob("GMP_Report_*.md"))
    logger.info(f"Found {len(gmp_files)} GMP report files")

    if dry_run:
        logger.info("DRY RUN - would index:")
        for f in gmp_files:
            logger.info(f"  - {f.name}")
        return

    # Initialize memory substrate service
    try:
        from memory.substrate_service import init_service, close_service

        database_url = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL or TEST_DATABASE_URL not set")
            return

        service = await init_service(database_url)
        logger.info("Memory substrate service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize memory substrate: {e}", exc_info=True)
        return

    try:
        # Parse and index each report
        results = []
        for gmp_file in gmp_files:
            if verbose:
                logger.info(f"Processing {gmp_file.name}")

            report_data = parse_gmp_report(gmp_file)
            if not report_data:
                continue

            result = await index_gmp_report(report_data, service)
            results.append(result)

            if verbose:
                logger.info(
                    f"Indexed {result['gmp_id']}: "
                    f"{result.get('facts_created', 0)} facts, "
                    f"embedding={'yes' if result.get('embedding_created') else 'no'}"
                )

        # Summary
        total_facts = sum(r.get("facts_created", 0) for r in results)
        total_embeddings = sum(1 for r in results if r.get("embedding_created"))
        successful = sum(1 for r in results if r.get("status") == "success")

        logger.info("=" * 60)
        logger.info("GMP REPORTS INDEXING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  Reports processed: {len(results)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Total facts created: {total_facts}")
        logger.info(f"  Total embeddings created: {total_embeddings}")
        logger.info("=" * 60)

    finally:
        await close_service()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Index GMP reports to memory graph")
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
        "cli",
        "debugging",
        "filesystem",
        "logging",
        "memory-substrate",
        "operations",
        "service",
        "testing",
    ],
    "keywords": ["gmp", "graph", "index", "memory", "parse", "report", "reports"],
    "business_value": "Utility module for index gmp reports",
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
