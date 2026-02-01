"""
EOS Hypergraph Client — L9 Accountability Constraint Queries
============================================================

Wraps Neo4jClient to provide EOS-specific hypergraph queries for
constraint checking, permission validation, and violation detection.

The hypergraph models:
- Permission edges (agent)-[:HAS_CAPABILITY]->(capability)
- Constraint edges (action)-[:VIOLATES]->(prohibition)
- Obligation edges (action)-[:REQUIRES]->(evidence)
- Causal edges (action)-[:CAUSED]->(state_change)

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "EOS Hypergraph Client",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-25T18:30:00Z",
    "layer": "foundation",
    "domain": "eos",
    "module_name": "hypergraph_client",
    "type": "client",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": [],
        "imported_by": ["core.eos.accountability_engine"],
    },
}
# ============================================================================

from datetime import UTC
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class EOSHypergraphClient:
    """
    EOS-specific hypergraph client for accountability queries.

    Provides constraint checking, permission validation, and
    violation detection using the accountability hypergraph schema.

    The hypergraph is stored in Neo4j with node types:
    - EpistemicObject (fact, belief, rule, invariant, contract, prohibition)
    - Action (tool_call, code_diff, deploy, db_write, gmp_run, memory_write)
    - Agent (with authority_tier, health_state)
    - Capability (with scope, risk_class)
    - Verdict (allow, deny, conditional, rollback)
    """

    def __init__(self, neo4j_client: Any | None = None):
        """
        Initialize EOS Hypergraph Client.

        Args:
            neo4j_client: Neo4jClient instance from memory.graph_client
        """
        self._neo4j = neo4j_client
        self._available = neo4j_client is not None
        self.logger = logger.bind(component=self.__class__.__name__)

        if self._available:
            self.logger.info("eos.hypergraph_client.initialized")
        else:
            self.logger.warning(
                "eos.hypergraph_client.no_neo4j",
                message="Neo4j client not provided, constraint checks will be skipped",
            )

    @property
    def available(self) -> bool:
        """Check if hypergraph client is available."""
        return self._available and self._neo4j is not None

    async def check_violations(
        self,
        action_type: str,
        agent_id: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Check if an action would violate any constraints.

        Queries the hypergraph for:
        1. (action)-[:VIOLATES]->(prohibition) edges
        2. Missing required (action)-[:REQUIRES]->(evidence) edges
        3. Agent capability mismatches

        Args:
            action_type: Type of action (tool_call, code_diff, etc.)
            agent_id: Agent attempting the action
            context: Additional context for the check

        Returns:
            Dict with 'violations' list and 'satisfied' list
        """
        context = context or {}
        result = {
            "violations": [],
            "satisfied": [],
            "checked": True,
        }

        if not self.available:
            result["checked"] = False
            return result

        try:
            # Query 1: Check for direct prohibition violations
            prohibition_query = """
            MATCH (a:Action {type: $action_type})-[:VIOLATES]->(p:Prohibition)
            WHERE p.active = true
            RETURN p.name AS prohibition, p.description AS description, p.severity AS severity
            """

            prohibitions = await self._neo4j.execute_read(
                prohibition_query,
                action_type=action_type,
            )

            for prohibition in prohibitions:
                result["violations"].append(
                    {
                        "type": "prohibition",
                        "name": prohibition.get("prohibition"),
                        "description": prohibition.get("description"),
                        "severity": prohibition.get("severity", "high"),
                    }
                )

            # Query 2: Check agent capabilities
            capability_query = """
            MATCH (agent:Agent {id: $agent_id})-[:HAS_CAPABILITY]->(cap:Capability)
            WHERE cap.action_type = $action_type
            RETURN cap.name AS capability, cap.scope AS scope, cap.risk_class AS risk_class
            """

            capabilities = await self._neo4j.execute_read(
                capability_query,
                agent_id=agent_id,
                action_type=action_type,
            )

            if not capabilities:
                result["violations"].append(
                    {
                        "type": "missing_capability",
                        "name": f"No capability for {action_type}",
                        "description": f"Agent {agent_id} lacks capability for {action_type}",
                        "severity": "medium",
                    }
                )
            else:
                for cap in capabilities:
                    result["satisfied"].append(
                        {
                            "type": "capability",
                            "name": cap.get("capability"),
                            "scope": cap.get("scope"),
                        }
                    )

            # Query 3: Check required evidence obligations
            obligation_query = """
            MATCH (a:Action {type: $action_type})-[:REQUIRES]->(o:Obligation {type: 'evidence'})
            WHERE o.active = true
            RETURN o.name AS obligation, o.evidence_type AS evidence_type
            """

            obligations = await self._neo4j.execute_read(
                obligation_query,
                action_type=action_type,
            )

            evidence_refs = context.get("evidence_refs", [])
            for obligation in obligations:
                evidence_type = obligation.get("evidence_type")
                if not any(evidence_type in str(ref) for ref in evidence_refs):
                    result["violations"].append(
                        {
                            "type": "missing_evidence",
                            "name": obligation.get("obligation"),
                            "description": f"Missing required evidence: {evidence_type}",
                            "severity": "medium",
                        }
                    )

            self.logger.debug(
                "eos.hypergraph_client.check_violations",
                action_type=action_type,
                agent_id=agent_id,
                violation_count=len(result["violations"]),
                satisfied_count=len(result["satisfied"]),
            )

        except Exception as e:
            self.logger.error(
                "eos.hypergraph_client.check_violations_failed",
                action_type=action_type,
                agent_id=agent_id,
                error=str(e),
            )
            result["checked"] = False
            result["error"] = str(e)

        return result

    async def get_agent_capabilities(
        self,
        agent_id: str,
    ) -> list[dict[str, Any]]:
        """
        Get all capabilities for an agent.

        Args:
            agent_id: Agent ID to query

        Returns:
            List of capability dicts
        """
        if not self.available:
            return []

        try:
            query = """
            MATCH (agent:Agent {id: $agent_id})-[:HAS_CAPABILITY]->(cap:Capability)
            RETURN cap.name AS name, cap.action_type AS action_type,
                   cap.scope AS scope, cap.risk_class AS risk_class
            """

            return await self._neo4j.execute_read(query, agent_id=agent_id)

        except Exception as e:
            self.logger.error(
                "eos.hypergraph_client.get_capabilities_failed",
                agent_id=agent_id,
                error=str(e),
            )
            return []

    async def get_active_prohibitions(self) -> list[dict[str, Any]]:
        """
        Get all active prohibitions in the hypergraph.

        Returns:
            List of prohibition dicts
        """
        if not self.available:
            return []

        try:
            query = """
            MATCH (p:Prohibition)
            WHERE p.active = true
            RETURN p.name AS name, p.description AS description,
                   p.severity AS severity, p.created_at AS created_at
            ORDER BY p.severity DESC
            """

            return await self._neo4j.execute_read(query)

        except Exception as e:
            self.logger.error(
                "eos.hypergraph_client.get_prohibitions_failed",
                error=str(e),
            )
            return []

    async def record_verdict(
        self,
        verdict_id: str,
        action_id: str,
        decision: str,
        agent_id: str,
        justification: list[str] | None = None,
    ) -> bool:
        """
        Record a verdict in the hypergraph for audit trail.

        Creates:
        - (verdict:Verdict) node
        - (verdict)-[:FOR_ACTION]->(action) edge
        - (agent)-[:ISSUED]->(verdict) edge

        Args:
            verdict_id: Unique verdict ID
            action_id: Action the verdict is for
            decision: Verdict decision (allow, deny, conditional, rollback)
            agent_id: Agent that issued the verdict
            justification: List of justification refs

        Returns:
            True if recorded successfully
        """
        if not self.available:
            return False

        try:
            from datetime import datetime

            query = """
            MERGE (v:Verdict {id: $verdict_id})
            SET v.action_id = $action_id,
                v.decision = $decision,
                v.agent_id = $agent_id,
                v.justification = $justification,
                v.created_at = $created_at
            RETURN v.id AS id
            """

            result = await self._neo4j.execute_write(
                query,
                verdict_id=verdict_id,
                action_id=action_id,
                decision=decision,
                agent_id=agent_id,
                justification=justification or [],
                created_at=datetime.now(UTC).isoformat(),
            )

            self.logger.info(
                "eos.hypergraph_client.verdict_recorded",
                verdict_id=verdict_id,
                decision=decision,
            )

            return len(result) > 0

        except Exception as e:
            self.logger.error(
                "eos.hypergraph_client.record_verdict_failed",
                verdict_id=verdict_id,
                error=str(e),
            )
            return False


