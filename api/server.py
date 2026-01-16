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

from config.settings import settings

import os
from datetime import datetime
import structlog
from contextlib import asynccontextmanager

# Initialize logger early for import error handling
logger = structlog.get_logger(__name__)
from fastapi import (  # noqa: E402
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Depends,
    Header,
)
from pydantic import BaseModel
from openai import OpenAI
from api.memory.router import router as memory_router
from api.memory.graph import router as graph_router
from api.memory.cache import router as cache_router
from api.auth import verify_api_key
import api.db as db
import api.os_routes as os_routes
import api.agent_routes as agent_routes

# Telemetry / Prometheus metrics
try:
    from telemetry.memory_metrics import init_metrics, PROMETHEUS_AVAILABLE
    from prometheus_client import make_asgi_app as prometheus_make_asgi_app

    _has_prometheus = PROMETHEUS_AVAILABLE
except ImportError:
    _has_prometheus = False

    def init_metrics():
        return False


# Optional: World Model API (v1.1.0+)
try:
    from api.world_model_api import router as world_model_router

    _has_world_model = True
except ImportError:
    _has_world_model = False

# World Model Query Routes (GMP-18)
try:
    from api.routes.worldmodel import router as worldmodel_query_router

    _has_worldmodel_query = True
except ImportError:
    _has_worldmodel_query = False

# Optional: Slack Adapter (v2.0+)
try:
    from api.routes.slack import router as slack_router
    from api.slack_adapter import SlackRequestValidator
    from api.slack_client import SlackAPIClient
    import httpx

    _has_slack = True
except ImportError:
    _has_slack = False

# Optional: Modules Status Router (GMP-45)
try:
    from api.routes.modules import router as modules_router

    _has_modules_router = True
except ImportError:
    _has_modules_router = False

# Optional: Quantum Research Factory (v2.1+)
try:
    from services.research.research_api import router as research_router
    from services.research.graph_runtime import init_runtime, shutdown_runtime

    _has_research = True
except ImportError:
    _has_research = False

