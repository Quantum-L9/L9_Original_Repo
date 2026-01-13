"""
L9 Core - SubstrateRetriever
Version: 1.0.0

LangChain-compatible retriever that uses the Memory Substrate's
semantic_search API under the hood.
"""

from __future__ import annotations

from typing import Any, List, Optional

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from core.schemas.packet_envelope_v2 import SemanticSearchRequest, SemanticSearchResult
from memory.substrate_service import MemorySubstrateService


class SubstrateRetriever(BaseRetriever):
    """
    LangChain retriever wrapper over MemorySubstrateService.semantic_search.
    """

    def __init__(
        self,
        service: MemorySubstrateService,
        agent_id: Optional[str] = None,
        top_k: int = 5,
    ) -> None:
        super().__init__()
        self._service = service
        self._agent_id = agent_id
        self._top_k = top_k

    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """
        Async retrieval of relevant documents using semantic_search.
        """
        request = SemanticSearchRequest(
            query=query,
            top_k=self._top_k,
            agent_id=self._agent_id,
        )
        result: SemanticSearchResult = await self._service.semantic_search(request)

        docs: List[Document] = []
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

    def _get_relevant_documents(self, query: str) -> List[Document]:
        """
        Synchronous wrapper required by BaseRetriever.

        NOTE: This should only be used in non-async contexts; otherwise prefer
        the async API from LangChain.
        """
        import asyncio

        return asyncio.run(self._aget_relevant_documents(query))