# =============================================================================
# Factory Function
# =============================================================================


async def create_eos_hypergraph_client() -> EOSHypergraphClient:
    """
    Factory function to create EOSHypergraphClient with Neo4j.

    Uses the singleton Neo4jClient from memory.graph_client.

    Returns:
        Configured EOSHypergraphClient instance
    """
    try:
        from memory.graph_client import get_neo4j_client

        neo4j = await get_neo4j_client()
        return EOSHypergraphClient(neo4j_client=neo4j)
    except ImportError:
        logger.warning("Neo4j client not available, creating without backend")
        return EOSHypergraphClient(neo4j_client=None)
    except Exception as e:
        logger.error(f"Failed to create EOS hypergraph client: {e}")
        return EOSHypergraphClient(neo4j_client=None)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "EOSHypergraphClient",
    "create_eos_hypergraph_client",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-214",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.graph_client"],
    "tags": [
        "async",
        "auth",
        "authorization",
        "client",
        "core",
        "debugging",
        "foundation",
        "logging",
        "messaging",
        "service",
    ],
    "keywords": [
        "action",
        "active",
        "agent",
        "available",
        "capabilities",
        "check",
        "client",
        "constraint",
    ],
    "business_value": "Permission edges (agent)-[:HAS_CAPABILITY]->(capability) Constraint edges (action)-[:VIOLATES]->(prohibition) Obligation edges (action)-[:REQUIRES]->(evidence) Causal edges (action)-[:CAUSED]->(state_",
    "last_modified": "2026-01-31T22:21:48Z",
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
