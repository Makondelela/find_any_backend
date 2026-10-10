"""Executive Placements job listing scraper."""

import json
import logging
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


class ExecutivePlacementsScraper:
    BASE_URL = "https://www.executiveplacements.com"
    OUTPUT = "data/data_jobs_executiveplacements.json"
    MAX_PAGES = 5
    RESULTS_PER_PAGE = 10
    DELAY_MIN = 1.0
    DELAY_MAX = 2.0
    SUPPLEMENTAL_KEYWORDS = ("Integration", "Integration Developer", "Integration Engineer")
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-ZA,en-GB;q=0.9,en;q=0.8",
    }

    @staticmethod
    def build_url(keyword: str) -> str:
        return f"{ExecutivePlacementsScraper.BASE_URL}/jobList.asp?{urlencode({'kwds': keyword})}"

    @staticmethod
    def get_page(
        session: requests.Session,
        url: str,
        data: Optional[dict[str, str]] = None,
    ) -> Optional[BeautifulSoup]:
        try:
            if data is None:
                response = session.get(url, headers=ExecutivePlacementsScraper.HEADERS, timeout=30)
            else:
                response = session.post(url, data=data, headers=ExecutivePlacementsScraper.HEADERS, timeout=30)
            if response.status_code != 200:
                log.warning("  [HTTP %s] %s", response.status_code, url)
                return None
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException as exc:
            log.warning("  [ERROR] Executive Placements request failed: %s", exc)
            return None

    @staticmethod
    def form_data(soup: BeautifulSoup, keyword: str, page: int) -> tuple[str, dict[str, str]]:
        form = soup.select_one('form[name="jobSearch"]')
        values: dict[str, str] = {}
        action = f"{ExecutivePlacementsScraper.BASE_URL}/jobList.asp"
        if form:
            action = urljoin(ExecutivePlacementsScraper.BASE_URL + "/", form.get("action", "JobList.asp"))
            for field in form.select("input[name], select[name]"):
                name = field.get("name")
                if not name:
                    continue
                if field.name == "input":
                    field_type = (field.get("type") or "text").lower()
                    if field_type in {"submit", "button", "image", "reset", "file"}:
                        continue
                    if field_type in {"checkbox", "radio"} and not field.has_attr("checked"):
                        continue
                    values[name] = field.get("value", "")
                else:
                    options = field.select("option")
                    selected = next((option for option in options if option.has_attr("selected")), None)
                    if selected is None and options:
                        selected = options[0]
                    if selected is not None:
                        values[name] = selected.get("value", selected.get_text(strip=True))
        values["kwds"] = keyword
        values["start"] = str(page)
        return action, values

    @staticmethod
    def total_pages(soup: BeautifulSoup) -> int:
        text = soup.get_text(" ", strip=True)
        match = re.search(r"Showing\s+\d+\s+to\s+\d+\s+of\s+([\d,]+)\s+jobs", text, re.I)
        if match:
            total = int(match.group(1).replace(",", ""))
            pages = -(-total // ExecutivePlacementsScraper.RESULTS_PER_PAGE)
            return min(ExecutivePlacementsScraper.MAX_PAGES, max(1, pages))

        page_numbers = []
        for link in soup.select("a[href]"):
            page_match = re.search(r"start\.value\s*=\s*(\d+)", link.get("href", ""), re.I)
            if page_match:
                page_numbers.append(int(page_match.group(1)))
        return min(ExecutivePlacementsScraper.MAX_PAGES, max(page_numbers, default=1))

    @staticmethod
    def parse_cards(soup: BeautifulSoup, keyword: str) -> list[dict]:
        jobs = []
        cards = soup.select("div.entry")
        log.info("  Found %s Executive Placements listings", len(cards))
        for card in cards:
            title_element = card.select_one("strong span")
            details_link = next(
                (link for link in card.select("a[href]") if link.get_text(" ", strip=True).lower() == "details"),
                None,
            )
            if not title_element or not details_link:
                continue

            title = title_element.get_text(" ", strip=True)
            if not title:
                continue
            text_parts = list(card.stripped_strings)
            details_index = next(
                (index for index, part in enumerate(text_parts) if part.lower() == "details"),
                len(text_parts),
            )
            listing_parts = text_parts[:details_index]
            salary_index = next(
                (index for index, part in enumerate(listing_parts) if part.lower().startswith("salary:")),
                None,
            )
            salary = listing_parts[salary_index].partition(":")[2].strip() if salary_index is not None else ""
            description_start = salary_index + 1 if salary_index is not None else 3
            detail_url = urljoin(ExecutivePlacementsScraper.BASE_URL, details_link.get("href", ""))
            job_id_match = re.search(r"/(\d+)-Job-Search-", detail_url, re.I)
            if not job_id_match:
                job_id_match = re.search(r"showJob\(\s*\d+\s*,\s*(\d+)\s*\)", card.get("onclick", ""), re.I)

            jobs.append({
                "title": title,
                "company": "",
                "location": listing_parts[1] if len(listing_parts) > 1 else "",
                "job_type": "",
                "salary": salary,
                "summary": " ".join(listing_parts[description_start:]).strip(),
                "url": detail_url,
                "job_id": job_id_match.group(1) if job_id_match else "",
                "posted": listing_parts[2] if len(listing_parts) > 2 else "",
                "keyword": keyword,
                "source": "Executive Placements",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })
        return jobs

    @staticmethod
    def scrape_keyword(session: requests.Session, keyword: str) -> list[dict]:
        log.info("\n--- Executive Placements keyword: '%s' ---", keyword)
        first_page = ExecutivePlacementsScraper.get_page(
            session,
            ExecutivePlacementsScraper.build_url(keyword),
        )
        if first_page is None:
            return []

        jobs = ExecutivePlacementsScraper.parse_cards(first_page, keyword)
        for page_number in range(2, ExecutivePlacementsScraper.total_pages(first_page) + 1):
            time.sleep(random.uniform(ExecutivePlacementsScraper.DELAY_MIN, ExecutivePlacementsScraper.DELAY_MAX))
            page_url, values = ExecutivePlacementsScraper.form_data(first_page, keyword, page_number)
            page_soup = ExecutivePlacementsScraper.get_page(session, page_url, values)
            if page_soup is None:
                break
            page_jobs = ExecutivePlacementsScraper.parse_cards(page_soup, keyword)
            if not page_jobs:
                break
            jobs.extend(page_jobs)
        return jobs

    @classmethod
    def get_keywords(cls, search_keywords: Optional[list[str]] = None) -> list[str]:
        base_keywords = search_keywords or ["Software Developer", "Software Engineer", "Integration", "Engineering"]
        keywords = []
        seen_keywords = set()
        for keyword in [*base_keywords, *cls.SUPPLEMENTAL_KEYWORDS]:
            normalized_keyword = keyword.casefold()
            if normalized_keyword not in seen_keywords:
                seen_keywords.add(normalized_keyword)
                keywords.append(keyword)
        return keywords

    @staticmethod
    def run(search_keywords: Optional[list[str]] = None) -> dict:
        keywords = ExecutivePlacementsScraper.get_keywords(search_keywords)
        session = requests.Session()
        all_jobs = []
        seen_keys = set()
        for keyword in keywords:
            for job in ExecutivePlacementsScraper.scrape_keyword(session, keyword):
                key = job.get("job_id") or job.get("url") or f"{job['title']}|{job['location']}"
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    all_jobs.append(job)
            time.sleep(random.uniform(ExecutivePlacementsScraper.DELAY_MIN, ExecutivePlacementsScraper.DELAY_MAX))

        payload = {
            "meta": {
                "source": "Executive Placements",
                "keywords": keywords,
                "total_jobs": len(all_jobs),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            },
            "jobs": all_jobs,
        }
        output_path = Path(ExecutivePlacementsScraper.OUTPUT)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("[OK] Saved %s jobs -> %s", len(all_jobs), output_path)
        return payload