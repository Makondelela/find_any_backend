"""
Firebase Job Data Service
=========================
Handles storing and retrieving job data from Firebase Realtime Database.
Replaces the JSON file-based storage for production deployment.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from collections import defaultdict

from firebase_admin import db as firebase_db

log = logging.getLogger(__name__)

# Firebase paths
JOBS_PATH = 'jobs'
JOBS_META_PATH = 'jobs_meta'
USER_CHECKED_PATH = 'user_checked'
USER_HISTORY_PATH = 'user_job_views'

# Local fallback paths (for development)
DATA_DIR = Path(__file__).parent.parent / 'data'
COMBINED_JOBS_FILE = DATA_DIR / 'data_jobs_combined.json'
USER_CHECKED_FILE = DATA_DIR / 'user_checked.json'
USER_HISTORY_FILE = DATA_DIR / 'user_history.json'


def _get_jobs_ref():
    """Get Firebase reference for jobs."""
    return firebase_db.reference(JOBS_PATH)


def _get_jobs_meta_ref():
    """Get Firebase reference for jobs metadata."""
    return firebase_db.reference(JOBS_META_PATH)


def _get_user_checked_ref(user_id: str = None):
    """Get Firebase reference for user checked jobs."""
    if user_id:
        return firebase_db.reference(f'{USER_CHECKED_PATH}/{user_id}')
    return firebase_db.reference(USER_CHECKED_PATH)


def _get_user_history_ref(username: str = None):
    """Get Firebase reference for user job view history."""
    if username:
        return firebase_db.reference(f'{USER_HISTORY_PATH}/{username}')
    return firebase_db.reference(USER_HISTORY_PATH)


def _now_iso():
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


# ══════════════════════════════════════════════════════════════════════════════
# JOBS OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def save_jobs_to_firebase(jobs: List[Dict], meta: Dict = None) -> bool:
    """
    Save all jobs to Firebase Realtime Database.

    Args:
        jobs: List of job dictionaries
        meta: Optional metadata dictionary

    Returns:
        True if successful, False otherwise
    """
    try:
        jobs_ref = _get_jobs_ref()
        meta_ref = _get_jobs_meta_ref()

        # Prepare jobs data - use job_id or URL as key
        jobs_data = {}
        for job in jobs:
            job_key = job.get('job_id') or job.get('url')
            if not job_key:
                # Generate key from title + company if neither exists
                job_key = f"{job.get('title', '')}|{job.get('company', '')}".replace('/', '_').replace('.', '_')

            # Sanitize key for Firebase (no . $ # [ ] /)
            job_key = job_key.replace('.', '_').replace('$', '_').replace('#', '_').replace('[', '_').replace(']', '_').replace('/', '_')

            # Ensure job has scraped_at timestamp
            if 'scraped_at' not in job:
                job['scraped_at'] = _now_iso()

            jobs_data[job_key] = job

        # Save jobs
        jobs_ref.set(jobs_data)
        log.info(f"Saved {len(jobs_data)} jobs to Firebase")

        # Save metadata
        if meta is None:
            meta = {}
        meta['total_jobs'] = len(jobs_data)
        meta['updated_at'] = _now_iso()
        meta_ref.set(meta)
        log.info(f"Saved jobs metadata to Firebase")

        return True

    except Exception as e:
        log.error(f"Error saving jobs to Firebase: {e}")
        return False


def load_jobs_from_firebase() -> List[Dict]:
    """
    Load all jobs from Firebase Realtime Database.

    Returns:
        List of job dictionaries
    """
    try:
        jobs_ref = _get_jobs_ref()
        jobs_data = jobs_ref.get()

        if not jobs_data:
            log.warning("No jobs found in Firebase")
            return []

        # Convert from dict to list
        jobs = list(jobs_data.values())
        log.info(f"Loaded {len(jobs)} jobs from Firebase")
        return jobs

    except Exception as e:
        log.error(f"Error loading jobs from Firebase: {e}")
        return []


def load_jobs_meta_from_firebase() -> Dict:
    """Load jobs metadata from Firebase."""
    try:
        meta_ref = _get_jobs_meta_ref()
        meta = meta_ref.get() or {}
        return meta
    except Exception as e:
        log.error(f"Error loading jobs metadata from Firebase: {e}")
        return {}


def get_job_count() -> int:
    """Get total job count from Firebase metadata."""
    meta = load_jobs_meta_from_firebase()
    return meta.get('total_jobs', 0)


def get_jobs_stats() -> Dict:
    """Get job statistics from Firebase."""
    try:
        jobs = load_jobs_from_firebase()

        jobs_by_source = defaultdict(int)
        jobs_by_location = defaultdict(int)

        for job in jobs:
            source = job.get('source', 'Unknown')
            location = job.get('location', 'Unknown')
            jobs_by_source[source] += 1
            jobs_by_location[location] += 1

        meta = load_jobs_meta_from_firebase()

        return {
            'total_jobs': len(jobs),
            'jobs_by_source': dict(jobs_by_source),
            'jobs_by_location': dict(jobs_by_location),
            'combined_at': meta.get('updated_at', 'Unknown'),
            'sources': meta.get('sources', []),
        }
    except Exception as e:
        log.error(f"Error getting job stats: {e}")
        return {
            'total_jobs': 0,
            'jobs_by_source': {},
            'jobs_by_location': {},
            'combined_at': 'Unknown',
        }


# ══════════════════════════════════════════════════════════════════════════════
# USER CHECKED JOBS
# ══════════════════════════════════════════════════════════════════════════════

def load_user_checked_from_firebase(user_id: str = None) -> Dict:
    """
    Load user checked jobs from Firebase.

    Args:
        user_id: Optional user ID to filter checked jobs for specific user

    Returns:
        Dictionary of checked jobs keyed by job_id, each containing user-specific data
    """
    try:
        ref = _get_user_checked_ref()
        data = ref.get() or {}

        if user_id:
            # Filter for specific user
            filtered = {}
            for job_id, users in data.items():
                if user_id in users:
                    filtered[job_id] = {user_id: users[user_id]}
            return filtered

        return data
    except Exception as e:
        log.error(f"Error loading user checked from Firebase: {e}")
        return {}


def save_user_checked_to_firebase(data: Dict, user_id: str = None) -> bool:
    """
    Save user checked jobs to Firebase.

    Args:
        data: Dictionary of checked jobs
        user_id: Optional user ID to save for specific user

    Returns:
        True if successful
    """
    try:
        ref = _get_user_checked_ref(user_id)
        ref.set(data)
        return True
    except Exception as e:
        log.error(f"Error saving user checked to Firebase: {e}")
        return False


def update_job_checked_status(job_id: str, user: str, checked: bool) -> bool:
    """
    Update checked status for a specific job and user.

    Args:
        job_id: Job ID
        user: User identifier (email or uid)
        checked: Boolean checked status

    Returns:
        True if successful
    """
    try:
        # Sanitize job_id for Firebase key
        safe_job_id = job_id.replace('.', '_').replace('$', '_').replace('#', '_').replace('[', '_').replace(']', '_').replace('/', '_')

        ref = _get_user_checked_ref().child(safe_job_id).child(user)
        ref.set({
            'checked': checked,
            'timestamp': _now_iso()
        })
        return True
    except Exception as e:
        log.error(f"Error updating checked status: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# USER HISTORY (JOB VIEWS)
# ══════════════════════════════════════════════════════════════════════════════

def track_job_view(username: str, job_id: str, job_url: str = '') -> bool:
    """
    Track when a user views a job.

    Args:
        username: User identifier (Firebase UID)
        job_id: Job ID or URL
        job_url: Optional job URL

    Returns:
        True if successful
    """
    try:
        import hashlib

        # Hash job_id if it's a URL to create valid Firebase node name
        firebase_node_id = job_id
        if job_id.startswith('http://') or job_id.startswith('https://'):
            firebase_node_id = hashlib.md5(job_id.encode('utf-8')).hexdigest()

        ref = _get_user_history_ref(username).child(firebase_node_id)
        existing = ref.get()

        if existing:
            return True  # Already tracked

        ref.set({
            'job_id': job_id,
            'job_url': job_url,
            'viewed_at': _now_iso()
        })
        log.info(f"Tracked job view: user={username}, job={job_id}")
        return True

    except Exception as e:
        log.error(f"Error tracking job view: {e}")
        return False


def get_user_history_from_firebase(username: str) -> List[Dict]:
    """
    Get user's job viewing history from Firebase.

    Args:
        username: User identifier (Firebase UID)

    Returns:
        List of viewed job records
    """
    try:
        ref = _get_user_history_ref(username)
        data = ref.get()

        if not data:
            return []

        viewed_jobs = []
        for job_key, job_data in data.items():
            viewed_jobs.append({
                'job_id': job_data.get('job_id', job_key),
                'job_url': job_data.get('job_url', ''),
                'viewed_at': job_data.get('viewed_at', '')
            })

        # Sort by viewed_at descending
        viewed_jobs.sort(key=lambda x: x.get('viewed_at', ''), reverse=True)
        return viewed_jobs

    except Exception as e:
        log.error(f"Error getting user history: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# LOCAL FILE FALLBACK (for development)
# ══════════════════════════════════════════════════════════════════════════════

def save_jobs_to_local(jobs: List[Dict], meta: Dict = None) -> bool:
    """Save jobs to local JSON file (development fallback)."""
    try:
        DATA_DIR.mkdir(exist_ok=True)
        if meta is None:
            meta = {}
        meta['total_jobs'] = len(jobs)
        meta['combined_at'] = _now_iso()

        combined_data = {
            'meta': meta,
            'jobs': jobs
        }

        with open(COMBINED_JOBS_FILE, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)

        log.info(f"Saved {len(jobs)} jobs to local file: {COMBINED_JOBS_FILE}")
        return True
    except Exception as e:
        log.error(f"Error saving jobs to local file: {e}")
        return False


def load_jobs_from_local() -> List[Dict]:
    """Load jobs from local JSON file (development fallback)."""
    try:
        if not COMBINED_JOBS_FILE.exists():
            return []

        with open(COMBINED_JOBS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        jobs = data.get('jobs', [])
        log.info(f"Loaded {len(jobs)} jobs from local file")
        return jobs
    except Exception as e:
        log.error(f"Error loading jobs from local file: {e}")
        return []


def load_user_checked_from_local(user_id: str = None) -> Dict:
    """Load user checked jobs from local JSON file."""
    try:
        if not USER_CHECKED_FILE.exists():
            return {}

        with open(USER_CHECKED_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if user_id:
            # Filter for specific user
            filtered = {}
            for job_id, users in data.items():
                if user_id in users:
                    filtered[job_id] = {user_id: users[user_id]}
            return filtered

        return data
    except Exception as e:
        log.error(f"Error loading user checked from local: {e}")
        return {}


def save_user_checked_to_local(data: Dict) -> bool:
    """Save user checked jobs to local JSON file."""
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(USER_CHECKED_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log.error(f"Error saving user checked to local: {e}")
        return False


def load_user_history_from_local(username: str) -> List[Dict]:
    """Load user history from local JSON file."""
    try:
        if not USER_HISTORY_FILE.exists():
            return []

        with open(USER_HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data.get(username, [])
    except Exception as e:
        log.error(f"Error loading user history from local: {e}")
        return []


def save_user_history_to_local(username: str, history: List[Dict]) -> bool:
    """Save user history to local JSON file."""
    try:
        DATA_DIR.mkdir(exist_ok=True)

        # Load existing data
        all_data = {}
        if USER_HISTORY_FILE.exists():
            with open(USER_HISTORY_FILE, 'r', encoding='utf-8') as f:
                all_data = json.load(f)

        all_data[username] = history

        with open(USER_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log.error(f"Error saving user history to local: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED INTERFACE (auto-detects Firebase availability)
# ══════════════════════════════════════════════════════════════════════════════

_firebase_available = None


def _check_firebase_available() -> bool:
    """Check if Firebase is available and initialized."""
    global _firebase_available
    if _firebase_available is not None:
        return _firebase_available

    try:
        # Try to access Firebase
        _get_jobs_ref()
        _firebase_available = True
        return True
    except Exception:
        _firebase_available = False
        return False


def save_jobs(jobs: List[Dict], meta: Dict = None) -> bool:
    """Save jobs - uses Firebase if available, otherwise local file."""
    if _check_firebase_available():
        return save_jobs_to_firebase(jobs, meta)
    else:
        log.warning("Firebase not available, falling back to local file storage")
        return save_jobs_to_local(jobs, meta)


def load_jobs() -> List[Dict]:
    """Load jobs - uses Firebase if available, otherwise local file."""
    if _check_firebase_available():
        return load_jobs_from_firebase()
    else:
        log.warning("Firebase not available, falling back to local file storage")
        return load_jobs_from_local()


def load_jobs_meta() -> Dict:
    """Load jobs metadata."""
    if _check_firebase_available():
        return load_jobs_meta_from_firebase()
    else:
        try:
            if COMBINED_JOBS_FILE.exists():
                with open(COMBINED_JOBS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get('meta', {})
        except Exception:
            pass
        return {}


def get_jobs_statistics() -> Dict:
    """Get job statistics."""
    if _check_firebase_available():
        return get_jobs_stats()
    else:
        jobs = load_jobs_from_local()
        jobs_by_source = defaultdict(int)
        jobs_by_location = defaultdict(int)

        for job in jobs:
            jobs_by_source[job.get('source', 'Unknown')] += 1
            jobs_by_location[job.get('location', 'Unknown')] += 1

        meta = load_jobs_meta()
        return {
            'total_jobs': len(jobs),
            'jobs_by_source': dict(jobs_by_source),
            'jobs_by_location': dict(jobs_by_location),
            'combined_at': meta.get('combined_at', 'Unknown'),
        }


def load_user_checked(user_id: str = None) -> Dict:
    """Load user checked jobs."""
    if _check_firebase_available():
        return load_user_checked_from_firebase(user_id)
    else:
        return load_user_checked_from_local()


def save_user_checked(data: Dict, user_id: str = None) -> bool:
    """Save user checked jobs."""
    if _check_firebase_available():
        return save_user_checked_to_firebase(data, user_id)
    else:
        return save_user_checked_to_local(data)


def update_checked(job_id: str, user: str, checked: bool) -> bool:
    """Update job checked status."""
    if _check_firebase_available():
        return update_job_checked_status(job_id, user, checked)
    else:
        # Local fallback
        user_checked = load_user_checked_from_local()
        if job_id not in user_checked:
            user_checked[job_id] = {}
        user_checked[job_id][user] = {
            'checked': checked,
            'timestamp': _now_iso()
        }
        return save_user_checked_to_local(user_checked)


def track_job_view_unified(username: str, job_id: str, job_url: str = '') -> bool:
    """Track job view - unified interface."""
    if _check_firebase_available():
        return track_job_view(username, job_id, job_url)
    else:
        # Local fallback - append to user history
        history = load_user_history_from_local(username)
        # Check if already exists
        for item in history:
            if item.get('job_id') == job_id:
                return True
        history.append({
            'job_id': job_id,
            'job_url': job_url,
            'viewed_at': _now_iso()
        })
        return save_user_history_to_local(username, history)


def get_user_history(username: str) -> List[Dict]:
    """Get user job view history."""
    if _check_firebase_available():
        return get_user_history_from_firebase(username)
    else:
        return load_user_history_from_local(username)