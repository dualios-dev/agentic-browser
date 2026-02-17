"""Autonomous AI agent loop for browser control.

The agent receives a goal, observes the current page state,
plans the next action using an LLM, executes it, and repeats
until the goal is achieved or max steps are reached.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import httpx

from .actions import BrowserActions
from .guardrail import scan_content, ThreatLevel
from .sanitizer import sanitize_html

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """Status of an agent step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentStep:
    """A single step in the agent's execution."""
    step_number: int
    thought: str = ""
    action: str = ""
    action_args: dict[str, Any] = field(default_factory=dict)
    observation: str = ""
    status: StepStatus = StepStatus.PENDING
    screenshot: bytes | None = None
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "thought": self.thought,
            "action": self.action,
            "action_args": self.action_args,
            "observation": self.observation[:500] if self.observation else "",
            "status": self.status.value,
            "has_screenshot": self.screenshot is not None,
            "timestamp": self.timestamp,
        }


@dataclass
class AgentResult:
    """Final result of an agent run."""
    goal: str
    success: bool
    summary: str
    steps: list[AgentStep]
    total_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "success": self.success,
            "summary": self.summary,
            "steps": [s.to_dict() for s in self.steps],
            "total_time": round(self.total_time, 2),
        }


# System prompt for the agent LLM
AGENT_SYSTEM_PROMPT = """You are an AI browser agent. You control a web browser to accomplish tasks.

You receive:
- The current page URL and title
- The page content (as clean markdown)
- A screenshot description
- The task/goal to accomplish

You respond with a JSON object containing:
{
    "thought": "Your reasoning about what to do next",
    "action": "one of: navigate, click, type, submit, scroll, screenshot, extract, done, fail",
    "args": {
        // depends on the action:
        // navigate: {"url": "https://..."}
        // click: {"selector": "css selector"}
        // type: {"selector": "css selector", "text": "text to type"}
        // scroll: {"direction": "down|up", "distance": 500}
        // screenshot: {}
        // extract: {}
        // done: {"summary": "what was accomplished"}
        // fail: {"reason": "why it failed"}
    }
}

Rules:
- Always explain your thinking in "thought"
- Use CSS selectors for click/type (e.g., "textarea[name=q]", "#search-btn", "a[href*=login]")
- Google Search uses textarea[name=q] (not input). For submitting, navigate to https://www.google.com/search?q=YOUR+QUERY is often faster than typing+clicking
- Amazon: ALWAYS use direct URL https://www.amazon.com/s?k=YOUR+SEARCH+TERMS instead of typing in their search box (avoids bot detection)
- If you see a "Continue shopping" or CAPTCHA page, click the continue button first
- After typing in a search box, use the "submit" action to press Enter, or click the submit button
- Prefer navigating directly via URL when possible (faster, more reliable)
- For product pages, use navigate with the full URL instead of clicking links when possible
- After typing in a search box, you often need to click search or press Enter — use click on the submit button or type with selector "body" and text "\\n" won't work; instead navigate or click
- If the page doesn't have what you need, navigate somewhere else
- If you're stuck after 3 attempts, use "fail"
- When the goal is achieved, use "done" with a summary
- Be efficient — don't take unnecessary steps
- ONLY respond with valid JSON, nothing else
"""


