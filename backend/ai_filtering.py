"""
AI-Powered Job Filtering Module
================================
Intelligently filters jobs based on user criteria with robust experience matching.
Uses Google Gemini AI for advanced semantic understanding.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Load pre-extracted experience data once at module load
EXPERIENCE_DATA = {}
try:
    with open('data_jobs_experience.json', 'r', encoding='utf-8') as f:
        exp_file = json.load(f)
        # Create lookup dictionary: job_id -> experience data
        for item in exp_file.get('experience', []):
            EXPERIENCE_DATA[item['job_id']] = item
        logger.info(f"✓ Loaded experience data for {len(EXPERIENCE_DATA)} jobs")
except FileNotFoundError:
    logger.warning("⚠️ data_jobs_experience.json not found - run extract_experience.py first")
except Exception as e:
    logger.warning(f"⚠️ Could not load experience data: {e}")

# Google Gemini API Configuration
GEMINI_API_KEY = "AIzaSyB9yYOOqHHw_-NC9zM68FcgQQVSYJRXjj8"
API_AVAILABLE = False

# Try to import Gemini with new package
try:
    from google import genai
    from google.genai.types import GenerateContentConfig
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    API_AVAILABLE = True
    logger.info("✓ Gemini AI enabled (google-genai)")
except ImportError:
    # Try old package for backwards compatibility
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        API_AVAILABLE = True
        logger.info("✓ Gemini AI enabled (google-generativeai)")
    except ImportError:
        logger.warning("Gemini API not available. Install with: pip install google-genai")
except Exception as e:
    logger.warning(f"Could not configure Gemini: {e}")


def filter_jobs_by_criteria(jobs: List[Dict[str, Any]], user_criteria: str, descriptions_data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Filter jobs based on user criteria with intelligent experience matching.
    
    Uses pre-extracted experience data for fast, accurate filtering.
    
    When user mentions "years" or "experience":
    - Uses pre-extracted experience data from data_jobs_experience.json
    - Matches based on numeric years or seniority level
    - Includes jobs without requirements unless strict mode ("only" keyword)
    
    Args:
        jobs: List of job dictionaries from data_jobs_combined.json
        user_criteria: User's filter criteria (e.g., "2 years experience", "remote jobs", etc.)
        descriptions_data: Optional dict from data_jobs_descriptions.json with full descriptions
    
    Returns:
        Dict with filtered_jobs and explanation
    """
    
    # Use fast experience-based filtering
    return experience_based_filter(jobs, user_criteria)


