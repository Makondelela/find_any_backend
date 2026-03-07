#!/usr/bin/env python3
"""
Combine Job Data from Multiple Sources
=======================================
Simple script to merge all job site data into a single combined file.

Usage:
    python combine_jobs.py
"""

import json
from pathlib import Path
from datetime import datetime, timezone

# Paths
DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / "data_jobs_combined.json"

# Source files
SOURCE_FILES = [
    DATA_DIR / "data_jobs_careers24.json",
    DATA_DIR / "data_jobs_careerjunction.json",
    DATA_DIR / "data_jobs_pnet.json",
    DATA_DIR / "data_jobs_nri_api.json",
    DATA_DIR / "data_jobs_linkedin.json",
]


def load_jobs_from_file(filepath):
    """Load jobs from a source file"""
    if not filepath.exists():
        print(f"⚠️  {filepath.name} not found, skipping...")
        return []
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            jobs = data.get("jobs", [])
            print(f"✓ {filepath.name}: {len(jobs)} jobs")
            return jobs
    except Exception as e:
        print(f"✗ Error reading {filepath.name}: {e}")
        return []


def main():
    print("=" * 60)
    print("Combining Jobs from All Sources")
    print("=" * 60)
    
    all_jobs = []
    seen_ids = set()
    
    # Load jobs from each source
    for source_file in SOURCE_FILES:
        jobs = load_jobs_from_file(source_file)
        
        # Deduplicate by job_id or URL
        for job in jobs:
            job_id = job.get("job_id") or job.get("url")
            if job_id and job_id not in seen_ids:
                seen_ids.add(job_id)
                all_jobs.append(job)
    
    print()
    print(f"Total unique jobs: {len(all_jobs)}")
    
    # Create combined output
    combined_data = {
        "meta": {
            "sources": [f.stem.replace("data_jobs_", "") for f in SOURCE_FILES if f.exists()],
            "total_jobs": len(all_jobs),
            "combined_at": datetime.now(timezone.utc).isoformat(),
        },
        "jobs": all_jobs,
    }
    
    # Save combined file
    DATA_DIR.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved to: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
