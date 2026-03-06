"""
User Service
============
Business logic for user operations.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from backend.config import Config

logger = logging.getLogger(__name__)


class UserService:
    """Service for user-related operations."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def load_user_jobs(self) -> Dict[str, List[Dict]]:
        """Load user viewed jobs history."""
        if not self.config.USER_JOBS_FILE.exists():
            return {}
        
        try:
            with open(self.config.USER_JOBS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading user jobs: {e}")
            return {}
    
    def save_user_jobs(self, data: Dict[str, List[Dict]]) -> None:
        """Save user viewed jobs history."""
        try:
            with open(self.config.USER_JOBS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving user jobs: {e}")
            raise
    
    def track_job_view(
        self,
        username: str,
        job_id: str,
        job_url: str
    ) -> Dict[str, Any]:
        """
        Track a job view for a user.
        
        Args:
            username: Username
            job_id: Job ID
            job_url: Job URL
            
        Returns:
            Success status
        """
        if not username or not job_id:
            return {
                'success': False,
                'message': 'Username and job_id required'
            }
        
        user_jobs = self.load_user_jobs()
        
        if username not in user_jobs:
            user_jobs[username] = []
        
        # Check if job already tracked
        existing = [j for j in user_jobs[username] if j.get('job_id') == job_id]
        
        if not existing:
            user_jobs[username].append({
                'job_id': job_id,
                'job_url': job_url,
                'viewed_at': datetime.now(timezone.utc).isoformat()
            })
            self.save_user_jobs(user_jobs)
        
        return {
            'success': True,
            'message': 'Job tracked successfully'
        }
    
    def get_user_history(self, username: str) -> Dict[str, Any]:
        """
        Get viewed jobs for a user.
        
        Args:
            username: Username
            
        Returns:
            User history data
        """
        user_jobs = self.load_user_jobs()
        viewed_jobs = user_jobs.get(username, [])
        
        return {
            'success': True,
            'username': username,
            'viewed_jobs': viewed_jobs,
            'total_viewed': len(viewed_jobs)
        }
    
    def get_viewed_job_ids(self, username: str) -> Set[str]:
        """
        Get set of viewed job IDs for a user.
        
        Args:
            username: Username
            
        Returns:
            Set of job IDs
        """
        user_jobs = self.load_user_jobs()
        viewed_jobs = user_jobs.get(username, [])
        return set(job.get('job_id') for job in viewed_jobs if job.get('job_id'))
