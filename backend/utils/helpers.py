"""
Utility Functions
=================
Helper functions for data processing and formatting.
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any


def format_relative_date(date_str: str) -> str:
    """
    Convert date string to relative format (e.g. '2 days ago').
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        Relative date string
    """
    try:
        if not date_str or date_str == "Not specified":
            return "Recently"
        
        # Try parsing ISO format with timezone
        if 'T' in date_str:
            if '+' in date_str or 'Z' in date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(date_str)
        else:
            # Simple date format like "23 Feb 2026"
            dt = datetime.strptime(date_str, "%d %b %Y")
        
        # Make naive datetime aware if needed
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        delta = now - dt
        
        days = delta.days
        if days == 0:
            return "Today"
        elif days == 1:
            return "Yesterday"
        elif days < 7:
            return f"{days} days ago"
        elif days < 30:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            months = days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
    except Exception:
        return "Recently"


def truncate_text(text: str, length: int = 150) -> str:
    """
    Truncate text with ellipsis.
    
    Args:
        text: Text to truncate
        length: Maximum length
        
    Returns:
        Truncated text
    """
    if not text:
        return ""
    if len(text) > length:
        return text[:length] + "..."
    return text


def get_location_display(job: Dict[str, Any]) -> str:
    """
    Extract location for display.
    
    Args:
        job: Job dictionary
        
    Returns:
        Location string
    """
    return job.get('location') or job.get('town') or 'Location not specified'


def parse_date_for_sorting(posted: str) -> datetime:
    """
    Parse various date formats for sorting.
    
    Args:
        posted: Posted date string
        
    Returns:
        datetime object
    """
    if not posted:
        return datetime.min
    
    posted = posted.lower()
    now = datetime.now()
    
    # Extract number
    numbers = re.findall(r'(\d+)', posted)
    if not numbers:
        return datetime.min
    
    num = int(numbers[0])
    
    # Determine time unit
    if 'hour' in posted:
        return now - timedelta(hours=num)
    elif 'day' in posted:
        return now - timedelta(days=num)
    elif 'week' in posted:
        return now - timedelta(weeks=num)
    elif 'month' in posted:
        return now - timedelta(days=num * 30)
    elif 'year' in posted:
        return now - timedelta(days=num * 365)
    
    # Try parsing absolute dates
    try:
        for fmt in ['%d %b %Y', '%d %B %Y', '%Y-%m-%d']:
            try:
                return datetime.strptime(posted, fmt)
            except:
                continue
    except:
        pass
    
    return datetime.min


def extract_salary_for_sorting(salary: str) -> int:
    """
    Extract numeric value from salary string for sorting.
    
    Args:
        salary: Salary string
        
    Returns:
        Numeric salary value
    """
    salary = salary.lower()
    if 'not specified' in salary or not salary:
        return 0
    try:
        numbers = re.findall(r'[\d,]+', salary.replace(' ', ''))
        if numbers:
            return int(numbers[0].replace(',', ''))
    except:
        pass
    return 0
