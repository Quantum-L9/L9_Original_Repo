"""
Blob Store — S3 Client for Large Content Offloading
====================================================

Provides S3-backed blob storage for large packet payloads (>512KB).
Supports presigned URLs for secure, time-limited access.

Usage:
    blob_store = BlobStore()

    # Store large content
    blob_id = await blob_store.store(large_content)

    # Retrieve content
    content = await blob_store.retrieve(blob_id)

    # Get presigned URL for direct download
    url = blob_store.get_presigned_url(blob_id, expires_in=3600)

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Blob Store",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T06:18:10Z",
    "updated_at": "2026-01-25T08:58:44Z",
    "layer": "learning",
    "domain": "memory_substrate",
    "module_name": "blob_store",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["S3"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import hashlib
import os
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# =============================================================================
# Configuration
# =============================================================================

# Blob offload threshold (512KB default, per memory_spec_v3.0.yaml)
BLOB_THRESHOLD_BYTES = int(os.getenv("BLOB_THRESHOLD_BYTES", str(512 * 1024)))

# S3 Configuration
S3_BUCKET = os.getenv("S3_BLOB_BUCKET", "l9-blobs")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
S3_PREFIX = os.getenv("S3_BLOB_PREFIX", "packets")

# Presigned URL default expiry (1 hour)
PRESIGNED_URL_EXPIRY = int(os.getenv("PRESIGNED_URL_EXPIRY", "3600"))


# =============================================================================
# Blob Store Interface
# =============================================================================


@dataclass
class BlobMetadata:
    """Metadata for a stored blob."""

    blob_id: str
    content_hash: str
    size_bytes: int
    content_type: str
    s3_key: str
    bucket: str


@dataclass
class BlobStore:
    """
    S3-backed blob storage for large content.

    Automatically offloads content exceeding BLOB_THRESHOLD_BYTES to S3,
    storing only a reference (blob_id) in the packet envelope.

    Features:
    - Content-addressed storage (SHA-256 hash as blob_id)
    - Deduplication (same content = same blob_id)
    - Presigned URLs for secure, time-limited access
    - Async operations for non-blocking I/O
    """

    bucket: str = field(default_factory=lambda: S3_BUCKET)
    region: str = field(default_factory=lambda: S3_REGION)
    prefix: str = field(default_factory=lambda: S3_PREFIX)
    threshold_bytes: int = field(default_factory=lambda: BLOB_THRESHOLD_BYTES)

    _client: Any = field(default=None, init=False, repr=False)
    _initialized: bool = field(default=False, init=False, repr=False)

    def _get_client(self) -> Any:
        """Lazy initialization of S3 client."""
        if self._client is None:
            try:
                import boto3

                self._client = boto3.client("s3", region_name=self.region)
                self._initialized = True
                logger.info(
                    "blob_store_initialized",
                    bucket=self.bucket,
                    region=self.region,
                    threshold_kb=self.threshold_bytes // 1024,
                )
            except ImportError:
                logger.error("boto3 not installed - blob store unavailable")
                raise RuntimeError("boto3 required for S3 blob storage")
        return self._client

    def _compute_blob_id(self, content: bytes) -> str:
        """Compute content-addressed blob ID (SHA-256 hash)."""
        return hashlib.sha256(content).hexdigest()

    def _get_s3_key(self, blob_id: str) -> str:
        """Generate S3 key for a blob."""
        # Use first 4 chars as partition prefix for better S3 performance
        partition = blob_id[:4]
        return f"{self.prefix}/{partition}/{blob_id}"

    def should_offload(self, content: str | bytes) -> bool:
        """Check if content should be offloaded to blob storage."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        return len(content) > self.threshold_bytes

    async def store(
        self,
        content: str | bytes,
        content_type: str = "application/octet-stream",
    ) -> BlobMetadata:
        """
        Store content in S3 blob storage.

        Args:
            content: Content to store (str or bytes)
            content_type: MIME type of content

        Returns:
            BlobMetadata with blob_id and storage details

        Raises:
            RuntimeError: If S3 upload fails
        """
        if isinstance(content, str):
            content = content.encode("utf-8")

        blob_id = self._compute_blob_id(content)
        s3_key = self._get_s3_key(blob_id)

        client = self._get_client()

        try:
            # Check if blob already exists (deduplication)
            try:
                client.head_object(Bucket=self.bucket, Key=s3_key)
                logger.debug(
                    "blob_already_exists",
                    blob_id=blob_id,
                    size_bytes=len(content),
                )
                return BlobMetadata(
                    blob_id=blob_id,
                    content_hash=blob_id,
                    size_bytes=len(content),
                    content_type=content_type,
                    s3_key=s3_key,
                    bucket=self.bucket,
                )
            except client.exceptions.ClientError as e:
                if e.response["Error"]["Code"] != "404":
                    raise

            # Upload to S3
            client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=content,
                ContentType=content_type,
                Metadata={
                    "blob_id": blob_id,
                    "content_hash": blob_id,
                },
            )

            logger.info(
                "blob_stored",
                blob_id=blob_id,
                size_bytes=len(content),
                s3_key=s3_key,
            )

            return BlobMetadata(
                blob_id=blob_id,
                content_hash=blob_id,
                size_bytes=len(content),
                content_type=content_type,
                s3_key=s3_key,
                bucket=self.bucket,
            )

        except Exception as e:
            logger.error(
                "blob_store_failed",
                blob_id=blob_id,
                error=str(e),
            )
            raise RuntimeError(f"Failed to store blob: {e}") from e

    async def retrieve(self, blob_id: str) -> bytes | None:
        """
        Retrieve content from S3 blob storage.

        Args:
            blob_id: Blob identifier (SHA-256 hash)

        Returns:
            Content bytes or None if not found
        """
        s3_key = self._get_s3_key(blob_id)
        client = self._get_client()

        try:
            response = client.get_object(Bucket=self.bucket, Key=s3_key)
            content = response["Body"].read()

            logger.debug(
                "blob_retrieved",
                blob_id=blob_id,
                size_bytes=len(content),
            )

            return content

        except client.exceptions.NoSuchKey:
            logger.warning("blob_not_found", blob_id=blob_id)
            return None
        except Exception as e:
            logger.error(
                "blob_retrieve_failed",
                blob_id=blob_id,
                error=str(e),
            )
            raise

    def get_presigned_url(
        self,
        blob_id: str,
        expires_in: int = PRESIGNED_URL_EXPIRY,
    ) -> str:
        """
        Generate a presigned URL for direct blob download.

        Args:
            blob_id: Blob identifier
            expires_in: URL expiry time in seconds (default: 1 hour)

        Returns:
            Presigned URL string
        """
        s3_key = self._get_s3_key(blob_id)
        client = self._get_client()

        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": s3_key},
            ExpiresIn=expires_in,
        )

        logger.debug(
            "presigned_url_generated",
            blob_id=blob_id,
            expires_in=expires_in,
        )

        return url

    def get_presigned_upload_url(
        self,
        blob_id: str,
        content_type: str = "application/octet-stream",
        expires_in: int = PRESIGNED_URL_EXPIRY,
    ) -> str:
        """
        Generate a presigned URL for direct blob upload.

        Args:
            blob_id: Blob identifier (caller must compute)
            content_type: MIME type of content
            expires_in: URL expiry time in seconds

        Returns:
            Presigned URL for PUT upload
        """
        s3_key = self._get_s3_key(blob_id)
        client = self._get_client()

        url = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )

        logger.debug(
            "presigned_upload_url_generated",
            blob_id=blob_id,
            expires_in=expires_in,
        )

        return url

    async def delete(self, blob_id: str) -> bool:
        """
        Delete a blob from S3.

        Args:
            blob_id: Blob identifier

        Returns:
            True if deleted, False if not found
        """
        s3_key = self._get_s3_key(blob_id)
        client = self._get_client()

        try:
            client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info("blob_deleted", blob_id=blob_id)
            return True
        except client.exceptions.NoSuchKey:
            logger.warning("blob_delete_not_found", blob_id=blob_id)
            return False
        except Exception as e:
            logger.error(
                "blob_delete_failed",
                blob_id=blob_id,
                error=str(e),
            )
            raise

    async def exists(self, blob_id: str) -> bool:
        """Check if a blob exists in S3."""
        s3_key = self._get_s3_key(blob_id)
        client = self._get_client()

        try:
            client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise


