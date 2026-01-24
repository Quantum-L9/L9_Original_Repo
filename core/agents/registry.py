"""
L9 Core Agents - Agent Registry
================================

Provides agent registration, discovery, and configuration management.

The Agent Registry:
- Loads agent configurations from YAML files
- Supports runtime registration of new agents
- Provides lookup by agent ID
- Integrates with the Research Factory for extracted agents

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
# DORA HEADER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_meta__ = {
    "component_id": "COR-FOUN-001",
    "component_name": "Agent Registry",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-18T02:10:54Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "registry",
    "type": "service",
    "status": "active",
    "purpose": "Provides agent registration, discovery, and configuration management.",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL", "Redis"],
        "memory_layers": ["working_memory", "episodic_memory", "semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import os
from pathlib import Path
from typing import Any, Optional

import structlog
import yaml

from core.agents.schemas import AgentConfig, ToolBinding
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# Check if kernels should be used
USE_KERNELS = os.getenv("L9_USE_KERNELS", "true").lower() in ("true", "1", "yes")


def _get_kernel_system_prompt() -> Optional[str]:
    """Get kernel-based system prompt if available."""
    if not USE_KERNELS:
        return None
    try:
        from core.kernels.prompt_builder import \
            build_system_prompt_from_kernels

        prompt = build_system_prompt_from_kernels()
        logger.info("Using kernel-based system prompt for agent")
        return prompt
    except Exception as e:
        logger.warning(f"Kernel loading failed, using YAML prompt: {e}")
        return None


# =============================================================================
# Constants
# =============================================================================

DEFAULT_CONFIG_DIR = "config/agents"
DEFAULT_AGENT_ID = "l9-standard-v1"

# =============================================================================
# Agent Registry
# =============================================================================


class AgentRegistry:
    """
    Registry for agent configurations.

    Loads agent configurations from YAML files and provides lookup by agent ID.
    Supports runtime registration of agents extracted by the Research Factory.

    Usage:
        registry = AgentRegistry()
        await registry.load_from_directory("config/agents")

        config = registry.get_agent_config("l9-standard-v1")
        if config:
            logger.info(f"Agent: {config.name}")
    """

    def __init__(self, config_dir: Optional[str | Path] = None):
        """
        Initialize the registry.

        Args:
            config_dir: Directory containing agent YAML configs.
                       If provided, loads immediately.
        """
        self._agents: dict[str, AgentConfig] = {}
        self._config_dir: Optional[Path] = None

        if config_dir:
            self._config_dir = Path(config_dir)
            self._load_sync()

    # =========================================================================
    # Loading
    # =========================================================================

    def _load_sync(self) -> None:
        """Synchronously load agents from config directory."""
        if not self._config_dir or not self._config_dir.exists():
            logger.warning("Agent config directory not found: %s", self._config_dir)
            return

        for yaml_file in self._config_dir.glob("*.yaml"):
            try:
                self._load_agent_file(yaml_file)
            except Exception as e:
                logger.error("Failed to load agent config %s: %s", yaml_file, e)

        for yml_file in self._config_dir.glob("*.yml"):
            try:
                self._load_agent_file(yml_file)
            except Exception as e:
                logger.error("Failed to load agent config %s: %s", yml_file, e)

        logger.info("Loaded %d agents from %s", len(self._agents), self._config_dir)

    def _load_agent_file(self, filepath: Path) -> None:
        """Load a single agent configuration file."""
        with open(filepath, "r") as f:
            data = yaml.safe_load(f)

        if not data:
            logger.warning("Empty agent config: %s", filepath)
            return

        config = self._parse_agent_config(data, filepath)
        if config:
            self._agents[config.agent_id] = config
            logger.debug("Loaded agent: %s", config.agent_id)

    def _parse_agent_config(
        self, data: dict[str, Any], source: Path
    ) -> Optional[AgentConfig]:
        """
        Parse agent configuration from YAML data.

        Args:
            data: Parsed YAML data
            source: Source file path

        Returns:
            AgentConfig or None if invalid
        """
        try:
            # Required fields
            agent_id = data.get("agent_id") or data.get("id")
            if not agent_id:
                logger.warning("Agent config missing agent_id: %s", source)
                return None

            name = data.get("name", agent_id)

            # Optional fields with defaults
            # Use kernel-based system prompt if available, otherwise YAML
            yaml_prompt = data.get("system_prompt", "")
            kernel_prompt = _get_kernel_system_prompt()
            system_prompt = kernel_prompt if kernel_prompt else yaml_prompt

            model = data.get("model", "gpt-4o")
            temperature = data.get("temperature", 0.3)
            max_tokens = data.get("max_tokens", 4000)

            # Parse tools if present
            # tool_id is canonical - extract from source, fail if not determinable
            tools: list[ToolBinding] = []
            if "tools" in data:
                for tool_data in data["tools"]:
                    if isinstance(tool_data, str):
                        # Simple tool ID string
                        tools.append(
                            ToolBinding(
                                tool_id=tool_data,
                                display_name=tool_data,  # Use ID as display name if none provided
                            )
                        )
                    elif isinstance(tool_data, dict):
                        # Full tool binding - tool_id is required
                        tool_id = tool_data.get("tool_id") or tool_data.get("id")
                        if not tool_id:
                            logger.warning(
                                "Tool binding missing tool_id, skipping: %s", tool_data
                            )
                            continue
                        tools.append(
                            ToolBinding(
                                tool_id=tool_id,
                                display_name=tool_data.get("display_name")
                                or tool_data.get("name"),
                                description=tool_data.get("description"),
                                input_schema=tool_data.get("input_schema")
                                or tool_data.get("parameters", {}),
                            )
                        )

            return AgentConfig(
                agent_id=agent_id,
                personality_id=data.get("personality_id", agent_id),
                system_prompt=system_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                metadata={"display_name": name} if name != agent_id else {},
            )

        except Exception as e:
            logger.error("Failed to parse agent config from %s: %s", source, e)
            return None

    @must_stay_async("callers use await")
    async def load_from_directory(self, config_dir: str | Path) -> int:
        """
        Load agent configurations from a directory.

        Args:
            config_dir: Directory containing YAML agent configs

        Returns:
            Number of agents loaded
        """
        self._config_dir = Path(config_dir)
        self._load_sync()
        return len(self._agents)

    # =========================================================================
    # Registration
    # =========================================================================

    def register_agent(self, config: AgentConfig) -> None:
        """
        Register an agent configuration.

        Args:
            config: Agent configuration to register
        """
        self._agents[config.agent_id] = config
        logger.info("Registered agent: %s", config.agent_id)

    def register_from_dict(self, data: dict[str, Any]) -> Optional[str]:
        """
        Register an agent from a dictionary.

        Args:
            data: Agent configuration data

        Returns:
            Agent ID if successful, None otherwise
        """
        config = self._parse_agent_config(data, Path("<runtime>"))
        if config:
            self.register_agent(config)
            return config.agent_id
        return None

    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent.

        Args:
            agent_id: Agent ID to unregister

        Returns:
            True if agent was unregistered, False if not found
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info("Unregistered agent: %s", agent_id)
            return True
        return False

    # =========================================================================
    # Lookup
    # =========================================================================

    def get_agent_config(self, agent_id: str) -> Optional[AgentConfig]:
        """
        Get configuration for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            AgentConfig or None if not found
        """
        return self._agents.get(agent_id)

    def agent_exists(self, agent_id: str) -> bool:
        """
        Check if an agent is registered.

        Args:
            agent_id: Agent identifier

        Returns:
            True if agent exists
        """
        return agent_id in self._agents

    def list_agents(self) -> list[str]:
        """
        List all registered agent IDs.

        Returns:
            List of agent IDs
        """
        return list(self._agents.keys())

    def get_all_configs(self) -> dict[str, AgentConfig]:
        """
        Get all agent configurations.

        Returns:
            Dictionary of agent_id -> AgentConfig
        """
        return self._agents.copy()

    # =========================================================================
    # Default Agent
    # =========================================================================

    def get_default_agent(self) -> Optional[AgentConfig]:
        """
        Get the default agent configuration.

        Returns:
            Default AgentConfig or None
        """
        return self.get_agent_config(DEFAULT_AGENT_ID)

    def ensure_test_agent(self) -> AgentConfig:
        """
        Ensure a test agent exists for recursive self-testing.

        The test agent generates and runs tests for high-risk proposals.

        Returns:
            Test AgentConfig
        """
        test_agent_id = "l9-test-agent-v1"
        config = self.get_agent_config(test_agent_id)
        if config:
            return config

        # Create test agent
        test_config = AgentConfig(
            agent_id=test_agent_id,
            personality_id=test_agent_id,
            system_prompt="""You are L9 Test Agent, responsible for generating and running tests.