# Optional: World Model Runtime (v2.5+)
try:
    from world_model.runtime import (
        create_runtime_with_substrate,
        get_or_create_runtime,
        WorldModelRuntime,
        RuntimeConfig,
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
        DuplicateTaskResponse,
        ExecutionResult,
        TaskKind,
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

# Optional: Research Factory (v2.3+)
try:
    from api.routes.factory import router as factory_router

    _has_factory = True
except ImportError:
    _has_factory = False

# Optional: Igor Command Interface (v2.7+ / GMP-11)
try:
    from api.routes.commands import router as commands_router

    _has_commands = True
except ImportError:
    _has_commands = False

# Optional: Tools Router (v2.8+ / Wire Orchestrators)
try:
    from api.tools.router import router as tools_router

    _has_tools_router = True
except ImportError:
    _has_tools_router = False

# Optional: Reasoning Orchestrator (v3.5+ / Stage 2.6 Phase 2)
try:
    from api.routes.reasoning import router as reasoning_router
    from orchestrators.reasoning.orchestrator import ReasoningOrchestrator

    _has_reasoning = True
except ImportError:
    _has_reasoning = False

# Optional: Pattern Orchestrator (v4.0+ / Agent Pattern System)
try:
    from api.routes.pattern import router as pattern_router
    from orchestrators.pattern import PatternOrchestrator, CellAgentAdapter

    _has_pattern = True
except ImportError:
    _has_pattern = False

# Optional: ResearchSwarm Orchestrator (v3.5+ / Stage 2.6 Phase 3)
try:
    from api.routes.research import router as research_swarm_router
    from orchestrators.research_swarm.orchestrator import ResearchSwarmOrchestrator

    _has_research_swarm = True
except ImportError:
    _has_research_swarm = False

# Optional: Cursor Executor (GMP-48)
try:
    from api.routes.cursor import router as cursor_router
    from agents.cursor.integrations.cursor_executor import CursorExecutor
    from agents.cursor.integrations.cursor_gateway import CursorMemoryGateway
    from agents.cursor.integrations.cursor_langgraph import build_cursor_langgraph
    from memory.checkpoint.cursor_checkpoint_manager import CursorCheckpointManager
    from memory.checkpoint.postgres_saver import L9PostgresSaver
    from memory.substrate_dag_wrapper import SubstrateDagOrchestrator
    from memory.substrate_dag import SubstrateDAG
    from core.governance.approval_manager import ApprovalManager
    from config.cursor_langgraph_config import get_cursor_langgraph_config

    _has_cursor_executor = True
except ImportError as e:
    logger.debug(f"Cursor Executor not available: {e}")
    _has_cursor_executor = False

# Optional: Governance Engine (v2.4+)
try:
    from core.governance.engine import GovernanceEngineService, create_governance_engine
    from core.governance.loader import PolicyLoadError, InvalidPolicyError

    _has_governance = True
except ImportError:
    _has_governance = False

# Optional: Symbolic Computation Service (v2.9+ / GMP-SYMPY-TASK4)
try:
    from services.symbolic_computation.api.routes import router as symbolic_router

    _has_symbolic = True
except ImportError:
    _has_symbolic = False

# Optional: Kernel-Aware Agent Registry (v2.5+)
try:
    from core.agents.kernel_registry import (
        create_kernel_aware_registry,
        KernelAwareAgentRegistry,
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

    _has_graph_agent_state = True
except ImportError:
    _has_graph_agent_state = False

# Optional: Five-Tier Observability (v3.3+ GMP-OBS-DEPLOY)
L9_OBSERVABILITY = settings.l9_observability
try:
    from core.observability.service import (
        initialize_observability,
        ObservabilityService,
    )
    from core.observability.l9_integration import (
        instrument_agent_executor,
        instrument_tool_registry,
        instrument_governance_engine,
        instrument_memory_substrate,
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
    from core.evaluation.evaluator import Evaluator

    _has_evaluator = True
except ImportError:
    _has_evaluator = False

# Optional: Calendar Adapter (v2.6+)
try:
    from api.adapters.calendar_adapter.routes.calendar_adapter import (
        router as calendar_adapter_router,
    )
    from api.adapters.calendar_adapter.config import get_config as get_calendar_config

    _has_calendar_adapter = True
except ImportError:
    _has_calendar_adapter = False

# Optional: Email Adapter (v2.6+)
try:
    from api.adapters.email_adapter.routes.email_adapter import (
        router as email_adapter_router,
    )
    from api.adapters.email_adapter.config import get_config as get_email_config

    _has_email_adapter = True
except ImportError:
    _has_email_adapter = False

# Optional: Twilio Adapter (v2.6+)
try:
    from api.adapters.twilio_adapter.routes.twilio_adapter import (
        router as twilio_adapter_router,
    )
    from api.adapters.twilio_adapter.config import get_config as get_twilio_config

    _has_twilio_adapter = True
except ImportError:
    _has_twilio_adapter = False

# Optional: Email Agent (Gmail multi-account)
# Toggleable via EMAIL_AGENT_ENABLED=false in .env
_has_email_agent = False
if settings.email_agent_enabled:
    try:
        from email_agent.router import router as email_agent_router

        _has_email_agent = True
    except ImportError as e:
        logger.warning(f"Email Agent import failed: {e}")
        _has_email_agent = False
else:
    logger.info("Email Agent DISABLED via EMAIL_AGENT_ENABLED=false")

# Note: Slack handled by api/routes/slack.py → memory/slack_ingest.py

# Optional: Housekeeping Engine (v2.4+)
try:
    from memory.housekeeping import HousekeepingEngine, init_housekeeping_engine

    _has_housekeeping = True
except ImportError:
    _has_housekeeping = False

# Optional: Mac Agent API (from centralized settings)
_has_mac_agent = settings.mac_agent_enabled

# Optional: WABA/WhatsApp (from centralized settings)
_has_waba = settings.waba_enabled

# Memory system imports
from memory.migration_runner import run_migrations
from memory.substrate_service import init_service, close_service
from memory.agent_persistence import AgentPersistenceService

# Integration settings
logger = structlog.get_logger(__name__)

# Development mode flag (from centralized settings)
LOCAL_DEV = settings.local_dev

# GMP v2.0 Learning Engine (global, initialized in lifespan if enabled)
gmp_learning_engine = None  # Type: Optional[GMPMetaLearningEngine]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Handles startup (migrations + memory init) and shutdown.
    """
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
        from core.moduleregistry import ModuleRegistry, ModuleDefinition

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
                db.init_db()

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
            # Store error for downstream diagnostics (Agent Executor will read this)
            app.state._substrate_init_error = str(e)
            app.state.substrate_service = None
            app.state.agent_persistence = None
            app.state.restored_agent_state = None

    # Initialize MCP Memory DB pool (for /mcp/call routes)
    # This is REQUIRED for MCP tools to work when routed through l9-api
    if database_url:
        try:
            import sys
            from pathlib import Path

            mcp_path = Path(__file__).parent.parent / "mcp_memory"
            if str(mcp_path) not in sys.path:
                sys.path.insert(0, str(mcp_path))

            from src.db import init_db as mcp_init_db
            from src.config import settings as mcp_settings

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
            # ========================================================================
            try:
                from core.tools.tool_embeddings import sync_all_tool_embeddings

                tool_embedding_count = await sync_all_tool_embeddings()
                logger.info(f"Tool embeddings synced: {tool_embedding_count} tools")
            except ImportError:
                logger.debug("Tool embeddings service not available (optional)")
            except Exception as e:
                # Non-fatal: semantic tool retrieval is an optimization
                logger.warning(f"Tool embedding sync failed (non-fatal): {e}")

            # ========================================================================
            # SESSION STARTUP: Preflight checks + kernel readiness gate (v3.4+)
            # ========================================================================
            app.state.session_startup_result = None
            app.state.startup_ready = False

            # Skip startup checks in container environments (broken symlinks, missing governance files)
            # Detection: L9_SKIP_STARTUP_CHECKS=true OR running in Docker (/app as cwd)
            skip_startup = settings.l9_skip_startup_checks
            in_container = str(Path.cwd()) == "/app" or os.path.exists("/.dockerenv")

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
                            startup_result.errors[:3]
                            if startup_result.errors
                            else "none",
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
                # In production, you might want to crash here
                # For dev, fall back to stub
                logger.warning("Falling back to stub agent registry")
                agent_registry = None
            except Exception as e:
                # Unexpected error during kernel registry creation
                logger.critical(
                    "FATAL: Unexpected error creating kernel registry: %s",
                    str(e),
                    exc_info=True,
                )
                logger.warning("Falling back to stub agent registry")
                agent_registry = None

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

            # Initialize WorldModelService (explicit, not lazy)
            try:
                from world_model.service import get_world_model_service

                world_model_service = get_world_model_service()
                app.state.world_model_service = world_model_service
                logger.info("WorldModelService initialized")
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

                    # 1. SubstrateDAG + Orchestrator
                    substrate_dag = SubstrateDAG(
                        repository=repository,
                        semantic_service=app.state.substrate_service._semantic_service,
                    )
                    dag_orchestrator = SubstrateDagOrchestrator(dag=substrate_dag)

                    # 2. Memory Gateway
                    memory_gateway = CursorMemoryGateway(
                        dag_orchestrator=dag_orchestrator
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
                        dag_orchestrator=dag_orchestrator,
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

    settings = get_integration_settings()

    # Check if legacy Slack router is disabled (new routing enabled)
    legacy_slack_enabled = getattr(settings, "l9_enable_legacy_slack_router", False)

    if not legacy_slack_enabled:
        # New Slack routing is enabled - agent_executor is REQUIRED
        agent_executor = getattr(app.state, "agent_executor", None)

        if agent_executor is None:
            logger.critical(
                "╔═══════════════════════════════════════════════════════════════╗\n"
                "║  CRITICAL: Agent Executor Initialization Failed              ║\n"
                "║                                                               ║\n"
                "║  The new Slack routing (L9_ENABLE_LEGACY_SLACK_ROUTER=False) ║\n"
                "║  requires AgentExecutorService to be initialized.            ║\n"
                "║                                                               ║\n"
                "║  Options:                                                     ║\n"
                "║  1. Fix agent_executor initialization (check logs above)     ║\n"
                "║  2. Set L9_ENABLE_LEGACY_SLACK_ROUTER=true in .env           ║\n"
                "║  3. Install missing dependencies: pip install -r requirements.txt ║\n"
                "╚═══════════════════════════════════════════════════════════════╝"
            )
            raise RuntimeError(
                "Agent Executor required for new Slack routing but failed to initialize. "
                "Set L9_ENABLE_LEGACY_SLACK_ROUTER=true or fix initialization."
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

    # Initialize Neo4j client (optional, graceful if unavailable)
    try:
        from memory.graph_client import get_neo4j_client, close_neo4j_client

        neo4j = await get_neo4j_client()
        if neo4j and neo4j.is_available():
            app.state.neo4j_client = neo4j
            logger.info("Neo4j graph client initialized")

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
        else:
            # Neo4j not available or not healthy
            app.state.neo4j_client = None
            logger.info("Neo4j not available - graph features disabled")
    except ImportError:
        app.state.neo4j_client = None
        logger.debug("Neo4j client not available")
    except Exception as e:
        app.state.neo4j_client = None
        logger.warning(f"Failed to initialize Neo4j: {e}")

    # Initialize Redis client (optional, graceful if unavailable)
    try:
        from runtime.redis_client import get_redis_client, close_redis_client

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
    app.state.l_cto_startup = None  # Kept for backward compatibility

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
                app.state.l_agent_ready = True

                logger.info(
                    "✓ L-CTO Agent Bootstrap complete",
                    instance_id=l_instance.instance_id[:12],
                    signature=l_instance.initialization_signature[:16]
                    if l_instance.initialization_signature
                    else "none",
                )
            else:
                logger.warning("Bootstrap skipped: substrate_service not available")
                app.state.l_agent_ready = False

        except Exception as e:
            logger.error("Agent Bootstrap failed: %s", str(e), exc_info=True)
            app.state.l_agent_ready = False
            # Non-fatal in dev mode - fall back to legacy initialization
    elif L9_NEW_AGENT_INIT:
        logger.warning("L9_NEW_AGENT_INIT=true but bootstrap module not available")
        app.state.l_agent_ready = False
    else:
        app.state.l_agent_ready = False  # Using legacy init

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
            app.state.memory_tools_registered = True
        else:
            logger.warning("⚠️ Memory tools not registered: tool_registry not available")
            app.state.memory_tools_registered = False
    except Exception as e:
        logger.error(f"❌ Memory tool registration failed: {e}", exc_info=True)
        app.state.memory_tools_registered = False

    # ========================================================================
    # STARTUP: Initialize Prometheus metrics
    # ========================================================================
    if _has_prometheus:
        metrics_ok = init_metrics()
        app.state.prometheus_enabled = metrics_ok
        if metrics_ok:
            logger.info("✓ Prometheus metrics initialized")
        else:
            logger.warning("⚠️ Prometheus metrics init returned False")
    else:
        app.state.prometheus_enabled = False
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
                # Pass neo4j_driver for graph state consolidation
                neo4j_for_vcm = getattr(app.state, "neo4j_client", None)
                virtual_context = VirtualContextManager(
                    substrate_service=substrate,
                    neo4j_driver=neo4j_for_vcm,
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
                evaluator = Evaluator(
                    substrate_service=substrate,
                )
                app.state.evaluator = evaluator
                logger.info("✓ Evaluator initialized (LLM-as-judge)")
            except Exception as e:
                logger.error(f"❌ Evaluator init failed: {e}", exc_info=True)
                app.state.evaluator = None
        else:
            app.state.evaluator = None
            if not _has_evaluator:
                logger.debug("Evaluator module not available")

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

                # Schedule background cleanup every 24 hours
                # NOTE: This loop is for MemoryConsolidationService (different from ConsolidationPipeline).
                # ConsolidationPipeline (v3.1) should be scheduled separately per memory_spec_v3.0.yaml:
                # schedule: weekly_saturday_2am_utc (see orchestrators/memory/housekeeping.py run_consolidation())
                async def run_consolidation_loop():
                    """Background task for periodic memory consolidation"""
                    consolidation_interval = (
                        settings.l9_consolidation_interval_hours * 3600
                    )
                    logger.info(
                        f"Memory consolidation scheduled every {consolidation_interval // 3600} hours"
                    )

                    while True:
                        try:
                            await asyncio.sleep(consolidation_interval)
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
                            if hasattr(
                                consolidation_service, "consolidate_graph_state"
                            ):
                                try:
                                    graph_result = await consolidation_service.consolidate_graph_state(
                                        "L"
                                    )
                                    logger.info(
                                        f"Graph state consolidation: {graph_result.get('status', 'UNKNOWN')}"
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f"Graph state consolidation failed: {e}"
                                    )
                        except asyncio.CancelledError:
                            logger.info("Consolidation loop cancelled")
                            break
                        except Exception as e:
                            logger.error(
                                f"Consolidation loop error: {e}", exc_info=True
                            )

                # Start background consolidation task
                app.state.consolidation_task = asyncio.create_task(
                    run_consolidation_loop()
                )
                logger.info(
                    "✓ MemoryConsolidationService initialized (24h cleanup cycle)"
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
    # STAGE 5: Graph-Backed Agent State (Neo4j REQUIRED)
    # ========================================================================
    if L9_GRAPH_AGENT_STATE and _has_graph_agent_state:
        logger.info("╔════════════════════════════════════════╗")
        logger.info("║  Stage 5: Graph-Backed Agent State     ║")
        logger.info("╚════════════════════════════════════════╝")

        # GMP-90: Neo4j is MANDATORY for graph agent state - fail loudly if unavailable
        neo4j_client = getattr(app.state, "neo4j_client", None)

        if neo4j_client is None:
            error_msg = (
                "L9_GRAPH_AGENT_STATE=true but Neo4j is unavailable. "
                "Neo4j is MANDATORY for graph-backed agent state. "
                "Either fix Neo4j connection or set L9_GRAPH_AGENT_STATE=false."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

        try:
            substrate = getattr(app.state, "substrate_service", None) or getattr(
                app.state, "memory_service", None
            )

            # Initialize AgentGraphLoader (uses neo4j_client)
            agent_graph_loader = AgentGraphLoader(neo4j_client)
            app.state.agent_graph_loader = agent_graph_loader
            logger.info("✓ AgentGraphLoader initialized")

            # Initialize GraphHydrator (with optional kernel stack)
            kernel_stack = getattr(app.state, "kernel_stack", None)
            graph_hydrator = GraphHydrator(
                neo4j_driver=neo4j_client,
                kernel_stack=kernel_stack,
            )
            app.state.graph_hydrator = graph_hydrator
            logger.info("✓ GraphHydrator initialized")

            # Initialize AgentSelfModifyTool
            self_modify_tool = create_self_modify_tool(
                neo4j_driver=neo4j_client,
                substrate_service=substrate,
            )
            app.state.agent_self_modify_tool = self_modify_tool
            logger.info("✓ AgentSelfModifyTool initialized")

            # Check if L exists in graph, bootstrap if not
            if await agent_graph_loader.exists("L"):
                logger.info("✓ L agent found in Neo4j graph")
            else:
                logger.warning("L agent not in graph - run migration script")
                logger.info("  python scripts/migrate_kernels_to_graph.py")

            logger.info("Stage 5 (Graph-Backed Agent State) complete")

        except Exception as e:
            error_msg = f"Stage 5 init failed: {e}"
            logger.critical(error_msg, exc_info=True)
            raise RuntimeError(error_msg)
            app.state.agent_self_modify_tool = None
    elif L9_GRAPH_AGENT_STATE and not _has_graph_agent_state:
        logger.warning("Stage 5 enabled but graph_state module not available")
    else:
        logger.debug("Stage 5 (Graph-Backed Agent State) disabled")

    # ========================================================================
    # STARTUP: UKG Phase 3 - Graph to World Model Sync (REQUIRES Neo4j)
    # ========================================================================
    L9_GRAPH_WM_SYNC = settings.l9_graph_wm_sync

    if L9_GRAPH_WM_SYNC:
        # GMP-90: Neo4j is MANDATORY for Graph-WM Sync - fail loudly if unavailable
        neo4j_for_sync = getattr(app.state, "neo4j_client", None)

        if neo4j_for_sync is None:
            error_msg = (
                "L9_GRAPH_WM_SYNC=true but Neo4j is unavailable. "
                "Neo4j is MANDATORY for graph features. "
                "Either fix Neo4j connection or set L9_GRAPH_WM_SYNC=false."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

        try:
            from core.integration.graph_to_wm_sync import (
                start_graph_wm_sync,
                get_graph_wm_sync,
            )

            await start_graph_wm_sync(neo4j_driver=neo4j_for_sync)
            app.state.graph_wm_sync = get_graph_wm_sync(neo4j_driver=neo4j_for_sync)
            logger.info("✅ UKG Phase 3: Graph-WM Sync started")
        except ImportError as e:
            error_msg = f"Graph-WM Sync module import failed: {e}"
            logger.critical(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Graph-WM Sync init failed: {e}"
            logger.critical(error_msg)
            raise RuntimeError(error_msg)
    else:
        logger.debug("Graph-WM Sync disabled (L9_GRAPH_WM_SYNC=false)")
        app.state.graph_wm_sync = None

    # ========================================================================
    # STARTUP: UKG Phase 3.5 - World Model to Graph Sync (causal data)
    # ========================================================================
    L9_WM_GRAPH_SYNC = os.getenv("L9_WM_GRAPH_SYNC", "true").lower() == "true"
    neo4j_for_wm_sync = getattr(app.state, "neo4j_client", None)

    if L9_WM_GRAPH_SYNC and neo4j_for_wm_sync is not None:
        try:
            from core.integration.wm_to_graph_sync import (
                start_wm_graph_sync,
                get_wm_graph_sync,
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
                logger.debug("Created standalone CausalMapper (world_model_service not available)")

            app.state.causal_mapper = causal_mapper

            await start_wm_graph_sync(
                neo4j_driver=neo4j_for_wm_sync,
                causal_mapper=app.state.causal_mapper,
            )
            app.state.wm_graph_sync = get_wm_graph_sync(
                neo4j_driver=neo4j_for_wm_sync,
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
                start_tool_pattern_extraction,
                get_tool_pattern_extractor,
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

            # Start background task to update Prometheus metrics periodically
            async def update_observability_metrics():
                """Periodically update Prometheus metrics from observability spans."""
                update_interval = 30  # Update every 30 seconds
                while True:
                    try:
                        await asyncio.sleep(update_interval)
                        if observability:
                            # Compute and update SRE metrics
                            metrics = await observability.compute_metrics()
                            # Update agent KPIs
                            await observability.update_agent_kpis()
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.debug(f"Observability metrics update failed: {e}")

            asyncio.create_task(update_observability_metrics())
            logger.info("Observability metrics update task started (30s interval)")
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
            from core.gmp import GMPMetaLearningEngine

            global gmp_learning_engine
            gmp_learning_engine = GMPMetaLearningEngine(database_url)
            await gmp_learning_engine.create_tables()
            app.state.gmp_learning_engine = gmp_learning_engine
            logger.info("GMP Learning Engine initialized (v2.0)")
        except ImportError as e:
            logger.debug(f"GMP Learning Engine not available: {e}")
            app.state.gmp_learning_engine = None
        except Exception as e:
            logger.error(f"GMP Learning Engine init failed: {e}", exc_info=True)
            app.state.gmp_learning_engine = None
    else:
        if not settings.l9_gmp_learning_enabled:
            logger.debug("GMP Learning disabled (L9_GMP_LEARNING_ENABLED=false)")
        elif not database_url:
            logger.debug("GMP Learning skipped (no database_url)")
        app.state.gmp_learning_engine = None

    yield

    # ========================================================================
    # SHUTDOWN: Clean up memory service and Slack adapter
    # ========================================================================
    logger.info("Shutting down L9 API server...")

    # Shutdown Five-Tier Observability (flush spans)
    if hasattr(app.state, "observability_service") and app.state.observability_service:
        try:
            await app.state.observability_service.shutdown()
            logger.info("Observability service shutdown complete")
        except Exception as e:
            logger.warning(f"Error shutting down observability: {e}")

    # Save agent checkpoints before shutdown
    if hasattr(app.state, "agent_persistence") and app.state.agent_persistence:
        try:
            default_agent_id = os.getenv("DEFAULT_AGENT_ID", "l9-standard-v1")
            shutdown_state = {
                "shutdown_timestamp": datetime.utcnow().isoformat(),
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
                try:
                    await app.state.event_processor_task
                except asyncio.CancelledError:
                    pass
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
                try:
                    await app.state.world_model_task
                except asyncio.CancelledError:
                    pass
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


# FastAPI App
app = FastAPI(
    title="L9 Phase 2 Secure AI OS",
    lifespan=lifespan,
)


# =============================================================================
# Global Exception Handler with Neo4j Error Tracking
# =============================================================================
from fastapi import Request
from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that logs errors to Neo4j for causality tracking.
    """
    # Log to Neo4j (best-effort, non-blocking)
    try:
        from core.error_tracking import log_error_to_graph
        import asyncio

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
def root():
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
            "calendar_adapter": _has_calendar_adapter,
            "email_adapter": _has_email_adapter,
            "email_agent": _has_email_agent,
            "twilio_adapter": _has_twilio_adapter,
            "commands_interface": _has_commands,
            "tools_router": _has_tools_router,
            "symbolic_computation": _has_symbolic,
        },
    }


# Health Check (Docker healthcheck endpoint)
@app.get("/health")
async def health():
    """
    Root health check endpoint for Docker healthchecks and load balancers.
    Returns basic status without requiring authentication.

    Includes startup readiness gate (v3.4+ / GMP-KERNEL-BOOT).
    """
    startup_ready = getattr(app.state, "startup_ready", False)
    startup_result = getattr(app.state, "session_startup_result", None)

    # Determine overall health status
    if startup_ready:
        status = "ok"
    else:
        status = "degraded"

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
            errors=[f"Kernel reload module not available: {str(e)}"],
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
            errors=[f"Failed to get L-CTO agent: {str(e)}"],
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
        else:
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
            message=f"Kernel reload failed with exception: {str(e)}",
        )


