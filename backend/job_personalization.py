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
EXPERIENCE_FILE = Path(__file__).parent.parent / "data" / "data_jobs_experience.json"
PREFERRED_TITLE = re.compile(
    r"\b(?:software|developer|development|programmer|integration|backend|"
    r"back-end|frontend|front-end|full[ -]?stack|application|devops|platform)\b",
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
    """Float software/development/integration roles for the configured users."""
    if not email or email.strip().lower() not in PREFERRED_USERS:
        return jobs

    experience = _experience_by_job_id()

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