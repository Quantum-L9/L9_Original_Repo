"""
L9 IR Engine - Semantic Compiler
================================

Converts natural language input into structured IR representations.

Responsibilities:
- Parse user input text
- Extract intents, constraints, actions
- Build initial IR graph
- Integrate with LLM for semantic understanding
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Semantic Compiler",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "intelligence",
    "domain": "ir_compilation",
    "module_name": "semantic_compiler",
    "type": "engine",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [
            "ir_engine.__init__",
            "ir_engine.deliberation_cell",
            "orchestration.orchestrator_kernel",
            "orchestration.unified_controller",
            "tests.ir_engine.test_ir_semantic_incremental",
            "tests.ir_engine.test_ir_semantic_to_plan_integration",
        ],
    },
}
# ============================================================================

import json
import structlog
from typing import Any, Optional
from uuid import UUID

from openai import AsyncOpenAI

from ir_engine.ir_schema import (
    IRGraph,
    IRMetadata,
    IntentNode,
    IntentType,
    ConstraintNode,
    ConstraintType,
    ActionNode,
    ActionType,
    NodePriority,
    IRStatus,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# Compiler Configuration
# =============================================================================

INTENT_EXTRACTION_PROMPT = """You are an intent extraction system. Analyze the user input and extract structured intents.

For each intent found, provide:
- type: one of [create, modify, delete, query, analyze, transform, validate, execute]
- description: clear description of what the user wants
- target: what the intent operates on
- parameters: relevant parameters as key-value pairs
- priority: one of [critical, high, medium, low]
- confidence: 0.0 to 1.0

Return JSON with format:
{
    "intents": [
        {
            "type": "create",
            "description": "...",
            "target": "...",
            "parameters": {},
            "priority": "medium",
            "confidence": 0.95
        }
    ],
    "constraints": [
        {
            "type": "explicit",
            "description": "...",
            "applies_to": ["intent description"],
            "priority": "medium"
        }
    ],
    "suggested_actions": [
        {
            "type": "code_write",
            "description": "...",
            "target": "...",
            "parameters": {}
        }
    ]
}