# Neo4j Health Check
@app.get("/health/neo4j")
async def neo4j_health():
    """
    Neo4j graph database health check.
    Returns healthy if connected, unavailable if not configured.
    """
    if not hasattr(app.state, "neo4j_client") or not app.state.neo4j_client:
        return {"status": "unavailable", "message": "Neo4j not configured"}

    try:
        result = await app.state.neo4j_client.run_query("RETURN 1 as check")
        if result:
            return {"status": "healthy", "neo4j": True}
        return {"status": "unhealthy", "message": "Query returned no results"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# Chat endpoint (from server_memory.py for compatibility)
class ChatRequest(BaseModel):
    message: str
    system_prompt: str | None = None


class ChatResponse(BaseModel):
    reply: str


# =============================================================================
# L-CTO Agent Chat Endpoint (kernel-aware via AgentExecutorService)
# =============================================================================

from typing import Any, Optional
from pydantic import Field


class LChatRequest(BaseModel):
    """Request for L-CTO agent chat via AgentExecutorService."""

    message: str = Field(..., description="User message to send to L")
    thread_id: Optional[str] = Field(
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
        kind=TaskKind.CONVERSATION,
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
        raise HTTPException(status_code=500, detail=f"Agent execution error: {e}")

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
if OPENAI_API_KEY:
    chat_client = OpenAI(api_key=OPENAI_API_KEY)
else:
    chat_client = None

# Legacy /chat route - gated by L9_ENABLE_LEGACY_CHAT flag
if settings.l9_enable_legacy_chat:

    @app.post("/chat", response_model=ChatResponse)
    async def chat(
        payload: ChatRequest,
        authorization: str = Header(None),
        _: bool = Depends(verify_api_key),
    ):
        """
        Basic LLM chat endpoint using OpenAI.
        Ingests both request and response to memory for audit trail.

        LEGACY: This route calls OpenAI directly. Use POST /lchat for
        kernel-aware agent execution via AgentExecutorService.
        """
        if not chat_client:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

        from memory.ingestion import ingest_packet
        from core.schemas import PacketEnvelopeIn

        try:
            messages = []
            if payload.system_prompt:
                messages.append({"role": "system", "content": payload.system_prompt})
            else:
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "You are L, an infrastructure-focused assistant connected to an L9 "
                            "backend and memory system. Be concise, precise, and avoid destructive "
                            "actions. When appropriate, suggest using tools like the CTO agent."
                        ),
                    }
                )
            messages.append({"role": "user", "content": payload.message})

            completion = chat_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
            )
            reply = completion.choices[0].message.content

            # Ingest chat interaction to memory (audit trail)
            try:
                packet_in = PacketEnvelopeIn(
                    packet_type="chat_interaction",
                    payload={
                        "user_message": payload.message,
                        "system_prompt": payload.system_prompt,
                        "assistant_reply": reply,
                        "model": "gpt-4.1-mini",
                    },
                    metadata={"agent": "chat_api", "source": "server"},
                )
                await ingest_packet(packet_in)
            except Exception as mem_err:
                # Log but don't fail the request if memory ingestion fails
                logger.warning(f"Failed to ingest chat to memory: {mem_err}")

            return ChatResponse(reply=reply)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chat backend error: {e}")

    logger.info("Legacy /chat route registered (L9_ENABLE_LEGACY_CHAT=true)")
