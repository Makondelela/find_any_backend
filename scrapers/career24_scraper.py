"""
Careers24 Job Scraper - Data Roles (South Africa)
==================================================
Server-side rendered — uses requests + BeautifulSoup (no Playwright needed).
URL pattern: https://www.careers24.com/jobs/kw-{slug}/rmt-incl/?pg={page}

Usage:
    pip install requests beautifulsoup4
    python careers24_scraper.py

Output: data_jobs_careers24.json
"""

import json
import logging
import sys
import io
import time
import random
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

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
BASE_URL  = "https://www.careers24.com"
OUTPUT    = "data_jobs_careers24.json"
MAX_PAGES = 20     # safety cap — pagination tells us real count
DELAY_MIN = 2.0
DELAY_MAX = 4.5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-ZA,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.careers24.com/",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def sleep():
    t = random.uniform(DELAY_MIN, DELAY_MAX)
    log.info(f"  Waiting {t:.1f}s ...")
    time.sleep(t)


def get_page(session: requests.Session, url: str) -> BeautifulSoup | None:
    try:
        r = session.get(url, headers=HEADERS, timeout=25)
        if r.status_code == 403:
            log.warning(f"  [BLOCKED] 403 — {url}")
            return None
        if r.status_code != 200:
            log.warning(f"  [HTTP {r.status_code}] {url}")
            return None
        log.info(f"  [OK] {r.status_code} — {len(r.text):,} chars")
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as e:
        log.error(f"  [ERROR] {e}")
        return None


def get_total_pages(soup: BeautifulSoup) -> int:
    """Read data-total-pages from the pagination element — most reliable."""
    # Primary: <ul id="pagination" data-total-pages="3">
    pager = soup.select_one("ul#pagination[data-total-pages]")
    if pager:
        try:
            return min(MAX_PAGES, int(pager["data-total-pages"]))
        except (ValueError, KeyError):
            pass

    # Fallback: calculate from NumFound hidden input (pageSize=10 fixed)
    num_found_el = soup.select_one("#NumFound")
    if num_found_el:
        try:
            total = int(num_found_el.get("value", 0))
            return min(MAX_PAGES, -(-total // 10))  # ceiling division
        except ValueError:
            pass

    return 1  # at least one page


def parse_cards(soup: BeautifulSoup) -> list[dict]:
    """Extract job cards using confirmed Careers24 HTML selectors."""
    jobs = []
    cards = soup.select('div.job-card[data-control="job-card"]')
    log.info(f"  Found {len(cards)} job cards")

    for card in cards:
        try:
            job_id = card.get("data-id", "")

            # Title + URL
            title_link = card.select_one('a[data-control="vacancy-title"]')
            if not title_link:
                continue
            h2 = title_link.select_one("h2")
            title = h2.get_text(strip=True) if h2 else title_link.get_text(strip=True)
            if not title:
                continue

            href = title_link.get("href", "")
            url = (href if href.startswith("http") else f"{BASE_URL}{href}").split("?")[0]

            # Location, job type, posted date — from left column <li> items
            lis = card.select(".job-card-left ul li")
            location = lis[0].get_text(strip=True) if len(lis) > 0 else ""
            job_type  = lis[1].get_text(strip=True).replace("Job Type:", "").strip() if len(lis) > 1 else ""

            posted = ""
            if len(lis) > 2:
                raw = lis[2].get_text(" ", strip=True)
                m = re.search(r"Posted:\s*(\d+\s+\w+\s+\d{4})", raw)
                posted = m.group(1).strip() if m else raw.replace("Posted:", "").strip()

            # Company — primary: img alt in right column
            #           fallback: data-title on the envelope <i> (always present)
            company = ""
            logo_img = card.select_one(".job-card-right img[alt]")
            if logo_img:
                company = logo_img.get("alt", "").strip()
            if not company:
                envelope = card.select_one('i[data-title]')
                if envelope:
                    company = envelope.get("data-title", "").strip()

            # Location fallback from data-location on envelope icon
            if not location:
                envelope = card.select_one('i[data-location]')
                if envelope:
                    location = envelope.get("data-location", "").strip()

            jobs.append({
                "title":      title,
                "company":    company,
                "location":   location,
                "job_type":   job_type,
                "salary":     "Not specified",
                "summary":    "",
                "url":        url,
                "job_id":     job_id,
                "posted":     posted,
                "source":     "Careers24",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            log.debug(f"  Card parse error: {e}")

    return jobs


def scrape_slug(session: requests.Session, slug: str) -> list[dict]:
    jobs = []
    log.info(f"\n--- Slug: '{slug}' ---")

    # Page 1
    url_p1 = f"{BASE_URL}/jobs/kw-{slug}/rmt-incl/"
    soup = get_page(session, url_p1)
    if soup is None:
        return []

    total_pages = get_total_pages(soup)
    num_found = soup.select_one("#NumFound")
    total_jobs = int(num_found.get("value", 0)) if num_found else "?"
    log.info(f"  Results: {total_jobs} jobs across {total_pages} page(s)")

    jobs.extend(parse_cards(soup))

    for pg in range(2, total_pages + 1):
        sleep()
        url = f"{BASE_URL}/jobs/kw-{slug}/rmt-incl/?pg={pg}"
        log.info(f"  Page {pg}/{total_pages}: {url}")
        soup = get_page(session, url)
        if soup is None:
            break
        page_jobs = parse_cards(soup)
        if not page_jobs:
            log.info("  No jobs on page — stopping.")
            break
        jobs.extend(page_jobs)

    log.info(f"  Slug done: {len(jobs)} jobs collected")
    return jobs


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("Careers24 ZA - Data Jobs Scraper")
    log.info("=" * 60)

    session = requests.Session()

    # Warm up with homepage to collect cookies
    log.info("Warming up session ...")
    get_page(session, BASE_URL)
    sleep()

    all_jobs  = []
    seen_keys = set()

    for slug in DEFAULT_SEARCH_SLUGS:
        jobs = scrape_slug(session, slug)
        for job in jobs:
            key = job.get("job_id") or job.get("url") or f"{job['title']}|{job['company']}"
            if key and key not in seen_keys:
                seen_keys.add(key)
                all_jobs.append(job)
        sleep()

    log.info(f"\nTotal unique jobs: {len(all_jobs)}")

    payload = {
        "meta": {
            "source":     "Careers24 ZA",
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
    print("CAREERS24 SCRAPER SUMMARY")
    print("=" * 60)
    print(f"Total unique jobs: {len(all_jobs)}")
    print(f"Output:            {OUTPUT}")
    print("=" * 60)

    if all_jobs:
        print("\nSample results:")
        for job in all_jobs[:5]:
            print(f"  - {job['title']} | {job['company']} | {job['location']}")


if __name__ == "__main__":
    main()