"""
Job Scraping - Unified Entry Point
===================================
Consolidates scraping from multiple job boards into a single command.

Job Types Supported:
  • Data Engineer
  • Data Analyst
  • Data Scientist
  • Data Architect
  • Business Intelligence / BI Developer
  • Machine Learning Engineer
  • ETL Developer
  • Analytics Engineer
  • And related data/analytics roles

Supported Job Boards:
  1. Careers24 (careers24.com) - Web scraping with requests + BeautifulSoup
  2. CareerJunction (careerjunction.co.za) - Web scraping with requests + BeautifulSoup
  3. Pnet (pnet.co.za) - Browser automation with Playwright
  4. Network Recruitment International - Direct API (no scraping needed)

Usage:
    # Run all scrapers
    python main.py

    # Run specific scrapers
    python main.py --careers24
    python main.py --careerjunction
    python main.py --pnet
    python main.py --nri

    # Run subset
    python main.py --careers24 --careerjunction

Output:
    - All data combined and deduplicated → data_jobs_combined.json
    - Individual source files also saved → data_jobs_*.json
    - Summary printed to console

Dependencies:
    pip install requests beautifulsoup4 playwright
    playwright install chromium
"""

import json
import logging
import sys
import io
import time

# Set UTF-8 encoding for stdout to handle special characters
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import random
import re
import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus, urlencode
from typing import Optional
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

from search_config import (
    DEFAULT_SEARCH_SLUGS,
    parse_search_terms
)

# Try to import Playwright — optional for Pnet scraper
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

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

# ══════════════════════════════════════════════════════════════════════════════
# SCRAPERS
# ══════════════════════════════════════════════════════════════════════════════

# ── CAREERS24 SCRAPER ─────────────────────────────────────────────────────────

