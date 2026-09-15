"""Headless browser used by the FindFast application assistant."""

import os
import re
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


NAME = "Makondelela"
SURNAME = "Mutshinya"
EMAIL = "makondelelamaps@gmail.com"
CELLPHONE = "0795171404"
CV_FILE_PATH = Path(__file__).parent / "Makondelela_Mutshinya_FlowCV_Resume_2026-06-23.pdf"


class AssistantBrowser:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def _ensure_page(self):
        if self.page and not self.page.is_closed():
            return self.page
        if self.context is None:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            self.context = self.browser.new_context(accept_downloads=False)
        self.page = self.context.new_page()
        return self.page

    def open(self, url):
        page = self._ensure_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return self.status()

    def reset(self):
        if self.page and not self.page.is_closed():
            self.page.goto("about:blank", wait_until="commit", timeout=10000)
            return True
        return False

    def status(self):
        if not self.page or self.page.is_closed():
            return {"running": False, "url": None}
        return {"running": True, "url": self.page.url}

    def fill(self):
        page = self._ensure_page()
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        values = {
            "first name": NAME,
            "full name": NAME,
            "surname": SURNAME,
            "last name": SURNAME,
            "email": EMAIL,
            "e-mail": EMAIL,
            "cell": CELLPHONE,
            "mobile": CELLPHONE,
        }
        filled = []
        skipped = []
        fields = page.locator("input, textarea, select")
        for index in range(fields.count()):
            field = fields.nth(index)
            field_type = (field.get_attribute("type") or "").lower()
            if field_type in {"hidden", "submit", "button", "reset", "file"}:
                continue
            label = self._label_for(field).lower()
            match = next((value for key, value in values.items() if re.search(rf"\b{re.escape(key)}\b", label)), None)
            if match is None:
                skipped.append(label or field.get_attribute("name") or field.get_attribute("id") or "unlabeled field")
                continue
            try:
                if field.evaluate("el => el.tagName.toLowerCase()") == "select":
                    field.select_option(label=match)
                else:
                    field.fill(match)
                filled.append(label)
            except Exception:
                skipped.append(label or "unavailable field")

        return {"filled": filled, "skipped": skipped, "url": page.url}

    @staticmethod
    def _label_for(field):
        field_id = field.get_attribute("id")
        label = field.evaluate(
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
            label = field.get_attribute("name") or field_id or ""
        return label.strip()

    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None


assistant_browser = AssistantBrowser()