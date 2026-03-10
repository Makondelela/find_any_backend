#!/usr/bin/env python3
"""
LinkedIn Job Scraper - Data Roles (South Africa)
=================================================
Scrapes jobs from LinkedIn using RapidAPI.

Usage:
    python linkedin_scraper.py

Output: data_jobs_linkedin.json
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
API_BASE_URL = "http://localhost:3000/api"
OUTPUT = "data/data_jobs_linkedin.json"
DELAY_MIN = 2.0
DELAY_MAX = 4.0
LOCATION = "South Africa"
DATE_POSTED = "past_month"  # Default to past month
# ── Helpers ───────────────────────────────────────────────────────────────────

def sleep():
    t = random.uniform(DELAY_MIN, DELAY_MAX)
    log.info(f"  Waiting {t:.1f}s ...")
    time.sleep(t)


def generate_job_id(url: str, title: str, company: str) -> str:
    """Generate a unique job ID - uses URL directly to prevent duplicates across scrapes."""
    if url:
        return url
    # Fallback: hash title + company if no URL
    key = f"{title}|{company}".lower()
    return f"linkedin_{hashlib.md5(key.encode()).hexdigest()[:12]}"


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


def search_jobs(keywords: str, location: str = LOCATION, date_posted: str = DATE_POSTED) -> list[dict]:
    """
    Search LinkedIn jobs via API.
    
    Args:
        keywords: Job search keywords
        location: Job location
        date_posted: Date filter (past_24h, past_week, past_month)
    
    Returns:
        List of job dictionaries
    """
    log.info(f"  Searching: '{keywords}' in {location}")
    
    try:
        params = {
            "keywords": keywords,
            "location": location,
            "dateSincePosted": date_posted
        }
        
        response = requests.get(
            f"{API_BASE_URL}/search",
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
        
        jobs = data.get("jobs", [])
        log.info(f"  Found {len(jobs)} jobs")
        
        # Transform to standard format
        standardized_jobs = []
        for job in jobs:
            title = job.get("title", "")
            company = job.get("company", "")
            url = job.get("link", "")
            job_id = job.get("jobId", "") or generate_job_id(url, title, company)
            description = job.get("description", "")
            date_field = job.get("date", "")
            posted = extract_posted_date(description, date_field)
            
            standardized_jobs.append({
                "title": title,
                "company": company,
                "location": job.get("location", location),
                "job_type": "Full-time",
                "salary": "Not specified",
                "summary": description[:500],
                "url": url,
                "job_id": job_id,
                "posted": posted,
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
        search_keywords: Optional list of keywords to search. Uses DEFAULT_SEARCH_KEYWORDS if not provided.
    """
    log.info("\n" + "=" * 60)
    log.info("LINKEDIN - Data Jobs Scraper")
    log.info("=" * 60)
    log.info(f"Location: {LOCATION}")
    log.info(f"Date Filter: {DATE_POSTED}")
    
    # Use provided keywords or default
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
    # Check if keywords provided via command line
    if len(sys.argv) > 1:
        # Use command line keywords
        keywords = [arg.strip() for arg in sys.argv[1:]]
        main(search_keywords=keywords)
    else:
        # Use default keywords
        main()
