"""User-specific job ordering preferences."""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


PREFERRED_USERS = frozenset({
    "murendi.marytendani@gmail.com",
    "makondelelamaps@gmail.com",
})
DATA_ROLE_USERS = frozenset({"maswimewanga26@gmail.com"})
EXPERIENCE_FILE = Path(__file__).parent.parent / "data" / "data_jobs_experience.json"
PREFERRED_TITLE = re.compile(
    r"\b(?:software|developer|development|programmer|integration|backend|"
    r"back-end|frontend|front-end|full[ -]?stack|application|devops|platform)\b",
    re.IGNORECASE,
)
DATA_TITLE = re.compile(
    r"\b(?:data|analytics?|business intelligence|\bbi\b|machine learning|database)\b",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def _experience_by_job_id() -> dict[str, dict[str, Any]]:
    try:
        with EXPERIENCE_FILE.open("r", encoding="utf-8") as experience_file:
            records = json.load(experience_file).get("experience", [])
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(record.get("job_id", "")): record for record in records}


def prioritize_jobs_for_user(
    jobs: list[dict[str, Any]], email: str | None
) -> list[dict[str, Any]]:
    """Apply configured job relevance and experience ordering for a user."""
    if not email:
        return jobs

    normalized_email = email.strip().lower()
    if normalized_email not in PREFERRED_USERS and normalized_email not in DATA_ROLE_USERS:
        return jobs

    experience = _experience_by_job_id()

    if normalized_email in DATA_ROLE_USERS:
        def data_role_rank(job: dict[str, Any]) -> tuple[int, int, float]:
            title = str(job.get("title") or "")
            is_data_role = bool(DATA_TITLE.search(title))
            record = experience.get(str(job.get("job_id", "")), {})
            years = record.get("min_years")

            try:
                numeric_years = float(years) if years is not None else None
            except (TypeError, ValueError):
                numeric_years = None

            if numeric_years is not None and numeric_years <= 5:
                experience_group = 0
                experience_value = numeric_years
            elif numeric_years is None:
                experience_group = 1
                experience_value = 0
            else:
                experience_group = 2
                experience_value = numeric_years

            return (0 if is_data_role else 1, experience_group, experience_value)

        return sorted(jobs, key=data_role_rank)

    if normalized_email not in PREFERRED_USERS:
        return jobs

    def rank(job: dict[str, Any]) -> tuple[int, int]:
        title = str(job.get("title") or "")
        preferred_title = bool(PREFERRED_TITLE.search(title))
        record = experience.get(str(job.get("job_id", "")), {})
        years = record.get("min_years")

        if years is not None and years < 2:
            experience_rank = 0
        elif years == 3:
            experience_rank = 1
        elif not record or not record.get("has_requirement") or years is None:
            experience_rank = 2
        else:
            experience_rank = 3

        return (0 if preferred_title else 1, experience_rank)

    return sorted(jobs, key=rank)