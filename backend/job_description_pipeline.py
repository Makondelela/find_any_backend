"""
Job Description Scraper Pipeline
=================================
Reads combined jobs JSON, visits each URL, scrapes full job descriptions,
and creates a new JSON file with descriptions linked by job_id.

Usage:
    python job_description_pipeline.py

Input:  data_jobs_combined.json
Output: data_jobs_descriptions.json
"""

import json
import logging
import sys
import io
import time
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

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
INPUT_FILE = "data/data_jobs_combined.json"
OUTPUT_FILE = "data/data_jobs_descriptions.json"
DELAY_MIN = 5.0  # Increased to reduce rate limiting
DELAY_MAX = 10.0  # Increased to reduce rate limiting
REQUEST_TIMEOUT = 90  # Increased timeout for slow-loading pages like PNet
BATCH_SIZE = 10  # Process this many jobs before asking to continue
MAX_RETRIES = 3  # Retry failed requests this many times
RETRY_DELAY_BASE = 10  # Base delay for exponential backoff

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-ZA,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


# ── Scraper Functions ─────────────────────────────────────────────────────────

def sleep():
    """Random delay between requests to be polite."""
    t = random.uniform(DELAY_MIN, DELAY_MAX)
    log.info(f"  Waiting {t:.1f}s ...")
    time.sleep(t)


def scrape_careers24_description(session: requests.Session, url: str) -> Optional[str]:
    """Scrape job description from Careers24 job page - extracts ALL text content."""
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                log.warning(f"  [HTTP {r.status_code}] {url}")
                return None
            
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Careers24 job description is in div.v-descrip within div.c24-vacancy-details
            desc_elem = (
                soup.select_one("div.v-descrip") or
                soup.select_one("div.c24-vacancy-details div.v-descrip") or
                soup.select_one("div.job-description") or
                soup.select_one("div[itemprop='description']") or
                soup.select_one("div.description")
            )
            
            if desc_elem:
                # Extract ALL text content preserving structure
                # Use get_text with separator to maintain line breaks between elements
                description = desc_elem.get_text(separator="\n", strip=False)
                # Clean up excessive whitespace but preserve structure
                lines = [line.strip() for line in description.split("\n") if line.strip()]
                description = "\n".join(lines)
                return description
            
            log.warning(f"  No description found for: {url}")
            return None
            
        except (requests.RequestException, TimeoutError, KeyboardInterrupt) as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            if attempt < MAX_RETRIES - 1:
                retry_delay = RETRY_DELAY_BASE * (2 ** attempt)
                log.warning(f"  [RETRY {attempt + 1}/{MAX_RETRIES}] {e} - {url}")
                log.info(f"  Waiting {retry_delay}s before retry...")
                time.sleep(retry_delay)
                continue
            else:
                log.error(f"  [ERROR] Failed after {MAX_RETRIES} attempts: {e} - {url}")
                return None


def scrape_careerjunction_description(session: requests.Session, url: str) -> Optional[str]:
    """Scrape job description from CareerJunction job page - extracts ALL text content."""
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                log.warning(f"  [HTTP {r.status_code}] {url}")
                return None
            
            soup = BeautifulSoup(r.text, "html.parser")
            
            # CareerJunction selectors - look for the job-details div
            desc_elem = (
                soup.select_one("div.job-details") or
                soup.select_one("div.job-details-description") or
                soup.select_one("div.job-description") or
                soup.select_one("div[itemprop='description']")
            )
            
            if desc_elem:
                # Extract ALL text content preserving structure
                description = desc_elem.get_text(separator="\n", strip=False)
                lines = [line.strip() for line in description.split("\n") if line.strip()]
                description = "\n".join(lines)
                return description
            
            log.warning(f"  No description found for: {url}")
            return None
            
        except (requests.RequestException, TimeoutError, KeyboardInterrupt) as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            if attempt < MAX_RETRIES - 1:
                retry_delay = RETRY_DELAY_BASE * (2 ** attempt)
                log.warning(f"  [RETRY {attempt + 1}/{MAX_RETRIES}] {e} - {url}")
                log.info(f"  Waiting {retry_delay}s before retry...")
                time.sleep(retry_delay)
                continue
            else:
                log.error(f"  [ERROR] Failed after {MAX_RETRIES} attempts: {e} - {url}")
                return None


