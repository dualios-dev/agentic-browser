# 🌐 Agentic Browser

A secure, undetectable, AI-controlled browser. Give it a task in plain English — it opens a stealth browser, figures out the steps, and does it for you.

![Dashboard](https://img.shields.io/badge/dashboard-live_view-blue) ![Python](https://img.shields.io/badge/python-3.10+-green) ![License](https://img.shields.io/badge/license-MIT-gray)

## What It Does

- **Autonomous browsing** — Tell it "search for flights from NYC to LA" and watch it work
- **Stealth browser** — Uses [Camoufox](https://github.com/daijro/camoufox) (Firefox fork) — undetectable by anti-bot systems
- **Live dashboard** — Watch the browser in real-time, chat with the agent, see each step
- **Safety built-in** — Prompt injection guardrail, HTML sanitizer, content filtering
- **Human-like behavior** — Bezier mouse curves, realistic typing, natural scrolling

## Quick Start

### Option 1: pip install

```bash
# Clone the repo
git clone https://github.com/dualios-dev/agentic-browser.git
cd agentic-browser

# Install
pip install -e .

# Set your LLM API key (pick one)
export GEMINI_API_KEY="your-key-here"
# or: export ANTHROPIC_API_KEY="your-key-here"
# or: export OPENAI_API_KEY="your-key-here"

# Launch
agentic-browser
```

Open **http://localhost:8888** — that's your dashboard.

### Option 2: Docker

```bash
docker build -t agentic-browser .
docker run -p 8888:8888 -e GEMINI_API_KEY="your-key" agentic-browser
```

### Option 3: Quick browse (no dashboard)

```bash
agentic-browser browse https://example.com
agentic-browser browse https://example.com --screenshot shot.png
```

## Dashboard

The dashboard gives you:

| Panel | What it does |
|-------|-------------|
| **Live View** | Real-time screenshot stream of the browser |
| **URL Bar** | Navigate the browser manually |
| **Agent Chat** | Type tasks in plain English |
| **Task Steps** | Watch each step the AI takes (think → act → observe) |

## Architecture

```
You (Dashboard) → FastAPI Server → AI Agent (Gemini/Claude/GPT)
                                       ↓
                                   Stealth Browser (Camoufox)
                                       ↓
                                   HTML → Sanitizer → Clean Markdown
                                       ↓
                                   Guardrail (prompt injection filter)
                                       ↓
                                   Safe content → AI decides next action
```

## Project Structure

```
agentic-browser/
├── src/
│   ├── agent.py          # AI agent loop (observe → think → act)
│   ├── server.py         # FastAPI + WebSocket dashboard backend
│   ├── bridge.py         # Orchestrator — ties everything together
│   ├── browser.py        # Stealth browser launcher (Camoufox)
│   ├── actions.py        # Click, type, scroll, extract, screenshot
│   ├── humanize.py       # Human-like mouse/typing/scroll simulation
│   ├── fingerprint.py    # Browser fingerprint generation
│   ├── sanitizer.py      # HTML → clean Markdown
│   ├── guardrail.py      # Prompt injection detection
│   ├── proxy_router.py   # Domain-based proxy routing
│   ├── tasks.py          # Task queue and history
│   └── cli.py            # CLI entry point
├── web/
│   ├── index.html        # Dashboard UI
│   ├── style.css         # Dark theme
│   └── app.js            # WebSocket client
├── config.yaml           # All settings (browser, proxy, agent, etc.)
├── Dockerfile            # One-command Docker setup
├── setup.py              # pip installable
└── requirements.txt      # Python dependencies
```

## Configuration

Edit `config.yaml` to customize:

- **Browser** — headless mode, viewport, timeouts
- **Proxy** — domain-based routing (social media → mobile proxy, etc.)
- **Agent** — LLM provider (gemini/anthropic/openai), model, max steps
- **Guardrail** — prompt injection patterns, block vs warn
- **Humanize** — mouse speed, typing delay, scroll behavior

## LLM Support

| Provider | Models | Env Variable |
|----------|--------|-------------|
| Google Gemini | gemini-2.0-flash, gemini-pro | `GEMINI_API_KEY` |
| Anthropic | claude-sonnet, claude-haiku | `ANTHROPIC_API_KEY` |
| OpenAI | gpt-4o, gpt-4o-mini | `OPENAI_API_KEY` |

## Security

- **Prompt injection guardrail** — Scans all page content before the AI sees it
- **HTML sanitizer** — Strips scripts, hidden elements, zero-width chars
- **Proxy routing** — High-risk sites get residential/mobile proxies
- **Sandbox ready** — Run in Docker for isolation

## License

MIT
