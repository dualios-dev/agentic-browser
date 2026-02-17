"""Fingerprint generation for stealth browsing.

Generates realistic browser fingerprints: screen resolution, timezone,
locale, WebGL vendor/renderer, and canvas noise parameters.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class Fingerprint:
    """A complete browser fingerprint."""

    screen_width: int = 1920
    screen_height: int = 1080
    color_depth: int = 24
    timezone: str = "America/New_York"
    locale: str = "en-US"
    platform: str = "Win32"
    webgl_vendor: str = "Google Inc. (NVIDIA)"
    webgl_renderer: str = "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"
    canvas_noise_seed: int = 0
    hardware_concurrency: int = 8
    device_memory: int = 8
    max_touch_points: int = 0
    languages: list[str] = field(default_factory=lambda: ["en-US", "en"])
    do_not_track: str | None = None

    def to_camoufox_config(self) -> dict[str, Any]:
        """Convert to camoufox-compatible config dict."""
        return {
            "window.outerWidth": self.screen_width,
            "window.outerHeight": self.screen_height,
            "screen.width": self.screen_width,
            "screen.height": self.screen_height,
            "screen.colorDepth": self.color_depth,
            "navigator.hardwareConcurrency": self.hardware_concurrency,
            "navigator.deviceMemory": self.device_memory,
            "navigator.maxTouchPoints": self.max_touch_points,
            "navigator.languages": self.languages,
        }


_PLATFORMS = [
    ("Win32", ["en-US", "en"]),
    ("MacIntel", ["en-US", "en"]),
    ("Linux x86_64", ["en-US", "en"]),
]

_HARDWARE = [
    (4, 4),
    (8, 8),
    (12, 16),
    (16, 16),
    (16, 32),
]


def generate_fingerprint(config: dict[str, Any] | None = None) -> Fingerprint:
    """Generate a realistic random fingerprint.

    Args:
        config: Optional config dict (fingerprint section from config.yaml).

    Returns:
        A populated Fingerprint instance.
    """
    cfg = config or {}

    # Screen resolution
    resolutions = cfg.get("screen_resolutions", [
        [1920, 1080], [2560, 1440], [1536, 864], [1440, 900],
    ])
    width, height = random.choice(resolutions)

    # WebGL
    webgl_pairs = cfg.get("webgl_pairs", [
        {
            "vendor": "Google Inc. (NVIDIA)",
            "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        },
    ])
    webgl = random.choice(webgl_pairs)

    # Platform & languages
    platform, default_langs = random.choice(_PLATFORMS)
    locale = cfg.get("locale", "en-US")
    langs = [locale] if locale not in default_langs else default_langs

    # Hardware
    cores, mem = random.choice(_HARDWARE)

    # Canvas noise seed — deterministic per "session" but random across sessions
    noise_seed = random.randint(0, 2**32 - 1)

    return Fingerprint(
        screen_width=width,
        screen_height=height,
        color_depth=random.choice([24, 30]),
        timezone=cfg.get("timezone", "America/New_York"),
        locale=locale,
        platform=platform,
        webgl_vendor=webgl["vendor"],
        webgl_renderer=webgl["renderer"],
        canvas_noise_seed=noise_seed,
        hardware_concurrency=cores,
        device_memory=mem,
        max_touch_points=0 if "Linux" in platform or "Win" in platform else random.choice([0, 5]),
        languages=langs,
        do_not_track=random.choice([None, "1"]),
    )


def fingerprint_hash(fp: Fingerprint) -> str:
    """Generate a deterministic hash for a fingerprint (for logging/tracking)."""
    data = f"{fp.screen_width}{fp.screen_height}{fp.webgl_renderer}{fp.platform}{fp.canvas_noise_seed}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]
