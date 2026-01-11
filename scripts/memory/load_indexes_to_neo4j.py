#!/usr/bin/env python3
"""
load_indexes_to_neo4j.py - L9 Repository Graph Loader
======================================================

Loads repository index files into Neo4j for graph-based code navigation.

Created: 2026-01-06
Version: 1.0.0

Usage:
    python3 scripts/load_indexes_to_neo4j.py [--dry-run] [--verbose]

Loads:
    - class_definitions.txt → Class nodes
    - inheritance_graph.txt → EXTENDS relationships
    - method_catalog.txt → Method nodes + HAS_METHOD relationships
    - route_handlers.txt → Route nodes + HANDLED_BY relationships
    - function_signatures.txt → Function nodes
    - pydantic_models.txt → PydanticModel nodes
    - file_metrics.txt → File nodes with metrics
"""

import os
import re
import sys
import argparse
import structlog
from pathlib import Path
from typing import Optional

logger = structlog.get_logger(__name__)

# Configuration
REPO_DIR = Path("/Users/ib-mac/Projects/L9")
INDEX_DIR = REPO_DIR / "readme" / "repo-index"

# Try to import Neo4j
try:
    from neo4j import GraphDatabase, basic_auth
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False
    logger.warning("Neo4j driver not installed. Run: pip install neo4j")


