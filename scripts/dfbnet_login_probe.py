#!/usr/bin/env python3
"""
DFBNet SRIA login/API probe for local headed Playwright debugging.

Run this on your Mac, log in manually, then create/list a Freihalter in the UI.
The script records the API shape and auth/session clues without printing full tokens.

It does NOT create Freihalter by itself. It only observes browser traffic.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, Request, Response, TimeoutError as PlaywrightTimeoutError, Page

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

DEFAULT_START_URL = "https://sria.dfbnet.org/"
DEFAULT_API_PREFIX = "https://api.dfbnet.org/api/referee/"
TOKEN_RE = re.compile(r"Bearer\s+([A-Za-z0-9_\-.]+)")
JWT_RE = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(msg: str) -> None:
    print(f"[{now()}] {msg}", flush=True)


def redact_header_value(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    lname = name.lower()
    if lname == "authorization":
        m = TOKEN_RE.search(value)
        if not m:
            return "<redacted>"
        tok = m.group(1)
        return f"Bearer {tok[:16]}...{tok[-10:]} (len={len(tok)})"
    if any(x in lname for x in ["cookie", "token", "secret", "password", "key"]):
        return "<redacted>"
    return value


def decode_jwt_claims(token: str) -> dict[str, Any] | None:
    try:
        import base64
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
    except Exception:
        return None


def summarize_token(auth_header: str | None) -> dict[str, Any] | None:
    if not auth_header:
        return None
    m = TOKEN_RE.search(auth_header)
    if not m:
        return {"present": True, "type": "unknown"}
    tok = m.group(1)
    claims = decode_jwt_claims(tok)
    out: dict[str, Any] = {
        "present": True,
        "prefix": tok[:16],
        "suffix": tok[-10:],
        "length": len(tok),
    }
    if claims:
        for key in ["iss", "azp", "sub", "scope", "dfbnet_id", "dfbnet_techuser_id", "email"]:
            if key in claims:
                out[key] = claims[key]
        for key in ["iat", "exp", "auth_time"]:
            if key in claims:
                out[key] = claims[key]
                try:
                    out[f"{key}_utc"] = datetime.fromtimestamp(int(claims[key]), timezone.utc).isoformat()
                except Exception:
                    pass
    return out


def safe_json_parse(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return text


def safe_console_text(text: str) -> str:
    if "tokenResponse" in text or "access_token" in text or "refresh_token" in text:
        return "<redacted token-related browser console message>"
    return text


class Recorder:
    def __init__(self, out_dir: Path, api_prefix: str):
        self.out_dir = out_dir
        self.api_prefix = api_prefix
        self.events: list[dict[str, Any]] = []
        self.api_events: list[dict[str, Any]] = []
        self.last_auth_summary: dict[str, Any] | None = None
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def append_event(self, event: dict[str, Any], api: bool = False) -> None:
        self.events.append(event)
        if api:
            self.api_events.append(event)
        # Persist often, so logs survive Ctrl+C/crashes.
        self.flush()

    def flush(self) -> None:
        (self.out_dir / "events.json").write_text(json.dumps(self.events, indent=2, ensure_ascii=False), encoding="utf-8")
        (self.out_dir / "api-events.json").write_text(json.dumps(self.api_events, indent=2, ensure_ascii=False), encoding="utf-8")
        if self.last_auth_summary:
            (self.out_dir / "last-auth-summary.json").write_text(json.dumps(self.last_auth_summary, indent=2, ensure_ascii=False), encoding="utf-8")

    async def on_request(self, request: Request) -> None:
        url = request.url
        method = request.method
        is_api = url.startswith(self.api_prefix) or "api.dfbnet.org" in url
        if not is_api:
            return

        headers = await request.all_headers()
        post_data = request.post_data
        auth = headers.get("authorization")
        auth_summary = summarize_token(auth)
        if auth_summary:
            self.last_auth_summary = auth_summary

        redacted_headers = {k: redact_header_value(k, v) for k, v in headers.items()}
        event = {
            "ts": now(),
            "kind": "request",
            "method": method,
            "url": url,
            "headers": redacted_headers,
            "auth_summary": auth_summary,
            "post_data": safe_json_parse(post_data),
        }
        self.append_event(event, api=True)

        if "/exemption" in url:
            log(f"API REQUEST {method} {url}")
            if auth_summary:
                exp = auth_summary.get("exp_utc", "?")
                log(f"  auth token seen: {auth_summary.get('prefix')}... expires={exp}")
            if post_data:
                log(f"  body: {post_data}")

    async def on_response(self, response: Response) -> None:
        url = response.url
        is_api = url.startswith(self.api_prefix) or "api.dfbnet.org" in url
        if not is_api:
            return

        body: Any = None
        body_note = None
        content_type = response.headers.get("content-type", "")
        if response.request.method != "OPTIONS":
            try:
                if "application/json" in content_type:
                    body = await response.json()
                elif "/exemption" in url:
                    text = await response.text()
                    body = safe_json_parse(text)
            except Exception as e:
                body_note = f"could not read body: {type(e).__name__}: {e}"

        event = {
            "ts": now(),
            "kind": "response",
            "method": response.request.method,
            "url": url,
            "status": response.status,
            "status_text": response.status_text,
            "headers": {k: redact_header_value(k, v) for k, v in response.headers.items()},
            "body": body,
            "body_note": body_note,
        }
        self.append_event(event, api=True)

        if "/exemption" in url:
            log(f"API RESPONSE {response.request.method} {response.status} {url}")
            if body is not None:
                preview = json.dumps(body, ensure_ascii=False)[:1000]
                log(f"  response body preview: {preview}")
            if body_note:
                log(f"  {body_note}")


async def auto_login(page: Page, login_id: str, password: str) -> bool:
    """Best-effort Keycloak login. Never logs credentials."""
    log("Auto-login enabled: waiting for DFBNet/Keycloak login form.")
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
    except Exception:
        pass

    email_selectors = [
        "input#username",
        "input[name='username']",
        "input[name='email']",
        "input[type='email']",
        "input[autocomplete='username']",
        "input[type='text']",
    ]
    password_selectors = [
        "input#password",
        "input[name='password']",
        "input[type='password']",
        "input[autocomplete='current-password']",
    ]
    submit_selectors = [
        "input#kc-login",
        "button#kc-login",
        "input[type='submit']",
        "button[type='submit']",
        "button:has-text('Anmelden')",
        "button:has-text('Einloggen')",
        "button:has-text('Log in')",
        "button:has-text('Sign in')",
    ]

    # Some apps first redirect asynchronously from frontend to auth.
    for _ in range(30):
        if "auth.dfbnet.org" in page.url or await _first_visible(page, email_selectors + password_selectors):
            break
        await page.wait_for_timeout(1000)

    email_sel = await _first_visible(page, email_selectors)
    pass_sel = await _first_visible(page, password_selectors)

    if not email_sel or not pass_sel:
        log(f"Auto-login could not find username/password fields on {page.url}")
        await _write_login_debug(page)
        return False

    log(f"Auto-login found login form on {page.url}; filling credentials from env (not logged).")
    await page.fill(email_sel, login_id)
    await page.fill(pass_sel, password)

    submit_sel = await _first_visible(page, submit_selectors)
    if submit_sel:
        await page.click(submit_sel)
    else:
        await page.press(pass_sel, "Enter")

    try:
        await page.wait_for_url(lambda url: "sria.dfbnet.org" in url, timeout=30000)
    except Exception:
        # Keycloak can stay on auth URL briefly while app bootstraps; continue and let token detection decide.
        pass

    for _ in range(30):
        try:
            token_present = await page.evaluate("() => !!sessionStorage.getItem('access_token')")
        except Exception:
            token_present = False
        if token_present:
            log("Auto-login succeeded: access_token found in sessionStorage.")
            return True
        if "sria.dfbnet.org" in page.url and "/login" not in page.url:
            # Give frontend a little more time to populate tokens.
            await page.wait_for_timeout(1000)
        else:
            await page.wait_for_timeout(1000)

    log(f"Auto-login did not observe access_token after submit. Current URL: {page.url}")
    await _write_login_debug(page)
    return False


async def _first_visible(page: Page, selectors: list[str]) -> str | None:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() and await loc.is_visible(timeout=500):
                return sel
        except Exception:
            continue
    return None


async def _write_login_debug(page: Page) -> None:
    try:
        html = await page.content()
        path = Path("/tmp/dfbnet-login-debug.html")
        path.write_text(html[:200000], encoding="utf-8")
        log(f"Wrote login debug HTML to {path}")
    except Exception as e:
        log(f"Could not write login debug HTML: {type(e).__name__}: {e}")


async def dump_browser_storage(context, page, out_dir: Path) -> None:
    log("Saving Playwright storage_state.json (sensitive; keep local, chmod 600).")
    storage_path = out_dir / "storage_state.json"
    await context.storage_state(path=str(storage_path))
    try:
        os.chmod(storage_path, 0o600)
    except Exception:
        pass

    # Debug keys only; values redacted/truncated.
    try:
        snapshot = await page.evaluate(
            """() => {
                const summarize = (storage) => {
                    const out = [];
                    for (let i = 0; i < storage.length; i++) {
                        const key = storage.key(i);
                        const val = storage.getItem(key) || '';
                        out.push({
                          key,
                          length: val.length,
                          looks_like_jwt: /^[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+$/.test(val),
                          preview: val.slice(0, 80)
                        });
                    }
                    return out;
                };
                return {
                  url: location.href,
                  localStorage: summarize(localStorage),
                  sessionStorage: summarize(sessionStorage),
                };
            }"""
        )
        (out_dir / "browser-storage-keys.json").write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")

        # Sensitive token export for the MCP/CLI. Do not share this file.
        token_state = await page.evaluate(
            """() => {
                const keys = ['access_token', 'refresh_token', 'id_token', 'access_token_stored_at', 'expires_at', 'id_token_expires_at', 'session_state'];
                const out = { exported_at: Date.now(), origin: location.origin };
                for (const key of keys) {
                    const val = sessionStorage.getItem(key);
                    if (val !== null) out[key] = val;
                }
                return out;
            }"""
        )
        token_path = out_dir / "token_state.json"
        token_path.write_text(json.dumps(token_state, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            os.chmod(token_path, 0o600)
        except Exception:
            pass
    except Exception as e:
        log(f"Could not dump browser storage/token state: {type(e).__name__}: {e}")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Observe DFBNet SRIA login and exemption API traffic.")
    parser.add_argument("--start-url", default=DEFAULT_START_URL)
    parser.add_argument("--api-prefix", default=DEFAULT_API_PREFIX)
    parser.add_argument("--out", default="./dfbnet_probe_out")
    parser.add_argument("--user-data-dir", default="./dfbnet_browser_profile")
    parser.add_argument("--browser", default="chromium", choices=["chromium", "firefox", "webkit"])
    parser.add_argument("--headless", action="store_true", help="Run browser headless. Use with --auto-login / env credentials.")
    parser.add_argument("--auto-login", action="store_true", help="Fill DFBNet login form from DFBNET_LOGIN_ID and DFBNET_PASSWORD.")
    parser.add_argument("--env-file", default=os.getenv("DFBNET_ENV_FILE", "~/.dfbnet_env"), help="Env file with DFBNET_LOGIN_ID/DFBNET_PASSWORD.")
    parser.add_argument("--slow-mo", type=int, default=0)
    parser.add_argument("--timeout-minutes", type=int, default=30)
    args = parser.parse_args()

    out_dir = Path(args.out).expanduser().resolve()
    user_data_dir = Path(args.user_data_dir).expanduser().resolve()
    env_file = Path(args.env_file).expanduser().resolve() if args.env_file else None
    if load_dotenv and env_file and env_file.exists():
        load_dotenv(env_file)
    login_id = os.getenv("DFBNET_LOGIN_ID") or os.getenv("DFBNET_USERNAME") or os.getenv("DFBNET_USER")
    password = os.getenv("DFBNET_PASSWORD")
    if args.auto_login and (not login_id or not password):
        raise SystemExit("--auto-login requires DFBNET_LOGIN_ID and DFBNET_PASSWORD in env or --env-file")
    recorder = Recorder(out_dir, args.api_prefix)

    log(f"Output dir: {out_dir}")
    log(f"Browser profile dir: {user_data_dir}")
    log("Starting headed browser. Log in manually. Then create/list a Freihalter in the UI.")
    log("Press Ctrl+C in this terminal when done; files are flushed continuously.")

    async with async_playwright() as p:
        browser_type = getattr(p, args.browser)
        context = await browser_type.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=args.headless,
            slow_mo=args.slow_mo,
            viewport={"width": 1440, "height": 1000},
            locale="de-DE",
            timezone_id="Europe/Berlin",
            args=["--disable-blink-features=AutomationControlled"] if args.browser == "chromium" else [],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        page.on("console", lambda msg: log(f"BROWSER CONSOLE {msg.type}: {safe_console_text(msg.text)}"))
        page.on("pageerror", lambda exc: log(f"BROWSER PAGE ERROR: {exc}"))
        context.on("request", lambda request: asyncio.create_task(recorder.on_request(request)))
        context.on("response", lambda response: asyncio.create_task(recorder.on_response(response)))

        await page.goto(args.start_url, wait_until="domcontentloaded")
        if args.auto_login:
            ok = await auto_login(page, login_id or "", password or "")
            if not ok:
                log("Auto-login failed or needs manual intervention. If this is due to 2FA/Captcha, run headed on a machine with GUI.")
            await dump_browser_storage(context, page, out_dir)
            recorder.flush()
        deadline = time.time() + args.timeout_minutes * 60
        try:
            while time.time() < deadline:
                await asyncio.sleep(10)
                await dump_browser_storage(context, page, out_dir)
                recorder.flush()
                if recorder.last_auth_summary:
                    log(f"Still running. Last auth expires: {recorder.last_auth_summary.get('exp_utc', '?')}")
                else:
                    log("Still running. No DFBNet API Authorization token observed yet.")
        except KeyboardInterrupt:
            log("Ctrl+C received, finishing.")
        finally:
            await dump_browser_storage(context, page, out_dir)
            recorder.flush()
            await context.close()

    log("Done.")
    log(f"Send me these files if you want me to continue implementing the MCP:")
    log(f"  {out_dir / 'api-events.json'}")
    log(f"  {out_dir / 'last-auth-summary.json'}")
    log(f"  {out_dir / 'browser-storage-keys.json'}")
    log("For the MCP/CLI on your own machine, set DFBNET_TOKEN_STATE to:")
    log(f"  {out_dir / 'token_state.json'}")
    log("Do NOT send token_state.json or storage_state.json unless you intentionally want to share live session credentials.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        raise SystemExit(130)
