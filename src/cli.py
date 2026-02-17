"""CLI entry point for Agentic Browser.

Usage:
    agentic-browser              # Launch dashboard on port 8888
    agentic-browser --port 3000  # Custom port
    agentic-browser --headless   # Run browser in headless mode
    agentic-browser browse URL   # Quick browse a URL and print content
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="agentic-browser",
        description="🌐 Agentic Browser — AI-controlled stealth browser",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Default: start the dashboard server
    parser.add_argument("--port", type=int, default=8888, help="Dashboard port (default: 8888)")
    parser.add_argument("--host", default="0.0.0.0", help="Dashboard host (default: 0.0.0.0)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--api-key", help="LLM API key (or set GEMINI_API_KEY env var)")

    # Subcommand: browse
    browse_parser = subparsers.add_parser("browse", help="Browse a URL and print sanitized content")
    browse_parser.add_argument("url", help="URL to browse")
    browse_parser.add_argument("--screenshot", "-s", help="Save screenshot to path")

    args = parser.parse_args()

    if args.command == "browse":
        asyncio.run(_browse(args))
    else:
        _start_server(args)


def _start_server(args):
    """Start the dashboard server."""
    import uvicorn

    # Set env vars for the server
    if args.api_key:
        os.environ["GEMINI_API_KEY"] = args.api_key
    if args.config:
        os.environ["AGENT_CONFIG"] = args.config
    if args.headless:
        os.environ["AGENT_HEADLESS"] = "1"

    print(f"""
╔══════════════════════════════════════════╗
║     🌐 Agentic Browser v0.1.0          ║
║                                          ║
║  Dashboard: http://localhost:{args.port:<5}      ║
║  Press Ctrl+C to stop                    ║
╚══════════════════════════════════════════╝
""")

    uvicorn.run(
        "src.server:app",
        host=args.host,
        port=args.port,
        log_level="info",
    )


async def _browse(args):
    """Quick browse a URL."""
    from .bridge import AgentBridge

    bridge = AgentBridge.from_config(args.config if hasattr(args, "config") else "config.yaml")

    async with bridge:
        result = await bridge.browse(args.url)
        print(f"# {result.title}")
        print(f"URL: {result.url}")
        print(f"Guardrail: {result.guardrail.level.value}")
        if result.guardrail.matches:
            print(f"⚠️  Warnings: {result.guardrail.details}")
        print("---")
        print(result.content[:5000])

        if args.screenshot:
            await bridge.screenshot(args.screenshot)
            print(f"\n📸 Screenshot saved to {args.screenshot}")


if __name__ == "__main__":
    main()
