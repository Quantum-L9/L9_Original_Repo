"""
L9 Research Graph Persistence Service
======================================

Persists research findings as typed Neo4j graph nodes.

Finding Types:
- ARCHITECTURE: Architecture decisions
- TRADEOFF: Trade-off analysis
- GAP: Identified gaps
- HYPOTHESIS: Testable hypotheses
- FACT: Verified facts
- INSIGHT: Synthesized insights

All findings are linked to the query/agent that produced them
and create an audit trail in Neo4j.

Version: 1.0.0
Created: 2026-01-20
GMP: Research Graph Persistence
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Research Graph Persistence",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-20T00:00:00Z",
    "updated_at": "2026-01-20T00:00:00Z",
    "layer": "operations",
    "domain": "research_services",
    "module_name": "graph_persistence",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": ["graph_memory"],
        "imported_by": [
            "services.research.__init__",
            "services.research.agents.researcher_agent",
        ],
    },
}
# ============================================================================

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, TypedDict

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# Types
# =============================================================================


class FindingType(str, Enum):
    """Types of research findings."""

    ARCHITECTURE = "ARCHITECTURE"  # Architecture decisions found
    TRADEOFF = "TRADEOFF"  # Trade-off analysis
    GAP = "GAP"  # Identified gaps
    HYPOTHESIS = "HYPOTHESIS"  # Testable hypotheses
    FACT = "FACT"  # Verified facts
    INSIGHT = "INSIGHT"  # Synthesized insights


class ResearchFinding(TypedDict, total=False):
    """A typed research finding for Neo4j persistence."""

    finding_id: str
    finding_type: str  # FindingType value
    content: str
    confidence: float
    source_query: str
    source_agent: str
    key_facts: list[str]
    tags: list[str]
    timestamp: str
    metadata: dict[str, Any]


# =============================================================================
# Configuration
# =============================================================================


class GraphPersistenceConfig:
    """Configuration for Research Graph Persistence."""

    # Schema version for compatibility
    SCHEMA_VERSION: str = "1.0.0"

    # Default confidence threshold for auto-persistence
    MIN_CONFIDENCE_FOR_PERSIST: float = 0.5

    # Maximum findings per query (to prevent spam)
    MAX_FINDINGS_PER_QUERY: int = 20


# =============================================================================
# Neo4j Cypher Queries
# =============================================================================

CREATE_FINDING_QUERY = """
CREATE (f:ResearchFinding {
    id: $finding_id,
    finding_type: $finding_type,
    content: $content,
    confidence: $confidence,
    source_query: $source_query,
    source_agent: $source_agent,
    key_facts: $key_facts,
    tags: $tags,
    created_at: datetime($timestamp),
    schema_version: $schema_version
})
RETURN f.id as finding_id
"""

LINK_FINDING_TO_QUERY_QUERY = """
MATCH (f:ResearchFinding {id: $finding_id})
MERGE (q:ResearchQuery {query: $query_text})
ON CREATE SET q.created_at = datetime($timestamp)
CREATE (q)-[:PRODUCED]->(f)
RETURN f.id as finding_id, q.query as query
"""

LINK_FINDING_TO_AGENT_QUERY = """
MATCH (f:ResearchFinding {id: $finding_id})
MERGE (a:Agent {agent_id: $agent_id})
CREATE (a)-[:DISCOVERED]->(f)
RETURN f.id as finding_id, a.agent_id as agent_id
"""

GET_FINDINGS_BY_TYPE_QUERY = """
MATCH (f:ResearchFinding)
WHERE f.finding_type = $finding_type
  AND f.confidence >= $min_confidence
RETURN f.id as finding_id,
       f.finding_type as finding_type,
       f.content as content,
       f.confidence as confidence,
       f.source_query as source_query,
       f.key_facts as key_facts,
       f.tags as tags,
       f.created_at as created_at
ORDER BY f.confidence DESC, f.created_at DESC
LIMIT $limit
"""

GET_FINDINGS_FOR_QUERY_QUERY = """
MATCH (q:ResearchQuery {query: $query_text})-[:PRODUCED]->(f:ResearchFinding)
RETURN f.id as finding_id,
       f.finding_type as finding_type,
       f.content as content,
       f.confidence as confidence,
       f.key_facts as key_facts,
       f.tags as tags
