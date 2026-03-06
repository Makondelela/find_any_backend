"""
Job Service
===========
Business logic for job operations.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from backend.config import Config
from backend.utils import (
    get_location_display,
    parse_date_for_sorting,
    extract_salary_for_sorting,
    truncate_text
)

logger = logging.getLogger(__name__)


class JobService:
    """Service for job-related operations."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def load_jobs_data(self) -> Dict[str, Any]:
        """Load combined jobs data from JSON file."""
        if not self.config.COMBINED_DATA.exists():
            return {"meta": {"total_jobs": 0, "jobs_by_source": {}}, "jobs": []}
        
        with open(self.config.COMBINED_DATA, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_descriptions_data(self) -> Optional[Dict[str, Any]]:
        """Load job descriptions data."""
        if not self.config.DESCRIPTIONS_DATA.exists():
            return None
        
        try:
            with open(self.config.DESCRIPTIONS_DATA, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load descriptions: {e}")
            return None
    
    def get_jobs(
        self,
        keyword: Optional[str] = None,
        location: Optional[str] = None,
        source: Optional[str] = None,
        sort_by: str = 'recent',
        view_status: str = 'all',
        username: Optional[str] = None,
        viewed_job_ids: set = None
    ) -> Dict[str, Any]:
        """
        Get filtered and sorted jobs.
        
        Args:
            keyword: Search keyword
            location: Location filter
            source: Source filter
            sort_by: Sort method (recent, company, salary)
            view_status: View status filter (all, viewed, not_viewed)
            username: Username for view status
            viewed_job_ids: Set of viewed job IDs
            
        Returns:
            Dictionary with jobs and total count
        """
        data = self.load_jobs_data()
        jobs = data.get('jobs', [])
        
        # Apply filters
        filtered_jobs = self._filter_jobs(
            jobs, keyword, location, source, view_status, viewed_job_ids
        )
        
        # Sort jobs
        sorted_jobs = self._sort_jobs(filtered_jobs, sort_by)
        
        return {
            'jobs': sorted_jobs,
            'total': len(sorted_jobs)
        }
    
    def _filter_jobs(
        self,
        jobs: List[Dict],
        keyword: Optional[str],
        location: Optional[str],
        source: Optional[str],
        view_status: str,
        viewed_job_ids: Optional[set]
    ) -> List[Dict]:
        """Filter jobs based on criteria."""
        filtered = []
        
        for job in jobs:
            # Keyword search
            if keyword:
                searchable = (
                    job.get('title', '').lower() + ' ' +
                    job.get('company', '').lower() + ' ' +
                    job.get('summary', '').lower()
                )
                if keyword.lower() not in searchable:
                    continue
            
            # Location filter
            if location and get_location_display(job).lower() != location.lower():
                continue
            
            # Source filter
            if source and job.get('source', '').lower() != source.lower():
                continue
            
            # View status filter
            if view_status != 'all' and viewed_job_ids is not None:
                job_id = job.get('job_id', '') or job.get('url', '')
                if view_status == 'viewed' and job_id not in viewed_job_ids:
                    continue
                elif view_status == 'not_viewed' and job_id in viewed_job_ids:
                    continue
            
            filtered.append(job)
        
        return filtered
    
    def _sort_jobs(self, jobs: List[Dict], sort_by: str) -> List[Dict]:
        """Sort jobs based on method."""
        if sort_by == 'company':
            return sorted(jobs, key=lambda x: x.get('company', 'Unknown').lower())
        elif sort_by == 'salary':
            return sorted(
                jobs,
                key=lambda x: extract_salary_for_sorting(x.get('salary', '')),
                reverse=True
            )
        else:  # recent (default)
            return sorted(
                jobs,
                key=lambda x: parse_date_for_sorting(x.get('posted', '')),
                reverse=True
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get job statistics."""
        data = self.load_jobs_data()
        meta = data.get('meta', {})
        
        return {
            'total_jobs': meta.get('total_jobs', 0),
            'jobs_by_source': meta.get('jobs_by_source', {}),
            'jobs_by_location': meta.get('jobs_by_location', {}),
            'combined_at': meta.get('combined_at', 'Unknown')
        }
