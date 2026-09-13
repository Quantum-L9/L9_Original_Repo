"""
Mac Agent Configuration
Loads settings from config.yaml and environment variables.
"""


import os
from pathlib import Path

import structlog
import yaml

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
                with open(config_path) as f:
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
_config: MacAgentConfig | None = None


def get_config() -> MacAgentConfig:
    """Get or create config singleton."""
    global _config
    if _config is None:
        _config = MacAgentConfig()
    return _config


# Runtime execution trace - updated automatically on every execution
