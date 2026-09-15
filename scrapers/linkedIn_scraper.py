#!/usr/bin/env python3
"""
LinkedIn Job Scraper - Data Roles (South Africa)
=================================================
Server-side rendered — scrapes LinkedIn's public "guest" job search API
directly with requests + BeautifulSoup (no browser, no local Node server).

URL pattern: https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search

Usage:
    python linkedIn_scraper.py

Output: data/data_jobs_linkedin.json
"""

import json
import logging
import sys
import io
import time
import random
import hashlib
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

import requests
from bs4 import BeautifulSoup

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
GUEST_API_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
OUTPUT = "data/data_jobs_linkedin.json"
PAGE_SIZE = 25
MAX_PAGES = 8      # safety cap — 8 * 25 = 200 jobs per keyword
DELAY_MIN = 2.0
DELAY_MAX = 4.0
LOCATION = "South Africa"
DATE_POSTED = "past_month"  # past_24h | past_week | past_month

# LinkedIn's guest search expects f_TPR as "r<seconds>"
DATE_POSTED_TO_TPR = {
    "past_24h": "r86400",
    "past_week": "r604800",
    "past_month": "r2592000",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-ZA,en-GB;q=0.9,en;q=0.8",
    "Referer": "https://www.linkedin.com/jobs/search",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def sleep():
    t = random.uniform(DELAY_MIN, DELAY_MAX)
    log.info(f"  Waiting {t:.1f}s ...")
    time.sleep(t)


def validate_search_params(keywords: str, location: str) -> Optional[str]:
    """Mirror the validation the old scraper API used to enforce."""
    if not keywords:
        return "Keywords parameter is required"
    if not location:
        return "Location parameter is required"
    if len(keywords) < 2:
        return "Keywords must be at least 2 characters long"
    if len(location) < 2:
        return "Location must be at least 2 characters long"
    return None


def generate_job_id(url: str, title: str, company: str) -> str:
    """Generate a unique job ID - uses URL directly to prevent duplicates across scrapes."""
    if url:
        return url
    # Fallback: hash title + company if no URL
    key = f"{title}|{company}".lower()
    return f"linkedin_{hashlib.md5(key.encode()).hexdigest()[:12]}"


def clean_url(url: str) -> str:
    if not url:
        return ""
    return url.split("?")[0]


def extract_posted_date(description: str, date_field: str) -> str:
    """Extract posted date from LinkedIn data or description text."""
    if date_field and date_field.strip():
        return date_field.strip()

    if description:
        lines = description.strip().split('\n')
        for line in reversed(lines[-5:]):
            line_clean = line.strip()
            if any(x in line_clean.lower() for x in ['ago', 'day', 'week', 'month', 'hour']):
                return line_clean

    return ""


def get_page(session: requests.Session, params: dict) -> Optional[BeautifulSoup]:
    try:
        r = session.get(GUEST_API_URL, params=params, headers=HEADERS, timeout=25)
        if r.status_code == 429:
            log.warning("  [RATE LIMITED] 429 — backing off")
            return None
        if r.status_code != 200:
            log.warning(f"  [HTTP {r.status_code}]")
            return None
        if not r.text.strip():
            return None
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as e:
        log.error(f"  [ERROR] {e}")
        return None


def parse_cards(soup: BeautifulSoup) -> list[dict]:
    """Extract job cards from a guest-search-api response fragment."""
    jobs = []
    cards = soup.select("li")
    for card in cards:
        try:
            title_el = card.select_one(".base-search-card__title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)

            company_el = card.select_one(".base-search-card__subtitle")
            company = company_el.get_text(strip=True) if company_el else ""

            location_el = card.select_one(".job-search-card__location")
            location = location_el.get_text(strip=True) if location_el else LOCATION

            link_el = card.select_one(".base-card__full-link")
            url = clean_url(link_el.get("href", "")) if link_el else ""

            time_el = card.select_one("time")
            list_date = time_el.get("datetime", "") if time_el else ""

            metadata_el = card.select_one(".base-search-card__metadata")
            description = metadata_el.get_text(" ", strip=True) if metadata_el else ""

            job_id = generate_job_id(url, title, company)
            posted = extract_posted_date(description, list_date)

            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "job_type": "Full-time",
                "salary": "Not specified",
                "summary": description[:500],
                "url": url,
                "job_id": job_id,
                "posted": posted,
                "source": "LinkedIn",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            log.debug(f"    Card parse error: {e}")

    return jobs


def search_jobs(keywords: str, location: str = LOCATION, date_posted: str = DATE_POSTED) -> list[dict]:
    """
    Search LinkedIn jobs directly via the public guest search API, paging
    through results until a page comes back empty.
    """
    error = validate_search_params(keywords, location)
    if error:
        log.warning(f"  Skipping '{keywords}': {error}")
        return []

    log.info(f"  Searching: '{keywords}' in {location}")

    session = requests.Session()
    f_tpr = DATE_POSTED_TO_TPR.get(date_posted, "")

    all_jobs = []
    for page in range(MAX_PAGES):
        params = {
            "keywords": keywords,
            "location": location,
            "start": page * PAGE_SIZE,
        }
        if f_tpr:
            params["f_TPR"] = f_tpr

        soup = get_page(session, params)
        if soup is None:
            break

        page_jobs = parse_cards(soup)
        if not page_jobs:
            break

        all_jobs.extend(page_jobs)
        log.info(f"  Page {page + 1}: {len(page_jobs)} jobs")

        if len(page_jobs) < PAGE_SIZE:
            break

        sleep()

    log.info(f"  Found {len(all_jobs)} jobs")
    return all_jobs


def scrape_keyword(keyword: str) -> list[dict]:
    """Scrape all jobs for one keyword."""
    jobs = []
    log.info(f"\n--- Keyword: '{keyword}' ---")

    keyword_jobs = search_jobs(keyword, LOCATION, DATE_POSTED)
    jobs.extend(keyword_jobs)

    sleep()

    log.info(f"  Keyword done: {len(jobs)} jobs")
    return jobs


def main(search_keywords: Optional[list[str]] = None):
    """
    Main scraping function.

    Args:
        search_keywords: Optional list of keywords to search. Uses DEFAULT_SEARCH_SLUGS if not provided.
    """
    log.info("\n" + "=" * 60)
    log.info("LINKEDIN - Data Jobs Scraper")
    log.info("=" * 60)
    log.info(f"Location: {LOCATION}")
    log.info(f"Date Filter: {DATE_POSTED}")

    keywords = search_keywords if search_keywords else DEFAULT_SEARCH_SLUGS

    all_jobs = []
    seen_keys = set()

    for keyword in keywords:
        jobs = scrape_keyword(keyword)
        for job in jobs:
            key = job.get("job_id") or job.get("url") or f"{job['title']}|{job['company']}"
            if key and key not in seen_keys:
                seen_keys.add(key)
                all_jobs.append(job)
        sleep()

    log.info(f"\nTotal unique jobs: {len(all_jobs)}")

    payload = {
        "meta": {
            "source": "LinkedIn",
            "location": LOCATION,
            "date_filter": DATE_POSTED,
            "keywords": keywords,
            "total_jobs": len(all_jobs),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        "jobs": all_jobs,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    log.info(f"[OK] Saved → {OUTPUT}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        keywords = [arg.strip() for arg in sys.argv[1:]]
        main(search_keywords=keywords)
    else:
        main()
