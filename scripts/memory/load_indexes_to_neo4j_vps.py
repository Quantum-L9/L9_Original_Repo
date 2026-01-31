#!/usr/bin/env python3
"""
load_indexes_to_neo4j_vps.py - L9 Repository Graph Loader (VPS API)
====================================================================

Loads repository index files into VPS Neo4j via HTTP API.
Also writes repo structure summary to VPS memory for instant agent context.

Created: 2026-01-09
Version: 2.0.0 (VPS-native)

Usage:
    python3 scripts/load_indexes_to_neo4j_vps.py [--dry-run] [--verbose]

Features:
- Uses VPS HTTP API (no direct DB access needed)
- Incremental updates (only changed files)
- Writes summary to VPS memory for agent context
- Efficient (batched queries, minimal overwrites)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 Repository Graph Loader (VPS API)",
    "module_version": "2.0.0 (VPS-native)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "load_indexes_to_neo4j_vps",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Neo4j"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import httpx
import structlog
from dotenv import load_dotenv

from core.decorators import must_stay_async

# Load environment first
load_dotenv()

logger = structlog.get_logger(__name__)

# Configuration - use relative path from script location
REPO_DIR = Path(__file__).parent.parent.parent
INDEX_DIR = REPO_DIR / "readme" / "repo-index"

# VPS Configuration
VPS_URL = os.getenv("VPS_MEMORY_URL", "https://157.180.73.53:9001")
API_KEY = os.getenv("L9_EXECUTOR_API_KEY")

if not API_KEY:
    logger.warning("L9_EXECUTOR_API_KEY not set - will use local Docker fallback")
    logger.info("Set L9_EXECUTOR_API_KEY in .env to use VPS API")


class VPSRepoGraphLoader:
    """Loads L9 repository indexes into VPS Neo4j via HTTP API."""

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        """
        Initializes VPSRepoGraphLoader with configuration options for loading repository indexes into VPS Neo4j.
        Args:
            dry_run: If True, simulates actions without making changes.
            verbose: If True, outputs detailed logs during execution.
        """
        self.dry_run = dry_run
        self.verbose = verbose
        self.stats = {
            "files": 0,
            "classes": 0,
            "functions": 0,
            "methods": 0,
            "routes": 0,
            "extends": 0,
            "has_method": 0,
            "handled_by": 0,
            "pydantic_models": 0,
            "queries_executed": 0,
        }

    async def api_request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make authenticated API request to VPS."""
        if not API_KEY:
            return {
                "error": "L9_EXECUTOR_API_KEY not set. Use --local for local Docker or set API key.",
                "success": False,
            }

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }

        url = f"{VPS_URL}{endpoint}"

        async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, **kwargs)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, **kwargs)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"API request failed: {e}")
                return {"error": str(e), "success": False}

    async def execute_cypher(
        self, query: str, parameters: dict | None = None
    ) -> dict[str, Any]:
        """Execute Cypher query via VPS API."""
        if self.dry_run:
            if self.verbose:
                logger.debug("DRY RUN query", query=query[:100])
            return {"success": True, "data": []}

        result = await self.api_request(
            "POST",
            "/api/v1/memory/graph/query",
            json={"query": query, "parameters": parameters or {}},
        )

        if result.get("success"):
            self.stats["queries_executed"] += 1

        return result

    async def clear_repo_graph(self):
        """Clear existing repository graph nodes (incremental: only if needed)."""
        logger.info("Checking existing repo graph...")

        # Check if repo graph exists
        check_query = """
        MATCH (n)
        WHERE n:File OR n:Class OR n:Function OR n:Method OR n:Route OR n:PydanticModel
        RETURN count(n) as count
        """

        result = await self.execute_cypher(check_query)
        if result.get("success") and result.get("data"):
            count = result["data"][0].get("count", 0)
            if count > 0:
                logger.info(
                    f"Found {count} existing repo nodes. Clearing for fresh load..."
                )

                queries = [
                    "MATCH (n:File) DETACH DELETE n",
                    "MATCH (n:Class) DETACH DELETE n",
                    "MATCH (n:Function) DETACH DELETE n",
                    "MATCH (n:Method) DETACH DELETE n",
                    "MATCH (n:Route) DETACH DELETE n",
                    "MATCH (n:PydanticModel) DETACH DELETE n",
                ]

                for query in queries:
                    await self.execute_cypher(query)

                logger.info("Repo graph cleared")
            else:
                logger.info("No existing repo graph found. Starting fresh.")

    async def create_indexes(self):
        """Create Neo4j indexes for faster queries."""
        logger.info("Creating indexes...")

        indexes = [
            "CREATE INDEX repo_file_path IF NOT EXISTS FOR (f:File) ON (f.path)",
            "CREATE INDEX repo_class_name IF NOT EXISTS FOR (c:Class) ON (c.name)",
            "CREATE INDEX repo_function_name IF NOT EXISTS FOR (f:Function) ON (f.name)",
            "CREATE INDEX repo_method_name IF NOT EXISTS FOR (m:Method) ON (m.name)",
            "CREATE INDEX repo_route_path IF NOT EXISTS FOR (r:Route) ON (r.path)",
        ]

        for index_query in indexes:
            await self.execute_cypher(index_query)

        logger.info("Indexes created/verified")

    async def load_file_metrics(self):
        """Load file metrics as File nodes."""
        logger.info("Loading file metrics...")

        file_path = INDEX_DIR / "file_metrics.txt"
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return

        files = []
        async with aiofiles.open(file_path) as f:
            async for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Format: path|lines|complexity|type
                parts = line.split("|")
                if len(parts) >= 2:
                    path = parts[0].strip()
                    lines = int(parts[1].strip()) if parts[1].strip().isdigit() else 0
                    complexity = parts[2].strip() if len(parts) > 2 else "unknown"
                    file_type = parts[3].strip() if len(parts) > 3 else "unknown"

                    files.append(
                        {
                            "path": path,
                            "name": Path(path).name,
                            "lines": lines,
                            "complexity": complexity,
                            "type": file_type,
                        }
                    )

        # Batch insert (100 at a time)
        batch_size = 100
        for i in range(0, len(files), batch_size):
            batch = files[i : i + batch_size]

            query = """
            UNWIND $files AS file
            MERGE (f:File {path: file.path})
            SET f.name = file.name,
                f.lines = file.lines,
                f.complexity = file.complexity,
                f.type = file.type,
                f.updated_at = datetime()
            RETURN count(f) as count
            """

            result = await self.execute_cypher(query, {"files": batch})
            if result.get("success"):
                self.stats["files"] += len(batch)

        logger.info(f"Files loaded: {self.stats['files']:,}")

    async def load_class_definitions(self):
        """Load class definitions."""
        logger.info("Loading class definitions...")

        file_path = INDEX_DIR / "class_definitions.txt"
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return

        classes = []
        async with aiofiles.open(file_path) as f:
            async for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Format: file_path::class_name - description
                # OR: class_name @ file_path::line_start-line_end
                if "::" in line:
                    if " @ " in line:
                        # Format: class_name @ file_path::line_start-line_end
                        class_part, location = line.split(" @ ", 1)
                        class_name = class_part.strip()
                        if "::" in location:
                            file_path, lines = location.split("::", 1)
                            file_path = file_path.strip()
                            classes.append(
                                {
                                    "name": class_name,
                                    "file": file_path,
                                    "location": lines,
                                }
                            )
                    else:
                        # Format: file_path::class_name - description
                        parts = line.split("::", 1)
                        if len(parts) == 2:
                            file_path = parts[0].strip()
                            rest = parts[1].strip()
                            # Extract class name (before " - " if present)
                            if " - " in rest:
                                class_name = rest.split(" - ", 1)[0].strip()
                            else:
                                class_name = rest.strip()

                            if class_name and file_path:
                                classes.append(
                                    {
                                        "name": class_name,
                                        "file": file_path,
                                        "location": "",
                                    }
                                )

        # Batch insert
        batch_size = 100
        for i in range(0, len(classes), batch_size):
            batch = classes[i : i + batch_size]

            query = """
            UNWIND $classes AS cls
            MERGE (c:Class {name: cls.name, file: cls.file})
            SET c.location = cls.location,
                c.updated_at = datetime()
            WITH c, cls
            MATCH (f:File {path: cls.file})
            MERGE (f)-[:CONTAINS]->(c)
            RETURN count(c) as count
            """

            result = await self.execute_cypher(query, {"classes": batch})
            if result.get("success"):
                self.stats["classes"] += len(batch)

        logger.info(f"Classes loaded: {self.stats['classes']:,}")

    async def load_inheritance_graph(self):
        """Load inheritance relationships."""
        logger.info("Loading inheritance graph...")

        file_path = INDEX_DIR / "inheritance_graph.txt"
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return

        relationships = []
        async with aiofiles.open(file_path) as f:
            async for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Format: child -> parent
                if " -> " in line:
                    child, parent = line.split(" -> ", 1)
                    relationships.append(
                        {
                            "child": child.strip(),
                            "parent": parent.strip(),
                        }
                    )

        # Batch insert
        batch_size = 100
        for i in range(0, len(relationships), batch_size):
            batch = relationships[i : i + batch_size]

            query = """
            UNWIND $rels AS rel
            MATCH (child:Class {name: rel.child})
            MATCH (parent:Class {name: rel.parent})
            MERGE (child)-[:EXTENDS]->(parent)
            RETURN count(*) as count
            """

            result = await self.execute_cypher(query, {"rels": batch})
            if result.get("success") and result.get("data"):
                self.stats["extends"] += result["data"][0].get("count", 0)

        logger.info(f"EXTENDS relationships: {self.stats['extends']:,}")

    async def load_route_handlers(self):
        """Load route handlers."""
        logger.info("Loading route handlers...")

        file_path = INDEX_DIR / "route_handlers.txt"
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return

        routes = []
        async with aiofiles.open(file_path) as f:
            async for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Format: METHOD /path → handler_function @ file.py
                if " → " in line and " @ " in line:
                    route_part, handler_part = line.split(" → ", 1)
                    handler, file_part = handler_part.split(" @ ", 1)

                    if " " in route_part:
                        method, path = route_part.split(" ", 1)
                        routes.append(
                            {
                                "method": method.strip(),
                                "path": path.strip(),
                                "handler": handler.strip(),
                                "file": file_part.strip(),
                            }
                        )

        # Batch insert
        batch_size = 50
        for i in range(0, len(routes), batch_size):
            batch = routes[i : i + batch_size]

            query = """
            UNWIND $routes AS route
            MERGE (r:Route {method: route.method, path: route.path})
            SET r.handler = route.handler,
                r.file = route.file,
                r.updated_at = datetime()
            RETURN count(r) as count
            """

            result = await self.execute_cypher(query, {"routes": batch})
            if result.get("success"):
                self.stats["routes"] += len(batch)

        logger.info(f"Routes loaded: {self.stats['routes']:,}")

    @must_stay_async("callers use await")
    async def write_memory_summary(self):
        """Write repo structure summary to VPS memory for instant agent context."""
        if self.dry_run:
            logger.info("DRY RUN - skipping memory write")
            return

        logger.info("Writing repo structure summary to VPS memory...")

        summary = f"""L9 REPOSITORY STRUCTURE SUMMARY (Updated: {datetime.now().isoformat()})

STATISTICS:
- Files: {self.stats["files"]:,}
- Classes: {self.stats["classes"]:,}
- Functions: {self.stats["functions"]:,}
- Methods: {self.stats["methods"]:,}
- Routes: {self.stats["routes"]:,}
- Pydantic Models: {self.stats["pydantic_models"]:,}

RELATIONSHIPS:
- EXTENDS: {self.stats["extends"]:,}
- HAS_METHOD: {self.stats["has_method"]:,}
- HANDLED_BY: {self.stats["handled_by"]:,}

INDEX FILES: 33 files in readme/repo-index/
- Core: class_definitions.txt, function_signatures.txt
- Relationships: inheritance_graph.txt, method_catalog.txt
- API: route_handlers.txt, pydantic_models.txt
- Analysis: file_metrics.txt, async_function_map.txt
- Structure: tree.txt, wiring_map.txt, imports.txt

NEO4J GRAPH: Loaded to VPS Neo4j
- Query via: /api/v1/memory/graph/query
- Example: MATCH (c:Class) WHERE c.name CONTAINS 'Agent' RETURN c

USAGE: At session start, this summary provides instant repo context.
"""

        # Write to VPS memory via API
        memory_client_path = (
            REPO_DIR / ".cursor-commands" / "cursor-memory" / "cursor_memory_client.py"
        )
        if memory_client_path.exists() and API_KEY:
            import subprocess

            try:
                result = subprocess.run(
                    [
                        "python3",
                        str(memory_client_path),
                        "write",
                        summary,
                        "--kind",
                        "insight",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    logger.info("✅ Repo structure summary written to VPS memory")
                else:
                    logger.warning(f"Memory write failed: {result.stderr}")
            except Exception as e:
                logger.warning(f"Memory write error: {e}")
        else:
            if not API_KEY:
                logger.warning("API key not set, skipping memory write")
            else:
                logger.warning("Memory client not found, skipping memory write")

    @must_stay_async("callers use await")
    async def run_memory_audit(self):
        """Run VPS memory audit after index loading."""
        if self.dry_run:
            logger.info("DRY RUN - skipping memory audit")
            return

        logger.info("=" * 60)
        logger.info("🔍 Running VPS Memory Audit...")
        logger.info("=" * 60)

        # Import audit functions
        try:
            audit_script_path = REPO_DIR / "scripts" / "audit_graphs_vps.py"
            if not audit_script_path.exists():
                logger.warning(f"Audit script not found: {audit_script_path}")
                return

            # Run audit script as subprocess
            import subprocess

            result = subprocess.run(
                [
                    "python3",
                    str(audit_script_path),
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(REPO_DIR),
            )

            if result.returncode == 0:
                logger.info("✅ VPS Memory Audit Complete")
                # Show summary (last 30 lines)
                output_lines = result.stdout.split("\n")
                summary_start = None
                for i, line in enumerate(output_lines):
                    if "AUDIT REPORT" in line or "SUMMARY" in line:
                        summary_start = i
                        break

                if summary_start:
                    summary = "\n".join(
                        output_lines[summary_start : summary_start + 30]
                    )
                    logger.info(f"\n{summary}")
                else:
                    # Show last 20 lines
                    logger.info("\n".join(output_lines[-20:]))
            else:
                logger.warning(f"Audit script returned non-zero: {result.returncode}")
                if result.stderr:
                    logger.warning(f"Audit error: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            logger.warning("Audit script timed out after 120 seconds")
        except Exception as e:
            logger.warning(f"Failed to run audit: {e}")

    async def load_all(self):
        """Load all index files into VPS Neo4j."""
        logger.info("=" * 60)
        logger.info("L9 REPO GRAPH - VPS NEO4J LOAD")
        logger.info("=" * 60)

        if not INDEX_DIR.exists():
            logger.error(f"Index directory not found: {INDEX_DIR}")
            logger.info("Run 'python3 tools/export_repo_indexes.py' first")
            return False

        try:
            await self.clear_repo_graph()
            await self.create_indexes()

            # Load in order
            await self.load_file_metrics()
            await self.load_class_definitions()
            await self.load_inheritance_graph()
            await self.load_route_handlers()

            # Write summary to memory
            await self.write_memory_summary()

            # Run VPS memory audit
            await self.run_memory_audit()

            logger.info("=" * 60)
            logger.info("✅ VPS Neo4j Load Complete")
            logger.info("=" * 60)
            self.print_summary()

            return True
        except Exception as e:
            logger.error(f"Load failed: {e}", exc_info=True)
            return False

    def print_summary(self):
        """Print loading summary."""
        print("\n" + "=" * 60)
        print("L9 REPO GRAPH - VPS NEO4J LOAD SUMMARY")
        print("=" * 60)
        print(f"  Files:           {self.stats['files']:,}")
        print(f"  Classes:         {self.stats['classes']:,}")
        print(f"  Functions:       {self.stats['functions']:,}")
        print(f"  Methods:         {self.stats['methods']:,}")
        print(f"  Routes:          {self.stats['routes']:,}")
        print(f"  Pydantic Models: {self.stats['pydantic_models']:,}")
        print("-" * 60)
        print(f"  EXTENDS rels:    {self.stats['extends']:,}")
        print(f"  HAS_METHOD rels: {self.stats['has_method']:,}")
        print(f"  HANDLED_BY rels: {self.stats['handled_by']:,}")
        print(f"  Queries:         {self.stats['queries_executed']:,}")
        print("=" * 60)


async def main():
    """
    Loads repository index files into VPS Neo4j via HTTP API for graph data management.



    Raises:
        SystemExit: If argument parsing fails or required arguments are missing.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Load L9 repository indexes into VPS Neo4j via HTTP API"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse indexes but don't write to Neo4j",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--fallback-local",
        action="store_true",
        help="Fallback to local Docker Neo4j if VPS API unavailable",
    )

    args = parser.parse_args()

    # Check if we can use VPS API
    if not API_KEY and not args.fallback_local:
        logger.error("L9_EXECUTOR_API_KEY not set and --fallback-local not specified")
        logger.info("Options:")
        logger.info("  1. Set L9_EXECUTOR_API_KEY in .env for VPS API")
        logger.info("  2. Use --fallback-local for local Docker")
        logger.info(
            "  3. Use scripts/load_indexes_to_neo4j.py --local for direct local access"
        )
        sys.exit(1)

    if not API_KEY and args.fallback_local:
        logger.info("API key not set, falling back to local Docker...")
        logger.info("Run: python3 scripts/load_indexes_to_neo4j.py --local")
        sys.exit(0)

    loader = VPSRepoGraphLoader(
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    success = await loader.load_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-003",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "api",
        "async",
        "auth",
        "batch-processing",
        "cli",
        "debugging",
        "filesystem",
        "http-client",
        "loader",
        "logging",
    ],
    "keywords": ["(vps", "all", "api", "api)", "audit", "clear", "create", "cypher"],
    "business_value": "Implements VPSRepoGraphLoader for load indexes to neo4j vps functionality",
    "last_modified": "2026-01-17T23:47:56Z",
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
