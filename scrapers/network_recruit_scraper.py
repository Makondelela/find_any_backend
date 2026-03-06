"""
Network Recruitment International - Direct API Scraper
=======================================================
Calls the PlacementPartner API directly instead of scraping rendered HTML.
No Playwright required — just requests.

Usage:
    pip install requests
    python scraper_api.py

Output: data_jobs_nri_api.json
"""

import json
import logging
import sys
import io
import re
from datetime import datetime, timezone

import requests

# ── UTF-8 safe logging (Windows cp1252 fix) ─────────────────────────────────
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
if root_logger.handlers:
    root_logger.handlers.clear()
_handler = logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace"))
_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
root_logger.addHandler(_handler)
log = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
BASE_API = "https://az-jhb-was-rescr-duda-api-prod-networkrecruitint.azurewebsites.net/PlacementPartnerXml"
PAGE_SIZE = 200          # fetch more than the default 50 to get everything
NICHE     = "IT"
OUTPUT    = "data_jobs_nri_api.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.networkrecruitmentinternational.com",
    "Referer": "https://www.networkrecruitmentinternational.com/",
}

# Keywords checked against job TITLE only — must unambiguously signal a data role.
# Broad terms like "python", "sql", "data" alone are intentionally excluded
# because they appear in nearly every IT job description.
DATA_TITLE_KEYWORDS = [
    "data engineer",
    "data scientist",
    "data analyst",
    "data architect",
    "data modell",       # modeller / modelling
    "data steward",
    "data governance",
    "data quality",
    "data manager",
    "data warehou",      # warehouse / warehousing
    "etl",
    "elt ",
    "analytics engineer",
    "analytics manager",
    "business intelligence",
    " bi ",
    "bi developer",
    "bi analyst",
    "bi architect",
    "power bi",
    "tableau",
    "qlik",
    "looker",
    "machine learning",
    "ml engineer",
    "mlops",
    "databricks",
    "snowflake",
    "dbt ",                # data build tool
    "spark developer",
    "big data",
    "hadoop",
    "lakehouse",
    "data lake",
    "reporting analyst",
    "reporting developer",
    "insights analyst",
    "quantitative analyst",
    "quant ",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def fetch_all_jobs() -> list[dict]:
    """Pull all IT vacancies from the API."""
    url = f"{BASE_API}/api/getallnetworkrecruitmentadsvianiche"
    params = {"niche": NICHE, "pageSize": PAGE_SIZE}
    log.info(f"Calling API: {url}  (pageSize={PAGE_SIZE})")
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        log.info(f"[OK] API returned {len(data)} records")
        return data
    except requests.RequestException as e:
        log.error(f"API request failed: {e}")
        return []
    except ValueError as e:
        log.error(f"Failed to parse JSON: {e}")
        log.error(f"Response text: {r.text[:500]}")
        return []


def strip_html(text: str) -> str:
    """Remove HTML tags from a string."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", str(text))
    clean = re.sub(r"&amp;", "&", clean)
    clean = re.sub(r"&nbsp;", " ", clean)
    clean = re.sub(r"&lt;", "<", clean)
    clean = re.sub(r"&gt;", ">", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def is_data_job(record: dict) -> bool:
    """Return True if the job TITLE contains a data/analytics keyword.
    Deliberately title-only to avoid false positives from description text.
    """
    title = str(record.get("job_title", "")).lower()
    return any(kw in title for kw in DATA_TITLE_KEYWORDS)


def build_salary(record: dict) -> str:
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


def build_url(record: dict) -> str:
    instance = record.get("company_ref", "network1")
    ref      = record.get("vacancy_ref", "")
    return f"https://www.networkrecruitmentinternational.com/job-details?instance={instance}&vacancy_ref={ref}"


def transform(record: dict) -> dict:
    """Convert raw API record to clean job dict."""
    expiry = str(record.get("expiry_date", ""))[:10]  # trim to YYYY-MM-DD
    return {
        "title":          record.get("job_title", "").strip(),
        "company":        "Network Recruitment International",
        "location":       f"{record.get('region', '')} > {record.get('town', '')}".strip(" >"),
        "region":         record.get("region", ""),
        "town":           record.get("town", ""),
        "sector":         record.get("sector", ""),
        "salary":         build_salary(record),
        "vacancy_ref":    record.get("vacancy_ref", ""),
        "expiry_date":    expiry,
        "brief_description":  strip_html(record.get("brief_description", "")),
        "detail_description": strip_html(record.get("detail_description", "")),
        "url":            build_url(record),
        "scraped_at":     datetime.now(timezone.utc).isoformat(),
        "source":         "Network Recruitment International",
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("NRI API Scraper")
    log.info("=" * 60)

    raw = fetch_all_jobs()
    if not raw:
        log.warning("No data returned from API. Check connectivity.")
        return

    log.info(f"Processing {len(raw)} total records ...")

    all_jobs  = [transform(r) for r in raw]
    data_jobs = [j for j in all_jobs if is_data_job({"job_title": j["title"]})]

    # Deduplicate by vacancy_ref
    seen = set()
    unique_data = []
    for job in data_jobs:
        ref = job["vacancy_ref"]
        if ref not in seen:
            seen.add(ref)
            unique_data.append(job)

    log.info(f"Total IT jobs fetched:    {len(all_jobs)}")
    log.info(f"Data-related jobs found:  {len(unique_data)}")

    payload = {
        "meta": {
            "source":     "Network Recruitment International",
            "category":   "Data Jobs",
            "niche":      NICHE,
            "total_it":   len(all_jobs),
            "total_data": len(unique_data),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        },
        "jobs": unique_data,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    log.info(f"[OK] Saved {len(unique_data)} data jobs -> {OUTPUT}")
    log.info("=" * 60)
    print("\n" + "=" * 60)
    print("API SCRAPER SUMMARY")
    print("=" * 60)
    print(f"Source:         Network Recruitment International")
    print(f"Total IT jobs:  {len(all_jobs)}")
    print(f"Data jobs:      {len(unique_data)}")
    print(f"Scraped at:     {datetime.now(timezone.utc).isoformat()}")
    print(f"Output:         {OUTPUT}")
    print("=" * 60)

    # Preview first 3
    if unique_data:
        print("\nSample results:")
        for job in unique_data[:3]:
            print(f"  - {job['title']} | {job['location']} | {job['salary']}")


if __name__ == "__main__":
    main()