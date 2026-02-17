"""Human behavior simulation for browser automation.

Implements bezier-curve mouse movements, gaussian-distributed typing delays,
and natural scroll patterns to evade bot detection.
"""

from __future__ import annotations

import asyncio
import math
import random
from typing import Any

from playwright.async_api import Page


def _bezier_curve(
    start: tuple[float, float],
    end: tuple[float, float],
    num_points: int = 20,
) -> list[tuple[float, float]]:
    """Generate points along a cubic bezier curve between start and end.

    Uses two random control points to create natural-looking mouse paths.
    """
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy

    # Random control points offset from the line
    cp1 = (
        sx + dx * random.uniform(0.1, 0.4) + random.uniform(-50, 50),
        sy + dy * random.uniform(0.1, 0.4) + random.uniform(-50, 50),
    )
    cp2 = (
        sx + dx * random.uniform(0.6, 0.9) + random.uniform(-50, 50),
        sy + dy * random.uniform(0.6, 0.9) + random.uniform(-50, 50),
    )

    points: list[tuple[float, float]] = []
    for i in range(num_points + 1):
        t = i / num_points
        inv = 1 - t
        x = (inv**3 * sx +
             3 * inv**2 * t * cp1[0] +
             3 * inv * t**2 * cp2[0] +
             t**3 * ex)
        y = (inv**3 * sy +
             3 * inv**2 * t * cp1[1] +
             3 * inv * t**2 * cp2[1] +
             t**3 * ey)
        points.append((x, y))

    return points


async def human_move_mouse(
    page: Page,
    target_x: float,
    target_y: float,
    speed_range: tuple[int, int] = (80, 250),
) -> None:
    """Move the mouse to target coordinates along a bezier curve.

    Args:
        page: Playwright page instance.
        target_x: Destination X coordinate.
        target_y: Destination Y coordinate.
        speed_range: Min/max total movement time in ms.
    """
    # Get current mouse position (default to random starting point)
    # Playwright doesn't expose cursor position, so we track roughly
    start_x = random.uniform(100, 500)
    start_y = random.uniform(100, 500)

    points = _bezier_curve((start_x, start_y), (target_x, target_y))
    total_time = random.uniform(speed_range[0], speed_range[1]) / 1000.0
    step_delay = total_time / len(points)

    for x, y in points:
        await page.mouse.move(x, y)
        # Add slight jitter to timing
        await asyncio.sleep(step_delay * random.uniform(0.7, 1.3))


async def human_click(
    page: Page,
    x: float,
    y: float,
    speed_range: tuple[int, int] = (80, 250),
) -> None:
    """Move to coordinates with bezier curve then click.

    Args:
        page: Playwright page instance.
        x: Click X coordinate.
        y: Click Y coordinate.
        speed_range: Mouse movement speed range in ms.
    """
    await human_move_mouse(page, x, y, speed_range)
    # Small pause before click (humans don't click instantly on arrival)
    await asyncio.sleep(random.uniform(0.02, 0.1))
    await page.mouse.down()
    # Hold click for realistic duration
    await asyncio.sleep(random.uniform(0.04, 0.12))
    await page.mouse.up()


async def human_type(
    page: Page,
    text: str,
    mean_delay: float = 75.0,
    stddev: float = 25.0,
) -> None:
    """Type text with gaussian-distributed delays between keystrokes.

    Simulates realistic typing patterns including occasional pauses
    at word boundaries and slight speed variations.

    Args:
        page: Playwright page instance.
        text: Text to type.
        mean_delay: Mean delay between keystrokes in ms.
        stddev: Standard deviation for delay distribution.
    """
    for i, char in enumerate(text):
        await page.keyboard.type(char)

        # Base delay with gaussian distribution
        delay = max(20, random.gauss(mean_delay, stddev)) / 1000.0

        # Longer pause at word boundaries (space, punctuation)
        if char in " .,;:!?\n":
            delay *= random.uniform(1.5, 3.0)

        # Occasional "thinking" pause (roughly 1 in 20 chars)
        if random.random() < 0.05:
            delay += random.uniform(0.3, 0.8)

        await asyncio.sleep(delay)


async def human_scroll(
    page: Page,
    direction: str = "down",
    distance: int = 500,
    step_mean: float = 120.0,
    step_stddev: float = 40.0,
    delay_mean: float = 50.0,
    delay_stddev: float = 20.0,
) -> None:
    """Scroll the page in natural increments.

    Uses gaussian-distributed step sizes and delays to simulate
    natural human scrolling behavior.

    Args:
        page: Playwright page instance.
        direction: "down" or "up".
        distance: Total distance to scroll in pixels.
        step_mean: Mean pixels per scroll step.
        step_stddev: Standard deviation for step size.
        delay_mean: Mean delay between steps in ms.
        delay_stddev: Standard deviation for delay.
    """
    scrolled = 0
    sign = 1 if direction == "down" else -1

    while scrolled < distance:
        step = max(20, int(random.gauss(step_mean, step_stddev)))
        step = min(step, distance - scrolled)

        await page.mouse.wheel(0, step * sign)
        scrolled += step

        delay = max(10, random.gauss(delay_mean, delay_stddev)) / 1000.0
        await asyncio.sleep(delay)

    # Small settling pause after scrolling
    await asyncio.sleep(random.uniform(0.1, 0.3))


async def random_pause(min_ms: int = 200, max_ms: int = 800) -> None:
    """Random micro-pause between actions.

    Args:
        min_ms: Minimum pause in milliseconds.
        max_ms: Maximum pause in milliseconds.
    """
    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000.0)
