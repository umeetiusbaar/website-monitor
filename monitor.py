import os
import json
import asyncio
import hashlib
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List

import yaml
from playwright.async_api import async_playwright, ViewportSize
import aiohttp

# Ympäristömuuttujat
STATE_FILE = os.getenv("STATE_FILE", "tm_state.json")
CONFIG_FILE = os.getenv("CONFIG_FILE", "config/urls.yaml")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK", "")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "60"))
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

def log(level: str, msg: str) -> None:
    """Print log message with timestamp."""
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")

# Evästepopuppien napeista kokeiltavat tekstit
COOKIE_BUTTON_CANDIDATES = [
    "Accept All", "Accept all", "Accept all cookies", "Accept Cookies",
    "Hyväksy kaikki", "Salli kaikki", "Agree", "I Accept", "OK", "Got it",
]

def load_state() -> Dict[str, Any]:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_state(state: Dict[str, Any]) -> None:
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)

def load_config() -> List[Dict[str, Any]]:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    items = cfg.get("urls", [])
    assert isinstance(items, list) and items, "config/urls.yaml: 'urls' pitää olla lista, jossa on vähintään yksi kohde."
    for it in items:
        if "url" not in it or "search_text" not in it or "mode" not in it:
            raise ValueError("Jokaisella rivillä pitää olla: url, search_text, mode (appears|disappears)")
        if it["mode"] not in ("appears", "disappears"):
            raise ValueError("mode pitää olla 'appears' tai 'disappears'")
    return items

async def slack_post(text: str):
    if not SLACK_WEBHOOK:
        log("INFO", f"SLACK_WEBHOOK not set; printing instead:\n{text}")
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(SLACK_WEBHOOK, json={"text": text}, timeout=20) as r:
                if r.status >= 300:
                    body = await r.text()
                    log("WARN", f"Slack HTTP {r.status}: {body}")
                else:
                    log("INFO", f"Slack message sent successfully (HTTP {r.status})")
    except Exception as e:
        log("ERROR", f"Failed to send Slack message: {e}")

async def click_cookie_banners(page):
    # Yritetään useita kertoja: osa sivuista lataa bannerin viiveellä
    for _ in range(3):
        for label in COOKIE_BUTTON_CANDIDATES:
            # noinspection PyBroadException
            try:
                btn = await page.get_by_role("button", name=label).first
                if await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(400)
            except Exception:  # Intentionally broad - UI interactions are unpredictable
                pass
            # noinspection PyBroadException
            try:
                el = page.get_by_text(label, exact=False).first
                if await el.is_visible():
                    await el.click()
                    await page.wait_for_timeout(400)
            except Exception:  # Intentionally broad - UI interactions are unpredictable
                pass
        await page.wait_for_timeout(400)

async def get_text_snapshot(page) -> str:
    txt = await page.locator("body").inner_text()
    return " ".join(txt.split())