class Careers24Scraper:
    """Scraper for Careers24.com (South Africa)"""

    BASE_URL = "https://www.careers24.com"
    OUTPUT = "data/data_jobs_careers24.json"
    MAX_PAGES = 20
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

    @staticmethod
    def sleep():
        t = random.uniform(Careers24Scraper.DELAY_MIN, Careers24Scraper.DELAY_MAX)
        log.info(f"  Waiting {t:.1f}s ...")
        time.sleep(t)

    @staticmethod
    def get_page(session: requests.Session, url: str) -> Optional[BeautifulSoup]:
        try:
            r = session.get(url, headers=Careers24Scraper.HEADERS, timeout=25)
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

    @staticmethod
    def get_total_pages(soup: BeautifulSoup) -> int:
        pager = soup.select_one("ul#pagination[data-total-pages]")
        if pager:
            try:
                return min(Careers24Scraper.MAX_PAGES, int(pager["data-total-pages"]))
            except (ValueError, KeyError):
                pass

        num_found_el = soup.select_one("#NumFound")
        if num_found_el:
            try:
                total = int(num_found_el.get("value", 0))
                return min(Careers24Scraper.MAX_PAGES, -(-total // 10))
            except ValueError:
                pass

        return 1

    @staticmethod
    def parse_cards(soup: BeautifulSoup) -> list[dict]:
        jobs = []
        cards = soup.select('div.job-card[data-control="job-card"]')
        log.info(f"  Found {len(cards)} job cards")

        for card in cards:
            try:
                job_id = card.get("data-id", "")

                title_link = card.select_one('a[data-control="vacancy-title"]')
                if not title_link:
                    continue
                h2 = title_link.select_one("h2")
                title = h2.get_text(strip=True) if h2 else title_link.get_text(strip=True)
                if not title:
                    continue

                href = title_link.get("href", "")
                url = (href if href.startswith("http") else f"{Careers24Scraper.BASE_URL}{href}").split("?")[0]

                lis = card.select(".job-card-left ul li")
                location = lis[0].get_text(strip=True) if len(lis) > 0 else ""
                job_type = lis[1].get_text(strip=True).replace("Job Type:", "").strip() if len(lis) > 1 else ""

                posted = ""
                if len(lis) > 2:
                    raw = lis[2].get_text(" ", strip=True)
                    m = re.search(r"Posted:\s*(\d+\s+\w+\s+\d{4})", raw)
                    posted = m.group(1).strip() if m else raw.replace("Posted:", "").strip()

                company = ""
                logo_img = card.select_one(".job-card-right img[alt]")
                if logo_img:
                    company = logo_img.get("alt", "").strip()
                if not company:
                    envelope = card.select_one('i[data-title]')
                    if envelope:
                        company = envelope.get("data-title", "").strip()

                if not location:
                    envelope = card.select_one('i[data-location]')
                    if envelope:
                        location = envelope.get("data-location", "").strip()

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "job_type": job_type,
                    "salary": "Not specified",
                    "summary": "",
                    "url": url,
                    "job_id": job_id,
                    "posted": posted,
                    "source": "Careers24",
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                log.debug(f"  Card parse error: {e}")

        return jobs

    @staticmethod
    def scrape_slug(session: requests.Session, slug: str) -> list[dict]:
        jobs = []
        log.info(f"\n--- Slug: '{slug}' ---")

        url_p1 = f"{Careers24Scraper.BASE_URL}/jobs/kw-{slug}/rmt-incl/"
        soup = Careers24Scraper.get_page(session, url_p1)
        if soup is None:
            return []

        total_pages = Careers24Scraper.get_total_pages(soup)
        num_found = soup.select_one("#NumFound")
        total_jobs = int(num_found.get("value", 0)) if num_found else "?"
        log.info(f"  Results: {total_jobs} jobs across {total_pages} page(s)")

        jobs.extend(Careers24Scraper.parse_cards(soup))

        for pg in range(2, total_pages + 1):
            Careers24Scraper.sleep()
            url = f"{Careers24Scraper.BASE_URL}/jobs/kw-{slug}/rmt-incl/?pg={pg}"
            log.info(f"  Page {pg}/{total_pages}: {url}")
            soup = Careers24Scraper.get_page(session, url)
            if soup is None:
                break
            page_jobs = Careers24Scraper.parse_cards(soup)
            if not page_jobs:
                log.info("  No jobs on page — stopping.")
                break
            jobs.extend(page_jobs)

        log.info(f"  Slug done: {len(jobs)} jobs collected")
        return jobs

    @staticmethod
    def run(search_slugs: Optional[list[str]] = None) -> dict:
        log.info("\n" + "=" * 60)
        log.info("CAREERS24 - Data Jobs Scraper")
        log.info("=" * 60)

        # Use provided search slugs or fall back to default
        slugs = search_slugs if search_slugs else DEFAULT_SEARCH_SLUGS

        session = requests.Session()
        log.info("Warming up session ...")
        Careers24Scraper.get_page(session, Careers24Scraper.BASE_URL)
        Careers24Scraper.sleep()

        all_jobs = []
        seen_keys = set()

        for slug in slugs:
            jobs = Careers24Scraper.scrape_slug(session, slug)
            for job in jobs:
                key = job.get("job_id") or job.get("url") or f"{job['title']}|{job['company']}"
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    all_jobs.append(job)
            Careers24Scraper.sleep()

        log.info(f"\nTotal unique jobs: {len(all_jobs)}")

        payload = {
            "meta": {
                "source": "Careers24 ZA",
                "job_types": DEFAULT_SEARCH_SLUGS,
                "slugs": slugs,
                "total_jobs": len(all_jobs),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            },
            "jobs": all_jobs,
        }

        with open(Careers24Scraper.OUTPUT, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        log.info(f"[OK] Saved → {Careers24Scraper.OUTPUT}")
        return payload


# ── CAREERJUNCTION SCRAPER ────────────────────────────────────────────────────

class CareerJunctionScraper:
    """Scraper for CareerJunction.co.za (South Africa)"""

    BASE_URL = "https://www.careerjunction.co.za"
    OUTPUT = "data/data_jobs_careerjunction.json"
    PER_PAGE = 100
    MAX_PAGES = 20
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

    @staticmethod
    def sleep():
        t = random.uniform(CareerJunctionScraper.DELAY_MIN, CareerJunctionScraper.DELAY_MAX)
        log.info(f"  Waiting {t:.1f}s ...")
        time.sleep(t)

    @staticmethod
    def build_url(keyword: str, page: int = 1) -> str:
        kw = quote_plus(keyword)
        url = (
            f"{CareerJunctionScraper.BASE_URL}/jobs/results"
            f"?keywords={kw}"
            f"&autosuggestEndpoint=%2Fautosuggest"
            f"&location=0"
            f"&category="
            f"&btnSubmit=+"
            f"&PerPage={CareerJunctionScraper.PER_PAGE}"
        )
        if page > 1:
            url += f"&page={page}"
        return url

    @staticmethod
    def get_page(session: requests.Session, url: str) -> Optional[BeautifulSoup]:
        try:
            r = session.get(url, headers=CareerJunctionScraper.HEADERS, timeout=25)
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

    @staticmethod
    def get_total_pages(soup: BeautifulSoup) -> int:
        label = soup.find("label", string=re.compile(r"Total Jobs Found", re.I))
        if label:
            span = label.find("span")
            if span:
                try:
                    total = int(span.get_text(strip=True).replace(",", ""))
                    pages = min(CareerJunctionScraper.MAX_PAGES, -(-total // CareerJunctionScraper.PER_PAGE))
                    log.info(f"  Total jobs: {total} → {pages} page(s)")
                    return pages
                except ValueError:
                    pass

        pager = soup.select_one("ul#pagination")
        if pager:
            nums = [
                int(a.get_text(strip=True))
                for a in pager.select("a")
                if a.get_text(strip=True).isdigit()
            ]
            if nums:
                return min(CareerJunctionScraper.MAX_PAGES, max(nums))

        return 1

    @staticmethod
    def parse_cards(soup: BeautifulSoup, keyword: str) -> list[dict]:
        jobs = []
        cards = soup.select("div.module.job-result")
        log.info(f"  Found {len(cards)} job cards")

        for card in cards:
            try:
                title_a = card.select_one("div.job-result-title h2 a")
                if not title_a:
                    continue
                title = title_a.get_text(strip=True)
                if not title:
                    continue

                job_id = title_a.get("jobid", "")
                href = title_a.get("href", "")
                url = (href if href.startswith("http") else f"{CareerJunctionScraper.BASE_URL}{href}").split("?")[0]

                company_a = card.select_one("div.job-result-title h3 a")
                company = company_a.get_text(strip=True) if company_a else ""

                if not company:
                    logo_img = card.select_one("div.job-result-logo img[alt]")
                    if logo_img:
                        company = logo_img.get("alt", "").replace(" jobs", "").strip()

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
                        location = " / ".join(
                            a.get_text(strip=True)
                            for a in location_li.select("a")
                        ) or location_li.get_text(strip=True)

                    posted_li = overview.select_one("li.updated-time")
                    if posted_li:
                        raw = posted_li.get_text(strip=True)
                        posted = re.sub(r"^Posted\s*", "", raw, flags=re.I).strip()

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "job_type": job_type,
                    "salary": salary,
                    "summary": "",
                    "url": url,
                    "job_id": job_id,
                    "posted": posted,
                    "keyword": keyword,
                    "source": "CareerJunction",
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                })

            except Exception as e:
                log.debug(f"  Card parse error: {e}")

        return jobs

    @staticmethod
    def scrape_keyword(session: requests.Session, keyword: str) -> list[dict]:
        jobs = []
        log.info(f"\n--- Keyword: '{keyword}' ---")

        url_p1 = CareerJunctionScraper.build_url(keyword, page=1)
        log.info(f"  {url_p1}")
        soup = CareerJunctionScraper.get_page(session, url_p1)
        if soup is None:
            return []

        total_pages = CareerJunctionScraper.get_total_pages(soup)
        jobs.extend(CareerJunctionScraper.parse_cards(soup, keyword))

        for pg in range(2, total_pages + 1):
            CareerJunctionScraper.sleep()
            url = CareerJunctionScraper.build_url(keyword, page=pg)
            log.info(f"  Page {pg}/{total_pages}: {url}")
            soup = CareerJunctionScraper.get_page(session, url)
            if soup is None:
                break
            page_jobs = CareerJunctionScraper.parse_cards(soup, keyword)
            if not page_jobs:
                log.info("  No jobs found — stopping pagination")
                break
            jobs.extend(page_jobs)

        log.info(f"  Keyword done: {len(jobs)} jobs")
        return jobs

    @staticmethod
    def run(search_keywords: Optional[list[str]] = None) -> dict:
        log.info("\n" + "=" * 60)
        log.info("CAREERJUNCTION - Data Jobs Scraper")
        log.info("=" * 60)

        # Use provided search keywords or fall back to default
        keywords = search_keywords if search_keywords else DEFAULT_SEARCH_SLUGS

        session = requests.Session()
        log.info("Warming up session ...")
        CareerJunctionScraper.get_page(session, CareerJunctionScraper.BASE_URL)
        CareerJunctionScraper.sleep()

        all_jobs = []
        seen_keys = set()

        for keyword in keywords:
            jobs = CareerJunctionScraper.scrape_keyword(session, keyword)
            for job in jobs:
                key = job.get("job_id") or job.get("url") or f"{job['title']}|{job['company']}"
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    all_jobs.append(job)
            CareerJunctionScraper.sleep()

        log.info(f"\nTotal unique jobs: {len(all_jobs)}")

        payload = {
            "meta": {
                "source": "CareerJunction ZA",
                "job_types": DEFAULT_SEARCH_SLUGS,
                "keywords": keywords,
                "total_jobs": len(all_jobs),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            },
            "jobs": all_jobs,
        }

        with open(CareerJunctionScraper.OUTPUT, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        log.info(f"[OK] Saved → {CareerJunctionScraper.OUTPUT}")
        return payload


# ── PNET SCRAPER ──────────────────────────────────────────────────────────────

class PnetScraper:
    """Scraper for Pnet.co.za (South Africa) - requires Playwright"""

    BASE_URL = "https://www.pnet.co.za"
    OUTPUT = "data/data_jobs_pnet.json"
    MAX_PAGES = 5
    DELAY_MIN = 3.0
    DELAY_MAX = 6.0

    @staticmethod
    def sleep():
        t = random.uniform(PnetScraper.DELAY_MIN, PnetScraper.DELAY_MAX)
        log.info(f"  Waiting {t:.1f}s ...")
        time.sleep(t)

    @staticmethod
    def parse_cards(html: str) -> list[dict]:
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
                url = href if href.startswith("http") else f"{PnetScraper.BASE_URL}{href}"

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
                    "title": title,
                    "company": company,
                    "location": location,
                    "job_type": "Full-time",
                    "salary": salary,
                    "summary": summary[:500] if summary else "",
                    "url": url,
                    "job_id": job_id,
                    "posted": posted,
                    "source": "Pnet",
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                log.debug(f"  Card parse error: {e}")

        return jobs

    @staticmethod
    def has_next_page(html: str) -> bool:
        soup = BeautifulSoup(html, "html.parser")
        return bool(soup.select_one(
            "a[aria-label='Next page'], a[rel='next'], [data-at='pagination-next']:not([disabled])"
        ))

    @staticmethod
    def scrape_slug(page, slug: str) -> list[dict]:
        jobs = []
        log.info(f"\n--- Slug: '{slug}' ---")

        for pg in range(1, PnetScraper.MAX_PAGES + 1):
            url = f"{PnetScraper.BASE_URL}/jobs/full-time/{slug}"
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
            page_jobs = PnetScraper.parse_cards(html)

            if not page_jobs:
                log.info("  No jobs on this page — stopping slug.")
                break

            jobs.extend(page_jobs)
            log.info(f"  +{len(page_jobs)} jobs (slug total: {len(jobs)})")

            if not PnetScraper.has_next_page(html):
                log.info("  No next page.")
                break

            PnetScraper.sleep()

        return jobs

    @staticmethod
    def run(search_slugs: Optional[list[str]] = None) -> dict:
        if not HAS_PLAYWRIGHT:
            log.error("\n[SKIP] Pnet scraper requires Playwright")
            log.error("       Run: pip install playwright && playwright install chromium")
            return {"meta": {"source": "Pnet", "skipped": True}, "jobs": []}

        log.info("\n" + "=" * 60)
        log.info("PNET - Data Jobs Scraper (Browser-based)")
        log.info("=" * 60)

        # Use provided search slugs or fall back to default
        slugs = search_slugs if search_slugs else DEFAULT_SEARCH_SLUGS

        all_jobs = []
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
                page.goto(PnetScraper.BASE_URL, wait_until="domcontentloaded", timeout=20_000)
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

            PnetScraper.sleep()

            for slug in slugs:
                jobs = PnetScraper.scrape_slug(page, slug)
                for job in jobs:
                    key = job.get("job_id") or job.get("url") or f"{job['title']}|{job['company']}"
                    if key and key not in seen_keys:
                        seen_keys.add(key)
                        all_jobs.append(job)
                PnetScraper.sleep()

            browser.close()

        log.info(f"\nTotal unique jobs: {len(all_jobs)}")

        payload = {
            "meta": {
                "source": "Pnet ZA",
                "job_types": DEFAULT_SEARCH_SLUGS,
                "slugs": slugs,
                "total_jobs": len(all_jobs),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            },
            "jobs": all_jobs,
        }

        with open(PnetScraper.OUTPUT, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        log.info(f"[OK] Saved → {PnetScraper.OUTPUT}")
        return payload


# ── NETWORK RECRUITMENT INTERNATIONAL (API) SCRAPER ──────────────────────────

class NRIScraper:
    """Scraper for Network Recruitment International - Direct API (no Playwright)"""

    BASE_API = "https://az-jhb-was-rescr-duda-api-prod-networkrecruitint.azurewebsites.net/PlacementPartnerXml"
    PAGE_SIZE = 200
    NICHE = "IT"
    OUTPUT = "data/data_jobs_nri_api.json"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.networkrecruitmentinternational.com",
        "Referer": "https://www.networkrecruitmentinternational.com/",
    }

    @staticmethod
    def fetch_all_jobs() -> list[dict]:
        url = f"{NRIScraper.BASE_API}/api/getallnetworkrecruitmentadsvianiche"
        params = {"niche": NRIScraper.NICHE, "pageSize": NRIScraper.PAGE_SIZE}
        log.info(f"Calling API: {url}  (pageSize={NRIScraper.PAGE_SIZE})")
        try:
            r = requests.get(url, params=params, headers=NRIScraper.HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
            # API returns a list directly
            if isinstance(data, list):
                log.info(f"[OK] API returned {len(data)} records")
                return data
            # Fallback if API returns dict with "ads" key
            ads = data.get("ads", []) if isinstance(data, dict) else []
            log.info(f"[OK] API returned {len(ads)} records")
            return ads
        except requests.RequestException as e:
            log.error(f"API request failed: {e}")
            return []
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON: {e}")
            return []

    @staticmethod
    def is_data_role(record: dict) -> bool:
        """Return True if job title contains data/analytics keyword."""
        title = str(record.get("job_title", "")).lower()
        return any(kw.lower() in title for kw in DEFAULT_SEARCH_SLUGS)

    @staticmethod
    def clean_html(text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""
        clean = re.sub(r"<[^>]+>", " ", str(text))
        clean = re.sub(r"&amp;", "&", clean)
        clean = re.sub(r"&nbsp;", " ", clean)
        clean = re.sub(r"&lt;", "<", clean)
        clean = re.sub(r"&gt;", ">", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    @staticmethod
    def build_url(record: dict) -> str:
        """Build job detail URL from API record."""
        instance = record.get("company_ref", "network1")
        ref = record.get("vacancy_ref", "")
        return f"https://www.networkrecruitmentinternational.com/job-details?instance={instance}&vacancy_ref={ref}"

    @staticmethod
    def build_salary(record: dict) -> str:
        """Extract salary from API record."""
        if record.get("market_related"):
            return "Market Related"
        if record.get("negotiable"):
            return "Negotiable"
        lo = record.get("salary_min")
        hi = record.get("salary_max")
        if lo and hi:
            return f"R{lo} - R{hi} per annum"
        if lo:
            return f"From R{lo} per annum"
        if hi:
            return f"Up to R{hi} per annum"
        return "Not specified"

    @staticmethod
    def run() -> dict:
        log.info("\n" + "=" * 60)
        log.info("NETWORK RECRUITMENT INTERNATIONAL - API Data Jobs")
        log.info("=" * 60)

        raw = NRIScraper.fetch_all_jobs()
        if not raw:
            log.warning("No data returned from API. Check connectivity.")
            return {
                "meta": {
                    "source": "Network Recruitment International",
                    "job_types": DEFAULT_SEARCH_SLUGS,
                    "total_jobs": 0,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                },
                "jobs": [],
            }

        log.info(f"Processing {len(raw)} total records ...")

        # Filter for data roles
        jobs = []
        for record in raw:
            if not NRIScraper.is_data_role(record):
                continue

            title = record.get("job_title", "").strip()
            brief_desc = NRIScraper.clean_html(record.get("brief_description", ""))
            detail_desc = NRIScraper.clean_html(record.get("detail_description", ""))
            location_parts = []
            if record.get("region"):
                location_parts.append(record.get("region", ""))
            if record.get("town"):
                location_parts.append(record.get("town", ""))
            location = " > ".join(location_parts) or "Not specified"
            
            url = NRIScraper.build_url(record)
            vacancy_ref = record.get("vacancy_ref", "")
            # Use URL as job_id for unique identification
            job_id = url if url else vacancy_ref

            jobs.append({
                "title": title,
                "company": "Network Recruitment International",
                "location": location,
                "region": record.get("region", ""),
                "town": record.get("town", ""),
                "job_type": "Not specified",
                "salary": NRIScraper.build_salary(record),
                "summary": brief_desc[:200] if brief_desc else "",
                "brief_description": brief_desc,  # Keep full brief description
                "detail_description": detail_desc,  # Keep full detail description
                "url": url,
                "job_id": job_id,
                "vacancy_ref": vacancy_ref,
                "posted": record.get("posted_date", ""),
                "source": "Network Recruitment Intl",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })

        log.info(f"Filtered: {len(jobs)} data-related jobs")

        # Deduplicate by job_id (URL)
        seen = set()
        unique_jobs = []
        for job in jobs:
            job_id = job.get("job_id", "")
            if job_id and job_id not in seen:
                seen.add(job_id)
                unique_jobs.append(job)

        jobs = unique_jobs
        log.info(f"After dedup: {len(jobs)} unique data jobs")

        payload = {
            "meta": {
                "source": "Network Recruitment International",
                "job_types": DEFAULT_SEARCH_SLUGS,
                "niche": NRIScraper.NICHE,
                "total_jobs": len(jobs),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            },
            "jobs": jobs,
        }

        with open(NRIScraper.OUTPUT, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        log.info(f"[OK] Saved → {NRIScraper.OUTPUT}")
        return payload


# ── LINKEDIN SCRAPER ──────────────────────────────────────────────────────────

class LinkedInScraper:
    """Scraper for LinkedIn using API"""

    API_BASE_URL = "http://localhost:3000/api"
    OUTPUT = "data/data_jobs_linkedin.json"
    LOCATION = "South Africa"
    DATE_POSTED = "past_month"
    DELAY_MIN = 2.0
    DELAY_MAX = 4.0

    @staticmethod
    def sleep():
        t = random.uniform(LinkedInScraper.DELAY_MIN, LinkedInScraper.DELAY_MAX)
        log.info(f"  Waiting {t:.1f}s ...")
        time.sleep(t)

    @staticmethod
    def generate_job_id(url: str, title: str, company: str) -> str:
        """Generate a unique job ID - uses URL directly to prevent duplicates across scrapes."""
        if url:
            return url
        # Fallback: hash title + company if no URL
        import hashlib
        key = f"{title}|{company}".lower()
        return f"linkedin_{hashlib.md5(key.encode()).hexdigest()[:12]}"
    
    @staticmethod
    def extract_posted_date(description: str, date_field: str) -> str:
        """Extract posted date from LinkedIn data or description text."""
        # Use API date field if available
        if date_field and date_field.strip():
            return date_field.strip()
        
        # Fallback: extract from end of description (e.g., "6 days ago")
        if description:
            lines = description.strip().split('\n')
            # Check last few lines for date patterns
            for line in reversed(lines[-5:]):
                line_clean = line.strip()
                # Match patterns like "6 days ago", "1 week ago", "2 months ago"
                if any(x in line_clean.lower() for x in ['ago', 'day', 'week', 'month', 'hour']):
                    return line_clean
        
        return ""

    @staticmethod
    def search_jobs(keywords: str) -> list[dict]:
        """Search LinkedIn jobs via API."""
        log.info(f"  Searching: '{keywords}' in {LinkedInScraper.LOCATION}")
        
        try:
            params = {
                "keywords": keywords,
                "location": LinkedInScraper.LOCATION,
                "dateSincePosted": LinkedInScraper.DATE_POSTED
            }
            
            response = requests.get(
                f"{LinkedInScraper.API_BASE_URL}/search",
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                log.warning(f"  API returned status {response.status_code}")
                return []
            
            data = response.json()
            
            if not data.get("success"):
                log.warning(f"  API error: {data.get('error', 'Unknown error')}")
                return []
            
            jobs_raw = data.get("jobs", [])
            log.info(f"  Found {len(jobs_raw)} jobs")
            
            # Transform to standard format
            standardized_jobs = []
            for job in jobs_raw:
                title = job.get("title", "")
                company = job.get("company", "")
                url = job.get("link", "")
                job_id = job.get("jobId", "") or LinkedInScraper.generate_job_id(url, title, company)
                
                standardized_jobs.append({
                    "title": title,
                    "company": company,
                    "location": job.get("location", LinkedInScraper.LOCATION),
                    "job_type": "Full-time",
                    "salary": "Not specified",
                    "summary": job.get("description", "")[:500],
                    "url": url,
                    "job_id": job_id,
                    "posted": job.get("date", ""),
                    "source": "LinkedIn",
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                })
            
            return standardized_jobs
            
        except requests.exceptions.RequestException as e:
            log.error(f"  Request error: {e}")
            return []
        except Exception as e:
            log.error(f"  Unexpected error: {e}")
            return []

    @staticmethod
    def scrape_keyword(keyword: str) -> list[dict]:
        """Scrape all jobs for one keyword."""
        jobs = []
        log.info(f"\n--- Keyword: '{keyword}' ---")
        
        keyword_jobs = LinkedInScraper.search_jobs(keyword)
        jobs.extend(keyword_jobs)
        
        LinkedInScraper.sleep()
        
        log.info(f"  Keyword done: {len(jobs)} jobs")
        return jobs

    @staticmethod
    def run(search_keywords: Optional[list[str]] = None) -> dict:
        log.info("\n" + "=" * 60)
        log.info("LINKEDIN - Data Jobs Scraper")
        log.info("=" * 60)
        log.info(f"Location: {LinkedInScraper.LOCATION}")
        log.info(f"Date Filter: {LinkedInScraper.DATE_POSTED}")
        
        # Use provided keywords or default
        keywords = search_keywords if search_keywords else ["Data Engineer", "Data Analyst", "Data Scientist"]
        
        all_jobs = []
        seen_keys = set()
        
        for keyword in keywords:
            jobs = LinkedInScraper.scrape_keyword(keyword)
            for job in jobs:
                key = job.get("job_id") or job.get("url") or f"{job['title']}|{job['company']}"
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    all_jobs.append(job)
            LinkedInScraper.sleep()
        
        log.info(f"\nTotal unique jobs: {len(all_jobs)}")
        
        payload = {
            "meta": {
                "source": "LinkedIn",
                "location": LinkedInScraper.LOCATION,
                "date_filter": LinkedInScraper.DATE_POSTED,
                "keywords": keywords,
                "total_jobs": len(all_jobs),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            },
            "jobs": all_jobs,
        }
        
        with open(LinkedInScraper.OUTPUT, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        log.info(f"[OK] Saved → {LinkedInScraper.OUTPUT}")
        return payload


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def combine_results(results: dict) -> None:
    """Combine all scraper outputs into a single file with deduplication."""
    log.info("\n" + "=" * 60)
    log.info("COMBINING RESULTS")
    log.info("=" * 60)

    all_jobs = []
    seen_keys = set()
    source_counts = defaultdict(int)

    for source, payload in results.items():
        if payload.get("meta", {}).get("skipped"):
            continue
        for job in payload.get("jobs", []):
            key = job.get("job_id") or job.get("url") or f"{job['title']}|{job['company']}"
            if key and key not in seen_keys:
                seen_keys.add(key)
                all_jobs.append(job)
                source_counts[job["source"]] += 1

    combined = {
        "meta": {
            "sources": list(results.keys()),
            "job_types": DEFAULT_SEARCH_SLUGS,
            "total_jobs": len(all_jobs),
            "jobs_by_source": dict(source_counts),
            "combined_at": datetime.now(timezone.utc).isoformat(),
        },
        "jobs": all_jobs,
    }

    output_file = "data_jobs_combined.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    log.info(f"[OK] Combined → {output_file}")
    log.info(f"Total jobs (deduplicated): {len(all_jobs)}")
    for source, count in source_counts.items():
        log.info(f"  {source}: {count}")

    return combined


def parse_search_terms(search_string: str) -> tuple[list[str], list[str]]:
    """
    Parse search string into slugs and keywords.
    
    Args:
        search_string: Comma-separated search terms (e.g., "data engineer, python developer")
    
    Returns:
        tuple: (slugs for URL paths, keywords for search queries)
    
    Examples:
        "data engineer" → (["data-engineer"], ["data engineer"])
        "python developer, ML engineer" → (["python-developer", "ml-engineer"], ["python developer", "ML engineer"])
    """
    if not search_string or not search_string.strip():
        return [], []
    
    terms = [t.strip() for t in search_string.split(',') if t.strip()]
    
    # Convert to slugs (lowercase with hyphens)
    slugs = [re.sub(r'\s+', '-', term.lower()) for term in terms]
    
    # Keywords remain as original (for search APIs)
    keywords = terms
    
    return slugs, keywords


def print_summary(results: dict, combined: dict) -> None:
    """Print summary to console."""
    print("\n" + "=" * 70)
    print(" " * 15 + "JOB SCRAPING SUMMARY")
    print("=" * 70)
    print(f"\nJob Types Searched:")
    for job_type in DEFAULT_SEARCH_SLUGS:
        print(f"  • {job_type}")

    print(f"\nSources Scraped:")
    for source, payload in results.items():
        total = payload.get("meta", {}).get("total_jobs", 0)
        skipped = " [SKIPPED]" if payload.get("meta", {}).get("skipped") else ""
        print(f"  • {source}: {total} jobs{skipped}")

    print(f"\nDeduplication Summary:")
    for source, count in combined["meta"]["jobs_by_source"].items():
        print(f"  • {source}: {count} unique jobs")

    print(f"\nTotal Unique Jobs: {combined['meta']['total_jobs']}")
    print(f"\nOutput Files:")
    print(f"  • data_jobs_combined.json (all sources combined)")
    print(f"  • data_jobs_careers24.json")
    print(f"  • data_jobs_careerjunction.json")
    print(f"  • data_jobs_pnet.json")
    print(f"  • data_jobs_nri_api.json")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Unified Job Scraper - Data Roles (South Africa)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Run all scrapers with default search terms
  python main.py --search "data engineer" # Search for specific terms
  python main.py --search "python developer, ML engineer"  # Multiple terms
  python main.py --careers24              # Only Careers24 with default terms
  python main.py --careerjunction --pnet  # CareerJunction and Pnet
  python main.py --nri --search "data analyst"  # Network Recruitment with custom search
        """,
    )

    parser.add_argument("--careers24", action="store_true", help="Run Careers24 scraper")
    parser.add_argument("--careerjunction", action="store_true", help="Run CareerJunction scraper")
    parser.add_argument("--pnet", action="store_true", help="Run Pnet scraper (requires Playwright)")
    parser.add_argument("--nri", action="store_true", help="Run Network Recruitment Intl API scraper")
    parser.add_argument("--linkedin", action="store_true", help="Run LinkedIn scraper (requires API)")
    parser.add_argument("--search", type=str, help="Comma-separated search terms (e.g., 'data engineer, python developer')")
    parser.add_argument("--json", action="store_true", help="Output jobs as JSON to stdout (for pipeline integration)")

    args = parser.parse_args()

    # Parse search terms if provided
    search_slugs, search_keywords = None, None
    if args.search:
        search_slugs, search_keywords = parse_search_terms(args.search)
        log.info(f"Custom search terms: {args.search}")
        log.info(f"  Slugs: {search_slugs}")
        log.info(f"  Keywords: {search_keywords}")

    # If no specific scraper selected, run all
    run_all = not any([args.careers24, args.careerjunction, args.pnet, args.nri, args.linkedin])

    results = {}

    if run_all or args.careers24:
        results["Careers24"] = Careers24Scraper.run(search_slugs=search_slugs)

    if run_all or args.careerjunction:
        results["CareerJunction"] = CareerJunctionScraper.run(search_keywords=search_keywords)

    if run_all or args.pnet:
        results["Pnet"] = PnetScraper.run(search_slugs=search_slugs)

    if run_all or args.nri:
        results["NRI"] = NRIScraper.run()

    if run_all or args.linkedin:
        results["LinkedIn"] = LinkedInScraper.run(search_keywords=search_keywords)

    # If --json flag is set, output only JSON to stdout for pipeline
    if args.json:
        # Combine all jobs from results
        all_jobs = []
        for source_name, result in results.items():
            if result and 'jobs' in result:
                all_jobs.extend(result['jobs'])
        
        # Output JSON with markers for easy parsing (write as UTF-8 bytes to avoid encoding issues)
        json_output = json.dumps({'jobs': all_jobs}, ensure_ascii=False)
        sys.stdout.buffer.write(b'===JSON_START===\n')
        sys.stdout.buffer.write(json_output.encode('utf-8'))
        sys.stdout.buffer.write(b'\n===JSON_END===\n')
        sys.stdout.buffer.flush()
    else:
        # Normal output with file saving and summary
        combined = combine_results(results)
        print_summary(results, combined)


if __name__ == "__main__":
    main()
