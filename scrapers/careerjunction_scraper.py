"""
CareerJunction Job Scraper - Data Roles (South Africa)
======================================================
Plain requests + BeautifulSoup — no Playwright needed.
Selectors confirmed from live HTML inspection.

Card structure:
    <div class="module job-result">
      <div class="module-content">
        <div class="job-result-logo-title">
          <div class="job-result-logo"> <img alt="Company Name"> </div>
          <div class="job-result-title">
            <h2><a jobid="..." href="...">Job Title</a></h2>
            <h3><a href="/companies/...">Company Name</a></h3>
          </div>
        </div>
        <div class="job-result-overview">
          <ul class="job-overview">
            <li class="salary">...</li>
            <li class="position">...</li>
            <li class="location"><a>...</a></li>
            <li class="updated-time">Posted DD Mon YYYY</li>
          </ul>
        </div>
      </div>
    </div>

Pagination: <ul id="pagination"> with numbered <a> links
Total jobs:  <label>Total Jobs Found: <span>221</span></label>

URL pattern:
    Page 1: https://www.careerjunction.co.za/jobs/results?keywords=Data+Engineer&autosuggestEndpoint=%2Fautosuggest&location=0&category=&btnSubmit=+
    Page N: same URL + &page=N
    Per page can be set with &PerPage=100 (max supported)

Usage:
    pip install requests beautifulsoup4
    python careerjunction_scraper.py

Output: data_jobs_careerjunction.json
"""

import json
import logging
import sys
import io
import time
import random
import re
from datetime import datetime, timezone
from urllib.parse import urlencode, quote_plus

import requests
from bs4 import BeautifulSoup

from search_config import DEFAULT_SEARCH_KEYWORDS

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
BASE_URL  = "https://www.careerjunction.co.za"
OUTPUT    = "data_jobs_careerjunction.json"
PER_PAGE  = 100     # CJ supports 25 / 50 / 100
MAX_PAGES = 20      # safety cap
DELAY_MIN = 2.0
DELAY_MAX = 4.0

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
    "Referer": "https://www.careerjunction.co.za/",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def sleep():
    t = random.uniform(DELAY_MIN, DELAY_MAX)
    log.info(f"  Waiting {t:.1f}s ...")
    time.sleep(t)


def build_url(keyword: str, page: int = 1) -> str:
    """
    Matches the exact URL CareerJunction generates in the browser.
    PerPage=100 fetches up to 100 results per request.
    """
    kw = quote_plus(keyword)
    url = (
        f"{BASE_URL}/jobs/results"
        f"?keywords={kw}"
        f"&autosuggestEndpoint=%2Fautosuggest"
        f"&location=0"
        f"&category="
        f"&btnSubmit=+"
        f"&PerPage={PER_PAGE}"
    )
    if page > 1:
        url += f"&page={page}"
    return url


