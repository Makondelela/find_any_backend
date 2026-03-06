"""
Firebase Database Service
=========================
Service for interacting with Firebase Realtime Database.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
from pathlib import Path

logger = logging.getLogger(__name__)


class FirebaseService:
    """Service for Firebase Realtime Database operations."""
    
    def __init__(self, config):
        """Initialize Firebase service."""
        self.config = config
        self._initialized = False
        self._init_firebase()
    
    def _init_firebase(self):
        """Initialize Firebase Admin SDK."""
        if self._initialized:
            return
        
        try:
            # Look for Firebase credentials
            cred_path = Path(self.config.BASE_DIR) / 'firebase.config.json'
            
            if not cred_path.exists():
                logger.warning("Firebase config not found, using application default credentials")
                cred = credentials.ApplicationDefault()
            else:
                cred = credentials.Certificate(str(cred_path))
            
            # Initialize Firebase App
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://find-any-55a42-default-rtdb.firebaseio.com'
            })
            
            self._initialized = True
            logger.info("Firebase initialized successfully")
            
            # Initialize default sources if they don't exist
            self._init_default_sources()
            
        except Exception as e:
            logger.error(f"Error initializing Firebase: {e}")
            raise
    
    def _init_default_sources(self):
        """Initialize default job sources in Firebase if they don't exist."""
        try:
            sources_ref = db.reference('sources')
            existing = sources_ref.get() or {}
            
            default_sources = {
                'linkedin': {'name': 'LinkedIn', 'jobCount': 0},
                'pnet': {'name': 'PNet', 'jobCount': 0},
                'careerjunction': {'name': 'CareerJunction', 'jobCount': 0},
                'careers24': {'name': 'Careers24', 'jobCount': 0},
                'networkrecruitment': {'name': 'Network Recruitment', 'jobCount': 0}
            }
            
            # Add missing sources
            updated = False
            for source_id, source_data in default_sources.items():
                if source_id not in existing:
                    sources_ref.child(source_id).set(source_data)
                    logger.info(f"Added missing source: {source_id}")
                    updated = True
            
            if updated:
                logger.info("Updated job sources in Firebase")
            elif not existing:
                logger.info("Initialized default job sources in Firebase")
                
        except Exception as e:
            logger.warning(f"Could not initialize default sources: {e}")
    
    # ==================== JOB OPERATIONS ====================
    
    def save_job(self, source: str, job_id: str, job_data: Dict) -> bool:
        """
        Save a job to Firebase.
        
        Args:
            source: Job source (linkedin, pnet, etc.)
            job_id: Unique job identifier
            job_data: Job data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            ref = db.reference(f'jobs/{source}/{job_id}')
            
            # Add metadata
            job_data['updatedAt'] = datetime.utcnow().isoformat()
            
            ref.set(job_data)
            logger.debug(f"Saved job {job_id} to {source}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving job {job_id}: {e}")
            return False
    
    def job_exists(self, source: str, job_id: str) -> bool:
        """Check if a job already exists."""
        try:
            ref = db.reference(f'jobs/{source}/{job_id}')
            return ref.get() is not None
        except Exception as e:
            logger.error(f"Error checking job existence: {e}")
            return False
    
    def get_job(self, source: str, job_id: str) -> Optional[Dict]:
        """Get a specific job."""
        try:
            ref = db.reference(f'jobs/{source}/{job_id}')
            return ref.get()
        except Exception as e:
            logger.error(f"Error getting job: {e}")
            return None
    
    def get_all_jobs(self, source: Optional[str] = None) -> List[Dict]:
        """Get all jobs, optionally filtered by source."""
        try:
            if source:
                ref = db.reference(f'jobs/{source}')
                jobs_data = ref.get()
                if not jobs_data:
                    return []
                return [
                    {**job, 'id': job_id, 'source': source}
                    for job_id, job in jobs_data.items()
                ]
            else:
                ref = db.reference('jobs')
                all_sources = ref.get()
                if not all_sources:
                    return []
                
                jobs = []
                for src, jobs_data in all_sources.items():
                    if jobs_data:
                        for job_id, job in jobs_data.items():
                            jobs.append({**job, 'id': job_id, 'source': src})
                
                return jobs
                
        except Exception as e:
            logger.error(f"Error getting jobs: {e}")
            return []
    
    def update_job_description(self, source: str, job_id: str, description: str) -> bool:
        """Update job description."""
        try:
            ref = db.reference(f'jobs/{source}/{job_id}')
            ref.update({
                'description': description,
                'descriptionUpdatedAt': datetime.utcnow().isoformat()
            })
            logger.debug(f"Updated description for {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating description: {e}")
            return False
    
    def update_job_experience(self, source: str, job_id: str, experience: str) -> bool:
        """Update job experience requirement."""
        try:
            ref = db.reference(f'jobs/{source}/{job_id}')
            ref.update({
                'experience': experience,
                'experienceUpdatedAt': datetime.utcnow().isoformat()
            })
            logger.debug(f"Updated experience for {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating experience: {e}")
            return False
    
    # ==================== SOURCE OPERATIONS ====================
    
    def update_source_metadata(self, source_id: str, metadata: Dict) -> bool:
        """Update source metadata after scraping."""
        try:
            ref = db.reference(f'sources/{source_id}')
            metadata['updatedAt'] = datetime.utcnow().isoformat()
            ref.update(metadata)
            logger.info(f"Updated metadata for {source_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating source metadata: {e}")
            return False
    
    def get_source_metadata(self, source_id: str) -> Optional[Dict]:
        """Get source metadata."""
        try:
            ref = db.reference(f'sources/{source_id}')
            return ref.get()
        except Exception as e:
            logger.error(f"Error getting source metadata: {e}")
            return None
    
    # ==================== SCRAPE JOB OPERATIONS ====================
    
    def create_scrape_job(self, sources: List[str]) -> str:
        """Create a new scrape job."""
        try:
            ref = db.reference('scrapeJobs')
            new_job_ref = ref.push({
                'source': ','.join(sources),
                'status': 'pending',
                'progress': 0,
                'startedAt': datetime.utcnow().isoformat(),
                'stats': {
                    'totalJobs': 0,
                    'newJobs': 0,
                    'skippedJobs': 0,
                    'descriptionsProcessed': 0,
                    'experienceExtracted': 0
                }
            })
            job_id = new_job_ref.key
            logger.info(f"Created scrape job {job_id} for sources: {sources}")
            return job_id
        except Exception as e:
            logger.error(f"Error creating scrape job: {e}")
            raise
    
    def update_scrape_job(self, job_id: str, updates: Dict) -> bool:
        """Update scrape job status."""
        try:
            ref = db.reference(f'scrapeJobs/{job_id}')
            updates['updatedAt'] = datetime.utcnow().isoformat()
            ref.update(updates)
            logger.debug(f"Updated scrape job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating scrape job: {e}")
            return False
    
    def get_scrape_job(self, job_id: str) -> Optional[Dict]:
        """Get scrape job by ID."""
        try:
            ref = db.reference(f'scrapeJobs/{job_id}')
            return ref.get()
        except Exception as e:
            logger.error(f"Error getting scrape job: {e}")
            return None
    
    # ==================== USER TRACKING ====================
    
    def mark_job_viewed(self, user_id: str, source: str, job_id: str) -> bool:
        """Mark a job as viewed by user."""
        try:
            # Sanitize user_id for Firebase (replace @ and . which are illegal)
            safe_user_id = user_id.replace('@', '_at_').replace('.', '_')
            ref = db.reference(f'users/{safe_user_id}/viewedJobs/{source}/{job_id}')
            ref.set({
                'viewedAt': datetime.utcnow().isoformat()
            })
            return True
        except Exception as e:
            logger.error(f"Error marking job as viewed: {e}")
            return False
    
    def get_user_viewed_jobs(self, user_id: str) -> List[str]:
        """Get list of job IDs viewed by user."""
        try:
            # Sanitize user_id for Firebase (replace @ and . which are illegal)
            safe_user_id = user_id.replace('@', '_at_').replace('.', '_')
            ref = db.reference(f'users/{safe_user_id}/viewedJobs')
            data = ref.get()
            if not data:
                return []
            
            viewed_ids = []
            for source, jobs in data.items():
                if jobs:
                    viewed_ids.extend(jobs.keys())
            
            return viewed_ids
        except Exception as e:
            logger.error(f"Error getting viewed jobs: {e}")
            return []
    
    # ==================== STATS ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            jobs = self.get_all_jobs()
            
            stats = {
                'total_jobs': len(jobs),
                'jobs_by_source': {},
                'combined_at': datetime.utcnow().isoformat()
            }
            
            # Count by source
            for job in jobs:
                source = job.get('source', 'unknown')
                stats['jobs_by_source'][source] = stats['jobs_by_source'].get(source, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_jobs': 0,
                'jobs_by_source': {},
                'combined_at': datetime.utcnow().isoformat()
            }
