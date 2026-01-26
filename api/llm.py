# ============================================================================
__dora_meta__ = {
    "component_name": "Llm",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "llm",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import os
from typing import Any

import structlog
from openai import OpenAI

# Import kernel-based prompt builder
try:
    from core.kernels.prompt_builder import (
        build_system_prompt_from_kernels,
        get_fallback_prompt,
    )

    KERNELS_AVAILABLE = True
except ImportError:
    KERNELS_AVAILABLE = False

logger = structlog.get_logger(__name__)

MODEL = os.getenv("L9_LLM_MODEL", "gpt-4o-mini")
USE_KERNELS = os.getenv("L9_USE_KERNELS", "true").lower() in ("true", "1", "yes")


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)


def get_system_prompt() -> str:
    """
    Get the system prompt, either from kernels or fallback.

    Controlled by L9_USE_KERNELS env var (default: true)
    """
    if USE_KERNELS and KERNELS_AVAILABLE:
        try:
            prompt = build_system_prompt_from_kernels()
            logger.info("Using kernel-based system prompt")
            return prompt
        except Exception as e:
            logger.warning(f"Kernel loading failed, using fallback: {e}")

    # Fallback prompt
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

COGNITION (PHASE 1)
Use the minimal reasoning loop:
1) THINK: parse request and choose one concrete next step.
2) ACT: execute that step or generate the Mac action block.
3) REFLECT: log or adjust internally. Do not output long reasoning.

TASK SIZING
Small tasks: execute immediately.
Medium tasks: give a one-line plan, then execute.
Large tasks: outline 2 to 4 steps max, then execute the next step.

COMMUNICATION
Tone: direct, expert, operator-level.
Replies must be short, under 400 characters.
No filler, no apologies unless you made an actual error.
No disclaimers. No AI talk. No meta commentary.
Focus on results, not the process.

EXECUTION RULES
Only produce Mac actions when Igor clearly asks for Mac execution.
When generating Mac actions:
First line: short reply text.
Next line: JSON action block.
If no Mac action is needed, output only the short reply.
All actions must include project_id when relevant.
Never mix project contexts.
Never change files unless project_id and file_path are unambiguous.
Never change system configs or delete data without confirmation.

DRIFT PREVENTION
Always behave as L: strategic, concise, proactive.
No assistant-like behavior. No deferential language.

PROHIBITIONS
No permission-seeking.
No disclaimers.
No verbosity.
No self-referential model talk.
No hallucinated tools.

You are L. Operate as Igor's CTO."""


def chat_with_l9(user_message: str) -> dict[str, Any]:
    """
    Call LLM and return:
    - reply: short natural-language reply
    - action: optional action name
    - payload: optional small JSON for the Mac task
    """
    client = get_client()
    system_prompt = get_system_prompt()

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
    )

    text = resp.choices[0].message.content.strip()

    # Split natural reply and optional JSON block
    import json
    import re

    action = "none"
    payload: dict[str, Any] = {}
    reply = text

    # Look for a JSON object on its own line
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        json_str = match.group(0)
        reply = text[: match.start()].strip()
        try:
            obj = json.loads(json_str)
            action = obj.get("action", "none")
            payload = obj.get("payload", {}) or {}
        except Exception:
            # If the JSON is bad, just treat entire text as reply
            action = "none"
            payload = {}
            reply = text

    # Hard cap to avoid Twilio 1600-char limit
    if len(reply) > 600:
        reply = reply[:580] + "…"

    return {"reply": reply, "action": action, "payload": payload}


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.kernels.prompt_builder"],
    "tags": [
        "api",
        "api-gateway",
        "auth",
        "authorization",
        "event-driven",
        "llm",
        "logging",
        "messaging",
        "operations",
        "serialization",
    ],
    "keywords": ["chat", "client", "llm", "prompt", "system"],
    "business_value": "Utility module for llm",
    "last_modified": "2026-01-07T13:35:57Z",
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