def get_page(session: requests.Session, url: str) -> BeautifulSoup | None:
    try:
        r = session.get(url, headers=HEADERS, timeout=25)
        if r.status_code == 403:
            log.warning(f"  [403 BLOCKED] {url}")
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
    """
    Read total job count from the label, calculate pages.
    Fallback: read highest page number from pagination links.
    """
    # Primary: <label>Total Jobs Found: <span>221</span></label>
    label = soup.find("label", string=re.compile(r"Total Jobs Found", re.I))
    if label:
        span = label.find("span")
        if span:
            try:
                total = int(span.get_text(strip=True).replace(",", ""))
                pages = min(MAX_PAGES, -(-total // PER_PAGE))
                log.info(f"  Total jobs: {total} → {pages} page(s)")
                return pages
            except ValueError:
                pass

    # Fallback: numbered links in <ul id="pagination">
    pager = soup.select_one("ul#pagination")
    if pager:
        nums = [
            int(a.get_text(strip=True))
            for a in pager.select("a")
            if a.get_text(strip=True).isdigit()
        ]
        if nums:
            return min(MAX_PAGES, max(nums))

    return 1


def parse_cards(soup: BeautifulSoup, keyword: str) -> list[dict]:
    """
    Parse confirmed CareerJunction card structure:
        <div class="module job-result">
    
    Filters jobs to only include those with data-related terms in the title.
    """
    # Data-related terms that should appear in job titles
    DATA_TERMS = [
        'data', 'analyst', 'analytics', 'engineer', 'scientist',
        'bi', 'business intelligence', 'etl', 'sql', 'python',
        'machine learning', 'ml', 'ai', 'artificial intelligence',
        'architect', 'developer', 'warehouse', 'pipeline', 'integration',
        'reporting', 'visualization', 'power bi', 'tableau', 'azure',
        'aws', 'gcp', 'cloud', 'big data', 'spark', 'hadoop'
    ]
    
    jobs = []
    cards = soup.select("div.module.job-result")
    log.info(f"  Found {len(cards)} job cards")

    for card in cards:
        try:
            # ── Title + job_id + URL ─────────────────────────────────────────
            title_a = card.select_one("div.job-result-title h2 a")
            if not title_a:
                continue
            title = title_a.get_text(strip=True)
            if not title:
                continue
            
            # ── Filter: Only keep jobs with data-related terms in title ──────
            title_lower = title.lower()
            if not any(term in title_lower for term in DATA_TERMS):
                log.debug(f"  Skipping irrelevant job: {title}")
                continue

            job_id = title_a.get("jobid", "")
            href = title_a.get("href", "")
            url = (href if href.startswith("http") else f"{BASE_URL}{href}").split("?")[0]

            # ── Company ──────────────────────────────────────────────────────
            company_a = card.select_one("div.job-result-title h3 a")
            company = company_a.get_text(strip=True) if company_a else ""

            # fallback: logo img alt
            if not company:
                logo_img = card.select_one("div.job-result-logo img[alt]")
                if logo_img:
                    company = logo_img.get("alt", "").replace(" jobs", "").strip()

            # ── Overview list items ───────────────────────────────────────────
            overview = card.select_one("ul.job-overview")

            salary = "Not specified"
            job_type = ""
            location = ""
            posted = ""

            if overview:
                salary_li = overview.select_one("li.salary")
                if salary_li:
                    salary = salary_li.get_text(strip=True)

                position_li = overview.select_one("li.position")
                if position_li:
                    job_type = position_li.get_text(strip=True)

                location_li = overview.select_one("li.location")
                if location_li:
                    # may have multiple <a> tags (e.g. "Johannesburg / Work From Home")
                    location = " / ".join(
                        a.get_text(strip=True)
                        for a in location_li.select("a")
                    ) or location_li.get_text(strip=True)

                posted_li = overview.select_one("li.updated-time")
                if posted_li:
                    raw = posted_li.get_text(strip=True)
                    # "Posted 24 Feb 2026" → strip prefix
                    posted = re.sub(r"^Posted\s*", "", raw, flags=re.I).strip()

            jobs.append({
                "title":      title,
                "company":    company,
                "location":   location,
                "job_type":   job_type,
                "salary":     salary,
                "summary":    "",
                "url":        url,
                "job_id":     job_id,
                "posted":     posted,
                "keyword":    keyword,
                "source":     "CareerJunction",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })

        except Exception as e:
            log.debug(f"  Card parse error: {e}")

    return jobs


def scrape_keyword(session: requests.Session, keyword: str) -> list[dict]:
    jobs = []
    log.info(f"\n--- Keyword: '{keyword}' ---")

    url_p1 = build_url(keyword, page=1)
    log.info(f"  {url_p1}")
    soup = get_page(session, url_p1)
    if soup is None:
        return []

    total_pages = get_total_pages(soup)
    jobs.extend(parse_cards(soup, keyword))

    for pg in range(2, total_pages + 1):
        sleep()
        url = build_url(keyword, page=pg)
        log.info(f"  Page {pg}/{total_pages}: {url}")
        soup = get_page(session, url)
        if soup is None:
            break
        page_jobs = parse_cards(soup, keyword)
        if not page_jobs:
            log.info("  No jobs found — stopping pagination")
            break
        jobs.extend(page_jobs)

    log.info(f"  Keyword done: {len(jobs)} jobs")
    return jobs


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("CareerJunction ZA - Data Jobs Scraper")
    log.info("=" * 60)

    session = requests.Session()

    log.info("Warming up session ...")
    get_page(session, BASE_URL)
    sleep()

    all_jobs  = []
    seen_keys = set()

    for keyword in DEFAULT_SEARCH_KEYWORDS:
        jobs = scrape_keyword(session, keyword)
        for job in jobs:
            key = job.get("job_id") or job.get("url") or f"{job['title']}|{job['company']}"
            if key and key not in seen_keys:
                seen_keys.add(key)
                all_jobs.append(job)
        sleep()

    log.info(f"\nTotal unique jobs: {len(all_jobs)}")

    payload = {
        "meta": {
            "source":     "CareerJunction ZA",
            "keywords":   DEFAULT_SEARCH_KEYWORDS,
            "total_jobs": len(all_jobs),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        "jobs": all_jobs,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    log.info(f"[OK] Saved → {OUTPUT}")
    log.info("=" * 60)

    print("\n" + "=" * 60)
    print("CAREERJUNCTION SCRAPER SUMMARY")
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