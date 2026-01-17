"""
L9 ResearchSwarm Orchestrator - Implementation
Version: 1.1.0

Runs concurrent research agents, analyst pass, convergence scoring.
"""

import asyncio
from typing import Any, Dict, List, Optional
from uuid import uuid4

import structlog
from core.decorators import must_stay_async

from .interface import (
    IResearchSwarmOrchestrator,
    ResearchSwarmRequest,
    ResearchSwarmResponse,
)

logger = structlog.get_logger(__name__)


class ResearchSwarmOrchestrator(IResearchSwarmOrchestrator):
    """
    ResearchSwarm Orchestrator implementation.

    Spawns parallel research agents, collects results, and attempts consensus.
    """

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize research_swarm orchestrator.

        Args:
            llm_client: Optional LLM client for agent reasoning. If None,
                        attempts to create one from environment.
        """
        self._llm_client = llm_client
        logger.info("ResearchSwarmOrchestrator initialized")

    async def _spawn_research_agent(
        self,
        agent_id: str,
        query: str,
        agent_index: int,
    ) -> Dict[str, Any]:
        """
        Spawn a single research agent to investigate the query.

        Args:
            agent_id: Unique identifier for this agent instance
            query: Research query to investigate
            agent_index: Index of this agent in the swarm

        Returns:
            Agent result dict with findings, confidence, and metadata
        """
        logger.info(
            "Spawning research agent",
            agent_id=agent_id,
            agent_index=agent_index,
            query_length=len(query),
        )

        try:
            # Try to use LLM for actual research
            if self._llm_client:
                # Real LLM-based research
                response = await self._llm_client.chat_completion(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                f"You are Research Agent #{agent_index + 1}. "
                                "Investigate the query thoroughly and provide your findings. "
                                "Be specific and cite your reasoning."
                            ),
                        },
                        {"role": "user", "content": query},
                    ],
                    temperature=0.7
                    + (agent_index * 0.05),  # Slight variation per agent
                )
                findings = response.get("content", "No findings")
                confidence = 0.8
            else:
                # Fallback: Return structured placeholder with agent variation
                findings = (
                    f"Agent {agent_index + 1} analysis of query: '{query[:100]}...'\n"
                    f"Key findings: Query requires further investigation with LLM capability.\n"
                    f"Recommendation: Enable OPENAI_API_KEY for full research capability."
                )
                confidence = 0.5  # Lower confidence without real LLM

            return {
                "agent_id": agent_id,
                "agent_index": agent_index,
                "findings": findings,
                "confidence": confidence,
                "status": "completed",
            }

        except Exception as e:
            logger.error(f"Research agent {agent_id} failed: {e}")
            return {
                "agent_id": agent_id,
                "agent_index": agent_index,
                "findings": None,
                "confidence": 0.0,
                "status": "failed",
                "error": str(e),
            }

    @must_stay_async("callers use await")
    async def _attempt_consensus(
        self,
        results: List[Dict[str, Any]],
        threshold: float,
    ) -> Optional[str]:
        """
        Attempt to reach consensus from agent results.

        Args:
            results: List of agent result dicts
            threshold: Agreement threshold (0.0-1.0)

        Returns:
            Consensus string if reached, None otherwise
        """
        # Filter successful results
        successful = [r for r in results if r.get("status") == "completed"]

        if not successful:
            return None

        # Calculate average confidence
        avg_confidence = sum(r.get("confidence", 0) for r in successful) / len(
            successful
        )

        if avg_confidence >= threshold:
            # Combine findings into consensus
            findings = [r.get("findings", "") for r in successful if r.get("findings")]
            if findings:
                return (
                    f"Consensus reached (confidence: {avg_confidence:.2f}): "
                    + " | ".join(
                        f"Agent {r.get('agent_index', '?')}: {r.get('findings', '')[:200]}"
                        for r in successful[:3]  # Top 3 for brevity
                    )
                )

        return None

    async def execute(self, request: ResearchSwarmRequest) -> ResearchSwarmResponse:
        """
        Execute research_swarm orchestration.

        Spawns parallel agents, collects results, attempts consensus.
        """
        logger.info(
            "Executing research_swarm orchestration",
            query_length=len(request.query),
            agent_count=request.agent_count,
            convergence_threshold=request.convergence_threshold,
        )

        # Spawn agents concurrently
        agent_tasks = [
            self._spawn_research_agent(
                agent_id=f"research-{uuid4().hex[:8]}",
                query=request.query,
                agent_index=i,
            )
            for i in range(request.agent_count)
        ]

        # Gather all results
        results = await asyncio.gather(*agent_tasks, return_exceptions=True)

        # Process results (handle any exceptions)
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "agent_id": f"agent-{i}",
                        "agent_index": i,
                        "status": "error",
                        "error": str(result),
                    }
                )
            else:
                processed_results.append(result)

        # Attempt consensus
        consensus = await self._attempt_consensus(
            processed_results,
            request.convergence_threshold,
        )

        # Determine success
        successful_count = sum(
            1 for r in processed_results if r.get("status") == "completed"
        )
        success = successful_count > 0

        logger.info(
            "Research swarm orchestration complete",
            total_agents=len(processed_results),
            successful=successful_count,
            has_consensus=consensus is not None,
        )

        return ResearchSwarmResponse(
            success=success,
            message=f"Research completed: {successful_count}/{len(processed_results)} agents succeeded",
            results=processed_results,
            consensus=consensus,
        )