class BrowserAgent:
    """Autonomous browser agent powered by an LLM.

    Implements a observe-think-act loop:
    1. Observe: Get current page state (URL, content, screenshot)
    2. Think: Ask LLM what to do next
    3. Act: Execute the action
    4. Repeat until done or max steps
    """

    def __init__(
        self,
        actions: BrowserActions,
        config: dict[str, Any] | None = None,
        on_step: Callable[[AgentStep], Any] | None = None,
    ) -> None:
        """Initialize the agent.

        Args:
            actions: BrowserActions instance for controlling the browser.
            config: Agent config dict.
            on_step: Optional callback fired after each step (for live updates).
        """
        self.actions = actions
        self.config = config or {}
        self.on_step = on_step
        self.max_steps = self.config.get("max_steps", 15)
        self.steps: list[AgentStep] = []
        self._running = False

        # LLM config
        self.llm_provider = self.config.get("llm_provider", "gemini")
        self.llm_model = self.config.get("llm_model", "gemini-2.0-flash")
        self.api_key = (
            self.config.get("api_key")
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
        )

    async def run(self, goal: str) -> AgentResult:
        """Run the agent to accomplish a goal.

        Args:
            goal: Natural language description of what to achieve.

        Returns:
            AgentResult with success status, summary, and step history.
        """
        logger.info("Agent starting: %s", goal)
        start_time = time.time()
        self._running = True
        self.steps = []

        try:
            for step_num in range(1, self.max_steps + 1):
                if not self._running:
                    break

                step = AgentStep(step_number=step_num, timestamp=time.time())
                step.status = StepStatus.RUNNING
                self.steps.append(step)

                # 1. Observe current state
                observation = await self._observe()

                # 2. Think — ask LLM for next action
                llm_response = await self._think(goal, observation, self.steps)

                if llm_response is None:
                    step.thought = "LLM call failed"
                    step.status = StepStatus.FAILED
                    if self.on_step:
                        await _maybe_await(self.on_step, step)
                    break

                step.thought = llm_response.get("thought", "")
                step.action = llm_response.get("action", "")
                step.action_args = llm_response.get("args", {})

                logger.info(
                    "Step %d: %s → %s %s",
                    step_num, step.thought[:80], step.action, step.action_args,
                )

                # 3. Check for terminal actions
                if step.action == "done":
                    step.observation = step.action_args.get("summary", "Goal achieved")
                    step.status = StepStatus.COMPLETED
                    step.screenshot = await self.actions.screenshot()
                    if self.on_step:
                        await _maybe_await(self.on_step, step)
                    return AgentResult(
                        goal=goal,
                        success=True,
                        summary=step.observation,
                        steps=self.steps,
                        total_time=time.time() - start_time,
                    )

                if step.action == "fail":
                    step.observation = step.action_args.get("reason", "Agent gave up")
                    step.status = StepStatus.FAILED
                    if self.on_step:
                        await _maybe_await(self.on_step, step)
                    return AgentResult(
                        goal=goal,
                        success=False,
                        summary=step.observation,
                        steps=self.steps,
                        total_time=time.time() - start_time,
                    )

                # 4. Act — execute the action
                try:
                    step.observation = await self._act(step.action, step.action_args)
                    step.screenshot = await self.actions.screenshot()
                    step.status = StepStatus.COMPLETED
                except Exception as e:
                    step.observation = f"Action failed: {e}"
                    step.status = StepStatus.FAILED
                    logger.error("Step %d action failed: %s", step_num, e)

                if self.on_step:
                    await _maybe_await(self.on_step, step)

            # Max steps reached
            return AgentResult(
                goal=goal,
                success=False,
                summary=f"Reached max steps ({self.max_steps}) without completing goal",
                steps=self.steps,
                total_time=time.time() - start_time,
            )

        finally:
            self._running = False

    def stop(self) -> None:
        """Stop the agent's execution."""
        self._running = False

    async def _observe(self) -> dict[str, str]:
        """Get the current page state."""
        try:
            url = await self.actions.get_url()
            title = await self.actions.get_title()

            # Auto-handle "Continue shopping" / CAPTCHA interstitial pages
            try:
                continue_btn = await self.actions.page.wait_for_selector(
                    "input[value='Continue shopping'], a:has-text('Continue shopping'), button:has-text('Continue')",
                    timeout=2000
                )
                if continue_btn:
                    await continue_btn.click()
                    logger.info("Auto-clicked 'Continue shopping' button")
                    await asyncio.sleep(2)
                    url = await self.actions.get_url()
                    title = await self.actions.get_title()
            except Exception:
                pass  # No interstitial page, continue normally

            content = await self.actions.extract_content()

            # Run guardrail on content
            scan = scan_content(content)
            if scan.level == ThreatLevel.DANGEROUS:
                content = "[GUARDRAIL: Content blocked — potential prompt injection detected]"

            # Truncate content for LLM context
            if len(content) > 8000:
                content = content[:8000] + "\n\n[... truncated]"

            return {
                "url": url,
                "title": title,
                "content": content,
            }
        except Exception as e:
            logger.error("Observe failed: %s", e)
            return {"url": "unknown", "title": "unknown", "content": f"Error: {e}"}

    async def _think(
        self,
        goal: str,
        observation: dict[str, str],
        history: list[AgentStep],
    ) -> dict[str, Any] | None:
        """Ask the LLM what to do next."""
        if not self.api_key:
            logger.error("No API key configured for agent LLM")
            return None

        # Build conversation with history
        history_text = ""
        for s in history[:-1]:  # Exclude current step
            if s.action:
                history_text += (
                    f"Step {s.step_number}: {s.thought}\n"
                    f"  Action: {s.action} {s.action_args}\n"
                    f"  Result: {s.observation[:200]}\n\n"
                )

        user_message = (
            f"## Goal\n{goal}\n\n"
            f"## Current Page\n"
            f"URL: {observation['url']}\n"
            f"Title: {observation['title']}\n\n"
            f"## Page Content\n{observation['content']}\n\n"
        )
        if history_text:
            user_message += f"## Previous Steps\n{history_text}\n"
        user_message += "## What should I do next? Respond with JSON only."

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if self.llm_provider == "gemini":
                    model = self.llm_model or "gemini-2.0-flash"
                    resp = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}",
                        headers={"Content-Type": "application/json"},
                        json={
                            "system_instruction": {
                                "parts": [{"text": AGENT_SYSTEM_PROMPT}]
                            },
                            "contents": [
                                {"role": "user", "parts": [{"text": user_message}]}
                            ],
                            "generationConfig": {
                                "maxOutputTokens": 1024,
                                "temperature": 0,
                            },
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]

                elif self.llm_provider == "anthropic":
                    resp = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": self.api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json={
                            "model": self.llm_model,
                            "max_tokens": 1024,
                            "system": AGENT_SYSTEM_PROMPT,
                            "messages": [{"role": "user", "content": user_message}],
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    text = data["content"][0]["text"]
                else:  # openai
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.llm_model or "gpt-4o-mini",
                            "messages": [
                                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                                {"role": "user", "content": user_message},
                            ],
                            "max_tokens": 1024,
                            "temperature": 0,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"]

                # Parse JSON from response
                # Handle markdown code blocks
                text = text.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                    text = text.rsplit("```", 1)[0]
                    text = text.strip()

                return json.loads(text)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON: %s", e)
            return None
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return None

    async def _act(self, action: str, args: dict[str, Any]) -> str:
        """Execute a browser action.

        Returns:
            Observation string describing the result.
        """
        if action == "navigate":
            url = args.get("url", "")
            content = await self.actions.navigate(url)
            return f"Navigated to {url}. Page content:\n{content[:2000]}"

        elif action == "click":
            selector = args.get("selector", "")
            await self.actions.click_element(selector)
            await asyncio.sleep(1)  # Wait for page reaction
            content = await self.actions.extract_content()
            return f"Clicked {selector}. Page content:\n{content[:2000]}"

        elif action == "type":
            selector = args.get("selector", "")
            text = args.get("text", "")
            await self.actions.type_text(selector, text)
            return f"Typed '{text}' into {selector}"

        elif action == "submit":
            # Press Enter to submit a form
            await self.actions.page.keyboard.press("Enter")
            await asyncio.sleep(2)  # Wait for page load
            content = await self.actions.extract_content()
            return f"Pressed Enter to submit. Page content:\n{content[:2000]}"

        elif action == "scroll":
            direction = args.get("direction", "down")
            distance = args.get("distance", 500)
            await self.actions.scroll_page(direction, distance)
            content = await self.actions.extract_content()
            return f"Scrolled {direction} {distance}px. Content:\n{content[:2000]}"

        elif action == "screenshot":
            await self.actions.screenshot()
            return "Screenshot taken"

        elif action == "extract":
            content = await self.actions.extract_content()
            return f"Extracted content:\n{content[:3000]}"

        else:
            return f"Unknown action: {action}"


async def _maybe_await(fn: Callable, *args: Any) -> None:
    """Call a function, awaiting it if it's a coroutine."""
    result = fn(*args)
    if asyncio.iscoroutine(result):
        await result
