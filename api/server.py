"""
L9 API Server
=============

FastAPI application for L9 Phase 2 Secure AI OS.

Provides:
- REST API endpoints for OS, agent, and memory operations
- WebSocket endpoint for real-time agent communication
- World model API (optional, v1.1.0+)

Version: 0.5.0 (Research Factory Integration)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Server",
    "module_version": "0.5.0 (Research Factory Integration)",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-18T02:40:22Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "server",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [
            "GET /",
            "GET /health",
            "GET /health/startup",
            "POST /kernels/reload",
            "GET /health/neo4j",
            "GET /health/services",
            "POST /lchat",
            "POST /chat",
        ],
        "datasources": ["HTTP API", "Neo4j", "OpenAI API", "Redis", "Slack API"],
        "memory_layers": ["working_memory", "semantic_memory"],
        "imported_by": [
            "api.routes.gmp_learning",
            "scripts.audit.find_dead_code",
            "tests.api.test_server_health",
            "tests.api.test_websocket_auth",
            "tests.integration.test_api_agent_integration",
            "tests.integration.test_api_memory_integration",
            "tests.integration.test_kernel_hot_reload",
            "tests.test_imports",
        ],
    },
}
# ============================================================================

import os
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime, timezone

import structlog

from config.settings import settings

# Initialize logger early for import error handling
logger = structlog.get_logger(__name__)
from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from openai import OpenAI
from pydantic import BaseModel

import api.agent_routes as agent_routes
import api.db as db
from api.auth import verify_api_key

# Router Auto-Registration (Phase 2 Auto-Wiring)
from api.routes.registry import discover_routers, router_registry
from core.decorators import must_stay_async

# Event Type Auto-Registration (Phase 2 Auto-Wiring)
from core.event_type_registry import get_all_event_types, register_core_event_types

# Singleton Auto-Registration (Phase 2 Auto-Wiring)
from core.singleton_auto_registry import (
    discover_singleton_services,
    wire_singletons_to_registry,
)
from core.singleton_registry import get_singleton_registry

# Background Task Registry (Auto-Wiring)
from runtime.background_tasks import BackgroundTaskRegistry

# MCP Server Auto-Registration (Phase 1 Auto-Wiring - GMP-95)
from runtime.mcp_server_registry import (
    get_all_mcp_servers,
)

# Tool Executor Auto-Registration (Phase 1 Auto-Wiring - GMP-95)
from runtime.tool_registry import (
    get_tool_executors,
)

# Telemetry / Prometheus metrics
try:
    from prometheus_client import make_asgi_app as prometheus_make_asgi_app

    from telemetry.memory_metrics import PROMETHEUS_AVAILABLE, init_metrics

    _has_prometheus = PROMETHEUS_AVAILABLE
except ImportError:
    _has_prometheus = False

    def init_metrics():
        return False


# World Model API availability (auto-registered via router_registry)
_has_world_model = True

# Optional: Slack Adapter (v2.0+)
try:
    import httpx

    from api.slack_adapter import SlackRequestValidator
    from api.slack_client import SlackAPIClient

    _has_slack = True
except ImportError:
    _has_slack = False

# Optional: Quantum Research Factory (v2.1+)
try:
    from services.research.graph_runtime import init_runtime, shutdown_runtime
    from services.research.research_api import router as research_router

    _has_research = True
except ImportError:
    _has_research = False

# Optional: World Model Runtime (v2.5+)
try:
    from world_model.runtime import (
        RuntimeConfig,
        WorldModelRuntime,
        create_runtime_with_substrate,
        get_or_create_runtime,
    )

    _has_world_model_runtime = True
except ImportError:
    _has_world_model_runtime = False

# Optional: Agent Executor (v2.2+)
try:
    from core.agents.executor import AgentExecutorService
    from core.agents.schemas import (
        AgentConfig,
        AgentTask,
        AgentType,
        DuplicateTaskResponse,
        ExecutionResult,
        ToolBinding,
    )

    _has_agent_executor = True
except ImportError as e:
    logger.error(f"Failed to import AgentExecutorService: {e}", exc_info=True)
    _has_agent_executor = False
except Exception as e:
    logger.error(f"Unexpected error importing AgentExecutorService: {e}", exc_info=True)
    _has_agent_executor = False

# Optional: AIOS Runtime (v2.2+)
try:
    from core.aios.runtime import AIOSRuntime, create_aios_runtime

    _has_aios_runtime = True
except ImportError as e:
    logger.debug(f"AIOS Runtime not available: {e}")
    _has_aios_runtime = False
except Exception as e:
    logger.error(f"Unexpected error importing AIOS Runtime: {e}", exc_info=True)
    _has_aios_runtime = False

# Optional: Tool Registry Adapter (v2.2+)
try:
    from core.tools.registry_adapter import (
        ExecutorToolRegistry,
        create_executor_tool_registry,
    )

    _has_tool_registry = True
except ImportError as e:
    logger.debug(f"Tool Registry not available: {e}")
    _has_tool_registry = False
except Exception as e:
    logger.error(f"Unexpected error importing Tool Registry: {e}", exc_info=True)
    _has_tool_registry = False

# Tools Router availability (auto-registered via router_registry)
_has_tools_router = True

# Optional: Reasoning Orchestrator (v3.5+ / Stage 2.6 Phase 2)
try:
    from orchestrators.reasoning.orchestrator import ReasoningOrchestrator

    _has_reasoning = True
except ImportError:
    _has_reasoning = False

# Optional: Pattern Orchestrator (v4.0+ / Agent Pattern System)
try:
    from orchestrators.pattern import CellAgentAdapter, PatternOrchestrator

    _has_pattern = True
except ImportError:
    _has_pattern = False

# Optional: ResearchSwarm Orchestrator (v3.5+ / Stage 2.6 Phase 3)
try:
    from orchestrators.research_swarm.orchestrator import ResearchSwarmOrchestrator

    _has_research_swarm = True
except ImportError:
    _has_research_swarm = False

# Optional: ResearchAgent (Perplexity-based unified research-to-code agent)
try:
    from agents.research_agent_impl import ResearchAgent, create_research_agent

    _has_research_agent = True
except ImportError as e:
    logger.debug(f"ResearchAgent not available: {e}")
    _has_research_agent = False

# Optional: ReflectionAgent (Meta-reasoning and self-improvement agent)
try:
    from agents.reflection_agent import ReflectionAgent, create_reflection_agent

    _has_reflection_agent = True
except ImportError as e:
    logger.debug(f"ReflectionAgent not available: {e}")
    _has_reflection_agent = False

# Optional: Cursor Executor (GMP-48)
try:
    from agents.cursor.integrations.cursor_executor import CursorExecutor
    from agents.cursor.integrations.cursor_gateway import CursorMemoryGateway
    from agents.cursor.integrations.cursor_langgraph import build_cursor_langgraph
    from config.cursor_langgraph_config import get_cursor_langgraph_config
    from core.governance.approval_manager import ApprovalManager
    from memory.checkpoint.cursor_checkpoint_manager import CursorCheckpointManager
    from memory.checkpoint.postgres_saver import L9PostgresSaver

    _has_cursor_executor = True
except ImportError as e:
    logger.debug(f"Cursor Executor not available: {e}")
    _has_cursor_executor = False

# Optional: Governance Engine (v2.4+)
try:
    from core.governance.engine import GovernanceEngineService, create_governance_engine
    from core.governance.loader import InvalidPolicyError, PolicyLoadError

    _has_governance = True
except ImportError:
    _has_governance = False

# Optional: Symbolic Computation Service (v2.9+ / GMP-SYMPY-TASK4)
# DISABLED: sympy commented out in requirements-production.txt to reduce VPS bloat
_has_symbolic = False
# try:
#     from services.symbolic_computation.api.routes import router as symbolic_router
#     _has_symbolic = True
# except Exception:
#     _has_symbolic = False

# Optional: Kernel-Aware Agent Registry (v2.5+)
try:
    from core.agents.kernel_registry import (
        KernelAwareAgentRegistry,
        create_kernel_aware_registry,
    )

    _has_kernel_registry = True
except ImportError as e:
    logger.debug(f"Kernel Registry not available: {e}")
    _has_kernel_registry = False
except Exception as e:
    logger.error(f"Unexpected error importing Kernel Registry: {e}", exc_info=True)
    _has_kernel_registry = False

# Optional: Session Startup (v3.4+ / GMP-KERNEL-BOOT)
try:
    # Try new location first, fallback to old location
    try:
        import sys
        from pathlib import Path

        startup_path = Path(__file__).parent.parent / ".cursor-commands" / "startup"
        if startup_path.exists():
            sys.path.insert(0, str(startup_path.parent))
            from startup.session_startup import SessionStartup, StartupResult
        else:
            from core.governance.session_startup import SessionStartup, StartupResult
    except ImportError:
        from core.governance.session_startup import SessionStartup, StartupResult

    _has_session_startup = True
except ImportError as e:
    logger.debug(f"Session Startup not available: {e}")
    _has_session_startup = False
except Exception as e:
    logger.error(f"Unexpected error importing Session Startup: {e}", exc_info=True)
    _has_session_startup = False

# Optional: Agent Bootstrap Orchestrator (v3.0+ Paradigm Shift)
try:
    from core.agents.bootstrap import AgentBootstrapOrchestrator

    _has_bootstrap = True
except ImportError:
    _has_bootstrap = False

# Feature flags from centralized settings (config/settings.py)
L9_NEW_AGENT_INIT = settings.l9_new_agent_init
L9_STAGE3_MODULES = settings.l9_stage3_modules
L9_GRAPH_AGENT_STATE = settings.l9_graph_agent_state

# Optional: Graph-Backed Agent State (v3.2+ Stage 5)
try:
    from core.agents.graph_state import (
        AgentGraphLoader,
        GraphHydrator,
        bootstrap_l_graph,
    )
    from core.tools.agent_self_modify import (
        AgentSelfModifyTool,
        create_self_modify_tool,
    )
    from services.research.graph_persistence import (
        ResearchGraphPersistence,
        create_graph_persistence,
        init_graph_persistence,
    )

    _has_graph_agent_state = True
    _has_research_graph_persistence = True
except ImportError:
    _has_graph_agent_state = False
    _has_research_graph_persistence = False

# Optional: Five-Tier Observability (v3.3+ GMP-OBS-DEPLOY)
L9_OBSERVABILITY = settings.l9_observability
try:
    from core.observability.l9_integration import (
        instrument_agent_executor,
        instrument_governance_engine,
        instrument_memory_substrate,
        instrument_tool_registry,
    )
    from core.observability.service import (
        ObservabilityService,
        initialize_observability,
    )

    _has_observability = True
except ImportError:
    _has_observability = False
    L9_OBSERVABILITY = False

# Optional: ToolAuditService (v3.1+ Stage 3)
try:
    from core.tools.tool_audit import ToolAuditService

    _has_tool_audit_service = True
except ImportError:
    _has_tool_audit_service = False

# Optional: Event Queue (v3.1+ Stage 3)
try:
    from core.coordination.event_queue import EventQueue, init_event_driven_coordination

    _has_event_queue = True
except ImportError:
    _has_event_queue = False

# Optional: Virtual Context Manager (v3.1+ Stage 3)
try:
    from core.memory.virtual_context import VirtualContextManager

    _has_virtual_context = True
except ImportError:
    _has_virtual_context = False

# Optional: Evaluator (v3.1+ Stage 3)
try:
    from core.evaluation import Evaluator, load_default_eval_sets

    _has_evaluator = True
except ImportError:
    _has_evaluator = False

# Email Agent availability (auto-registered via router_registry if enabled)
# Toggleable via EMAIL_AGENT_ENABLED=false in .env
_has_email_agent = settings.email_agent_enabled
if not _has_email_agent:
    logger.info("Email Agent DISABLED via EMAIL_AGENT_ENABLED=false")

# Note: Slack handled by api/routes/slack.py → memory/slack_ingest.py

# Optional: Housekeeping Engine (v2.4+)
try:
    from memory.housekeeping import HousekeepingEngine, init_housekeeping_engine

    _has_housekeeping = True
except ImportError:
    _has_housekeeping = False

# Optional: Bayesian Calibration Services (v4.0+ / Bayesian Upgrade)
try:
    from core.bayesian import BayesianKernel, get_bayesian_kernel
    from core.calibration import (
        CalibrationService,
        GatingPolicyService,
        load_calibration_config,
        load_gating_config,
    )

    _has_calibration = True
except ImportError as e:
    logger.debug(f"Calibration services not available: {e}")
    _has_calibration = False

# Optional: Mac Agent API (from centralized settings)
_has_mac_agent = settings.mac_agent_enabled

# Optional: WABA/WhatsApp (from centralized settings)
_has_waba = settings.waba_enabled

from memory.agent_persistence import AgentPersistenceService

# Memory system imports
from memory.migration_runner import run_migrations
from memory.state_manager import MemoryStateManager
from memory.substrate_service import close_service, init_service
from memory.timeline_service import TimelineService

# Integration settings
logger = structlog.get_logger(__name__)

# Development mode flag (from centralized settings)
LOCAL_DEV = settings.local_dev

# GMP v2.0 Learning Engine (global, initialized in lifespan if enabled)
gmp_learning_engine = None  # Type: Optional[GMPMetaLearningEngine]

# Stage 5: Predictive Memory Warming (global, initialized in lifespan if enabled)
memory_warming_service = None  # Type: Optional[MemoryWarmingService]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Handles startup (migrations + memory init) and shutdown.
    """
    # ========================================================================
    # STARTUP: Ensure bootstrap has completed (fail-fast)
    # ========================================================================
    try:
        from api.startup_guard import ensure_bootstrap

        await ensure_bootstrap()
        logger.info("Bootstrap verification passed")
    except Exception as e:
        logger.warning(f"Bootstrap check skipped or failed: {e}")
        # Note: In production, you may want to make this fatal
        # raise RuntimeError(f"Bootstrap not completed: {e}")

    # ========================================================================
    # STARTUP: Validate required environment variables (fail-fast)
    # ========================================================================
    required_env_vars = ["OPENAI_API_KEY"]  # MEMORY_DSN is optional, SLACK is optional
    recommended_env_vars = ["MEMORY_DSN", "SLACK_BOT_TOKEN"]

    missing_required = [v for v in required_env_vars if not os.getenv(v)]
    if missing_required:
        logger.critical(
            "FATAL: Missing required environment variables: %s. L9 cannot start.",
            missing_required,
        )
        raise RuntimeError(f"Missing required env vars: {missing_required}")

    missing_recommended = [v for v in recommended_env_vars if not os.getenv(v)]
    if missing_recommended:
        logger.warning(
            "Missing recommended env vars (some features disabled): %s",
            missing_recommended,
        )

    # ========================================================================
    # STARTUP: Run migrations and initialize memory service
    # ========================================================================
    logger.info("Starting L9 API server...")

    # ------------------------------------------------------------------------
    # GMP-45: ModuleRegistry (runtime truth)
    # ------------------------------------------------------------------------
    try:
        from core.moduleregistry import ModuleDefinition, ModuleRegistry

        module_registry = ModuleRegistry()
        module_registry.register(
            ModuleDefinition(
                module_id="memory",
                display_name="Memory Substrate",
                route_prefix="/api/v1/memory",
            )
        )
        module_registry.register(
            ModuleDefinition(
                module_id="tools",
                display_name="Tools Router",
                route_prefix="/tools",
            )
        )
        module_registry.register(
            ModuleDefinition(
                module_id="slack",
                display_name="Slack Adapter",
                route_prefix="/slack",
            )
        )
        module_registry.register(
            ModuleDefinition(
                module_id="research_swarm",
                display_name="Research Swarm",
                route_prefix="/research/swarm",
            )
        )
        module_registry.register(
            ModuleDefinition(
                module_id="world_model",
                display_name="World Model",
                route_prefix="/worldmodel",
            )
        )

        app.state.module_registry = module_registry
        logger.info("ModuleRegistry ready (GMP-45)")
    except Exception as e:
        # Fail-fast contract: ModuleRegistry is a required wiring primitive for E2E observability.
        # Do not silently degrade; server must not start in a half-working state.
        app.state.module_registry = None
        logger.critical("FATAL: ModuleRegistry init failed: %s", str(e), exc_info=True)
        raise RuntimeError(f"ModuleRegistry init failed: {e}") from e

    # ------------------------------------------------------------------------
    # Singleton Auto-Registration (Phase 2 Auto-Wiring)
    # Discover and wire @register_singleton decorated services
    # ------------------------------------------------------------------------
    try:
        # Discover singletons in packages that may have @register_singleton decorators
        discovered_count = 0
        for package in ["runtime", "memory", "config", "services.research", "agents"]:
            try:
                count = discover_singleton_services(package)
                discovered_count += count
            except Exception as pkg_err:
                logger.debug(f"Singleton discovery skipped for {package}: {pkg_err}")

        # Wire discovered singletons to the main registry
        registry = get_singleton_registry()
        wired_count = wire_singletons_to_registry(registry)

        if wired_count > 0:
            logger.info(
                "Singleton auto-registration complete",
                discovered_modules=discovered_count,
                wired_singletons=wired_count,
            )
        else:
            logger.info(
                "No @register_singleton services found — using legacy registration only"
            )
    except Exception as e:
        # Non-fatal: system will continue with manually registered singletons
        logger.warning(f"Singleton auto-registration failed: {e}")

    # ------------------------------------------------------------------------
    # Event Type Auto-Registration (Phase 2 Auto-Wiring)
    # Register core event types for backward compatibility + dynamic extension
    # ------------------------------------------------------------------------
    try:
        register_core_event_types()
        event_types = get_all_event_types()
        logger.info(
            "Event type auto-registration complete",
            registered_types=len(event_types),
            categories=list({et.category for et in event_types.values()}),
        )
    except Exception as e:
        # Non-fatal: event types can still be registered dynamically later
        logger.warning(f"Event type auto-registration failed: {e}")

    # ------------------------------------------------------------------------
    # Background Task Registry (Auto-Wiring)
    # Centralized management of all periodic background tasks
    # ------------------------------------------------------------------------
    bg_tasks = BackgroundTaskRegistry()
    app.state.background_tasks = bg_tasks
    logger.info("BackgroundTaskRegistry initialized")

    # ------------------------------------------------------------------------
    # Tool Executor Auto-Registration (GMP-95 Auto-Wiring)
    # Register all tools: legacy TOOL_EXECUTORS + extension modules + @register_tool
    # ------------------------------------------------------------------------
    try:
        from runtime.tool_registry import (
            discover_tools,
            get_tool_snapshot,
            register_extension_tool_executors,
        )

        # 1. All tools now use @register_tool decorator - legacy bridge removed
        # 2. Register extension tools (research, reflection)
        extension_count = register_extension_tool_executors()

        # 3. Discover any new @register_tool decorated functions
        for package in ["runtime", "core.tools"]:
            try:
                discover_tools(package)
            except Exception as pkg_err:
                logger.debug(f"Tool discovery skipped for {package}: {pkg_err}")

        snapshot = get_tool_snapshot()
        logger.info(
            "Tool executor auto-registration complete",
            extension_tools=extension_count,
            total_tools=snapshot["component_count"],
        )
    except Exception as e:
        # Non-fatal: tools can still be accessed via legacy TOOL_EXECUTORS directly
        logger.warning(f"Tool executor auto-registration failed: {e}")

    # ------------------------------------------------------------------------
    # MCP Server Auto-Registration (GMP-95 Auto-Wiring)
    # Load MCP server configs from config/mcp_servers.yaml
    # ------------------------------------------------------------------------
    try:
        from pathlib import Path

        from runtime.mcp_server_registry import (
            get_all_mcp_servers,
            load_mcp_servers_from_yaml,
        )

        mcp_config_path = Path(__file__).parent.parent / "config" / "mcp_servers.yaml"
        if mcp_config_path.exists():
            loaded_count = load_mcp_servers_from_yaml(mcp_config_path)
            servers = get_all_mcp_servers()
            enabled_count = sum(1 for s in servers.values() if s.enabled)
            logger.info(
                "MCP server auto-registration complete",
                servers_loaded=loaded_count,
                servers_enabled=enabled_count,
            )
        else:
            logger.debug("No MCP server config found at config/mcp_servers.yaml")
    except Exception as e:
        # Non-fatal: MCP servers can still be configured manually
        logger.warning(f"MCP server auto-registration failed: {e}")

    # ------------------------------------------------------------------------
    # Agent Auto-Registration (GMP-95 Auto-Wiring)
    # Register all agents: legacy exports + @register_agent decorated
    # ------------------------------------------------------------------------
    try:
        from agents.agent_registry import (
            discover_agents,
            get_agent_snapshot,
            register_legacy_agents,
        )

        # 1. Register legacy agent classes
        legacy_agent_count = register_legacy_agents()

        # 2. Discover any new @register_agent decorated classes
        discover_agents("agents")

        snapshot = get_agent_snapshot()
        logger.info(
            "Agent auto-registration complete",
            legacy_agents=legacy_agent_count,
            total_agents=snapshot["component_count"],
        )
    except Exception as e:
        logger.warning(f"Agent auto-registration failed: {e}")

    # ------------------------------------------------------------------------
    # Orchestrator Auto-Registration (GMP-95 Auto-Wiring)
    # Register all orchestrators: legacy exports + @register_orchestrator decorated
    # ------------------------------------------------------------------------
    try:
        from orchestrators.orchestrator_registry import (
            discover_orchestrators,
            get_orchestrator_snapshot,
            register_legacy_orchestrators,
        )

        # 1. Register legacy orchestrator classes
        legacy_orch_count = register_legacy_orchestrators()

        # 2. Discover any new @register_orchestrator decorated classes
        discover_orchestrators("orchestrators")

        snapshot = get_orchestrator_snapshot()
        logger.info(
            "Orchestrator auto-registration complete",
            legacy_orchestrators=legacy_orch_count,
            total_orchestrators=snapshot["component_count"],
        )
    except Exception as e:
        logger.warning(f"Orchestrator auto-registration failed: {e}")

    # ------------------------------------------------------------------------
    # Collaborative Cell Auto-Registration (GMP-95 Auto-Wiring)
    # Register all cells: legacy exports + @register_cell decorated
    # ------------------------------------------------------------------------
    try:
        from collaborative_cells.cell_registry import (
            discover_cells,
            get_cell_snapshot,
            register_legacy_cells,
        )

        # 1. Register legacy cell classes
        legacy_cell_count = register_legacy_cells()

        # 2. Discover any new @register_cell decorated classes
        discover_cells("collaborative_cells")

        snapshot = get_cell_snapshot()
        logger.info(
            "Cell auto-registration complete",
            legacy_cells=legacy_cell_count,
            total_cells=snapshot["component_count"],
        )
    except Exception as e:
        logger.warning(f"Cell auto-registration failed: {e}")

    # ------------------------------------------------------------------------
    # Policy Source Auto-Registration (GMP-95 Auto-Wiring)
    # Register default policy directories
    # ------------------------------------------------------------------------
    try:
        from core.governance.policy_registry import (
            get_policy_source_snapshot,
            register_default_policy_sources,
        )

        # Register default policy directories
        policy_source_count = register_default_policy_sources()

        snapshot = get_policy_source_snapshot()
        logger.info(
            "Policy source auto-registration complete",
            policy_sources=policy_source_count,
            total_sources=snapshot["component_count"],
        )
    except Exception as e:
        logger.warning(f"Policy source auto-registration failed: {e}")

    # ------------------------------------------------------------------------
    # Governance Integration (CA + L Agent Runtime)
    # Unified loader for DevLayer governance and ArchitectMentor runtime
    # ------------------------------------------------------------------------
    try:
        from pathlib import Path

        from core.governance_integration import GovernanceIntegration

        governance = GovernanceIntegration(
            repo_root=Path.cwd(),
            agent_id=os.getenv("DEFAULT_AGENT_ID", "l"),
            memory_manager=None,  # Will be wired later if memory service available
        )
        app.state.governance = governance
        logger.info(
            "Governance Integration initialized",
            agent_id=governance.agent_id,
            confidence_threshold=governance.l_agent.confidence_threshold,
        )
    except Exception as e:
        # Non-fatal: governance features degraded but core API still works
        app.state.governance = None
        logger.warning(f"Governance Integration init failed: {e}")

    # ------------------------------------------------------------------------
    # Router Auto-Registration (Phase 2 Auto-Wiring)
    # Discover and wire @router_registry.register() decorated routers
    # NOTE: This runs ALONGSIDE legacy manual registrations during migration
    # ------------------------------------------------------------------------
    try:
        # Discover routers in api/routes/ that use router_registry.register()
        discovered_modules = discover_routers()

        # Wire discovered routers to app (after yield, before legacy registrations)
        # For now, just log discovery - actual wiring happens after app is created
        if len(router_registry) > 0:
            logger.info(
                "Router auto-registration discovered",
                modules_scanned=discovered_modules,
                routers_registered=len(router_registry),
            )
        else:
            logger.info(
                "No @router_registry.register() routers found — using legacy registration only"
            )
    except Exception as e:
        # Non-fatal: fall back to legacy manual router registration
        logger.warning(f"Router auto-discovery failed (using legacy): {e}")

    # Get database URL
    database_url = os.getenv("MEMORY_DSN") or os.getenv("DATABASE_URL")
    if not database_url:
        logger.warning(
            "MEMORY_DSN/DATABASE_URL not set. Memory system will not be available. "
            "Set MEMORY_DSN environment variable to enable memory."
        )
    else:
        try:
            # Initialize DB schema (deferred from module-level for Docker DNS readiness)
            if not LOCAL_DEV:
                await db.init_db()

            # Run migrations
            logger.info("Running database migrations...")
            migration_result = await run_migrations(database_url)
            logger.info(
                f"Migrations complete: {migration_result['applied']} applied, "
                f"{migration_result['skipped']} skipped, {migration_result['errors']} errors"
            )
            if migration_result["errors"]:
                logger.error(f"Migration errors: {migration_result['error_details']}")

            # Initialize memory service
            logger.info("Initializing memory service...")
            substrate_service = await init_service(
                database_url=database_url,
                embedding_provider_type=os.getenv("EMBEDDING_PROVIDER", "openai"),
                embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-large"),
                openai_api_key=os.getenv("OPENAI_API_KEY"),
            )
            logger.info("Memory service initialized")

            # GMP-78: Also initialize the repository singleton for tool_embeddings
            # The tool embeddings service uses get_repository() directly
            from memory.substrate_repository import init_repository

            await init_repository(database_url)
            logger.info("Repository singleton initialized for tool embeddings")

            # Store in app state for route dependencies
            app.state.substrate_service = substrate_service

            # Initialize Agent Persistence Service for checkpoint management
            try:
                agent_persistence = AgentPersistenceService(
                    service=substrate_service,
                    repository=substrate_service._repository,
                )
                app.state.agent_persistence = agent_persistence
                logger.info("Agent persistence service initialized")

                # Restore agent checkpoints on startup (best-effort)
                try:
                    default_agent_id = os.getenv("DEFAULT_AGENT_ID", "l9-standard-v1")
                    restored_state = await agent_persistence.restore_checkpoint(
                        default_agent_id
                    )
                    if restored_state:
                        logger.info(
                            "Agent checkpoint restored on startup",
                            agent_id=default_agent_id,
                            state_keys=list(restored_state.keys()),
                        )
                        app.state.restored_agent_state = restored_state
                    else:
                        logger.debug(
                            "No checkpoint found for agent", agent_id=default_agent_id
                        )
                        app.state.restored_agent_state = None
                except Exception as restore_err:
                    logger.warning(f"Failed to restore agent checkpoint: {restore_err}")
                    app.state.restored_agent_state = None

            except Exception as persistence_err:
                logger.warning(
                    f"Failed to initialize agent persistence: {persistence_err}"
                )
                app.state.agent_persistence = None
                app.state.restored_agent_state = None

            # Initialize TimelineService for memory timeline reconstruction
            try:
                timeline_service = TimelineService(
                    repository=substrate_service._repository
                )
                app.state.timeline_service = timeline_service
                logger.info("TimelineService initialized")
            except Exception as timeline_err:
                logger.warning(f"Failed to initialize TimelineService: {timeline_err}")
                app.state.timeline_service = None

            # Initialize MemoryStateManager for L-CTO agent state management
            try:
                memory_state_manager = MemoryStateManager(
                    service=substrate_service,
                    agent_id="L",  # L-CTO agent
                )
                app.state.memory_state_manager = memory_state_manager
                logger.info("MemoryStateManager initialized for agent 'L'")
            except Exception as state_err:
                logger.warning(f"Failed to initialize MemoryStateManager: {state_err}")
                app.state.memory_state_manager = None

        except Exception as e:
            logger.error(
                "memory_system.init_FAILED",
                error=str(e),
                error_type=type(e).__name__,
                database_url_set=bool(database_url),
                openai_api_key_set=bool(os.getenv("OPENAI_API_KEY")),
                embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
                exc_info=True,
            )
            app.state.substrate_service = None
            app.state.agent_persistence = None
            app.state.restored_agent_state = None
            app.state.timeline_service = None
            app.state.memory_state_manager = None

    # Initialize MCP Memory DB pool (for /mcp/call routes)
    # This is REQUIRED for MCP tools to work when routed through l9-api
    if database_url:
        try:
            import sys
            from pathlib import Path

            mcp_path = Path(__file__).parent.parent / "mcp_memory"
            if str(mcp_path) not in sys.path:
                sys.path.insert(0, str(mcp_path))

            from src.config import settings as mcp_settings
            from src.db import init_db as mcp_init_db

            # Set MCP config to use same database
            mcp_settings.MEMORY_DSN = database_url

            await mcp_init_db()
            app.state.mcp_db_initialized = True
            logger.info("MCP Memory DB pool initialized (for /mcp/call routes)")
        except Exception as e:
            logger.warning(f"Failed to initialize MCP Memory DB pool: {e}")
            app.state.mcp_db_initialized = False
    else:
        app.state.mcp_db_initialized = False

    # Initialize Quantum Research Factory (if enabled)
    if _has_research and database_url:
        try:
            logger.info("Initializing Quantum Research Factory...")
            await init_runtime(database_url)
            app.state.research_enabled = True
            logger.info("Quantum Research Factory initialized at /research")
        except Exception as e:
            logger.error(f"Failed to initialize Research Factory: {e}", exc_info=True)
            app.state.research_enabled = False
    elif _has_research:
        logger.warning("Research Factory not initialized: database_url required")
        app.state.research_enabled = False

    # Initialize World Model Runtime (if enabled and substrate available)
    if (
        _has_world_model_runtime
        and hasattr(app.state, "substrate_service")
        and app.state.substrate_service
    ):
        try:
            logger.info("Initializing World Model Runtime...")
            world_model_runtime = await create_runtime_with_substrate(
                app.state.substrate_service,
                config=RuntimeConfig(
                    poll_interval_seconds=60,  # Poll memory every minute
                    batch_size=50,
                ),
            )
            app.state.world_model_runtime = world_model_runtime

            # Start the runtime loop in background
            import asyncio

            app.state.world_model_task = asyncio.create_task(
                world_model_runtime.run_forever()
            )
            logger.info(
                "World Model Runtime initialized and running",
                poll_interval=60,
                batch_size=50,
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize World Model Runtime: {e}", exc_info=True
            )
            app.state.world_model_runtime = None
    elif _has_world_model_runtime:
        logger.warning(
            "World Model Runtime not initialized: substrate_service required"
        )
        app.state.world_model_runtime = None

    # Initialize Governance Engine (if enabled)
    if _has_governance:
        try:
            policy_dir = os.getenv("POLICY_MANIFEST_DIR", "config/policies")
            logger.info("Initializing Governance Engine from %s...", policy_dir)

            substrate = getattr(app.state, "substrate_service", None)
            governance_engine = create_governance_engine(
                policy_dir=policy_dir,
                substrate_service=substrate,
            )

            app.state.governance_engine = governance_engine
            logger.info(
                "Governance Engine initialized: %d policies loaded",
                governance_engine.policy_count,
            )
        except (PolicyLoadError, InvalidPolicyError) as e:
            # Governance failure is critical - log but allow startup for dev
            logger.critical("Governance Engine failed to initialize: %s", str(e))
            app.state.governance_engine = None
        except Exception as e:
            logger.error(
                "Failed to initialize Governance Engine: %s", str(e), exc_info=True
            )
            app.state.governance_engine = None
    else:
        app.state.governance_engine = None

    # Initialize Housekeeping Engine (if enabled and substrate available)
    if (
        _has_housekeeping
        and hasattr(app.state, "substrate_service")
        and app.state.substrate_service
    ):
        try:
            logger.info("Initializing Housekeeping Engine...")
            housekeeping = init_housekeeping_engine(
                app.state.substrate_service._repository
            )
            app.state.housekeeping_engine = housekeeping
            logger.info("Housekeeping Engine initialized")
        except Exception as e:
            logger.error("Failed to initialize Housekeeping Engine: %s", str(e))
            app.state.housekeeping_engine = None
    else:
        app.state.housekeeping_engine = None

    # Initialize Agent Executor (if enabled and substrate available)
    if (
        _has_agent_executor
        and hasattr(app.state, "substrate_service")
        and app.state.substrate_service
    ):
        try:
            logger.info("Initializing Agent Executor...")

            # Use real AIOS runtime - FAIL LOUDLY if unavailable
            if not _has_aios_runtime:
                raise RuntimeError(
                    "FATAL: AIOSRuntime import failed. "
                    "Server cannot start without core agent runtime. "
                    "Check core/agents/runtime.py exists and imports cleanly."
                )
            aios_runtime = create_aios_runtime()
            logger.info("AIOSRuntime initialized successfully")

            # Use real tool registry - FAIL LOUDLY if unavailable
            if not _has_tool_registry:
                raise RuntimeError(
                    "FATAL: ToolRegistry import failed. "
                    "Server cannot start without tool dispatch capability. "
                    "Check core/tools/registry_adapter.py exists and imports cleanly."
                )
            # Connect governance engine if available
            gov_engine = getattr(app.state, "governance_engine", None)
            tool_registry = create_executor_tool_registry(
                governance_enabled=True,
                governance_engine=gov_engine,
            )
            logger.info(
                "ExecutorToolRegistry initialized (governance=%s)",
                "attached" if gov_engine else "legacy",
            )

            # ========================================================================
            # GMP-78: Sync tool embeddings for semantic tool retrieval
            # Phase 2: Track sync status for dynamic tool discovery health
            # ========================================================================
            app.state.tool_embeddings_synced = False
            app.state.tool_embedding_count = 0
            try:
                from core.tools.tool_embeddings import sync_all_tool_embeddings

                tool_embedding_count = await sync_all_tool_embeddings()
                app.state.tool_embeddings_synced = True
                app.state.tool_embedding_count = tool_embedding_count
                logger.info(
                    f"✓ Tool embeddings synced: {tool_embedding_count} tools (dynamic discovery enabled)"
                )
            except ImportError:
                logger.warning(
                    "Tool embeddings service not available - dynamic tool discovery DISABLED"
                )
            except Exception as e:
                # Non-fatal: semantic tool retrieval is an optimization, but log clearly
                logger.warning(
                    f"Tool embedding sync failed - dynamic tool discovery may be impaired: {e}"
                )

            # ========================================================================
            # SESSION STARTUP: Preflight checks + kernel readiness gate (v3.4+)
            # ========================================================================
            app.state.session_startup_result = None
            app.state.startup_ready = False

            # Skip startup checks in container environments (broken symlinks, missing governance files)
            # Detection: L9_SKIP_STARTUP_CHECKS=true OR L9_CONTAINER_ENV=true OR /.dockerenv exists
            skip_startup = settings.l9_skip_startup_checks
            in_container = (
                os.getenv("L9_CONTAINER_ENV", "").lower() == "true"
                or os.path.exists("/.dockerenv")
                or str(Path.cwd()) == "/app"
            )

            if skip_startup or in_container:
                logger.info("╔════════════════════════════════════════╗")
                logger.info("║  Skipping Session Startup (container)  ║")
                logger.info("╚════════════════════════════════════════╝")
                app.state.startup_ready = True
                app.state.session_startup_result = None
            elif _has_session_startup:
                try:
                    logger.info("╔════════════════════════════════════════╗")
                    logger.info("║  Running Session Startup Checks...     ║")
                    logger.info("╚════════════════════════════════════════╝")

                    workspace_root = Path(os.getenv("L9_WORKSPACE_ROOT", Path.cwd()))
                    session_startup = SessionStartup(workspace_root=workspace_root)
                    startup_result: StartupResult = await session_startup.execute()

                    app.state.session_startup_result = startup_result
                    app.state.startup_ready = startup_result.status == "READY"

                    if startup_result.status == "READY":
                        logger.info(
                            "✓ Session Startup PASSED: preflight=%s, files_loaded=%d, kernels_ready=%s",
                            startup_result.preflight_passed,
                            len(startup_result.files_loaded),
                            startup_result.kernels_ready,
                        )
                        if startup_result.kernel_hash_snapshot:
                            logger.info(
                                "  Kernel hash snapshot: %d kernels verified",
                                len(startup_result.kernel_hash_snapshot),
                            )
                    else:
                        logger.critical(
                            "❌ Session Startup FAILED: status=%s, errors=%s",
                            startup_result.status,
                            (
                                startup_result.errors[:3]
                                if startup_result.errors
                                else "none"
                            ),
                        )
                        # In production, this should be fatal
                        # For dev, we continue with degraded mode
                        if startup_result.warnings:
                            for warning in startup_result.warnings[:5]:
                                logger.warning("  Startup warning: %s", warning)

                except Exception as e:
                    logger.critical(
                        "Session Startup crashed: %s", str(e), exc_info=True
                    )
                    app.state.startup_ready = False
                    # Non-fatal in dev mode
            else:
                logger.warning(
                    "SessionStartup not available - skipping preflight checks"
                )
                app.state.startup_ready = True  # Assume ready if no checks available

            # Initialize agent registry with kernel loading - FAIL LOUDLY if unavailable
            if not _has_kernel_registry:
                raise RuntimeError(
                    "FATAL: KernelAwareAgentRegistry import failed. "
                    "Server cannot start without agent configuration capability. "
                    "Check core/agents/registry.py exists and imports cleanly."
                )

            logger.debug("Attempting to create kernel-aware agent registry...")
            logger.info("Initializing Kernel-Aware Agent Registry...")
            try:
                agent_registry = create_kernel_aware_registry()
                app.state.agent_registry = agent_registry
                logger.info(
                    "Kernel-Aware Agent Registry initialized: kernel_state=%s",
                    agent_registry.get_kernel_state(),
                )
            except RuntimeError as e:
                # Kernel loading failed - this is critical
                logger.critical(
                    "FATAL: Kernel loading failed: %s", str(e), exc_info=True
                )
                raise
            except Exception as e:
                # Unexpected error during kernel registry creation
                logger.critical(
                    "FATAL: Unexpected error creating kernel registry: %s",
                    str(e),
                    exc_info=True,
                )
                raise

            # Create executor
            logger.debug(
                "Creating AgentExecutorService with aios_runtime=%s, tool_registry=%s, agent_registry=%s",
                aios_runtime is not None,
                tool_registry is not None,
                type(agent_registry).__name__ if agent_registry else "None",
            )
            executor = AgentExecutorService(
                aios_runtime=aios_runtime,
                tool_registry=tool_registry,
                substrate_service=app.state.substrate_service,
                agent_registry=agent_registry,
            )
            if agent_registry is None or not hasattr(agent_registry, "get_l_cto_agent"):
                raise RuntimeError(
                    "FATAL: Kernel-aware agent registry required for executor startup"
                )
            l_cto_agent = agent_registry.get_l_cto_agent()
            if l_cto_agent is None:
                raise RuntimeError(
                    "FATAL: Kernel-aware agent not available for executor startup"
                )
            executor.set_kernel_aware_agent(l_cto_agent)
            if executor._get_kernel_aware_agent() is None:
                raise RuntimeError(
                    "FATAL: Kernel-aware agent not active; refusing to start executor"
                )

            app.state.agent_executor = executor
            app.state.aios_runtime = aios_runtime
            app.state.tool_registry = tool_registry
            app.state.agent_registry = agent_registry
            logger.info("Agent Executor initialized")

            # Initialize ActionToolOrchestrator (for /tools/execute endpoint)
            try:
                from orchestrators.action_tool.orchestrator import (
                    ActionToolOrchestrator,
                )

                gov_engine = getattr(app.state, "governance_engine", None)
                action_tool_orchestrator = ActionToolOrchestrator(
                    tool_registry=tool_registry,
                    governance_engine=gov_engine,
                )
                app.state.action_tool_orchestrator = action_tool_orchestrator
                logger.info("ActionToolOrchestrator initialized")
            except ImportError:
                logger.debug("ActionToolOrchestrator not available")
                app.state.action_tool_orchestrator = None
            except Exception as orch_err:
                logger.warning(f"ActionToolOrchestrator init failed: {orch_err}")
                app.state.action_tool_orchestrator = None

            # Initialize MemoryOrchestrator (for /memory/batch, /memory/compact endpoints)
            try:
                from orchestrators.memory.orchestrator import MemoryOrchestrator

                memory_orchestrator = MemoryOrchestrator()
                app.state.memory_orchestrator = memory_orchestrator
                logger.info("MemoryOrchestrator initialized")
            except ImportError:
                logger.debug("MemoryOrchestrator not available")
                app.state.memory_orchestrator = None
            except Exception as mem_orch_err:
                logger.warning(f"MemoryOrchestrator init failed: {mem_orch_err}")
                app.state.memory_orchestrator = None

            # Initialize ReasoningOrchestrator (for /reasoning/execute endpoint)
            if _has_reasoning:
                try:
                    reasoning_orchestrator = ReasoningOrchestrator()
                    app.state.reasoning_orchestrator = reasoning_orchestrator
                    logger.info("ReasoningOrchestrator initialized")
                except Exception as reason_err:
                    logger.warning(f"ReasoningOrchestrator init failed: {reason_err}")
                    app.state.reasoning_orchestrator = None
            else:
                app.state.reasoning_orchestrator = None

            # Initialize ResearchSwarmOrchestrator (for /research/swarm/execute endpoint)
            if _has_research_swarm:
                try:
                    research_swarm_orchestrator = ResearchSwarmOrchestrator()
                    app.state.research_swarm_orchestrator = research_swarm_orchestrator
                    logger.info("ResearchSwarmOrchestrator initialized")
                except Exception as swarm_err:
                    logger.warning(
                        f"ResearchSwarmOrchestrator init failed: {swarm_err}"
                    )
                    app.state.research_swarm_orchestrator = None
            else:
                app.state.research_swarm_orchestrator = None

            # Initialize ResearchAgent (Perplexity-based research-to-code agent)
            if _has_research_agent:
                try:
                    research_agent = create_research_agent()
                    app.state.research_agent = research_agent
                    logger.info(
                        "ResearchAgent initialized (agent_id=%s, variations=%d)",
                        research_agent.agent_id,
                        len(research_agent.prompt_variations),
                    )
                except ValueError as api_err:
                    # Missing PERPLEXITY_API_KEY - expected in some environments
                    logger.warning(
                        f"ResearchAgent init failed (missing API key): {api_err}"
                    )
                    app.state.research_agent = None
                except Exception as agent_err:
                    logger.warning(f"ResearchAgent init failed: {agent_err}")
                    app.state.research_agent = None
            else:
                app.state.research_agent = None

            # Initialize ReflectionAgent (Meta-reasoning and self-improvement)
            if _has_reflection_agent:
                try:
                    reflection_agent = create_reflection_agent()
                    app.state.reflection_agent = reflection_agent
                    logger.info(
                        "ReflectionAgent initialized (agent_id=%s)",
                        reflection_agent.agent_id,
                    )
                except Exception as agent_err:
                    logger.warning(f"ReflectionAgent init failed: {agent_err}")
                    app.state.reflection_agent = None
            else:
                app.state.reflection_agent = None

            # Initialize WorldModelService (explicit, not lazy)
            try:
                from world_model.service import get_world_model_service

                world_model_service = get_world_model_service()
                app.state.world_model_service = world_model_service
                logger.info("WorldModelService initialized")

                # Wire WorldModelService to WorldModelRuntime for DB sync (GMP-WIRE)
                # This connects the in-memory World Model to PostgreSQL persistence
                if (
                    hasattr(app.state, "world_model_runtime")
                    and app.state.world_model_runtime
                ):
                    app.state.world_model_runtime.set_world_model_service(
                        world_model_service
                    )
                    logger.info(
                        "WorldModelService wired to WorldModelRuntime for DB sync"
                    )
            except ImportError:
                logger.debug("WorldModelService not available")
                app.state.world_model_service = None
            except Exception as wm_err:
                logger.warning(f"WorldModelService init failed: {wm_err}")
                app.state.world_model_service = None

            # Initialize CursorExecutor (GMP-87: Wire to app.state for /cursor routes)
            if _has_cursor_executor:
                try:
                    # Get repository from substrate_service
                    repository = app.state.substrate_service._repository

                    # Build dependency chain
                    cursor_config = get_cursor_langgraph_config()

                    # 1. Memory Gateway (uses MemorySubstrateService directly)
                    memory_gateway = CursorMemoryGateway(
                        substrate_service=app.state.substrate_service
                    )

                    # 3. PostgresSaver + Checkpoint Manager
                    postgres_saver = L9PostgresSaver(repository=repository)
                    checkpoint_manager = CursorCheckpointManager(
                        postgres_saver=postgres_saver,
                        memory_gateway=memory_gateway,
                    )

                    # 4. Approval Manager
                    approval_manager = ApprovalManager(
                        substrate_service=app.state.substrate_service
                    )

                    # 5. Build LangGraph app (using a deps object)
                    class CursorGraphDeps:
                        pass

                    deps = CursorGraphDeps()
                    deps.memory_gateway = memory_gateway
                    deps.approval_gate = approval_manager
                    deps.checkpoint_manager = checkpoint_manager

                    langgraph_app = build_cursor_langgraph(
                        config=cursor_config,
                        deps=deps,
                    )

                    # 6. Create CursorExecutor
                    cursor_executor = CursorExecutor(
                        langgraph_app=langgraph_app,
                        memory_gateway=memory_gateway,
                        substrate_service=app.state.substrate_service,
                        checkpoint_manager=checkpoint_manager,
                        approval_manager=approval_manager,
                    )

                    app.state.cursor_executor = cursor_executor
                    logger.info("CursorExecutor initialized (GMP-87)")
                except Exception as cursor_err:
                    logger.warning(f"CursorExecutor init failed: {cursor_err}")
                    app.state.cursor_executor = None
            else:
                app.state.cursor_executor = None

        except Exception as e:
            logger.error(f"Failed to initialize Agent Executor: {e}", exc_info=True)
            app.state.agent_executor = None
            app.state.aios_runtime = None
            app.state.tool_registry = None
            app.state.agent_registry = None
    elif _has_agent_executor:
        # Log detailed reason WHY substrate_service is missing
        substrate_error = getattr(
            app.state, "_substrate_init_error", "unknown - no error stored"
        )
        logger.error(
            "agent_executor.SKIPPED",
            reason="substrate_service_not_available",
            substrate_init_error=substrate_error,
            substrate_service_exists=hasattr(app.state, "substrate_service"),
            substrate_service_is_none=getattr(app.state, "substrate_service", None)
            is None,
        )
        app.state.agent_executor = None
        app.state.aios_runtime = None
        app.state.tool_registry = None
        app.state.agent_registry = None

    # =========================================================================
    # CRITICAL HEALTH CHECK: Verify agent_executor if new Slack routing enabled
    # =========================================================================
    from config.settings import get_integration_settings

    integration_settings = get_integration_settings()

    # Modern Slack routing uses AgentExecutorService (legacy router removed)
    agent_executor = getattr(app.state, "agent_executor", None)

    # Allow minimal deployment without agent executor (L9_MINIMAL_MODE=true)
    minimal_mode = os.environ.get("L9_MINIMAL_MODE", "false").lower() == "true"

    if agent_executor is None:
        if minimal_mode:
            logger.warning(
                "Agent Executor not initialized (L9_MINIMAL_MODE=true). "
                "Slack routing and agent features will be disabled."
            )
        else:
            logger.critical(
                "╔═══════════════════════════════════════════════════════════════╗\n"
                "║  CRITICAL: Agent Executor Initialization Failed              ║\n"
                "║                                                               ║\n"
                "║  Slack routing requires AgentExecutorService to be initialized. ║\n"
                "║                                                               ║\n"
                "║  Options:                                                     ║\n"
                "║  1. Fix agent_executor initialization (check logs above)     ║\n"
                "║  2. Install missing dependencies: pip install -r requirements.txt ║\n"
                "║  3. Set L9_MINIMAL_MODE=true to skip this check              ║\n"
                "╚═══════════════════════════════════════════════════════════════╝"
            )
            raise RuntimeError(
                "Agent Executor required for Slack routing but failed to initialize. "
                "Fix initialization or check dependencies. "
                "Set L9_MINIMAL_MODE=true to start in minimal mode."
            )
    else:
        logger.info(
            "✓ Health Check PASSED: Agent Executor is available for Slack routing"
        )

    # Initialize Slack adapter (if enabled)
    if _has_slack:
        from config.settings import get_integration_settings

        integration_settings = get_integration_settings()

        if not integration_settings.slack_app_enabled:
            logger.debug("Slack adapter disabled (SLACK_APP_ENABLED=false)")
            app.state.slack_validator = None
            app.state.slack_client = None
        else:
            try:
                slack_signing_secret = (
                    integration_settings.slack_signing_secret
                    or os.getenv("SLACK_SIGNING_SECRET")
                )
                slack_bot_token = integration_settings.slack_bot_token or os.getenv(
                    "SLACK_BOT_TOKEN"
                )

                if slack_signing_secret and slack_bot_token:
                    logger.info("Initializing Slack adapter...")

                    # Initialize Slack components
                    validator = SlackRequestValidator(slack_signing_secret)
                    http_client = httpx.AsyncClient()
                    slack_client = SlackAPIClient(
                        bot_token=slack_bot_token,
                        http_client=http_client,
                    )

                    # Store in app state for route dependencies
                    app.state.slack_validator = validator
                    app.state.slack_client = slack_client
                    app.state.aios_base_url = os.getenv(
                        "AIOS_BASE_URL", "http://localhost:8000"
                    )
                    app.state.http_client = http_client

                    logger.info("Slack adapter initialized")
                else:
                    logger.warning(
                        "Slack adapter not initialized: SLACK_SIGNING_SECRET or SLACK_BOT_TOKEN not set"
                    )
                    app.state.slack_validator = None
                    app.state.slack_client = None
            except Exception as e:
                logger.error(f"Failed to initialize Slack adapter: {e}", exc_info=True)
                app.state.slack_validator = None
                app.state.slack_client = None

    # ========================================================================
    # NEO4J GRAPH INTEGRATIONS (v2.7+)
    # ========================================================================

    # Validate Neo4j URI format (if set)
    neo4j_uri = os.getenv("NEO4J_URI")
    if neo4j_uri:
        valid_prefixes = ("bolt://", "neo4j://", "neo4j+s://", "neo4j+ssc://")
        if not neo4j_uri.startswith(valid_prefixes):
            logger.error(
                f"Invalid NEO4J_URI format: {neo4j_uri}. "
                f"Must start with one of: {valid_prefixes}"
            )
            raise ValueError(f"Invalid NEO4J_URI format: {neo4j_uri}")

    # Initialize Neo4j client (SINGLE SOURCE OF TRUTH)
    # Retry with exponential backoff to wait for Neo4j container to be ready
    # Neo4j is OPTIONAL - app continues in degraded mode if unavailable
    import asyncio

    neo4j_max_retries = 5  # 10 retries = ~30 seconds total
    neo4j_retry_delay = 3  # Start with 3 seconds

    try:
        from memory.graph_client import close_neo4j_client, get_neo4j_client

        neo4j = None
        for attempt in range(neo4j_max_retries):
            try:
                # Reset singleton on retry to force fresh connection attempt
                if attempt > 0:
                    try:
                        await close_neo4j_client()
                    except Exception:
                        pass  # Ignore errors closing non-existent client

                neo4j = await get_neo4j_client()
                if neo4j and neo4j.is_available():
                    app.state.neo4j_client = neo4j
                    logger.info(
                        f"Neo4j graph client initialized (attempt {attempt + 1})"
                    )
                    break
                else:
                    if attempt < neo4j_max_retries - 1:
                        logger.warning(
                            f"Neo4j not available (attempt {attempt + 1}/{neo4j_max_retries}) - retrying in {neo4j_retry_delay:.1f}s..."
                        )
                        await asyncio.sleep(neo4j_retry_delay)
                        neo4j_retry_delay = min(
                            neo4j_retry_delay * 1.5, 10
                        )  # Exponential backoff, max 10s
                    else:
                        # Final attempt failed - continue without Neo4j
                        app.state.neo4j_client = None
                        logger.warning(
                            "Neo4j failed to connect after retries - graph features will be disabled",
                            neo4j_uri=os.getenv("NEO4J_URI")
                            or os.getenv("NEO4J_URL", "not set"),
                            neo4j_user=os.getenv("NEO4J_USER", "not set"),
                            has_password=bool(os.getenv("NEO4J_PASSWORD")),
                        )
                        break
            except Exception as e:
                if attempt < neo4j_max_retries - 1:
                    logger.warning(
                        f"Neo4j connection error (attempt {attempt + 1}/{neo4j_max_retries}): {e} - retrying in {neo4j_retry_delay:.1f}s..."
                    )
                    await asyncio.sleep(neo4j_retry_delay)
                    neo4j_retry_delay = min(neo4j_retry_delay * 1.5, 10)
                else:
                    logger.warning(
                        f"Neo4j connection failed after retries (non-critical): {e}",
                        neo4j_uri=os.getenv("NEO4J_URI")
                        or os.getenv("NEO4J_URL", "not set"),
                    )
                    app.state.neo4j_client = None
                    break

        # Only proceed with Neo4j initialization if we have a client
        if neo4j and neo4j.is_available():
            # Bootstrap governance schema (creates Responsibility, Directive, SOP labels)
            try:
                from scripts.bootstrap_neo4j_schema import bootstrap_l_governance

                bootstrap_result = await bootstrap_l_governance(neo4j.driver)
                if bootstrap_result.get("success"):
                    logger.info(
                        "Neo4j governance schema bootstrapped",
                        responsibilities=bootstrap_result.get("responsibilities", 0),
                        directives=bootstrap_result.get("directives", 0),
                        sops=bootstrap_result.get("sops", 0),
                    )
                else:
                    logger.warning(
                        f"Governance schema bootstrap failed: {bootstrap_result.get('error')}"
                    )
            except Exception as e:
                logger.warning(f"Failed to bootstrap governance schema: {e}")

            # Register L9 tools in graph (for dependency tracking)
            try:
                from core.tools.tool_graph import register_l9_tools, register_l_tools

                tool_count = await register_l9_tools()
                logger.info(f"Registered {tool_count} tools in Neo4j graph")

                # Register L agent internal tools
                l_tool_count = await register_l_tools()
                logger.info(f"Registered {l_tool_count} L agent tools in Neo4j graph")
            except Exception as e:
                logger.warning(f"Failed to register tools in Neo4j: {e}")

            # Start GMP worker (for processing approved GMP tasks)
            try:
                from runtime.gmp_worker import start_gmp_worker

                await start_gmp_worker(poll_interval=2.0)
                logger.info("GMP worker started")
            except Exception as e:
                logger.warning(f"Failed to start GMP worker: {e}")

            # Initialize Strategy Memory Service (GMP-102: Phase 0-1)
            try:
                from memory.neo4j_strategy_memory import Neo4jStrategyMemoryService

                strategy_memory = Neo4jStrategyMemoryService(
                    neo4j_client=neo4j,
                    semantic_service=None,  # Phase 0: no embedding-based retrieval yet
                )
                app.state.strategy_memory = strategy_memory
                logger.info("Strategy Memory service initialized (Neo4j-backed)")
            except Exception as e:
                app.state.strategy_memory = None
                logger.warning(f"Failed to initialize Strategy Memory: {e}")
        else:
            # Neo4j not available or not healthy
            app.state.neo4j_client = None
            app.state.strategy_memory = None
            logger.info("Neo4j not available - graph features disabled")
    except ImportError:
        app.state.neo4j_client = None
        app.state.strategy_memory = None
        logger.debug("Neo4j client not available")
    except Exception as e:
        app.state.neo4j_client = None
        app.state.strategy_memory = None
        logger.warning(f"Failed to initialize Neo4j: {e}")

    # Initialize Redis client (optional, graceful if unavailable)
    try:
        from runtime.redis_client import close_redis_client, get_redis_client

        redis = await get_redis_client()
        if redis and redis.is_available():
            app.state.redis_client = redis
            logger.info("Redis client initialized")
        else:
            app.state.redis_client = None
            logger.info("Redis not available - using in-memory fallbacks")
    except ImportError:
        app.state.redis_client = None
        logger.debug("Redis client not available")
    except Exception as e:
        app.state.redis_client = None
        logger.warning(f"Failed to initialize Redis: {e}")

    # Store rate limiter in app state
    try:
        from runtime.rate_limiter import RateLimiter

        app.state.rate_limiter = RateLimiter()
        logger.info("Rate limiter initialized")
    except ImportError:
        app.state.rate_limiter = None

    # Initialize Permission Graph (RBAC via Neo4j)
    try:
        from core.security.permission_graph import PermissionGraph

        if hasattr(app.state, "neo4j_client") and app.state.neo4j_client:
            app.state.permission_graph = PermissionGraph
            logger.info("✓ Permission Graph initialized (Neo4j-backed)")
        else:
            app.state.permission_graph = None
            logger.info("Permission Graph not available (requires Neo4j)")
    except ImportError:
        app.state.permission_graph = None
        logger.debug("Permission Graph module not available")
    except Exception as e:
        app.state.permission_graph = None
        logger.warning(f"Failed to initialize Permission Graph: {e}")

    # ========================================================================
    # STARTUP VALIDATION: Enforce required components are initialized
    # ========================================================================

    # Validate Neo4j (fail-fast if URI set but connection failed)
    if os.getenv("NEO4J_URI"):
        if not hasattr(app.state, "neo4j_client") or not app.state.neo4j_client:
            logger.critical(
                "NEO4J_URI set but connection failed - graph features disabled"
            )
            # Note: Not fatal - Neo4j is optional for dev mode
        else:
            logger.info("✓ Neo4j validation passed")

    # NOTE: L-CTO startup (LStartup) is DEPRECATED and archived.
    # L-CTO agent initialization is now handled by KernelAwareAgentRegistry
    # which loads kernels and activates the agent via runtime/kernel_loader.py.
    # See core/agents/kernel_registry.py for the new kernel-based initialization.

    # ========================================================================
    # AGENT BOOTSTRAP CEREMONY (v3.0+ Paradigm Shift)
    # ========================================================================
    if L9_NEW_AGENT_INIT and _has_bootstrap:
        try:
            logger.info("╔════════════════════════════════════════╗")
            logger.info("║  L9_NEW_AGENT_INIT=true                ║")
            logger.info("║  Running Agent Bootstrap Ceremony...   ║")
            logger.info("╚════════════════════════════════════════╝")

            substrate = getattr(app.state, "substrate_service", None)
            if substrate:
                bootstrap = AgentBootstrapOrchestrator(substrate)

                # Bootstrap L-CTO agent with full kernel stack
                l_config = AgentConfig(
                    agent_id="l-cto",
                    name="L CTO",
                    kernel_refs=[
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
                    ],
                )

                l_instance = await bootstrap.bootstrap_agent(l_config)
                app.state.l_agent_instance = l_instance

                logger.info(
                    "✓ L-CTO Agent Bootstrap complete",
                    instance_id=l_instance.instance_id[:12],
                    signature=(
                        l_instance.initialization_signature[:16]
                        if l_instance.initialization_signature
                        else "none"
                    ),
                )
            else:
                logger.warning("Bootstrap skipped: substrate_service not available")

        except Exception as e:
            logger.error("Agent Bootstrap failed: %s", str(e), exc_info=True)
            # Non-fatal in dev mode - fall back to legacy initialization
    elif L9_NEW_AGENT_INIT:
        logger.warning("L9_NEW_AGENT_INIT=true but bootstrap module not available")

    # Validate Permission Graph (required if Slack is enabled)
    if os.getenv("SLACK_BOT_TOKEN"):
        if not hasattr(app.state, "permission_graph") or not app.state.permission_graph:
            logger.warning(
                "Slack enabled but Permission Graph not available. "
                "RBAC checks will be skipped."
            )
        else:
            logger.info("✓ Permission Graph validation passed (Slack protected)")

    # Validate kernel-aware agent registry (if enabled)
    if _has_kernel_registry:
        if not hasattr(app.state, "agent_registry") or app.state.agent_registry is None:
            logger.critical("STARTUP VALIDATION FAILED: agent_registry not initialized")
            # In dev mode, we continue; in prod, this would be fatal
        elif hasattr(app.state.agent_registry, "get_kernel_state"):
            kernel_state = app.state.agent_registry.get_kernel_state()
            if kernel_state != "ACTIVE":
                logger.critical(
                    "STARTUP VALIDATION FAILED: Kernels not ACTIVE (state=%s)",
                    kernel_state,
                )
            else:
                logger.info("✓✓✓ L9 FULLY INITIALIZED WITH ACTIVE KERNELS ✓✓✓")

    # Validate Session Startup result (v3.4+ / GMP-KERNEL-BOOT)
    if _has_session_startup:
        startup_result = getattr(app.state, "session_startup_result", None)
        startup_ready = getattr(app.state, "startup_ready", False)

        if startup_result is None:
            logger.warning("STARTUP VALIDATION: SessionStartup result not available")
        elif not startup_ready:
            logger.critical(
                "STARTUP VALIDATION FAILED: SessionStartup not ready (status=%s)",
                startup_result.status if startup_result else "unknown",
            )
            if startup_result and startup_result.errors:
                for error in startup_result.errors[:3]:
                    logger.critical("  Startup error: %s", error)
        else:
            logger.info(
                "✓ Session Startup validation passed: kernels_ready=%s, files=%d",
                startup_result.kernels_ready if startup_result else "unknown",
                len(startup_result.files_loaded) if startup_result else 0,
            )

    # Validate rate limiter
    if not hasattr(app.state, "rate_limiter") or app.state.rate_limiter is None:
        logger.warning("STARTUP VALIDATION: Rate limiter not initialized")

    # ========================================================================
    # REGISTER L-CTO TOOLS
    # ========================================================================
    try:
        from core.tools.registry_adapter import register_l_tools

        tool_count = await register_l_tools()
        if tool_count > 0:
            logger.info(f"✓ L-CTO tools registered: {tool_count} tools available")
            app.state.tool_graph_healthy = True
        else:
            logger.warning(
                "⚠️ Tool registration returned 0 tools. "
                "System will operate in degraded mode.",
                extra={"alert": "tool_graph_degraded"},
            )
            app.state.tool_graph_healthy = False
    except Exception as e:
        logger.error(
            f"❌ Tool registration failed: {e}. Tool graph unavailable.",
            exc_info=True,
            extra={"alert": "tool_graph_failed"},
        )
        app.state.tool_graph_healthy = False
        # Non-fatal: tools still work via direct executor dispatch

    # ========================================================================
    # REGISTER MEMORY TOOLS (Agent Self-Query)
    # ========================================================================
    try:
        from core.tools.memory_tools import register_memory_tools

        tool_registry = getattr(app.state, "tool_registry", None)
        substrate_service = getattr(app.state, "substrate_service", None)
        if tool_registry:
            memory_tool_count = await register_memory_tools(
                tool_registry,
                substrate_service=substrate_service,
            )
            logger.info(f"✓ Memory tools registered: {memory_tool_count} tools")
        else:
            logger.warning("⚠️ Memory tools not registered: tool_registry not available")
    except Exception as e:
        logger.error(f"❌ Memory tool registration failed: {e}", exc_info=True)

    # ========================================================================
    # STARTUP: Initialize Prometheus metrics
    # ========================================================================
    if _has_prometheus:
        metrics_ok = init_metrics()
        if metrics_ok:
            logger.info("✓ Prometheus metrics initialized")
        else:
            logger.warning("⚠️ Prometheus metrics init returned False")
    else:
        logger.info(
            "Prometheus metrics not available (prometheus_client not installed)"
        )

    # ========================================================================
    # STAGE 3 MODULES: Tool Audit, Event Queue, Virtual Context, Evaluator
    # ========================================================================
    if L9_STAGE3_MODULES:
        logger.info("╔════════════════════════════════════════╗")
        logger.info("║  Stage 3: Wiring Enterprise Modules    ║")
        logger.info("╚════════════════════════════════════════╝")

        substrate = getattr(app.state, "substrate_service", None)

        # 1. Tool Audit Service (Postgres-backed audit trail)
        if _has_tool_audit_service and substrate:
            try:
                tool_audit_service = ToolAuditService(
                    substrate_service=substrate,
                    buffer_size=100,
                )
                await tool_audit_service.start()
                app.state.tool_audit_service = tool_audit_service
                logger.info("✓ ToolAuditService initialized (Postgres audit trail)")
            except Exception as e:
                logger.error(f"❌ ToolAuditService init failed: {e}", exc_info=True)
                app.state.tool_audit_service = None
        else:
            app.state.tool_audit_service = None
            if not _has_tool_audit_service:
                logger.debug("ToolAuditService module not available")

        # 2. Event Queue (Async agent coordination)
        if _has_event_queue:
            try:
                event_queue = await init_event_driven_coordination(app.state)
                logger.info("✓ EventQueue initialized (async coordination)")
            except Exception as e:
                logger.error(f"❌ EventQueue init failed: {e}", exc_info=True)
                app.state.event_queue = None
        else:
            app.state.event_queue = None
            logger.debug("EventQueue module not available")

        # 3. Virtual Context Manager (MemGPT-style tiered memory)
        if _has_virtual_context and substrate:
            try:
                # Pass neo4j_driver for graph state consolidation (from single source of truth)
                neo4j_for_vcm = getattr(app.state, "neo4j_client", None)
                virtual_context = VirtualContextManager(
                    substrate_service=substrate,
                    neo4j_driver=(
                        neo4j_for_vcm.driver
                        if (neo4j_for_vcm and neo4j_for_vcm.is_available())
                        else None
                    ),
                    main_context_size=4096,
                    working_memory_size=8192,
                )
                app.state.virtual_context_manager = virtual_context
                logger.info("✓ VirtualContextManager initialized (tiered memory)")
            except Exception as e:
                logger.error(
                    f"❌ VirtualContextManager init failed: {e}", exc_info=True
                )
                app.state.virtual_context_manager = None
        else:
            app.state.virtual_context_manager = None
            if not _has_virtual_context:
                logger.debug("VirtualContextManager module not available")

        # 4. Evaluator (LLM-as-judge + CI/CD gates)
        if _has_evaluator and substrate:
            try:
                llm_for_eval = getattr(app.state, "llm_service", None)
                evaluator = Evaluator(
                    substrate_service=substrate,
                    llm_service=llm_for_eval,
                )
                # Load default evaluation sets
                load_default_eval_sets(evaluator)
                app.state.evaluator = evaluator
                logger.info(
                    "✓ Evaluator initialized (LLM-as-judge, %d eval sets)",
                    len(evaluator.eval_sets),
                )
            except Exception as e:
                logger.error(f"❌ Evaluator init failed: {e}", exc_info=True)
                app.state.evaluator = None
        else:
            app.state.evaluator = None
            if not _has_evaluator:
                logger.debug("Evaluator module not available")

        # Wire Stage 3 services to AgentExecutor
        agent_executor = getattr(app.state, "agent_executor", None)
        if agent_executor is not None:
            # Wire ToolAuditService for execution tracking
            tool_audit = getattr(app.state, "tool_audit_service", None)
            if tool_audit is not None:
                agent_executor.set_tool_audit_service(tool_audit)
                logger.info("✓ ToolAuditService wired to AgentExecutor")

            # Wire VirtualContextManager for tiered memory
            virtual_ctx = getattr(app.state, "virtual_context_manager", None)
            if virtual_ctx is not None:
                agent_executor.set_virtual_context_manager(virtual_ctx)
                logger.info("✓ VirtualContextManager wired to AgentExecutor")

            # Wire EventQueue for async coordination
            event_queue = getattr(app.state, "event_queue", None)
            if event_queue is not None:
                agent_executor.set_event_queue(event_queue)
                logger.info("✓ EventQueue wired to AgentExecutor")

        logger.info("Stage 3 module wiring complete")
    else:
        logger.info("Stage 3 modules disabled (L9_STAGE3_MODULES=false)")

    # ========================================================================
    # STAGE 4: Memory Consolidation (Background Cleanup)
    # ========================================================================
    import asyncio  # Ensure asyncio is available for this block

    L9_STAGE4_CONSOLIDATION = settings.l9_stage4_consolidation

    if L9_STAGE4_CONSOLIDATION:
        logger.info("╔════════════════════════════════════════╗")
        logger.info("║  Stage 4: Memory Consolidation         ║")
        logger.info("╚════════════════════════════════════════╝")

        try:
            from core.memory.virtual_context import MemoryConsolidationService
            from memory.hierarchical_summarizer import HierarchicalSummarizer
            from memory.neural_decay_scheduler import NeuralDecayScheduler

            substrate = getattr(app.state, "substrate_service", None) or getattr(
                app.state, "memory_service", None
            )
            llm_service = getattr(app.state, "llm_service", None)

            if substrate:
                consolidation_service = MemoryConsolidationService(
                    substrate_service=substrate,
                    llm_service=llm_service,
                )
                app.state.consolidation_service = consolidation_service

                # Stage 2: Initialize Neural Decay Scheduler
                repository = getattr(substrate, "_repository", None) or getattr(
                    substrate, "repository", None
                )
                neural_decay_scheduler = NeuralDecayScheduler(
                    repository=repository,
                    dry_run=False,
                )
                app.state.neural_decay_scheduler = neural_decay_scheduler
                logger.info("✓ NeuralDecayScheduler initialized")

                # Stage 2: Initialize Hierarchical Summarizer
                hierarchical_summarizer = HierarchicalSummarizer(
                    repository=repository,
                    llm_client=llm_service,
                    dry_run=False,
                )
                app.state.hierarchical_summarizer = hierarchical_summarizer
                logger.info("✓ HierarchicalSummarizer initialized")

                # Schedule background cleanup via BackgroundTaskRegistry
                # NOTE: This loop is for MemoryConsolidationService (different from ConsolidationPipeline).
                # ConsolidationPipeline (v3.1) scheduled weekly_saturday_2am_utc (see orchestrators/memory/housekeeping.py)
                async def run_consolidation():
                    """Single consolidation pass (called periodically by BackgroundTaskRegistry)"""
                    logger.info("Running scheduled memory consolidation...")

                    # Consolidate for L (primary agent)
                    if hasattr(consolidation_service, "consolidate"):
                        metrics = (
                            consolidation_service.get_metrics()
                            if hasattr(consolidation_service, "get_metrics")
                            else {}
                        )
                        logger.info(f"Consolidation metrics: {metrics}")

                    # UKG Phase 5: Consolidate graph state (if method exists)
                    if hasattr(consolidation_service, "consolidate_graph_state"):
                        try:
                            graph_result = (
                                await consolidation_service.consolidate_graph_state("L")
                            )
                            logger.info(
                                f"Graph state consolidation: {graph_result.get('status', 'UNKNOWN')}"
                            )
                        except Exception as e:
                            logger.warning(f"Graph state consolidation failed: {e}")

                    # Stage 2: Neural Decay Pass
                    try:
                        decay_result = await neural_decay_scheduler.run_decay_pass()
                        logger.info(
                            f"Neural decay pass: processed={decay_result.packets_processed}, "
                            f"updated={decay_result.packets_updated}, pruned={decay_result.packets_pruned}"
                        )
                    except Exception as e:
                        logger.warning(f"Neural decay pass failed: {e}")

                    # Stage 2: Hierarchical Summarization Cascade
                    try:
                        summary_results = await hierarchical_summarizer.run_cascade()
                        for tier, summaries in summary_results.items():
                            logger.info(
                                f"Summarization {tier.value}: {len(summaries)} summaries created"
                            )
                    except Exception as e:
                        logger.warning(f"Hierarchical summarization failed: {e}")

                # Register with BackgroundTaskRegistry
                consolidation_interval = settings.l9_consolidation_interval_hours * 3600
                bg_tasks.register(
                    name="memory_consolidation",
                    coro=run_consolidation,
                    interval_seconds=consolidation_interval,
                    enabled_flag=None,  # Already checked by outer condition
                )
                logger.info(
                    f"✓ MemoryConsolidationService initialized ({settings.l9_consolidation_interval_hours}h cycle)"
                )
            else:
                logger.warning(
                    "⚠️ Consolidation not started: substrate_service not available"
                )
                app.state.consolidation_service = None

        except ImportError as e:
            logger.debug(f"MemoryConsolidationService not available: {e}")
            app.state.consolidation_service = None
        except Exception as e:
            logger.error(f"❌ Stage 4 (consolidation) init failed: {e}", exc_info=True)
            app.state.consolidation_service = None
    else:
        logger.info("Stage 4 (consolidation) disabled (L9_STAGE4_CONSOLIDATION=false)")

    # ========================================================================
    # STAGE 5: Graph-Backed Agent State (Neo4j OPTIONAL - graceful degradation)
    # ========================================================================
    # Set runtime flag for graph state availability
    app.state.graph_state_enabled = False

    if L9_GRAPH_AGENT_STATE and _has_graph_agent_state:
        logger.info("╔════════════════════════════════════════╗")
        logger.info("║  Stage 5: Graph-Backed Agent State     ║")
        logger.info("╚════════════════════════════════════════╝")

        # Get Neo4j client from single source of truth (app.state.neo4j_client)
        neo4j_client = getattr(app.state, "neo4j_client", None)

        if neo4j_client is None or not neo4j_client.is_available():
            logger.warning(
                "Graph agent state requested but Neo4j is unavailable; "
                "disabling graph-backed agent state for this run.",
                neo4j_uri=os.getenv("NEO4J_URI") or os.getenv("NEO4J_URL", "not set"),
                l9_graph_agent_state=L9_GRAPH_AGENT_STATE,
            )
            # Disable graph state at runtime (keep config unchanged for diagnostics)
            app.state.graph_state_enabled = False
            app.state.agent_graph_loader = None
            app.state.graph_hydrator = None
            app.state.agent_self_modify_tool = None
            logger.info(
                "Stage 5 skipped - Neo4j unavailable (app continuing in degraded mode)"
            )
        else:
            # Neo4j is available - proceed with initialization
            app.state.graph_state_enabled = True

            try:
                substrate = getattr(app.state, "substrate_service", None) or getattr(
                    app.state, "memory_service", None
                )

                # Initialize AgentGraphLoader (uses neo4j_client from app.state)
                agent_graph_loader = AgentGraphLoader(neo4j_client)
                app.state.agent_graph_loader = agent_graph_loader
                logger.info("✓ AgentGraphLoader initialized")

                # Initialize GraphHydrator (with optional kernel stack)
                kernel_stack = getattr(app.state, "kernel_stack", None)
                graph_hydrator = GraphHydrator(
                    neo4j_driver=neo4j_client.driver,  # Use driver property from Neo4jClient
                    kernel_stack=kernel_stack,
                )
                app.state.graph_hydrator = graph_hydrator
                logger.info("✓ GraphHydrator initialized")

                # Wire GraphHydrator to AgentExecutor (GMP-76)
                agent_executor = getattr(app.state, "agent_executor", None)
                if agent_executor is not None:
                    agent_executor.set_graph_hydrator(graph_hydrator)
                    logger.info("✓ GraphHydrator wired to AgentExecutor")

                # Initialize AgentSelfModifyTool
                self_modify_tool = create_self_modify_tool(
                    neo4j_driver=neo4j_client.driver,  # Use driver property from Neo4jClient
                    substrate_service=substrate,
                )
                app.state.agent_self_modify_tool = self_modify_tool
                logger.info("✓ AgentSelfModifyTool initialized")

                # Initialize ResearchGraphPersistence for research findings
                if _has_research_graph_persistence:
                    try:
                        research_graph_persistence = init_graph_persistence(
                            neo4j_client
                        )
                        app.state.research_graph_persistence = (
                            research_graph_persistence
                        )
                        logger.info("✓ ResearchGraphPersistence initialized")
                    except Exception as e:
                        logger.warning(f"ResearchGraphPersistence init failed: {e}")
                        app.state.research_graph_persistence = None

                # Check if L exists in graph, bootstrap if not
                if await agent_graph_loader.exists("L"):
                    logger.info("✓ L agent found in Neo4j graph")
                else:
                    logger.warning("L agent not in graph - run migration script")
                    logger.info("  python scripts/migrate_kernels_to_graph.py")

                logger.info("Stage 5 (Graph-Backed Agent State) complete")

            except Exception as e:
                error_msg = f"Stage 5 init failed: {e}"
                logger.error(error_msg, exc_info=True)
                # Don't raise - disable graph state and continue
                app.state.graph_state_enabled = False
                app.state.agent_graph_loader = None
                app.state.graph_hydrator = None
                app.state.agent_self_modify_tool = None
                logger.warning(
                    "Stage 5 disabled due to initialization error - app continuing"
                )
    elif L9_GRAPH_AGENT_STATE and not _has_graph_agent_state:
        logger.warning("Stage 5 enabled but graph_state module not available")
    else:
        logger.debug("Stage 5 (Graph-Backed Agent State) disabled")

    # ========================================================================
    # STARTUP: UKG Phase 3 - Graph to World Model Sync (REQUIRES Neo4j)
    # ========================================================================
    L9_GRAPH_WM_SYNC = settings.l9_graph_wm_sync

    if L9_GRAPH_WM_SYNC:
        # Get Neo4j client from single source of truth (app.state.neo4j_client)
        neo4j_for_sync = getattr(app.state, "neo4j_client", None)

        if neo4j_for_sync is None or not neo4j_for_sync.is_available():
            logger.warning(
                "Graph-WM Sync requested but Neo4j is unavailable; "
                "disabling Graph-WM Sync for this run.",
                neo4j_uri=os.getenv("NEO4J_URI") or os.getenv("NEO4J_URL", "not set"),
                l9_graph_wm_sync=L9_GRAPH_WM_SYNC,
            )
            app.state.graph_wm_sync = None
            logger.info("Graph-WM Sync skipped - Neo4j unavailable (app continuing)")
        else:
            try:
                from core.integration.graph_to_wm_sync import (
                    get_graph_wm_sync,
                    start_graph_wm_sync,
                )

                # Use driver property from Neo4jClient (single source of truth)
                await start_graph_wm_sync(neo4j_driver=neo4j_for_sync.driver)
                app.state.graph_wm_sync = get_graph_wm_sync(
                    neo4j_driver=neo4j_for_sync.driver
                )
                logger.info("✅ UKG Phase 3: Graph-WM Sync started")
            except ImportError as e:
                logger.error(f"Graph-WM Sync module import failed: {e}", exc_info=True)
                app.state.graph_wm_sync = None
                logger.warning(
                    "Graph-WM Sync disabled due to import error - app continuing"
                )
            except Exception as e:
                logger.error(f"Graph-WM Sync init failed: {e}", exc_info=True)
                app.state.graph_wm_sync = None
                logger.warning(
                    "Graph-WM Sync disabled due to initialization error - app continuing"
                )
    else:
        logger.debug("Graph-WM Sync disabled (L9_GRAPH_WM_SYNC=false)")
        app.state.graph_wm_sync = None

    # ========================================================================
    # STARTUP: UKG Phase 3.5 - World Model to Graph Sync (causal data)
    # ========================================================================
    L9_WM_GRAPH_SYNC = os.getenv("L9_WM_GRAPH_SYNC", "true").lower() == "true"
    # Get Neo4j client from single source of truth (app.state.neo4j_client)
    neo4j_for_wm_sync = getattr(app.state, "neo4j_client", None)

    if (
        L9_WM_GRAPH_SYNC
        and neo4j_for_wm_sync is not None
        and neo4j_for_wm_sync.is_available()
    ):
        try:
            from core.integration.wm_to_graph_sync import (
                get_wm_graph_sync,
                start_wm_graph_sync,
            )
            from world_model.causal_mapper import CausalMapper

            # Get CausalMapper from world_model_service if available (ensures we sync actual data)
            # Otherwise create shared instance
            causal_mapper = None
            wm_service = getattr(app.state, "world_model_service", None)
            if wm_service:
                causal_mapper = getattr(wm_service, "_causal_mapper", None)

            if causal_mapper is None:
                causal_mapper = CausalMapper()
                logger.debug(
                    "Created standalone CausalMapper (world_model_service not available)"
                )

            app.state.causal_mapper = causal_mapper

            await start_wm_graph_sync(
                neo4j_driver=neo4j_for_wm_sync.driver,  # Use driver property from Neo4jClient
                causal_mapper=app.state.causal_mapper,
            )
            app.state.wm_graph_sync = get_wm_graph_sync(
                neo4j_driver=neo4j_for_wm_sync.driver,  # Use driver property from Neo4jClient
                causal_mapper=app.state.causal_mapper,
            )
            logger.info("✅ UKG Phase 3.5: WM-Graph Sync started (causal data → Neo4j)")
        except ImportError as e:
            logger.warning(f"WM-Graph Sync module not available: {e}")
            app.state.wm_graph_sync = None
        except Exception as e:
            logger.error(f"WM-Graph Sync init failed: {e}")
            app.state.wm_graph_sync = None
    else:
        logger.debug(
            "WM-Graph Sync disabled (L9_WM_GRAPH_SYNC=false or Neo4j unavailable)"
        )
        app.state.wm_graph_sync = None

    # ========================================================================
    # STARTUP: UKG Phase 4 - Tool Pattern Extraction (optional)
    # ========================================================================
    L9_TOOL_PATTERN_EXTRACTION = settings.l9_tool_pattern_extraction

    if L9_TOOL_PATTERN_EXTRACTION:
        try:
            from core.integration.tool_pattern_extractor import (
                get_tool_pattern_extractor,
                start_tool_pattern_extraction,
            )

            await start_tool_pattern_extraction()
            app.state.tool_pattern_extractor = get_tool_pattern_extractor()
            logger.info("✅ UKG Phase 4: Tool Pattern Extraction started (6h interval)")
        except ImportError:
            logger.warning("Tool Pattern Extraction module not available")
            app.state.tool_pattern_extractor = None
        except Exception as e:
            logger.error(f"Tool Pattern Extraction init failed: {e}")
            app.state.tool_pattern_extractor = None
    else:
        logger.debug(
            "Tool Pattern Extraction disabled (L9_TOOL_PATTERN_EXTRACTION=false)"
        )
        app.state.tool_pattern_extractor = None

    # ========================================================================
    # STARTUP: Five-Tier Observability (v3.3+ GMP-OBS-DEPLOY)
    # ========================================================================
    if _has_observability and L9_OBSERVABILITY:
        try:
            substrate = getattr(app.state, "substrate_service", None)
            logger.info("Initializing Five-Tier Observability...")
            observability = await initialize_observability(substrate_service=substrate)
            app.state.observability_service = observability

            # Instrument L9 services (non-blocking, wraps existing methods)
            executor = getattr(app.state, "agent_executor", None)
            tool_registry = getattr(app.state, "tool_registry", None)
            governance = getattr(app.state, "governance_engine", None)

            if executor:
                await instrument_agent_executor(executor)
            if tool_registry:
                await instrument_tool_registry(tool_registry)
            if governance:
                await instrument_governance_engine(governance)
            if substrate:
                await instrument_memory_substrate(substrate)

            logger.info(
                "✅ Five-Tier Observability initialized",
                instrumented={
                    "executor": executor is not None,
                    "tool_registry": tool_registry is not None,
                    "governance": governance is not None,
                    "substrate": substrate is not None,
                },
            )

            # Register observability metrics update with BackgroundTaskRegistry
            async def update_observability_metrics():
                """Single observability metrics update pass"""
                if observability:
                    await observability.compute_metrics()
                    await observability.update_agent_kpis()

            bg_tasks.register(
                name="observability_metrics",
                coro=update_observability_metrics,
                interval_seconds=30,
                run_immediately=False,
            )
            logger.info("Observability metrics task registered (30s interval)")
        except Exception as e:
            logger.error(f"Observability init failed: {e}", exc_info=True)
            app.state.observability_service = None
    else:
        if not _has_observability:
            logger.debug("Observability module not available")
        else:
            logger.debug("Observability disabled (L9_OBSERVABILITY=false)")
        app.state.observability_service = None

    # ------------------------------------------------------------------------
    # GMP v2.0 Learning Engine (GMP-92)
    # ------------------------------------------------------------------------
    if settings.l9_gmp_learning_enabled and database_url:
        try:
            from agents.cursor.gmp_meta_learning import GMPMetaLearningEngine

            global gmp_learning_engine
            gmp_learning_engine = GMPMetaLearningEngine(database_url)
            await gmp_learning_engine.create_tables()
            # Note: Routes access via global import, not app.state
            logger.info("GMP Learning Engine initialized (v2.0)")
        except ImportError as e:
            logger.debug(f"GMP Learning Engine not available: {e}")
        except Exception as e:
            logger.error(f"GMP Learning Engine init failed: {e}", exc_info=True)
    else:
        if not settings.l9_gmp_learning_enabled:
            logger.debug("GMP Learning disabled (L9_GMP_LEARNING_ENABLED=false)")
        elif not database_url:
            logger.debug("GMP Learning skipped (no database_url)")

    # ------------------------------------------------------------------------
    # Stage 5: Predictive Memory Warming (GMP-STAGE5)
    # ------------------------------------------------------------------------
    if settings.l9_memory_warming_enabled:
        try:
            from memory.warming_service import create_warming_service

            global memory_warming_service

            # Get Neo4j graph client if available (for real subgraph traversal)
            # Use single source of truth: app.state.neo4j_client
            neo4j_for_warming = getattr(app.state, "neo4j_client", None)
            neo4j_available = (
                neo4j_for_warming is not None and neo4j_for_warming.is_available()
            )

            memory_warming_service = await create_warming_service(
                graph_client=neo4j_for_warming if neo4j_available else None
            )
            app.state.memory_warming_service = memory_warming_service
            logger.info(
                "Memory Warming Service initialized (Stage 5)",
                graph_client_available=neo4j_available,
            )

            # Wire warming service to agent executor
            agent_executor = getattr(app.state, "agent_executor", None)
            if agent_executor is not None:
                agent_executor.set_memory_warming_service(memory_warming_service)
                logger.info("Memory Warming Service wired to Agent Executor")
        except ImportError as e:
            logger.debug(f"Memory Warming Service not available: {e}")
            app.state.memory_warming_service = None
        except Exception as e:
            logger.error(f"Memory Warming Service init failed: {e}", exc_info=True)
            app.state.memory_warming_service = None
    else:
        logger.debug("Memory Warming disabled (L9_MEMORY_WARMING_ENABLED=false)")
        app.state.memory_warming_service = None

    # ------------------------------------------------------------------------
    # Bayesian Calibration Services (Bayesian Upgrade)
    # Initialize CalibrationService and GatingPolicyService if enabled
    # ------------------------------------------------------------------------
    calibration_enabled = os.getenv("L9_ENABLE_CALIBRATION", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    bayesian_enabled = os.getenv("L9_ENABLE_BAYESIAN_REASONING", "false").lower() in (
        "true",
        "1",
        "yes",
    )

    if _has_calibration and calibration_enabled:
        try:
            calibration_config = load_calibration_config()
            gating_config = load_gating_config()

            app.state.calibration_service = CalibrationService(calibration_config)
            app.state.gating_service = GatingPolicyService(gating_config)

            logger.info(
                "Calibration services initialized",
                calibration_method=calibration_config.primary_method.value,
                gating_enabled=gating_config.enabled,
            )

            # Wire to agent executor if available
            agent_executor = getattr(app.state, "agent_executor", None)
            if agent_executor is not None:
                if hasattr(agent_executor, "set_calibration_service"):
                    agent_executor.set_calibration_service(
                        app.state.calibration_service
                    )
                if hasattr(agent_executor, "set_gating_service"):
                    agent_executor.set_gating_service(app.state.gating_service)
                logger.info("Calibration services wired to Agent Executor")
        except Exception as e:
            logger.error(f"Calibration services init failed: {e}", exc_info=True)
            app.state.calibration_service = None
            app.state.gating_service = None
    else:
        if not _has_calibration:
            logger.debug("Calibration services not available (import failed)")
        else:
            logger.debug("Calibration disabled (L9_ENABLE_CALIBRATION=false)")
        app.state.calibration_service = None
        app.state.gating_service = None

    if _has_calibration and bayesian_enabled:
        try:
            app.state.bayesian_kernel = get_bayesian_kernel()
            logger.info("Bayesian Kernel initialized")
        except Exception as e:
            logger.error(f"Bayesian Kernel init failed: {e}", exc_info=True)
            app.state.bayesian_kernel = None
    else:
        app.state.bayesian_kernel = None

    yield

    # ========================================================================
    # SHUTDOWN: Clean up memory service and Slack adapter
    # ========================================================================
    logger.info("Shutting down L9 API server...")

    # Shutdown all background tasks first (graceful)
    if hasattr(app.state, "background_tasks") and app.state.background_tasks:
        try:
            cancelled = await app.state.background_tasks.shutdown_all()
            logger.info(f"Background tasks shutdown complete ({cancelled} cancelled)")
        except Exception as e:
            logger.warning(f"Error shutting down background tasks: {e}")

    # Shutdown Five-Tier Observability (flush spans)
    if hasattr(app.state, "observability_service") and app.state.observability_service:
        try:
            await app.state.observability_service.shutdown()
            logger.info("Observability service shutdown complete")
        except Exception as e:
            logger.warning(f"Error shutting down observability: {e}")

    # Shutdown Memory Warming Service (Stage 5)
    if (
        hasattr(app.state, "memory_warming_service")
        and app.state.memory_warming_service
    ):
        try:
            await app.state.memory_warming_service.shutdown()
            logger.info("Memory Warming Service shutdown complete")
        except Exception as e:
            logger.warning(f"Error shutting down Memory Warming Service: {e}")

    # Shutdown Calibration Services (Bayesian Upgrade)
    if hasattr(app.state, "calibration_service") and app.state.calibration_service:
        try:
            await app.state.calibration_service.shutdown()
            logger.info("Calibration Service shutdown complete")
        except Exception as e:
            logger.warning(f"Error shutting down Calibration Service: {e}")

    if hasattr(app.state, "gating_service") and app.state.gating_service:
        try:
            await app.state.gating_service.shutdown()
            logger.info("Gating Policy Service shutdown complete")
        except Exception as e:
            logger.warning(f"Error shutting down Gating Policy Service: {e}")

    # Save Governance Integration agent state
    if hasattr(app.state, "governance") and app.state.governance:
        try:
            app.state.governance.l_agent.save_state()
            logger.info("Governance agent state saved on shutdown")
        except Exception as e:
            logger.warning(f"Error saving governance agent state: {e}")

    # Save agent checkpoints before shutdown
    if hasattr(app.state, "agent_persistence") and app.state.agent_persistence:
        try:
            default_agent_id = os.getenv("DEFAULT_AGENT_ID", "l9-standard-v1")
            shutdown_state = {
                "shutdown_timestamp": datetime.now(UTC).isoformat(),
                "reason": "server_shutdown",
                "restored_on_startup": app.state.restored_agent_state is not None,
            }
            checkpoint_id = await app.state.agent_persistence.create_checkpoint(
                agent_id=default_agent_id,
                state=shutdown_state,
                reason="on_agent_shutdown",
            )
            logger.info(
                "Agent checkpoint saved on shutdown",
                agent_id=default_agent_id,
                checkpoint_id=str(checkpoint_id),
            )
        except Exception as e:
            logger.warning(f"Error saving agent checkpoint on shutdown: {e}")

    # Stop UKG Phase 4: Tool Pattern Extraction
    if (
        hasattr(app.state, "tool_pattern_extractor")
        and app.state.tool_pattern_extractor
    ):
        try:
            from core.integration.tool_pattern_extractor import (
                stop_tool_pattern_extraction,
            )

            await stop_tool_pattern_extraction()
            logger.info("Tool Pattern Extraction stopped")
        except Exception as e:
            logger.warning(f"Error stopping Tool Pattern Extraction: {e}")

    # Stop UKG Phase 3: Graph-WM Sync
    if hasattr(app.state, "graph_wm_sync") and app.state.graph_wm_sync:
        try:
            from core.integration.graph_to_wm_sync import stop_graph_wm_sync

            await stop_graph_wm_sync()
            logger.info("Graph-WM Sync stopped")
        except Exception as e:
            logger.warning(f"Error stopping Graph-WM Sync: {e}")

    # Stop Stage 4 consolidation
    if hasattr(app.state, "consolidation_task") and app.state.consolidation_task:
        try:
            app.state.consolidation_task.cancel()
            await app.state.consolidation_task
        except asyncio.CancelledError:
            logger.info("Consolidation task stopped")
        except Exception as e:
            logger.warning(f"Error stopping consolidation task: {e}")

    # Stop Stage 3 modules
    if hasattr(app.state, "tool_audit_service") and app.state.tool_audit_service:
        try:
            await app.state.tool_audit_service.stop()
            logger.info("ToolAuditService stopped")
        except Exception as e:
            logger.warning(f"Error stopping ToolAuditService: {e}")

    if hasattr(app.state, "event_queue") and app.state.event_queue:
        try:
            app.state.event_queue.stop()
            if hasattr(app.state, "event_processor_task"):
                app.state.event_processor_task.cancel()
                with suppress(asyncio.CancelledError):
                    await app.state.event_processor_task
            logger.info("EventQueue stopped")
        except Exception as e:
            logger.warning(f"Error stopping EventQueue: {e}")

    # Stop GMP worker
    try:
        from runtime.gmp_worker import stop_gmp_worker

        await stop_gmp_worker()
        logger.info("GMP worker stopped")
    except Exception as e:
        logger.warning(f"Error stopping GMP worker: {e}")

    # Stop World Model Runtime
    if hasattr(app.state, "world_model_runtime") and app.state.world_model_runtime:
        try:
            app.state.world_model_runtime.stop()
            if hasattr(app.state, "world_model_task"):
                app.state.world_model_task.cancel()
                with suppress(asyncio.CancelledError):
                    await app.state.world_model_task
            logger.info("World Model Runtime stopped")
        except Exception as e:
            logger.error(f"Error stopping World Model Runtime: {e}")

    # Cleanup World Model Service singleton
    try:
        from world_model.service import close_world_model_service

        await close_world_model_service()
        logger.info("World Model Service closed")
    except ImportError:
        pass  # world_model.service not available
    except Exception as e:
        logger.warning(f"Error closing World Model Service: {e}")

    # Cleanup Research Factory
    if _has_research and getattr(app.state, "research_enabled", False):
        try:
            await shutdown_runtime()
            logger.info("Research Factory shutdown")
        except Exception as e:
            logger.error(f"Error shutting down Research Factory: {e}")

    # Cleanup Slack HTTP client
    if _has_slack and hasattr(app.state, "http_client") and app.state.http_client:
        try:
            await app.state.http_client.aclose()
            logger.info("Slack HTTP client closed")
        except Exception as e:
            logger.error(f"Error closing Slack HTTP client: {e}")

    # Cleanup Neo4j client
    if hasattr(app.state, "neo4j_client") and app.state.neo4j_client:
        try:
            from memory.graph_client import close_neo4j_client

            await close_neo4j_client()
            logger.info("Neo4j client closed")
        except Exception as e:
            logger.error(f"Error closing Neo4j client: {e}")

    # Cleanup Redis client
    if hasattr(app.state, "redis_client") and app.state.redis_client:
        try:
            from runtime.redis_client import close_redis_client

            await close_redis_client()
            logger.info("Redis client closed")
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")

    # Cleanup memory service
    try:
        await close_service()
        logger.info("Memory service closed")
    except Exception as e:
        logger.error(f"Error closing memory service: {e}")

    # Cleanup MCP Memory DB pool
    if getattr(app.state, "mcp_db_initialized", False):
        try:
            from src.db import close_db as mcp_close_db

            await mcp_close_db()
            logger.info("MCP Memory DB pool closed")
        except Exception as e:
            logger.warning(f"Error closing MCP Memory DB pool: {e}")


# FastAPI App with OpenAPI Configuration
from api.openapi_config import (
    get_openapi_config,
    get_security_schemes,
)

app = FastAPI(
    **get_openapi_config(),
    lifespan=lifespan,
)

# =============================================================================
# ROUTE REGISTRATION
# =============================================================================

# Register Observability Router (GMP-91)
if _has_observability_router:
    app.include_router(observability_router, prefix="/api")

# Register Evaluation Router (GMP-WIRE-VC-EQ)
if _has_evaluation_router:
    app.include_router(evaluation_router, prefix="/api")


# Add security schemes to OpenAPI schema
def custom_openapi() -> dict:
    """Generate custom OpenAPI schema with security schemes.

    Adds API key authentication to all non-health endpoints
    and caches the schema for subsequent requests.

    Returns:
        OpenAPI schema dictionary with security schemes applied.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = app.openapi()
    openapi_schema["components"]["securitySchemes"] = get_security_schemes()

    # Apply security to all endpoints by default
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if method in ["get", "post", "put", "delete", "patch"]:
                # Skip health endpoints from requiring auth in docs
                if "health" not in path:
                    openapi_schema["paths"][path][method]["security"] = [
                        {"ApiKeyAuth": []}
                    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# =============================================================================
# Global Exception Handler with Neo4j Error Tracking
# =============================================================================
from fastapi import Request
from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
@must_stay_async("FastAPI/ASGI route handler")
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that logs errors to Neo4j for causality tracking.
    """
    # Log to Neo4j (best-effort, non-blocking)
    try:
        import asyncio

        from core.error_tracking import log_error_to_graph

        asyncio.create_task(
            log_error_to_graph(
                error=exc,
                context={
                    "endpoint": str(request.url.path),
                    "method": request.method,
                },
                source=f"api:{request.url.path}",
            )
        )
    except ImportError:
        pass  # Error tracking not available
    except Exception:
        pass  # Don't fail request due to error tracking

    # Standard error response
    logger.error(f"Unhandled exception at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Basic Root
@app.get("/")
def root() -> dict:
    """Root endpoint returning L9 API status and feature flags.

    Returns:
        Dict with status, version, and enabled features.
    """
    return {
        "status": "L9 Phase 2 AI OS",
        "version": "0.5.0",
        "features": {
            "memory_substrate": True,
            "quantum_research": _has_research,
            "slack_adapter": _has_slack,
            "world_model": _has_world_model,
            "agent_executor": _has_agent_executor,
            "aios_runtime": _has_aios_runtime,
            "tool_registry": _has_tool_registry,
            "research_factory": _has_factory,
            "email_agent": _has_email_agent,
            "commands_interface": _has_commands,
            "tools_router": _has_tools_router,
            "symbolic_computation": _has_symbolic,
        },
    }


# Health Check (Docker healthcheck endpoint)
@app.get("/health")
@must_stay_async("FastAPI/ASGI route handler")
async def health():
    """
    Root health check endpoint for Docker healthchecks and load balancers.
    Returns basic status without requiring authentication.

    Includes startup readiness gate (v3.4+ / GMP-KERNEL-BOOT).
    """
    startup_ready = getattr(app.state, "startup_ready", False)
    startup_result = getattr(app.state, "session_startup_result", None)

    # Determine overall health status
    status = "ok" if startup_ready else "degraded"

    response = {
        "status": status,
        "service": "l9-api",
        "startup_ready": startup_ready,
    }

    # Include startup details if available
    if startup_result:
        response["startup"] = {
            "status": startup_result.status,
            "preflight_passed": startup_result.preflight_passed,
            "kernels_ready": startup_result.kernels_ready,
            "files_loaded": len(startup_result.files_loaded),
            "errors_count": len(startup_result.errors) if startup_result.errors else 0,
        }

    return response


# Detailed Startup Health Check (v3.4+ / GMP-KERNEL-BOOT)
@app.get("/health/startup")
@must_stay_async("FastAPI/ASGI route handler")
async def startup_health():
    """
    Detailed startup health check endpoint.
    Returns full SessionStartup result including kernel hash snapshot.
    """
    startup_result = getattr(app.state, "session_startup_result", None)
    startup_ready = getattr(app.state, "startup_ready", False)

    if startup_result is None:
        return {
            "status": "unknown",
            "message": "SessionStartup not executed or not available",
            "startup_ready": startup_ready,
        }

    return {
        "status": startup_result.status,
        "startup_ready": startup_ready,
        "preflight_passed": startup_result.preflight_passed,
        "kernels_ready": startup_result.kernels_ready,
        "files_loaded": startup_result.files_loaded,
        "files_failed": startup_result.files_failed,
        "errors": startup_result.errors,
        "warnings": startup_result.warnings,
        "kernel_hash_snapshot": startup_result.kernel_hash_snapshot,
    }


# Kernel Reload Endpoint (v3.4+ / GMP-KERNEL-BOOT)
class KernelReloadRequest(BaseModel):
    """Request body for kernel reload."""

    force: bool = False


class KernelReloadResponse(BaseModel):
    """Response from kernel reload."""

    success: bool
    kernels_reloaded: int
    modified_kernels: list[str]
    errors: list[str]
    message: str


@app.post("/kernels/reload", response_model=KernelReloadResponse)
async def reload_kernels_endpoint(
    request: KernelReloadRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Hot-reload kernels without restarting the server.

    This endpoint:
    1. Checks which kernels have been modified on disk
    2. Re-loads modified kernels (or all if force=True)
    3. Re-activates the agent with new kernel data
    4. Logs the evolution to memory substrate

    Requires API key authentication.

    WARNING: This is a potentially disruptive operation.
    The agent's kernel_state will briefly transition to RELOADING.
    """
    try:
        from core.kernels.kernelloader import reload_kernels
        from core.memory.runtime import log_kernel_evolution
    except ImportError as e:
        return KernelReloadResponse(
            success=False,
            kernels_reloaded=0,
            modified_kernels=[],
            errors=[f"Kernel reload module not available: {e!s}"],
            message="Kernel reload not available",
        )

    # Get the agent registry
    agent_registry = getattr(app.state, "agent_registry", None)
    if agent_registry is None or not hasattr(agent_registry, "get_l_cto_agent"):
        return KernelReloadResponse(
            success=False,
            kernels_reloaded=0,
            modified_kernels=[],
            errors=["Agent registry not available or not kernel-aware"],
            message="Cannot reload: no kernel-aware agent registry",
        )

    # Get the L-CTO agent
    try:
        l_cto_agent = agent_registry.get_l_cto_agent()
        if l_cto_agent is None:
            return KernelReloadResponse(
                success=False,
                kernels_reloaded=0,
                modified_kernels=[],
                errors=["L-CTO agent not available"],
                message="Cannot reload: L-CTO agent not initialized",
            )
    except Exception as e:
        return KernelReloadResponse(
            success=False,
            kernels_reloaded=0,
            modified_kernels=[],
            errors=[f"Failed to get L-CTO agent: {e!s}"],
            message="Cannot reload: agent retrieval failed",
        )

    # Perform the reload
    try:
        result = reload_kernels(l_cto_agent, force=request.force)

        # Log evolution to memory substrate
        try:
            await log_kernel_evolution(
                event_type="RELOAD",
                agent_id=getattr(l_cto_agent, "agent_id", "l-cto"),
                kernel_ids=list(result.new_hashes.keys()),
                previous_hashes=result.previous_hashes,
                new_hashes=result.new_hashes,
                modified_kernels=result.modified_kernels,
                trigger="manual",
                success=result.success,
                errors=result.errors,
                metadata={"force": request.force},
            )
        except Exception as log_error:
            logger.warning("kernel_reload.evolution_log_failed", error=str(log_error))

        if result.success:
            return KernelReloadResponse(
                success=True,
                kernels_reloaded=result.kernels_reloaded,
                modified_kernels=result.modified_kernels,
                errors=result.errors,
                message=f"Successfully reloaded {result.kernels_reloaded} kernels",
            )
        return KernelReloadResponse(
            success=False,
            kernels_reloaded=result.kernels_reloaded,
            modified_kernels=result.modified_kernels,
            errors=result.errors,
            message="Kernel reload failed",
        )

    except Exception as e:
        logger.error("kernel_reload.endpoint_error", error=str(e), exc_info=True)
        return KernelReloadResponse(
            success=False,
            kernels_reloaded=0,
            modified_kernels=[],
            errors=[str(e)],
            message=f"Kernel reload failed with exception: {e!s}",
        )


# Neo4j Health Check
@app.get("/health/neo4j")
async def neo4j_health():
    """
    Neo4j graph database health check.
    Returns healthy if connected, unavailable if not configured.
    Includes graph feature status flags.
    """
    if not hasattr(app.state, "neo4j_client") or not app.state.neo4j_client:
        return {"status": "unavailable", "message": "Neo4j not configured"}

    try:
        result = await app.state.neo4j_client.run_query("RETURN 1 as check")
        if result:
            return {
                "status": "healthy",
                "neo4j": True,
                "graph_state_enabled": getattr(app.state, "graph_state_enabled", False),
                "agent_graph_loader": getattr(app.state, "agent_graph_loader", None)
                is not None,
                "graph_hydrator": getattr(app.state, "graph_hydrator", None)
                is not None,
                "agent_self_modify_tool": getattr(
                    app.state, "agent_self_modify_tool", None
                )
                is not None,
            }
        return {"status": "unhealthy", "message": "Query returned no results"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# Services Health Check (GMP-WIRE-B: Category B wiring)
@app.get("/health/services")
async def services_health():
    """
    Internal services health check.
    Returns status of optional services initialized at startup.
    """
    # GMP-78 Phase 2: Include dynamic tool discovery status
    tool_discovery_status = {
        "synced": getattr(app.state, "tool_embeddings_synced", False),
        "tool_count": getattr(app.state, "tool_embedding_count", 0),
    }

    # Get dynamic discovery settings
    try:
        from config.settings import get_integration_settings

        settings = get_integration_settings()
        tool_discovery_status["enabled"] = settings.l9_dynamic_tool_discovery
        tool_discovery_status["top_k"] = settings.l9_tool_discovery_top_k
    except Exception:
        tool_discovery_status["enabled"] = False

    return {
        "status": "ok",
        "services": {
            "housekeeping_engine": {
                "available": getattr(app.state, "housekeeping_engine", None)
                is not None,
            },
            "virtual_context_manager": {
                "available": getattr(app.state, "virtual_context_manager", None)
                is not None,
            },
            "consolidation_service": {
                "available": getattr(app.state, "consolidation_service", None)
                is not None,
            },
            "observability_service": {
                "available": getattr(app.state, "observability_service", None)
                is not None,
            },
            "dynamic_tool_discovery": tool_discovery_status,
        },
    }


# Checkpoint Health Check (GMP-105 Batch 2: Pool Monitoring)
@app.get("/health/checkpoint")
async def checkpoint_health():
    """
    Checkpoint system health check.
    Returns pool statistics and checkpoint system status.

    Pool stats are updated by L9RetryablePostgresSaver when available.
    """
    from memory.checkpoint_metrics import PROMETHEUS_AVAILABLE, get_pool_stats_dict

    pool_stats = get_pool_stats_dict()

    # Try to get live stats from checkpoint saver if available
    checkpoint_saver = getattr(app.state, "checkpoint_saver", None)
    live_stats = None
    if checkpoint_saver and hasattr(checkpoint_saver, "get_pool_stats"):
        with suppress(Exception):
            live_stats = checkpoint_saver.get_pool_stats()

    return {
        "status": "ok",
        "checkpoint_system": {
            "prometheus_available": PROMETHEUS_AVAILABLE,
            "pool_stats": live_stats or pool_stats,
            "saver_available": checkpoint_saver is not None,
        },
    }


# Chat endpoint (from server_memory.py for compatibility)
class ChatRequest(BaseModel):
    message: str
    system_prompt: str | None = None


class ChatResponse(BaseModel):
    reply: str


# =============================================================================
# L-CTO Agent Chat Endpoint (kernel-aware via AgentExecutorService)
# =============================================================================

from typing import Any

from pydantic import Field


class LChatRequest(BaseModel):
    """Request for L-CTO agent chat via AgentExecutorService."""

    message: str = Field(..., description="User message to send to L")
    thread_id: str | None = Field(
        None, description="Thread identifier for conversation grouping"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class LChatResponse(BaseModel):
    """Response from L-CTO agent chat."""

    reply: str = Field(..., description="Agent reply content")
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(
        ..., description="Execution status (completed, duplicate, failed)"
    )


@app.post("/lchat", response_model=LChatResponse)
async def lchat(
    request: LChatRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
):
    """
    L-CTO agent chat endpoint using AgentExecutorService.

    Routes messages through the kernel-aware agent stack:
    AgentTask -> AgentExecutorService -> AIOSRuntime

    This is the recommended endpoint for interacting with L.
    """
    # Check if agent executor is available
    if not _has_agent_executor:
        raise HTTPException(
            status_code=503,
            detail="Agent executor not available. L-CTO agent stack not initialized.",
        )

    agent_executor = getattr(app.state, "agent_executor", None)
    if agent_executor is None:
        raise HTTPException(
            status_code=503,
            detail="Agent executor not initialized. Check server startup logs.",
        )

    # Construct AgentTask for L-CTO
    # Use deterministic thread identifier fallback
    thread_identifier = request.thread_id or "http-default"

    task = AgentTask(
        agent_id="l-cto",
        agent_type=AgentType.ASSISTANT,
        source_id="http",
        thread_identifier=thread_identifier,
        payload={
            "message": request.message,
            "channel": "http",
            "metadata": request.metadata,
        },
    )

    logger.info(
        "lchat: task_id=%s, agent_id=%s, thread=%s",
        str(task.id),
        task.agent_id,
        thread_identifier,
    )

    # Execute task via AgentExecutorService
    try:
        result = await agent_executor.start_agent_task(task)
    except Exception as e:
        logger.exception("lchat: execution failed: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Agent execution error: {e}"
        ) from e

    # Handle duplicate detection
    if isinstance(result, DuplicateTaskResponse):
        logger.info("lchat: duplicate task detected: %s", str(result.task_id))
        return LChatResponse(
            reply="Duplicate task",
            task_id=str(result.task_id),
            status="duplicate",
        )

    # Handle ExecutionResult
    if isinstance(result, ExecutionResult):
        reply = result.result or result.error or "No response"
        return LChatResponse(
            reply=reply,
            task_id=str(result.task_id),
            status=result.status,
        )

    # Fallback (should not happen)
    logger.warning("lchat: unexpected result type: %s", type(result))
    return LChatResponse(
        reply="Unexpected result format",
        task_id=str(task.id),
        status="error",
    )


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
chat_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# =============================================================================
# Legacy /chat endpoint REMOVED
# =============================================================================
# REMOVED: Legacy /chat endpoint has been deleted.
# Use POST /lchat for kernel-aware agent execution via AgentExecutorService.
# See api/agent_routes.py for the modern implementation.

# --- Routers ---

# Phase 2 Auto-Wiring: Wire auto-registered routers first
# Routers using @router_registry.register() are wired automatically
try:
    auto_wired_count = router_registry.wire_all(app)
    if auto_wired_count > 0:
        logger.info(f"Auto-wired {auto_wired_count} routers via router_registry")
except Exception as e:
    logger.warning(f"Router auto-wiring failed: {e}")

# Prometheus metrics endpoint
if _has_prometheus:
    try:
        metrics_app = prometheus_make_asgi_app()
        app.mount("/metrics", metrics_app)
        logger.info("Prometheus metrics endpoint registered at /metrics")
    except Exception as e:
        logger.warning(f"Failed to mount Prometheus metrics endpoint: {e}")


# Startup + Shutdown events (if the modules expose them)
# NOTE: Migrations and memory init are handled in lifespan() above
@app.on_event("startup")
async def on_startup():
    """Handle FastAPI startup event.

    Invokes agent_routes.startup() if available to initialize
    agent-specific resources after the main lifespan startup.
    """
    if hasattr(agent_routes, "startup"):
        await agent_routes.startup()


@app.on_event("shutdown")
async def on_shutdown():
    """Handle FastAPI shutdown event.

    Invokes agent_routes.shutdown() if available to cleanup
    agent-specific resources before the main lifespan shutdown.
    """
    if hasattr(agent_routes, "shutdown"):
        await agent_routes.shutdown()


# =============================================================================
# WebSocket Agent Endpoint
# =============================================================================

from core.schemas.event_stream import AgentHandshake

# Import the shared singleton orchestrator instance
from runtime.websocket_orchestrator import verify_ws_token, ws_orchestrator

# =============================================================================
# WebSocket Authentication Helper
# =============================================================================
# REMOVED: verify_websocket_auth() has been replaced by verify_ws_token()
# from runtime.websocket_orchestrator for unified authentication.
# See runtime/websocket_orchestrator.py for the canonical implementation.


@app.websocket("/ws/agent")
async def agent_ws_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket entrypoint for L9 Mac Agents and other workers.

    Protocol:
    1) Client connects with auth token (query param: ?token=... or in handshake).
    2) Server validates auth BEFORE accepting connection.
    3) Client sends AgentHandshake JSON.
    4) Server validates handshake and registers the agent_id.
    5) Subsequent frames are EventMessage JSON payloads.
    6) On disconnect, agent is automatically unregistered.

    Requires authentication via L9_EXECUTOR_API_KEY.

    Example client connection:
        import websockets
        import json

        async with websockets.connect("ws://localhost:8000/ws/agent?token=YOUR_API_KEY") as ws:
            # Step 1: Send handshake
            await ws.send(json.dumps({
                "agent_id": "mac-agent-1",
                "agent_version": "1.0.0",
                "capabilities": ["shell", "memory_read"]
            }))

            # Step 2: Send/receive events
            await ws.send(json.dumps({
                "type": "heartbeat",
                "agent_id": "mac-agent-1",
                "payload": {"running_tasks": 0}
            }))
    """
    # Validate auth BEFORE accept (enforced security gate)
    token = websocket.query_params.get("token")
    if not await verify_ws_token(websocket, token):
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await websocket.accept()
    agent_id: str | None = None

    try:
        # Step 1: Wait for handshake
        raw = await websocket.receive_json()
        handshake = AgentHandshake.model_validate(raw)

        # Verify token in handshake message too (if provided)
        if handshake.auth_token:
            if not await verify_ws_token(websocket, handshake.auth_token):
                await websocket.close(code=1008, reason="Invalid auth token")
                return
            # Use handshake token if query param wasn't provided
            if not token:
                token = handshake.auth_token

        agent_id = handshake.agent_id

        # Register with orchestrator (store handshake metadata)
        await ws_orchestrator.register(
            agent_id,
            websocket,
            metadata={
                "agent_version": handshake.agent_version,
                "capabilities": handshake.capabilities,
                "hostname": handshake.hostname,
                "platform": handshake.platform,
            },
        )

        # Step 2: Message loop
        while True:
            data = await websocket.receive_json()

            # Ingest WebSocket event as packet (canonical memory entrypoint)
            # NOTE: payload is intentionally dict[str, Any] per Memory.yaml v1.0.1 contract.
            # This is NOT unsafe deserialization - Pydantic validates structure, and the
            # untyped payload boundary is by design to accept arbitrary agent messages.
            # Static analysis warnings about "unsafe deserialization" are FALSE POSITIVES.
            try:
                from core.schemas import PacketEnvelopeIn
                from memory.ingestion import ingest_packet

                packet_in = PacketEnvelopeIn(
                    packet_type="websocket_event",
                    payload=data,  # Intentional: untyped JSON boundary
                    metadata={"agent": agent_id, "source": "websocket"},
                )
                await ingest_packet(packet_in)
            except Exception as e:
                # Log but don't fail WebSocket handling if memory ingestion fails
                logger.warning(f"Failed to ingest WebSocket event: {e}")

            await ws_orchestrator.handle_incoming(agent_id, data)

    except WebSocketDisconnect:
        # Clean disconnect
        if agent_id:
            await ws_orchestrator.unregister(agent_id)
    except Exception as exc:
        # Unexpected error - log and cleanup
        logger.error(
            "WebSocket error for agent %s: %s",
            agent_id or "unknown",
            exc,
            exc_info=True,
        )
        if agent_id:
            await ws_orchestrator.unregister(agent_id)


# =============================================================================
# L-CTO Agent WebSocket Endpoint (kernel-aware via AgentExecutorService)
# =============================================================================


@app.websocket("/lws")
async def l_ws(websocket: WebSocket) -> None:
    """
    WebSocket entrypoint for L-CTO agent interactions.

    Routes messages through kernel-aware agent stack via ws_orchestrator:
    WebSocket → ws_orchestrator.handle_conversation_task() → AgentExecutorService → AIOSRuntime

    Protocol:
    1) Client connects with auth token (query param: ?token=...).
    2) Server validates auth BEFORE accepting connection (enforced gate).
    3) Client sends JSON frames with:
       - message: str (required)
       - thread_id: str (optional, for conversation grouping)
       - metadata: dict (optional)
    4) Server executes via AgentExecutorService and returns:
       - task_id: str
       - status: str (completed, duplicate, failed, error)
       - reply: str

    Requires authentication via L9_EXECUTOR_API_KEY.

    Example client:
        import websockets
        import json

        async with websockets.connect("ws://localhost:8000/lws?token=YOUR_API_KEY") as ws:
            await ws.send(json.dumps({
                "message": "What is L9?",
                "thread_id": "my-session-123"
            }))
            response = json.loads(await ws.recv())
            print(response["reply"])
    """
    # Validate auth BEFORE accept (enforced security gate)
    token = websocket.query_params.get("token")
    if not await verify_ws_token(websocket, token):
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await websocket.accept()

    # Register as conversation client with orchestrator
    # Use unique client ID based on websocket object ID
    client_id = f"lws-{id(websocket)}"
    await ws_orchestrator.register(
        client_id, websocket, metadata={"type": "conversation", "endpoint": "/lws"}
    )

    try:
        # Message loop - orchestrator handles routing
        while True:
            try:
                data = await websocket.receive_json()
            except Exception as recv_err:
                logger.warning("lws: failed to receive JSON: %s", str(recv_err))
                break

            # Tag as conversation type and route through orchestrator
            data["type"] = "conversation"
            await ws_orchestrator.handle_incoming(client_id, data)

    except WebSocketDisconnect:
        logger.debug("lws: client disconnected: %s", client_id)
    except Exception as exc:
        logger.error("lws: unexpected error: %s", str(exc), exc_info=True)
    finally:
        # Cleanup connection
        await ws_orchestrator.unregister(client_id)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "agents.cursor.gmp_meta_learning",
        "agents.cursor.integrations.cursor_executor",
        "agents.cursor.integrations.cursor_gateway",
        "agents.cursor.integrations.cursor_langgraph",
        "agents.reflection_agent",
    ],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "auth",
        "authorization",
        "batch-processing",
        "caching",
        "debugging",
        "endpoint",
        "event-driven",
    ],
    "keywords": [
        "agent",
        "auth",
        "chat",
        "consolidation",
        "cursor",
        "deps",
        "endpoint",
        "global",
    ],
    "business_value": "REST API endpoints for OS, agent, and memory operations WebSocket endpoint for real-time agent communication World model API (optional, v1.1.0+) Version: 0.5.0 (Research Factory Integration)",
    "last_modified": "2026-01-18T02:40:22Z",
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
