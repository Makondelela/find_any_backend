"""
AI Filter Service
=================
Business logic for AI-powered job filtering.
"""

import logging
from typing import Dict, List, Any, Optional
from backend.config import Config

logger = logging.getLogger(__name__)


class AIFilterService:
    """Service for AI filtering operations."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def filter_jobs(
        self,
        jobs: List[Dict],
        criteria: str,
        descriptions_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Filter jobs using AI based on criteria.
        
        Args:
            jobs: List of jobs to filter
            criteria: Filter criteria
            descriptions_data: Optional job descriptions data
            
        Returns:
            Filtered results with explanation
        """
        try:
            from ai_filtering import filter_jobs_by_criteria
            
            result = filter_jobs_by_criteria(jobs, criteria, descriptions_data)
            
            return {
                'success': True,
                'filtered_jobs': result.get('filtered_jobs', []),
                'explanation': result.get('explanation', ''),
                'total_filtered': result.get('total_matches', len(result.get('filtered_jobs', []))),
                'experience_query': result.get('experience_query', False),
                'user_experience_years': result.get('user_experience_years')
            }
        except ImportError:
            return {
                'success': False,
                'message': 'AI filtering module not available. Install google-genai: pip install google-genai'
            }
        except Exception as e:
            logger.error(f"AI filtering error: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def filter_jobs_chunked(
        self,
        jobs: List[Dict],
        criteria: str,
        chunk_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Filter jobs with chunked processing.
        
        Args:
            jobs: List of jobs to filter
            criteria: Filter criteria
            chunk_size: Size of chunks (default from config)
            
        Returns:
            Filtered results
        """
        if chunk_size is None:
            chunk_size = self.config.CHUNK_SIZE
        
        all_filtered_jobs = []
        explanations = []
        
        for i in range(0, len(jobs), chunk_size):
            chunk = jobs[i:i + chunk_size]
            chunk_num = i // chunk_size + 1
            total_chunks = (len(jobs) + chunk_size - 1) // chunk_size
            
            logger.info(f"Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} jobs)")
            
            result = self.filter_jobs(chunk, criteria)
            
            if result.get('success'):
                filtered_in_chunk = result.get('filtered_jobs', [])
                all_filtered_jobs.extend(filtered_in_chunk)
                
                if result.get('explanation'):
                    explanations.append(result.get('explanation'))
                
                logger.info(f"Chunk {chunk_num}: Found {len(filtered_in_chunk)} matching jobs")
        
        # Get unique explanation
        final_explanation = explanations[0] if explanations else 'Filtered based on your criteria'
        
        return {
            'success': True,
            'filtered_jobs': all_filtered_jobs,
            'explanation': final_explanation,
            'total_filtered': len(all_filtered_jobs)
        }
