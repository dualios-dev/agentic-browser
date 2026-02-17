"""FastAPI server with WebSocket for the agentic browser dashboard.

Provides:
- REST API for task management
- WebSocket for live updates (screenshots, step progress, chat)
- Static file serving for the web dashboard
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .agent import BrowserAgent, AgentStep
from .bridge import AgentBridge
from .tasks import TaskManager, TaskStatus

logger = logging.getLogger(__name__)

# Paths
WEB_DIR = Path(__file__).parent.parent / "web"

app = FastAPI(title="Agentic Browser", version="1.0.0")

# Global state
bridge: AgentBridge | None = None
agent: BrowserAgent | None = None
task_manager = TaskManager()
connected_clients: list[WebSocket] = []
_screenshot_task: asyncio.Task | None = None
_task_lock: asyncio.Lock | None = None  # Ensure only one task runs at a time


# --- WebSocket broadcasting ---

async def broadcast(message: dict[str, Any]) -> None:
    """Send a message to all connected WebSocket clients."""
    if not connected_clients:
        return
    data = json.dumps(message)
    disconnected = []
    for ws in connected_clients:
        try:
            await ws.send_text(data)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        connected_clients.remove(ws)


async def broadcast_screenshot() -> None:
    """Take a screenshot and broadcast it to all clients."""
    if bridge and bridge._actions:
        try:
            png_bytes = await bridge.screenshot()
            b64 = base64.b64encode(png_bytes).decode("ascii")
            await broadcast({
                "type": "screenshot",
                "data": b64,
                "timestamp": time.time(),
            })
        except Exception as e:
            logger.debug("Screenshot broadcast failed: %s", e)


async def screenshot_loop() -> None:
    """Continuously broadcast screenshots while browser is running."""
    while True:
        if connected_clients and bridge and bridge._browser:
            await broadcast_screenshot()
        await asyncio.sleep(1.0)  # 1 FPS for live view


async def on_agent_step(step: AgentStep) -> None:
    """Callback fired by the agent after each step — broadcasts to clients."""
    step_data = step.to_dict()
    # Include screenshot if available
    if step.screenshot:
        step_data["screenshot"] = base64.b64encode(step.screenshot).decode("ascii")
    await broadcast({
        "type": "step",
        "data": step_data,
    })


# --- Lifecycle ---

@app.on_event("startup")
async def startup() -> None:
    """Start the browser and screenshot loop on server start."""
    global bridge, agent, _screenshot_task, _task_lock
    _task_lock = asyncio.Lock()

    config_path = os.environ.get("AGENT_CONFIG", "config.yaml")
    bridge = AgentBridge.from_config(config_path)

    # Override headless to False so user can see the browser
    bridge.config.setdefault("browser", {})["headless"] = False

    await bridge.start()
    logger.info("Browser started")

    # Create agent
    agent_config = bridge.config.get("agent", {})
    agent = BrowserAgent(
        actions=bridge.actions,
        config=agent_config,
        on_step=on_agent_step,
    )

    # Navigate to Google by default
    await bridge.actions.navigate("https://www.google.com")

    # Start screenshot broadcasting loop
    _screenshot_task = asyncio.create_task(screenshot_loop())
    logger.info("Agentic Browser server ready")


@app.on_event("shutdown")
async def shutdown() -> None:
    """Clean up on server shutdown."""
    global _screenshot_task
    if _screenshot_task:
        _screenshot_task.cancel()
    if bridge:
        await bridge.stop()
    logger.info("Server shut down")


# --- Web Dashboard ---

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the dashboard."""
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>Agentic Browser</h1><p>Web directory not found.</p>")


@app.get("/style.css")
async def css():
    return FileResponse(WEB_DIR / "style.css", media_type="text/css")


@app.get("/app.js")
async def js():
    return FileResponse(WEB_DIR / "app.js", media_type="application/javascript")


# --- REST API ---

@app.get("/api/status")
async def get_status():
    """Get server and browser status."""
    browser_status = {}
    if bridge:
        try:
            browser_status = await bridge.get_status()
        except Exception:
            browser_status = {"running": False}

    return {
        "server": "running",
        "browser": browser_status,
        "tasks": task_manager.get_status(),
    }


@app.get("/api/tasks")
async def get_tasks():
    """Get task history."""
    return {"tasks": task_manager.get_all_tasks()}


@app.post("/api/tasks")
async def create_task(body: dict[str, Any]):
    """Submit a new task."""
    goal = body.get("goal", "").strip()
    if not goal:
        return {"error": "Goal is required"}, 400

    task = task_manager.create_task(goal)
    # Run the task in the background
    asyncio.create_task(_run_task(task.id))
    return {"task": task.to_dict()}


@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a running task."""
    task = task_manager.get_task(task_id)
    if not task:
        return {"error": "Task not found"}, 404
    if agent:
        agent.stop()
    task_manager.cancel_task(task_id)
    await broadcast({"type": "task_cancelled", "task_id": task_id})
    return {"status": "cancelled"}


@app.post("/api/login/instagram")
async def login_instagram(body: dict[str, Any]):
    """Login to Instagram."""
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    if not username or not password:
        return {"error": "Username and password required"}, 400
    if not bridge:
        return {"error": "Browser not started"}, 500
    
    success = await bridge.actions.login_instagram(username, password)
    return {"success": success, "username": username}


@app.post("/api/navigate")
async def navigate(body: dict[str, Any]):
    """Manually navigate the browser."""
    url = body.get("url", "").strip()
    if not url:
        return {"error": "URL is required"}, 400
    if bridge:
        content = await bridge.actions.navigate(url)
        return {"url": url, "content": content[:2000]}
    return {"error": "Browser not running"}, 503


# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket connection for live updates."""
    await ws.accept()
    connected_clients.append(ws)
    logger.info("Client connected (%d total)", len(connected_clients))

    # Send initial state
    await ws.send_text(json.dumps({
        "type": "connected",
        "tasks": task_manager.get_all_tasks(limit=20),
    }))

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "task":
                # Submit a task via WebSocket
                goal = msg.get("goal", "").strip()
                if goal:
                    task = task_manager.create_task(goal)
                    await ws.send_text(json.dumps({
                        "type": "task_created",
                        "task": task.to_dict(),
                    }))
                    asyncio.create_task(_run_task(task.id))

            elif msg.get("type") == "navigate":
                url = msg.get("url", "").strip()
                if url and bridge:
                    await bridge.actions.navigate(url)

            elif msg.get("type") == "stop":
                if agent:
                    agent.stop()

    except WebSocketDisconnect:
        if ws in connected_clients:
            connected_clients.remove(ws)
        logger.info("Client disconnected (%d remaining)", len(connected_clients))
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        if ws in connected_clients:
            connected_clients.remove(ws)


# --- Task Runner ---

async def _run_task(task_id: str) -> None:
    """Run a task using the agent (sequential — one at a time)."""
    async with _task_lock:
        task = task_manager.get_task(task_id)
        if not task or not agent:
            return

        task_manager.start_task(task_id)
        await broadcast({
            "type": "task_started",
            "task": task.to_dict(),
        })

        try:
            result = await agent.run(task.goal)
            task_manager.complete_task(task_id, result)
            await broadcast({
                "type": "task_completed",
                "task": task.to_dict(),
            })
        except Exception as e:
            logger.error("Task %s failed: %s", task_id, e)
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()
            await broadcast({
                "type": "task_failed",
                "task": task.to_dict(),
                "error": str(e),
            })


def run_server(host: str = "0.0.0.0", port: int = 8888) -> None:
    """Start the server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
