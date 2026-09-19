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

    @staticmethod
    def profile_to_fill_values(profile=None, user=None):
        """Build the fill values for a target application form from the saved profile.

        The user profile lives in Firebase, while the browser-side assistant page
        only knows the authenticated session user. This helper normalizes both
        sources into the same dictionary that the existing HTML/form matcher
        already understands.
        """
        personal = (profile or {}).get('personal') or {}
        professional = (profile or {}).get('professional_profile') or {}

        user_email = (user or {}).get('email') or ''
        user_name = (user or {}).get('name') or ''

        first_name = personal.get('first_name') or personal.get('preferred_name') or ''
        last_name = personal.get('last_name') or ''

        if not first_name and user_name:
            parts = user_name.strip().split()
            first_name = parts[0] if parts else ''
            last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

        full_name = ' '.join(part for part in [first_name, last_name] if part).strip()
        if not full_name and user_name:
            full_name = user_name.strip()

        profile_values = {
            'first name': first_name or NAME,
            'full name': full_name or NAME,
            'surname': last_name or SURNAME,
            'last name': last_name or SURNAME,
            'email': personal.get('email') or user_email or EMAIL,
            'e-mail': personal.get('email') or user_email or EMAIL,
            'cell': personal.get('contact_number') or CELLPHONE,
            'mobile': personal.get('contact_number') or CELLPHONE,
            'job title': professional.get('current_job_title') or CURRENT_POSITION,
            'company name': professional.get('current_company') or CURRENT_EMPLOYER,
            'city': personal.get('city') or CURRENT_CITY,
        }

        if not profile_values['first name'] and NAME:
            profile_values['first name'] = NAME
        if not profile_values['full name'] and NAME:
            profile_values['full name'] = NAME
        if not profile_values['surname'] and SURNAME:
            profile_values['surname'] = SURNAME
        if not profile_values['last name'] and SURNAME:
            profile_values['last name'] = SURNAME
        if not profile_values['email'] and EMAIL:
            profile_values['email'] = EMAIL
        if not profile_values['e-mail'] and EMAIL:
            profile_values['e-mail'] = EMAIL
        if not profile_values['cell'] and CELLPHONE:
            profile_values['cell'] = CELLPHONE
        if not profile_values['mobile'] and CELLPHONE:
            profile_values['mobile'] = CELLPHONE
        if not profile_values['job title'] and CURRENT_POSITION:
            profile_values['job title'] = CURRENT_POSITION
        if not profile_values['company name'] and CURRENT_EMPLOYER:
            profile_values['company name'] = CURRENT_EMPLOYER
        if not profile_values['city'] and CURRENT_CITY:
            profile_values['city'] = CURRENT_CITY

        return profile_values

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
        dropdown = await page.evaluate(
            """
            ([x, y]) => {
                const element = document.elementFromPoint(x, y);
                if (!element || element.tagName.toLowerCase() !== 'select') return null;
                return {
                    id: element.id || '',
                    name: element.name || '',
                    options: Array.from(element.options).map((option, index) => ({
                        index,
                        label: option.text.trim(),
                        disabled: option.disabled,
                        selected: option.selected,
                    })),
                };
            }
            """,
            [x, y],
        )
        if dropdown:
            return {**await self._status(), "dropdown": dropdown}
        await page.mouse.click(x, y)
        return await self._status()

    def select_option(self, field_id='', field_name='', index=0):
        return self._run(self._select_option(field_id, field_name, index))

    async def _select_option(self, field_id, field_name, index):
        page = await self._active_page()
        if page is None:
            return {"running": False}
        selected = await page.evaluate(
            """
            ([fieldId, fieldName, optionIndex]) => {
                const selector = fieldId
                    ? `select#${CSS.escape(fieldId)}`
                    : `select[name="${CSS.escape(fieldName)}"]`;
                const element = document.querySelector(selector);
                if (!element || !element.options[optionIndex]) return null;
                const option = element.options[optionIndex];
                if (option.disabled) return null;
                element.selectedIndex = optionIndex;
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
                if (window.jQuery) window.jQuery(element).trigger('change');
                return option.text.trim();
            }
            """,
            [field_id, field_name, int(index)],
        )
        if selected is None:
            raise ValueError('Dropdown option is no longer available')
        return {**await self._status(), "selected": selected}

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

    def fill(self, profile=None, user=None):
        return self._run(self._fill(profile=profile, user=user))

    async def _fill(self, profile=None, user=None):
        page = await self._ensure_page()
        await page.wait_for_load_state("domcontentloaded", timeout=10000)
        values = self.profile_to_fill_values(profile=profile, user=user)
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