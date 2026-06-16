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
from typing import Optional

import requests
from bs4 import BeautifulSoup
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

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
OUTPUT    = "data/data_jobs_careers24.json"
MAX_PAGES = 20     # safety cap — pagination tells us real count
DELAY_MIN = 2.0
DELAY_MAX = 4.5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-ZA,en-GB;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def sleep():
    t = random.uniform(DELAY_MIN, DELAY_MAX)
    log.info(f"  Waiting {t:.1f}s ...")
    time.sleep(t)


def get_page(session: requests.Session, url: str) -> Optional[BeautifulSoup]:
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
            total_pages_attr = pager.get("data-total-pages")
            if total_pages_attr is not None:
                return min(MAX_PAGES, int(total_pages_attr))
        except (ValueError, KeyError, TypeError):
            pass

    # Fallback: calculate from NumFound hidden input (pageSize=10 fixed)
    num_found_el = soup.select_one("#NumFound")
    if num_found_el:
        try:
            value_attr = num_found_el.get("value") or 0
            total = int(value_attr)
            return min(MAX_PAGES, -(-total // 10))  # ceiling division
        except (ValueError, TypeError):
            pass

    return 1  # at least one page


def parse_cards(soup: BeautifulSoup, debug_slug: str = "") -> list[dict]:
    """Extract job cards using confirmed Careers24 HTML selectors."""
    jobs = []
    # Simplified selector that works: just match the class without requiring data-control attribute
    cards = soup.select('div.job-card')
    log.info(f"  Found {len(cards)} job cards")
    
    # Debug: if no cards found, save HTML
    if not cards and debug_slug:
        debug_file = f"debug_html_{debug_slug.replace(' ', '_')}.html"
        html_content = soup.prettify()
        if isinstance(html_content, bytes):
            html_content = html_content.decode("utf-8", errors="replace")
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(html_content[:100000])
        log.warning(f"  [DEBUG] No cards found. Saved HTML to {debug_file}")
        return jobs

    for i, card in enumerate(cards, 1):
        try:
            job_id = card.get("data-id", "")
            log.debug(f"    Card {i}: job_id={job_id}")

            # Title: <a data-control="vacancy-title"><h2>...
            title_link = card.select_one('a[data-control="vacancy-title"]')
            if not title_link:
                title_link = card.select_one('a h2')  # Fallback
            if not title_link:
                log.debug(f"    Card {i}: No title link found")
                continue
                
            h2 = title_link.select_one("h2")
            title = h2.get_text(strip=True) if h2 else title_link.get_text(strip=True)
            if not title:
                log.debug(f"    Card {i}: No title text")
                continue
            log.debug(f"    Card {i}: title={title[:50]}")

            href = title_link.get("href", "")
            url = (href if href.startswith("http") else f"{BASE_URL}{href}").split("?")[0]

            # Location, job type, posted — from job-card-left ul li items
            lis = card.select(".job-card-left ul li")
            location = lis[0].get_text(strip=True) if len(lis) > 0 else ""
            
            # Job type is in 2nd li with format "Job Type: Permanent"
            job_type = ""
            if len(lis) > 1:
                job_type_text = lis[1].get_text(strip=True)
                job_type = job_type_text.replace("Job Type:", "").strip()
            
            # Posted date is in 3rd li
            posted = ""
            if len(lis) > 2:
                # Format: "Posted: 10 Jun 2026  55 Days left"
                posted_text = lis[2].get_text(" ", strip=True)
                # Extract just the date part (before the <br> tag)
                if "Posted:" in posted_text:
                    m = re.search(r"Posted:\s*(\d+\s+\w+\s+\d{4})", posted_text)
                    posted = m.group(1).strip() if m else ""

            # Company — from img alt in right column
            company = ""
            logo_img = card.select_one(".job-card-right img[alt]")
            if logo_img:
                company = logo_img.get("alt", "").strip()

            job_dict = {
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
            }
            jobs.append(job_dict)
            log.debug(f"    Card {i}: Added job (company={company})")
        except Exception as e:
            log.debug(f"    Card {i}: Parse error: {e}")

    return jobs


def scrape_slug(session: requests.Session, slug: str) -> list[dict]:
    jobs = []
    log.info(f"\n--- Slug: '{slug}' ---")

    # Page 1 - note: slug URL pattern uses trailing dash
    url_p1 = f"{BASE_URL}/jobs/kw-{slug}-/rmt-incl/"
    log.debug(f"  URL: {url_p1}")
    soup = get_page(session, url_p1)
    if soup is None:
        return []

    total_pages = get_total_pages(soup)
    num_found = soup.select_one("#NumFound")
    if num_found:
        try:
            total_jobs = int(num_found.get("value") or 0)
        except (ValueError, TypeError):
            total_jobs = "?"
    else:
        total_jobs = "?"
    log.info(f"  Results: {total_jobs} jobs across {total_pages} page(s)")

    jobs.extend(parse_cards(soup, debug_slug=slug))

    for pg in range(2, total_pages + 1):
        sleep()
        # Include trailing dash in pagination URL too
        url = f"{BASE_URL}/jobs/kw-{slug}-/rmt-incl/?pg={pg}"
        log.info(f"  Page {pg}/{total_pages}: {url}")
        soup = get_page(session, url)
        if soup is None:
            break
        page_jobs = parse_cards(soup, debug_slug=slug)
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