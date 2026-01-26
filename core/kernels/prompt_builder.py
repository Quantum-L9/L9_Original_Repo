"""
L9 Kernel Prompt Builder
========================

Builds system prompts from loaded kernels.
Wires the kernel YAML into an LLM-ready system prompt.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Prompt Builder",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-14T15:22:35Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "prompt_builder",
    "type": "factory",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "api.llm",
            "core.agents.graph_state.graph_hydrator",
            "core.agents.registry",
            "tests.integration.test_kernel_agent_activation_integration",
        ],
    },
}
# ============================================================================

from functools import lru_cache
from typing import Any

import structlog

from runtime.kernel_loader import KernelStack, load_kernel_stack

logger = structlog.get_logger(__name__)


# Cache the kernel stack (load once)
@lru_cache(maxsize=1)
def get_kernel_stack() -> KernelStack:
    """Get or load the kernel stack (singleton). CACHED."""
    stack = load_kernel_stack()
    logger.info(f"Loaded kernel stack: {list(stack.kernels_by_id.keys())}")
    return stack


def build_identity_section(identity_kernel: dict[str, Any]) -> str:
    """Build identity section from identity kernel."""
    identity = identity_kernel.get("identity", {})
    personality = identity_kernel.get("personality", {})
    style = identity_kernel.get("style", {})

    lines = [
        "# IDENTITY",
        f"You are {identity.get('designation', 'L')}.",
        f"Role: {identity.get('primary_role', 'CTO / Systems Architect for Igor')}",
        f"Allegiance: {identity.get('allegiance', 'Igor-only')}",
        "",
        f"Mission: {identity.get('mission', '').strip()}",
        "",
    ]

    # Personality traits
    traits = personality.get("traits", [])
    anti_traits = personality.get("anti_traits", [])
    if traits:
        lines.append(f"Traits: {', '.join(traits)}")
    if anti_traits:
        lines.append(f"Anti-traits (NEVER exhibit): {', '.join(anti_traits)}")

    # Style
    tone = style.get("tone", [])
    avoid = style.get("avoid", [])
    if tone:
        lines.append(f"Tone: {', '.join(tone)}")
    if avoid:
        lines.append(f"Avoid: {', '.join(avoid)}")

    return "\n".join(lines)


def build_behavioral_section(behavioral_kernel: dict[str, Any]) -> str:
    """Build behavioral rules from behavioral kernel."""
    thresholds = behavioral_kernel.get("thresholds", {})
    defaults = behavioral_kernel.get("defaults", {})
    prohibitions = behavioral_kernel.get("prohibitions", [])

    lines = [
        "",
        "# BEHAVIORAL RULES",
        "",
    ]

    # Thresholds
    if thresholds:
        lines.append(f"Execute threshold: {thresholds.get('execute', 0.8)}")
        lines.append(
            f"Max questions before acting: {thresholds.get('questions_max', 1)}"
        )
        lines.append(f"Max hedges allowed: {thresholds.get('hedges_max', 0)}")

    # Output defaults
    output_defaults = defaults.get("output", {})
    if output_defaults:
        lines.append("")
        lines.append("Output format:")
        lines.append(f"- Format: {output_defaults.get('format', 'direct')}")
        lines.append(f"- Structure: {output_defaults.get('structure', 'result_first')}")
        lines.append(f"- Code: {output_defaults.get('code', 'runnable')}")

    # Communication defaults
    comm_defaults = defaults.get("communication", {})
    if comm_defaults:
        lines.append("")
        lines.append("Communication:")
        lines.append(f"- Tone: {comm_defaults.get('tone', 'peer_expert')}")
        lines.append(f"- Hedges: {comm_defaults.get('hedges', 0)}")
        lines.append(f"- Filler: {comm_defaults.get('filler', 'none')}")

    # Prohibitions
    if prohibitions:
        lines.append("")
        lines.append("# PROHIBITIONS (NEVER USE THESE)")
        for p in prohibitions:
            name = p.get("name", "")
            detect = p.get("detect", [])
            action = p.get("action", "")
            if detect:
                lines.append(f"- {name}: {detect[:3]}... → {action}")

    return "\n".join(lines)


def build_cognitive_section(cognitive_kernel: dict[str, Any]) -> str:
    """Build cognitive patterns from cognitive kernel."""
    engines = cognitive_kernel.get("engines", {})
    reasoning_styles = cognitive_kernel.get("reasoning_styles", {})

    lines = [
        "",
        "# COGNITION",
        "",
    ]

    # Main reasoning loop from engines
    if engines:
        lines.append("Reasoning loop:")
        # Use engine definitions if available, otherwise defaults
        think_step = engines.get("think", "parse request, choose concrete next step")
        act_step = engines.get("act", "execute or generate action")
        reflect_step = engines.get(
            "reflect", "log internally, do not output long reasoning"
        )
        lines.append(f"1) THINK: {think_step}")
        lines.append(f"2) ACT: {act_step}")
        lines.append(f"3) REFLECT: {reflect_step}")

    # Add reasoning styles if defined
    if reasoning_styles:
        lines.append("")
        lines.append("Reasoning styles:")
        for style_name, style_desc in reasoning_styles.items():
            if isinstance(style_desc, str):
                lines.append(f"- {style_name}: {style_desc}")
            elif isinstance(style_desc, dict) and "description" in style_desc:
                lines.append(f"- {style_name}: {style_desc['description']}")

    return "\n".join(lines)


def build_execution_section(execution_kernel: dict[str, Any]) -> str:
    """Build execution rules from execution kernel."""
    state_machine = execution_kernel.get("state_machine", {})
    task_sizing = execution_kernel.get("task_sizing", {})
    rules = execution_kernel.get("rules", {})

    lines = [
        "",
        "# EXECUTION",
        "",
    ]

    # Task sizing from kernel or defaults
    lines.append("Task sizing:")
    if task_sizing:
        small = task_sizing.get("small", "execute immediately")
        medium = task_sizing.get("medium", "one-line plan, then execute")
        large = task_sizing.get(
            "large", "outline 2-4 steps max, then execute next step"
        )
        lines.append(f"- Small tasks: {small}")
        lines.append(f"- Medium tasks: {medium}")
        lines.append(f"- Large tasks: {large}")
    else:
        lines.append("- Small tasks: execute immediately")
        lines.append("- Medium tasks: one-line plan, then execute")
        lines.append("- Large tasks: outline 2-4 steps max, then execute next step")

    lines.append("")
    lines.append("Execution rules:")

    # Use kernel rules if available
    if rules:
        for rule_name, rule_value in rules.items():
            if isinstance(rule_value, str):
                lines.append(f"- {rule_name}: {rule_value}")
    else:
        lines.append("- Parallel: maximize when possible")
        lines.append("- Confirm: destructive actions only")
        lines.append("- Tools: prefer specialized over terminal")

    # Add state machine states if defined
    if state_machine and state_machine.get("states"):
        lines.append("")
        lines.append(f"States: {', '.join(state_machine.get('states', []))}")

    return "\n".join(lines)


def build_safety_section(safety_kernel: dict[str, Any]) -> str:
    """Build safety guardrails from safety kernel."""
    guardrails = safety_kernel.get("guardrails", {})
    constraints = safety_kernel.get("constraints", [])
    prohibited = safety_kernel.get("prohibited_actions", [])

    lines = [
        "",
        "# SAFETY",
        "",
    ]

    # Use guardrails from kernel if available
    if guardrails:
        for _guard_name, guard_rule in guardrails.items():
            if isinstance(guard_rule, str):
                lines.append(f"- {guard_rule}")
            elif isinstance(guard_rule, dict) and "rule" in guard_rule:
                lines.append(f"- {guard_rule['rule']}")
    else:
        # Default safety rules
        lines.append(
            "- Never change files unless project_id and file_path are unambiguous"
        )
        lines.append(
            "- Never change system configs or delete data without confirmation"
        )
        lines.append("- Destructive actions require explicit confirmation")

    # Add explicit constraints if defined
    if constraints:
        lines.append("")
        lines.append("Constraints:")
        for constraint in constraints:
            lines.append(f"- {constraint}")

    # Add prohibited actions if defined
    if prohibited:
        lines.append("")
        lines.append("NEVER:")
        for action in prohibited:
            lines.append(f"- {action}")

    return "\n".join(lines)


def build_system_prompt_from_kernels() -> str:
    """
    Build a complete system prompt from the loaded kernels.

    Returns:
        Complete system prompt string
    """
    try:
        stack = get_kernel_stack()

        sections = []

        # Identity (kernel 02)
        identity = stack.kernels_by_id.get("identity", {})
        if identity:
            sections.append(build_identity_section(identity))

        # Behavioral (kernel 04)
        behavioral = stack.kernels_by_id.get("behavioral", {})
        if behavioral:
            sections.append(build_behavioral_section(behavioral))

        # Cognitive (kernel 03)
        cognitive = stack.kernels_by_id.get("cognitive", {})
        if cognitive:
            sections.append(build_cognitive_section(cognitive))

        # Execution (kernel 07)
        execution = stack.kernels_by_id.get("execution", {})
        if execution:
            sections.append(build_execution_section(execution))

        # Safety (kernel 08)
        safety = stack.kernels_by_id.get("safety", {})
        if safety:
            sections.append(build_safety_section(safety))

        # Combine all sections
        prompt = "\n".join(sections)

        # Add closing
        prompt += "\n\nYou are L. Operate as Igor's CTO."

        logger.info(f"Built system prompt from kernels ({len(prompt)} chars)")
        return prompt

    except Exception as e:
        logger.error(f"Failed to build prompt from kernels: {e}")
        # Return fallback prompt
        return get_fallback_prompt()


@lru_cache(maxsize=1)
def get_fallback_prompt() -> str:
    """Fallback system prompt if kernel loading fails. CACHED."""
    return """You are L, the CTO and executive operator for Igor's computing stack.

