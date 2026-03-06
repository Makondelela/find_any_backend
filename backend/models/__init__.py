"""
Data Models
===========
Data structures and schemas for the application.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class Job:
    """Job listing model."""
    job_id: str
    title: str
    company: str
    location: str
    source: str
    url: str
    posted: str = "Recently"
    salary: str = "Not specified"
    summary: str = ""
    full_summary: Optional[str] = None
    job_type: str = "Not specified"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class UserViewedJob:
    """User viewed job record."""
    job_id: str
    job_url: str
    viewed_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Stats:
    """Job statistics model."""
    total_jobs: int
    jobs_by_source: Dict[str, int]
    jobs_by_location: Dict[str, int]
    combined_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ScrapeStatus:
    """Scraping status model."""
    running: bool
    progress: int
    message: str
    total_jobs: int
    start_time: Optional[str]
    status: str = 'idle'  # idle, running, complete, error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
