"""
Experience Extraction Script
=============================
Crawls through job descriptions and extracts experience requirements.
Saves results to data_jobs_experience.json for fast filtering.
"""

import json
import re
import logging
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def extract_experience_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract experience requirement from job description text.
    
    Returns:
        Dict with:
        - min_years: int or None (minimum years required)
        - max_years: int or None (maximum years if range specified)
        - level: str or None ('junior', 'mid', 'senior')
        - raw_text: str or None (the actual text that matched)
    """
    if not text:
        return None
    
    text_lower = text.lower()
    result = {
        'min_years': None,
        'max_years': None,
        'level': None,
        'raw_text': None
    }
    
    # Extract numeric experience requirements FIRST (most reliable)
    patterns = [
        # "minimum 3 years", "at least 5 years"
        (r'(?:minimum|min|at least)\s*(?:of)?\s*(\d+)\s*(?:\+)?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)?', 'minimum'),
        # "4-7 years", "2 to 5 years"
        (r'(\d+)\s*(?:[-–]|to)\s*(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)?', 'range'),
        # "5+ years", "3 plus years"
        (r'(\d+)\+\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)?', 'plus'),
        # "3 years experience", "2 years of experience"
        (r'(\d+)\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)', 'exact'),
    ]
    
    for pattern, pattern_type in patterns:
        matches = list(re.finditer(pattern, text_lower))
        if matches:
            match = matches[0]  # Take first match
            
            if pattern_type == 'range':
                min_val = int(match.group(1))
                max_val = int(match.group(2))
                result['min_years'] = min_val
                result['max_years'] = max_val
                result['raw_text'] = match.group(0)
                
                # Determine level based on range
                if min_val <= 2:
                    result['level'] = 'junior'
                elif min_val <= 5:
                    result['level'] = 'mid'
                else:
                    result['level'] = 'senior'
                
                return result
            
            else:
                years = int(match.group(1))
                result['min_years'] = years
                result['raw_text'] = match.group(0)
                
                # Determine level based on years
                if years <= 2:
                    result['level'] = 'junior'
                elif years <= 5:
                    result['level'] = 'mid'
                else:
                    result['level'] = 'senior'
                
                if pattern_type == 'plus':
                    result['max_years'] = None  # Open-ended
                else:
                    result['max_years'] = years
                
                return result
    
    # Only check seniority keywords if NO numeric requirement found
    # Look for these in context of experience/requirements, not job titles
    experience_context_pattern = r'(?:experience|requirement|qualifications?|skills?).*?(\b(?:junior|entry.?level|graduate|grad|mid.?level|intermediate|senior|lead|principal|staff)\b)'
    
    context_match = re.search(experience_context_pattern, text_lower, re.DOTALL)
    if context_match:
        keyword = context_match.group(1)
        
        if re.search(r'junior|entry.?level|graduate|grad', keyword):
            result['level'] = 'junior'
            result['min_years'] = 0
            result['max_years'] = 2
            result['raw_text'] = f'experience: {keyword}'
            return result
        
        if re.search(r'mid.?level|intermediate', keyword):
            result['level'] = 'mid'
            result['min_years'] = 3
            result['max_years'] = 5
            result['raw_text'] = f'experience: {keyword}'
            return result
        
        if re.search(r'senior|lead|principal|staff', keyword):
            result['level'] = 'senior'
            result['min_years'] = 5
            result['max_years'] = None
            result['raw_text'] = f'experience: {keyword}'
            return result
    
    # No experience requirement found
    return None


def process_job_descriptions(input_file: str = 'data_jobs_descriptions.json', 
                            output_file: str = 'data_jobs_experience.json') -> None:
    """
    Process all job descriptions and extract experience requirements.
    
    Args:
        input_file: Path to descriptions JSON file
        output_file: Path to save experience data
    """
    logger.info(f"Loading job descriptions from {input_file}...")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {input_file}")
        return
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {input_file}: {e}")
        return
    
    descriptions = data.get('descriptions', [])
    logger.info(f"Found {len(descriptions)} job descriptions")
    
    # Process each job description
    experience_data = []
    stats = {
        'total': len(descriptions),
        'with_experience': 0,
        'no_experience': 0,
        'junior': 0,
        'mid': 0,
        'senior': 0,
        'numeric': 0
    }
    
    for idx, job_desc in enumerate(descriptions, 1):
        job_id = job_desc.get('job_id', '')
        description = job_desc.get('description', '')
        
        # Extract experience
        exp_data = extract_experience_from_text(description)
        
        if exp_data:
            stats['with_experience'] += 1
            
            # Track levels
            level = exp_data.get('level')
            if level == 'junior':
                stats['junior'] += 1
            elif level == 'mid':
                stats['mid'] += 1
            elif level == 'senior':
                stats['senior'] += 1
            
            if exp_data.get('min_years') is not None:
                stats['numeric'] += 1
            
            experience_data.append({
                'job_id': job_id,
                'min_years': exp_data.get('min_years'),
                'max_years': exp_data.get('max_years'),
                'level': exp_data.get('level'),
                'raw_text': exp_data.get('raw_text'),
                'has_requirement': True
            })
            
            if idx % 100 == 0:
                logger.info(f"Processed {idx}/{len(descriptions)} jobs...")
        else:
            stats['no_experience'] += 1
            experience_data.append({
                'job_id': job_id,
                'min_years': None,
                'max_years': None,
                'level': None,
                'raw_text': None,
                'has_requirement': False
            })
    
    # Save to JSON
    output_data = {
        'metadata': {
            'total_jobs': stats['total'],
            'jobs_with_experience': stats['with_experience'],
            'jobs_without_experience': stats['no_experience'],
            'breakdown': {
                'junior': stats['junior'],
                'mid': stats['mid'],
                'senior': stats['senior'],
                'with_numeric_years': stats['numeric']
            }
        },
        'experience': experience_data
    }
    
    logger.info(f"\nSaving experience data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Print statistics
    logger.info("\n" + "="*60)
    logger.info("EXPERIENCE EXTRACTION COMPLETE")
    logger.info("="*60)
    logger.info(f"Total jobs processed: {stats['total']}")
    logger.info(f"Jobs with experience requirements: {stats['with_experience']} ({stats['with_experience']/stats['total']*100:.1f}%)")
    logger.info(f"Jobs without requirements: {stats['no_experience']} ({stats['no_experience']/stats['total']*100:.1f}%)")
    logger.info(f"\nBreakdown by level:")
    logger.info(f"  Junior/Entry: {stats['junior']}")
    logger.info(f"  Mid-level: {stats['mid']}")
    logger.info(f"  Senior: {stats['senior']}")
    logger.info(f"  With numeric years: {stats['numeric']}")
    logger.info(f"\nData saved to: {output_file}")
    logger.info("="*60)


if __name__ == '__main__':
    process_job_descriptions()
