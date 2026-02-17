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
from .session import SessionManager

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
        self.session_manager = SessionManager(
            self.browser_config.get("profile_dir", "./profiles/default")
        )
        self._context_manager: Any = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def _setup_themed_profile(self, profile_path: str) -> None:
        """Pre-create a Firefox profile with custom theme and prefs."""
        profile = Path(profile_path)

        # Create chrome directory and copy userChrome.css
        chrome_dir = profile / "chrome"
        chrome_dir.mkdir(parents=True, exist_ok=True)

        theme_src = Path(__file__).parent / "theme" / "userChrome.css"
        if theme_src.exists():
            import shutil
            shutil.copy2(theme_src, chrome_dir / "userChrome.css")

        # Write user.js with required prefs
        user_js = profile / "user.js"
        with open(user_js, "w") as f:
            f.write('// Agentic Browser custom prefs\n')
            f.write('user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);\n')
            f.write('user_pref("browser.uidensity", 1);\n')  # Compact density
            f.write('user_pref("browser.tabs.drawInTitlebar", true);\n')
            f.write('user_pref("browser.chrome.site_icons", true);\n')

        logger.info("Set up themed profile at %s", profile_path)

    def _inject_theme(self) -> None:
        """Copy custom userChrome.css into the browser profile for theming."""
        theme_src = Path(__file__).parent / "theme" / "userChrome.css"
        if not theme_src.exists():
            return

        # Find active playwright profile
        import glob
        profiles = sorted(
            glob.glob("/tmp/playwright_firefoxdev_profile-*"),
            key=lambda p: Path(p).stat().st_mtime,
            reverse=True,
        )
        if not profiles:
            return

        chrome_dir = Path(profiles[0]) / "chrome"
        chrome_dir.mkdir(exist_ok=True)
        dest = chrome_dir / "userChrome.css"

        import shutil
        shutil.copy2(theme_src, dest)

        # Enable userChrome.css loading via user.js
        user_js = Path(profiles[0]) / "user.js"
        prefs = 'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);\n'
        if not user_js.exists() or "legacyUserProfileCustomizations" not in user_js.read_text():
            with open(user_js, "a") as f:
                f.write(prefs)

        logger.info("Injected custom theme into %s", profiles[0])

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

        # Get locale from fingerprint config
        fp_config = self.config.get("fingerprint", {})
        locale = fp_config.get("locale", "en-US")

        # Launch via camoufox async context manager
        # Let camoufox auto-generate fingerprints (screen, navigator, etc.)
        # We pass locale and geoip for timezone/geo consistency
        self._context_manager = AsyncCamoufox(
            headless=headless,
            locale=locale,
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

        # Load saved cookies if available
        try:
            context = self._page.context
            loaded = await self.session_manager.load_cookies(context)
            if loaded > 0:
                logger.info("Restored %d saved cookies", loaded)
        except Exception as e:
            logger.debug("Could not load saved cookies: %s", e)

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
        # Save cookies before closing
        if self._page is not None:
            try:
                context = self._page.context
                await self.session_manager.save_cookies(context)
            except Exception as e:
                logger.debug("Could not save cookies on close: %s", e)

        if self._context_manager is not None:
            try:
                await self._context_manager.__aexit__(None, None, None)
            except Exception as e:
                logger.warning("Error closing browser: %s", e)
            self._context_manager = None
            self._browser = None
            self._page = None
            logger.info("Browser closed")
