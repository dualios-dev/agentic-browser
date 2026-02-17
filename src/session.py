"""Session management: cookie import/export, persistent profiles, and login bypass.

Handles browser session persistence across restarts by saving/loading cookies,
localStorage, and session state. Enables login bypass by importing cookies
from a regular browser session.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages browser session state — cookies, storage, and login sessions."""

    def __init__(self, profile_dir: str = "./profiles/default"):
        self.profile_dir = Path(profile_dir)
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_file = self.profile_dir / "cookies.json"
        self.storage_file = self.profile_dir / "storage.json"

    async def save_cookies(self, context) -> int:
        """Save all cookies from the browser context.

        Args:
            context: Playwright BrowserContext.

        Returns:
            Number of cookies saved.
        """
        cookies = await context.cookies()
        self.cookies_file.write_text(json.dumps(cookies, indent=2))
        logger.info("Saved %d cookies to %s", len(cookies), self.cookies_file)
        return len(cookies)

    async def load_cookies(self, context) -> int:
        """Load saved cookies into the browser context.

        Args:
            context: Playwright BrowserContext.

        Returns:
            Number of cookies loaded.
        """
        if not self.cookies_file.exists():
            logger.debug("No saved cookies found at %s", self.cookies_file)
            return 0

        try:
            cookies = json.loads(self.cookies_file.read_text())
            await context.add_cookies(cookies)
            logger.info("Loaded %d cookies from %s", len(cookies), self.cookies_file)
            return len(cookies)
        except Exception as e:
            logger.error("Failed to load cookies: %s", e)
            return 0

    async def import_cookies_from_file(self, context, filepath: str) -> int:
        """Import cookies from an external JSON file (e.g., exported from browser extension).

        Supports multiple formats:
        - Playwright format: [{"name": ..., "value": ..., "domain": ..., ...}]
        - Netscape/curl format: domain\tTRUE\tpath\tsecure\texpiry\tname\tvalue
        - EditThisCookie format: [{"domain": ..., "name": ..., "value": ..., ...}]

        Args:
            context: Playwright BrowserContext.
            filepath: Path to cookie file.

        Returns:
            Number of cookies imported.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Cookie file not found: {filepath}")

        raw = path.read_text().strip()

        # Try JSON first
        try:
            cookies_raw = json.loads(raw)
            cookies = self._normalize_cookies(cookies_raw)
        except json.JSONDecodeError:
            # Try Netscape format
            cookies = self._parse_netscape_cookies(raw)

        if not cookies:
            raise ValueError("No valid cookies found in file")

        await context.add_cookies(cookies)
        # Also save to our profile
        self.cookies_file.write_text(json.dumps(cookies, indent=2))
        logger.info("Imported %d cookies from %s", len(cookies), filepath)
        return len(cookies)

    async def import_cookies_from_json(self, context, cookies_json: list[dict]) -> int:
        """Import cookies from a JSON array (e.g., from API call).

        Args:
            context: Playwright BrowserContext.
            cookies_json: List of cookie dicts.

        Returns:
            Number of cookies imported.
        """
        cookies = self._normalize_cookies(cookies_json)
        if not cookies:
            raise ValueError("No valid cookies in input")

        await context.add_cookies(cookies)
        self.cookies_file.write_text(json.dumps(cookies, indent=2))
        logger.info("Imported %d cookies via API", len(cookies))
        return len(cookies)

    async def export_cookies(self, context, domain: str | None = None) -> list[dict]:
        """Export current cookies, optionally filtered by domain.

        Args:
            context: Playwright BrowserContext.
            domain: Optional domain filter.

        Returns:
            List of cookie dicts.
        """
        cookies = await context.cookies()
        if domain:
            cookies = [c for c in cookies if domain in c.get("domain", "")]
        return cookies

    async def save_storage(self, page) -> dict:
        """Save localStorage and sessionStorage.

        Args:
            page: Playwright Page.

        Returns:
            Dict with localStorage and sessionStorage.
        """
        storage = await page.evaluate("""() => {
            const ls = {};
            const ss = {};
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                ls[key] = localStorage.getItem(key);
            }
            for (let i = 0; i < sessionStorage.length; i++) {
                const key = sessionStorage.key(i);
                ss[key] = sessionStorage.getItem(key);
            }
            return { localStorage: ls, sessionStorage: ss };
        }""")
        self.storage_file.write_text(json.dumps(storage, indent=2))
        logger.info("Saved storage (%d localStorage, %d sessionStorage keys)",
                     len(storage["localStorage"]), len(storage["sessionStorage"]))
        return storage

    async def load_storage(self, page, url: str) -> bool:
        """Restore localStorage for a given origin.

        Args:
            page: Playwright Page.
            url: URL whose origin to restore storage for.

        Returns:
            True if storage was loaded.
        """
        if not self.storage_file.exists():
            return False

        try:
            storage = json.loads(self.storage_file.read_text())
            ls = storage.get("localStorage", {})
            if ls:
                await page.goto(url, wait_until="domcontentloaded")
                for key, value in ls.items():
                    await page.evaluate(
                        f"localStorage.setItem({json.dumps(key)}, {json.dumps(value)})"
                    )
                logger.info("Restored %d localStorage keys for %s", len(ls), url)
                return True
        except Exception as e:
            logger.error("Failed to load storage: %s", e)
        return False

    async def check_login_status(self, page, platform: str = "instagram") -> bool:
        """Check if we're logged into a platform.

        Args:
            page: Playwright Page.
            platform: Platform to check.

        Returns:
            True if logged in.
        """
        checks = {
            "instagram": {
                "url": "https://www.instagram.com/",
                "logged_in_selector": 'svg[aria-label="Home"]',
                "logged_out_indicator": "Log in",
            },
            "twitter": {
                "url": "https://twitter.com/home",
                "logged_in_selector": '[data-testid="SideNav_AccountSwitcher_Button"]',
                "logged_out_indicator": "Log in",
            },
            "facebook": {
                "url": "https://www.facebook.com/",
                "logged_in_selector": '[aria-label="Facebook"]',
                "logged_out_indicator": "Log in",
            },
        }

        check = checks.get(platform)
        if not check:
            logger.warning("No login check defined for %s", platform)
            return False

        current_url = page.url
        await page.goto(check["url"], wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(3000)

        # Check for logged-in indicator
        try:
            el = await page.query_selector(check["logged_in_selector"])
            if el:
                logger.info("Logged into %s ✓", platform)
                return True
        except Exception:
            pass

        # Check for logged-out indicator
        text = await page.evaluate("document.body.innerText")
        if check["logged_out_indicator"] in text:
            logger.info("Not logged into %s", platform)
            return False

        return False

    def _normalize_cookies(self, cookies_raw: list[dict]) -> list[dict]:
        """Normalize cookie dicts to Playwright format."""
        cookies = []
        for c in cookies_raw:
            cookie = {
                "name": c.get("name", ""),
                "value": c.get("value", ""),
                "domain": c.get("domain", ""),
                "path": c.get("path", "/"),
            }

            # Handle secure flag
            if "secure" in c:
                cookie["secure"] = bool(c["secure"])

            # Handle httpOnly
            if "httpOnly" in c:
                cookie["httpOnly"] = bool(c["httpOnly"])

            # Handle sameSite
            sameSite = c.get("sameSite", "None")
            if sameSite in ("Strict", "Lax", "None"):
                cookie["sameSite"] = sameSite

            # Handle expiry — Playwright wants 'expires' as Unix timestamp
            if "expirationDate" in c:
                cookie["expires"] = float(c["expirationDate"])
            elif "expires" in c and isinstance(c["expires"], (int, float)):
                cookie["expires"] = float(c["expires"])

            # Skip empty cookies
            if cookie["name"] and cookie["value"]:
                cookies.append(cookie)

        return cookies

    def _parse_netscape_cookies(self, text: str) -> list[dict]:
        """Parse Netscape/curl format cookies."""
        cookies = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                cookies.append({
                    "name": parts[5],
                    "value": parts[6],
                    "domain": parts[0],
                    "path": parts[2],
                    "secure": parts[3].upper() == "TRUE",
                    "expires": float(parts[4]) if parts[4] != "0" else -1,
                })
        return cookies
