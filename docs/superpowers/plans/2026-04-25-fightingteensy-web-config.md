# FightingTeensy Web Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a browser-based PC configuration tool for bottom calibration and press/release/rapid-trigger tuning.

**Architecture:** Keep firmware protocol unchanged. Add a small Python HTTP server that reuses the existing serial command builder and serves a static single-page UI. The browser calls JSON endpoints for port listing, connect checks, settings, samples, calibration, setting changes, and EEPROM save.

**Tech Stack:** Python standard library HTTP server, optional pyserial, existing `tools/fighting_teensy_cli.py`, vanilla HTML/CSS/JavaScript, unittest.

---

### Task 1: API Model and Command Layer

**Files:**
- Create: `tools/fighting_teensy_web.py`
- Test: `tests/test_web_config.py`

- [ ] Write failing tests for request validation and command dispatch using a fake device.
- [ ] Implement a small `WebConfigApp` that converts JSON actions into existing serial protocol commands.
- [ ] Verify `python -m unittest tests.test_web_config` passes.

### Task 2: HTTP Server and Static UI

**Files:**
- Modify: `tools/fighting_teensy_web.py`
- Create: `tools/web_config/index.html`
- Create: `tools/web_config/app.js`
- Create: `tools/web_config/styles.css`
- Test: `tests/test_web_config.py`

- [ ] Add tests for HTTP JSON responses with a fake app.
- [ ] Serve `/`, static assets, `/api/ports`, `/api/ping`, `/api/settings`, `/api/sample`, `/api/calibrate`, `/api/set`, and `/api/save`.
- [ ] Implement a dense controller-focused UI with per-direction bottom calibration and press/release/rapid numeric controls.
- [ ] Verify unit tests pass.

### Task 3: Manual Verification

**Files:**
- Modify: `README.md`

- [ ] Document `python tools\fighting_teensy_web.py --port 8765`.
- [ ] Run `python -m unittest discover -s tests`.
- [ ] Run Python compile checks.
- [ ] Start the server and inspect `http://127.0.0.1:8765/` in the in-app browser.
- [ ] If a config firmware COM port is present, verify `ping`, `sample`, and settings loading.
