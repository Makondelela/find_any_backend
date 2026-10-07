import unittest
from unittest.mock import patch

from backend import job_personalization


class JobPersonalizationTests(unittest.TestCase):
    def test_preferred_users_see_relevant_roles_and_experience_first(self):
        experience = {
            "under-two": {"min_years": 1, "has_requirement": True},
            "three-years": {"min_years": 3, "has_requirement": True},
            "unspecified": {"min_years": None, "has_requirement": False},
            "senior": {"min_years": 6, "has_requirement": True},
            "unrelated": {"min_years": 1, "has_requirement": True},
        }
        jobs = [
            {"job_id": "senior", "title": "Integration Engineer"},
            {"job_id": "unrelated", "title": "Data Analyst"},
            {"job_id": "three-years", "title": "Software Developer"},
            {"job_id": "unspecified", "title": "Application Developer"},
            {"job_id": "under-two", "title": "Backend Engineer"},
        ]

        expected_ids = ["under-two", "three-years", "unspecified", "senior", "unrelated"]
        with patch.object(job_personalization, "_experience_by_job_id", return_value=experience):
            for email in (
                "murendi.marytendani@gmail.com",
                "Makondelelamaps@gmail.com",
            ):
                ranked = job_personalization.prioritize_jobs_for_user(jobs, email)
                self.assertEqual([job["job_id"] for job in ranked], expected_ids)

    def test_other_users_keep_existing_order(self):
        jobs = [
            {"job_id": "unrelated", "title": "Data Analyst"},
            {"job_id": "preferred", "title": "Software Engineer"},
        ]

        self.assertIs(job_personalization.prioritize_jobs_for_user(jobs, "other@example.com"), jobs)


if __name__ == "__main__":
    unittest.main()