def gemini_filter_jobs(jobs: List[Dict[str, Any]], user_criteria: str, descriptions_data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Use Gemini AI to intelligently filter jobs based on semantic understanding.
    
    Hybrid approach (optimized for API rate limits):
    1. Use regex for fast pre-filtering to get candidates
    2. Gemini validates and refines the top ~100-200 candidates  
    3. This keeps API calls under the free tier limit (20/day)
    """
    logger.info(f"🤖 Gemini AI analyzing: '{user_criteria}'")
    
    # Step 1: Fast regex pre-filter to reduce candidate pool
    regex_result = robust_filter_jobs(jobs, user_criteria, descriptions_data)
    candidates = regex_result['filtered_jobs']
    
    logger.info(f"Regex pre-filter: {len(jobs)} → {len(candidates)} candidates")
    
    # If very few candidates or no API, return regex results
    if len(candidates) <= 5 or not API_AVAILABLE:
        logger.info("Few candidates or no AI - returning regex results")
        return regex_result
    
    # Step 2: Use Gemini to understand the query better
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
    except:
        # Fallback to old API
        import google.generativeai as old_genai
        model = old_genai.GenerativeModel('gemini-pro')
        use_old_api = True
    else:
        use_old_api = False
    
    query_analysis_prompt = f"""Analyze this job search query: "{user_criteria}"

Answer these questions precisely:
1. Is this filtering by experience years? Answer yes if query mentions: years, experience, junior, senior, mid-level, entry-level
2. If yes, what years of experience does the user have?
   - "junior" or "entry-level" = 2
   - "mid-level" or "intermediate" = 5
   - "senior" = 8
   - If specific number like "2 years" or "5 years experience", use that number
   - Otherwise: unknown
3. Is strict mode? Answer yes ONLY if user says: "only", "exactly", "just"
4. Key skills/technologies mentioned? List programming languages, tools, technologies

Format your response EXACTLY as:
EXPERIENCE: yes/no
YEARS: number or unknown
STRICT: yes/no
SKILLS: skill1, skill2 or none

Example 1: "2 years experience only"
EXPERIENCE: yes
YEARS: 2
STRICT: yes
SKILLS: none

Example 2: "python developer with SQL"
EXPERIENCE: no
YEARS: unknown
STRICT: no
SKILLS: python, sql

Example 3: "senior data engineer"
EXPERIENCE: yes
YEARS: 8
STRICT: no
SKILLS: none"""

    try:
        if use_old_api:
            query_response = model.generate_content(query_analysis_prompt)
            query_analysis = query_response.text.strip()
        else:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=query_analysis_prompt
            )
            query_analysis = response.text.strip()
        
        logger.info(f"Query analysis:\n{query_analysis}")
        
        # Parse the analysis
        is_exp_query = 'EXPERIENCE: yes' in query_analysis
        strict_mode = 'STRICT: yes' in query_analysis
        
        user_years = None
        if is_exp_query:
            years_match = re.search(r'YEARS:\s*(\d+)', query_analysis)
            if years_match:
                user_years = int(years_match.group(1))
        
        # Extract skills
        skills = []
        skills_match = re.search(r'SKILLS:\s*(.+)', query_analysis, re.IGNORECASE)
        if skills_match and 'none' not in skills_match.group(1).lower():
            skills = [s.strip().lower() for s in skills_match.group(1).split(',') if s.strip()]
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Gemini query analysis failed: {error_msg}")
        
        # If rate limit or other AI error, fall back to regex results
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            logger.warning("⚠️ Gemini API rate limit reached - using regex filtering")
        else:
            logger.warning("⚠️ Gemini AI error - using regex filtering")
        
        return {
            **regex_result,
            "ai_enhanced": False,
            "explanation": f"{regex_result['explanation']} (AI unavailable: rate limit)"
        }
    
    # Build description lookup
    description_lookup = {}
    if descriptions_data:
        for desc in descriptions_data.get('descriptions', []):
            description_lookup[desc['job_id']] = desc.get('description', '')
    
    # Limit candidates to top 200 to stay within API limits (20 requests / 20 per batch = max 400 jobs)
    max_candidates = 200
    if len(candidates) > max_candidates:
        logger.info(f"Limiting candidates from {len(candidates)} to {max_candidates} for AI validation")
        candidates = candidates[:max_candidates]
    
    # Process candidates with Gemini in batches
    filtered_jobs = []
    batch_size = 20
    max_batches = 10  # Stay under 20 API calls (1 for query analysis + max 10 for batches)
    
    logger.info(f"Starting AI validation ({len(candidates)} candidates, max {min(len(candidates)//batch_size + 1, max_batches)} batches)")
    
    for batch_num, i in enumerate(range(0, len(candidates), batch_size)):
        if batch_num >= max_batches:
            logger.warning(f"Reached API limit ({max_batches} batches), including remaining candidates without AI validation")
            filtered_jobs.extend(candidates[i:])  # Include remaining without AI check
            break
            
        batch = candidates[i:i+batch_size]
        
        # Build batch prompt with job details
        job_summaries = []
        for idx, job in enumerate(batch):
            job_id = job.get('job_id', '')
            title = job.get('title', '')
            company = job.get('company', '')
            location = job.get('location', '')
            desc = description_lookup.get(job_id, job.get('summary', ''))[:400]  # First 400 chars
            job_summaries.append(f"{idx}. {title} at {company} ({location})\n{desc}")
        
        # Create intelligent batch prompt based on query type
        if is_exp_query and user_years is not None:
            batch_prompt = f"""User query: "{user_criteria}"
User has {user_years} years of experience.
Strict mode: {"YES - exclude jobs with no clear experience requirement" if strict_mode else "NO - include jobs with no requirement"}

Analyze these {len(batch)} jobs and identify which ones the user qualifies for:

{chr(10).join(job_summaries)}

Rules:
- MATCH if job requires ≤ {user_years} years of experience
- MATCH "junior" or "entry-level" if user has ≥ 0 years
- MATCH "mid-level" or "intermediate" if user has ≥ 3 years
- MATCH "senior" if user has ≥ 5 years
- If NO experience mentioned: {"EXCLUDE (strict mode)" if strict_mode else "INCLUDE (user qualifies)"}

Respond with ONLY the numbers (0-{len(batch)-1}) of matching jobs, one per line:"""
        elif skills:
            batch_prompt = f"""User query: "{user_criteria}"
Looking for jobs that require or mention: {', '.join(skills)}

Analyze these {len(batch)} jobs:

{chr(10).join(job_summaries)}

Respond with ONLY the numbers (0-{len(batch)-1}) of jobs that mention these skills, one per line:"""
        else:
            batch_prompt = f"""User query: "{user_criteria}"

Analyze these {len(batch)} jobs and identify which ones match the user's search:

{chr(10).join(job_summaries)}

Respond with ONLY the numbers (0-{len(batch)-1}) of matching jobs, one per line:"""
        
        try:
            if use_old_api:
                batch_response = model.generate_content(batch_prompt)
                matches_text = batch_response.text.strip() if batch_response.text else ""
            else:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=batch_prompt
                )
                matches_text = response.text.strip() if response and response.text else ""
            
            # Parse matching indices
            matching_indices = []
            for line in matches_text.split('\n'):
                line = line.strip()
                num_match = re.match(r'^(\d+)', line)
                if num_match:
                    idx = int(num_match.group(1))
                    if 0 <= idx < len(batch):
                        matching_indices.append(idx)
            
            # Add matching jobs
            for idx in matching_indices:
                filtered_jobs.append(batch[idx])
            
            logger.info(f"Batch {batch_num + 1}/{min((len(candidates)-1)//batch_size + 1, max_batches)}: {len(batch)} jobs → {len(matching_indices)} matches")
            
        except Exception as e:
            logger.error(f"Batch {batch_num + 1} processing error: {e}")
            # On error, include all batch jobs (safe fallback)
            filtered_jobs.extend(batch)
            continue
    
    logger.info(f"✓ Gemini AI filtered {len(candidates)} → {len(filtered_jobs)} jobs")
    
    # Generate explanation
    if is_exp_query and user_years is not None:
        if strict_mode:
            explanation = f"AI found {len(filtered_jobs)} jobs requiring up to {user_years} years of experience (excluded jobs without clear requirements)"
        else:
            explanation = f"AI found {len(filtered_jobs)} jobs matching your {user_years} years of experience (includes jobs without specific requirements)"
    elif skills:
        explanation = f"AI found {len(filtered_jobs)} jobs mentioning: {', '.join(skills)}"
    else:
        explanation = f"AI found {len(filtered_jobs)} jobs matching '{user_criteria}'"
    
    return {
        **regex_result,
        "ai_enhanced": True,
        "explanation": explanation,
        "experience_query": is_exp_query,
        "user_experience_years": user_years,
        "strict_mode": strict_mode,
        "ai_enhanced": True
    }


def experience_based_filter(jobs: List[Dict[str, Any]], user_criteria: str) -> Dict[str, Any]:
    """
    Fast filtering using pre-extracted experience data.
    
    This is the main filtering function that uses cached experience requirements
    instead of parsing descriptions on every search.
    """
    criteria_lower = user_criteria.lower()
    
    # Check if this is an experience query
    is_exp_query = is_experience_query(user_criteria)
    
    if not is_exp_query:
        # For non-experience queries, return all jobs
        logger.info(f"Non-experience query: '{user_criteria}' - returning all jobs")
        return {
            "filtered_jobs": jobs,
            "total_matches": len(jobs),
            "explanation": f"Showing all {len(jobs)} jobs (no experience filter)",
            "experience_query": False,
            "user_experience_years": None,
            "strict_mode": False
        }
    
    # Extract user's experience
    user_years = extract_experience_requirement(user_criteria)
    strict_mode = any(word in criteria_lower for word in ['only', 'exactly', 'just'])
    
    logger.info(f"🔍 Filtering by experience: user has {user_years} years, strict={strict_mode}")
    
    if user_years is None:
        logger.warning("Could not extract years from query")
        return {
            "filtered_jobs": jobs,
            "total_matches": len(jobs),
            "explanation": f"Could not determine experience level from '{user_criteria}'",
            "experience_query": True,
            "user_experience_years": None,
            "strict_mode": False
        }
    
    # Filter jobs using pre-extracted experience data
    filtered = []
    stats = {
        'matched': 0,
        'no_requirement': 0,
        'too_high': 0,
        'no_data': 0
    }
    
    for job in jobs:
        job_id = job.get('job_id', '')
        exp_data = EXPERIENCE_DATA.get(job_id)
        
        if not exp_data:
            # No experience data for this job - skip it
            stats['no_data'] += 1
            continue
        
        if not exp_data.get('has_requirement'):
            # Job has no experience requirement
            if not strict_mode:
                filtered.append(job)
                stats['no_requirement'] += 1
            continue
        
        # Job has experience requirement - check if user qualifies
        min_years = exp_data.get('min_years')
        
        if min_years is None:
            # Has requirement but no numeric value (shouldn't happen, but handle it)
            if not strict_mode:
                filtered.append(job)
                stats['no_requirement'] += 1
            continue
        
        # Check if user meets the requirement
        if user_years >= min_years:
            filtered.append(job)
            stats['matched'] += 1
        else:
            stats['too_high'] += 1
    
    # Generate explanation
    logger.info(f"Results: {len(filtered)} total | {stats['matched']} matched | {stats['no_requirement']} no req | {stats['too_high']} too high | {stats['no_data']} no data")
    
    if strict_mode:
        explanation = (
            f"Found {len(filtered)} jobs requiring up to {user_years} years of experience "
            f"(strict mode: excluded {stats['no_requirement']} jobs without requirements)"
        )
    else:
        explanation = (
            f"Found {len(filtered)} jobs: {stats['matched']} requiring ≤{user_years} years, "
            f"plus {stats['no_requirement']} without specific requirements"
        )
    
    return {
        "filtered_jobs": filtered,
        "total_matches": len(filtered),
        "explanation": explanation,
        "experience_query": True,
        "user_experience_years": user_years,
        "strict_mode": strict_mode,
        "breakdown": stats
    }


def robust_filter_jobs(jobs: List[Dict[str, Any]], user_criteria: str, descriptions_data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Robust filtering with intelligent experience matching and description search.
    
    When "years" or "experience" is mentioned:
    - Searches ONLY in job descriptions (fetches from descriptions_data)
    - Includes jobs without experience requirements UNLESS user says "only"
    - Matches various formats (junior, senior, mid-level, 2+ years, 3-5 years, etc.)
    """
    criteria_lower = user_criteria.lower()
    filtered = []
    
    # Check if user is searching by experience
    experience_search = is_experience_query(user_criteria)
    user_experience = extract_experience_requirement(user_criteria) if experience_search else None
    
    # Check if user wants EXACT match (used "only", "exactly", "just")
    strict_match = any(word in criteria_lower for word in ['only', 'exactly', 'just', 'exactly'])
    
    # Build description lookup if available
    description_lookup = {}
    if descriptions_data:
        for desc in descriptions_data.get('descriptions', []):
            description_lookup[desc['job_id']] = desc.get('description', '')
    
    logger.info(f"Filtering {len(jobs)} jobs. Experience query: {experience_search}, User years: {user_experience}, Strict: {strict_match}")
    
    # Track why jobs were filtered for debugging
    no_description_count = 0
    no_exp_req_count = 0
    matched_count = 0
    too_high_count = 0
    
    for job in jobs:
        job_id = job.get('job_id', '')
        
        # For experience queries, MUST search in description
        if experience_search:
            if not description_lookup:
                logger.warning("Experience query but no descriptions data available!")
                continue
                
            search_text = description_lookup.get(job_id, '').lower()
            if not search_text:
                # No description available, skip this job
                no_description_count += 1
                continue
        else:
            # For non-experience queries, search in title, company, summary, location
            title = (job.get('title', '') or '').lower()
            company = (job.get('company', '') or '').lower()
            summary = (job.get('summary', '') or '').lower()
            location = (job.get('location', '') or '').lower()
            search_text = f"{title} {company} {summary} {location}"
        
        # If user specified experience level, check requirements
        if user_experience is not None:
            job_experience = extract_job_experience(search_text)
            
            if job_experience is None:
                # No experience requirement found
                if not strict_match:
                    # Include jobs without requirements (unless user wants exact match)
                    filtered.append(job)
                    no_exp_req_count += 1
                    logger.debug(f"✓ Job {job_id}: No experience req (INCLUDED - not strict)")
                else:
                    logger.debug(f"✗ Job {job_id}: No experience req (EXCLUDED - strict mode)")
            elif job_experience <= user_experience:
                # Job requires <= user's experience (user qualifies)
                filtered.append(job)
                matched_count += 1
                logger.debug(f"✓ Job {job_id}: Requires {job_experience}y, user has {user_experience}y (INCLUDED)")
            else:
                too_high_count += 1
                logger.debug(f"✗ Job {job_id}: Requires {job_experience}y, user has {user_experience}y (EXCLUDED)")
        else:
            # No experience filter, just ensure it's a data-related job
            filtered.append(job)
    
    # Generate explanation
    logger.info(f"Filter results: {len(filtered)} total | {matched_count} matched exp | {no_exp_req_count} no req | {too_high_count} too high | {no_description_count} no desc")
    
    if experience_search and user_experience:
        if strict_match:
            explanation = (
                f"Found {len(filtered)} jobs requiring up to {user_experience} years of experience. "
                f"(Strict mode: excluded jobs without specific requirements)"
            )
        else:
            explanation = (
                f"Found {len(filtered)} jobs matching your criteria. "
                f"Includes {matched_count} jobs requiring up to {user_experience} years, "
                f"plus {no_exp_req_count} jobs without specific experience requirements."
            )
    else:
        explanation = f"Found {len(filtered)} jobs matching '{user_criteria}'."
    
    logger.info(f"Filter complete: {len(filtered)} jobs matched")
    
    return {
        "filtered_jobs": filtered,
        "total_matches": len(filtered),
        "explanation": explanation,
        "experience_query": experience_search,
        "user_experience_years": user_experience,
        "strict_mode": strict_match
    }


def is_experience_query(criteria: str) -> bool:
    """Check if user query is about experience/years."""
    criteria_lower = criteria.lower()
    experience_keywords = ['year', 'years', 'yr', 'yrs', 'experience', 'exp', 'junior', 'senior', 'mid-level', 'entry']
    return any(keyword in criteria_lower for keyword in experience_keywords)


def extract_keywords(criteria: str) -> List[str]:
    """Extract searchable keywords from user criteria."""
    # Remove common stop words and split
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'from'}
    words = criteria.lower().split()
    keywords = [w for w in words if w not in stop_words and len(w) > 1]
    return keywords


