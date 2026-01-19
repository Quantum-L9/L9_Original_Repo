"""
Mac Agent Configuration
Loads settings from config.yaml and environment variables.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Config",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "integration",
    "domain": "mac_integration",
    "module_name": "config",
    "type": "config",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["mac_agent.executor", "mac_agent.runner"],
    },
}
# ============================================================================

import os
import yaml
from pathlib import Path
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class MacAgentConfig:
    """Configuration for Mac Agent V2."""

    def __init__(self):
        self.l9_base_url = os.getenv("L9_BASE_URL", "http://127.0.0.1:8000")
        self.l9_api_key = os.getenv("L9_API_KEY", "")
        self.playwright_headless = (
            os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"
        )

        # Load from config.yaml if it exists
        config_path = Path(__file__).parent / "config.yaml"
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config_data = yaml.safe_load(f) or {}

                # Override with config.yaml values if present
                if "vps_url" in config_data:
                    self.l9_base_url = config_data["vps_url"]
                if "browser_headless" in config_data:
                    self.playwright_headless = config_data["browser_headless"]
                if "screenshot_dir" in config_data:
                    self.screenshot_dir = os.path.expanduser(
                        config_data["screenshot_dir"]
                    )
                else:
                    self.screenshot_dir = os.path.expanduser("~/Desktop/l9_screenshots")

                # Default browser
                self.default_browser = config_data.get("default_browser", "chromium")

            except Exception as e:
                logger.warning(f"Failed to load config.yaml: {e}")
                self.screenshot_dir = os.path.expanduser("~/Desktop/l9_screenshots")
                self.default_browser = "chromium"
        else:
            self.screenshot_dir = os.path.expanduser("~/Desktop/l9_screenshots")
            self.default_browser = "chromium"

        # Ensure screenshot directory exists
        os.makedirs(self.screenshot_dir, exist_ok=True)

        logger.info(
            f"Mac Agent Config: base_url={self.l9_base_url}, headless={self.playwright_headless}, screenshot_dir={self.screenshot_dir}"
        )


# Singleton instance
_config: Optional[MacAgentConfig] = None


def get_config() -> MacAgentConfig:
    """Get or create config singleton."""
    global _config
    if _config is None:
        _config = MacAgentConfig()
    return _config


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MAC-INTE-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "config",
        "filesystem",
        "integration",
        "logging",
        "mac-integration",
    ],
    "keywords": ["agent", "mac"],
    "business_value": "Implements MacAgentConfig for config functionality",
    "last_modified": "2026-01-07T13:35:57Z",
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
