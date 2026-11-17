#!/usr/bin/env python3
"""
Test Firebase Job Service Integration
======================================
Run this to verify Firebase job storage works correctly.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import firebase_admin
from firebase_admin import credentials, db as firebase_db
from backend.job_service import (
    save_jobs_to_firebase,
    load_jobs_from_firebase,
    load_jobs_meta_from_firebase,
    get_jobs_statistics,
    track_job_view,
    get_user_history,
    load_user_checked_from_firebase,
    save_user_checked_to_firebase,
    update_job_checked_status,
)


def test_firebase_connection():
    """Test Firebase initialization."""
    print("Testing Firebase connection...")
    try:
        firebase_config = os.environ.get('FIREBASE_CONFIG')
        database_url = os.environ.get('FIREBASE_DATABASE_URL')

        if not database_url:
            print("✗ FIREBASE_DATABASE_URL not set")
            return False

        if not firebase_admin._apps:
            if firebase_config:
                cred_dict = json.loads(firebase_config)
                cred = credentials.Certificate(cred_dict)
            else:
                cred_path = Path(__file__).parent / 'firebase-service-account.json'
                if not cred_path.exists():
                    print("✗ Firebase service account not found")
                    return False
                cred = credentials.Certificate(str(cred_path))

            firebase_admin.initialize_app(cred, {'databaseURL': database_url})

        # Test read/write
        test_ref = firebase_db.reference('_test_connection')
        test_ref.set({'test': 'ok', 'timestamp': '2024-01-01'})
        result = test_ref.get()
        test_ref.delete()

        if result and result.get('test') == 'ok':
            print("✓ Firebase connection successful")
            return True
        else:
            print("✗ Firebase read/write test failed")
            return False

    except Exception as e:
        print(f"✗ Firebase connection failed: {e}")
        return False


import json


def test_job_operations():
    """Test job CRUD operations."""
    print("\nTesting job operations...")

    # Create test jobs
    test_jobs = [
        {
            "title": "Test Data Engineer",
            "company": "Test Company",
            "location": "Cape Town",
            "job_type": "Full-time",
            "salary": "R500000 - R800000",
            "summary": "Test job description",
            "url": "https://example.com/job/1",
            "job_id": "test-job-1",
            "posted": "2024-01-15",
            "source": "TestSource",
        },
        {
            "title": "Test Data Analyst",
            "company": "Another Company",
            "location": "Johannesburg",
            "job_type": "Contract",
            "salary": "R400000 - R600000",
            "summary": "Another test job",
            "url": "https://example.com/job/2",
            "job_id": "test-job-2",
            "posted": "2024-01-16",
            "source": "TestSource",
        },
    ]

    test_meta = {
        "sources": ["TestSource"],
        "job_types": ["Data Engineer", "Data Analyst"],
        "scraped_at": "2024-01-15T10:00:00Z",
    }

    # Save jobs
    print("  Saving test jobs to Firebase...")
    if not save_jobs_to_firebase(test_jobs, test_meta):
        print("  ✗ Failed to save jobs")
        return False
    print("  ✓ Jobs saved")

    # Load jobs
    print("  Loading jobs from Firebase...")
    loaded_jobs = load_jobs_from_firebase()
    if len(loaded_jobs) < 2:
        print(f"  ✗ Expected at least 2 jobs, got {len(loaded_jobs)}")
        return False
    print(f"  ✓ Loaded {len(loaded_jobs)} jobs")

    # Check job data
    job1 = next((j for j in loaded_jobs if j.get('job_id') == 'test-job-1'), None)
    if not job1 or job1.get('title') != 'Test Data Engineer':
        print("  ✗ Job data mismatch")
        return False
    print("  ✓ Job data correct")

    # Test metadata
    print("  Loading metadata...")
    meta = load_jobs_meta_from_firebase()
    if meta.get('total_jobs') != len(loaded_jobs):
        print(f"  ✗ Metadata mismatch: {meta}")
        return False
    print("  ✓ Metadata correct")

    # Test statistics
    print("  Getting statistics...")
    stats = get_jobs_statistics()
    print(f"  Total jobs: {stats['total_jobs']}")
    print(f"  By source: {stats['jobs_by_source']}")
    print(f"  By location: {stats['jobs_by_location']}")
    print("  ✓ Statistics working")

    # Clean up test jobs
    print("  Cleaning up test jobs...")
    jobs_ref = firebase_db.reference('jobs')
    jobs_ref.child('test-job-1').delete()
    jobs_ref.child('test-job-2').delete()
    print("  ✓ Cleanup complete")

    return True


def test_user_checked():
    """Test user checked jobs."""
    print("\nTesting user checked jobs...")

    user_id = "test-user-123"
    job_id = "test-job-checked"

    # Update checked status
    print("  Updating checked status...")
    if not update_job_checked_status(job_id, user_id, True):
        print("  ✗ Failed to update checked status")
        return False
    print("  ✓ Checked status updated")

    # Load user checked
    print("  Loading user checked...")
    checked = load_user_checked_from_firebase(user_id)
    if job_id not in checked or checked[job_id].get(user_id, {}).get('checked') != True:
        print(f"  ✗ Checked data mismatch: {checked}")
        return False
    print("  ✓ User checked data correct")

    # Clean up
    firebase_db.reference(f'user_checked/{job_id}').delete()
    print("  ✓ Cleanup complete")

    return True


def test_user_history():
    """Test user job view history."""
    print("\nTesting user job view history...")

    username = "test-user-history"
    job_id = "https://example.com/job/history-test"
    job_url = "https://example.com/job/history-test"

    # Track job view
    print("  Tracking job view...")
    if not track_job_view(username, job_id, job_url):
        print("  ✗ Failed to track job view")
        return False
    print("  ✓ Job view tracked")

    # Get history
    print("  Getting user history...")
    history = get_user_history(username)
    if not history or history[0].get('job_id') != job_id:
        print(f"  ✗ History mismatch: {history}")
        return False
    print("  ✓ History correct")

    # Clean up
    import hashlib
    firebase_node_id = hashlib.md5(job_id.encode('utf-8')).hexdigest()
    firebase_db.reference(f'user_job_views/{username}/{firebase_node_id}').delete()
    print("  ✓ Cleanup complete")

    return True


def main():
    print("=" * 60)
    print("Firebase Job Service Integration Test")
    print("=" * 60)

    # Test Firebase connection
    if not test_firebase_connection():
        sys.exit(1)

    # Test job operations
    if not test_job_operations():
        sys.exit(1)

    # Test user checked
    if not test_user_checked():
        sys.exit(1)

    # Test user history
    if not test_user_history():
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()