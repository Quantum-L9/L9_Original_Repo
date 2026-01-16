"""
L9 Memory - Cross-Encoder Reranker
Version: 1.0.0

Implements neural re-ranking using cross-encoder models for improved
retrieval quality after initial RRF fusion.

Cross-encoders score (query, document) pairs jointly, producing more
accurate relevance scores than bi-encoder similarity alone.

Features:
- Graceful degradation if sentence-transformers unavailable
- Configurable model selection
- Batch processing for efficiency
- Score normalization
- Singleton pattern for model caching

Based on frontier AI lab patterns (Anthropic, OpenAI, DeepMind).
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = structlog.get_logger(__name__)

# Try to import sentence-transformers
_HAS_CROSS_ENCODER = False
_CrossEncoderModel = None

try:
    from sentence_transformers import CrossEncoder as _CrossEncoderModel

    _HAS_CROSS_ENCODER = True
    logger.info("CrossEncoder available from sentence-transformers")
except ImportError:
    logger.warning(
        "sentence-transformers not available - cross-encoder re-ranking disabled. "
        "Install with: pip install sentence-transformers"
    )


# =============================================================================
# Configuration
# =============================================================================


@dataclass(frozen=True)
class CrossEncoderConfig:
    """Configuration for cross-encoder re-ranking."""

    # Model selection (MS MARCO models are optimized for passage re-ranking)
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Batch size for inference
    batch_size: int = 32

    # Score normalization
    normalize_scores: bool = True

    # Minimum candidates required to trigger re-ranking
    min_candidates: int = 2

    # Maximum candidates to re-rank (for efficiency)
    max_candidates: int = 100

    # Device for inference (None = auto-detect)
    device: Optional[str] = None


# Default configuration
DEFAULT_CONFIG = CrossEncoderConfig()

# Available model presets (trade-off between speed and quality)
MODEL_PRESETS = {
    "fast": "cross-encoder/ms-marco-MiniLM-L-6-v2",  # ~80ms for 100 pairs
    "balanced": "cross-encoder/ms-marco-MiniLM-L-12-v2",  # ~150ms for 100 pairs
    "accurate": "cross-encoder/ms-marco-TinyBERT-L-2-v2",  # Smaller but fast
}


# =============================================================================
# Reranking Result
# =============================================================================


@dataclass
class RerankingResult:
    """Result from cross-encoder re-ranking."""

    # Re-ranked results (sorted by cross-encoder score)
    results: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    query: str = ""
    candidates_received: int = 0
    candidates_reranked: int = 0

    # Timing
    reranking_time_ms: float = 0.0

    # Status
    reranker_used: bool = False
    fallback_reason: Optional[str] = None


# =============================================================================
# Cross-Encoder Reranker
# =============================================================================


class CrossEncoderReranker:
    """
    Cross-encoder based neural re-ranker for improved retrieval quality.

    Uses a cross-encoder model to jointly score (query, document) pairs,
    producing more accurate relevance scores than bi-encoder similarity.

    Features:
    - Graceful degradation if sentence-transformers unavailable
    - Lazy model loading (only loads when first used)
    - Configurable model selection
    - Batch processing for efficiency
    """

    def __init__(self, config: Optional[CrossEncoderConfig] = None):
        """
        Initialize cross-encoder reranker.

        Args:
            config: Configuration (uses defaults if None)
        """
        self._config = config or DEFAULT_CONFIG
        self._model = None
        self._available = _HAS_CROSS_ENCODER

        logger.info(
            "CrossEncoderReranker initialized",
            model=self._config.model_name,
            available=self._available,
        )

    @property
    def is_available(self) -> bool:
        """Check if cross-encoder is available."""
        return self._available

    def _load_model(self) -> bool:
        """
        Lazy-load the cross-encoder model.

        Returns:
            True if model loaded successfully
        """
        if self._model is not None:
            return True

        if not _HAS_CROSS_ENCODER:
            return False

        try:
            self._model = _CrossEncoderModel(
                self._config.model_name,
                device=self._config.device,
            )
            logger.info(f"CrossEncoder model loaded: {self._config.model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to load CrossEncoder model: {e}")
            self._available = False
            return False

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: Optional[int] = None,
        text_key: str = "fact_text",
        fallback_text_keys: Optional[list[str]] = None,
    ) -> RerankingResult:
        """
        Re-rank candidates using cross-encoder scoring.

        Args:
            query: The search query
            candidates: List of candidate dicts to re-rank
            top_k: Number of top results to return (None = all)
            text_key: Primary key to extract text from candidates
            fallback_text_keys: Alternative keys if primary not found

        Returns:
            RerankingResult with re-ranked candidates
        """
        start_time = datetime.utcnow()
        fallback_text_keys = fallback_text_keys or [
            "content",
            "observation",
            "payload",
            "text",
        ]

        result = RerankingResult(
            query=query,
            candidates_received=len(candidates),
        )

        # Check if we should skip re-ranking
        if not candidates:
            result.fallback_reason = "No candidates to re-rank"
            result.results = []
            return result

        if len(candidates) < self._config.min_candidates:
            result.fallback_reason = f"Too few candidates ({len(candidates)} < {self._config.min_candidates})"
            result.results = candidates[:top_k] if top_k else candidates
            return result

        if not self._available:
            result.fallback_reason = "Cross-encoder not available"
            result.results = candidates[:top_k] if top_k else candidates
            return result

        # Lazy load model
        if not self._load_model():
            result.fallback_reason = "Failed to load cross-encoder model"
            result.results = candidates[:top_k] if top_k else candidates
            return result

        # Limit candidates for efficiency
        candidates_to_rank = candidates[: self._config.max_candidates]
        result.candidates_reranked = len(candidates_to_rank)

        # Extract text from candidates
        pairs = []
        for candidate in candidates_to_rank:
            text = self._extract_text(candidate, text_key, fallback_text_keys)
            if text:
                pairs.append((query, text))
            else:
                pairs.append((query, ""))  # Empty fallback

        # Score pairs with cross-encoder
        try:
            scores = self._model.predict(pairs, batch_size=self._config.batch_size)

            # Normalize scores if configured
            if self._config.normalize_scores and len(scores) > 0:
                min_score = min(scores)
                max_score = max(scores)
                if max_score > min_score:
                    scores = [(s - min_score) / (max_score - min_score) for s in scores]

            # Add scores to candidates
            for i, candidate in enumerate(candidates_to_rank):
                candidate["cross_encoder_score"] = float(scores[i])

            # Sort by cross-encoder score (descending)
            candidates_to_rank.sort(
                key=lambda x: x.get("cross_encoder_score", 0), reverse=True
            )

            result.reranker_used = True

        except Exception as e:
            logger.error(f"Cross-encoder prediction failed: {e}")
            result.fallback_reason = f"Prediction error: {str(e)}"

        # Apply top_k limit
        result.results = candidates_to_rank[:top_k] if top_k else candidates_to_rank

        # Calculate timing
        result.reranking_time_ms = (
            datetime.utcnow() - start_time
        ).total_seconds() * 1000

        logger.debug(
            "Re-ranking complete",
            candidates=result.candidates_reranked,
            reranker_used=result.reranker_used,
            time_ms=result.reranking_time_ms,
        )

        return result

    def _extract_text(
        self,
        candidate: dict[str, Any],
        primary_key: str,
        fallback_keys: list[str],
    ) -> str:
        """Extract text content from a candidate dict."""
        # Try primary key
        if primary_key in candidate:
            value = candidate[primary_key]
            if isinstance(value, str) and value.strip():
                return value.strip()

        # Try fallback keys
        for key in fallback_keys:
            if key in candidate:
                value = candidate[key]
                if isinstance(value, str) and value.strip():
                    return value.strip()
                if isinstance(value, dict):
                    # Try to extract from nested dict
                    for nested_key in ["text", "content", "description", "message"]:
                        if nested_key in value:
                            nested_value = value[nested_key]
                            if isinstance(nested_value, str) and nested_value.strip():
                                return nested_value.strip()

        return ""


# =============================================================================
# Singleton / Factory
# =============================================================================


_reranker: Optional[CrossEncoderReranker] = None


def get_cross_encoder_reranker() -> CrossEncoderReranker:
    """Get or create the CrossEncoderReranker singleton."""
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoderReranker()
    return _reranker


def create_reranker_with_model(model_preset: str) -> CrossEncoderReranker:
    """
    Create a reranker with a specific model preset.

    Args:
        model_preset: One of "fast", "balanced", "accurate"

    Returns:
        Configured CrossEncoderReranker
    """
    model_name = MODEL_PRESETS.get(model_preset, MODEL_PRESETS["fast"])
    config = CrossEncoderConfig(model_name=model_name)
    return CrossEncoderReranker(config)


def is_cross_encoder_available() -> bool:
    """Check if cross-encoder re-ranking is available."""
    return _HAS_CROSS_ENCODER
