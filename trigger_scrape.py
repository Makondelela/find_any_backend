#!/usr/bin/env python3
"""
Remote Scraping Trigger
=======================
Simple script to trigger scraping from anywhere (phone, cron, etc.)

Usage:
    python trigger_scrape.py --url https://your-domain.com --api-key YOUR_KEY
    python trigger_scrape.py --url https://your-domain.com --api-key YOUR_KEY --search "data engineer, python"
"""

import argparse
import json
import sys
import requests


def trigger_scrape(base_url: str, api_key: str, search_terms: str = None) -> dict:
    """Trigger remote scraping via API."""
    url = f"{base_url.rstrip('/')}/api/scrape/trigger"
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    data = {}
    if search_terms:
        data["search_terms"] = search_terms

    response = requests.post(url, headers=headers, json=data, timeout=30)
    response.raise_for_status()
    return response.json()


def check_status(base_url: str) -> dict:
    """Check scraping status."""
    url = f"{base_url.rstrip('/')}/api/scrape"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Trigger remote job scraping")
    parser.add_argument("--url", required=True, help="Base URL of deployed app (e.g., https://your-domain.com)")
    parser.add_argument("--api-key", required=True, help="SCRAPE_API_KEY from server .env")
    parser.add_argument("--search", help="Custom search terms (comma-separated)")
    parser.add_argument("--status", action="store_true", help="Check scraping status instead of triggering")

    args = parser.parse_args()

    try:
        if args.status:
            result = check_status(args.url)
            print(f"Status: {result.get('status')}")
            print(f"Running: {result.get('running')}")
            print(f"Message: {result.get('message')}")
            print(f"Progress: {result.get('progress')}%")
            print(f"Last Update: {result.get('last_update')}")
        else:
            result = trigger_scrape(args.url, args.api_key, args.search)
            print(json.dumps(result, indent=2))
            if result.get("success"):
                print("\n✓ Scraping triggered successfully!")
                print("Check status with: python trigger_scrape.py --url <url> --api-key <key> --status")
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()