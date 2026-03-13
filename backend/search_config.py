"""
Search Configuration - Default Search Terms for Job Scrapers
=============================================================
Centralized configuration to avoid duplication across scraper files.

Used by:
  - main.py (unified scraper)
  - pnet_scraper.py (standalone)
  - career24_scraper.py (standalone)
  - careerjunction_scraper.py (standalone)
  - linkedIn_scraper.py (standalone)
  - network_recruit_scraper.py (standalone)
"""

# Search slugs and keywords are now provided by the user via the frontend modal
# No default search terms - they must be passed to scrapers

# Default search terms - single source of truth for all scrapers
DEFAULT_SEARCH_SLUGS = [
    # Data & Analytics
    "Data Engineer",
    "Data Analyst",
    "Data Scientist",
    "Analytics Engineer",
    "Data Architect",
    "Business Intelligence",
    "Analyst",
    "BI Analyst",
    "BI Developer",
    "Business Intelligence Analyst",
    "Reporting Analyst",
    "Insights Analyst",
    "Decision Scientist",

    # AI / Machine Learning
    "Machine Learning Engineer",
    "ML Engineer",
    "AI Engineer",
    "Artificial Intelligence Engineer",
    "AI Developer",
    "Machine Learning Scientist",

    # Software Development
    "Software Engineer",
    "Software Developer",
    "Developer",
    "Programmer",
    "Application Developer",
    "Backend Developer",
    "Frontend Developer",
    "Full Stack Developer",

    # DevOps / Cloud
    "DevOps Engineer",
    "DevOps",
    "Site Reliability Engineer",
    "SRE",
    "Cloud Engineer",
    "Cloud Architect",
    "Platform Engineer",
    "AWS",
    "Azure",
    "cloud",
    "Infrastructure Engineer",

    # Cybersecurity
    "Cyber Security",
    "Cybersecurity",
    "Cybersecurity Analyst",
    "Security Engineer",
    "Security Analyst",
    "Information Security",
    "Information Security Analyst",
    "SOC Analyst",
    "Threat Analyst",
    "Penetration Tester",
    "Ethical Hacker",
    "Analyst",

    # Testing / QA
    "Software Tester",
    "QA Engineer",
    "Quality Assurance Engineer",
    "Test Engineer",


    # IT Support / Technical Support
    "IT Support",
    "Technical Support",
    "Support Engineer",
    "Application Support",
    "Production Support",
    "Customer Support Engineer",
    "Systems Support",
    "Help Desk",
    "Service Desk",
    "Desktop Support",
    "NOC Engineer",
    "Network Operations Center",
    "IT Operations",
    "Operations Engineer",
    "Technical Operations",
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
