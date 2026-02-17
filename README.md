# Agentic Browser — Project Spec

## Goal
Build a secure, undetectable, AI-controlled browser system.

## Requirements

### 1. Stealth (Anti-Detection)
- Undetectable browser engine (Camoufox / Rebrowser patches / undetected-chromedriver)
- No `navigator.webdriver` leaks, no automation fingerprints
- Human-like fingerprints (canvas, WebGL, fonts, timezone)
- Human behavior simulation (mouse bezier curves, realistic typing, natural scroll/delays)

### 2. Security (Anti-Prompt-Injection)
- Browser runs in a **sandbox** (container/namespace isolation)
- Raw website → **Structural Sanitizer** → clean Markdown only
  - Strip hidden elements, comments, scripts, iframes, zero-width chars
- **AI Guardrail Model** (small/cheap) scans markdown for prompt injection before main agent sees it
- Main agent **never** sees raw DOM or unsanitized content
- **Policy Layer** — action allowlist, rate limiting on sensitive ops

### 3. Proxy / IP Stealth
- Domain-based proxy routing:
  - High-security (Instagram, X, TikTok) → mobile proxy
  - Medium (Google, etc.) → static residential proxy
  - Low-risk / internal → direct
- Fingerprint-IP sync (timezone, locale, language match IP geolocation)
- WebRTC disabled / DNS leak protection
- IP warm-up protocol for new IPs
- Session stickiness (same IP + profile + cookies per identity)

### 4. AI Control Interface
- CDP (Chrome DevTools Protocol) bridge
- Actions: navigate, click, type, screenshot, extract
- Markdown-based task files for AI context
- Session persistence (cookies, logins survive restarts)

## Architecture

```
Website → [Proxy Router (residential/mobile/direct)]
              ↓
         [Stealth Browser in Sandbox]
              ↓ (CDP)
         [Structural Sanitizer] → clean Markdown
              ↓
         [AI Guardrail Model] → blocks prompt injection
              ↓ (safe markdown)
         [Main Agent] → reads & acts
              ↓ (actions)
         [Policy Layer] → validates against allowlist
              ↓
         [Browser executes via proxy]
```

## Tech Stack
- Browser: Camoufox (Firefox) or patched Chromium
- Anti-detect: Fingerprint spoofing, proxy rotation
- AI Control: CDP + Python bridge
- Proxy: SOCKS5/HTTP, residential + mobile pools
- Guardrail: Small LLM for injection detection
- Docs: Markdown specs in this folder

## File Structure
```
browser-agent/
├── README.md              # This file
├── config.yaml            # Browser profile, proxy, fingerprint settings
├── src/
│   ├── browser.py         # Stealth browser launcher
│   ├── actions.py         # Click, type, scroll, extract
│   ├── humanize.py        # Human behavior simulation
│   ├── fingerprint.py     # Fingerprint generation
│   ├── sanitizer.py       # HTML → clean Markdown
│   ├── guardrail.py       # AI prompt injection filter
│   ├── proxy_router.py    # Domain-based proxy selection
│   └── bridge.py          # AI ↔ browser CDP interface
├── profiles/              # Persistent browser profiles
└── logs/                  # Session logs
```

## Status
- [ ] Research & pick browser engine
- [ ] Setup on VM
- [ ] Build core (launcher + CDP bridge + actions)
- [ ] Add stealth (fingerprinting + human behavior)
- [ ] Build sanitizer (HTML → Markdown)
- [ ] Build guardrail (prompt injection filter)
- [ ] Proxy router
- [ ] Test against detection sites
- [ ] Integrate with OpenClaw
- [ ] Document everything
