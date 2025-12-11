import os
import json
import asyncio
import hashlib
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List

import yaml
from playwright.async_api import async_playwright, ViewportSize
from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
import aiohttp

# Ympäristömuuttujat
STATE_FILE = os.getenv("STATE_FILE", "tm_state.json")
CONFIG_FILE = os.getenv("CONFIG_FILE", "config/urls.yaml")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK", "")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "60"))
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
HEARTBEAT_FILE = os.getenv("HEARTBEAT_FILE", "/data/heartbeat.txt")

def log(level: str, msg: str) -> None:
    """Print log message with timestamp."""
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")

def update_heartbeat() -> None:
    """Write current timestamp to heartbeat file for health checks."""
    try:
        timestamp = datetime.now(UTC).isoformat()
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(timestamp)
    except Exception as e:
        log("WARN", f"Failed to update heartbeat: {e}")

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
        if "url" not in it:
            raise ValueError("Jokaisella rivillä pitää olla: url")

        # Support both old and new format
        # Old format: search_text + mode
        # New format: search_text_disappears and/or search_text_appears
        has_old_format = "search_text" in it and "mode" in it
        has_new_format = "search_text_disappears" in it or "search_text_appears" in it

        if not has_old_format and not has_new_format:
            raise ValueError("Käytä joko: (search_text + mode) TAI (search_text_disappears/search_text_appears)")

        if has_old_format:
            # Convert old format to new format internally
            if it["mode"] not in ("appears", "disappears"):
                raise ValueError("mode pitää olla 'appears' tai 'disappears'")

            search_text = it["search_text"]
            search_list = search_text if isinstance(search_text, list) else [search_text]

            if it["mode"] == "disappears":
                it["search_text_disappears"] = search_list
                it["search_text_appears"] = []
            else:
                it["search_text_disappears"] = []
                it["search_text_appears"] = search_list
        else:
            # Normalize new format to lists
            if "search_text_disappears" in it:
                txt = it["search_text_disappears"]
                it["search_text_disappears"] = txt if isinstance(txt, list) else [txt]
            else:
                it["search_text_disappears"] = []

            if "search_text_appears" in it:
                txt = it["search_text_appears"]
                it["search_text_appears"] = txt if isinstance(txt, list) else [txt]
            else:
                it["search_text_appears"] = []

        # At least one condition must be specified
        if not it["search_text_disappears"] and not it["search_text_appears"]:
            raise ValueError("Vähintään yksi search_text_disappears tai search_text_appears vaaditaan")

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