Analyze this input:
"""


class SemanticCompiler:
    """
    Compiles natural language into IR graphs.

    Uses LLM for semantic understanding and structured extraction.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.3,
    ):
        """
        Initialize the semantic compiler.

        Args:
            api_key: OpenAI API key (uses env if not provided)
            model: LLM model to use
            temperature: Generation temperature
        """
        self._client: Optional[AsyncOpenAI] = None
        self._api_key = api_key
        self._model = model
        self._temperature = temperature

        logger.info(f"SemanticCompiler initialized with model={model}")

    def _ensure_client(self) -> AsyncOpenAI:
        """Ensure OpenAI client is initialized."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    # ==========================================================================
    # Main Compilation
    # ==========================================================================

    async def compile(
        self,
        text: str,
        context: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> IRGraph:
        """
        Compile natural language text into an IR graph.

        Args:
            text: User input text
            context: Optional context for compilation
            session_id: Optional session identifier
            user_id: Optional user identifier

        Returns:
            Compiled IRGraph
        """
        logger.info(f"Compiling text: {text[:100]}...")

        # Create graph with metadata
        graph = IRGraph(
            metadata=IRMetadata(
                source="user_input",
                session_id=session_id,
                user_id=user_id,
                context=context or {},
            )
        )

        # Extract structured data via LLM
        extraction = await self._extract_semantic_structure(text, context)

        # Build intents
        intent_map: dict[str, UUID] = {}
        for intent_data in extraction.get("intents", []):
            intent = self._build_intent(intent_data, text)
            intent_map[intent_data.get("description", "")] = intent.node_id
            graph.add_intent(intent)

        # Build constraints
        for constraint_data in extraction.get("constraints", []):
            constraint = self._build_constraint(constraint_data, intent_map)
            graph.add_constraint(constraint)

        # Build suggested actions
        for action_data in extraction.get("suggested_actions", []):
            action = self._build_action(action_data, intent_map)
            graph.add_action(action)

        # Mark as compiled
        graph.set_status(IRStatus.COMPILED)

        logger.info(
            f"Compilation complete: {len(graph.intents)} intents, "
            f"{len(graph.constraints)} constraints, {len(graph.actions)} actions"
        )

        return graph

    async def _extract_semantic_structure(
        self,
        text: str,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Extract semantic structure from text using LLM.

        Args:
            text: Input text
            context: Optional context

        Returns:
            Extracted structure dict
        """
        client = self._ensure_client()

        # Build prompt
        prompt = INTENT_EXTRACTION_PROMPT + text
        if context:
            prompt += f"\n\nAdditional context:\n{json.dumps(context, indent=2)}"

        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an intent extraction system. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self._temperature,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            # Return basic structure on failure
            return {
                "intents": [
                    {
                        "type": "execute",
                        "description": text,
                        "target": "unknown",
                        "parameters": {},
                        "priority": "medium",
                        "confidence": 0.5,
                    }
                ],
                "constraints": [],
                "suggested_actions": [],
            }

    # ==========================================================================
    # Node Builders
    # ==========================================================================

    def _build_intent(
        self,
        data: dict[str, Any],
        source_text: str,
    ) -> IntentNode:
        """Build an IntentNode from extracted data."""
        intent_type = self._parse_intent_type(data.get("type", "execute"))
        priority = self._parse_priority(data.get("priority", "medium"))

        return IntentNode(
            intent_type=intent_type,
            description=data.get("description", ""),
            target=data.get("target", "unknown"),
            parameters=data.get("parameters", {}),
            priority=priority,
            confidence=float(data.get("confidence", 0.8)),
            source_text=source_text,
        )

    def _build_constraint(
        self,
        data: dict[str, Any],
        intent_map: dict[str, UUID],
    ) -> ConstraintNode:
        """Build a ConstraintNode from extracted data."""
        constraint_type = self._parse_constraint_type(data.get("type", "explicit"))
        priority = self._parse_priority(data.get("priority", "medium"))

        # Map applies_to descriptions to intent IDs
        applies_to: list[UUID] = []
        for desc in data.get("applies_to", []):
            if desc in intent_map:
                applies_to.append(intent_map[desc])

        return ConstraintNode(
            constraint_type=constraint_type,
            description=data.get("description", ""),
            applies_to=applies_to,
            priority=priority,
            confidence=float(data.get("confidence", 0.8)),
        )

    def _build_action(
        self,
        data: dict[str, Any],
        intent_map: dict[str, UUID],
    ) -> ActionNode:
        """Build an ActionNode from extracted data."""
        action_type = self._parse_action_type(data.get("type", "code_write"))
        priority = self._parse_priority(data.get("priority", "medium"))

        # Find derived_from intent
        derived_from: Optional[UUID] = None
        derived_desc = data.get("derived_from", "")
        if derived_desc in intent_map:
            derived_from = intent_map[derived_desc]

        return ActionNode(
            action_type=action_type,
            description=data.get("description", ""),
            target=data.get("target", "unknown"),
            parameters=data.get("parameters", {}),
            priority=priority,
            derived_from_intent=derived_from,
        )

    # ==========================================================================
    # Type Parsers
    # ==========================================================================

    def _parse_intent_type(self, value: str) -> IntentType:
        """Parse intent type string to enum."""
        mapping = {
            "create": IntentType.CREATE,
            "modify": IntentType.MODIFY,
            "delete": IntentType.DELETE,
            "query": IntentType.QUERY,
            "analyze": IntentType.ANALYZE,
            "transform": IntentType.TRANSFORM,
            "validate": IntentType.VALIDATE,
            "execute": IntentType.EXECUTE,
        }
        return mapping.get(value.lower(), IntentType.EXECUTE)

    def _parse_constraint_type(self, value: str) -> ConstraintType:
        """Parse constraint type string to enum."""
        mapping = {
            "explicit": ConstraintType.EXPLICIT,
            "implicit": ConstraintType.IMPLICIT,
            "hidden": ConstraintType.HIDDEN,
            "false": ConstraintType.FALSE,
            "system": ConstraintType.SYSTEM,
        }
        return mapping.get(value.lower(), ConstraintType.EXPLICIT)

    def _parse_action_type(self, value: str) -> ActionType:
        """Parse action type string to enum."""
        mapping = {
            "code_write": ActionType.CODE_WRITE,
            "code_read": ActionType.CODE_READ,
            "code_modify": ActionType.CODE_MODIFY,
            "file_create": ActionType.FILE_CREATE,
            "file_delete": ActionType.FILE_DELETE,
            "api_call": ActionType.API_CALL,
            "reasoning": ActionType.REASONING,
            "validation": ActionType.VALIDATION,
            "simulation": ActionType.SIMULATION,
        }
        return mapping.get(value.lower(), ActionType.CODE_WRITE)

    def _parse_priority(self, value: str) -> NodePriority:
        """Parse priority string to enum."""
        mapping = {
            "critical": NodePriority.CRITICAL,
            "high": NodePriority.HIGH,
            "medium": NodePriority.MEDIUM,
            "low": NodePriority.LOW,
        }
        return mapping.get(value.lower(), NodePriority.MEDIUM)

    # ==========================================================================
    # Incremental Compilation
    # ==========================================================================

    async def compile_incremental(
        self,
        graph: IRGraph,
        additional_text: str,
    ) -> IRGraph:
        """
        Incrementally add to an existing IR graph.

        Args:
            graph: Existing IR graph
            additional_text: New text to compile

        Returns:
            Updated IRGraph
        """
        logger.info(f"Incremental compilation: {additional_text[:50]}...")

        # Extract from new text
        context = {"existing_intents": [i.description for i in graph.intents.values()]}
        extraction = await self._extract_semantic_structure(additional_text, context)

        # Add new nodes
        intent_map: dict[str, UUID] = {}
        for intent in graph.intents.values():
            intent_map[intent.description] = intent.node_id

        for intent_data in extraction.get("intents", []):
            intent = self._build_intent(intent_data, additional_text)
            intent_map[intent_data.get("description", "")] = intent.node_id
            graph.add_intent(intent)

        for constraint_data in extraction.get("constraints", []):
            constraint = self._build_constraint(constraint_data, intent_map)
            graph.add_constraint(constraint)

        for action_data in extraction.get("suggested_actions", []):
            action = self._build_action(action_data, intent_map)
            graph.add_action(action)

        return graph


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "IR_-INTE-004",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "engine",
        "intelligence",
        "ir-compilation",
        "llm",
        "logging",
        "messaging",
        "serialization",
    ],
    "keywords": ["compile", "compiler", "incremental", "semantic"],
    "business_value": "Implements SemanticCompiler for semantic compiler functionality",
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
