"""Headless browser used by the FindFast application assistant."""

import asyncio
import base64
import re
import threading
from pathlib import Path

from playwright.async_api import async_playwright


NAME = "Makondelela"
SURNAME = "Mutshinya"
EMAIL = "makondelelamaps@gmail.com"
CELLPHONE = "0795171404"
CURRENT_POSITION = "Software Engineer"
CURRENT_EMPLOYER = "Lexis Nexis"
CURRENT_CITY = "Johannesburg"
CV_FILE_PATH = Path(__file__).parent / "Makondelela_Mutshinya_FlowCV_Resume_2026-06-23.pdf"

STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)

# Patches the most common signals bot-detection scripts check for on a
# freshly-launched headless Chromium (navigator.webdriver, missing
# chrome.runtime/plugins, permissions.query quirks). Runs before any page
# script, on every page in the context.
STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = window.chrome || { runtime: {} };
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters)
);
"""


class AssistantBrowser:
    """Expose a synchronous Flask-friendly facade over async Playwright."""

    def __init__(self):
        self.loop = None
        self.thread = None
        self.ready = threading.Event()
        self.start_lock = threading.Lock()

    def _ensure_loop(self):
        if self.thread and self.thread.is_alive():
            return
        with self.start_lock:
            if self.thread and self.thread.is_alive():
                return
            self.ready.clear()
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            self.ready.wait(timeout=10)

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.ready.set()
        self.loop.run_forever()

    def _run(self, coroutine):
        self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        return future.result(timeout=45)

    async def _ensure_page(self):
        if getattr(self, "page", None) and not self.page.is_closed():
            return self.page
        if not getattr(self, "context", None):
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                channel="chromium",
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            self.context = await self.browser.new_context(
                accept_downloads=False,
                user_agent=STEALTH_USER_AGENT,
            )
            self.context.set_default_timeout(10000)
            await self.context.add_init_script(STEALTH_INIT_SCRIPT)
        self.page = await self.context.new_page()
        # Desktop-ish landscape viewport so the screenshot's aspect ratio
        # matches the wide preview overlay (avoids letterboxing) and forms
        # render in their normal desktop layout rather than mobile.
        await self.page.set_viewport_size({"width": 1280, "height": 800})
        return self.page

    def open(self, url):
        return self._run(self._open(url))

    async def _open(self, url):
        page = await self._ensure_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return await self._status()

    def reset(self):
        return self._run(self._reset())

    async def _reset(self):
        if getattr(self, "page", None) and not self.page.is_closed():
            await self.page.goto("about:blank", wait_until="commit", timeout=10000)
            return True
        return False

    def status(self):
        return self._run(self._status())

    async def _status(self):
        if not getattr(self, "page", None) or self.page.is_closed():
            return {"running": False, "url": None}
        return {"running": True, "url": self.page.url}

    def screenshot(self):
        return self._run(self._screenshot())

    async def _screenshot(self):
        if not getattr(self, "page", None) or self.page.is_closed():
            return {"running": False, "image": None}
        image_bytes = await self.page.screenshot(type="jpeg", quality=60)
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return {
            "running": True,
            "url": self.page.url,
            "image": f"data:image/jpeg;base64,{encoded}",
        }

    async def _active_page(self):
        if not getattr(self, "page", None) or self.page.is_closed():
            return None
        return self.page

    def click(self, x, y):
        return self._run(self._click(x, y))

    async def _click(self, x, y):
        page = await self._active_page()
        if page is None:
            return {"running": False}
        await page.mouse.click(x, y)
        return await self._status()

    def press_key(self, key):
        return self._run(self._press_key(key))

    async def _press_key(self, key):
        page = await self._active_page()
        if page is None or not key:
            return {"running": False}
        await page.keyboard.press(key)
        return await self._status()

    def scroll(self, delta_x, delta_y):
        return self._run(self._scroll(delta_x, delta_y))

    async def _scroll(self, delta_x, delta_y):
        page = await self._active_page()
        if page is None:
            return {"running": False}
        await page.mouse.wheel(delta_x, delta_y)
        return await self._status()

    def fill(self):
        return self._run(self._fill())

    async def _fill(self):
        page = await self._ensure_page()
        await page.wait_for_load_state("domcontentloaded", timeout=10000)
        values = {
            "first name": NAME,
            "full name": NAME,
            "surname": SURNAME,
            "last name": SURNAME,
            "email": EMAIL,
            "e-mail": EMAIL,
            "cell": CELLPHONE,
            "mobile": CELLPHONE,
            "job title": CURRENT_POSITION,
            "company name": CURRENT_EMPLOYER,
            "city": CURRENT_CITY,
        }
        filled = []
        skipped = []
        fields = page.locator("input, textarea, select")
        for index in range(await fields.count()):
            field = fields.nth(index)
            field_type = (await field.get_attribute("type") or "").lower()
            if field_type in {"hidden", "submit", "button", "reset", "file"}:
                continue
            label = (await self._label_for(field)).lower()
            match = next(
                (value for key, value in values.items() if re.search(rf"\b{re.escape(key)}\b", label)),
                None,
            )
            if match is None:
                skipped.append(label or await field.get_attribute("name") or await field.get_attribute("id") or "unlabeled field")
                continue
            try:
                if await field.evaluate("el => el.tagName.toLowerCase()") == "select":
                    await field.select_option(label=match)
                else:
                    await field.fill(match)
                filled.append(label)
            except Exception:
                skipped.append(label or "unavailable field")

        return {"filled": filled, "skipped": skipped, "url": page.url}

    @staticmethod
    async def _label_for(field):
        field_id = await field.get_attribute("id")
        label = await field.evaluate(
            """
            el => {
                const linked = el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
                if (linked && linked.innerText.trim()) return linked.innerText.trim();
                const parentLabel = el.closest('label');
                if (parentLabel && parentLabel.innerText.trim()) return parentLabel.innerText.trim();
                return el.getAttribute('aria-label') || el.getAttribute('placeholder') || '';
            }
            """
        )
        if not label:
            label = await field.get_attribute("name") or field_id or ""
        return label.strip()


assistant_browser = AssistantBrowser()