def hsh(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

async def check_one(pw, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    url = item["url"]
    chromium = pw.chromium
    browser = await chromium.launch(headless=HEADLESS, args=["--no-sandbox"])
    viewport: ViewportSize = {"width": 1280, "height": 2200}
    context = await browser.new_context(
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"),
        viewport=viewport,
        java_script_enabled=True,
    )
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="networkidle", timeout=45000)
        await click_cookie_banners(page)
        await page.wait_for_timeout(2500)

        snapshot = await get_text_snapshot(page)
        contains = item["search_text"] in snapshot

        # Ota kuvakaappaus vain muutostilanteessa (tehdään kutsuvassa kohdassa)
        return {
            "url": url,
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            "contains": contains,
            "hash": hsh(snapshot),
        }
    finally:
        await context.close()
        await browser.close()

async def monitor_loop():
    config = load_config()
    state = load_state()
    log("START", f"{len(config)} kohdetta, väli {POLL_SECONDS}s, headless={HEADLESS}.")

    # Log all URLs being monitored
    for idx, item in enumerate(config, 1):
        log("START", f"  {idx}. {item.get('note', 'No note')} - {item['url'][:80]}...")

    # Send startup notification
    url_list = "\n".join([f"{i}. {item.get('note', item['url'][:50])}" for i, item in enumerate(config, 1)])
    startup_msg = (
        f"🚀 Website Monitor Started\n\n"
        f"Monitoring {len(config)} URLs:\n{url_list}\n\n"
        f"Poll interval: {POLL_SECONDS}s\n"
        f"Started at: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    await slack_post(startup_msg)

    # Track last ping time
    last_ping_time = datetime.now(UTC)
    ping_interval_hours = 12

    async with async_playwright() as pw:
        while True:
            for item in config:
                url = item["url"]
                search_text = item["search_text"]
                mode = item["mode"]
                note = item.get("note", "")
                try:
                    log("CHECK", f"Checking {url}...")
                    res = await check_one(pw, item)
                    if not res:
                        continue
                    prev = state.get(url)
                    prev_contains = prev["contains"] if prev else None
                    curr_contains = res["contains"]

                    # Ensimmäinen kierros: vain init
                    if prev_contains is None:
                        log("INIT", f"{url} -> contains '{search_text}': {curr_contains} ({mode})")
                        state[url] = res
                        save_state(state)
                        continue

                    changed = (prev_contains != curr_contains)
                    if changed:
                        # Tulkinta: milloin hälytetään
                        alert = (
                                (mode == "disappears" and prev_contains is True  and curr_contains is False) or
                                (mode == "appears"    and prev_contains is False and curr_contains is True)
                        )
                        # Ota muutostilanteessa myös kuvakaappaus talteen
                        if alert:
                            os.makedirs("/data/screens", exist_ok=True)
                            screenshot_path = f"/data/screens/{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}Z.png"
                            # Ota pikakuvakaappaus erillisellä selainsessiolla:
                            try:
                                browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
                                screenshot_viewport: ViewportSize = {"width": 1280, "height": 2200}
                                context = await browser.new_context(viewport=screenshot_viewport)
                                page = await context.new_page()
                                await page.goto(url, wait_until="networkidle", timeout=45000)
                                await page.screenshot(path=screenshot_path, full_page=True)
                                await context.close()
                                await browser.close()
                                log("INFO", f"Screenshot saved to {screenshot_path}")
                            except (OSError, asyncio.TimeoutError) as se:
                                log("WARN", f"Screenshot failed: {se}")

                        # Viesti
                        if alert:
                            if mode == "disappears" and prev_contains and not curr_contains:
                                status = f"🎉 **'{search_text}' EI enää näy** → mahdollisesti lippuja!"
                            elif mode == "appears" and (not prev_contains) and curr_contains:
                                status = f"⚠️ **'{search_text}' ilmestyi sivulle.**"
                            else:
                                status = f"🔔 Muutos havaittu (mode={mode})."

                            msg = (
                                f"{status}\n\n"
                                f"🎟️ {note}\n"
                                f"🔗 {url}"
                            )
                            log("ALERT", msg.replace("\n", " "))
                            await slack_post(msg)

                        # Päivitä tila
                        state[url] = res
                        save_state(state)

                except (asyncio.TimeoutError, OSError, aiohttp.ClientError) as e:
                    log("ERROR", f"{url}: {e}")

            # Check if it's time to send a ping message
            current_time = datetime.now(UTC)
            hours_since_last_ping = (current_time - last_ping_time).total_seconds() / 3600

            if hours_since_last_ping >= ping_interval_hours:
                url_list = "\n".join([f"{i}. {item.get('note', item['url'][:50])}" for i, item in enumerate(config, 1)])
                ping_msg = (
                    f"✅ Monitor Status: Running\n\n"
                    f"Monitoring {len(config)} URLs:\n{url_list}\n\n"
                    f"Last check: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                    f"Uptime: {hours_since_last_ping:.1f} hours"
                )
                await slack_post(ping_msg)
                log("PING", "Sent periodic status update to Slack")
                last_ping_time = current_time

            await asyncio.sleep(POLL_SECONDS)

if __name__ == "__main__":
    try:
        asyncio.run(monitor_loop())
    except KeyboardInterrupt:
        log("STOP", "Exiting.")