ORDER BY f.confidence DESC
LIMIT $limit
"""


# =============================================================================
# Research Graph Persistence Service
# =============================================================================


class ResearchGraphPersistence:
    """
    Persists research findings as typed Neo4j graph nodes.

    Usage:
        persistence = ResearchGraphPersistence(neo4j_client)
        finding_id = await persistence.persist_finding(finding)
        await persistence.link_finding_to_query(finding_id, "What is X?")
    """

    def __init__(
        self,
        neo4j_client: Any,
        config: GraphPersistenceConfig | None = None,
    ):
        """
        Initialize Research Graph Persistence.

        Args:
            neo4j_client: Neo4j client instance (memory.graph_client.Neo4jClient)
            config: Optional configuration overrides
        """
        self._neo4j = neo4j_client
        self._config = config or GraphPersistenceConfig()

        logger.info(
            "ResearchGraphPersistence initialized",
            schema_version=self._config.SCHEMA_VERSION,
            min_confidence=self._config.MIN_CONFIDENCE_FOR_PERSIST,
        )

    # =========================================================================
    # Core Operations
    # =========================================================================

    @must_stay_async("callers use await")
    async def persist_finding(
        self,
        finding: ResearchFinding,
    ) -> str:
        """
        Persist a research finding to Neo4j.

        Args:
            finding: The research finding to persist

        Returns:
            finding_id of the persisted finding

        Raises:
            RuntimeError: If Neo4j is unavailable
            ValueError: If finding is invalid
        """
        # Validate
        if not finding.get("content"):
            raise ValueError("Finding must have content")

        if not self._neo4j or not await self._neo4j.is_available():
            logger.error("Neo4j not available, cannot persist finding")
            raise RuntimeError("Neo4j not available")

        # Generate ID if not provided
        finding_id = finding.get("finding_id") or f"find_{uuid.uuid4().hex[:12]}"
        timestamp = finding.get("timestamp") or datetime.now(timezone.utc).isoformat()

        # Validate finding type
        finding_type = finding.get("finding_type", FindingType.INSIGHT.value)
        if finding_type not in [ft.value for ft in FindingType]:
            finding_type = FindingType.INSIGHT.value

        params = {
            "finding_id": finding_id,
            "finding_type": finding_type,
            "content": finding.get("content", ""),
            "confidence": float(finding.get("confidence", 0.5)),
            "source_query": finding.get("source_query", ""),
            "source_agent": finding.get("source_agent", "researcher"),
            "key_facts": finding.get("key_facts", []),
            "tags": finding.get("tags", []),
            "timestamp": timestamp,
            "schema_version": self._config.SCHEMA_VERSION,
        }

        try:
            await self._neo4j.execute_query(CREATE_FINDING_QUERY, params)

            logger.info(
                "research_finding_persisted",
                finding_id=finding_id,
                finding_type=finding_type,
                confidence=params["confidence"],
                source_query=(
                    params["source_query"][:50] + "..."
                    if len(params["source_query"]) > 50
                    else params["source_query"]
                ),
            )

            return finding_id

        except Exception as e:
            logger.error(
                "research_finding_persist_failed",
                finding_id=finding_id,
                error=str(e),
                exc_info=True,
            )
            raise

    @must_stay_async("callers use await")
    async def link_finding_to_query(
        self,
        finding_id: str,
        query_text: str,
    ) -> bool:
        """
        Link a finding to the query that produced it.

        Args:
            finding_id: ID of the finding
            query_text: The research query text

        Returns:
            True if link was created successfully
        """
        if not self._neo4j or not await self._neo4j.is_available():
            logger.warning("Neo4j not available, cannot link finding")
            return False

        params = {
            "finding_id": finding_id,
            "query_text": query_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self._neo4j.execute_query(LINK_FINDING_TO_QUERY_QUERY, params)
            logger.debug("finding_linked_to_query", finding_id=finding_id)
            return True

        except Exception as e:
            logger.error(
                "finding_link_to_query_failed",
                finding_id=finding_id,
                error=str(e),
            )
            return False

    @must_stay_async("callers use await")
    async def link_finding_to_agent(
        self,
        finding_id: str,
        agent_id: str,
    ) -> bool:
        """
        Link a finding to the agent that discovered it.

        Args:
            finding_id: ID of the finding
            agent_id: Agent identifier

        Returns:
            True if link was created successfully
        """
        if not self._neo4j or not await self._neo4j.is_available():
            logger.warning("Neo4j not available, cannot link finding")
            return False

        params = {
            "finding_id": finding_id,
            "agent_id": agent_id,
        }

        try:
            await self._neo4j.execute_query(LINK_FINDING_TO_AGENT_QUERY, params)
            logger.debug("finding_linked_to_agent", finding_id=finding_id)
            return True

        except Exception as e:
            logger.error(
                "finding_link_to_agent_failed",
                finding_id=finding_id,
                error=str(e),
            )
            return False

    # =========================================================================
    # Query Operations
    # =========================================================================

    @must_stay_async("callers use await")
    async def get_findings_by_type(
        self,
        finding_type: FindingType,
        min_confidence: float = 0.5,
        limit: int = 10,
    ) -> list[ResearchFinding]:
        """
        Retrieve findings by type.

        Args:
            finding_type: Type of findings to retrieve
            min_confidence: Minimum confidence threshold
            limit: Maximum results to return

        Returns:
            List of matching findings
        """
        if not self._neo4j or not await self._neo4j.is_available():
            logger.warning("Neo4j not available")
            return []

        params = {
            "finding_type": finding_type.value,
            "min_confidence": min_confidence,
            "limit": limit,
        }

        try:
            results = await self._neo4j.execute_query(
                GET_FINDINGS_BY_TYPE_QUERY, params
            )

            findings = []
            for record in results:
                findings.append(
                    ResearchFinding(
                        finding_id=record["finding_id"],
                        finding_type=record["finding_type"],
                        content=record["content"],
                        confidence=record["confidence"],
                        source_query=record["source_query"],
                        key_facts=record["key_facts"] or [],
                        tags=record["tags"] or [],
                        timestamp=str(record["created_at"]),
                    )
                )

            return findings

        except Exception as e:
            logger.error(
                "get_findings_by_type_failed",
                finding_type=finding_type.value,
                error=str(e),
            )
            return []

    @must_stay_async("callers use await")
    async def get_findings_for_query(
        self,
        query_text: str,
        limit: int = 10,
    ) -> list[ResearchFinding]:
        """
        Get all findings produced by a specific query.

        Args:
            query_text: The query to search for
            limit: Maximum results

        Returns:
            List of findings for this query
        """
        if not self._neo4j or not await self._neo4j.is_available():
            logger.warning("Neo4j not available")
            return []

        params = {
            "query_text": query_text,
            "limit": limit,
        }

        try:
            results = await self._neo4j.execute_query(
                GET_FINDINGS_FOR_QUERY_QUERY, params
            )

            findings = []
            for record in results:
                findings.append(
                    ResearchFinding(
                        finding_id=record["finding_id"],
                        finding_type=record["finding_type"],
                        content=record["content"],
                        confidence=record["confidence"],
                        key_facts=record["key_facts"] or [],
                        tags=record["tags"] or [],
                    )
                )

            return findings

        except Exception as e:
            logger.error(
                "get_findings_for_query_failed",
                query_text=query_text[:50],
                error=str(e),
            )
            return []

    # =========================================================================
    # Batch Operations
    # =========================================================================

    @must_stay_async("callers use await")
    async def persist_evidence_as_findings(
        self,
        evidence_list: list[dict[str, Any]],
        source_query: str,
        source_agent: str = "researcher",
    ) -> list[str]:
        """
        Persist a list of Evidence objects as typed findings.

        Automatically classifies finding types based on content.

        Args:
            evidence_list: List of Evidence dicts from ResearcherAgent
            source_query: The query that produced this evidence
            source_agent: Agent that gathered the evidence

        Returns:
            List of finding IDs created
        """
        finding_ids = []

        # Limit to prevent spam
        evidence_to_process = evidence_list[: self._config.MAX_FINDINGS_PER_QUERY]

        for evidence in evidence_to_process:
            # Skip low confidence evidence
            confidence = float(evidence.get("confidence", 0.5))
            if confidence < self._config.MIN_CONFIDENCE_FOR_PERSIST:
                continue

            # Classify finding type based on content
            finding_type = self._classify_finding_type(evidence)

            finding = ResearchFinding(
                finding_type=finding_type.value,
                content=evidence.get("content", ""),
                confidence=confidence,
                source_query=source_query,
                source_agent=source_agent,
                key_facts=evidence.get("metadata", {}).get("key_facts", []),
                tags=evidence.get("metadata", {}).get("sources", []),
                timestamp=evidence.get("timestamp", datetime.now(timezone.utc).isoformat()),
            )

            try:
                finding_id = await self.persist_finding(finding)
                await self.link_finding_to_query(finding_id, source_query)
                await self.link_finding_to_agent(finding_id, source_agent)
                finding_ids.append(finding_id)

            except Exception as e:
                logger.warning(
                    "evidence_persist_failed",
                    error=str(e),
                )
                continue

        logger.info(
            "evidence_batch_persisted",
            total_evidence=len(evidence_list),
            findings_created=len(finding_ids),
            source_agent=source_agent,
        )

        return finding_ids

    def _classify_finding_type(self, evidence: dict[str, Any]) -> FindingType:
        """
        Classify finding type based on evidence content.

        Simple heuristic classification - can be enhanced with ML.
        """
        content = evidence.get("content", "").lower()
        gaps = evidence.get("metadata", {}).get("gaps", [])

        # Check for gaps
        if gaps or "gap" in content or "missing" in content or "lack" in content:
            return FindingType.GAP

        # Check for architecture
        if any(
            term in content
            for term in ["architecture", "design", "pattern", "system", "structure"]
        ):
            return FindingType.ARCHITECTURE

        # Check for tradeoffs
        if any(term in content for term in ["tradeoff", "trade-off", "vs", "versus"]):
            return FindingType.TRADEOFF

        # Check for hypotheses
        if any(term in content for term in ["hypothesis", "might", "could", "suggest"]):
            return FindingType.HYPOTHESIS

        # Check for facts
        if evidence.get("confidence", 0) >= 0.8:
            return FindingType.FACT

        # Default to insight
        return FindingType.INSIGHT


# =============================================================================
# Factory Function
# =============================================================================


def create_graph_persistence(
    neo4j_client: Any,
    config: GraphPersistenceConfig | None = None,
) -> ResearchGraphPersistence:
    """
    Factory function to create ResearchGraphPersistence.

    Use this in server startup or dependency injection.

    Args:
        neo4j_client: Neo4j client instance
        config: Optional configuration

    Returns:
        Configured ResearchGraphPersistence instance
    """
    return ResearchGraphPersistence(
        neo4j_client=neo4j_client,
        config=config,
    )


# =============================================================================
# Singleton Instance
# =============================================================================

_persistence: ResearchGraphPersistence | None = None


def get_graph_persistence() -> ResearchGraphPersistence | None:
    """Get the singleton persistence instance."""
    return _persistence


def init_graph_persistence(
    neo4j_client: Any,
    config: GraphPersistenceConfig | None = None,
) -> ResearchGraphPersistence:
    """Initialize the singleton persistence instance."""
    global _persistence
    _persistence = create_graph_persistence(neo4j_client, config)
    return _persistence


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-015",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.decorators",
    ],
    "tags": [
        "async",
        "graph-db",
        "neo4j",
        "operations",
        "research-services",
        "service",
    ],
    "keywords": [
        "finding",
        "graph",
        "neo4j",
        "persistence",
        "research",
    ],
    "business_value": "Persists research findings as typed Neo4j nodes for knowledge graph",
    "last_modified": "2026-01-20T00:00:00Z",
    "modified_by": "GMP Research Graph Persistence",
    "change_summary": "Initial implementation",
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