def extract_experience_requirement(criteria: str) -> Optional[int]:
    """
    Extract years of experience from search criteria.
    
    Patterns matched:
    - "2 years" -> 2
    - "3+ years" -> 3
    - "2-5 years" -> 2 (minimum)
    - "junior" -> 2
    - "mid-level" or "intermediate" -> 3
    - "senior" -> 5
    """
    criteria_lower = criteria.lower()
    
    # Check for seniority keywords
    if 'junior' in criteria_lower or 'entry' in criteria_lower or 'graduate' in criteria_lower:
        logger.debug(f"Extract exp: Found junior/entry/graduate keyword -> 2 years")
        return 2
    if 'mid-level' in criteria_lower or 'intermediate' in criteria_lower or 'mid level' in criteria_lower:
        logger.debug(f"Extract exp: Found mid-level/intermediate keyword -> 3 years")
        return 3
    if 'senior' in criteria_lower or 'lead' in criteria_lower:
        logger.debug(f"Extract exp: Found senior/lead keyword -> 5 years")
        return 5
    
    # Extract numeric values
    patterns = [
        r'(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)',  # "2-5 years"
        r'(\d+)\+\s*(?:years?|yrs?)',                # "3+ years"
        r'(\d+)\s*(?:years?|yrs?)',                  # "2 years"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, criteria_lower)
        if match:
            # Take the first number (minimum for ranges)
            years = int(match.group(1))
            logger.debug(f"Extract exp: Found numeric pattern '{pattern}' -> {years} years")
            return years
    
    logger.debug(f"Extract exp: No experience pattern found in '{criteria}'")
    return None


def extract_job_experience(job_text: str) -> Optional[int]:
    """
    Extract required years of experience from job description.
    
    Returns:
        int: Minimum required years, or None if no requirement found
    
    Patterns matched:
    - "4-7 years" -> 4
    - "5+ years" -> 5
    - "minimum 3 years" -> 3
    - "at least 2 years" -> 2
    - "junior" -> 2
    - "senior" -> 5
    """
    job_text_lower = job_text.lower()
    
    # Check for seniority keywords first
    if re.search(r'\b(?:junior|entry.level|graduate)\b', job_text_lower):
        return 2
    if re.search(r'\b(?:mid.level|intermediate)\b', job_text_lower):
        return 3
    if re.search(r'\b(?:senior|lead|principal|staff)\b', job_text_lower):
        return 5
    
    # Extract numeric experience requirements
    patterns = [
        r'(?:minimum|min|at least)\s*(?:of)?\s*(\d+)\s*(?:\+)?\s*(?:years?|yrs?)',  # "minimum 3 years"
        r'(\d+)\s*[-–]\s*(\d+)\+?\s*(?:years?|yrs?)',                                # "4-7 years"
        r'(\d+)\+\s*(?:years?|yrs?)',                                                 # "5+ years"
        r'(\d+)\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)',                  # "3 years experience"
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, job_text_lower)
        for match in matches:
            try:
                # Take the first number (minimum for ranges)
                return int(match.group(1))
            except (ValueError, IndexError):
                continue
    
    return None


def demo_filter_jobs(jobs: List[Dict[str, Any]], user_criteria: str) -> Dict[str, Any]:
    """
    Legacy demo filtering mode - kept for backwards compatibility.
    Use robust_filter_jobs instead.
    """
    # Redirect to robust filtering without descriptions
    return robust_filter_jobs(jobs, user_criteria, None)


def get_ai_job_insights(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get AI insights about a specific job.
    (Currently disabled - full AI mode coming soon!)
    
    Args:
        job: Job dictionary
    
    Returns:
        Dict with insights like seniority level, required skills, etc.
    """
    # Return placeholder insights
    return {
        "seniority_level": "unknown",
        "required_skills": [],
        "experience_years": "unknown",
        "work_type": "unknown",
        "key_responsibilities": [],
        "salary_range": None,
        "match_score": 0
    }