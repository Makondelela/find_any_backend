"""
Profile Data Access
====================
Firebase Realtime Database access for the Profile feature.

The existing project already uses a Firebase-backed profile with separate keyed
child nodes for repeatable records. This service extends that structure to a
full job-application profile while retaining the same ownership and storage model.
"""

from datetime import datetime, timezone
from firebase_admin import db as firebase_db

from user_profile.crypto import decrypt_field, encrypt_field

PERSONAL_FIELDS = [
    'first_name', 'middle_name', 'last_name', 'preferred_name', 'id_number',
    'date_of_birth', 'gender', 'ethnicity', 'nationality', 'country',
    'country_of_residence', 'city', 'province', 'postal_code',
    'email', 'alternative_email', 'contact_number', 'alternative_contact_number',
    'street_address', 'work_authorisation', 'willing_to_relocate',
    'willing_to_travel', 'preferred_work_arrangement', 'preferred_employment_type',
    'notice_period', 'availability_date', 'current_employment_status'
]

PROFESSIONAL_FIELDS = [
    'professional_headline', 'professional_summary', 'current_job_title',
    'current_company', 'years_of_experience', 'career_level', 'desired_job_title',
    'desired_salary', 'currency', 'linkedin_profile', 'github_profile',
    'portfolio_website'
]

APPLICATION_INFO_FIELDS = [
    'drivers_license', 'license_type', 'own_transport', 'willing_to_relocate',
    'willing_to_travel', 'notice_period', 'availability_date',
    'preferred_job_location', 'preferred_work_arrangement',
    'preferred_employment_type', 'work_authorisation', 'visa_status'
]

EDUCATION_FIELDS = [
    'institution', 'institution_type', 'qualification', 'field_of_study',
    'specialisation', 'start_date', 'end_date', 'currently_studying',
    'country', 'province', 'city', 'grade', 'description'
]

EXPERIENCE_FIELDS = [
    'company', 'position', 'employment_type', 'start_date', 'end_date',
    'currently_working_here', 'country', 'province', 'city', 'description',
    'responsibilities', 'achievements'
]

SKILL_FIELDS = ['skill_name', 'skill_category', 'proficiency_level']
CERTIFICATION_FIELDS = [
    'certification_name', 'issuing_organisation', 'issue_date', 'expiry_date',
    'credential_id', 'credential_url', 'does_not_expire'
]
LANGUAGE_FIELDS = [
    'language', 'speaking_proficiency', 'reading_proficiency',
    'writing_proficiency'
]
PROJECT_FIELDS = [
    'project_name', 'description', 'role', 'start_date', 'end_date',
    'technologies_used', 'project_url', 'github_url'
]
MEMBERSHIP_FIELDS = [
    'organisation', 'membership_type', 'membership_number', 'start_date', 'end_date'
]
REFERENCE_FIELDS = [
    'full_name', 'job_title', 'company', 'relationship', 'email',
    'contact_number', 'available_upon_request'
]
DOCUMENT_FIELDS = [
    'document_name', 'document_type', 'document_url', 'uploaded_at', 'file_name'
]

# Personal fields stored encrypted at rest (decrypted only for the owner on read)
SENSITIVE_PERSONAL_FIELDS = ['id_number', 'contact_number', 'alternative_contact_number']


def _profile_ref(uid):
    return firebase_db.reference(f'profiles/{uid}')


def _now():
    return datetime.now(timezone.utc).isoformat()


def _strip_empty(value):
    if isinstance(value, str):
        return value.strip()
    return value


def _normalise_record(payload, fields):
    record = {}
    for field in fields:
        value = payload.get(field, '')
        record[field] = _strip_empty(value)
    return record


def _records_from_section(data, section_name):
    raw = (data.get(section_name) or {}) or {}
    if not isinstance(raw, dict):
        return []
    records = [{'id': key, **value} for key, value in raw.items()]
    records.sort(key=lambda item: item.get('created_at', item.get('updated_at', '')))
    return records


def _decrypt_sensitive_personal(personal):
    if not isinstance(personal, dict):
        return {}
    decrypted = dict(personal)
    for field in SENSITIVE_PERSONAL_FIELDS:
        decrypted[field] = decrypt_field(personal.get(field, ''))
    return decrypted


def get_profile(uid):
    """Return the full profile for the current user including all sections."""
    data = _profile_ref(uid).get() or {}
    personal = _decrypt_sensitive_personal(data.get('personal', {}) or {})

    return {
        'personal': personal,
        'professional_profile': data.get('professional_profile', {}) or {},
        'education': _records_from_section(data, 'education'),
        'experience': _records_from_section(data, 'experience'),
        'skills': _records_from_section(data, 'skills'),
        'certifications': _records_from_section(data, 'certifications'),
        'languages': _records_from_section(data, 'languages'),
        'projects': _records_from_section(data, 'projects'),
        'professional_memberships': _records_from_section(data, 'professional_memberships'),
        'references': _records_from_section(data, 'references'),
        'documents': _records_from_section(data, 'documents'),
        'application_info': data.get('application_info', {}) or {},
    }


