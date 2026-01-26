

api/memory/router.py
api/memory/router.py
+28
-0

"""
L9 Memory API Router
Version: 1.1.0

Memory substrate API endpoints using MemorySubstrateService.
All packets are automatically ingested via canonical ingest_packet().
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from api.auth import verify_api_key
from typing import Optional, List
from uuid import UUID
import structlog

from memory.substrate_service import get_service
from memory.substrate_models import PacketEnvelopeIn, SemanticSearchRequest
from memory.ingestion import ingest_packet
from memory.retrieval import get_retrieval_pipeline
from memory.housekeeping import get_housekeeping_engine
from orchestrators.memory.interface import MemoryRequest, MemoryOperation
from orchestrators.memory.orchestrator import MemoryOrchestrator
from memory.reasoning_replay import ReasoningReplayPipeline
from memory.consolidation import ConsolidationPipeline
from core.observability.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

logger = structlog.get_logger(__name__)

router = APIRouter()

_batch_circuit_breaker = CircuitBreaker(
    CircuitBreakerConfig(
        failure_threshold=10,
        window_seconds=60,
        reset_timeout=30,
        name="memory_batch",
    )
)


# ============================================================================
# Dependency: Get MemoryOrchestrator from app.state
# ============================================================================


def get_memory_orchestrator(request: Request) -> MemoryOrchestrator:
    """Get MemoryOrchestrator from app.state."""
    orchestrator = getattr(request.app.state, "memory_orchestrator", None)
    if orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="MemoryOrchestrator not initialized. Check server logs.",
        )
    return orchestrator


class PacketRequest(BaseModel):
    """Request model for packet ingestion (PacketEnvelope v2.0 compatible)."""

    packet_type: str
    payload: dict
    metadata: Optional[dict] = None
    provenance: Optional[dict] = None
    confidence: Optional[dict] = None
@@ -472,70 +482,88 @@ class BatchResponse(BaseModel):

    success: bool
    processed_count: int
    errors: List[str] = []


class CompactResponse(BaseModel):
    """Response model for compact operation."""

    success: bool
    message: str


@router.post("/batch", response_model=BatchResponse)
async def batch_write(
    request: BatchRequest,
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    orchestrator: MemoryOrchestrator = Depends(get_memory_orchestrator),
):
    """
    Batch write multiple packets via MemoryOrchestrator.

    This endpoint processes packets in batches for efficient bulk ingestion.
    """
    if _batch_circuit_breaker.is_open():
        cb_stats = _batch_circuit_breaker.get_stats()
        logger.warning(
            "batch_circuit_breaker_open",
            failures_in_window=cb_stats["failures_in_window"],
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "Circuit breaker open: "
                f"{cb_stats['failures_in_window']} failures in "
                f"{cb_stats['window_seconds']}s"
            ),
        )

    try:
        logger.info(
            "Batch write request",
            packet_count=len(request.packets),
            batch_size=request.batch_size,
        )

        mem_request = MemoryRequest(
            operation=MemoryOperation.BATCH_WRITE,
            packets=request.packets,
        )

        result = await orchestrator.execute(mem_request)

        _batch_circuit_breaker.record_success()

        return BatchResponse(
            success=result.success,
            processed_count=result.processed_count,
            errors=result.errors,
        )
    except Exception as e:
        _batch_circuit_breaker.record_failure(str(e))
        logger.error(f"Batch write failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch write failed: {str(e)}")


@router.post("/compact", response_model=CompactResponse)
async def compact_storage(
    authorization: str = Header(None),
    _: bool = Depends(verify_api_key),
    orchestrator: MemoryOrchestrator = Depends(get_memory_orchestrator),
):
    """
    Compact/optimize memory storage via MemoryOrchestrator.

    This endpoint triggers storage optimization (vacuum, reindex, etc.).
    """
    try:
        logger.info("Compact storage request")

        mem_request = MemoryRequest(
            operation=MemoryOperation.COMPACT,
        )

        result = await orchestrator.execute(mem_request)

        return CompactResponse(
core/tools/memory_tools.py
core/tools/memory_tools.py
+29
-1

"""
Memory Tools for Agent Self-Query