# =============================================================================
# Factory Function
# =============================================================================


_blob_store_instance: BlobStore | None = None


def get_blob_store() -> BlobStore:
    """
    Get singleton BlobStore instance.

    Returns:
        BlobStore instance configured from environment
    """
    global _blob_store_instance
    if _blob_store_instance is None:
        _blob_store_instance = BlobStore()
    return _blob_store_instance


# =============================================================================
# Helper Functions
# =============================================================================


def compute_content_hash(content: str | bytes) -> str:
    """
    Compute SHA-256 hash of content.

    Use this to pre-compute blob_id before upload for deduplication checks.
    """
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def build_blob_reference(metadata: BlobMetadata) -> dict[str, Any]:
    """
    Build a blob reference dict for packet payload.

    This reference replaces inline content in the packet envelope.
    """
    return {
        "blob_ref": f"s3://{metadata.bucket}/{metadata.s3_key}",
        "blob_id": metadata.blob_id,
        "blob_size": metadata.size_bytes,
        "content_type": metadata.content_type,
    }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-018",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "dataclass",
        "debugging",
        "learning",
        "logging",
        "memory-substrate",
        "security",
        "streaming",
    ],
    "keywords": [
        "await",
        "blob",
        "build",
        "compute",
        "delete",
        "exists",
        "hash",
        "large",
    ],
    "business_value": "Provides S3-backed blob storage for large packet payloads (>512KB). Supports presigned URLs for secure, time-limited access. blob_store = BlobStore() # Store large content blob_id = await blob_store.s",
    "last_modified": "2026-01-25T08:58:44Z",
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
