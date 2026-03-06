"""
Scrape Service
==============
Business logic for scraping operations.
"""

import subprocess
import sys
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from backend.config import Config

logger = logging.getLogger(__name__)


class ScrapeService:
    """Service for scraping operations."""
    
    def __init__(self, config: Config):
        self.config = config
        self.scrape_status = {
            'running': False,
            'progress': 0,
            'message': 'Idle',
            'total_jobs': 0,
            'start_time': None,
            'status': 'idle'
        }
        self.scrape_lock = threading.Lock()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scraping status."""
        with self.scrape_lock:
            return self.scrape_status.copy()
    
    def is_running(self) -> bool:
        """Check if scraping is currently running."""
        with self.scrape_lock:
            return self.scrape_status['running']
    
    def trigger_scrape(self, search_terms: Optional[str] = None) -> Dict[str, Any]:
        """
        Trigger scraping process in background.
        
        Args:
            search_terms: Optional search terms to use
            
        Returns:
            Status dictionary
        """
        with self.scrape_lock:
            if self.scrape_status['running']:
                return {
                    'status': 'already_running',
                    'message': 'Scraping is already in progress'
                }
            
            self.scrape_status['running'] = True
            self.scrape_status['progress'] = 0
            self.scrape_status['message'] = f"Starting scraper{' for: ' + search_terms if search_terms else ''}..."
            self.scrape_status['start_time'] = datetime.now().isoformat()
            self.scrape_status['status'] = 'running'
        
        logger.info(f"Scraping triggered{' with terms: ' + search_terms if search_terms else ''}")
        
        # Run scraper in background thread
        thread = threading.Thread(
            target=self._run_scraper,
            args=(search_terms,),
            daemon=True
        )
        thread.start()
        
        return {
            'status': 'success',
            'message': 'Scraping started in background'
        }
    
    def _run_scraper(self, search_terms: Optional[str] = None) -> None:
        """Run scraper in background thread."""
        try:
            with self.scrape_lock:
                self.scrape_status['message'] = 'Searching jobs...'
                self.scrape_status['progress'] = 10
            
            # Build command
            cmd = [sys.executable, str(self.config.BASE_DIR / 'main.py')]
            if search_terms:
                cmd.extend(['--search', search_terms])
            
            logger.info(f"Running scraper: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=str(self.config.BASE_DIR),
                capture_output=True,
                timeout=self.config.SCRAPE_TIMEOUT,
                text=True
            )
            
            logger.info(f"Scraper exit code: {result.returncode}")
            
            if result.returncode == 0:
                # Count jobs from result
                from backend.services.job_service import JobService
                job_service = JobService(self.config)
                data = job_service.load_jobs_data()
                total = len(data.get('jobs', []))
                
                with self.scrape_lock:
                    self.scrape_status['running'] = False
                    self.scrape_status['progress'] = 100
                    self.scrape_status['message'] = f'Completed! Loaded {total} jobs'
                    self.scrape_status['total_jobs'] = total
                    self.scrape_status['status'] = 'complete'
                
                logger.info(f"Scraping completed successfully. Total jobs: {total}")
            else:
                with self.scrape_lock:
                    self.scrape_status['running'] = False
                    self.scrape_status['progress'] = 0
                    self.scrape_status['message'] = f'Error: {result.stderr[:100]}'
                    self.scrape_status['status'] = 'error'
                
                logger.error(f"Scraping failed: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            with self.scrape_lock:
                self.scrape_status['running'] = False
                self.scrape_status['progress'] = 0
                self.scrape_status['message'] = 'Scraper timed out'
                self.scrape_status['status'] = 'error'
            logger.error("Scraper timed out")
        
        except Exception as e:
            with self.scrape_lock:
                self.scrape_status['running'] = False
                self.scrape_status['progress'] = 0
                self.scrape_status['message'] = f'Error: {str(e)}'
                self.scrape_status['status'] = 'error'
            logger.error(f"Error running scraper: {e}", exc_info=True)