else:
    logger.info("Legacy /chat route DISABLED (L9_ENABLE_LEGACY_CHAT=false)")

# --- Routers ---
# OS health + metrics + routing
app.include_router(os_routes.router, prefix="/os")

# Background agent tasking
app.include_router(agent_routes.router, prefix="/agent")

# Modules status router (GMP-45)
if _has_modules_router:
    app.include_router(modules_router)
    logger.info("Modules router registered at /modules")

# Persistent memory router
app.include_router(memory_router, prefix="/api/v1/memory")

# Graph router (Neo4j) - for cursor_memory_client.py
app.include_router(graph_router, prefix="/api/v1/memory/graph")

# Cache router (Redis) - for cursor_memory_client.py
app.include_router(cache_router, prefix="/api/v1/memory/cache")

# World Model router (v1.1.0+)
if _has_world_model:
    app.include_router(world_model_router)

# World Model Query router (GMP-18)
if _has_worldmodel_query:
    app.include_router(worldmodel_query_router)
    logger.info("World Model Query router registered at /worldmodel")

# Slack adapter router (v2.0+)
if _has_slack:
    app.include_router(slack_router)

# Quantum Research Factory router (v2.1+)
if _has_research:
    app.include_router(research_router)

# Research Factory router (v2.3+)
if _has_factory:
    app.include_router(factory_router)

