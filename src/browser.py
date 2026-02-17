"""Stealth browser launcher using camoufox + Playwright.

Launches an undetectable Firefox-based browser with fingerprint
spoofing, proxy routing, and anti-detection features.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from camoufox.async_api import AsyncCamoufox
from playwright.async_api import Browser, BrowserContext, Page

from .fingerprint import Fingerprint, generate_fingerprint, fingerprint_hash
from .proxy_router import ProxyRouter

logger = logging.getLogger(__name__)


class StealthBrowser:
    """Manages a stealth browser instance with anti-detection features.

    Uses camoufox (a Firefox fork) with Playwright for automation,
    combined with fingerprint spoofing and proxy routing.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the stealth browser.

        Args:
            config: Full config dict (from config.yaml).
        """
        self.config = config
        self.browser_config = config.get("browser", {})
        self.fingerprint: Fingerprint | None = None
        self.proxy_router: ProxyRouter | None = None
        self._context_manager: Any = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def launch(self) -> Page:
        """Launch the stealth browser and return the main page.

        Returns:
            Playwright Page instance ready for automation.
        """
        # Generate fingerprint
        self.fingerprint = generate_fingerprint(self.config.get("fingerprint", {}))
        fp_id = fingerprint_hash(self.fingerprint)
        logger.info("Launching stealth browser with fingerprint %s", fp_id)

        # Setup proxy router
        proxy_config = self.config.get("proxy", {})
        self.proxy_router = ProxyRouter.from_config(proxy_config)

        # Ensure profile directory exists
        profile_dir = self.browser_config.get("profile_dir", "./profiles/default")
        Path(profile_dir).mkdir(parents=True, exist_ok=True)

        # Build camoufox config
        headless = self.browser_config.get("headless", True)
        viewport = self.browser_config.get("viewport", {"width": 1920, "height": 1080})

        # Get default proxy
        default_proxy = proxy_config.get("default")
        proxy_setting = {"server": default_proxy} if default_proxy else None

        # Launch via camoufox async context manager
        camoufox_config = self.fingerprint.to_camoufox_config()

        self._context_manager = AsyncCamoufox(
            headless=headless,
            config=camoufox_config,
            proxy=proxy_setting,
            geoip=True,
        )
        self._browser = await self._context_manager.__aenter__()

        # Create page
        self._page = await self._browser.new_page()
        await self._page.set_viewport_size(viewport)

        # Set default timeout
        timeout = self.browser_config.get("timeout", 30000)
        self._page.set_default_timeout(timeout)
        self._page.set_default_navigation_timeout(timeout)

        logger.info("Stealth browser launched successfully (headless=%s)", headless)
        return self._page

    @property
    def page(self) -> Page:
        """Get the current page."""
        if self._page is None:
            raise RuntimeError("Browser not launched. Call launch() first.")
        return self._page

    async def new_page(self) -> Page:
        """Create a new page/tab in the browser.

        Returns:
            New Playwright Page instance.
        """
        if self._browser is None:
            raise RuntimeError("Browser not launched. Call launch() first.")
        page = await self._browser.new_page()
        viewport = self.browser_config.get("viewport", {"width": 1920, "height": 1080})
        await page.set_viewport_size(viewport)
        return page

    async def close(self) -> None:
        """Close the browser and clean up resources."""
        if self._context_manager is not None:
            try:
                await self._context_manager.__aexit__(None, None, None)
            except Exception as e:
                logger.warning("Error closing browser: %s", e)
            self._context_manager = None
            self._browser = None
            self._page = None
            logger.info("Browser closed")
