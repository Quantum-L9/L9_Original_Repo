"""
L9 Core - SubstrateRetriever
Version: 1.0.0

LangChain-compatible retriever that uses the Memory Substrate's
semantic_search API under the hood.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "SubstrateRetriever",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-14T13:21:36Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "substrate_retriever",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": ["core.retrievers.__init__"],
    },
}
# ============================================================================

from typing import Any, TYPE_CHECKING

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from core.schemas import SemanticSearchRequest, SemanticSearchResult

if TYPE_CHECKING:
    from memory.substrate_service import MemorySubstrateService


class SubstrateRetriever(BaseRetriever):
    """
    LangChain retriever wrapper over MemorySubstrateService.semantic_search.
    """

    def __init__(
        self,
        service: MemorySubstrateService,
        agent_id: str | None = None,
        top_k: int = 5,
    ) -> None:
        """
        Performs initialization of the SubstrateRetriever with a MemorySubstrateService for semantic search in the substrate memory.

        Args:
            service: Instance of MemorySubstrateService used to perform semantic searches.
            agent_id: Optional identifier for the agent, used to scope searches.
            top_k: Number of top relevant documents to retrieve during search.
        """
        super().__init__()
        self._service = service
        self._agent_id = agent_id
        self._top_k = top_k

    async def _aget_relevant_documents(self, query: str) -> list[Document]:
        """
        Async retrieval of relevant documents using semantic_search.
        """
        request = SemanticSearchRequest(
            query=query,
            top_k=self._top_k,
            agent_id=self._agent_id,
        )
        result: SemanticSearchResult = await self._service.semantic_search(request)

        docs: list[Document] = []
        for hit in result.hits:
            payload: dict[str, Any] = hit.payload
            text = payload.get("text") or payload.get("content") or str(payload)
            metadata = {
                k: v for k, v in payload.items() if k not in ("text", "content")
            }
            metadata.update(
                {
                    "embedding_id": str(hit.embedding_id),
                    "score": hit.score,
                    "agent_id": self._agent_id,
                }
            )
            docs.append(Document(page_content=text, metadata=metadata))
        return docs

    def _get_relevant_documents(self, query: str) -> list[Document]:
        """
        Synchronous wrapper required by BaseRetriever.

        NOTE: This should only be used in non-async contexts; otherwise prefer
        the async API from LangChain.
        """
        import asyncio

        return asyncio.run(self._aget_relevant_documents(query))


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-012",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas", "memory.substrate_service"],
    "tags": ["async", "core", "foundation", "llm", "service"],
    "keywords": ["memory", "retriever", "substrate", "substrateretriever"],
    "business_value": "Implements SubstrateRetriever for substrate retriever functionality",
    "last_modified": "2026-01-14T13:21:36Z",
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