# Igor Command Interface router (v2.7+ / GMP-11)
if _has_commands:
    app.include_router(commands_router)
    logger.info("Igor Command Interface registered at /commands")

# Tools router (v2.8+ / Wire Orchestrators)
if _has_tools_router:
    app.include_router(tools_router, prefix="/tools")
    logger.info("Tools router registered at /tools")

# Reasoning router (Stage 2.6 Phase 2)
if _has_reasoning:
    app.include_router(reasoning_router, prefix="/reasoning")
    logger.info("Reasoning router registered at /reasoning")

# Pattern router (Agent Pattern System v4.0+)
if _has_pattern:
    app.include_router(pattern_router, prefix="/pattern")
    logger.info("Pattern router registered at /pattern")

# ResearchSwarm router (Stage 2.6 Phase 3)
if _has_research_swarm:
    app.include_router(research_swarm_router, prefix="/research/swarm")
    logger.info("ResearchSwarm router registered at /research/swarm")

# Cursor Executor router (GMP-48)
if _has_cursor_executor:
    app.include_router(cursor_router, prefix="/cursor")
    logger.info("Cursor Executor router registered at /cursor")

# Compliance router (GMP-21)
try:
    from api.routes.compliance import router as compliance_router

    app.include_router(compliance_router)
    logger.info("Compliance router registered at /compliance")
