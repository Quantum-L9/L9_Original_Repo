#!/usr/bin/env python3.11
"""
L9 Agent Executor Verification Script

This script verifies that the agent_executor initialization fix is working correctly.
It checks:
1. All required imports are available
2. Kernel files exist and are valid
3. Agent registry can be created
4. AgentExecutorService can be instantiated
5. Health checks are in place
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Verify Agent Executor",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "agent_execution",
    "module_name": "verify_agent_executor",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import sys
import structlog
from pathlib import Path

# Add the repo root to the Python path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

def print_section(title):
    """Print a formatted section header."""
    logger.info(f"\n{'=' * 70}")
    logger.info(f"  {title}")
    logger.info(f"{'=' * 70}\n")

def check_imports():
    """Verify all critical imports."""
    print_section("1. Checking Critical Imports")
    
    all_ok = True
    
    imports_to_check = [
        ("core.agents.executor", "AgentExecutorService"),
        ("core.agents.kernel_registry", "create_kernel_aware_registry"),
        ("core.aios.runtime", "create_aios_runtime"),
        ("core.agents.schemas", "AgentTask"),
        ("core.agents.schemas", "TaskKind"),
        ("core.agents.schemas", "ExecutionResult"),
    ]
    
    for module_name, class_name in imports_to_check:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            logger.info(f"✓ {module_name}.{class_name}")
        except ImportError as e:
            logger.error(f"✗ {module_name}.{class_name}: Import failed - {e}")
            all_ok = False
        except AttributeError as e:
            logger.info(f"✗ {module_name}.{class_name}: Attribute not found - {e}")
            all_ok = False
        except Exception as e:
            logger.error(f"✗ {module_name}.{class_name}: Unexpected error - {e}")
            all_ok = False
    
    return all_ok

def check_kernel_files():
    """Verify kernel files exist and are readable."""
    print_section("2. Checking Kernel Files")
    
    kernel_dir = repo_root / "private" / "kernels" / "00_system"
    
    if not kernel_dir.exists():
        logger.info(f"✗ Kernel directory not found: {kernel_dir}")
        return False
    
    expected_kernels = [
        "01_master_kernel.yaml",
        "02_identity_kernel.yaml",
        "03_cognitive_kernel.yaml",
        "04_behavioral_kernel.yaml",
        "05_memory_kernel.yaml",
        "06_worldmodel_kernel.yaml",
        "07_execution_kernel.yaml",
        "08_safety_kernel.yaml",
        "09_developer_kernel.yaml",
        "10_packet_protocol_kernel.yaml",
    ]
    
    all_ok = True
    for kernel_file in expected_kernels:
        kernel_path = kernel_dir / kernel_file
        if kernel_path.exists():
            logger.info(f"✓ {kernel_file}")
        else:
            logger.info(f"✗ {kernel_file}: Not found")
            all_ok = False
    
    return all_ok

def check_agent_registry():
    """Verify agent registry can be created."""
    print_section("3. Checking Agent Registry Creation")
    
    try:
        from core.agents.kernel_registry import create_kernel_aware_registry
        
        logger.info("Attempting to create kernel-aware agent registry...")
        agent_registry = create_kernel_aware_registry()
        
        logger.info("✓ Agent registry created successfully")
        logger.info(f"  Kernel state: {agent_registry.get_kernel_state()}")
        
        # Try to get a test agent config
        try:
            config = agent_registry.get_agent_config("l-cto")
            logger.info("✓ Retrieved config for 'l-cto' agent")
            logger.info(f"  Agent ID: {config.agent_id}")
            logger.info(f"  Personality ID: {config.personality_id}")
        except Exception as e:
            logger.info(f"⚠ Could not retrieve 'l-cto' config: {e}")
        
        return True
        
    except RuntimeError as e:
        logger.error(f"✗ Kernel loading failed: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_executor_service():
    """Verify AgentExecutorService can be instantiated."""
    print_section("4. Checking AgentExecutorService Instantiation")
    
    try:
        from core.agents.executor import AgentExecutorService
        from core.agents.kernel_registry import create_kernel_aware_registry
        
        # Create minimal dependencies
        logger.info("Creating agent registry...")
        agent_registry = create_kernel_aware_registry()
        
        logger.info("Creating AgentExecutorService...")
        executor = AgentExecutorService(
            aios_runtime=None,  # Can be None for this test
            tool_registry=None,  # Can be None for this test
            substrate_service=None,  # Can be None for this test
            agent_registry=agent_registry,
        )
        
        logger.info("✓ AgentExecutorService created successfully")
        logger.info(f"  Type: {type(executor).__name__}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to create AgentExecutorService: {e}")
        import traceback
        traceback.print_exc()
        return False

logger = structlog.get_logger(__name__)
def check_health_checks():
    """Verify health check code is present in server.py."""
    print_section("5. Checking Health Check Implementation")
    
    server_file = repo_root / "api" / "server.py"
    
    if not server_file.exists():
        logger.info(f"✗ server.py not found: {server_file}")
        return False
    
    with open(server_file, 'r') as f:
        content = f.read()
    
    checks = [
        ("CRITICAL HEALTH CHECK", "Health check section"),
        ("Agent Executor required for new Slack routing", "Fail-fast error message"),
        ("L9_ENABLE_LEGACY_SLACK_ROUTER", "Feature flag check"),
        ("RuntimeError", "Startup failure on missing executor"),
    ]
    
    all_ok = True
    for search_str, description in checks:
        if search_str in content:
            logger.info(f"✓ {description}: Found")
        else:
            logger.info(f"✗ {description}: Not found")
            all_ok = False
    
    return all_ok

def main():
    """Run all verification checks."""
    logger.info("\n" + "=" * 70)
    logger.info("  L9 Agent Executor Verification")
    logger.info("=" * 70)
    
    results = {
        "Imports": check_imports(),
        "Kernel Files": check_kernel_files(),
        "Agent Registry": check_agent_registry(),
        "Executor Service": check_executor_service(),
        "Health Checks": check_health_checks(),
    }
    
    # Summary
    print_section("Verification Summary")
    
    all_passed = True
    for check_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status:10} {check_name}")
        if not passed:
            all_passed = False
    
    logger.info("\n" + "=" * 70)
    if all_passed:
        logger.info("  ✓ ALL CHECKS PASSED")
        logger.info("  The agent_executor fix has been successfully applied.")
        logger.info("=" * 70 + "\n")
        return 0
    else:
        logger.error("  ✗ SOME CHECKS FAILED")
        logger.error("  Please review the errors above and fix the issues.")
        logger.info("=" * 70 + "\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.agents.executor", "core.agents.kernel_registry"],
    "tags": ["agent-execution", "api", "cli", "filesystem", "logging", "messaging", "operations", "testing", "tracing"],
    "keywords": ["agent", "check", "checks", "executor", "files", "health", "imports", "kernel"],
    "business_value": "This script verifies that the agent_executor initialization fix is working correctly. 1. All required imports are available 2. Kernel files exist and are valid 3. Agent registry can be created 4. Agen",
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
