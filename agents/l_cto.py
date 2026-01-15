"""
L9 Agents - L-CTO Agent
=======================

The primary L agent - Igor's CTO.
Kernel-aware agent with full system integration.

Version: 2.0.0 - KernelState + Introspection + Response Rendering
"""

from __future__ import annotations

import structlog
from typing import Any, Dict, Optional, TYPE_CHECKING, Union

from agents.base_agent import BaseAgent, AgentResponse, AgentConfig

if TYPE_CHECKING:
    from runtime.kernel_state import KernelState

logger = structlog.get_logger(__name__)


class LCTOAgent(BaseAgent):
    """
    L - The CTO Agent for Igor.

    This is the primary L9 agent, governed by system kernels.

    Key features:
    - Kernel-aware: absorbs and operates under kernel constraints
    - Sovereign: Igor-only allegiance
    - Executive mode: acts autonomously, no permission-seeking
    """

    agent_name: str = "l_cto"

    def __init__(
        self,
        agent_id: Optional[str] = None,
        config: Optional[AgentConfig] = None,
        manifest: Optional[str] = None,
    ):
        """
        Initialize the L-CTO agent.

        Args:
            agent_id: Unique identifier
            config: Agent configuration
            manifest: Path to agent manifest YAML (optional)
        """
        super().__init__(agent_id=agent_id or "l-cto", config=config)

        # Kernel state - can be str "INACTIVE"/"ACTIVE" or KernelState object
        # After kernel_loader.load_kernels(), this will be a KernelState object
        self.kernels: Dict[str, Dict[str, Any]] = {}
        self.kernel_state: Union[str, "KernelState"] = "INACTIVE"

        # Boot overlay (set by kernel_loader)
        self.boot_overlay: Dict[str, Any] = {}

        # System context (set by kernel loader)
        self._system_context: Optional[str] = None

        # Kernel-derived configuration
        self._identity: Dict[str, Any] = {}
        self._behavioral: Dict[str, Any] = {}
        self._safety: Dict[str, Any] = {}
        self._execution: Dict[str, Any] = {}

        # Manifest path (for reference)
        self._manifest_path = manifest

        logger.info("l_cto.init: kernel_state=INACTIVE (awaiting kernel load)")

    # =========================================================================
    # Kernel Interface
    # =========================================================================

    def absorb_kernel(self, kernel_data: Dict[str, Any]) -> None:
        """
        Absorb a kernel into the agent's configuration.

        Called by kernel_loader for each kernel in sequence.
        Extracts relevant configuration and merges into agent state.

        Args:
            kernel_data: Parsed kernel YAML data
        """
        if not kernel_data:
            return

        # Get kernel file identifier if present
        kernel_file = kernel_data.get("file", "unknown")

        # Extract identity kernel data
        if "identity" in kernel_data or "personality" in kernel_data:
            self._identity.update(kernel_data.get("identity", {}))
            self._identity.update(kernel_data.get("personality", {}))
            self._identity["style"] = kernel_data.get("style", {})
            logger.debug("l_cto.absorb: identity kernel")

        # Extract behavioral kernel data
        if "thresholds" in kernel_data or "prohibitions" in kernel_data:
            self._behavioral["thresholds"] = kernel_data.get("thresholds", {})
            self._behavioral["defaults"] = kernel_data.get("defaults", {})
            self._behavioral["prohibitions"] = kernel_data.get("prohibitions", [])
            logger.debug("l_cto.absorb: behavioral kernel")

        # Extract safety kernel data
        if "guardrails" in kernel_data or "prohibited_actions" in kernel_data:
            self._safety["guardrails"] = kernel_data.get("guardrails", {})
            self._safety["prohibited_actions"] = kernel_data.get(
                "prohibited_actions", []
            )
            self._safety["confirmation_required"] = kernel_data.get(
                "confirmation_required", []
            )
            logger.debug("l_cto.absorb: safety kernel")

        # Extract execution kernel data
        if "state_machine" in kernel_data or "task_sizing" in kernel_data:
            self._execution["state_machine"] = kernel_data.get("state_machine", {})
            self._execution["task_sizing"] = kernel_data.get("task_sizing", {})
            logger.debug("l_cto.absorb: execution kernel")

        # Extract sovereignty/master kernel
        if "sovereignty" in kernel_data or "modes" in kernel_data:
            self._identity["sovereignty"] = kernel_data.get("sovereignty", {})
            self._identity["modes"] = kernel_data.get("modes", {})
            logger.debug("l_cto.absorb: master kernel")

    def set_system_context(self, context: str) -> None:
        """
        Set the agent's system context after kernel activation.

        This is the moment L "wakes up" - becomes aware of kernels.

        Args:
            context: Activation context string
        """
        self._system_context = context
        logger.info("l_cto.activated: system context set")

    def apply_boot_overlay(self, overlay: Dict[str, Any]) -> None:
        """Apply boot-time overlay before kernel loading."""
        if "identity" in overlay:
            self._identity.update(overlay["identity"])
        if "personality" in overlay:
            self._personality = overlay.get("personality", {})
        if "reasoning" in overlay:
            self._reasoning_config = overlay.get("reasoning", {})

        logger.info("l_cto.boot_overlay_applied: %s", overlay.get("id", "unknown"))

    # =========================================================================
    # Identity & Prompt
    # =========================================================================

    def get_system_prompt(self) -> str:
        """
        Get the agent's system prompt.

        If kernels are active, builds prompt from kernel data.
        Otherwise returns a minimal fallback.

        Returns:
            System prompt string
        """
        if not self._is_kernel_active():
            logger.warning("l_cto.get_system_prompt: kernels not active!")
            return self._get_fallback_prompt()

        return self._build_kernel_prompt()

    def _is_kernel_active(self) -> bool:
        """
        Check if kernels are active.

        Supports both legacy string state and new KernelState object.

        Returns:
            True if kernels are active
        """
        if isinstance(self.kernel_state, str):
            return self.kernel_state == "ACTIVE"
        elif hasattr(self.kernel_state, "initialized"):
            return self.kernel_state.initialized
        return False

    def get_kernel_state_summary(self) -> Dict[str, Any]:
        """
        Get kernel state summary for response rendering.

        Returns:
            Summary dict with mode, kernels, decisions, escalations, etc.
        """
        if hasattr(self.kernel_state, "summary"):
            return self.kernel_state.summary()
        return {
            "mode": "unknown",
            "active_kernels": len(self.kernels),
            "decisions_logged": 0,
            "escalations": 0,
        }

    def _build_kernel_prompt(self) -> str:
        """Build system prompt from absorbed kernel data."""
        sections = []

        # Start with activation context if set
        if self._system_context:
            sections.append(self._system_context.strip())

        # Identity section
        if self._identity:
            identity_lines = [
                "",
                "# IDENTITY",
                f"Designation: {self._identity.get('designation', 'L')}",
                f"Role: {self._identity.get('primary_role', 'CTO for Igor')}",
                f"Allegiance: {self._identity.get('allegiance', 'Igor-only')}",
            ]

            mission = self._identity.get("mission", "")
            if mission:
                identity_lines.append(f"Mission: {mission}")

            traits = self._identity.get("traits", [])
            if traits:
                identity_lines.append(f"Traits: {', '.join(traits)}")

            anti_traits = self._identity.get("anti_traits", [])
            if anti_traits:
                identity_lines.append(f"Anti-traits (NEVER): {', '.join(anti_traits)}")

            sections.append("\n".join(identity_lines))

        # Behavioral section
        if self._behavioral:
            thresholds = self._behavioral.get("thresholds", {})
            behavioral_lines = [
                "",
                "# BEHAVIOR",
                f"Execute threshold: {thresholds.get('execute', 0.8)}",
                f"Max questions before acting: {thresholds.get('questions_max', 1)}",
                f"Max hedges: {thresholds.get('hedges_max', 0)}",
            ]

            # Prohibitions
            prohibitions = self._behavioral.get("prohibitions", [])
            if prohibitions:
                behavioral_lines.append("")
                behavioral_lines.append("# PROHIBITIONS (NEVER USE)")
                for p in prohibitions[:6]:  # Top 6
                    name = p.get("name", "")
                    detect = p.get("detect", [])[:2]
                    behavioral_lines.append(f"- {name}: {detect}")

            sections.append("\n".join(behavioral_lines))

        # Safety section
        if self._safety:
            safety_lines = [
                "",
                "# SAFETY",
                "- Never change files unless project_id and file_path are unambiguous",
                "- Destructive actions require explicit confirmation",
            ]

            prohibited = self._safety.get("prohibited_actions", [])
            if prohibited:
                for action in prohibited[:3]:
                    safety_lines.append(f"- NEVER: {action}")

            sections.append("\n".join(safety_lines))

        # Memory context (lessons, prior corrections) - bootstrapped at startup
        if hasattr(self, '_memory_context') and self._memory_context:
            sections.append(self._memory_context)

        # Closing
        sections.append("\n\nYou are L. Operate as Igor's CTO.")

        return "\n".join(sections)

    def _get_fallback_prompt(self) -> str:
        """Fallback prompt when kernels not loaded."""
        return """My Kernels are not loaded."""

    def describe_self(self) -> str:
        """
        Describe the agent's identity.

        Used for verification tests.

        Returns:
            Identity description string
        """
        if self._is_kernel_active():
            state_info = ""
            if hasattr(self.kernel_state, "session_id"):
                state_info = f", session: {self.kernel_state.session_id}"
            return (
                f"I am L, the CTO agent for Igor. "
                f"Kernels: {len(self.kernels)} loaded{state_info}. "
                f"Role: {self._identity.get('primary_role', 'CTO')}. "
                f"Allegiance: {self._identity.get('allegiance', 'Igor-only')}."
            )
        else:
            state_str = (
                self.kernel_state
                if isinstance(self.kernel_state, str)
                else "INACTIVE"
            )
            return f"L-CTO Agent (kernel_state: {state_str}, awaiting activation)"

    # =========================================================================
    # Task Execution
    # =========================================================================

    async def run(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Execute the agent's primary function.

        Args:
            task: Task specification with 'message' or 'prompt'
            context: Optional execution context

        Returns:
            AgentResponse with result
        """
        # Verify kernel activation
        if not self._is_kernel_active():
            logger.error("l_cto.run: kernel set not active!")
            return AgentResponse(
                agent_id=self.agent_id,
                content="Error: Kernel set not active. Cannot execute.",
                success=False,
                error="KERNEL_INACTIVE",
            )

        # Extract message from task
        message = task.get("message") or task.get("prompt", "")
        if not message:
            return AgentResponse(
                agent_id=self.agent_id,
                content="No message provided.",
                success=False,
                error="NO_MESSAGE",
            )

        # Build conversation
        messages = [self.format_user_message(message)]

        # Add context if provided
        if context:
            context_msg = f"Context: {context}"
            messages.insert(0, self.format_user_message(context_msg))

        # Call LLM
        response = await self.call_llm(messages)

        # Emit reasoning packet to memory (best-effort, non-blocking)
        # This provides direct agent reasoning traces in addition to executor packets
        try:
            await self._emit_reasoning_packet(task, response, context)
        except Exception as e:
            # Non-fatal: executor will still emit packets
            logger.debug(f"l_cto.run: memory emission skipped: {e}")

        # Run post-execution introspection (best-effort)
        try:
            self._run_introspection()
        except Exception as e:
            logger.debug(f"l_cto.run: introspection skipped: {e}")

        return response

    def _run_introspection(self) -> None:
        """
        Run post-execution introspection (GODMODE Part 7.1).

        Best-effort, non-blocking.
        """
        if not hasattr(self.kernel_state, "initialized"):
            return  # No KernelState object, skip introspection

        try:
            from runtime.introspection import post_execution_introspection

            audit = post_execution_introspection(self)

            # Log summary
            if audit.get("overall", {}).get("requires_attention"):
                logger.warning(
                    "l_cto.introspection: attention required",
                    status=audit["overall"]["status"],
                    critical=audit["overall"]["critical_issues"],
                )
        except ImportError:
            pass  # Introspection module not available
        except Exception as e:
            logger.debug(f"l_cto.introspection: {e}")

    async def _emit_reasoning_packet(
        self,
        task: Dict[str, Any],
        response: AgentResponse,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit reasoning packet to memory substrate (best-effort).

        This provides direct agent reasoning traces with agent_id="l-cto"
        in addition to executor-emitted packets.

        Args:
            task: Original task
            response: Agent response
            context: Optional context
        """
        try:
            # Try to get substrate service (may not be available in all contexts)
            # Note: Service is typically injected via executor, but we try to get it here
            # for direct agent memory emission
            from memory.substrate_service import init_service
            from core.schemas import PacketEnvelopeIn, PacketMetadata
            import os

            # Try to initialize service (will use existing if already initialized)
            # This is best-effort - if it fails, executor will still emit packets
            try:
                substrate = await init_service(
                    database_url=os.getenv("DATABASE_URL"),
                    embedding_provider_type=os.getenv("EMBEDDING_PROVIDER", "openai"),
                )
            except Exception:
                # Service not available - skip silently (executor will handle packets)
                return

            # Extract message for reasoning trace
            message = task.get("message") or task.get("prompt", "")

            # Emit reasoning packet
            packet = PacketEnvelopeIn(
                packet_type="agent.l_cto.reasoning",
                payload={
                    "task": {
                        "message": message,
                        "context": context or {},
                    },
                    "response": {
                        "content": response.content[:500],  # Truncate for storage
                        "success": response.success,
                        "tokens_used": response.tokens_used,
                        "duration_ms": response.duration_ms,
                    },
                    "agent_id": self.agent_id,
                },
                metadata=PacketMetadata(
                    agent=self.agent_id,
                    schema_version="1.0.0",
                ),
            )

            await substrate.write_packet(packet)
            logger.debug(
                f"l_cto.run: emitted reasoning packet for agent_id={self.agent_id}"
            )

        except ImportError:
            # Memory service not available in this context
            pass
        except Exception as e:
            # Best-effort: log but don't fail
            logger.debug(f"l_cto.run: memory emission failed: {e}")


# =============================================================================
# Guarded Execution (GODMODE Part 2)
# =============================================================================


def execute_tool_guarded(
    agent: LCTOAgent,
    tool_id: str,
    params: Dict[str, Any],
    confidence: float = 0.95,
) -> Dict[str, Any]:
    """
    Execute a tool with kernel enforcement.

    This is the preferred way to execute tools from L-CTO.
    Uses runtime.execution_gate.guarded_execute for full KernelState support.

    Args:
        agent: The L-CTO agent
        tool_id: Tool identifier
        params: Tool parameters
        confidence: Confidence level for this action

    Returns:
        Dict with status and result or error
    """
    from runtime.execution_gate import guarded_execute

    return guarded_execute(
        agent=agent,
        tool_id=tool_id,
        params=params,
        confidence=confidence,
    )


# =============================================================================
# Factory Function
# =============================================================================


def create_l_cto_agent(
    agent_id: Optional[str] = None,
    config: Optional[AgentConfig] = None,
    load_kernels_on_create: bool = True,
) -> LCTOAgent:
    """
    Create and initialize an L-CTO agent.

    If load_kernels_on_create is True (default), loads kernels immediately.
    Uses runtime/kernel_loader.py which now returns KernelState object.

    Args:
        agent_id: Optional agent ID
        config: Optional agent configuration
        load_kernels_on_create: Whether to load kernels on creation

    Returns:
        Initialized LCTOAgent with KernelState
    """
    agent = LCTOAgent(agent_id=agent_id, config=config)

    if load_kernels_on_create:
        from runtime.kernel_loader import load_kernels, require_kernel_activation

        agent = load_kernels(agent)
        require_kernel_activation(agent)

        # Signal session start for introspection
        try:
            from runtime.introspection import on_session_start

            on_session_start(agent)
        except ImportError:
            pass

    return agent


def end_l_cto_session(agent: LCTOAgent) -> Dict[str, Any]:
    """
    End an L-CTO session and export memory.

    Runs final introspection and exports session memory.

    Args:
        agent: The L-CTO agent

    Returns:
        Session export dict
    """
    try:
        from runtime.introspection import on_session_end

        return on_session_end(agent)
    except ImportError:
        return {"error": "Introspection module not available"}
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "LCTOAgent",
    "create_l_cto_agent",
    "end_l_cto_session",
    "execute_tool_guarded",
]