except ImportError:
    logger.debug("Compliance router not available")

# Simulation router (GMP-24)
try:
    from api.routes.simulation import router as simulation_router

    app.include_router(simulation_router)
    logger.info("Simulation router registered at /simulation")
except ImportError:
    logger.debug("Simulation router not available")

# Symbolic Computation router (GMP-SYMPY-TASK4)
if _has_symbolic:
    app.include_router(symbolic_router)  # Router already has /symbolic prefix
    logger.info("Symbolic Computation router registered at /symbolic")

# Calendar Adapter router (v2.6+)
if _has_calendar_adapter:
    app.include_router(calendar_adapter_router)

# Email Adapter router (v2.6+)
if _has_email_adapter:
    app.include_router(email_adapter_router)

# Twilio Adapter router (v2.6+)
if _has_twilio_adapter:
    app.include_router(twilio_adapter_router)

# Slack Webhook Adapter (v2.6+) - NOT USED (using slack_router v2.0+ instead)
# Legacy webhook router - NOT USED (using slack_router v2.0+ instead)

# Mac Agent API
if _has_mac_agent:
    try:
        from api.webhook_mac_agent import router as mac_agent_router

        app.include_router(mac_agent_router)
    except Exception as e:
        logger.warning(f"Failed to load Mac Agent router: {e}")