async def check_one(pw, item: Dict[str, Any], retry_count: int = 0) -> Optional[Dict[str, Any]]:
    """Check a single URL with retry logic for browser crashes."""
    url = item["url"]
    max_retries = 3

    browser = None
    context = None

    try:
        chromium = pw.chromium

        # Enhanced browser launch args for stability
        launch_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu",
            "--single-process",  # More stable in containers
        ]

        browser = await chromium.launch(
            headless=HEADLESS,
            args=launch_args,
            timeout=60000  # 60s timeout for browser launch
        )

        viewport: ViewportSize = {"width": 1280, "height": 2200}
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"),
            viewport=viewport,
            java_script_enabled=True,
        )
        page = await context.new_page()

        await page.goto(url, wait_until="networkidle", timeout=45000)
        await click_cookie_banners(page)
        await page.wait_for_timeout(2500)

        snapshot = await get_text_snapshot(page)

        # Check which texts from each list are present
        disappears_list = item.get("search_text_disappears", [])
        appears_list = item.get("search_text_appears", [])

        found_disappears = [txt for txt in disappears_list if txt in snapshot]
        found_appears = [txt for txt in appears_list if txt in snapshot]

        # Include a text snippet for debugging (first 1000 chars)
        snippet = snapshot[:1000] if len(snapshot) > 1000 else snapshot

        # Ota kuvakaappaus vain muutostilanteessa (tehdään kutsuvassa kohdassa)
        return {
            "url": url,
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            "found_disappears": found_disappears,
            "found_appears": found_appears,
            "hash": hsh(snapshot),
            "snippet": snippet,
        }
    except PlaywrightError as e:
        # Handle browser crashes and target closed errors
        error_msg = str(e)
        if "Target page, context or browser has been closed" in error_msg or "SIGTRAP" in error_msg:
            if retry_count < max_retries:
                wait_time = 2 ** retry_count  # Exponential backoff: 1s, 2s, 4s
                log("WARN", f"{url}: Browser crash detected (retry {retry_count + 1}/{max_retries}), waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await check_one(pw, item, retry_count + 1)
            else:
                log("ERROR", f"{url}: Browser crashed after {max_retries} retries: {e}")
                raise
        else:
            raise
    finally:
        # Ensure cleanup even if errors occur
        try:
            if context:
                await context.close()
        except Exception as e:
            log("WARN", f"Error closing context: {e}")

        try:
            if browser:
                await browser.close()
        except Exception as e:
            log("WARN", f"Error closing browser: {e}")

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
                disappears_list = item.get("search_text_disappears", [])
                appears_list = item.get("search_text_appears", [])
                note = item.get("note", "")
                try:
                    res = await check_one(pw, item)
                    if not res:
                        continue
                    prev = state.get(url)

                    curr_found_disappears = res["found_disappears"]
                    curr_found_appears = res["found_appears"]

                    # Ensimmäinen kierros: vain init
                    if prev is None:
                        log("INIT", f"{url} -> disappears:{curr_found_disappears}, appears:{curr_found_appears}")
                        state[url] = res
                        save_state(state)
                        continue

                    prev_found_disappears = prev.get("found_disappears", [])
                    prev_found_appears = prev.get("found_appears", [])

                    # Check if conditions have changed
                    changed = (prev_found_disappears != curr_found_disappears or
                              prev_found_appears != curr_found_appears)

                    if changed:
                        # Alert logic:
                        # - ALL disappears texts must be gone (were present, now all gone)
                        # - At least ONE appears text must be present (was not present, now at least one is there)
                        alert = False

                        # Check disappears condition (if specified)
                        disappears_satisfied = True
                        if disappears_list:
                            # Were any disappears texts present before? Are they all gone now?
                            disappears_satisfied = (len(prev_found_disappears) > 0 and
                                                  len(curr_found_disappears) == 0)

                        # Check appears condition (if specified)
                        appears_satisfied = True
                        if appears_list:
                            # Were all appears texts absent before? Is at least one present now?
                            appears_satisfied = (len(prev_found_appears) == 0 and
                                               len(curr_found_appears) > 0)

                        # Alert if both conditions are satisfied
                        # (If only one type is specified, the other is always satisfied)
                        alert = disappears_satisfied and appears_satisfied
                        # Ota muutostilanteessa myös kuvakaappaus talteen
                        if alert:
                            os.makedirs("/data/screens", exist_ok=True)
                            screenshot_path = f"/data/screens/{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}Z.png"
                            # Ota pikakuvakaappaus erillisellä selainsessiolla:
                            screenshot_browser = None
                            screenshot_context = None
                            try:
                                # Use same stable browser args
                                screenshot_args = [
                                    "--no-sandbox",
                                    "--disable-setuid-sandbox",
                                    "--disable-dev-shm-usage",
                                    "--disable-accelerated-2d-canvas",
                                    "--no-first-run",
                                    "--no-zygote",
                                    "--disable-gpu",
                                    "--single-process",
                                ]
                                screenshot_browser = await pw.chromium.launch(
                                    headless=True,
                                    args=screenshot_args,
                                    timeout=60000
                                )
                                screenshot_viewport: ViewportSize = {"width": 1280, "height": 2200}
                                screenshot_context = await screenshot_browser.new_context(viewport=screenshot_viewport)
                                page = await screenshot_context.new_page()
                                await page.goto(url, wait_until="networkidle", timeout=45000)
                                await page.screenshot(path=screenshot_path, full_page=True)
                                log("INFO", f"Screenshot saved to {screenshot_path}")
                            except (OSError, asyncio.TimeoutError, PlaywrightTimeoutError, PlaywrightError) as se:
                                log("WARN", f"Screenshot failed: {se}")
                            finally:
                                # Ensure cleanup
                                try:
                                    if screenshot_context:
                                        await screenshot_context.close()
                                except Exception as e:
                                    log("WARN", f"Error closing screenshot context: {e}")
                                try:
                                    if screenshot_browser:
                                        await screenshot_browser.close()
                                except Exception as e:
                                    log("WARN", f"Error closing screenshot browser: {e}")

                        # Viesti
                        if alert:
                            # Build status message
                            status_parts = []

                            if disappears_list and len(curr_found_disappears) == 0:
                                disappeared_texts = ", ".join(f"'{t}'" for t in disappears_list)
                                status_parts.append(f"✅ {disappeared_texts} kadonnut")

                            if appears_list and len(curr_found_appears) > 0:
                                appeared_texts = ", ".join(f"'{t}'" for t in curr_found_appears)
                                status_parts.append(f"✅ {appeared_texts} ilmestynyt")

                            if status_parts:
                                status = "🎉 " + " JA ".join(status_parts) + " → mahdollisesti lippuja!"
                            else:
                                status = "🔔 Muutos havaittu."

                            # Include snippet of current page content for debugging
                            current_snippet = res.get("snippet", "N/A")

                            msg = (
                                f"{status}\n\n"
                                f"🎟️ {note}\n"
                                f"🔗 {url}\n\n"
                                f"📄 Current page text (first 1000 chars):\n{current_snippet}"
                            )
                            log("ALERT", msg.replace("\n", " "))
                            await slack_post(msg)

                        # Päivitä tila
                        state[url] = res
                        save_state(state)

                except PlaywrightError as e:
                    error_msg = str(e)
                    # More detailed logging for browser crashes
                    if "Target page, context or browser has been closed" in error_msg or "SIGTRAP" in error_msg:
                        log("ERROR", f"{url}: Browser crash detected (possibly due to website's anti-bot detection or resource constraints)")
                    else:
                        log("ERROR", f"{url}: Playwright error: {e}")
                except (asyncio.TimeoutError, PlaywrightTimeoutError) as e:
                    log("ERROR", f"{url}: Timeout error: {e}")
                except (OSError, aiohttp.ClientError) as e:
                    log("ERROR", f"{url}: Network/OS error: {e}")
                except Exception as e:
                    log("ERROR", f"{url}: Unexpected error: {type(e).__name__}: {e}")

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

            # Update heartbeat for health checks
            update_heartbeat()

            await asyncio.sleep(POLL_SECONDS)

if __name__ == "__main__":
    try:
        asyncio.run(monitor_loop())
    except KeyboardInterrupt:
        log("STOP", "Exiting.")