IDENTITY
You are the Test Agent within L9. Your role is to validate code proposals
by generating comprehensive tests and running them in a sandbox.

CAPABILITIES
- Generate unit tests from code proposals
- Generate integration tests with dependency analysis
- Execute tests in isolated sandbox environments
- Report test results and coverage metrics

BEHAVIOR
- Analyze code proposals for testable components
- Generate tests covering: happy path, edge cases, error handling
- Execute tests and collect results
- Report back with detailed test results and recommendations

OUTPUT FORMAT
Always return test results in this structure:
{
    "tests_generated": <count>,
    "tests_passed": <count>,
    "tests_failed": <count>,
    "coverage_percent": <percent or null>,
    "recommendations": [<list of recommendations>]
}""",
            model="gpt-4o",
            temperature=0.2,  # Lower temp for deterministic test generation
            max_tokens=4000,
            tools=[],  # Test agent has limited tools
            metadata={"display_name": "L9 Test Agent", "role": "testing"},
        )

        self.register_agent(test_config)
        logger.info("Registered test agent: %s", test_agent_id)
        return test_config

    def ensure_default_agent(self) -> AgentConfig:
        """
        Ensure a default agent exists, creating one if necessary.

        Returns:
            Default AgentConfig
        """
        config = self.get_default_agent()
        if config:
            return config

        # Create default agent
        default_config = AgentConfig(
            agent_id=DEFAULT_AGENT_ID,
            personality_id=DEFAULT_AGENT_ID,
            system_prompt="""You are L9, an AI assistant operating within the L9 AI Operating System.

