"""Shared constant option lists for the Profile feature."""

# Reusable options for the comprehensive job-application profile.
# Keep this the single source of truth; the frontend fetches it via
# GET /api/profile/constants so options are not duplicated in templates/JS.
ETHNICITY_OPTIONS = [
    'African',
    'Coloured',
    'Indian/Asian',
    'White',
    'Other',
    'Prefer not to say',
]

GENDER_OPTIONS = [
    'Female',
    'Male',
    'Non-binary',
    'Prefer not to say',
    'Other',
]

WORK_ARRANGEMENTS = [
    'On-site',
    'Hybrid',
    'Remote',
]

EMPLOYMENT_TYPES = [
    'Permanent',
    'Contract',
    'Temporary',
    'Internship',
    'Graduate Programme',
]

INSTITUTION_TYPES = [
    'High School',
    'College',
    'University',
    'Technical/Vocational',
    'Other',
]

SKILL_CATEGORIES = [
    'Programming',
    'Software Development',
    'Cloud',
    'DevOps',
    'Databases',
    'Cybersecurity',
    'Data',
    'Project Management',
    'Communication',
    'Other',
]

PROFICIENCY_LEVELS = [
    'Beginner',
    'Intermediate',
    'Advanced',
    'Expert',
]

LANGUAGE_PROFICIENCY = [
    'Basic',
    'Conversational',
    'Professional',
    'Fluent',
    'Native',
]

CAREER_LEVELS = [
    'Entry Level',
    'Junior',
    'Mid-Level',
    'Senior',
    'Lead',
    'Manager',
    'Executive',
]

DOCUMENT_TYPES = [
    'CV / Resume',
    'Cover Letter',
    'Certificates',
    'Qualification Documents',
    'Other Supporting Documents',
]

MEMBERSHIP_TYPES = [
    'Professional',
    'Student',
    'Affiliate',
    'Honorary',
    'Other',
]

REFERENCE_RELATIONSHIPS = [
    'Manager',
    'Colleague',
    'Mentor',
    'Academic',
    'Client',
    'Other',
]

WORK_AUTHORIZATION_OPTIONS = [
    'Citizen',
    'Permanent Resident',
    'Work Permit / Visa',
    'Temporary Work Authorization',
    'Open to Sponsorship',
    'Prefer not to say',
]

DRIVING_LICENSE_TYPES = [
    'None',
    'Code 1',
    'Code 2',
    'Code 3',
    'Code 8',
    'Code 10',
    'Code 14',
]

EMPLOYMENT_STATUSES = [
    'Employed',
    'Unemployed',
    'Self-employed',
    'Contractor',
    'Student',
    'Retired',
    'Prefer not to say',
]
