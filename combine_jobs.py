#!/usr/bin/env python3
"""
Combine Job Data from Multiple Sources
=======================================
Simple script to merge all job site data into a single combined file
and save to Firebase Realtime Database.

Usage:
    python combine_jobs.py
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

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
    DATA_DIR / "data_jobs_executiveplacements.json",
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


def save_to_firebase(jobs, meta):
    """Save jobs to Firebase Realtime Database"""
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()

        import firebase_admin
        from firebase_admin import credentials, db as firebase_db

        # Initialize Firebase if not already done
        if not firebase_admin._apps:
            firebase_config = os.environ.get('FIREBASE_CONFIG')
            database_url = os.environ.get('FIREBASE_DATABASE_URL')

            if not database_url:
                print("⚠️  FIREBASE_DATABASE_URL not set, skipping Firebase save")
                return False

            if firebase_config:
                cred_dict = json.loads(firebase_config)
                cred = credentials.Certificate(cred_dict)
            else:
                cred_path = Path(__file__).parent / 'firebase-service-account.json'
                if not cred_path.exists():
                    print("⚠️  Firebase service account not found, skipping Firebase save")
                    return False
                cred = credentials.Certificate(str(cred_path))

            firebase_admin.initialize_app(cred, {'databaseURL': database_url})

        # Save jobs to Firebase
        jobs_ref = firebase_db.reference('jobs')
        meta_ref = firebase_db.reference('jobs_meta')

        jobs_data = {}
        for job in jobs:
            job_key = job.get('job_id') or job.get('url')
            if not job_key:
                job_key = f"{job.get('title', '')}|{job.get('company', '')}".replace('/', '_').replace('.', '_')

            job_key = job_key.replace('.', '_').replace('$', '_').replace('#', '_').replace('[', '_').replace(']', '_').replace('/', '_')

            if 'scraped_at' not in job:
                job['scraped_at'] = datetime.now(timezone.utc).isoformat()

            jobs_data[job_key] = job

        jobs_ref.set(jobs_data)
        print(f"✓ Saved {len(jobs_data)} jobs to Firebase")

        meta['total_jobs'] = len(jobs_data)
        meta['updated_at'] = datetime.now(timezone.utc).isoformat()
        meta_ref.set(meta)
        print(f"✓ Saved jobs metadata to Firebase")

        return True

    except Exception as e:
        print(f"✗ Error saving to Firebase: {e}")
        return False


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
    meta = {
        "sources": [f.stem.replace("data_jobs_", "") for f in SOURCE_FILES if f.exists()],
        "total_jobs": len(all_jobs),
        "combined_at": datetime.now(timezone.utc).isoformat(),
    }
    combined_data = {
        "meta": meta,
        "jobs": all_jobs,
    }

    # Save combined file locally
    DATA_DIR.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved to: {OUTPUT_FILE}")

    # Also save to Firebase
    print("\nSaving to Firebase...")
    if save_to_firebase(all_jobs, meta):
        print("✓ Firebase sync complete")
    else:
        print("⚠️  Firebase sync skipped or failed")

    print("=" * 60)


if __name__ == "__main__":
    main()