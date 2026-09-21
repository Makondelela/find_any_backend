"""
Experience Extraction Script
=============================
Crawls through job descriptions and extracts experience requirements.
Saves results to data_jobs_experience.json for fast filtering.
"""

import json
import re
import logging
from typing import Optional, Dict, Any, Iterable, Tuple

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


EXPERIENCE_WORDS = r"(?:experience|exp|work history|background)"
LEVELS = {
    'junior': ('junior', 'entry level', 'entry-level', 'graduate', 'trainee', 'intern'),
    'mid': ('mid level', 'mid-level', 'intermediate'),
    'senior': ('senior', 'lead', 'principal', 'staff', 'expert', 'manager'),
}
RECRUITER_CONTEXT = re.compile(
    r"(?:recruit(?:er|ment)|staffing|consult(?:ing|ancy)|agency|company history|"
    r"our team|years'? experience in (?:recruiting|the industry))",
    re.IGNORECASE,
)


def _sentences(text: str) -> Iterable[str]:
    cleaned = re.sub(r"\s+", " ", text.replace("\r", " ").replace("\n", " ")).strip()
    return (part.strip(" •-\t") for part in re.split(r"(?<=[.!?;])\s+|\s*•\s*", cleaned) if part.strip())


def _years(number: str, unit: str) -> float:
    value = float(number.replace(',', '.'))
    return value / 12 if unit.lower().startswith('month') else value


def _normalise_year(value: float) -> int | float:
    return int(value) if value.is_integer() else round(value, 2)


def _level_from_years(years: Optional[float]) -> Optional[str]:
    if years is None:
        return None
    if years <= 2:
        return 'junior'
    if years <= 5:
        return 'mid'
    return 'senior'


def _numeric_requirement(sentence: str) -> Optional[Tuple[Optional[float], Optional[float], str]]:
    number = r"\d+(?:[.,]\d+)?"
    unit = r"(?:years?|yrs?|months?)"
    range_patterns = (
        rf"({number})\s*(?:-|–|—|to)\s*({number})\s*({unit})",
        rf"between\s+({number})\s+and\s+({number})\s*({unit})",
    )
    for pattern in range_patterns:
        match = re.search(pattern, sentence, re.IGNORECASE)
        if match:
            low = _years(match.group(1), match.group(3))
            high = _years(match.group(2), match.group(3))
            return low, high, match.group(0)

    patterns = (
        (rf"(?:minimum|min(?:imum)?|at least)\s*(?:of\s*)?({number})\s*({unit})", 'minimum'),
        (rf"({number})\s*\+\s*({unit})", 'minimum'),
        (rf"(?:more than|over|greater than)\s*({number})\s*({unit})", 'minimum'),
        (rf"(?:less than|under|up to)\s*({number})\s*({unit})", 'maximum'),
        (rf"({number})\s*({unit})\s*(?:of\s*)?{EXPERIENCE_WORDS}", 'exact'),
        (rf"{EXPERIENCE_WORDS}\s*(?:of|in)?\s*({number})\s*({unit})", 'exact'),
    )
    for pattern, kind in patterns:
        match = re.search(pattern, sentence, re.IGNORECASE)
        if match:
            years = _years(match.group(1), match.group(2))
            if kind == 'maximum':
                return 0, years, match.group(0)
            return years, None if kind == 'minimum' else years, match.group(0)
    return None


def _candidate_score(sentence: str, index: int) -> int:
    score = 0
    lowered = sentence.lower()
    if RECRUITER_CONTEXT.search(sentence):
        return -100
    if re.search(r"required|requirement|must|required|minimum|at least|essential|qualification", lowered):
        score += 5
    if re.search(r"relevant|professional|practical|commercial|industry", lowered):
        score += 2
    if re.search(EXPERIENCE_WORDS, lowered):
        score += 2
    return score - min(index, 3)


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
    
    result = {
        'min_years': None,
        'max_years': None,
        'level': None,
        'raw_text': None
    }
    
    candidates = []
    for index, sentence in enumerate(_sentences(text)):
        numeric = _numeric_requirement(sentence)
        if numeric:
            low, high, raw = numeric
            score = _candidate_score(sentence, index)
            if score >= 0:
                candidates.append((score + 10, low, high, raw, sentence, None))
            continue
        lowered = sentence.lower()
        found_level = next((level for level, words in LEVELS.items() if any(word in lowered for word in words)), None)
        if found_level and re.search(r"experience|requirement|qualification|skills?|position|role", lowered):
            score = _candidate_score(sentence, index)
            if score < 0:
                continue
            bounds = {'junior': (0, 2), 'mid': (3, 5), 'senior': (5, None)}[found_level]
            candidates.append((score, bounds[0], bounds[1], sentence, sentence, found_level))

    if not candidates:
        return None
    _, minimum, maximum, raw, sentence, explicit_level = max(candidates, key=lambda item: item[0])
    result['min_years'] = _normalise_year(minimum) if minimum is not None else None
    result['max_years'] = _normalise_year(maximum) if maximum is not None else None
    result['level'] = explicit_level or _level_from_years(minimum)
    result['raw_text'] = sentence.strip()[:500]
    return result


def process_job_descriptions(input_file: str = 'data/data_jobs_descriptions.json', 
                            output_file: str = 'data/data_jobs_experience.json') -> None:
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
