"""
Agent UI Control configuration.

Env vars ALWAYS win. config.yaml supplies non-sensitive defaults only.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:  # pragma: no cover - structlog optional at import time
    import logging

    logger = logging.getLogger(__name__)


class AgentUIControlConfig:
    """Configuration for Agent UI Control (local-first)."""

    def __init__(self) -> None:
        self.mode = os.getenv("L9_AGENT_UI_MODE", "local").strip().lower() or "local"
        self.l9_base_url = os.getenv("L9_BASE_URL", "http://127.0.0.1:8000")
        self.l9_api_key = os.getenv("L9_API_KEY", "")
        self.playwright_headless = (
            os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"
        )
        self.poll_interval = float(os.getenv("L9_AGENT_POLL_INTERVAL", "3"))
        self.enabled = os.getenv("L9_AGENT_UI_ENABLED", "true").lower() != "false"

        self.screenshot_dir = os.path.expanduser("~/Desktop/l9_screenshots")
        self.default_browser = "chromium"
        self.gui_safety = True

        config_path = Path(__file__).parent / "config.yaml"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config_data = yaml.safe_load(f) or {}

                if "mode" in config_data and not os.getenv("L9_AGENT_UI_MODE"):
                    self.mode = str(config_data["mode"]).strip().lower() or "local"
                if "vps_url" in config_data and not os.getenv("L9_BASE_URL"):
                    self.l9_base_url = config_data["vps_url"]
                if "browser_headless" in config_data and not os.getenv(
                    "PLAYWRIGHT_HEADLESS"
                ):
                    self.playwright_headless = bool(config_data["browser_headless"])
                if "poll_interval" in config_data and not os.getenv(
                    "L9_AGENT_POLL_INTERVAL"
                ):
                    self.poll_interval = float(config_data["poll_interval"])
                if "screenshot_dir" in config_data:
                    self.screenshot_dir = os.path.expanduser(
                        str(config_data["screenshot_dir"])
                    )
                self.default_browser = config_data.get(
                    "default_browser", self.default_browser
                )
                self.gui_safety = bool(config_data.get("gui_safety", True))
            except Exception as exc:  # noqa: BLE001 — config load must not crash runner
                logger.warning("Failed to load config.yaml: %s", exc)

        os.makedirs(self.screenshot_dir, exist_ok=True)
        logger.info(
            "Agent UI Control config: mode=%s base_url=%s headless=%s screenshot_dir=%s",
            self.mode,
            self.l9_base_url,
            self.playwright_headless,
            self.screenshot_dir,
        )


_config: AgentUIControlConfig | None = None


def get_config() -> AgentUIControlConfig:
    """Get or create config singleton."""
    global _config
    if _config is None:
        _config = AgentUIControlConfig()
    return _config