def scrape_pnet_description(url: str) -> Optional[str]:
    """Scrape job description from PNet job page using Playwright - extracts from rendered DOM sections."""
    for attempt in range(MAX_RETRIES):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                
                # Navigate to the page
                page.goto(url, timeout=REQUEST_TIMEOUT * 1000, wait_until="domcontentloaded")
                
                # Wait a bit for dynamic content to load
                page.wait_for_timeout(2000)
                
                # Get the rendered HTML
                html = page.content()
                browser.close()
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Look for all section divs that contain job description content
            # Pattern: <div class="at-section-text-*" data-at="section-text-*">
            section_divs = soup.select('div[class*="at-section-text-"]')
            
            if section_divs:
                sections = []
                for section_div in section_divs:
                    # Find the article within this section
                    article = section_div.select_one('article[data-genesis-element="CARD"]')
                    if not article:
                        continue
                    
                    # Get section heading (h4)
                    heading = article.select_one('h4[data-genesis-element="TEXT"]')
                    if heading:
                        sections.append(f"\n{heading.get_text(strip=True)}\n")
                    
                    # Get section content - the actual description text
                    content = article.select_one('div[data-genesis-element="CARD_CONTENT"]')
                    if content:
                        text = content.get_text(separator="\n", strip=False)
                        lines = [line.strip() for line in text.split("\n") if line.strip()]
                        if lines:
                            sections.append("\n".join(lines))
                
                if sections:
                    description = "\n".join(sections)
                    return description
            
            log.warning(f"  No description found for: {url}")
            return None
            
        except (PWTimeout, Exception, KeyboardInterrupt) as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            if attempt < MAX_RETRIES - 1:
                retry_delay = RETRY_DELAY_BASE * (2 ** attempt)
                log.warning(f"  [RETRY {attempt + 1}/{MAX_RETRIES}] {e} - {url}")
                log.info(f"  Waiting {retry_delay}s before retry...")
                time.sleep(retry_delay)
                continue
            else:
                log.error(f"  [ERROR] Failed after {MAX_RETRIES} attempts: {e} - {url}")
                return None


def scrape_nri_description(session: requests.Session, url: str) -> Optional[str]:
    """Scrape job description from Network Recruitment International job page - extracts ALL text content."""
    try:
        r = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            log.warning(f"  [HTTP {r.status_code}] {url}")
            return None
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # NRI uses a table-based layout - look for the ReadMore class or specific td elements
        # First try the ReadMore td which contains the full description
        desc_elem = soup.select_one('td[class^="ReadMore"]')
        
        if not desc_elem:
            # Fallback: look for td with specific padding that contains job description
            desc_elem = soup.select_one('td[style*="padding-left:93px"]')
        
        if not desc_elem:
            # Another fallback: find all td elements and look for the one with substantial content
            all_tds = soup.select('td[colspan="4"]')
            for td in all_tds:
                # Look for td with meaningful job description content
                if td.get_text(strip=True) and len(td.get_text(strip=True)) > 200:
                    desc_elem = td
                    break
        
        if desc_elem:
            # Extract ALL text content preserving structure
            description = desc_elem.get_text(separator="\n", strip=False)
            lines = [line.strip() for line in description.split("\n") if line.strip()]
            description = "\n".join(lines)
            return description
        
        log.warning(f"  No description found for: {url}")
        return None
        
    except requests.RequestException as e:
        log.error(f"  [ERROR] {e} - {url}")
        return None


