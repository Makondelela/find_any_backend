"""
Pnet Job Scraper - Data Roles (South Africa)
=============================================
Uses Playwright to render JavaScript and scrape job cards from Pnet.co.za.

Usage:
    pip install playwright beautifulsoup4
    playwright install chromium
    python indeed_scraper.py

Output: data_jobs_pnet.json
"""

import json
import logging
import sys
import io
import time
import random
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from search_config import DEFAULT_SEARCH_SLUGS

# ── UTF-8 safe logging ────────────────────────────────────────────────────────
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
if root_logger.handlers:
    root_logger.handlers.clear()
_handler = logging.StreamHandler(
    io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
)
_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
root_logger.addHandler(_handler)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL  = "https://www.pnet.co.za"
OUTPUT    = "data_jobs_pnet.json"
MAX_PAGES = 5
DELAY_MIN = 3.0
DELAY_MAX = 6.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def sleep():
    t = random.uniform(DELAY_MIN, DELAY_MAX)
    log.info(f"  Waiting {t:.1f}s ...")
    time.sleep(t)


def parse_cards(html: str, page=None) -> list[dict]:
    """Extract job data from rendered HTML using confirmed Pnet selectors."""
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    cards = soup.select('article[id^="job-item-"]')
    if not cards:
        cards = soup.select('[data-at="job-item"]')

    log.info(f"  Parsed {len(cards)} job cards from rendered HTML")

    for card in cards:
        try:
            raw_id = card.get("id", "")
            job_id = raw_id.replace("job-item-", "").strip()

            title_el = card.select_one('[data-at="job-item-title"]')
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            link = card.select_one('a[data-at="job-item-title"]') or card.select_one('a[href]')
            href = link.get("href", "") if link else ""
            url = href if href.startswith("http") else f"{BASE_URL}{href}"

            company_el = card.select_one('[data-at="job-item-company-name"]')
            company = company_el.get_text(strip=True) if company_el else ""

            location_el = card.select_one('[data-at="job-item-location"]')
            location = location_el.get_text(strip=True) if location_el else ""

            summary_el = card.select_one('[data-at="jobcard-content"]')
            summary = summary_el.get_text(strip=True) if summary_el else ""

            time_el = card.select_one("time")
            posted = time_el.get("datetime", "") if time_el else ""

            salary_el = card.select_one('[data-at="job-item-salary"]')
            salary = salary_el.get_text(strip=True) if salary_el else "Not specified"

            jobs.append({
                "title":      title,
                "company":    company,
                "location":   location,
                "salary":     salary,
                "summary":    summary[:150000],  # Increased from 500 to 1500 chars
                "url":        url,
                "job_id":     job_id,
                "posted":     posted,
                "source":     "Pnet",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            log.debug(f"  Card parse error: {e}")


    return jobs


def has_next_page(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    return bool(soup.select_one(
        "a[aria-label='Next page'], a[rel='next'], [data-at='pagination-next']:not([disabled])"
    ))


def scrape_slug(page, slug: str) -> list[dict]:
    """Scrape all pages for one search slug using an open Playwright page."""
    jobs = []
    log.info(f"\n--- Slug: '{slug}' ---")

    for pg in range(1, MAX_PAGES + 1):
        url = f"{BASE_URL}/jobs/full-time/{slug}"
        if pg > 1:
            url += f"?page={pg}"

        log.info(f"  Page {pg}: {url}")

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_selector(
                'article[id^="job-item-"], [data-at="job-item"]',
                timeout=15_000
            )
        except PWTimeout:
            log.warning("  Timeout waiting for job cards — page may be empty or blocked.")
            snippet = page.inner_text("body")[:300].replace("\n", " ")
            log.info(f"  Page text: {snippet!r}")
            break
        except Exception as e:
            log.warning(f"  Navigation error: {e}")
            break

        html = page.content()
        page_jobs = parse_cards(html)

        if not page_jobs:
            log.info("  No jobs on this page — stopping slug.")
            break

        jobs.extend(page_jobs)
        log.info(f"  +{len(page_jobs)} jobs (slug total: {len(jobs)})")

        if not has_next_page(html):
            log.info("  No next page.")
            break

        sleep()

    return jobs


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("Pnet ZA - Data Jobs Scraper (Playwright)")
    log.info("=" * 60)

    all_jobs  = []
    seen_keys = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="en-ZA",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        # Warm up — visit homepage to collect cookies
        log.info("Warming up (loading homepage) ...")
        try:
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=20_000)
            # Dismiss cookie banner if present
            try:
                page.click(
                    '[data-testid="cookie-accept"], #onetrust-accept-btn-handler',
                    timeout=4_000
                )
                log.info("  Dismissed cookie banner.")
            except Exception:
                pass
        except Exception as e:
            log.warning(f"  Warmup error (non-fatal): {e}")

        sleep()

        for slug in DEFAULT_SEARCH_SLUGS:
            jobs = scrape_slug(page, slug)
            for job in jobs:
                key = job.get("job_id") or job.get("url") or f"{job['title']}|{job['company']}"
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    all_jobs.append(job)
            sleep()

        browser.close()

    log.info(f"\nTotal unique jobs: {len(all_jobs)}")

    payload = {
        "meta": {
            "source":     "Pnet ZA",
            "slugs":      DEFAULT_SEARCH_SLUGS,
            "total_jobs": len(all_jobs),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        "jobs": all_jobs,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    log.info(f"[OK] Saved -> {OUTPUT}")
    log.info("=" * 60)

    print("\n" + "=" * 60)
    print("PNET SCRAPER SUMMARY")
    print("=" * 60)
    print(f"Total jobs:  {len(all_jobs)}")
    print(f"Output:      {OUTPUT}")
    print("=" * 60)

    if all_jobs:
        print("\nSample results:")
        for job in all_jobs[:5]:
            print(f"  - {job['title']} | {job['company']} | {job['location']}")


if __name__ == "__main__":
    main()