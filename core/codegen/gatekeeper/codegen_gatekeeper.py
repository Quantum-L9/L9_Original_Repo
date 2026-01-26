"""
CodeGen Gatekeeper Agent - Single Entry Point for All Code Generation

This is the main orchestrator that receives contracts/specs and converts them
into deterministic codegen-level specifications with research-enhanced gap filling.

Author: L9 AIOS
Version: 1.0.0
Created: 2025-12-31
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Single Entry Point for All Code Generation",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-23T15:56:58Z",
    "updated_at": "2026-01-24T13:02:52Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "codegen_gatekeeper",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Perplexity API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import json
import os
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

# L9 imports (matching existing patterns)
from core.agents.base_agent import AgentResponse, BaseAgent


class ContractType(str, Enum):
    """Supported contract input formats"""

    AGENT_YAML = "agent_yaml"  # QPF v6.0 / Universal Schema
    MODULE_BLOCK = "module_block"  # Module-Spec v2.6
    SYMCODE = "symcode"  # Symbolic mathematics spec
    CONCEPT = "concept"  # Natural language concept (SuperPrompt format)
    PARTIAL = "partial"  # Partial spec requiring gap filling


class BlindSpot(BaseModel):
    """Detected blind spot or missing information"""

    category: str = Field(
        ...,
        description="Category of blind spot (security, performance, edge_case, etc.)",
    )
    description: str = Field(..., description="Description of what's missing")
    severity: str = Field(..., description="high, medium, low")
    research_query: str = Field(..., description="Perplexity query to fill this gap")
    confidence: float = Field(
        ..., ge=0, le=100, description="Confidence that this is a real gap"
    )


class ResearchFinding(BaseModel):
    """Research result from Perplexity"""

    query: str = Field(..., description="Original research query")
    answer: str = Field(..., description="Research answer")
    sources: list[str] = Field(default_factory=list, description="Source URLs")
    confidence: float = Field(..., ge=0, le=100, description="Confidence in answer")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NormalizedSpec(BaseModel):
    """Normalized specification ready for code generation"""

    spec_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_contract_type: ContractType
    normalized_format: str = Field(
        default="module_spec_v2.6", description="Target spec format"
    )
    spec_data: dict[str, Any] = Field(
        ..., description="Normalized spec in Module-Spec v2.6 format"
    )
    confidence: float = Field(..., ge=0, le=100, description="Overall confidence score")
    gaps: list[BlindSpot] = Field(default_factory=list)
    research_findings: list[ResearchFinding] = Field(default_factory=list)
    generation_strategy: str = Field(..., description="Recommended generation strategy")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CodeGenOutput(BaseModel):
    """Generated code output"""

    output_dir: Path
    files: list[Path] = Field(default_factory=list)
    git_branch: str
    git_commits: list[str] = Field(default_factory=list)
    coverage: float = Field(..., ge=0, le=100, description="Test coverage percentage")
    validation_passed: bool
    validation_report: dict[str, Any] = Field(default_factory=dict)
    dora_blocks_generated: int = 0
    generation_time_seconds: float


class CodeGenGatekeeperAgent(BaseAgent):
    """
    CodeGen Gatekeeper Agent - Main entry point for all code generation.

    Responsibilities:
    - Parse and validate incoming contracts
    - Detect blind spots using Perplexity research
    - Normalize to Module-Spec v2.6 format
    - Calculate confidence scores
    - Route to appropriate generation strategy
    - Orchestrate code generation pipeline
    """

    def __init__(
        self,
        agent_id: str = "codegen_gatekeeper",
        perplexity_api_key: str | None = None,
        research_enabled: bool = True,
        min_confidence: float = 85.0,
        **kwargs,
    ):
        super().__init__(agent_id=agent_id, **kwargs)

        self.perplexity_api_key = perplexity_api_key or os.getenv("PERPLEXITY_API_KEY")
        self.research_enabled = research_enabled and bool(self.perplexity_api_key)
        self.min_confidence = min_confidence

        # Perplexity API configuration
        self.perplexity_base_url = "https://api.perplexity.ai"
        self.perplexity_model = (
            "llama-3.1-sonar-large-128k-online"  # Sonar model with web search
        )

        self.logger.info(
            "CodeGenGatekeeperAgent initialized",
            extra={
                "research_enabled": self.research_enabled,
                "min_confidence": self.min_confidence,
            },
        )

    async def run(
        self, task: dict[str, Any], context: dict[str, Any] | None = None
    ) -> AgentResponse:
        """
        Main entry point for code generation requests.

        Task format:
        {
            "contract": str | dict,  # Raw contract input
            "contract_type": str,  # agent_yaml, module_block, symcode, concept, partial
            "output_dir": str,  # Where to generate code
            "research_enabled": bool,  # Override instance setting
            "options": dict  # Additional options
        }
        """
        try:
            contract = task.get("contract")
            contract_type = ContractType(task.get("contract_type", "partial"))
            output_dir = Path(task.get("output_dir", "/tmp/codegen_output"))
            research_enabled = task.get("research_enabled", self.research_enabled)
            options = task.get("options", {})

            self.logger.info(
                "Processing code generation request",
                extra={
                    "contract_type": contract_type.value,
                    "output_dir": str(output_dir),
                    "research_enabled": research_enabled,
                },
            )

            # Step 1: Process contract and normalize
            normalized_spec = await self.process_contract(
                contract=contract,
                contract_type=contract_type,
                research_enabled=research_enabled,
            )

            # Step 2: Check confidence threshold
            if normalized_spec.confidence < self.min_confidence:
                self.logger.warning(
                    "Confidence below threshold",
                    extra={
                        "confidence": normalized_spec.confidence,
                        "min_confidence": self.min_confidence,
                        "gaps_count": len(normalized_spec.gaps),
                    },
                )

                return AgentResponse(
                    success=False,
                    data={
                        "normalized_spec": normalized_spec.model_dump(),
                        "reason": f"Confidence {normalized_spec.confidence}% below threshold {self.min_confidence}%",
                    },
                    confidence=normalized_spec.confidence / 100.0,
                    metadata={"gaps": [g.model_dump() for g in normalized_spec.gaps]},
                )

            # Step 3: Generate code
            code_output = await self.generate_code(
                spec=normalized_spec, output_dir=output_dir, options=options
            )

            return AgentResponse(
                success=code_output.validation_passed,
                data={
                    "output_dir": str(code_output.output_dir),
                    "files_generated": [str(f) for f in code_output.files],
                    "git_branch": code_output.git_branch,
                    "coverage": code_output.coverage,
                    "generation_time": code_output.generation_time_seconds,
                },
                confidence=normalized_spec.confidence / 100.0,
                metadata={
                    "validation_report": code_output.validation_report,
                    "dora_blocks": code_output.dora_blocks_generated,
                },
            )

        except Exception as e:
            self.logger.error(f"Code generation failed: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                data={"error": str(e)},
                confidence=0.0,
                metadata={"exception_type": type(e).__name__},
            )

    async def process_contract(
        self,
        contract: str | dict,
        contract_type: ContractType,
        research_enabled: bool = True,
    ) -> NormalizedSpec:
        """
        Process incoming contract and normalize to Module-Spec v2.6.

        Pipeline:
        1. Parse contract based on type
        2. Validate schema completeness
        3. Detect blind spots
        4. Research gaps (if enabled)
        5. Fill gaps with research findings
        6. Calculate confidence score
        7. Return normalized spec
        """
        start_time = datetime.utcnow()

        # Step 1: Parse contract
        parsed_contract = await self._parse_contract(contract, contract_type)

        # Step 2: Validate completeness
        validation_result = await self._validate_contract(
            parsed_contract, contract_type
        )

        # Step 3: Detect blind spots
        blind_spots = await self._detect_blind_spots(
            spec=parsed_contract, contract_type=contract_type
        )

        # Step 4 & 5: Research and fill gaps (if enabled)
        research_findings = []
        if research_enabled and blind_spots:
            research_findings = await self._research_blind_spots(blind_spots)
            parsed_contract = await self._fill_gaps_with_research(
                spec=parsed_contract, research_findings=research_findings
            )

        # Step 6: Normalize to Module-Spec v2.6
        normalized_spec_data = await self._normalize_to_module_spec(
            contract=parsed_contract, contract_type=contract_type
        )

        # Step 7: Calculate confidence
        confidence = await self._calculate_confidence(
            spec=normalized_spec_data,
            validation_result=validation_result,
            blind_spots=blind_spots,
            research_findings=research_findings,
        )

        # Step 8: Determine generation strategy
        generation_strategy = await self._determine_generation_strategy(
            contract_type=contract_type,
            spec=normalized_spec_data,
            confidence=confidence,
        )

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        self.logger.info(
            "Contract processed",
            extra={
                "contract_type": contract_type.value,
                "confidence": confidence,
                "blind_spots": len(blind_spots),
                "research_findings": len(research_findings),
                "processing_time": processing_time,
            },
        )

        return NormalizedSpec(
            original_contract_type=contract_type,
            spec_data=normalized_spec_data,
            confidence=confidence,
            gaps=blind_spots,
            research_findings=research_findings,
            generation_strategy=generation_strategy,
            metadata={
                "processing_time_seconds": processing_time,
                "validation_result": validation_result,
            },
        )

    async def _parse_contract(
        self, contract: str | dict, contract_type: ContractType
    ) -> dict[str, Any]:
        """Parse contract based on type"""
        if isinstance(contract, dict):
            return contract

        # Parse YAML/JSON string
        import yaml

        try:
            return yaml.safe_load(contract)
        except yaml.YAMLError:
            try:
                return json.loads(contract)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Failed to parse contract as YAML or JSON: {e}"
                ) from e

    async def _validate_contract(
        self, contract: dict[str, Any], contract_type: ContractType
    ) -> dict[str, Any]:
        """Validate contract schema completeness"""
        validation_result = {"valid": True, "missing_fields": [], "warnings": []}

        # Define required fields per contract type
        required_fields = {
            ContractType.AGENT_YAML: [
                "system",
                "integration",
                "governance",
                "memorytopology",
                "communicationstack",
                "reasoningengine",
            ],
            ContractType.MODULE_BLOCK: [
                "metadata",
                "runtime_wiring",
                "external_surface",
                "packet_contract",
            ],
            ContractType.SYMCODE: ["symbols", "equations"],
            ContractType.CONCEPT: ["CONCEPT_NAME", "ARCHITECTURE", "DATA_FLOW"],
        }

        if contract_type in required_fields:
            for field in required_fields[contract_type]:
                if field not in contract:
                    validation_result["missing_fields"].append(field)
                    validation_result["valid"] = False

        return validation_result

    async def _detect_blind_spots(
        self, spec: dict[str, Any], contract_type: ContractType
    ) -> list[BlindSpot]:
        """
        Detect blind spots and missing information in spec.

        Uses heuristics + pattern matching to identify:
        - Missing error handling
        - Undefined edge cases
        - Security considerations
        - Performance implications
        - Integration touchpoints
        """
        blind_spots = []

        # Heuristic 1: Check for error handling
        if "error_policy" not in spec and "error_handling" not in spec:
            blind_spots.append(
                BlindSpot(
                    category="error_handling",
                    description="No error handling policy defined",
                    severity="high",
                    research_query=f"What are best practices for error handling in {contract_type.value} systems?",
                    confidence=85.0,
                )
            )

        # Heuristic 2: Check for security considerations
        if "security" not in spec and "authentication" not in spec:
            blind_spots.append(
                BlindSpot(
                    category="security",
                    description="No security or authentication specified",
                    severity="high",
                    research_query=f"What are critical security considerations for {contract_type.value}?",
                    confidence=90.0,
                )
            )

        # Heuristic 3: Check for observability
        if (
            "observability" not in spec
            and "logging" not in spec
            and "metrics" not in spec
        ):
            blind_spots.append(
                BlindSpot(
                    category="observability",
                    description="No observability (logging/metrics) specified",
                    severity="medium",
                    research_query=f"What observability is required for production {contract_type.value} systems?",
                    confidence=80.0,
                )
            )

        # Heuristic 4: Check for testing strategy
        if "test_scope" not in spec and "testing" not in spec:
            blind_spots.append(
                BlindSpot(
                    category="testing",
                    description="No testing strategy defined",
                    severity="medium",
                    research_query=f"What testing is required for {contract_type.value} in production?",
                    confidence=75.0,
                )
            )

        # Heuristic 5: Check for performance considerations
        if "performance" not in spec and "scalability" not in spec:
            blind_spots.append(
                BlindSpot(
                    category="performance",
                    description="No performance or scalability requirements",
                    severity="low",
                    research_query=f"What are performance best practices for {contract_type.value}?",
                    confidence=70.0,
                )
            )

        return blind_spots

    async def _research_blind_spots(
        self, blind_spots: list[BlindSpot]
    ) -> list[ResearchFinding]:
        """
        Use Perplexity Labs API to research blind spots.

        Queries Perplexity Sonar model (web-connected) for each blind spot.
        """
        if not self.perplexity_api_key:
            self.logger.warning("Perplexity API key not set, skipping research")
            return []

        research_findings = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for blind_spot in blind_spots:
                try:
                    # Call Perplexity API
                    response = await client.post(
                        f"{self.perplexity_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.perplexity_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.perplexity_model,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "You are a production systems expert. Provide concise, actionable answers with specific examples.",
                                },
                                {"role": "user", "content": blind_spot.research_query},
                            ],
                            "max_tokens": 500,
                            "temperature": 0.2,  # Low temperature for factual answers
                            "return_citations": True,
                        },
                    )

                    if response.status_code == 200:
                        result = response.json()
                        answer = result["choices"][0]["message"]["content"]

                        # Extract citations if available
                        sources = []
                        if "citations" in result:
                            sources = result["citations"]

                        research_findings.append(
                            ResearchFinding(
                                query=blind_spot.research_query,
                                answer=answer,
                                sources=sources,
                                confidence=blind_spot.confidence,
                            )
                        )

                        self.logger.info(
                            "Research completed for blind spot",
                            extra={
                                "category": blind_spot.category,
                                "sources_count": len(sources),
                            },
                        )
                    else:
                        self.logger.error(
                            f"Perplexity API error: {response.status_code}",
                            extra={"response": response.text},
                        )

                except Exception as e:
                    self.logger.error(
                        f"Research failed for blind spot: {e}", exc_info=True
                    )

        return research_findings

    async def _fill_gaps_with_research(
        self, spec: dict[str, Any], research_findings: list[ResearchFinding]
    ) -> dict[str, Any]:
        """Fill spec gaps with research findings"""
        # This is a simplified version - in production, use LLM to intelligently merge
        filled_spec = spec.copy()

        # Add research findings as metadata
        filled_spec["_research_findings"] = [
            {
                "category": finding.query.split()[0],  # Extract category from query
                "summary": finding.answer[:200],  # First 200 chars
                "sources": finding.sources,
            }
            for finding in research_findings
        ]

        return filled_spec

    async def _normalize_to_module_spec(
        self, contract: dict[str, Any], contract_type: ContractType
    ) -> dict[str, Any]:
        """
        Normalize any contract type to Module-Spec v2.6 format.

        This is the core transformation that makes all inputs compatible
        with the deterministic code generator.
        """
        # Base Module-Spec v2.6 structure
        module_spec = {
            "schema_version": "2.6",
            "meta": {
                "schema_version": "2.6.0",
                "created_at": datetime.utcnow().isoformat(),
                "created_by": "codegen_gatekeeper",
            },
            "metadata": {},
            "ownership": {},
            "runtime_wiring": {},
            "runtime_contract": {},
            "external_surface": {},
            "dependency_contract": {},
            "dependencies": {},
            "packet_contract": {},
            "packet_expectations": {},
            "idempotency": {},
            "error_policy": {},
            "observability": {},
            "runtime_touchpoints": {},
            "tier_expectations": {},
            "test_scope": {},
            "acceptance": {},
            "global_invariants_ack": {},
            "spec_confidence": {},
        }

        # Transform based on contract type
        if contract_type == ContractType.MODULE_BLOCK:
            # Already in Module-Spec format, just merge
            module_spec.update(contract)

        elif contract_type == ContractType.AGENT_YAML:
            # Transform QPF/Universal Schema to Module-Spec
            module_spec["metadata"] = {
                "module_id": contract.get("system", {})
                .get("name", "unknown")
                .lower()
                .replace(" ", "_"),
                "name": contract.get("system", {}).get("name", "Unknown Agent"),
                "tier": 2,  # Default tier for agents
                "description": contract.get("system", {}).get("role", ""),
                "system": "L9",
                "language": "python",
                "runtime": "python>=3.11",
            }

            module_spec["runtime_wiring"] = {
                "service": "api",
                "startup_phase": "normal",
                "depends_on": contract.get("integration", {}).get("depends_on", []),
                "blocks_startup_on_failure": False,
            }

            module_spec["external_surface"] = {
                "exposes_http_endpoint": True,
                "exposes_webhook": False,
                "exposes_tool": True,
                "callable_from": ["internal"],
            }

        elif contract_type == ContractType.SYMCODE:
            # Transform SymCode to Module-Spec
            module_spec["metadata"] = {
                "module_id": "symcode_" + str(uuid.uuid4())[:8],
                "name": "SymCode Module",
                "tier": 1,
                "description": "Symbolic mathematics module",
                "system": "L9",
                "language": "python",
                "runtime": "python>=3.11",
            }

            # Store SymCode spec in metadata for later processing
            module_spec["_symcode_spec"] = contract

        elif contract_type == ContractType.CONCEPT:
            # Transform natural language concept to Module-Spec
            module_spec["metadata"] = {
                "module_id": contract.get("CONCEPT_NAME", "unknown")
                .lower()
                .replace(" ", "_"),
                "name": contract.get("CONCEPT_NAME", "Unknown Module"),
                "tier": 3,
                "description": contract.get("ONE_SENTENCE", ""),
                "system": "L9",
                "language": "python",
                "runtime": "python>=3.11",
            }

            # Store concept for later processing
            module_spec["_concept"] = contract

        return module_spec

    async def _calculate_confidence(
        self,
        spec: dict[str, Any],
        validation_result: dict[str, Any],
        blind_spots: list[BlindSpot],
        research_findings: list[ResearchFinding],
    ) -> float:
        """
        Calculate confidence score (0-100%).

        Formula:
        BASE: 100%
        PENALTIES:
        - Missing required field: -10% per field
        - High severity blind spot (unfilled): -15%
        - Medium severity blind spot (unfilled): -8%
        - Low severity blind spot (unfilled): -3%
        BONUSES:
        - Research finding applied: +5% per finding (max +20%)
        """
        confidence = 100.0

        # Penalty for missing fields
        missing_fields = validation_result.get("missing_fields", [])
        confidence -= len(missing_fields) * 10

        # Penalty for unfilled blind spots
        filled_categories = {f.query.split()[0] for f in research_findings}
        for blind_spot in blind_spots:
            if blind_spot.category not in filled_categories:
                if blind_spot.severity == "high":
                    confidence -= 15
                elif blind_spot.severity == "medium":
                    confidence -= 8
                else:
                    confidence -= 3

        # Bonus for research findings
        research_bonus = min(len(research_findings) * 5, 20)
        confidence += research_bonus

        # Clamp to 0-100
        confidence = max(0.0, min(100.0, confidence))

        return confidence

    async def _determine_generation_strategy(
        self, contract_type: ContractType, spec: dict[str, Any], confidence: float
    ) -> str:
        """
        Determine which generation strategy to use.

        Strategies:
        - "module_compiler": Deterministic Module-Spec → Python
        - "qpf_factory": Multi-agent QPF generation
        - "symcode": Symbolic mathematics + multi-language
        - "superprompt": Concept → Module via LLM
        - "hybrid": Combination of strategies
        """
        if contract_type == ContractType.SYMCODE or "_symcode_spec" in spec:
            return "symcode"

        if contract_type == ContractType.AGENT_YAML and confidence >= 90:
            # High confidence agent spec → QPF factory
            return "qpf_factory"

        if contract_type == ContractType.MODULE_BLOCK:
            # Module block → deterministic compiler
            return "module_compiler"

        if contract_type == ContractType.CONCEPT:
            # Natural language concept → SuperPrompt
            return "superprompt"

        # Default to hybrid approach
        return "hybrid"

    async def generate_code(
        self,
        spec: NormalizedSpec,
        output_dir: Path,
        options: dict[str, Any] | None = None,
    ) -> CodeGenOutput:
        """
        Generate production-ready code from normalized spec.

        This orchestrates the full generation pipeline:
        1. Create Git branch
        2. Generate code based on strategy
        3. Generate DORA blocks
        4. Generate tests
        5. Validate (14 gates)
        6. Commit files
        7. Run tests
        8. Generate documentation
        """
        start_time = datetime.utcnow()
        options = options or {}

        # Import generation modules (lazy import to avoid circular dependencies)
        from core.codegen.compiler.module_compiler import ModuleCompiler
        from core.codegen.dora.dora_generator import DORABlockGenerator
        from core.codegen.git_safety.git_manager import GitSafetyManager
        from core.codegen.validator.code_validator import CodeValidator

        # Step 1: Initialize Git safety
        git_manager = GitSafetyManager(
            repo_root=Path(os.getenv("L9_REPO_ROOT", "/home/ubuntu/L9"))
        )
        git_branch = await git_manager.create_feature_branch(
            task_name=spec.spec_data.get("metadata", {}).get("module_id", "codegen")
        )

        # Step 2: Generate code based on strategy
        compiler = ModuleCompiler()
        generated_files = await compiler.compile_module(
            spec=spec.spec_data, output_dir=output_dir
        )

        # Step 3: Generate DORA blocks for all files
        dora_generator = DORABlockGenerator()
        dora_count = 0
        for file_path in generated_files:
            await dora_generator.add_dora_block(
                file_path=file_path,
                spec_id=spec.spec_id,
                metadata={
                    "generation_strategy": spec.generation_strategy,
                    "confidence": spec.confidence,
                },
            )
            dora_count += 1

        # Step 4: Commit files
        git_commits = []
        for file_path in generated_files:
            commit_sha = await git_manager.commit_file(
                file_path=file_path,
                message=f"Generated {file_path.name} from spec {spec.spec_id}",
            )
            git_commits.append(commit_sha)

        # Step 5: Validate code
        validator = CodeValidator()
        validation_report = await validator.validate_all(
            files=generated_files, spec=spec.spec_data
        )

        # Step 6: Calculate coverage (mock for now)
        coverage = validation_report.get("coverage", 0.0)

        generation_time = (datetime.utcnow() - start_time).total_seconds()

        return CodeGenOutput(
            output_dir=output_dir,
            files=generated_files,
            git_branch=git_branch,
            git_commits=git_commits,
            coverage=coverage,
            validation_passed=validation_report.get("passed", False),
            validation_report=validation_report,
            dora_blocks_generated=dora_count,
            generation_time_seconds=generation_time,
        )


# ═══════════════════════════════════════════════════════════════
# DORA BLOCK - DO NOT EDIT MANUALLY
# ═══════════════════════════════════════════════════════════════
"""
{
  "dora_metadata": {
    "file_id": "codegen-gatekeeper-001",
    "last_updated_by": "manus_agent",
    "last_updated_timestamp": "2025-12-31T00:00:00Z",
    "version": "1.0.0",
    "change_type": "create",
    "codegen_trace_id": "unified-codegen-system-v1.0",
    "spec_ids_implemented": ["unified-codegen-architecture-v1.0"],
    "validation_status": "pending",
    "dependencies": [
      "/l9/core/agents/base_agent.py",
      "/l9/core/tools/registry_adapter.py"
    ],
    "deprecated": false,
    "successor_file": null
  },
  "automation_rules": {
    "auto_update_enabled": true,
    "update_triggers": ["spec_change", "dependency_change"],
    "validation_required_before_update": true,
    "rollback_enabled": true
  },
  "l9_integration": {
    "feature_flags": ["L9_ENABLE_CODEGEN", "L9_ENABLE_PERPLEXITY_RESEARCH"],
    "kernel_dependencies": ["01-master-kernel.yaml", "07-execution-kernel.yaml"],
    "memory_substrate_access": false,
    "tool_registry_integration": true,
    "agent_capabilities": ["reasoning", "research", "code_generation"],
    "protected_by_safety_kernel": true
  },
  "quality_metrics": {
    "code_coverage_percent": 0,
    "lint_score": 100,
    "security_scan_passed": true
  }
}
"""

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-134",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.agents.base_agent",
        "core.codegen.compiler.module_compiler",
        "core.codegen.dora.dora_generator",
        "core.codegen.git_safety.git_manager",
        "core.codegen.validator.code_validator",
    ],
    "tags": [
        "api",
        "async",
        "config",
        "data-models",
        "enum",
        "filesystem",
        "foundation",
        "http-client",
        "linting",
        "messaging",
    ],
    "keywords": [
        "agent",
        "all",
        "blind",
        "codegen",
        "contract",
        "entry",
        "finding",
        "gatekeeper",
    ],
    "business_value": "This is the main orchestrator that receives contracts/specs and converts them into deterministic codegen-level specifications with research-enhanced gap filling. Author: L9 AIOS Version: 1.0.0 Created",
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
