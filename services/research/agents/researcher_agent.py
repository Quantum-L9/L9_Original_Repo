"""
L9 Research Factory - Researcher Agent
Version: 1.0.0

Gathers evidence by executing research steps using tools.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Researcher Agent",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "agent_execution",
    "module_name": "researcher_agent",
    "type": "agent",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["services.research.agents.__init__"],
    },
}
# ============================================================================

from datetime import datetime, timezone
from typing import Any

import structlog

from services.research.agents.base_agent import BaseAgent
from services.research.graph_state import Evidence, ResearchStep

logger = structlog.get_logger(__name__)


RESEARCHER_SYSTEM_PROMPT = """You are a research agent. Your job is to gather information based on the given query and synthesize findings.

Given a research query:
1. Analyze what information is needed
2. If tool results are provided, synthesize them
3. Extract key facts, findings, and insights
4. Cite sources when available

Respond in JSON format with:
{
  "findings": "Main findings summary",
  "key_facts": ["fact1", "fact2", ...],
  "sources": ["source1", "source2", ...],
  "confidence": 0.0-1.0,
  "gaps": ["What's missing or unclear"]
}"""


class ResearcherAgent(BaseAgent):
    """
    Researcher Agent - Gathers evidence and information.

    Executes research steps by:
    - Calling tools (Perplexity, web search, etc.)
    - Synthesizing results
    - Extracting evidence
    """

    def __init__(self, agent_id: str = "research_worker"):
        """Initialize researcher agent."""
        super().__init__(agent_id=agent_id)
        self._tool_registry = None
        self._graph_persistence = None

    def set_tool_registry(self, registry: Any) -> None:
        """Set the tool registry for tool execution."""
        self._tool_registry = registry

    def set_graph_persistence(self, persistence: Any) -> None:
        """Set the graph persistence service for persisting findings to Neo4j."""
        self._graph_persistence = persistence

    async def run(
        self,
        step: ResearchStep,
        previous_evidence: list[Evidence] | None = None,
    ) -> Evidence:
        """
        Execute a research step and gather evidence.

        Args:
            step: The research step to execute
            previous_evidence: Evidence from previous steps for context

        Returns:
            Evidence gathered from this step
        """
        step_id = step.get('step_id', 'unknown_step')
        logger.info(f"Researcher executing step: {step_id}")

        query = step.get("query", "")
        tools = step.get("tools", [])

        # Execute tools if available
        tool_results = []
        if self._tool_registry and tools:
            for tool_name in tools:
                try:
                    result = await self._execute_tool(tool_name, query)
                    if result:
                        tool_results.append({"tool": tool_name, "result": result})
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(f"Tool {tool_name} failed with data error: {e}")
                except (ConnectionError, TimeoutError) as e:
                    logger.error(f"Could not connect to the graph database: {e}")
                except Exception as e:
                    logger.error(f"An unexpected error occurred in tool {tool_name}: {e}")

        # Build context from previous evidence
        context = ""
        if previous_evidence:
            context = "\n\nPrevious findings:\n"
            for ev in previous_evidence[-3:]:  # Last 3 pieces
                context += f"- {ev.get('content', '')[:200]}...\n"

        # Build tool results context
        tool_context = ""
        if tool_results:
            tool_context = "\n\nTool Results:\n"
            for tr in tool_results:
                result_str = str(tr["result"])[:1000]
                tool_context += f"[{tr['tool']}]: {result_str}\n"

        # Call LLM to synthesize
        messages = [
            self.format_system_prompt(RESEARCHER_SYSTEM_PROMPT),
            self.format_user_prompt(
                f"Research Query: {query}"
                f"{context}"
                f"{tool_context}"
                "\n\nSynthesize the findings and respond in JSON format."
            ),
        ]

        response = await self.call_llm_json(messages, max_tokens=2000)

        # Create evidence
        evidence = Evidence(
            source=step.get("step_id", "unknown"),
            content=response.get("findings", "No findings"),
            confidence=float(response.get("confidence", 0.5)),
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "key_facts": response.get("key_facts", []),
                "sources": response.get("sources", []),
                "gaps": response.get("gaps", []),
                "tools_used": tools,
            },
        )

        # Persist finding to Neo4j graph if persistence is configured
        if self._graph_persistence:
            try:
                await self._graph_persistence.persist_evidence_as_findings(
                    evidence_list=[evidence],
                    source_query=query,
                    source_agent=self.agent_id,
                )
            except (ConnectionError, TimeoutError) as e:
                    logger.error(f"Could not connect to the graph database: {e}")
                except Exception as e:
                # Don't fail the research if persistence fails
                logger.warning(
                    f"Failed to persist finding to graph: {e}",
                    agent_id=self.agent_id,
                )

        logger.info(
            f"Researcher gathered evidence with confidence {evidence['confidence']}"
        )
        return evidence

    async def _execute_tool(self, tool_name: str, query: str) -> str | None:
        """
        Execute a tool and return results.

        Args:
            tool_name: Name of tool to execute
            query: Query to pass to tool

        Returns:
            Tool result string, or None on failure
        """
        if not self._tool_registry:
            logger.warning("No tool registry available")
            return None

        try:
            tool = self._tool_registry.get(tool_name)
            if tool:
                result = await tool.execute({"query": query})
                return str(result)
        except (ConnectionError, TimeoutError) as e:
                    logger.error(f"Could not connect to the graph database: {e}")
                except Exception as e:
            logger.error(f"Tool execution failed: {e}")

        return None

    async def synthesize_evidence(
        self,
        evidence_list: list[Evidence],
        query: str,
    ) -> str:
        """
        Synthesize multiple pieces of evidence into a summary.

        Args:
            evidence_list: List of evidence to synthesize
            query: Original research query

        Returns:
            Synthesized summary
        """
        if not evidence_list:
            return "No evidence gathered."

        # Format evidence for synthesis
        evidence_text = ""
        for i, ev in enumerate(evidence_list, 1):
            evidence_text += (
                f"\n[Evidence {i}] (confidence: {ev.get('confidence', 0):.2f})\n"
            )
            evidence_text += f"{ev.get('content', '')}\n"
            if ev.get("metadata", {}).get("key_facts"):
                evidence_text += (
                    f"Key facts: {', '.join(ev['metadata']['key_facts'][:5])}\n"
                )

        messages = [
            self.format_system_prompt(
                "You are a research synthesizer. Combine the evidence into a clear, "
                "comprehensive summary. Include key findings, supporting facts, and "
                "note any gaps or uncertainties. Be thorough but concise."
            ),
            self.format_user_prompt(
                f"Original Query: {query}\n\n"
                f"Evidence:{evidence_text}\n\n"
                "Synthesize this evidence into a comprehensive summary."
            ),
        ]

        summary = await self.call_llm(messages, max_tokens=2000)
        return summary.strip()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-011",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["agent", "agent-execution", "async", "logging", "messaging", "operations"],
    "keywords": [
        "agent",
        "evidence",
        "registry",
        "research",
        "researcher",
        "synthesize",
        "tool",
    ],
    "business_value": "Implements ResearcherAgent for researcher agent functionality",
    "last_modified": "2026-01-07T13:35:58Z",
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
