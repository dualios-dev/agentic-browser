"""Browser actions: click, type, scroll, extract, navigate.

High-level actions that combine Playwright automation with
human behavior simulation for natural-looking interactions.
"""

from __future__ import annotations

import logging
from typing import Any

from playwright.async_api import Page

from .humanize import (
    human_click,
    human_move_mouse,
    human_scroll,
    human_type,
    random_pause,
)
from .sanitizer import sanitize_html

logger = logging.getLogger(__name__)


class BrowserActions:
    """High-level browser actions with human simulation.

    All actions incorporate humanized behavior (bezier mouse movements,
    realistic typing delays, natural scrolling) to avoid detection.
    """

    def __init__(self, page: Page, config: dict[str, Any] | None = None) -> None:
        self.page = page
        self.config = config or {}
        self.humanize_cfg = self.config.get("humanize", {})
        self.sanitizer_cfg = self.config.get("sanitizer", {})

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> str:
        """Navigate to a URL and return sanitized page content.

        Args:
            url: URL to navigate to.
            wait_until: Navigation wait condition.

        Returns:
            Sanitized markdown of the page content.
        """
        logger.info("Navigating to %s", url)
        try:
            await self.page.goto(url, wait_until="networkidle", timeout=15000)
        except Exception:
            # Fallback to domcontentloaded if networkidle times out
            try:
                await self.page.goto(url, wait_until=wait_until, timeout=15000)
            except Exception:
                pass  # Page may still be usable
        await random_pause(
            self.humanize_cfg.get("action_pause", [200, 800])[0],
            self.humanize_cfg.get("action_pause", [200, 800])[1],
        )
        # Extra wait for JS-heavy sites
        await self.page.wait_for_timeout(1500)
        return await self.extract_content()

    async def click_element(self, selector: str) -> None:
        """Click an element with human-like mouse movement.

        Args:
            selector: CSS selector for the element to click.
        """
        logger.debug("Clicking element: %s", selector)
        element = await self.page.wait_for_selector(selector)
        if element is None:
            raise ValueError(f"Element not found: {selector}")

        box = await element.bounding_box()
        if box is None:
            # Fallback to direct click if no bounding box
            await element.click()
            return

        # Click at a random point within the element (not dead center)
        import random
        x = box["x"] + box["width"] * random.uniform(0.25, 0.75)
        y = box["y"] + box["height"] * random.uniform(0.25, 0.75)

        speed = self.humanize_cfg.get("mouse_speed", [80, 250])
        await human_click(self.page, x, y, tuple(speed))
        await random_pause()

    async def type_text(self, selector: str, text: str, clear: bool = True) -> None:
        """Type text into an input field with realistic delays.

        Args:
            selector: CSS selector for the input element.
            text: Text to type.
            clear: Whether to clear existing content first.
        """
        logger.debug("Typing into: %s", selector)
        # Try the selector, then fallback alternatives for common inputs
        try:
            element = await self.page.wait_for_selector(selector, timeout=5000)
        except Exception:
            # Fallback: try common alternatives (Google changed input→textarea)
            fallbacks = [
                "textarea[name=q]", "input[name=q]", "textarea[title='Search']",
                "input[title='Search']", "[role='combobox']", "[aria-label='Search']",
                "#twotabsearchtextbox", "input[name='field-keywords']",
                "#search-input", "input[type='search']", "input[placeholder*='Search']",
                "input[aria-label*='Search']", "textarea[aria-label*='Search']",
            ]
            element = None
            for fb in fallbacks:
                try:
                    element = await self.page.wait_for_selector(fb, timeout=3000)
                    if element:
                        selector = fb
                        logger.info("Fallback selector matched: %s", fb)
                        break
                except Exception:
                    continue
            if element is None:
                raise ValueError(f"Element not found: {selector} (tried fallbacks too)")

        # Click the field first
        await self.click_element(selector)

        if clear:
            await self.page.keyboard.press("Control+A")
            await random_pause(50, 150)
            await self.page.keyboard.press("Backspace")
            await random_pause(100, 200)

        typing_cfg = self.humanize_cfg.get("typing_delay", {})
        await human_type(
            self.page,
            text,
            mean_delay=typing_cfg.get("mean", 75),
            stddev=typing_cfg.get("stddev", 25),
        )
        await random_pause()

    async def scroll_page(
        self, direction: str = "down", distance: int = 500
    ) -> None:
        """Scroll the page with natural behavior.

        Args:
            direction: "down" or "up".
            distance: Total scroll distance in pixels.
        """
        logger.debug("Scrolling %s %dpx", direction, distance)
        scroll_cfg = self.humanize_cfg.get("scroll", {})
        await human_scroll(
            self.page,
            direction=direction,
            distance=distance,
            step_mean=scroll_cfg.get("step_mean", 120),
            step_stddev=scroll_cfg.get("step_stddev", 40),
            delay_mean=scroll_cfg.get("delay_mean", 50),
            delay_stddev=scroll_cfg.get("delay_stddev", 20),
        )

    async def extract_content(self) -> str:
        """Extract and sanitize the current page content.

        Returns:
            Clean markdown representation of the page.
        """
        html = await self.page.content()
        return sanitize_html(html, config=self.sanitizer_cfg)

    async def screenshot(self, path: str | None = None, full_page: bool = False) -> bytes:
        """Take a screenshot of the current page.

        Args:
            path: Optional file path to save the screenshot.
            full_page: Whether to capture the full scrollable page.

        Returns:
            Screenshot as PNG bytes.
        """
        logger.debug("Taking screenshot (full_page=%s)", full_page)
        return await self.page.screenshot(path=path, full_page=full_page)

    async def login_instagram(self, username: str, password: str) -> bool:
        """Log into Instagram.
        
        Args:
            username: Instagram username.
            password: Instagram password.
            
        Returns:
            True if login successful.
        """
        logger.info("Logging into Instagram as %s", username)
        await self.page.goto("https://www.instagram.com/accounts/login/", wait_until="networkidle")
        await self.page.wait_for_timeout(2000)
        
        # Type username
        try:
            username_input = await self.page.wait_for_selector('input[name="username"]', timeout=10000)
            await username_input.click()
            await username_input.fill(username)
            await random_pause(300, 600)
            
            # Type password
            password_input = await self.page.wait_for_selector('input[name="password"]', timeout=5000)
            await password_input.click()
            await password_input.fill(password)
            await random_pause(300, 600)
            
            # Click login button
            login_btn = await self.page.wait_for_selector('button[type="submit"]', timeout=5000)
            await login_btn.click()
            
            # Wait for navigation
            await self.page.wait_for_timeout(5000)
            
            # Check if logged in
            current_url = self.page.url
            if "login" not in current_url.lower():
                logger.info("Instagram login successful")
                # Dismiss "Save login info" or "Turn on notifications" popups
                for btn_text in ["Not Now", "Not now"]:
                    try:
                        btn = await self.page.wait_for_selector(f'button:has-text("{btn_text}")', timeout=3000)
                        if btn:
                            await btn.click()
                            await self.page.wait_for_timeout(1000)
                    except Exception:
                        pass
                return True
            else:
                logger.error("Instagram login failed — still on login page")
                return False
        except Exception as e:
            logger.error("Instagram login failed: %s", e)
            return False

    async def wait_for(self, selector: str, timeout: int = 10000) -> None:
        """Wait for an element to appear.

        Args:
            selector: CSS selector to wait for.
            timeout: Maximum wait time in ms.
        """
        await self.page.wait_for_selector(selector, timeout=timeout)

    async def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript in the page context.

        Args:
            expression: JavaScript expression to evaluate.

        Returns:
            Result of the evaluation.
        """
        return await self.page.evaluate(expression)

    async def get_url(self) -> str:
        """Get the current page URL."""
        return self.page.url

    async def get_title(self) -> str:
        """Get the current page title."""
        return await self.page.title()
