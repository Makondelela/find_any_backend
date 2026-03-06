"""
Search Configuration - Default Search Terms for Job Scrapers
=============================================================
Centralized configuration to avoid duplication across scraper files.

Used by:
  - main.py (unified scraper)
  - pnet_scraper.py (standalone)
  - career24_scraper.py (standalone)
  - careerjunction_scraper.py (standalone)
"""

# Search slugs and keywords are now provided by the user via the frontend modal
# No default search terms - they must be passed to scrapers

# Job type descriptions for metadata
JOB_TYPES = [
    "Data Engineer",
    "Data Analyst",
    "Data Scientist",
    "Data Architect",
    "Business Intelligence",
    "BI Developer",
    "Machine Learning Engineer",
    "Analytics Engineer",
    "ETL Developer",
    "Data Warehouse Developer",
    "Data Quality Analyst",
    "Data Governance Specialist",
    "business analyst",
]


def parse_search_terms(search_string: str) -> tuple[list[str], list[str]]:
    """
    Convert user search terms to both slug and keyword formats.
    
    Args:
        search_string: Comma-separated search terms (e.g., "python developer, ML engineer")
    
    Returns:
        Tuple of (slugs, keywords)
        - slugs: ["python-developer", "ml-engineer"]
        - keywords: ["Python Developer", "ML Engineer"]
    """
    if not search_string or not search_string.strip():
        # Fallback to common data job titles if no terms provided
        default_terms = "Data Engineer, Data Analyst, Data Scientist"
        search_string = default_terms
    
    terms = [term.strip() for term in search_string.split(',') if term.strip()]
    
    slugs = []
    keywords = []
    
    for term in terms:
        # Create slug: lowercase with hyphens
        slug = term.lower().replace(' ', '-')
        slugs.append(slug)
        
        # Create keyword: title case
        keyword = ' '.join(word.capitalize() for word in term.split())
        keywords.append(keyword)
    
    return slugs, keywords
