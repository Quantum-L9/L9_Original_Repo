# ══════════════════════════════════════════════════════════════════════════════
# Generated from Module-Spec v2.6
# module_id: email.adapter
# enforced_acceptance: ["valid_email_processed", "idempotent_replay_cached", "email_parsed_correctly", "aios_response_forwarded", "packet_written_on_success", ... (8 total)]
# ══════════════════════════════════════════════════════════════════════════════
# DORA META BLOCK — DO NOT EDIT MANUALLY (CI-owned)
# ══════════════════════════════════════════════════════════════════════════════
# __meta__ = {
#     "template_version": "2.6.0",
#     "spec_hash": "SPEC-62d9295fc71f",
#     "created_at": "2025-12-18T06:24:54.974886+00:00",
#     "created_by": "module_pipeline",
#     "last_updated_at": "2025-12-18T06:24:54.974886+00:00",
#     "last_updated_by": "module_pipeline",
#     "module_id": "email.adapter",
#     "file": "clients/email_adapter_client.py",
# }
# ══════════════════════════════════════════════════════════════════════════════

"""
Email Adapter Client
────────────────────
External API client for Email Adapter

Auto-generated from Module-Spec v2.6.0
"""

import structlog
import httpx
from typing import Optional
from dataclasses import dataclass
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


@dataclass
class EmailAdapterClientConfig:
    """Client configuration."""

    base_url: str
    api_key: Optional[str] = None
    timeout: float = 30.0
    retries: int = 3


class EmailAdapterClient:
    """
    External API client for Email Adapter.
    Uses httpx for async HTTP operations.
    """

    def __init__(self, config: EmailAdapterClientConfig):
        self.config = config
        self.logger = structlog.get_logger(__name__)
        self._client: Optional[httpx.AsyncClient] = None

    @must_stay_async("async context manager protocol")
    async def __aenter__(self) -> "EmailAdapterClient":
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            headers=self._get_headers(),
        )
        return self

    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> dict:
        """Make HTTP request with retry logic."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        last_error = None
        for attempt in range(self.config.retries):
            try:
                response = await self._client.request(
                    method=method,
                    url=endpoint,
                    json=data,
                    timeout=timeout or self.config.timeout,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                last_error = e
                self.logger.warning(
                    "request_failed", attempt=attempt + 1, status=e.response.status_code
                )
                if e.response.status_code < 500:
                    raise
            except httpx.RequestError as e:
                last_error = e
                self.logger.warning("request_error", attempt=attempt + 1, error=str(e))

        raise last_error or RuntimeError("Request failed after retries")

    # ──────────────────────────────────────────────────────────────────────────
    # API METHODS (from spec.interfaces.outbound)
    # ──────────────────────────────────────────────────────────────────────────

    async def aios_runtime_call(self, data: dict) -> dict:
        """
        Call aios_runtime_call endpoint.

        Endpoint: /chat
        Method: POST
        Timeout: 30s
        Retry: False
        """
        return await self._request("POST", "/chat", data, timeout=30)

    async def memory_service_call(self, data: dict) -> dict:
        """
        Call memory_service_call endpoint.

        Endpoint: /memory/ingest
        Method: POST
        Timeout: 30s
        Retry: False
        """
        return await self._request("POST", "/memory/ingest", data, timeout=30)

    async def gmail_users_messages_get(self, data: dict) -> dict:
        """
        Call gmail_users_messages_get endpoint.

        Endpoint: https://api.gmail.com/...
        Method: POST
        Timeout: 10s
        Retry: True
        """
        return await self._request(
            "POST", "https://api.gmail.com/...", data, timeout=10
        )

    async def gmail_users_messages_send(self, data: dict) -> dict:
        """
        Call gmail_users_messages_send endpoint.

        Endpoint: https://api.gmail.com/...
        Method: POST
        Timeout: 10s
        Retry: True
        """
        return await self._request(
            "POST", "https://api.gmail.com/...", data, timeout=10
        )
