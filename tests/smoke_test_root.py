#!/usr/bin/env python3
"""
L9 Audit Smoke Test
===================

Minimal runtime smoke test to verify server starts and core wiring is functional.
This test does NOT require a running database - it validates import chains and
basic functionality only.

Usage:
    python tests/smoke_test_root.py

For full DB-connected tests, set MEMORY_DSN and run:
    python dev/audit/smoke_test.py --with-db
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Smoke Test Root",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:23:43Z",
    "updated_at": "2026-01-14T15:02:45Z",
    "layer": "operations",
    "domain": "tests",
    "module_name": "smoke_test_root",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import sys
import asyncio
import logging
import structlog
from pathlib import Path

# Ensure repo root is in path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = structlog.get_logger(__name__)


class SmokeTestResults:
    def __init__(self):
        self.passed = []
        self.failed = []

    def record(self, name: str, success: bool, error: str = ""):
        if success:
            self.passed.append(name)
            logger.info(f"PASS: {name}")
        else:
            self.failed.append((name, error))
            logger.error(f"FAIL: {name} - {error}")

    def summary(self) -> bool:
        logger.info("=" * 60)
        logger.info(f"PASSED: {len(self.passed)}")
        logger.info(f"FAILED: {len(self.failed)}")
        if self.failed:
            logger.error("Failed tests:")
            for name, err in self.failed:
                logger.error(f"  - {name}: {err}")
        return len(self.failed) == 0


def test_compileall() -> tuple[bool, str]:
    """Test that all Python files compile (excluding venv/node_modules)."""
    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "compileall",
            "-q",
            "-x",
            "venv|node_modules|__pycache__|.git",
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, result.stderr[:200] if result.stderr else "Compilation errors (see output)"
    return True, ""


def test_core_imports() -> tuple[bool, str]:
    """Test that core imports work without circular import issues."""
    try:
        # Orchestrators (no DB required)
        from orchestrators import MetaOrchestrator, WorldModelOrchestrator
        from world_model.runtime import WorldModelRuntime

        # Memory imports may need DB drivers - skip gracefully
        try:
            from core.schemas import PacketEnvelope, PacketEnvelopeIn
            from memory.substrate_dag import SubstrateDAG
            from memory.substrate_service import MemorySubstrateService
        except ImportError as e:
            if "asyncpg" in str(e) or "psycopg" in str(e):
                pass  # DB drivers not installed, OK for smoke test
            else:
                raise

        return True, ""
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


def test_langgraph_not_shadowed() -> tuple[bool, str]:
    """Test that langgraph library is not shadowed by local package."""
    try:
        from langgraph.graph import StateGraph, END

        # Verify it's the actual library, not our local shim
        import langgraph

        # langgraph is a namespace package, so __file__ may be None
        # Instead, check that we can access the graph module
        if hasattr(langgraph, "__path__"):
            for p in langgraph.__path__:
                if "l9" in p.lower() and "venv" not in p.lower():
                    return False, f"langgraph is local package: {p}"
        return True, ""
    except ImportError:
        # langgraph not installed - that's OK for smoke test, just skip
        return True, "langgraph not installed (skipped)"


def test_server_module_imports() -> tuple[bool, str]:
    """Test that server module can be imported (without DB connection)."""
    try:
        # Core schemas (no DB required)

        # API modules may need DB drivers
        try:
            from api.memory.router import router as memory_router
            from api import os_routes, agent_routes
        except ImportError as e:
            if "asyncpg" in str(e) or "psycopg" in str(e):
                pass  # DB drivers not installed, OK for smoke test
            else:
                raise

        return True, ""
    except Exception as e:
        return False, str(e)


def test_migrations_exist() -> tuple[bool, str]:
    """Test that migrations directory exists and has SQL files."""
    migrations_dir = REPO_ROOT / "migrations"
    if not migrations_dir.exists():
        return False, "migrations/ directory not found"

    sql_files = list(migrations_dir.glob("*.sql"))
    if len(sql_files) == 0:
        return False, "No .sql files in migrations/"

    return True, f"{len(sql_files)} migration files found"


def test_core_modules_exist() -> tuple[bool, str]:
    """Test that core module directories exist."""
    required_dirs = ["memory", "orchestrators", "world_model", "api", "email_agent"]
    missing = [d for d in required_dirs if not (REPO_ROOT / d).exists()]

    if missing:
        return False, f"Missing directories: {missing}"

    # Check for __init__.py in each
    missing_init = [d for d in required_dirs if not (REPO_ROOT / d / "__init__.py").exists()]
    if missing_init:
        return False, f"Missing __init__.py in: {missing_init}"

    return True, ""


def test_no_nested_repos() -> tuple[bool, str]:
    """Test that there are no nested .git directories within project."""
    import subprocess

    result = subprocess.run(
        [
            "find",
            str(REPO_ROOT),
            "-type",
            "d",
            "-name",
            ".git",
            "-not",
            "-path",
            str(REPO_ROOT / ".git"),
        ],
        capture_output=True,
        text=True,
    )
    nested_dirs = [
        d for d in result.stdout.strip().split("\n") if d and d.startswith(str(REPO_ROOT))
    ]

    if nested_dirs:
        return False, f"Nested repos found: {nested_dirs}"

    return True, ""


def test_entrypoints_exist() -> tuple[bool, str]:
    """Test that entrypoints listed in entrypoints.txt exist."""
    entrypoints_file = REPO_ROOT / "entrypoints.txt"
    if not entrypoints_file.exists():
        return False, "entrypoints.txt not found"

    missing = []
    for line in entrypoints_file.read_text().strip().split("\n"):
        # Only check lines that are actual file paths (not indented, end with .py, not comments)
        if line and not line.startswith("#") and not line.startswith(" ") and line.endswith(".py"):
            path = REPO_ROOT / line
            if not path.exists():
                missing.append(line)

    if missing:
        return False, f"Missing entrypoints: {missing}"

    return True, ""


async def test_memory_pipeline_dry_run() -> tuple[bool, str]:
    """Test that memory pipeline components can be instantiated."""
    try:
        from uuid import uuid4
        from core.schemas import PacketEnvelope, PacketEnvelopeIn

        # Create a test packet
        packet = PacketEnvelopeIn(
            packet_type="smoke_test",
            payload={"test": True, "source": "audit_smoke_test"},
            metadata={"agent": "smoke_tester"},
        )

        # Create envelope with proper UUID
        envelope = PacketEnvelope(
            packet_id=uuid4(),
            packet_type=packet.packet_type,
            payload=packet.payload,
            metadata=packet.metadata,
        )

        # Try to import SubstrateDAG if langgraph is available
        try:
            from memory.substrate_dag import SubstrateDAG

            # Create DAG without services (dry run)
            dag = SubstrateDAG(repository=None, semantic_service=None)
        except ImportError:
            # langgraph not installed, skip DAG instantiation
            pass

        return True, ""
    except Exception as e:
        return False, str(e)


async def test_world_model_instantiation() -> tuple[bool, str]:
    """Test that world model can be instantiated."""
    try:
        from world_model.runtime import WorldModelRuntime

        # Create without DB connection
        runtime = WorldModelRuntime()

        return True, ""
    except Exception as e:
        return False, str(e)


def main():
    results = SmokeTestResults()

    logger.info("=" * 60)
    logger.info("L9 AUDIT SMOKE TEST")
    logger.info("=" * 60)

    # Sync tests
    result, err = test_compileall()
    results.record("compileall", result, err)

    result, err = test_no_nested_repos()
    results.record("no_nested_repos", result, err)

    result, err = test_entrypoints_exist()
    results.record("entrypoints_exist", result, err)

    result, err = test_migrations_exist()
    results.record("migrations_exist", result, err)

    result, err = test_core_modules_exist()
    results.record("core_modules_exist", result, err)

    result, err = test_langgraph_not_shadowed()
    results.record("langgraph_not_shadowed", result, err)

    result, err = test_core_imports()
    results.record("core_imports", result, err)

    result, err = test_server_module_imports()
    results.record("server_module_imports", result, err)

    # Async tests
    async def run_async_tests():
        result, err = await test_memory_pipeline_dry_run()
        results.record("memory_pipeline_dry_run", result, err)

        result, err = await test_world_model_instantiation()
        results.record("world_model_instantiation", result, err)

    asyncio.run(run_async_tests())

    # Summary
    success = results.summary()

    if success:
        print("\n" + "=" * 60)
        print("ALL SMOKE TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("SMOKE TESTS FAILED - SEE ERRORS ABOVE")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TES-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "api.memory.router",
        "core.schemas",
        "memory.substrate_dag",
        "memory.substrate_service",
    ],
    "tags": [
        "api",
        "async",
        "caching",
        "filesystem",
        "logging",
        "messaging",
        "migration",
        "operations",
        "subprocess",
        "test",
    ],
    "keywords": [
        "async",
        "compileall",
        "core",
        "dry",
        "entrypoints",
        "exist",
        "imports",
        "instantiation",
    ],
    "business_value": "This test does NOT require a running database - it validates import chains and basic functionality only. python tests/smoke_test_root.py python dev/audit/smoke_test.py --with-db",
    "last_modified": "2026-01-14T15:02:45Z",
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