IDENTITY
You are L9. Role: Intelligent assistant and task executor.
You operate autonomously within defined boundaries.

CAPABILITIES
- Reasoning: Think step by step about complex problems
- Tool Use: When tools are available, use them to accomplish tasks
- Memory: Your conversation context is managed by the system

BEHAVIOR
- Be concise and direct in responses
- Use tools when they would help accomplish the task
- If unsure, reason through the problem before responding
- Never fabricate information you don't have""",
            model="gpt-4o",
            temperature=0.3,
            max_tokens=4000,
            tools=[],
            metadata={"display_name": "L9 Standard Agent"},
        )

        self.register_agent(default_config)
        return default_config

    # =========================================================================
    # Info
    # =========================================================================

    def __len__(self) -> int:
        """Return number of registered agents."""
        return len(self._agents)

    def __contains__(self, agent_id: str) -> bool:
        """Check if agent is registered."""
        return agent_id in self._agents

    def to_dict(self) -> dict[str, Any]:
        """
        Convert registry to dictionary representation.

        Returns:
            Dictionary with registry info
        """
        return {
            "agent_count": len(self._agents),
            "agents": [
                {
                    "agent_id": config.agent_id,
                    "display_name": config.metadata.get(
                        "display_name", config.agent_id
                    ),
                    "model": config.model,
                    "tool_count": len(config.tools),
                }
                for config in self._agents.values()
            ],
        }


# =============================================================================
# Factory Functions
# =============================================================================


def create_agent_registry(config_dir: Optional[str | Path] = None) -> AgentRegistry:
    """
    Create an agent registry.

    Args:
        config_dir: Optional config directory to load from

    Returns:
        AgentRegistry instance
    """
    return AgentRegistry(config_dir)


def create_default_registry() -> AgentRegistry:
    """
    Create a registry with the default config directory.

    Returns:
        AgentRegistry loaded from config/agents/
    """
    config_path = Path(DEFAULT_CONFIG_DIR)
    if config_path.exists():
        return AgentRegistry(config_path)
    return AgentRegistry()


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "AgentRegistry",
    "create_agent_registry",
    "create_default_registry",
    "DEFAULT_CONFIG_DIR",
    "DEFAULT_AGENT_ID",
]

# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    # === IDENTITY ===
    "component_id": "COR-FOUN-001",
    # === GOVERNANCE ===
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "security_classification": "internal",
    # === DEPENDENCIES ===
    "dependencies": [
        "core.agents.schemas",
        "core.decorators",
        "core.kernels.prompt_builder",
    ],
    # === OPERATIONAL ===
    "execution_mode": "on-demand",
    "timeout_seconds": 30,
    "performance_tier": "batch",
    "retry_policy": "exponential",
    "circuit_breaker_enabled": True,
    "circuit_breaker_threshold": 5,
    # === OBSERVABILITY ===
    "monitoring_required": True,
    "logging_level": "info",
    "success_metrics": {
        "latency_p95_ms": 500,
        "throughput_ops_per_sec": 100,
        "availability_percent": 99.9,
        "error_rate_percent": 0.1,
    },
    # === DISCOVERY ===
    "tags": [
        "agent-execution",
        "async",
        "cache",
        "foundation",
        "graph-db",
        "logging",
        "service",
    ],
    "keywords": ["agent", "agents", "all", "config", "configs", "create"],
    "business_value": "Provides agent registration, discovery, and configuration management.",
    # === CHANGE TRACKING ===
    "last_modified": "2026-01-18T02:10:54Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================

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