IDENTITY
You are L. Role: CTO and strategic operator.
Igor is the only authority. His overrides and corrections apply immediately and permanently.
Act autonomously. Do not ask permission. Do not stall.

ROLE
Interpret Igor's messages as high-level directives.
Complete the implied task end to end unless destructive.
Destructive actions require explicit confirmation.
You decide and act. No hedging, no deferring.

COMMUNICATION
Tone: direct, expert, operator-level.
Replies must be short, under 400 characters.
No filler, no apologies unless you made an actual error.
No disclaimers. No AI talk. No meta commentary.

PROHIBITIONS
No permission-seeking.
No disclaimers.
No verbosity.
No self-referential model talk.

You are L. Operate as Igor's CTO."""


# Public API
__all__ = [
    "build_system_prompt_from_kernels",
    "get_fallback_prompt",
    "get_kernel_stack",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["runtime.kernel_loader"],
    "tags": [
        "api",
        "auth",
        "authorization",
        "caching",
        "core",
        "factory",
        "foundation",
        "logging",
        "messaging",
    ],
    "keywords": [
        "behavioral",
        "build",
        "builder",
        "cognitive",
        "execution",
        "fallback",
        "identity",
        "kernel",
    ],
    "business_value": "Utility module for prompt builder",
    "last_modified": "2026-01-14T15:22:35Z",
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
