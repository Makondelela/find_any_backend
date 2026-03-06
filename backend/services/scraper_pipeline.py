"""
Scraper Pipeline Service
========================
Orchestrates the scraping pipeline: Source Scraping → Descriptions → Experience
Integrates with Firebase for job storage and deduplication.
"""

import logging
import subprocess
import sys
import threading
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class ScraperPipeline:
    """Pipeline for scraping jobs with Firebase integration."""
    
    # Source to scraper mapping
    SOURCE_MAP = {
        'linkedin': 'linkedin',
        'pnet': 'pnet',
        'careerjunction': 'careerjunction',
        'careers24': 'careers24',
        'networkrecruitment': 'nri',
        'network recruitment': 'nri',
        'nri': 'nri'
    }
    
    # Source to output filename mapping
    OUTPUT_FILE_MAP = {
        'linkedin': 'data_jobs_linkedin.json',
        'pnet': 'data_jobs_pnet.json',
        'careerjunction': 'data_jobs_careerjunction.json',
        'careers24': 'data_jobs_careers24.json',
        'networkrecruitment': 'data_jobs_networkrecruitment.json',
        'network recruitment': 'data_jobs_networkrecruitment.json',
        'nri': 'data_jobs_networkrecruitment.json'
    }
    
    def __init__(self, config, firebase_service):
        """Initialize pipeline with config and Firebase service."""
        self.config = config
        self.firebase = firebase_service
        # __file__ is backend/services/scraper_pipeline.py
        # parent.parent goes up to scrape/ folder
        self.base_dir = Path(__file__).parent.parent.parent  # Go up 3 levels to scrape/
        self.running_jobs = {}  # job_id -> thread
        logger.info(f"ScraperPipeline base_dir: {self.base_dir}")
    
    def start_scrape(self, job_id: str, sources: List[str], search_terms: str = '') -> None:
        """
        Start scraping pipeline in background.
        
        Args:
            job_id: Firebase scrape job ID
            sources: List of sources to scrape (lowercase)
            search_terms: Comma-separated search terms from user
        """
        thread = threading.Thread(
            target=self._run_pipeline,
            args=(job_id, sources, search_terms),
            daemon=True
        )
        self.running_jobs[job_id] = thread
        thread.start()
        logger.info(f"Started scrape pipeline {job_id} for sources: {sources} with terms: {search_terms}")
    
    def _run_pipeline(self, job_id: str, sources: List[str], search_terms: str = '') -> None:
        """Run complete scraping pipeline."""
        try:
            # Update status to running
            self.firebase.update_scrape_job(job_id, {
                'status': 'running',
                'progress': 5
            })
            
            # Step 1: Run source scrapers and save to Firebase
            logger.info(f"[{job_id}] Scraping jobs from sources")
            self._run_source_scrapers(job_id, sources, search_terms)
            
            # Complete
            scrape_data = self.firebase.get_scrape_job(job_id)
            stats = scrape_data.get('stats', {})
            
            self.firebase.update_scrape_job(job_id, {
                'status': 'completed',
                'progress': 100,
                'completedAt': datetime.utcnow().isoformat()
            })
            
            logger.info(f"[{job_id}] Scraping completed: {stats}")
            
        except Exception as e:
            logger.error(f"[{job_id}] Pipeline failed: {e}")
            self.firebase.update_scrape_job(job_id, {
                'status': 'error',
                'error': str(e)
            })
        finally:
            # Clean up
            self.running_jobs.pop(job_id, None)
    
    def _run_source_scrapers(self, job_id: str, sources: List[str], search_terms: str = '') -> None:
        """Run scrapers for each source and save to Firebase."""
        stats = {'totalJobs': 0, 'newJobs': 0, 'skippedJobs': 0}
        
        for idx, source in enumerate(sources):
            try:
                logger.info(f"[{job_id}] Scraping {source}...")
                progress = 10 + (idx * 20 // len(sources))
                
                self.firebase.update_scrape_job(job_id, {
                    'progress': progress,
                    'currentStep': f'scraping_{source}'
                })
                
                # Run scraper with search terms
                jobs = self._scrape_source(source, search_terms)
                
                # Save to Firebase (skip if exists)
                for job in jobs:
                    stats['totalJobs'] += 1
                    # Use job_id field, fallback to URL, then generate from title+company
                    job_identifier = job.get('job_id') or job.get('id') or job.get('url')
                    if not job_identifier:
                        # Generate ID from title + company as last resort
                        import hashlib
                        key = f"{job.get('title', '')}_{job.get('company', '')}_{source}"
                        job_identifier = hashlib.md5(key.encode()).hexdigest()
                    
                    # Hash the identifier to create a valid Firebase key (URLs have / which Firebase doesn't allow)
                    import hashlib
                    job_id_field = hashlib.md5(job_identifier.encode()).hexdigest()
                    
                    if self.firebase.job_exists(source, job_id_field):
                        stats['skippedJobs'] += 1
                        logger.debug(f"Skipping existing job {job_id_field}")
                    else:
                        # Add metadata
                        job['scrapedAt'] = datetime.utcnow().isoformat()
                        job['source'] = source
                        job['id'] = job_id_field  # Ensure id field is set
                        
                        if self.firebase.save_job(source, job_id_field, job):
                            stats['newJobs'] += 1
                            logger.info(f"Saved new job: {job.get('title', 'Unknown')} - {job_id_field[:8]}")
                
                # Update source metadata
                self.firebase.update_source_metadata(source, {
                    'name': source.title(),
                    'lastScraped': datetime.utcnow().isoformat(),
                    'jobCount': len(jobs)
                })
                
                logger.info(f"[{job_id}] {source}: {len(jobs)} jobs ({stats['newJobs']} new, {stats['skippedJobs']} skipped)")
                
            except Exception as e:
                logger.error(f"[{job_id}] Error scraping {source}: {e}")
        
        # Update stats
        self.firebase.update_scrape_job(job_id, {'stats': stats})
    
    def _scrape_source(self, source: str, search_terms: str = '') -> List[Dict]:
        """Run scraper for specific source and return jobs."""
        # Map source name to scraper flag
        scraper_flag = f"--{self.SOURCE_MAP.get(source.lower(), source.lower())}"
        
        # base_dir is scrape/, main.py is in scrape/backend/
        cmd = [
            sys.executable,
            str(self.base_dir / 'backend' / 'main.py'),
            scraper_flag,
            '--json'  # Tell scraper to output JSON to stdout
        ]
        
        # Add search terms if provided
        if search_terms and search_terms.strip():
            cmd.extend(['--search', search_terms])
        
        try:
            logger.info(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=str(self.base_dir),  # Run from scrape/ folder
                capture_output=True,
                timeout=self.config.SCRAPE_TIMEOUT,
                text=True,
                encoding='utf-8',  # Force UTF-8 encoding to handle special characters
                errors='replace'   # Replace invalid characters instead of crashing
            )
            
            if result.returncode != 0:
                logger.warning(f"Scraper returned non-zero: {result.returncode}")
                logger.error(f"Stderr: {result.stderr}")
                logger.error(f"Stdout: {result.stdout}")
                return []
            
            # Parse JSON output from stdout
            try:
                # Look for JSON output marker
                output = result.stdout
                if '===JSON_START===' in output:
                    json_start = output.index('===JSON_START===') + len('===JSON_START===')
                    json_end = output.index('===JSON_END===') if '===JSON_END===' in output else len(output)
                    json_str = output[json_start:json_end].strip()
                    data = json.loads(json_str)
                    jobs = data.get('jobs', []) if isinstance(data, dict) else []
                    logger.info(f"Parsed {len(jobs)} jobs from scraper output")
                    return jobs
                else:
                    logger.warning(f"No JSON marker found in scraper output")
                    return []
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse JSON from scraper output: {e}")
                logger.debug(f"Output was: {result.stdout[:1000]}")
                return []
            
        except subprocess.TimeoutExpired:
            logger.error(f"Scraper timeout for {source}")
            return []
        except Exception as e:
            logger.error(f"Error running scraper for {source}: {e}")
            return []


# Import json for file loading
import json