Provides memory_search and memory_write tools for agents to access their own memory.
These are low-risk tools that do not require Igor approval.
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import re
import structlog

if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService

logger = structlog.get_logger(__name__)


INJECTION_PATTERNS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bTRUNCATE\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r";.*--",
    r"\bMATCH\s*\(\s*n\s*\)",
    r"\bDETACH\s+DELETE\b",
]


def _detect_query_injection(query: str) -> bool:
    """Detect SQL/Cypher injection patterns in query."""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return True
    return False


class MemorySegment(Enum):
    """Memory segments available for agent queries"""
    GOVERNANCE_META = "governance_meta"      # Kernel rules, policies
    PROJECT_HISTORY = "project_history"      # Past projects, decisions
    TOOL_AUDIT = "tool_audit"                # Tool execution history
    SESSION_CONTEXT = "session_context"      # Current session context
    IDENTITY = "identity"                    # Agent identity, personality
    WORLD_MODEL = "world_model"              # World state, entities


@dataclass
class MemorySearchResult:
    """Result from memory search"""
    id: str
    content: str
    segment: str
    relevance_score: float
    created_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MemoryWriteResult:
    """Result from memory write"""
    success: bool
    chunk_id: Optional[str] = None
    error: Optional[str] = None


async def memory_search(
    agent_id: str,
    query: str,
    segment: Optional[str] = None,
    limit: int = 10,
    substrate_service: Optional["MemorySubstrateService"] = None,
) -> List[MemorySearchResult]:
    """
    Search agent memory for relevant information.

    Args:
        agent_id: Agent performing the search
        query: Natural language query
        segment: Optional segment to search (defaults to all)
        limit: Maximum results to return
        substrate_service: Memory substrate service

    Returns:
        List of MemorySearchResult sorted by relevance
    """
    if _detect_query_injection(query):
        logger.warning(
            "memory_search_injection_blocked",
            agent_id=agent_id,
            query_preview=query[:50],
        )
        return []

    logger.debug(
        "memory_search",
        agent_id=agent_id,
        query=query[:50],
        segment=segment,
        limit=limit,
    )

    if not substrate_service:
        logger.warning("memory_search: substrate_service not available")
        return []

    try:
        # Use substrate semantic search
        if hasattr(substrate_service, 'semantic_search'):
            results = await substrate_service.semantic_search(
                query=query,
                agent_id=agent_id,
                limit=limit,
            )
        elif hasattr(substrate_service, 'search'):
            results = await substrate_service.search(
                query=query,
                filters={"agent_id": agent_id},
                limit=limit,
@@ -333,26 +362,25 @@ async def register_memory_tools(tool_registry: Any, substrate_service: Any = Non

                if 'tool_id' in params or len(params) >= 4:
                    # ExecutorToolRegistry: register_tool(tool_id, name, description, executor)
                    tool_registry.register_tool(
                        tool_id=tool_id,
                        name=name,
                        description=description,
                        executor=executor,
                    )
                else:
                    # Dict-style registration
                    await tool_registry.register_tool(tool_def)
            elif hasattr(tool_registry, 'register'):
                await tool_registry.register(tool_def)
            else:
                logger.warning(f"No register method available on registry for {tool_id}")
                continue

            registered += 1
            logger.debug(f"Registered memory tool: {tool_id}")
        except Exception as e:
            logger.warning(f"Failed to register tool {tool_def['tool_id']}: {e}")

    logger.info(f"✓ Memory tools registered: {registered} tools")
    return registered

memory/__init__.py
memory/__init__.py
+8
-0

@@ -100,83 +100,91 @@ from memory.strategymemory import (
from memory.cypher_templates import (
    CypherTemplate,
    CypherTemplateCategory,
    CypherTemplateLibrary,
    get_template_library,
    execute_template,
)

# Schema Introspection (GMP-55: Dynamic schema discovery)
from memory.schema_introspection import (
    SchemaIntrospector,
    PostgresIntrospector,
    Neo4jIntrospector,
    get_schema_introspector,
)

# Hybrid RAG (GMP-55: Vector-Graph Bridge)
from memory.hybrid_rag import (
    EnrichmentStrategy,
    HybridRAGPipeline,
    HybridSearchResult,
    get_hybrid_rag_pipeline,
    hybrid_search,
)

from memory.substrate_alignment import (
    AlignmentReport,
    SubstrateAlignmentChecker,
)

__all__ = [
    # Models (always available)
    "PacketEnvelope",
    "PacketEnvelopeIn",
    "PacketWriteResult",
    "StructuredReasoningBlock",
    "SemanticSearchRequest",
    "SemanticSearchResult",
    "SemanticHit",
    "SubstrateState",
    # v1.1.0+ Models
    "KnowledgeFact",
    "KnowledgeFactRow",
    "ExtractedInsight",
    # v1.1.0+ Pipelines
    "HousekeepingEngine",
    "get_housekeeping_engine",
    "init_housekeeping_engine",
    "IngestionPipeline",
    "get_ingestion_pipeline",
    "init_ingestion_pipeline",
    "RetrievalPipeline",
    "get_retrieval_pipeline",
    "init_retrieval_pipeline",
    "InsightExtractionPipeline",
    "get_insight_pipeline",
    "init_insight_pipeline",
    # Strategy Memory
    "IStrategyMemoryService",
    "StrategyMemoryService",
    "StrategyCandidate",
    "StrategyRetrievalRequest",
    "StrategyFeedback",
    # Cypher Templates (GMP-55)
    "CypherTemplate",
    "CypherTemplateCategory",
    "CypherTemplateLibrary",
    "get_template_library",
    "execute_template",
    # Schema Introspection (GMP-55)
    "SchemaIntrospector",
    "PostgresIntrospector",
    "Neo4jIntrospector",
    "get_schema_introspector",
    # Hybrid RAG (GMP-55)
    "EnrichmentStrategy",
    "HybridRAGPipeline",
    "HybridSearchResult",
    "get_hybrid_rag_pipeline",
    "hybrid_search",
    # Cross-Substrate Alignment
    "AlignmentReport",
    "SubstrateAlignmentChecker",
    # NOTE: These are available via direct import to avoid circular deps:
    # from memory.substrate_repository import SubstrateRepository, ...
    # from memory.substrate_graph import SubstrateDAG, ...
    # from memory.substrate_service import MemorySubstrateService, ...
    # from memory.substrate_semantic import SemanticService, ...
]

__version__ = "1.1.0"
memory/extractor/agent_config_extractor.py
memory/extractor/agent_config_extractor.py
+1
-1

"""
Agent Configuration Extractor

Extracts preferences, SOPs, roles, signals from conversations.
Uses the recursive_extractor v3.2.0 schema (12 blocks).
Output: Extracted Files/agent_config/*.yaml
"""

import re
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from .base_extractor import BaseExtractor


class AgentConfigExtractor(BaseExtractor):
    """Extracts agent configuration (preferences, SOPs, roles)."""

    def extract(self, input_path: Path, output_root: Path) -> Dict:
    def _do_extraction(self, input_path: Path, output_root: Path) -> Dict:
        """Extract agent configuration from input."""
        self.logger.info(f"AgentConfigExtractor: Processing {input_path.name}")

        content = input_path.read_text(encoding="utf-8", errors="ignore")
        mode = self.get_config("mode") or "full"

        # Extract configuration
        config = self.extract_config(content, mode)

        if not config or not any(config.values()):
            self.logger.warning("No configuration found")
            return {
                "success": False,
                "files_extracted": 0,
                "errors": ["No configuration found"],
            }

        # Create output directory
        output_dir = self.create_output_dir(output_root, "agent_config")
        output_file = output_dir / f"{input_path.stem}_config.yaml"

        # Write YAML output
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(
                config, f, default_flow_style=False, allow_unicode=True, sort_keys=False
memory/extractor/base_extractor.py
memory/extractor/base_extractor.py
+41
-2

"""
Base Extractor Class

All extractors inherit from this base class to ensure consistent interface.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any
from typing import Dict, Any, List
import logging

from memory.substrate_models import PacketEnvelopeIn
from memory.validators.packet_validator import PacketValidator, PacketValidationError


class BaseExtractor(ABC):
    """Base class for all extractors."""

    def __init__(self, config: Dict, logger: logging.Logger):
        """
        Initialize base extractor.

        Args:
            config: Suite configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.name = self.__class__.__name__
        self._validator = PacketValidator()

    @abstractmethod
    def extract(self, input_path: Path, output_root: Path) -> Dict[str, Any]:
    def _do_extraction(
        self,
        input_path: Path,
        output_root: Path,
    ) -> Dict[str, Any]:
        """
        Extract data from input file.

        Args:
            input_path: Path to input file
            output_root: Root output directory (Extracted Files/)

        Returns:
            Dict with extraction results:
            {
                'success': bool,
                'files_extracted': int,
                'output_path': str,
                'errors': List[str]
            }
        """
        pass

    def extract(self, input_path: Path, output_root: Path) -> Dict[str, Any]:
        """
        Extract data from input file with packet validation.

        All extracted packets are validated before returning. Invalid packets are
        logged and dropped.
        """
        result = self._do_extraction(input_path, output_root)
        raw_packets = result.get("packets", [])
        validated: List[PacketEnvelopeIn] = []
        dropped = 0

        for packet in raw_packets:
            try:
                self._validator.validate(packet)
                validated.append(packet)
            except PacketValidationError as exc:
                self.logger.warning(
                    f"Extracted packet invalid, dropping: {exc}",
                    extractor=self.name,
                )
                dropped += 1

        if raw_packets:
            result["packets"] = validated
            result["packets_dropped"] = dropped
            result["packets_validated"] = len(validated)

        return result

    def get_config(self, key: str) -> Any:
        """Get extractor-specific configuration."""
        extractor_key = self.name.lower().replace("extractor", "_extractor")
        return self.config["extractors"].get(extractor_key, {}).get(key)

    def is_enabled(self) -> bool:
        """Check if this extractor is enabled."""
        extractor_key = self.name.lower().replace("extractor", "_extractor")
        return self.config["extractors"].get(extractor_key, {}).get("enabled", False)

    def create_output_dir(self, output_root: Path, subdir: str = "") -> Path:
        """
        Create output directory for this extractor.

        Args:
            output_root: Root output directory
            subdir: Optional subdirectory name

        Returns:
            Path to output directory
        """
        if subdir:
            output_dir = output_root / subdir
        else:
            output_dir = output_root
memory/extractor/code_extractor.py
memory/extractor/code_extractor.py
+1
-1

@@ -16,51 +16,51 @@ class CodeExtractor(BaseExtractor):

    PATTERNS = [
        # Pattern 1: Comment-based path headers
        # # api/mcp/mcp_auth.py
        (
            r"^#\s+([\w/\-\.]+\.(?:py|js|ts|yaml|yml|json|jsx|tsx))\s*$",
            "comment_header",
        ),
        # Pattern 2: Numbered file lists
        # 1) mcp_auth.py
        (r"^\d+\)\s+([\w/\-\.]+\.(?:py|js|ts|yaml|yml|json|jsx|tsx))", "numbered_list"),
        # Pattern 3: Emoji markers
        # 🔥 agent.py – Description
        (
            r"^[🔥📁📄✨💡]\s+([\w/\-\.]+\.(?:py|js|ts|yaml|yml|json|jsx|tsx))",
            "emoji_marker",
        ),
        # Pattern 4: Triple backticks with filename
        # ```python:path/to/file.py
        (
            r"```(?:python|javascript|typescript|yaml|json)?:([\w/\-\.]+\.(?:py|js|ts|yaml|yml|json|jsx|tsx))",
            "code_block_with_path",
        ),
    ]

    def extract(self, input_path: Path, output_root: Path) -> Dict:
    def _do_extraction(self, input_path: Path, output_root: Path) -> Dict:
        """Extract code files from input."""
        self.logger.info(f"CodeExtractor: Processing {input_path.name}")

        content = input_path.read_text(encoding="utf-8", errors="ignore")
        files_extracted = {}
        errors = []

        # Find all code blocks
        code_blocks = self.find_code_blocks(content)

        self.logger.info(f"Found {len(code_blocks)} potential code blocks")

        for file_path, code_content in code_blocks:
            try:
                # Create full output path: Extracted Files/{filepath}
                output_file = output_root / file_path
                output_file.parent.mkdir(parents=True, exist_ok=True)

                # Write file
                output_file.write_text(code_content, encoding="utf-8")
                files_extracted[str(file_path)] = str(output_file)

                self.logger.debug(f"  ✅ Extracted: {file_path}")

            except Exception as e:
memory/extractor/memory_extractor.py
memory/extractor/memory_extractor.py
+1
-1

@@ -10,51 +10,51 @@ import json
from pathlib import Path
from typing import Dict, List
from .base_extractor import BaseExtractor


class MemoryExtractor(BaseExtractor):
    """Extracts structured memory for Supabase."""

    MEMORY_TYPES = [
        "reasoning_block",
        "directive",
        "upgrade_log",
        "context_snapshot",
        "task_memory",
        "convo_memory",
        "agent_registry",
        "experimental_memory",
        "tool_registry",
        "project_glossary",
        "security_directive",
        "file_memory",
        "memory_index",
        "agent_plan",
    ]

    def extract(self, input_path: Path, output_root: Path) -> Dict:
    def _do_extraction(self, input_path: Path, output_root: Path) -> Dict:
        """Extract memory entries from input."""
        self.logger.info(f"MemoryExtractor: Processing {input_path.name}")

        content = input_path.read_text(encoding="utf-8", errors="ignore")

        # Extract memory entries
        memory_entries = self.extract_memory_entries(content)

        if not memory_entries:
            self.logger.warning("No memory entries found")
            return {
                "success": False,
                "files_extracted": 0,
                "errors": ["No memory entries found"],
            }

        # Create output directory
        output_dir = self.create_output_dir(output_root, "memory_db")
        output_file = output_dir / f"{input_path.stem}_memory.json"

        # Write JSON output
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(memory_entries, f, indent=2, ensure_ascii=False)

        self.logger.info(f"  ✅ Extracted {len(memory_entries)} memory entries")
memory/extractor/module_schema_extractor.py
memory/extractor/module_schema_extractor.py
+1
-1

"""
Module Schema Extractor

Extracts L9 module definitions from kernel YAML files.
Output: Extracted Files/modules/*.yaml
"""

import yaml
from pathlib import Path
from typing import Dict
from .base_extractor import BaseExtractor


class ModuleSchemaExtractor(BaseExtractor):
    """Extracts L9 module schema definitions."""

    def extract(self, input_path: Path, output_root: Path) -> Dict:
    def _do_extraction(self, input_path: Path, output_root: Path) -> Dict:
        """Extract module schemas from kernel."""
        self.logger.info(f"ModuleSchemaExtractor: Processing {input_path.name}")

        # Only process YAML files
        if input_path.suffix not in [".yaml", ".yml"]:
            return {
                "success": False,
                "files_extracted": 0,
                "errors": ["Not a YAML file"],
            }

        try:
            # Load kernel
            with open(input_path, "r") as f:
                kernel = yaml.safe_load(f)

            # Check if this is a cognition suite kernel
            if "kernel" not in kernel or "modules" not in kernel.get("kernel", {}):
                return {
                    "success": False,
                    "files_extracted": 0,
                    "errors": ["Not a cognition suite kernel"],
                }

            # Generate modules