def scrape_linkedin_description(url: str) -> Optional[str]:
    """
    Scrape job description from LinkedIn job page using Playwright.
    LinkedIn requires JavaScript rendering for content.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navigate to the LinkedIn job page
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for the description container to load
            try:
                page.wait_for_selector('div[class*="description"]', timeout=10000)
            except PWTimeout:
                log.warning(f"  Timeout waiting for description: {url}")
                browser.close()
                return None
            
            # Extract description from the specific div structure
            # Target: div with "About the job" content
            desc_selectors = [
                'div._96097510.b79b8b84._139faa0c._6c02cb58._7ac497bf.c2a587a1._1cd67b9d.f71fadda._8b2a7df7.fa63afb9._42c7fec2',
                'div[class*="description"]',
                'div[class*="job-details"]',
                'div.show-more-less-html__markup',
            ]
            
            description = None
            for selector in desc_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        description = element.inner_text()
                        if description and len(description) > 100:
                            break
                except Exception:
                    continue
            
            browser.close()
            
            if description:
                # Clean up the description
                lines = [line.strip() for line in description.split("\n") if line.strip()]
                description = "\n".join(lines)
                log.info(f"  Scraped LinkedIn description ({len(description)} chars)")
                return description
            else:
                log.warning(f"  No description found for: {url}")
                return None
                
    except Exception as e:
        log.error(f"  [ERROR] LinkedIn scraping failed: {e} - {url}")
        return None


def scrape_job_description(session: requests.Session, job: Dict) -> Optional[str]:
    """
    Route to appropriate scraper based on job source/URL.
    Returns the full job description text.
    """
    url = job.get("url", "")
    source = job.get("source", "")
    
    if not url:
        log.warning(f"  No URL for job: {job.get('job_id', 'unknown')}")
        return None
    
    log.info(f"Scraping: {job.get('title', 'N/A')} ({source}) - {url}")
    
    # For NRI jobs, try to use existing API data fields first
    if "networkrecruitmentinternational.com" in url:
        # Log available fields for debugging
        log.info(f"  NRI job fields available: {', '.join(job.keys())}")
        
        # NRI jobs come from API with structured data - combine available description fields
        descriptions = []
        
        # Check for various description fields that might exist
        for field in ["detail_description", "brief_description", "summary", "description"]:
            content = job.get(field, "")
            if content and len(content) > 50:
                descriptions.append(content)
                log.info(f"  Found {field}: {len(content)} chars")
        
        if descriptions:
            # Combine all available descriptions, removing duplicates
            combined = "\n\n".join(descriptions)
            log.info(f"  Using existing API data for NRI job ({len(combined)} chars)")
            return combined
        
        # Fallback: try to scrape if no API data available
        log.info(f"  No API data found, attempting to scrape...")
        return scrape_nri_description(session, url)
    
    if "careers24.com" in url:
        return scrape_careers24_description(session, url)
    elif "careerjunction.co.za" in url:
        return scrape_careerjunction_description(session, url)
    elif "pnet.co.za" in url:
        return scrape_pnet_description(url)  # No session needed - uses Playwright
    elif "linkedin.com" in url:
        # LinkedIn requires JavaScript rendering - use Playwright
        return scrape_linkedin_description(url)
    else:
        log.warning(f"  Unknown job source: {url}")
        return None


# ── Main Pipeline ─────────────────────────────────────────────────────────────

def load_existing_descriptions() -> List[Dict]:
    """Load existing descriptions if the output file exists."""
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("descriptions", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def main():
    log.info("=" * 70)
    log.info("Job Description Scraper Pipeline")
    log.info("=" * 70)
    
    # Load combined jobs
    log.info(f"Loading jobs from: {INPUT_FILE}")
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        log.error(f"Input file not found: {INPUT_FILE}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON in {INPUT_FILE}: {e}")
        sys.exit(1)
    
    jobs = data.get("jobs", [])
    log.info(f"Found {len(jobs)} total jobs")
    
    # Load existing descriptions to resume
    descriptions = load_existing_descriptions()
    existing_job_ids = {d.get("job_id") for d in descriptions}
    
    if existing_job_ids:
        log.info(f"Found {len(existing_job_ids)} already processed jobs")
    
    # Initialize session
    session = requests.Session()
    
    log.info(f"\nProcessing all {len(jobs)} jobs...")
    log.info("-" * 70)
    
    # Process all jobs
    for idx, job in enumerate(jobs):
        job_id = job.get("job_id", "unknown")
        
        # Skip if already processed
        if job_id in existing_job_ids:
            log.info(f"[{idx + 1}/{len(jobs)}] ✓ Already processed: {job_id}")
            continue
        
        log.info(f"\n[{idx + 1}/{len(jobs)}] Processing job_id: {job_id}")
        
        description = scrape_job_description(session, job)
        
        # Create description record
        desc_record = {
            "job_id": job_id,
            "url": job.get("url"),
            "title": job.get("title"),
            "company": job.get("company"),
            "source": job.get("source"),
            "description": description,
            "scraped_at": datetime.now(timezone.utc).isoformat()
        }
        
        descriptions.append(desc_record)
        existing_job_ids.add(job_id)
        
        # Save after each job
        save_descriptions(descriptions, data.get("meta", {}))
        
        # Be polite - delay between requests (skip for last job)
        if idx < len(jobs) - 1 and description:
            sleep()
    
    # Final save
    log.info("\nSaving final results...")
    save_descriptions(descriptions, data.get("meta", {}))
    
    log.info("=" * 70)
    log.info(f"✓ Complete! Processed {len(descriptions)} total jobs")
    log.info(f"✓ Jobs with descriptions: {sum(1 for d in descriptions if d.get('description'))}")
    log.info(f"✓ Jobs without descriptions: {sum(1 for d in descriptions if not d.get('description'))}")
    log.info(f"✓ Output: {OUTPUT_FILE}")
    log.info("=" * 70)


def save_descriptions(descriptions: List[Dict], original_meta: Dict):
    """Save descriptions to JSON file."""
    output = {
        "meta": {
            "source_file": INPUT_FILE,
            "total_jobs": len(descriptions),
            "jobs_with_descriptions": sum(1 for d in descriptions if d.get("description")),
            "jobs_without_descriptions": sum(1 for d in descriptions if not d.get("description")),
            "original_meta": original_meta,
            "scraped_at": datetime.now(timezone.utc).isoformat()
        },
        "descriptions": descriptions
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    log.info(f"✓ Saved {len(descriptions)} descriptions to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
