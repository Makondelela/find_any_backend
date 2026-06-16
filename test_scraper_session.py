#!/usr/bin/env python3
"""Test career24 scraper with session."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

import requests
from bs4 import BeautifulSoup
from search_config import DEFAULT_SEARCH_SLUGS

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

BASE_URL = "https://www.careers24.com"

# Test with session (like the scraper)
print("=== Using Session (like scraper) ===")
session = requests.Session()

# Warm up
print("Warming up session...")
r = session.get(BASE_URL, headers=HEADERS, timeout=25)
print(f"Warmup: {r.status_code} - {len(r.text):,} chars\n")

# Get first slug
slug = DEFAULT_SEARCH_SLUGS[0]
url = f"{BASE_URL}/jobs/kw-{slug}/rmt-incl/"
print(f"Fetching: {url}")
r = session.get(url, headers=HEADERS, timeout=25)
print(f"Status: {r.status_code}")
print(f"Content-Length: {len(r.text):,} chars")

soup = BeautifulSoup(r.text, "html.parser")
cards = soup.select('div.job-card[data-control="job-card"]')
print(f"Cards found: {len(cards)}")

if len(cards) == 0:
    print("\nDEBUGGING: Checking what's in the HTML...")
    print(f"Body length: {len(soup.body.decode())}")
    
    # Check if JavaScript is present
    scripts = soup.find_all('script')
    print(f"Script tags: {len(scripts)}")
    
    # Look for JavaScript that loads jobs
    import re
    for script in scripts[:3]:
        if script.string:
            print(f"\nScript content (first 200 chars):\n{script.string[:200]}")
    
    # Look for any data in the page
    divs_with_job = soup.find_all('div', class_=re.compile('job', re.I))
    print(f"\nDivs with 'job' in class: {len(divs_with_job)}")