def save_personal(uid, payload):
    """Create/update the personal information section for a user."""
    personal = _normalise_record(payload, PERSONAL_FIELDS)
    for field in SENSITIVE_PERSONAL_FIELDS:
        personal[field] = encrypt_field(personal.get(field, ''))
    personal['updated_at'] = _now()
    _profile_ref(uid).child('personal').set(personal)
    for field in SENSITIVE_PERSONAL_FIELDS:
        personal[field] = decrypt_field(personal.get(field, ''))
    return personal


def save_professional(uid, payload):
    """Create/update the professional profile section."""
    professional = _normalise_record(payload, PROFESSIONAL_FIELDS)
    professional['updated_at'] = _now()
    _profile_ref(uid).child('professional_profile').set(professional)
    return professional


def save_application_info(uid, payload):
    """Create/update the application info section."""
    application_info = _normalise_record(payload, APPLICATION_INFO_FIELDS)
    application_info['updated_at'] = _now()
    _profile_ref(uid).child('application_info').set(application_info)
    return application_info


def save_section_record(uid, section_name, payload, fields):
    """Create or update a single keyed record for a repeatable section."""
    record = _normalise_record(payload, fields)
    record['updated_at'] = _now()
    if payload.get('id'):
        ref = _profile_ref(uid).child(section_name).child(payload['id'])
        if ref.get() is None:
            return None
        ref.update(record)
        return {'id': payload['id'], **ref.get()}

    record['created_at'] = _now()
    new_ref = _profile_ref(uid).child(section_name).push(record)
    return {'id': new_ref.key, **record}


def add_record(uid, section_name, payload, fields):
    return save_section_record(uid, section_name, payload, fields)


def update_record(uid, section_name, item_id, payload, fields):
    payload_with_id = dict(payload)
    payload_with_id['id'] = item_id
    return save_section_record(uid, section_name, payload_with_id, fields)


def delete_record(uid, section_name, item_id):
    ref = _profile_ref(uid).child(section_name).child(item_id)
    if ref.get() is None:
        return False
    ref.delete()
    return True


def add_education(uid, payload):
    return add_record(uid, 'education', payload, EDUCATION_FIELDS)


def update_education(uid, edu_id, payload):
    return update_record(uid, 'education', edu_id, payload, EDUCATION_FIELDS)


def delete_education(uid, edu_id):
    return delete_record(uid, 'education', edu_id)


def add_experience(uid, payload):
    return add_record(uid, 'experience', payload, EXPERIENCE_FIELDS)


def update_experience(uid, exp_id, payload):
    return update_record(uid, 'experience', exp_id, payload, EXPERIENCE_FIELDS)


def delete_experience(uid, exp_id):
    return delete_record(uid, 'experience', exp_id)


def add_skill(uid, payload):
    return add_record(uid, 'skills', payload, SKILL_FIELDS)


def update_skill(uid, skill_id, payload):
    return update_record(uid, 'skills', skill_id, payload, SKILL_FIELDS)


def delete_skill(uid, skill_id):
    return delete_record(uid, 'skills', skill_id)


def add_certification(uid, payload):
    return add_record(uid, 'certifications', payload, CERTIFICATION_FIELDS)


def update_certification(uid, cert_id, payload):
    return update_record(uid, 'certifications', cert_id, payload, CERTIFICATION_FIELDS)


def delete_certification(uid, cert_id):
    return delete_record(uid, 'certifications', cert_id)


def add_language(uid, payload):
    return add_record(uid, 'languages', payload, LANGUAGE_FIELDS)


def update_language(uid, language_id, payload):
    return update_record(uid, 'languages', language_id, payload, LANGUAGE_FIELDS)


def delete_language(uid, language_id):
    return delete_record(uid, 'languages', language_id)


def add_project(uid, payload):
    return add_record(uid, 'projects', payload, PROJECT_FIELDS)


def update_project(uid, project_id, payload):
    return update_record(uid, 'projects', project_id, payload, PROJECT_FIELDS)


def delete_project(uid, project_id):
    return delete_record(uid, 'projects', project_id)


def add_membership(uid, payload):
    return add_record(uid, 'professional_memberships', payload, MEMBERSHIP_FIELDS)


def update_membership(uid, membership_id, payload):
    return update_record(uid, 'professional_memberships', membership_id, payload, MEMBERSHIP_FIELDS)


def delete_membership(uid, membership_id):
    return delete_record(uid, 'professional_memberships', membership_id)


def add_reference(uid, payload):
    return add_record(uid, 'references', payload, REFERENCE_FIELDS)


def update_reference(uid, reference_id, payload):
    return update_record(uid, 'references', reference_id, payload, REFERENCE_FIELDS)


def delete_reference(uid, reference_id):
    return delete_record(uid, 'references', reference_id)


def add_document(uid, payload):
    return add_record(uid, 'documents', payload, DOCUMENT_FIELDS)


def update_document(uid, document_id, payload):
    return update_record(uid, 'documents', document_id, payload, DOCUMENT_FIELDS)


def delete_document(uid, document_id):
    return delete_record(uid, 'documents', document_id)