# Twilio webhook router (legacy)
if _has_twilio_adapter:
    try:
        from api.webhook_twilio import router as twilio_webhook_router

        app.include_router(twilio_webhook_router)
    except Exception as e:
        logger.warning(f"Failed to load legacy Twilio webhook router: {e}")

# WABA (WhatsApp Business Account - native Meta) (legacy)
if _has_waba:
    try:
        from api.webhook_waba import router as waba_router

        app.include_router(waba_router)
    except Exception as e:
        logger.warning(f"Failed to load WABA router: {e}")

# Email Agent API (email_agent/router.py) - Gmail multi-account
if _has_email_agent:
    app.include_router(email_agent_router)
    logger.info("Email Agent router registered at /email/{account}/*")

# PacketEnvelope Upgrades API (Phases 2-5)
try:
    from api.routes.upgrades import router as upgrades_router

    app.include_router(upgrades_router, prefix="/api/v1")
    logger.info("PacketEnvelope upgrades router registered at /api/v1/upgrades")
except Exception as e:
    logger.warning(f"Failed to load PacketEnvelope upgrades router: {e}")

# MCP Memory Router (MCP Protocol endpoints)
try:
    from api.routes.mcp import router as mcp_router

    app.include_router(mcp_router)
    logger.info("MCP memory router registered at /mcp/*")
except Exception as e:
    logger.warning(f"Failed to load MCP router: {e}")

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
    if hasattr(agent_routes, "startup"):
        await agent_routes.startup()


