"""Main AI ↔ Browser bridge interface.

Orchestrates all components: stealth browser, actions, sanitizer,
guardrail, and proxy router into a single unified interface
for AI agent control.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .actions import BrowserActions
from .browser import StealthBrowser
from .guardrail import ScanResult, ThreatLevel, scan_content, scan_with_llm
from .proxy_router import ProxyRouter

logger = logging.getLogger(__name__)


@dataclass
class BrowseResult:
    """Result of a browse operation."""
    url: str
    title: str
    content: str  # Sanitized markdown
    guardrail: ScanResult
    success: bool
    error: str | None = None


class AgentBridge:
    """Main interface between AI agents and the browser.

    Provides a high-level API for browsing with built-in safety:
    - Stealth browser with fingerprint spoofing
    - Human-like behavior simulation
    - HTML → clean Markdown sanitization
    - Prompt injection guardrail
    - Domain-based proxy routing

    Usage:
        bridge = AgentBridge.from_config("config.yaml")
        async with bridge:
            result = await bridge.browse("https://example.com")
            print(result.content)
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._browser: StealthBrowser | None = None
        self._actions: BrowserActions | None = None
        self._setup_logging()

    @classmethod
    def from_config(cls, config_path: str = "config.yaml") -> AgentBridge:
        """Create an AgentBridge from a YAML config file.

        Args:
            config_path: Path to config.yaml.

        Returns:
            Configured AgentBridge instance.
        """
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                config = yaml.safe_load(f) or {}
        else:
            logger.warning("Config file %s not found, using defaults", config_path)
            config = {}
        return cls(config)

    def _setup_logging(self) -> None:
        """Configure logging based on config."""
        log_cfg = self.config.get("logging", {})
        level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)

        root_logger = logging.getLogger("src")
        root_logger.setLevel(level)

        # Console handler
        if log_cfg.get("console", True) and not root_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
            )
            root_logger.addHandler(handler)

        # File handler
        log_file = log_cfg.get("file")
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(log_file)
            fh.setFormatter(
                logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
            )
            root_logger.addHandler(fh)

    async def start(self) -> None:
        """Launch the stealth browser."""
        self._browser = StealthBrowser(self.config)
        page = await self._browser.launch()
        self._actions = BrowserActions(page, self.config)
        logger.info("AgentBridge started")

    async def stop(self) -> None:
        """Close the browser and clean up."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._actions = None
            logger.info("AgentBridge stopped")

    async def __aenter__(self) -> AgentBridge:
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.stop()

    @property
    def actions(self) -> BrowserActions:
        if self._actions is None:
            raise RuntimeError("Bridge not started. Call start() first.")
        return self._actions

    async def browse(self, url: str) -> BrowseResult:
        """Navigate to a URL and return safe, sanitized content.

        Full pipeline:
        1. Route through appropriate proxy
        2. Navigate with stealth browser
        3. Extract and sanitize HTML → Markdown
        4. Scan for prompt injection
        5. Return safe content

        Args:
            url: URL to browse.

        Returns:
            BrowseResult with sanitized content and guardrail status.
        """
        try:
            # Navigate and get sanitized content
            content = await self.actions.navigate(url)
            title = await self.actions.get_title()

            # Run guardrail scan
            guardrail_cfg = self.config.get("guardrail", {})
            if guardrail_cfg.get("llm_enabled"):
                scan_result = await scan_with_llm(content, guardrail_cfg)
            else:
                scan_result = scan_content(content, guardrail_cfg)

            if scan_result.level == ThreatLevel.DANGEROUS:
                logger.warning(
                    "Guardrail DANGEROUS for %s: %s", url, scan_result.details
                )

            return BrowseResult(
                url=url,
                title=title,
                content=scan_result.content,
                guardrail=scan_result,
                success=True,
            )

        except Exception as e:
            logger.error("Browse failed for %s: %s", url, e)
            return BrowseResult(
                url=url,
                title="",
                content="",
                guardrail=ScanResult(
                    level=ThreatLevel.SAFE, matches=[], details="", content=""
                ),
                success=False,
                error=str(e),
            )

    async def click(self, selector: str) -> None:
        """Click an element with human-like behavior."""
        await self.actions.click_element(selector)

    async def type_text(self, selector: str, text: str) -> None:
        """Type text into a field with realistic delays."""
        await self.actions.type_text(selector, text)

    async def scroll(self, direction: str = "down", distance: int = 500) -> None:
        """Scroll the page naturally."""
        await self.actions.scroll_page(direction, distance)

    async def screenshot(self, path: str | None = None) -> bytes:
        """Take a screenshot."""
        return await self.actions.screenshot(path)

    async def extract(self) -> str:
        """Extract current page content as sanitized markdown."""
        return await self.actions.extract_content()

    async def get_status(self) -> dict[str, Any]:
        """Get current browser status."""
        if self._browser is None or self._browser._page is None:
            return {"running": False}
        return {
            "running": True,
            "url": self._browser.page.url,
            "title": await self._browser.page.title(),
            "fingerprint": self._browser.fingerprint.__dict__ if self._browser.fingerprint else None,
        }


async def main() -> None:
    """CLI entry point for the agent bridge."""
    import argparse

    parser = argparse.ArgumentParser(description="Agentic Browser Bridge")
    parser.add_argument("url", nargs="?", help="URL to browse")
    parser.add_argument(
        "-c", "--config", default="config.yaml", help="Config file path"
    )
    parser.add_argument(
        "--screenshot", "-s", help="Save screenshot to path"
    )
    args = parser.parse_args()

    bridge = AgentBridge.from_config(args.config)

    async with bridge:
        if args.url:
            result = await bridge.browse(args.url)
            print(f"# {result.title}")
            print(f"URL: {result.url}")
            print(f"Guardrail: {result.guardrail.level.value}")
            if result.guardrail.matches:
                print(f"Warnings: {result.guardrail.details}")
            print("---")
            print(result.content[:5000])

            if args.screenshot:
                await bridge.screenshot(args.screenshot)
                print(f"\nScreenshot saved to {args.screenshot}")
        else:
            print("Agentic Browser started. No URL provided.")
            status = await bridge.get_status()
            print(f"Status: {status}")


if __name__ == "__main__":
    asyncio.run(main())
