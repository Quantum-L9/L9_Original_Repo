#!/usr/bin/env python3
"""
Load GMP Reports into Neo4j Knowledge Graph

Parses GMP report markdown files and creates graph nodes/relationships:
- GMP nodes with metadata (id, name, tier, status, date, risk_level)
- File nodes for modified files
- MODIFIED relationships (GMP → File)
- DEPENDS_ON relationships (GMP → GMP) for chained GMPs

Usage:
    python scripts/load_gmp_reports_to_graph.py
    
Or from API startup:
    from scripts.load_gmp_reports_to_graph import load_gmp_reports
    await load_gmp_reports(neo4j_driver)

Author: L9 System
Created: 2026-01-06
"""

import asyncio
import os
import re
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from neo4j import AsyncDriver

logger = structlog.get_logger(__name__)

REPORTS_DIR = Path(__file__).parent.parent / "reports"


def parse_gmp_report(file_path: Path) -> dict[str, Any] | None:
    """Parse a GMP report markdown file and extract metadata.
    
    Returns dict with:
    - id: GMP ID (e.g., "GMP-34")
    - name: Task name
    - tier: Execution tier
    - status: COMPLETE/PARTIAL/FAILED
    - executed: Execution date
    - risk_level: Low/Medium/High
    - files_modified: List of file paths
    - summary: Brief description
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("failed_to_read_report", file=str(file_path), error=str(e))
        return None
    
    result = {
        "source_file": str(file_path.name),
        "files_modified": [],
    }
    
    # Extract GMP ID from various formats
    # Format 1: **GMP ID:** GMP-34
    # Format 2: GMP ID: GMP-34
    # Format 3: # GMP Report: ... or # EXECUTION REPORT — GMP-34
    id_patterns = [
        r"\*\*GMP ID:\*\*\s*(GMP-[\w-]+)",
        r"GMP ID:\s*(GMP-[\w-]+)",
        r"#.*?(GMP-\d+)",
        r"Report[_-](GMP-[\w-]+)",
    ]
    for pattern in id_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            result["id"] = match.group(1).upper()
            break
    
    if "id" not in result:
        # Try to extract from filename
        filename_match = re.search(r"(GMP-[\w-]+)", file_path.stem, re.IGNORECASE)
        if filename_match:
            result["id"] = filename_match.group(1).upper()
        else:
            result["id"] = f"GMP-{file_path.stem[:20]}"
    
    # Extract name/title
    title_patterns = [
        r"\*\*Task:\*\*\s*(.+?)(?:\n|$)",
        r"\*\*Title:\*\*\s*(.+?)(?:\n|$)",
        r"#\s*(?:EXECUTION REPORT|GMP Report)[:\s—-]+(.+?)(?:\n|$)",
        r"#\s*(.+?)(?:\n|$)",
    ]
    for pattern in title_patterns:
        match = re.search(pattern, content)
        if match:
            result["name"] = match.group(1).strip().replace("*", "")[:100]
            break
    
    if "name" not in result:
        result["name"] = file_path.stem.replace("Report_", "").replace("GMP_Report_", "")
    
    # Extract tier
    tier_match = re.search(r"\*\*Tier:\*\*\s*(\w+)", content, re.IGNORECASE)
    if tier_match:
        result["tier"] = tier_match.group(1).upper()
    else:
        result["tier"] = "RUNTIME"  # Default
    
    # Extract status
    if "✅ COMPLETE" in content or "Status:** ✅" in content:
        result["status"] = "COMPLETE"
    elif "PARTIAL" in content:
        result["status"] = "PARTIAL"
    elif "FAILED" in content:
        result["status"] = "FAILED"
    else:
        result["status"] = "COMPLETE"  # Assume complete if report exists
    
    # Extract date
    date_patterns = [
        r"\*\*Executed:\*\*\s*([\d-]+\s*[\d:]*)",
        r"\*\*Date:\*\*\s*([\d-]+)",
        r"(\d{4}-\d{2}-\d{2})",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, content)
        if match:
            result["executed"] = match.group(1).strip()[:20]
            break
    
    if "executed" not in result:
        # Use file modification time
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        result["executed"] = mtime.strftime("%Y-%m-%d")
    
    # Extract risk level
    risk_match = re.search(r"\*\*Risk Level:\*\*\s*(\w+)", content, re.IGNORECASE)
    if risk_match:
        result["risk_level"] = risk_match.group(1).capitalize()
    else:
        result["risk_level"] = "Medium"
    
    # Extract files modified
    # Look for file paths in various formats
    file_patterns = [
        r"`([/\w._-]+\.py)`",  # `path/to/file.py`
        r"\| `([/\w._-]+\.py)` \|",  # | `file.py` |
        r"File:\s*`?(/[/\w._-]+\.py)`?",  # File: /path/to/file.py
        r"\*\*\[T\d+\]\*\* File:\s*`?([/\w._-]+)`?",  # [T1] File: path
    ]
    
    files_found = set()
    for pattern in file_patterns:
        for match in re.finditer(pattern, content):
            file_path_str = match.group(1)
            # Normalize path
            if file_path_str.startswith("/Users/"):
                # Extract relative path
                if "/L9/" in file_path_str:
                    file_path_str = file_path_str.split("/L9/")[1]
            files_found.add(file_path_str)
    
    result["files_modified"] = list(files_found)[:20]  # Limit to 20 files
    
    # Extract summary (first paragraph after executive summary or description)
    summary_patterns = [
        r"## Executive Summary\s*\n+(.+?)(?:\n\n|---)",
        r"## Summary\s*\n+(.+?)(?:\n\n|---)",
        r"\*\*Context:\*\*\s*(.+?)(?:\n|$)",
    ]
    for pattern in summary_patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            summary = match.group(1).strip()
            # Clean up markdown
            summary = re.sub(r"\*\*|\*|`", "", summary)
            summary = re.sub(r"\n+", " ", summary)
            result["summary"] = summary[:300]
            break
    
    if "summary" not in result:
        result["summary"] = result["name"]
    
    return result


async def create_gmp_nodes(driver: "AsyncDriver", reports: list[dict]) -> dict:
    """Create GMP nodes in Neo4j.
    
    Returns dict with creation statistics.
    """
    stats = {"gmps": 0, "files": 0, "modified_rels": 0}
    
    async with driver.session() as session:
        for report in reports:
            # Create GMP node
            result = await session.run(
                """
                MERGE (g:GMP {id: $id})
                SET g.name = $name,
                    g.tier = $tier,
                    g.status = $status,
                    g.executed = $executed,
                    g.risk_level = $risk_level,
                    g.summary = $summary,
                    g.source_file = $source_file,
                    g.tenant_id = 'l-cto'
                RETURN g.id
                """,
                {
                    "id": report["id"],
                    "name": report["name"],
                    "tier": report["tier"],
                    "status": report["status"],
                    "executed": report["executed"],
                    "risk_level": report["risk_level"],
                    "summary": report.get("summary", ""),
                    "source_file": report["source_file"],
                }
            )
            if await result.single():
                stats["gmps"] += 1
            
            # Create File nodes and MODIFIED relationships
            for file_path in report.get("files_modified", []):
                result = await session.run(
                    """
                    MERGE (f:File {path: $path})
                    SET f.name = $name,
                        f.tenant_id = 'l-cto'
                    WITH f
                    MATCH (g:GMP {id: $gmp_id})
                    MERGE (g)-[:MODIFIED]->(f)
                    RETURN f.path
                    """,
                    {
                        "path": file_path,
                        "name": Path(file_path).name,
                        "gmp_id": report["id"],
                    }
                )
                if await result.single():
                    stats["files"] += 1
                    stats["modified_rels"] += 1
    
    return stats


async def create_gmp_schema(driver: "AsyncDriver") -> int:
    """Create GMP-related constraints and indexes.
    
    Returns number of constraints created.
    """
    constraints = [
        "CREATE CONSTRAINT gmp_id IF NOT EXISTS FOR (g:GMP) REQUIRE g.id IS UNIQUE",
        "CREATE CONSTRAINT file_path IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE",
        "CREATE INDEX gmp_status IF NOT EXISTS FOR (g:GMP) ON (g.status)",
        "CREATE INDEX gmp_tier IF NOT EXISTS FOR (g:GMP) ON (g.tier)",
    ]
    
    created = 0
    async with driver.session() as session:
        for constraint in constraints:
            try:
                await session.run(constraint)
                created += 1
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning("constraint_failed", constraint=constraint[:50], error=str(e))
    
    return created


async def load_gmp_reports(driver: "AsyncDriver") -> dict:
    """Load all GMP reports from reports/ directory into Neo4j.
    
    Returns dict with statistics.
    """
    logger.info("load_gmp_reports_start", reports_dir=str(REPORTS_DIR))
    
    # Find all GMP report files
    report_files = list(REPORTS_DIR.glob("*GMP*.md")) + list(REPORTS_DIR.glob("Report_*.md"))
    report_files = list(set(report_files))  # Remove duplicates
    
    logger.info("found_report_files", count=len(report_files))
    
    # Parse all reports
    reports = []
    for file_path in report_files:
        parsed = parse_gmp_report(file_path)
        if parsed:
            reports.append(parsed)
    
    logger.info("parsed_reports", count=len(reports))
    
    try:
        # Create schema
        constraints = await create_gmp_schema(driver)
        logger.info("gmp_schema_created", constraints=constraints)
        
        # Create nodes
        stats = await create_gmp_nodes(driver, reports)
        logger.info(
            "gmp_reports_loaded",
            gmps=stats["gmps"],
            files=stats["files"],
            modified_rels=stats["modified_rels"],
        )
        
        return {
            "success": True,
            "reports_found": len(report_files),
            "reports_parsed": len(reports),
            **stats,
        }
        
    except Exception as e:
        logger.error("load_gmp_reports_failed", error=str(e))
        return {"success": False, "error": str(e)}


async def main():
    """CLI entrypoint for standalone execution."""
    from neo4j import AsyncGraphDatabase, basic_auth
    
    uri = os.getenv("NEO4J_URL") or os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")
    
    if not password:
        logger.info("ERROR: NEO4J_PASSWORD environment variable required")
        return
    
    logger.info(f"Connecting to Neo4j at {uri}...")
    driver = AsyncGraphDatabase.driver(uri, auth=basic_auth(user, password))
    
    try:
        result = await load_gmp_reports(driver)
        logger.info("GMP Reports Load Complete:")
        logger.info(f"  Reports found:  {result.get('reports_found', 0)}")
        logger.info(f"  Reports parsed: {result.get('reports_parsed', 0)}")
        logger.info(f"  GMP nodes:      {result.get('gmps', 0)}")
        logger.info(f"  File nodes:     {result.get('files', 0)}")
        logger.info(f"  MODIFIED rels:  {result.get('modified_rels', 0)}")
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())