class RepoGraphLoader:
    """Loads L9 repository indexes into Neo4j graph database."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: str = "neo4j",
        dry_run: bool = False,
        verbose: bool = False,
    ):
        self.uri = uri or os.getenv("NEO4J_URL") or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self.database = database
        self.dry_run = dry_run
        self.verbose = verbose
        self.driver = None
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
        }

    def connect(self) -> bool:
        """Connect to Neo4j."""
        if self.dry_run:
            logger.info("DRY RUN - skipping Neo4j connection", uri=self.uri)
            return True

        if not HAS_NEO4J:
            logger.error("Neo4j driver not available")
            return False

        if not self.password:
            logger.error("NEO4J_PASSWORD not set")
            return False

        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=basic_auth(self.user, self.password),
            )
            # Test connection
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            logger.info("Neo4j connected", uri=self.uri, database=self.database)
            return True
        except Exception as e:
            logger.error("Neo4j connection failed", error=str(e))
            return False

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j disconnected")

    def _run_query(self, query: str, parameters: dict = None):
        """Run a Cypher query."""
        if self.dry_run:
            if self.verbose:
                logger.debug("DRY RUN query", query=query[:100])
            return

        if not self.driver:
            return

        with self.driver.session(database=self.database) as session:
            session.run(query, parameters or {})

    def clear_repo_graph(self):
        """Clear existing repository graph nodes."""
        logger.info("Clearing existing repo graph...")
        
        queries = [
            "MATCH (n:RepoFile) DETACH DELETE n",
            "MATCH (n:RepoClass) DETACH DELETE n",
            "MATCH (n:RepoFunction) DETACH DELETE n",
            "MATCH (n:RepoMethod) DETACH DELETE n",
            "MATCH (n:RepoRoute) DETACH DELETE n",
            "MATCH (n:RepoPydanticModel) DETACH DELETE n",
        ]
        
        for query in queries:
            self._run_query(query)
        
        logger.info("Repo graph cleared")

    def create_indexes(self):
        """Create Neo4j indexes for faster queries."""
        logger.info("Creating indexes...")
        
        indexes = [
            "CREATE INDEX repo_file_path IF NOT EXISTS FOR (f:RepoFile) ON (f.path)",
            "CREATE INDEX repo_class_name IF NOT EXISTS FOR (c:RepoClass) ON (c.name)",
            "CREATE INDEX repo_function_name IF NOT EXISTS FOR (f:RepoFunction) ON (f.name)",
            "CREATE INDEX repo_method_name IF NOT EXISTS FOR (m:RepoMethod) ON (m.name)",
            "CREATE INDEX repo_route_path IF NOT EXISTS FOR (r:RepoRoute) ON (r.path)",
        ]
        
        for index_query in indexes:
            self._run_query(index_query)
        
        logger.info("Indexes created")

    def load_file_metrics(self):
        """Load file metrics as File nodes."""
        metrics_file = INDEX_DIR / "file_metrics.txt"
        if not metrics_file.exists():
            logger.warning("file_metrics.txt not found")
            return

        logger.info("Loading file metrics...")
        
        with open(metrics_file, "r") as f:
            for line in f:
                # Parse: | `path/to/file.py` | 100 | 5 | 10 | 3 |
                match = re.match(r'\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|', line)
                if match:
                    path, lines, classes, functions, async_funcs = match.groups()
                    
                    query = """
                    MERGE (f:RepoFile {path: $path})
                    SET f.lines = $lines,
                        f.class_count = $classes,
                        f.function_count = $functions,
                        f.async_count = $async_funcs,
                        f.name = $name
                    """
                    
                    self._run_query(query, {
                        "path": path,
                        "lines": int(lines),
                        "classes": int(classes),
                        "functions": int(functions),
                        "async_funcs": int(async_funcs),
                        "name": Path(path).name,
                    })
                    self.stats["files"] += 1

        logger.info("File metrics loaded", count=self.stats["files"])

    def load_class_definitions(self):
        """Load class definitions as Class nodes."""
        classes_file = INDEX_DIR / "class_definitions.txt"
        if not classes_file.exists():
            logger.warning("class_definitions.txt not found")
            return

        logger.info("Loading class definitions...")
        
        with open(classes_file, "r") as f:
            for line in f:
                # Parse: path/to/file.py::ClassName - Docstring
                match = re.match(r'^([^:]+)::(\w+)\s*-\s*(.*)$', line.strip())
                if match:
                    path, class_name, docstring = match.groups()
                    
                    query = """
                    MERGE (c:RepoClass {name: $name, file: $file})
                    SET c.docstring = $docstring
                    WITH c
                    MERGE (f:RepoFile {path: $file})
                    MERGE (f)-[:CONTAINS]->(c)
                    """
                    
                    self._run_query(query, {
                        "name": class_name,
                        "file": path,
                        "docstring": docstring[:200] if docstring else "",
                    })
                    self.stats["classes"] += 1

        logger.info("Class definitions loaded", count=self.stats["classes"])

    def load_inheritance_graph(self):
        """Load inheritance relationships."""
        inheritance_file = INDEX_DIR / "inheritance_graph.txt"
        if not inheritance_file.exists():
            logger.warning("inheritance_graph.txt not found")
            return

        logger.info("Loading inheritance graph...")
        
        with open(inheritance_file, "r") as f:
            for line in f:
                # Parse: ChildClass::Parent1,Parent2 @ path/to/file.py
                match = re.match(r'^(\w+)::([^@]+)\s*@\s*(.+)$', line.strip())
                if match:
                    child, parents_str, path = match.groups()
                    parents = [p.strip() for p in parents_str.split(',')]
                    
                    for parent in parents:
                        if parent and parent not in ('object', 'ABC', 'Protocol'):
                            query = """
                            MERGE (child:RepoClass {name: $child})
                            SET child.file = $file
                            MERGE (parent:RepoClass {name: $parent})
                            MERGE (child)-[:EXTENDS]->(parent)
                            """
                            
                            self._run_query(query, {
                                "child": child,
                                "parent": parent,
                                "file": path,
                            })
                            self.stats["extends"] += 1

        logger.info("Inheritance graph loaded", count=self.stats["extends"])

    def load_method_catalog(self):
        """Load class methods."""
        methods_file = INDEX_DIR / "method_catalog.txt"
        if not methods_file.exists():
            logger.warning("method_catalog.txt not found")
            return

        logger.info("Loading method catalog...")
        
        with open(methods_file, "r") as f:
            for line in f:
                # Parse: ClassName::method_name(args) @ path/to/file.py
                match = re.match(r'^(\w+)::(async\s+)?(\w+)\(([^)]*)\)\s*@\s*(.+)$', line.strip())
                if match:
                    class_name, is_async, method_name, args, path = match.groups()
                    
                    query = """
                    MERGE (c:RepoClass {name: $class_name})
                    MERGE (m:RepoMethod {name: $method_name, class: $class_name})
                    SET m.args = $args,
                        m.is_async = $is_async,
                        m.file = $file
                    MERGE (c)-[:HAS_METHOD]->(m)
                    """
                    
                    self._run_query(query, {
                        "class_name": class_name,
                        "method_name": method_name,
                        "args": args,
                        "is_async": bool(is_async),
                        "file": path,
                    })
                    self.stats["methods"] += 1
                    self.stats["has_method"] += 1

        logger.info("Method catalog loaded", count=self.stats["methods"])

    def load_route_handlers(self):
        """Load API route handlers."""
        routes_file = INDEX_DIR / "route_handlers.txt"
        if not routes_file.exists():
            logger.warning("route_handlers.txt not found")
            return

        logger.info("Loading route handlers...")
        
        with open(routes_file, "r") as f:
            for line in f:
                # Parse: GET /api/health → handler_func() @ path/to/file.py
                match = re.match(r'^(GET|POST|PUT|DELETE|PATCH|WEBSOCKET)\s+(\S+)\s*→\s*(\w+)\(\)\s*@\s*(.+)$', line.strip())
                if match:
                    method, path, handler, file_path = match.groups()
                    
                    query = """
                    MERGE (r:RepoRoute {method: $method, path: $path})
                    SET r.full_path = $full_path
                    MERGE (f:RepoFunction {name: $handler, file: $file})
                    MERGE (r)-[:HANDLED_BY]->(f)
                    """
                    
                    self._run_query(query, {
                        "method": method,
                        "path": path,
                        "full_path": f"{method} {path}",
                        "handler": handler,
                        "file": file_path,
                    })
                    self.stats["routes"] += 1
                    self.stats["handled_by"] += 1

        logger.info("Route handlers loaded", count=self.stats["routes"])

    def load_function_signatures(self):
        """Load top-level function definitions."""
        funcs_file = INDEX_DIR / "function_signatures.txt"
        if not funcs_file.exists():
            logger.warning("function_signatures.txt not found")
            return

        logger.info("Loading function signatures...")
        
        # Only load first 500 to avoid timeout - methods are more important
        count = 0
        max_funcs = 500
        
        with open(funcs_file, "r") as f:
            for line in f:
                if count >= max_funcs:
                    break
                    
                # Parse: path/to/file.py::function_name(args) - docstring
                match = re.match(r'^([^:]+)::(\w+)\(([^)]*)\)\s*-\s*(.*)$', line.strip())
                if match:
                    path, func_name, args, docstring = match.groups()
                    
                    # Skip private functions and test functions
                    if func_name.startswith('_') or func_name.startswith('test_'):
                        continue
                    
                    query = """
                    MERGE (f:RepoFunction {name: $name, file: $file})
                    SET f.args = $args,
                        f.docstring = $docstring
                    WITH f
                    MERGE (file:RepoFile {path: $file})
                    MERGE (file)-[:CONTAINS]->(f)
                    """
                    
                    self._run_query(query, {
                        "name": func_name,
                        "file": path,
                        "args": args,
                        "docstring": docstring[:100] if docstring else "",
                    })
                    self.stats["functions"] += 1
                    count += 1

        logger.info("Function signatures loaded", count=self.stats["functions"])

    def load_pydantic_models(self):
        """Load Pydantic model definitions."""
        models_file = INDEX_DIR / "pydantic_models.txt"
        if not models_file.exists():
            logger.warning("pydantic_models.txt not found")
            return

        logger.info("Loading Pydantic models...")
        
        with open(models_file, "r") as f:
            for line in f:
                # Parse: ModelName @ path/to/file.py - docstring
                match = re.match(r'^(\w+)\s*@\s*([^\s-]+)\s*-?\s*(.*)$', line.strip())
                if match:
                    model_name, path, docstring = match.groups()
                    
                    query = """
                    MERGE (m:RepoPydanticModel {name: $name})
                    SET m.file = $file,
                        m.docstring = $docstring
                    WITH m
                    MERGE (f:RepoFile {path: $file})
                    MERGE (f)-[:CONTAINS]->(m)
                    """
                    
                    self._run_query(query, {
                        "name": model_name,
                        "file": path,
                        "docstring": docstring[:100] if docstring else "",
                    })
                    self.stats["pydantic_models"] += 1

        logger.info("Pydantic models loaded", count=self.stats["pydantic_models"])

    def load_all(self):
        """Load all index files into Neo4j."""
        if not self.connect():
            return False

        try:
            self.clear_repo_graph()
            self.create_indexes()
            
            # Load in order of importance
            self.load_file_metrics()
            self.load_class_definitions()
            self.load_inheritance_graph()
            self.load_method_catalog()
            self.load_route_handlers()
            self.load_pydantic_models()
            self.load_function_signatures()
            
            logger.info("=== Neo4j Load Complete ===")
            logger.info("Stats", **self.stats)
            
            return True
        finally:
            self.close()

    def print_summary(self):
        """Print loading summary."""
        logger.info("\n" + "=" * 60)
        logger.info("L9 REPO GRAPH - NEO4J LOAD SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  Files:           {self.stats['files']:,}")
        logger.info(f"  Classes:         {self.stats['classes']:,}")
        logger.info(f"  Functions:       {self.stats['functions']:,}")
        logger.info(f"  Methods:         {self.stats['methods']:,}")
        logger.info(f"  Routes:          {self.stats['routes']:,}")
        logger.info(f"  Pydantic Models: {self.stats['pydantic_models']:,}")
        logger.info("-" * 60)
        logger.info(f"  EXTENDS rels:    {self.stats['extends']:,}")
        logger.info(f"  HAS_METHOD rels: {self.stats['has_method']:,}")
        logger.info(f"  HANDLED_BY rels: {self.stats['handled_by']:,}")
        logger.info("=" * 60)
        
        if self.dry_run:
            logger.info("⚠️  DRY RUN - no data was loaded to Neo4j")
        else:
            logger.info("✅ Graph loaded to Neo4j")


def main():
    parser = argparse.ArgumentParser(
        description="Load L9 repository indexes into Neo4j graph database"
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
        "--uri",
        default=None,
        help="Neo4j URI (default: NEO4J_URI env or bolt://localhost:7687)",
    )
    parser.add_argument(
        "--database",
        default="neo4j",
        help="Neo4j database name (default: neo4j)",
    )
    parser.add_argument(
        "--vps",
        action="store_true",
        help="Load to VPS Neo4j (requires SSH tunnel: ssh -L 7687:127.0.0.1:7687 root@157.180.73.53)",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Load to local Docker Neo4j (default if no --vps)",
    )

    args = parser.parse_args()

    # Check index directory exists
    if not INDEX_DIR.exists():
        logger.error(f"Index directory not found: {INDEX_DIR}")
        logger.info("Run 'python3 tools/export_repo_indexes.py' first")
        sys.exit(1)

    # Determine Neo4j URI
    uri = args.uri
    if args.vps and not uri:
        # VPS Neo4j via SSH tunnel: ssh -L 7687:127.0.0.1:7687 root@157.180.73.53
        uri = "bolt://127.0.0.1:7687"
        logger.info("Using VPS Neo4j (via SSH tunnel)")
    elif args.local and not uri:
        uri = "bolt://localhost:7687"
        logger.info("Using local Docker Neo4j")
    
    loader = RepoGraphLoader(
        uri=uri,
        database=args.database,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    success = loader.load_all()
    loader.print_summary()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

