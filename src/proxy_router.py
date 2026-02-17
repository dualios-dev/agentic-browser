"""Domain-based proxy routing.

Routes browser traffic through different proxy tiers based on
domain risk classification. Supports SOCKS5 and HTTP proxies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ProxyRoute:
    """A resolved proxy route for a given URL."""
    url: str
    domain: str
    tier: str  # "high", "medium", "low", "direct"
    proxy: str | None  # Proxy URL or None for direct


@dataclass
class ProxyRouter:
    """Routes domains to proxy tiers based on configuration.

    Tiers:
    - high: High-security sites (social media) → mobile/residential proxy
    - medium: Medium-risk sites (search, shopping) → static residential
    - low: Low-risk sites → direct or cheap proxy
    - direct: No proxy
    """
    tiers: dict[str, dict[str, Any]] = field(default_factory=dict)
    default_proxy: str | None = None
    _domain_cache: dict[str, tuple[str, str | None]] = field(
        default_factory=dict, repr=False
    )

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> ProxyRouter:
        """Create a ProxyRouter from the proxy section of config.yaml.

        Args:
            config: The 'proxy' section of the config dict.

        Returns:
            Configured ProxyRouter instance.
        """
        tiers = config.get("tiers", {})
        default = config.get("default")
        router = cls(tiers=tiers, default_proxy=default)

        # Pre-build domain cache
        for tier_name, tier_cfg in tiers.items():
            proxy = tier_cfg.get("proxy")
            for domain in tier_cfg.get("domains", []):
                router._domain_cache[domain.lower()] = (tier_name, proxy)

        return router

    def _extract_domain(self, url: str) -> str:
        """Extract the registrable domain from a URL."""
        parsed = urlparse(url if "://" in url else f"https://{url}")
        hostname = (parsed.hostname or "").lower()
        # Strip 'www.' prefix
        if hostname.startswith("www."):
            hostname = hostname[4:]
        return hostname

    def route(self, url: str) -> ProxyRoute:
        """Determine the proxy route for a URL.

        Matches against configured domain lists to find the appropriate
        proxy tier. Falls back to default proxy if no match.

        Args:
            url: The URL to route.

        Returns:
            ProxyRoute with the resolved proxy information.
        """
        domain = self._extract_domain(url)

        # Check exact domain match
        if domain in self._domain_cache:
            tier, proxy = self._domain_cache[domain]
            logger.debug("Routing %s → tier=%s proxy=%s", domain, tier, proxy or "direct")
            return ProxyRoute(url=url, domain=domain, tier=tier, proxy=proxy)

        # Check if it's a subdomain of a configured domain
        for configured_domain, (tier, proxy) in self._domain_cache.items():
            if domain.endswith(f".{configured_domain}"):
                logger.debug(
                    "Routing %s (sub of %s) → tier=%s proxy=%s",
                    domain, configured_domain, tier, proxy or "direct",
                )
                return ProxyRoute(url=url, domain=domain, tier=tier, proxy=proxy)

        # Default
        logger.debug("Routing %s → default proxy=%s", domain, self.default_proxy or "direct")
        return ProxyRoute(
            url=url,
            domain=domain,
            tier="direct",
            proxy=self.default_proxy,
        )

    def get_playwright_proxy(self, url: str) -> dict[str, str] | None:
        """Get proxy config in Playwright's expected format.

        Args:
            url: The URL to route.

        Returns:
            Dict with 'server' key for Playwright, or None for direct.
        """
        route = self.route(url)
        if route.proxy is None:
            return None
        return {"server": route.proxy}
