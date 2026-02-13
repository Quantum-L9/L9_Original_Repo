"""
L9 CodeGen Gatekeeper Agent v2.0.0
===================================

Intelligent gatekeeper agent that receives contracts and converts them to
deterministic codegen specs with L9 integration.

**L9 Alignment Features**:
- Inherits from BaseAgent
- Returns PacketEnvelope v2.0.0
- Uses absolute L9 imports
- Includes @rate_limit decorators
- Includes @async_retry decorators
- Integrated with L9 memory substrate

Version: 2.0.0 (L9-Aligned)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "CodeGen Gatekeeper V2",
    "module_version": "2.0.0",
    "created_by": "CodeGenAgent",
    "created_at": "2025-12-31T20:00:00Z",
    "updated_at": "2025-12-31T20:00:00Z",
    "layer": "intelligence",
    "domain": "codegen",
    "module_name": "codegen_gatekeeper_v2",
    "type": "class",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Perplexity API", "PostgreSQL", "Redis"],
        "memory_layers": ["working_memory", "episodic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

# L9 Core Imports (absolute paths)
from agents.base_agent import (
    AgentConfig,
    AgentMessage,
    AgentResponse,
    AgentRole,
    BaseAgent,
)
from clients.memory_client import MemoryClient

# CodeGen imports
from core.codegen.compiler.module_compiler_v2 import ModuleCompilerV2
from core.decorators import must_stay_async
from core.governance.rate_limit_policy import rate_limit
from core.resilience.retry import AsyncRetryConfig, async_retry
from core.schemas import (
    PacketEnvelope,
    PacketMetadata,
    PacketProvenance,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums and Data Models
# =============================================================================


class ContractType(str, Enum):
    """Type of input contract"""

    AGENT_YAML = "agent_yaml"
    MODULE_BLOCK = "module_block"
    SYMCODE = "symcode"
    CONCEPT = "concept"


@dataclass
class BlindSpot:
    """Detected blind spot in spec"""

    field: str
    issue: str
    severity: str  # "critical", "high", "medium", "low"
    suggestion: str


@dataclass
class ResearchFinding:
    """Research finding from Perplexity"""

    query: str
    answer: str
    sources: list[str]
    confidence: float


@dataclass
class NormalizedSpec:
    """Normalized Module-Spec v2.6"""

    spec: dict[str, Any]
    confidence: float
    blind_spots_filled: int
    research_findings: list[ResearchFinding]


# =============================================================================
# CodeGen Gatekeeper Agent
# =============================================================================


class CodeGenGatekeeperAgent(BaseAgent):
    """
    CodeGen Gatekeeper Agent - L9 Integrated

    Intelligent gatekeeper that receives contracts and converts them to
    deterministic codegen specs.

    **Features**:
    - 4 contract types (Agent YAML, Module Block, SymCode, Concept)
    - Blind spot detection (5 heuristics)
    - Perplexity Labs integration (live research)
    - Gap filling with research findings
    - Normalization to Module-Spec v2.6
    - Confidence scoring (0-100%)
    - L9 memory substrate integration

    **Agent Role**: REFLECTION (meta-reasoning)
    **Tier**: 1 (high autonomy)
    **Escalation Path**: Igor
    """

    agent_role = AgentRole.REFLECTION
    agent_name = "codegen_gatekeeper"

    def __init__(
        self,
        agent_id: str | None = None,
        config: AgentConfig | None = None,
    ):
        """
        Initialize CodeGen Gatekeeper Agent.

        Args:
            agent_id: Unique agent identifier
            config: Agent configuration
        """
        super().__init__(agent_id, config)
        self.memory = MemoryClient()
        self.compiler = ModuleCompilerV2()
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")

        logger.info(
            "CodeGenGatekeeperAgent initialized",
            agent_id=self.agent_id,
            perplexity_enabled=bool(self.perplexity_api_key),
        )

    def get_system_prompt(self) -> str:
        """Get the agent's system prompt"""
        return """You are the CodeGen Gatekeeper Agent for L9 AIOS.

Role: Intelligent contract processor and spec normalizer
Tier: 1 (high autonomy)
Escalation Path: Igor

Your responsibilities:
1. Parse incoming contracts (Agent YAML, Module Block, SymCode, Concept)
2. Detect blind spots and missing information
3. Research gaps using Perplexity Labs API
4. Fill gaps deterministically with research findings
5. Normalize to Module-Spec v2.6
6. Calculate confidence scores
7. Route to appropriate code generator

You are a critical gatekeeper ensuring high-quality, complete specs
before code generation. Be thorough and precise.
"""

    @must_stay_async("callers use await")
    async def run(
        self, task: dict[str, Any], context: dict[str, Any] | None = None
    ) -> AgentResponse:
        """
        Execute the gatekeeper's primary function.

        Args:
            task: Task with 'contract', 'contract_type', 'output_dir'
            context: Optional execution context

        Returns:
            AgentResponse with PacketEnvelope result
        """
        logger.info(
            "CodeGenGatekeeperAgent starting task",
            agent_id=self.agent_id,
            task_keys=list(task.keys()),
        )

        try:
            # Extract task parameters
            contract = task.get("contract", "")
            contract_type = ContractType(task.get("contract_type", "agent_yaml"))
            output_dir = task.get("output_dir", "/tmp/codegen_output")
            enable_research = task.get("enable_research", True)

            # Step 1: Parse contract
            logger.info("Parsing contract", contract_type=contract_type.value)
            parsed_spec = await self._parse_contract(contract, contract_type)

            # Step 2: Detect blind spots
            logger.info("Detecting blind spots")
            blind_spots = await self._detect_blind_spots(parsed_spec)

            # Step 3: Research blind spots (if enabled)
            research_findings = []
            if enable_research and blind_spots and self.perplexity_api_key:
                logger.info("Researching blind spots", count=len(blind_spots))
                research_findings = await self._research_blind_spots(blind_spots)

            # Step 4: Fill gaps
            logger.info("Filling gaps", findings_count=len(research_findings))
            filled_spec = await self._fill_gaps(parsed_spec, research_findings)

            # Step 5: Normalize to Module-Spec v2.6
            logger.info("Normalizing to Module-Spec v2.6")
            normalized = await self._normalize_to_module_spec(filled_spec)

            # Step 6: Calculate confidence
            confidence = await self._calculate_confidence(normalized.spec, blind_spots)

            # Step 7: Generate code
            logger.info("Compiling module", confidence=confidence)
            compiler_output = await self.compiler.compile(
                spec=normalized.spec, output_dir=output_dir
            )

            # Create result payload
            result = {
                "files_generated": compiler_output.files_generated,
                "output_dir": str(compiler_output.output_dir),
                "module_id": compiler_output.module_id,
                "confidence": confidence,
                "blind_spots_detected": len(blind_spots),
                "blind_spots_filled": normalized.blind_spots_filled,
                "research_findings": len(research_findings),
                "spec": normalized.spec,
            }

            # Create PacketEnvelope response
            packet = PacketEnvelope(
                packet_type="codegen.result",
                payload=result,
                metadata=PacketMetadata(
                    agent=self.agent_name, schema_version="2.0.0", domain="codegen"
                ),
                provenance=PacketProvenance(
                    source_agent=self.agent_id,
                    source="agent",
                    tool="codegen",
                ),
                tags=["codegen", "module_generation", compiler_output.module_id],
            )

            # Write to memory substrate
            await self.memory.write_packet(
                packet_type=packet.packet_type,
                payload=packet.payload,
                metadata=packet.metadata.model_dump() if packet.metadata else None,
                provenance=packet.provenance.model_dump()
                if packet.provenance
                else None,
            )

            logger.info(
                "CodeGenGatekeeperAgent task completed",
                agent_id=self.agent_id,
                packet_id=str(packet.packet_id),
                files_generated=len(compiler_output.files_generated),
                confidence=confidence,
            )

            return AgentResponse(
                agent_id=self.agent_id,
                content=f"Generated {len(compiler_output.files_generated)} files with {confidence:.1f}% confidence",
                structured_output=result,
                success=True,
            )

        except Exception as e:
            logger.error(
                "CodeGenGatekeeperAgent task failed",
                agent_id=self.agent_id,
                error=str(e),
                exc_info=True,
            )

            return AgentResponse(
                agent_id=self.agent_id,
                content=f"Error: {e!s}",
                success=False,
                error=str(e),
            )

    async def _parse_contract(
        self, contract: str, contract_type: ContractType
    ) -> dict[str, Any]:
        """
        Parse contract into initial spec.

        Args:
            contract: Raw contract string (YAML or text)
            contract_type: Type of contract

        Returns:
            Parsed spec dictionary
        """
        if (
            contract_type == ContractType.AGENT_YAML
            or contract_type == ContractType.MODULE_BLOCK
        ):
            import yaml

            return yaml.safe_load(contract)

        if contract_type == ContractType.CONCEPT:
            # Use LLM to convert concept to spec
            messages = [
                AgentMessage(
                    role="user",
                    content=f"Convert this concept to a Module-Spec v2.6:\n\n{contract}",
                )
            ]
            response = await self.call_llm(messages, json_mode=True)
            return json.loads(response.content)

        raise ValueError(f"Unsupported contract type: {contract_type}")

    async def _detect_blind_spots(self, spec: dict[str, Any]) -> list[BlindSpot]:
        """
        Detect blind spots in spec using 5 heuristics.

        Args:
            spec: Parsed spec

        Returns:
            List of detected blind spots
        """
        blind_spots = []

        # Heuristic 1: Missing required fields
        required_fields = ["metadata", "system", "integration"]
        for field in required_fields:
            if field not in spec or not spec[field]:
                blind_spots.append(
                    BlindSpot(
                        field=field,
                        issue="Missing required field",
                        severity="critical",
                        suggestion=f"Add {field} section to spec",
                    )
                )

        # Heuristic 2: Ambiguous descriptions
        metadata = spec.get("metadata", {})
        description = metadata.get("description", "")
        if len(description) < 20:
            blind_spots.append(
                BlindSpot(
                    field="metadata.description",
                    issue="Description too short or missing",
                    severity="high",
                    suggestion="Provide detailed description (>20 chars)",
                )
            )

        # Heuristic 3: Missing dependencies
        integration = spec.get("integration", {})
        depends_on = integration.get("depends_on", [])
        if not depends_on:
            blind_spots.append(
                BlindSpot(
                    field="integration.depends_on",
                    issue="No dependencies specified",
                    severity="medium",
                    suggestion="Specify kernel and service dependencies",
                )
            )

        # Heuristic 4: Missing governance
        governance = spec.get("governance", {})
        if "tier" not in governance:
            blind_spots.append(
                BlindSpot(
                    field="governance.tier",
                    issue="Tier not specified",
                    severity="medium",
                    suggestion="Specify agent tier (0-3)",
                )
            )

        # Heuristic 5: Incomplete communication stack
        comm_stack = spec.get("communicationstack", {})
        if not comm_stack.get("input_channels"):
            blind_spots.append(
                BlindSpot(
                    field="communicationstack.input_channels",
                    issue="No input channels specified",
                    severity="low",
                    suggestion="Specify input channels (http, packet_envelope, etc.)",
                )
            )

        return blind_spots

    @rate_limit("external.perplexity")
    @async_retry(AsyncRetryConfig(max_retries=3, base_backoff=2.0))
    async def _research_blind_spots(
        self, blind_spots: list[BlindSpot]
    ) -> list[ResearchFinding]:
        """
        Research blind spots using Perplexity Labs API.

        Args:
            blind_spots: List of detected blind spots

        Returns:
            List of research findings
        """
        if not self.perplexity_api_key:
            logger.warning("Perplexity API key not configured, skipping research")
            return []

        findings = []

        # Group blind spots by severity
        critical_spots = [bs for bs in blind_spots if bs.severity == "critical"]
        high_spots = [bs for bs in blind_spots if bs.severity == "high"]

        # Research critical blind spots
        for blind_spot in critical_spots[:3]:  # Limit to 3 queries
            query = f"Best practices for {blind_spot.field} in Python agent systems"

            try:
                # Call Perplexity API
                import httpx

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.perplexity.ai/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.perplexity_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": "llama-3.1-sonar-small-128k-online",
                            "messages": [{"role": "user", "content": query}],
                        },
                        timeout=30.0,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        answer = data["choices"][0]["message"]["content"]

                        findings.append(
                            ResearchFinding(
                                query=query, answer=answer, sources=[], confidence=0.85
                            )
                        )

                        logger.info(
                            "Research finding obtained",
                            query=query,
                            answer_length=len(answer),
                        )
                    else:
                        logger.warning(
                            "Perplexity API error", status_code=response.status_code
                        )

            except Exception as e:
                logger.error("Research query failed", query=query, error=str(e))

        return findings

    async def _fill_gaps(
        self, spec: dict[str, Any], findings: list[ResearchFinding]
    ) -> dict[str, Any]:
        """
        Fill gaps in spec using research findings.

        Args:
            spec: Parsed spec with gaps
            findings: Research findings

        Returns:
            Spec with gaps filled
        """
        filled_spec = spec.copy()

        # Use LLM to intelligently fill gaps
        if findings:
            findings_text = "\n\n".join(
                [f"Q: {f.query}\nA: {f.answer}" for f in findings]
            )

            messages = [
                AgentMessage(
                    role="user",
                    content=f"""Given this spec:
{json.dumps(spec, indent=2)}

And these research findings:
{findings_text}

Fill in missing fields intelligently. Return complete spec as JSON.""",
                )
            ]

            response = await self.call_llm(messages, json_mode=True)
            filled_spec = json.loads(response.content)

        return filled_spec

    async def _normalize_to_module_spec(self, spec: dict[str, Any]) -> NormalizedSpec:
        """
        Normalize spec to Module-Spec v2.6 format.

        Args:
            spec: Filled spec

        Returns:
            Normalized spec
        """
        # Ensure all required Module-Spec v2.6 fields
        normalized = {
            "schema_version": "2.6",
            "metadata": spec.get("metadata", {}),
            "system": spec.get("system", {}),
            "integration": spec.get("integration", {}),
            "governance": spec.get("governance", {}),
            "memorytopology": spec.get("memorytopology", {}),
            "communicationstack": spec.get("communicationstack", {}),
            "reasoningengine": spec.get("reasoningengine", {}),
            "runtime_wiring": spec.get("runtime_wiring", {}),
            "external_surface": spec.get("external_surface", {}),
            "dependency_contract": spec.get("dependency_contract", {}),
            "packet_contract": spec.get("packet_contract", {}),
            "error_policy": spec.get("error_policy", {}),
        }

        return NormalizedSpec(
            spec=normalized, confidence=90.0, blind_spots_filled=0, research_findings=[]
        )

    async def _calculate_confidence(
        self, spec: dict[str, Any], blind_spots: list[BlindSpot]
    ) -> float:
        """
        Calculate confidence score for spec.

        Args:
            spec: Normalized spec
            blind_spots: Detected blind spots

        Returns:
            Confidence score (0-100)
        """
        base_confidence = 100.0

        # Penalty for blind spots
        for blind_spot in blind_spots:
            if blind_spot.severity == "critical":
                base_confidence -= 25.0
            elif blind_spot.severity == "high":
                base_confidence -= 10.0
            elif blind_spot.severity == "medium":
                base_confidence -= 5.0
            else:
                base_confidence -= 2.0

        return max(0.0, min(100.0, base_confidence))


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-133",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "agents.base_agent",
        "core.codegen.compiler.module_compiler_v2",
        "core.decorators",
        "core.governance.rate_limit_policy",
        "core.resilience.retry",
    ],
    "tags": [
        "api",
        "async",
        "auth",
        "config",
        "data-models",
        "dataclass",
        "filesystem",
        "foundation",
        "http-client",
        "logging",
    ],
    "keywords": [
        "agent",
        "blind",
        "codegen",
        "contract",
        "decorators",
        "finding",
        "gatekeeper",
        "gen",
    ],
    "business_value": "Provides codegen gatekeeper v2 components including ContractType, BlindSpot, ResearchFinding",
    "last_modified": "2026-01-24T13:02:52Z",
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