@app.on_event("shutdown")
async def on_shutdown():
    if hasattr(agent_routes, "shutdown"):
        await agent_routes.shutdown()


# =============================================================================
# WebSocket Agent Endpoint
# =============================================================================

from core.schemas.event_stream import AgentHandshake

# Import the shared singleton orchestrator instance
from runtime.websocket_orchestrator import ws_orchestrator


# =============================================================================
# WebSocket Authentication Helper
# =============================================================================


async def verify_websocket_auth(
    websocket: WebSocket, token: Optional[str] = None
) -> bool:
    """
    Verify WebSocket authentication token.

    Token can be provided via:
    1. Query parameter: ?token=...
    2. Function parameter (from handshake message)

    Args:
        websocket: WebSocket connection
        token: Optional token from handshake message

    Returns:
        True if token is valid, False otherwise
    """
    from api.auth import EXECUTOR_API_KEY

    if not EXECUTOR_API_KEY:
        logger.warning("WebSocket auth: L9_EXECUTOR_API_KEY not configured")
        return False

    # Token can come from query params or function parameter
    if not token:
        query_token = websocket.query_params.get("token")
        if query_token:
            token = query_token

    if not token or token != EXECUTOR_API_KEY:
        return False

    return True


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
    # Validate auth BEFORE accept
    token = websocket.query_params.get("token")
    if not await verify_websocket_auth(websocket, token):
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
            if not await verify_websocket_auth(websocket, handshake.auth_token):
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
            try:
                from memory.ingestion import ingest_packet
                from core.schemas import PacketEnvelopeIn

                packet_in = PacketEnvelopeIn(
                    packet_type="websocket_event",
                    payload=data,
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

    Routes messages through the kernel-aware agent stack:
    AgentTask -> AgentExecutorService -> AIOSRuntime

    Protocol:
    1) Client connects with auth token (query param: ?token=...).
    2) Server validates auth BEFORE accepting connection.
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
            logger.info(response["reply"])
    """
    # Validate auth BEFORE accept
    token = websocket.query_params.get("token")
    if not await verify_websocket_auth(websocket, token):
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await websocket.accept()

    # Check if agent executor is available
    if not _has_agent_executor:
        await websocket.send_json(
            {
                "task_id": "",
                "status": "error",
                "reply": "Agent executor not available. L-CTO agent stack not initialized.",
            }
        )
        await websocket.close(code=1011, reason="Agent executor unavailable")
        return

    agent_executor = getattr(app.state, "agent_executor", None)
    if agent_executor is None:
        await websocket.send_json(
            {
                "task_id": "",
                "status": "error",
                "reply": "Agent executor not initialized. Check server startup logs.",
            }
        )
        await websocket.close(code=1011, reason="Agent executor not initialized")
        return

    try:
        # Message loop
        while True:
            try:
                data = await websocket.receive_json()
            except Exception as recv_err:
                logger.warning("lws: failed to receive JSON: %s", str(recv_err))
                break

            # Extract fields from frame
            message = data.get("message")
            if not message:
                await websocket.send_json(
                    {
                        "task_id": "",
                        "status": "error",
                        "reply": "Missing required field: message",
                    }
                )
                continue

            thread_id = data.get("thread_id") or "ws-default"
            metadata = data.get("metadata", {})

            # Build AgentTask for L-CTO
            try:
                task = AgentTask(
                    agent_id="l-cto",
                    kind=TaskKind.CONVERSATION,
                    source_id="ws",
                    thread_identifier=thread_id,
                    payload={
                        "message": message,
                        "channel": "ws",
                        "metadata": metadata,
                    },
                )

                logger.info(
                    "lws: task_id=%s, thread=%s",
                    str(task.id),
                    thread_id,
                )

                # Execute task via AgentExecutorService
                result = await agent_executor.start_agent_task(task)

                # Handle duplicate detection
                if isinstance(result, DuplicateTaskResponse):
                    await websocket.send_json(
                        {
                            "task_id": str(result.task_id),
                            "status": "duplicate",
                            "reply": "Duplicate task",
                        }
                    )
                    continue

                # Handle ExecutionResult
                if isinstance(result, ExecutionResult):
                    reply = result.result or result.error or "No response"
                    await websocket.send_json(
                        {
                            "task_id": str(result.task_id),
                            "status": result.status,
                            "reply": reply,
                        }
                    )
                    continue

                # Fallback (should not happen)
                logger.warning("lws: unexpected result type: %s", type(result))
                await websocket.send_json(
                    {
                        "task_id": str(task.id),
                        "status": "error",
                        "reply": "Unexpected result format",
                    }
                )

            except Exception as exec_err:
                logger.exception("lws: execution error: %s", str(exec_err))
                await websocket.send_json(
                    {
                        "task_id": "",
                        "status": "error",
                        "reply": f"Execution error: {str(exec_err)}",
                    }
                )

    except WebSocketDisconnect:
        logger.debug("lws: client disconnected")
    except Exception as exc:
        logger.error("lws: unexpected error: %s", str(exc), exc_info=True)
