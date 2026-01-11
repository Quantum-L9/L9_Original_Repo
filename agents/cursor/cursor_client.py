"""
L9 Cursor Client
HTTP client wrapper for Cursor remote API.
Simple POST wrapper with timeout and error handling.
"""

import structlog
from typing import Dict, Any, Optional

logger = structlog.get_logger(__name__)


class CursorClient:
    """Client for Cursor remote API."""

    def __init__(self, host: str = "127.0.0.1", port: int = 3000, timeout: int = 30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"

    def _request(
        self, endpoint: str, method: str = "POST", data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Cursor API."""
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "POST":
                response = requests.post(url, json=data, timeout=self.timeout)
            elif method == "GET":
                response = requests.get(url, timeout=self.timeout)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}

            response.raise_for_status()

            return {
                "success": True,
                "response": response.json() if response.content else {},
                "status_code": response.status_code,
            }

        except requests.exceptions.Timeout:
            logger.error(f"Cursor API timeout: {url}")
            return {"success": False, "error": "Request timeout"}
        except requests.exceptions.ConnectionError:
            logger.error(f"Cursor API connection error: {url}")
            return {"success": False, "error": "Connection failed"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Cursor API error: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"success": False, "error": str(e)}

    def send_code(self, code: str) -> Dict[str, Any]:
        """
        Send code to Cursor.
        Returns: {success: bool, response: Dict, error: str}
        """
        return self._request("/api/code", data={"code": code})

    def send_command(self, command: str) -> Dict[str, Any]:
        """
        Send command to Cursor.
        Returns: {success: bool, response: Dict, error: str}
        """
        return self._request("/api/command", data={"command": command})

    def health_check(self) -> Dict[str, Any]:
        """
        Check Cursor API health.
        Returns: {success: bool, response: Dict}
        """
        return self._request("/health", method="GET")
