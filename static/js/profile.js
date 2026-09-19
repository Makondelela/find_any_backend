/* ═══════════════════════════════════════════════════════════════════════════
   FindFast - Profile Page JavaScript Logic
   ═══════════════════════════════════════════════════════════════════════════ */

let educationCount = 0;
let experienceCount = 0;
let skillCount = 0;
let certificationCount = 0;
let languageCount = 0;
let projectCount = 0;
let membershipCount = 0;
let referenceCount = 0;
let documentCount = 0;

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', info: 'fa-info-circle' };
    toast.innerHTML = `
        <i class="fas ${icons[type]}"></i>
        <span>${escapeHtml(message)}</span>
        <button class="toast-close" title="Close"><i class="fas fa-times"></i></button>
    `;
    container.appendChild(toast);
    toast.querySelector('.toast-close').addEventListener('click', () => toast.remove());
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function fillSelect(selectId, options, value = '') {
    const select = document.getElementById(selectId);
    if (!select) return;
    const current = select.value || value;
    select.innerHTML = '<option value="">Select...</option>';
    options.forEach(option => {
        const opt = document.createElement('option');
        opt.value = option;
        opt.textContent = option;
        select.appendChild(opt);
    });
    if (current) {
        select.value = current;
    }
}

function setFieldValue(id, value) {
    const element = document.getElementById(id);
    if (!element) return;
    if (element.tagName === 'SELECT') {
        element.value = value || '';
    } else {
        element.value = value || '';
    }
}

/* ── Education rows ────────────────────────────────────────────────────── */

function createEducationRow(record = {}) {
    educationCount += 1;
    const index = educationCount;
    const wrapper = document.createElement('div');
    wrapper.className = 'repeatable-entry';
    wrapper.dataset.recordId = record.id || '';
    wrapper.innerHTML = `
        <div class="repeatable-entry-header">
            <span class="repeatable-entry-title">Education ${index}</span>
            <button type="button" class="btn-remove-entry" title="Remove"><i class="fas fa-trash"></i></button>
        </div>
        <div class="profile-grid">
            <div class="form-group">
                <label>Institution / School Name</label>
                <input type="text" class="form-control edu-institution" value="${escapeHtml(record.institution || '')}">
            </div>
            <div class="form-group">
                <label>Qualification / Course</label>
                <input type="text" class="form-control edu-qualification" value="${escapeHtml(record.qualification || '')}">
            </div>
            <div class="form-group">
                <label>Field of Study</label>
                <input type="text" class="form-control edu-field" value="${escapeHtml(record.field_of_study || '')}">
            </div>
            <div class="form-group">
                <label>Country</label>
                <input type="text" class="form-control edu-country" value="${escapeHtml(record.country || '')}">
            </div>
            <div class="form-group">
                <label>Start Year</label>
                <input type="number" class="form-control edu-start" value="${escapeHtml(record.start_year || record.start_date || '')}">
            </div>
            <div class="form-group">
                <label>End Year</label>
                <input type="number" class="form-control edu-end" value="${escapeHtml(record.end_year || record.end_date || '')}">
            </div>
        </div>
    `;
    wrapper.querySelector('.btn-remove-entry').addEventListener('click', () => removeEntry(wrapper, 'education'));
    return wrapper;
}

function readEducationRow(wrapper) {
    return {
        id: wrapper.dataset.recordId || null,
        institution: wrapper.querySelector('.edu-institution').value.trim(),
        qualification: wrapper.querySelector('.edu-qualification').value.trim(),
        field_of_study: wrapper.querySelector('.edu-field').value.trim(),
        country: wrapper.querySelector('.edu-country').value.trim(),
        start_year: wrapper.querySelector('.edu-start').value.trim(),
        end_year: wrapper.querySelector('.edu-end').value.trim(),
    };
}

/* ── Work experience rows ─────────────────────────────────────────────── */

function createExperienceRow(record = {}) {
    experienceCount += 1;
    const index = experienceCount;
    const wrapper = document.createElement('div');
    wrapper.className = 'repeatable-entry';
    wrapper.dataset.recordId = record.id || '';
    wrapper.innerHTML = `
        <div class="repeatable-entry-header">
            <span class="repeatable-entry-title">Work Experience ${index}</span>
            <button type="button" class="btn-remove-entry" title="Remove"><i class="fas fa-trash"></i></button>
        </div>
        <div class="profile-grid">
            <div class="form-group">
                <label>Company Name</label>
                <input type="text" class="form-control exp-company" value="${escapeHtml(record.company || '')}">
            </div>
            <div class="form-group">
                <label>Job Title / Position</label>
                <input type="text" class="form-control exp-position" value="${escapeHtml(record.position || '')}">
            </div>
            <div class="form-group">
                <label>Country</label>
                <input type="text" class="form-control exp-country" value="${escapeHtml(record.country || '')}">
            </div>
            <div class="form-group">
                <label>Start Year</label>
                <input type="number" class="form-control exp-start" value="${escapeHtml(record.start_year || record.start_date || '')}">
            </div>
            <div class="form-group exp-end-group" style="${record.current_job || record.currently_working_here ? 'display:none;' : ''}">
                <label>End Year</label>
                <input type="number" class="form-control exp-end" value="${escapeHtml(record.end_year || record.end_date || '')}">
            </div>
        </div>
        <div class="checkbox-group">
            <input type="checkbox" class="exp-current" id="expCurrent${index}" ${record.current_job || record.currently_working_here ? 'checked' : ''}>
            <label for="expCurrent${index}">I currently work here</label>
        </div>
        <div class="form-group">
            <label>Description / Responsibilities</label>
            <textarea class="form-control exp-description" rows="3">${escapeHtml(record.description || '')}</textarea>
        </div>
    `;
    wrapper.querySelector('.btn-remove-entry').addEventListener('click', () => removeEntry(wrapper, 'experience'));
    const currentCheckbox = wrapper.querySelector('.exp-current');
    const endGroup = wrapper.querySelector('.exp-end-group');
    currentCheckbox.addEventListener('change', () => {
        endGroup.style.display = currentCheckbox.checked ? 'none' : '';
        if (currentCheckbox.checked) {
            wrapper.querySelector('.exp-end').value = '';
        }
    });
    return wrapper;
}

function readExperienceRow(wrapper) {
    return {
        id: wrapper.dataset.recordId || null,
        company: wrapper.querySelector('.exp-company').value.trim(),
        position: wrapper.querySelector('.exp-position').value.trim(),
        country: wrapper.querySelector('.exp-country').value.trim(),
        start_year: wrapper.querySelector('.exp-start').value.trim(),
        end_year: wrapper.querySelector('.exp-end').value.trim(),
        description: wrapper.querySelector('.exp-description').value.trim(),
        current_job: wrapper.querySelector('.exp-current').checked,
    };
}

/* ── Skills rows ───────────────────────────────────────────────────────── */

function createSkillRow(record = {}) {
    skillCount += 1;
    const index = skillCount;
    const wrapper = document.createElement('div');
    wrapper.className = 'repeatable-entry';
    wrapper.dataset.recordId = record.id || '';
    wrapper.innerHTML = `
        <div class="repeatable-entry-header">
            <span class="repeatable-entry-title">Skill ${index}</span>
            <button type="button" class="btn-remove-entry" title="Remove"><i class="fas fa-trash"></i></button>
        </div>
        <div class="profile-grid">
            <div class="form-group">
                <label>Skill Name</label>
                <input type="text" class="form-control skill-name" value="${escapeHtml(record.skill_name || '')}">
            </div>
            <div class="form-group">
                <label>Category</label>
                <input type="text" class="form-control skill-category" value="${escapeHtml(record.skill_category || '')}">
            </div>
            <div class="form-group">
                <label>Proficiency</label>
                <input type="text" class="form-control skill-proficiency" value="${escapeHtml(record.proficiency_level || '')}">
            </div>
        </div>
    `;
    wrapper.querySelector('.btn-remove-entry').addEventListener('click', () => removeEntry(wrapper, 'skills'));
    return wrapper;
}

function readSkillRow(wrapper) {
    return {
        id: wrapper.dataset.recordId || null,
        skill_name: wrapper.querySelector('.skill-name').value.trim(),
        skill_category: wrapper.querySelector('.skill-category').value.trim(),
        proficiency_level: wrapper.querySelector('.skill-proficiency').value.trim(),
    };
}

/* ── Certifications rows ───────────────────────────────────────────────── */

function createCertificationRow(record = {}) {
    certificationCount += 1;
    const index = certificationCount;
    const wrapper = document.createElement('div');
    wrapper.className = 'repeatable-entry';
    wrapper.dataset.recordId = record.id || '';
    wrapper.innerHTML = `
        <div class="repeatable-entry-header">
            <span class="repeatable-entry-title">Certification ${index}</span>
            <button type="button" class="btn-remove-entry" title="Remove"><i class="fas fa-trash"></i></button>
        </div>
        <div class="profile-grid">
            <div class="form-group">
                <label>Certification Name</label>
                <input type="text" class="form-control cert-name" value="${escapeHtml(record.certification_name || '')}">
            </div>
            <div class="form-group">
                <label>Issuing Organisation</label>
                <input type="text" class="form-control cert-org" value="${escapeHtml(record.issuing_organisation || '')}">
            </div>
            <div class="form-group">
                <label>Issue Date</label>
                <input type="date" class="form-control cert-issue" value="${escapeHtml(record.issue_date || '')}">
            </div>
            <div class="form-group">
                <label>Expiry Date</label>
                <input type="date" class="form-control cert-expiry" value="${escapeHtml(record.expiry_date || '')}">
            </div>
        </div>
    `;
    wrapper.querySelector('.btn-remove-entry').addEventListener('click', () => removeEntry(wrapper, 'certifications'));
    return wrapper;
}

function readCertificationRow(wrapper) {
    return {
        id: wrapper.dataset.recordId || null,
        certification_name: wrapper.querySelector('.cert-name').value.trim(),
        issuing_organisation: wrapper.querySelector('.cert-org').value.trim(),
        issue_date: wrapper.querySelector('.cert-issue').value.trim(),
        expiry_date: wrapper.querySelector('.cert-expiry').value.trim(),
    };
}

/* ── Languages rows ───────────────────────────────────────────────────── */

function createLanguageRow(record = {}) {
    languageCount += 1;
    const index = languageCount;
    const wrapper = document.createElement('div');
    wrapper.className = 'repeatable-entry';
    wrapper.dataset.recordId = record.id || '';
    wrapper.innerHTML = `
        <div class="repeatable-entry-header">
            <span class="repeatable-entry-title">Language ${index}</span>
            <button type="button" class="btn-remove-entry" title="Remove"><i class="fas fa-trash"></i></button>
        </div>
        <div class="profile-grid">
            <div class="form-group">
                <label>Language</label>
                <input type="text" class="form-control lang-name" value="${escapeHtml(record.language || '')}">
            </div>
            <div class="form-group">
                <label>Speaking</label>
                <input type="text" class="form-control lang-speaking" value="${escapeHtml(record.speaking_proficiency || '')}">
            </div>
            <div class="form-group">
                <label>Reading</label>
                <input type="text" class="form-control lang-reading" value="${escapeHtml(record.reading_proficiency || '')}">
            </div>
            <div class="form-group">
                <label>Writing</label>
                <input type="text" class="form-control lang-writing" value="${escapeHtml(record.writing_proficiency || '')}">
            </div>
        </div>
    `;
    wrapper.querySelector('.btn-remove-entry').addEventListener('click', () => removeEntry(wrapper, 'languages'));
    return wrapper;
}

function readLanguageRow(wrapper) {
    return {
        id: wrapper.dataset.recordId || null,
        language: wrapper.querySelector('.lang-name').value.trim(),
        speaking_proficiency: wrapper.querySelector('.lang-speaking').value.trim(),
        reading_proficiency: wrapper.querySelector('.lang-reading').value.trim(),
        writing_proficiency: wrapper.querySelector('.lang-writing').value.trim(),
    };
}

/* ── Projects rows ─────────────────────────────────────────────────────── */

function createProjectRow(record = {}) {
    projectCount += 1;
    const index = projectCount;
    const wrapper = document.createElement('div');
    wrapper.className = 'repeatable-entry';
    wrapper.dataset.recordId = record.id || '';
    wrapper.innerHTML = `
        <div class="repeatable-entry-header">
            <span class="repeatable-entry-title">Project ${index}</span>
            <button type="button" class="btn-remove-entry" title="Remove"><i class="fas fa-trash"></i></button>
        </div>
        <div class="profile-grid">
            <div class="form-group">
                <label>Project Name</label>
                <input type="text" class="form-control project-name" value="${escapeHtml(record.project_name || '')}">
            </div>
            <div class="form-group">
                <label>Role</label>
                <input type="text" class="form-control project-role" value="${escapeHtml(record.role || '')}">
            </div>
            <div class="form-group">
                <label>Start Date</label>
                <input type="date" class="form-control project-start" value="${escapeHtml(record.start_date || '')}">
            </div>
            <div class="form-group">
                <label>End Date</label>
                <input type="date" class="form-control project-end" value="${escapeHtml(record.end_date || '')}">
            </div>
            <div class="form-group form-group-wide">
                <label>Description</label>
                <textarea class="form-control project-description" rows="3">${escapeHtml(record.description || '')}</textarea>
            </div>
            <div class="form-group form-group-wide">
                <label>Technologies Used</label>
                <input type="text" class="form-control project-tech" value="${escapeHtml(record.technologies_used || '')}">
            </div>
        </div>
    `;
    wrapper.querySelector('.btn-remove-entry').addEventListener('click', () => removeEntry(wrapper, 'projects'));
    return wrapper;
}

function readProjectRow(wrapper) {
    return {
        id: wrapper.dataset.recordId || null,
        project_name: wrapper.querySelector('.project-name').value.trim(),
        role: wrapper.querySelector('.project-role').value.trim(),
        start_date: wrapper.querySelector('.project-start').value.trim(),
        end_date: wrapper.querySelector('.project-end').value.trim(),
        description: wrapper.querySelector('.project-description').value.trim(),
        technologies_used: wrapper.querySelector('.project-tech').value.trim(),
    };
}

/* ── Memberships rows ─────────────────────────────────────────────────── */

function createMembershipRow(record = {}) {
    membershipCount += 1;
    const index = membershipCount;
    const wrapper = document.createElement('div');
    wrapper.className = 'repeatable-entry';
    wrapper.dataset.recordId = record.id || '';
    wrapper.innerHTML = `
        <div class="repeatable-entry-header">
            <span class="repeatable-entry-title">Membership ${index}</span>
            <button type="button" class="btn-remove-entry" title="Remove"><i class="fas fa-trash"></i></button>
        </div>
        <div class="profile-grid">
            <div class="form-group">
                <label>Organisation</label>
                <input type="text" class="form-control membership-org" value="${escapeHtml(record.organisation || '')}">
            </div>
            <div class="form-group">
                <label>Membership Type</label>
                <input type="text" class="form-control membership-type" value="${escapeHtml(record.membership_type || '')}">
            </div>
            <div class="form-group">
                <label>Membership Number</label>
                <input type="text" class="form-control membership-number" value="${escapeHtml(record.membership_number || '')}">
            </div>
            <div class="form-group">
                <label>Start Date</label>
                <input type="date" class="form-control membership-start" value="${escapeHtml(record.start_date || '')}">
            </div>
            <div class="form-group">
                <label>End Date</label>
                <input type="date" class="form-control membership-end" value="${escapeHtml(record.end_date || '')}">
            </div>
        </div>
    `;
    wrapper.querySelector('.btn-remove-entry').addEventListener('click', () => removeEntry(wrapper, 'memberships'));
    return wrapper;
}

function readMembershipRow(wrapper) {
    return {
        id: wrapper.dataset.recordId || null,
        organisation: wrapper.querySelector('.membership-org').value.trim(),
        membership_type: wrapper.querySelector('.membership-type').value.trim(),
        membership_number: wrapper.querySelector('.membership-number').value.trim(),
        start_date: wrapper.querySelector('.membership-start').value.trim(),
        end_date: wrapper.querySelector('.membership-end').value.trim(),
    };
}

/* ── References rows ──────────────────────────────────────────────────── */

function createReferenceRow(record = {}) {
    referenceCount += 1;
    const index = referenceCount;
    const wrapper = document.createElement('div');
    wrapper.className = 'repeatable-entry';
    wrapper.dataset.recordId = record.id || '';
    wrapper.innerHTML = `
        <div class="repeatable-entry-header">
            <span class="repeatable-entry-title">Reference ${index}</span>
            <button type="button" class="btn-remove-entry" title="Remove"><i class="fas fa-trash"></i></button>
        </div>
        <div class="profile-grid">
            <div class="form-group">
                <label>Full Name</label>
                <input type="text" class="form-control ref-name" value="${escapeHtml(record.full_name || '')}">
            </div>
            <div class="form-group">
                <label>Job Title</label>
                <input type="text" class="form-control ref-title" value="${escapeHtml(record.job_title || '')}">
            </div>
            <div class="form-group">
                <label>Company</label>
                <input type="text" class="form-control ref-company" value="${escapeHtml(record.company || '')}">
            </div>
            <div class="form-group">
                <label>Relationship</label>
                <input type="text" class="form-control ref-relationship" value="${escapeHtml(record.relationship || '')}">
            </div>
            <div class="form-group">
                <label>Email</label>
                <input type="email" class="form-control ref-email" value="${escapeHtml(record.email || '')}">
            </div>
            <div class="form-group">
                <label>Contact Number</label>
                <input type="tel" class="form-control ref-phone" value="${escapeHtml(record.contact_number || '')}">
            </div>
        </div>
    `;
    wrapper.querySelector('.btn-remove-entry').addEventListener('click', () => removeEntry(wrapper, 'references'));
    return wrapper;
}

function readReferenceRow(wrapper) {
    return {
        id: wrapper.dataset.recordId || null,
        full_name: wrapper.querySelector('.ref-name').value.trim(),
        job_title: wrapper.querySelector('.ref-title').value.trim(),
        company: wrapper.querySelector('.ref-company').value.trim(),
        relationship: wrapper.querySelector('.ref-relationship').value.trim(),
        email: wrapper.querySelector('.ref-email').value.trim(),
        contact_number: wrapper.querySelector('.ref-phone').value.trim(),
    };
}

/* ── Documents rows ───────────────────────────────────────────────────── */

function createDocumentRow(record = {}) {
    documentCount += 1;
    const index = documentCount;
    const wrapper = document.createElement('div');
    wrapper.className = 'repeatable-entry';
    wrapper.dataset.recordId = record.id || '';
    wrapper.innerHTML = `
        <div class="repeatable-entry-header">
            <span class="repeatable-entry-title">Document ${index}</span>
            <button type="button" class="btn-remove-entry" title="Remove"><i class="fas fa-trash"></i></button>
        </div>
        <div class="profile-grid">
            <div class="form-group">
                <label>Document Name</label>
                <input type="text" class="form-control doc-name" value="${escapeHtml(record.document_name || '')}">
            </div>
            <div class="form-group">
                <label>Document Type</label>
                <input type="text" class="form-control doc-type" value="${escapeHtml(record.document_type || '')}">
            </div>
            <div class="form-group">
                <label>URL</label>
                <input type="url" class="form-control doc-url" value="${escapeHtml(record.document_url || '')}">
            </div>
            <div class="form-group">
                <label>File Name</label>
                <input type="text" class="form-control doc-file" value="${escapeHtml(record.file_name || '')}">
            </div>
        </div>
    `;
    wrapper.querySelector('.btn-remove-entry').addEventListener('click', () => removeEntry(wrapper, 'documents'));
    return wrapper;
}

function readDocumentRow(wrapper) {
    return {
        id: wrapper.dataset.recordId || null,
        document_name: wrapper.querySelector('.doc-name').value.trim(),
        document_type: wrapper.querySelector('.doc-type').value.trim(),
        document_url: wrapper.querySelector('.doc-url').value.trim(),
        file_name: wrapper.querySelector('.doc-file').value.trim(),
    };
}

/* ── Shared remove handling ───────────────────────────────────────────── */

async function removeEntry(wrapper, type) {
    const recordId = wrapper.dataset.recordId;
    if (!recordId) {
        wrapper.remove();
        return;
    }
    try {
        const res = await fetch(`/api/profile/${type}/${recordId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            wrapper.remove();
            showToast('Record removed', 'success');
        } else {
            showToast(data.error || 'Failed to remove record', 'error');
        }
    } catch (err) {
        console.error('Error removing record:', err);
        showToast('Failed to remove record', 'error');
    }
}

/* ── Load / populate ──────────────────────────────────────────────────── */

async function loadProfileOptions() {
    try {
        const res = await fetch('/api/profile/constants');
        if (!res.ok) return;
        const data = await res.json();
        if (!data.success) return;

        fillSelect('ethnicity', data.ethnicity_options || []);
        fillSelect('careerLevel', data.career_level_options || []);
        fillSelect('licenseType', data.driving_license_type_options || []);
        fillSelect('preferredWorkArrangement', data.work_arrangement_options || []);
        fillSelect('preferredEmploymentType', data.employment_type_options || []);
        fillSelect('workAuthorisation', data.work_authorisation_options || []);
    } catch (err) {
        console.error('Error loading profile options:', err);
    }
}

async function loadProfile() {
    try {
        const res = await fetch('/api/profile');
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }
        const data = await res.json();
        if (!data.success) {
            showToast(data.error || 'Failed to load profile', 'error');
            return;
        }
        populateProfile(data.profile, getStoredFirebaseUser());
    } catch (err) {
        console.error('Error loading profile:', err);
        showToast('Failed to load profile', 'error');
    }
}

function populateProfile(profile, firebaseUser = null) {
    const personal = profile.personal || {};
    const professional = profile.professional_profile || {};
    const applicationInfo = profile.application_info || {};
    const education = profile.education || [];
    const experience = profile.experience || [];
    const skills = profile.skills || [];
    const certifications = profile.certifications || [];
    const languages = profile.languages || [];
    const projects = profile.projects || [];
    const memberships = profile.professional_memberships || [];
    const references = profile.references || [];
    const documents = profile.documents || [];
    const displayName = firebaseUser?.displayName || '';
    const nameParts = displayName.trim().split(/\s+/).filter(Boolean);

    setFieldValue('firstName', personal.first_name || nameParts[0] || '');
    setFieldValue('lastName', personal.last_name || nameParts.slice(1).join(' ') || '');
    setFieldValue('idNumber', personal.id_number || '');
    setFieldValue('contactNumber', personal.contact_number || firebaseUser?.phoneNumber || '');
    setFieldValue('email', personal.email || firebaseUser?.email || '');
    setFieldValue('country', personal.country || '');
    setFieldValue('ethnicity', personal.ethnicity || '');

    setFieldValue('professionalHeadline', professional.professional_headline || '');
    setFieldValue('professionalSummary', professional.professional_summary || '');
    setFieldValue('currentJobTitle', professional.current_job_title || '');
    setFieldValue('currentCompany', professional.current_company || '');
    setFieldValue('yearsOfExperience', professional.years_of_experience || '');
    setFieldValue('careerLevel', professional.career_level || '');
    setFieldValue('desiredJobTitle', professional.desired_job_title || '');
    setFieldValue('desiredSalary', professional.desired_salary || '');
    setFieldValue('currency', professional.currency || '');
    setFieldValue('linkedinProfile', professional.linkedin_profile || '');
    setFieldValue('githubProfile', professional.github_profile || '');
    setFieldValue('portfolioWebsite', professional.portfolio_website || '');

    setFieldValue('driversLicense', applicationInfo.drivers_license || '');
    setFieldValue('licenseType', applicationInfo.license_type || '');
    setFieldValue('ownTransport', applicationInfo.own_transport || '');
    setFieldValue('workAuthorisation', applicationInfo.work_authorisation || '');
    setFieldValue('visaStatus', applicationInfo.visa_status || '');
    setFieldValue('preferredWorkArrangement', applicationInfo.preferred_work_arrangement || '');
    setFieldValue('preferredEmploymentType', applicationInfo.preferred_employment_type || '');
    setFieldValue('preferredJobLocation', applicationInfo.preferred_job_location || '');
    setFieldValue('willingToRelocate', applicationInfo.willing_to_relocate || '');
    setFieldValue('willingToTravel', applicationInfo.willing_to_travel || '');
    setFieldValue('noticePeriod', applicationInfo.notice_period || '');
    setFieldValue('availabilityDate', applicationInfo.availability_date || '');

    const educationList = document.getElementById('educationList');
    educationList.innerHTML = '';
    educationCount = 0;
    (education.length ? education : [{}]).forEach(record => educationList.appendChild(createEducationRow(record)));

    const experienceList = document.getElementById('experienceList');
    experienceList.innerHTML = '';
    experienceCount = 0;
    (experience.length ? experience : [{}]).forEach(record => experienceList.appendChild(createExperienceRow(record)));

    const skillsList = document.getElementById('skillsList');
    skillsList.innerHTML = '';
    skillCount = 0;
    (skills.length ? skills : [{}]).forEach(record => skillsList.appendChild(createSkillRow(record)));

    const certificationsList = document.getElementById('certificationsList');
    certificationsList.innerHTML = '';
    certificationCount = 0;
    (certifications.length ? certifications : [{}]).forEach(record => certificationsList.appendChild(createCertificationRow(record)));

    const languagesList = document.getElementById('languagesList');
    languagesList.innerHTML = '';
    languageCount = 0;
    (languages.length ? languages : [{}]).forEach(record => languagesList.appendChild(createLanguageRow(record)));

    const projectsList = document.getElementById('projectsList');
    projectsList.innerHTML = '';
    projectCount = 0;
    (projects.length ? projects : [{}]).forEach(record => projectsList.appendChild(createProjectRow(record)));

    const membershipsList = document.getElementById('membershipsList');
    membershipsList.innerHTML = '';
    membershipCount = 0;
    (memberships.length ? memberships : [{}]).forEach(record => membershipsList.appendChild(createMembershipRow(record)));

    const referencesList = document.getElementById('referencesList');
    referencesList.innerHTML = '';
    referenceCount = 0;
    (references.length ? references : [{}]).forEach(record => referencesList.appendChild(createReferenceRow(record)));

    const documentsList = document.getElementById('documentsList');
    documentsList.innerHTML = '';
    documentCount = 0;
    (documents.length ? documents : [{}]).forEach(record => documentsList.appendChild(createDocumentRow(record)));
}

function getStoredFirebaseUser() {
    try {
        return JSON.parse(sessionStorage.getItem('firebaseUser') || 'null');
    } catch (err) {
        console.error('Invalid stored Firebase user:', err);
        sessionStorage.removeItem('firebaseUser');
        return null;
    }
}

/* ── CV upload / extraction ───────────────────────────────────────────── */

async function uploadAndParseCv() {
    const fileInput = document.getElementById('cvFileInput');
    const statusEl = document.getElementById('cvUploadStatus');
    const uploadBtn = document.getElementById('uploadCvBtn');
    const file = fileInput.files[0];

    if (!file) {
        showToast('Please choose a CV file first', 'error');
        return;
    }

    const originalText = uploadBtn.innerHTML;
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Extracting...';
    statusEl.textContent = 'Reading your CV, this may take a few seconds...';
    statusEl.className = 'cv-upload-status';

    try {
        const formData = new FormData();
        formData.append('cv', file);

        const res = await fetch('/api/profile/parse-cv', { method: 'POST', body: formData });
        const data = await res.json();

        if (!data.success) {
            statusEl.textContent = data.error || 'Failed to extract data from CV';
            statusEl.className = 'cv-upload-status error';
            showToast(data.error || 'Failed to extract data from CV', 'error');
            return;
        }

        const extracted = data.extracted;
        const currentPersonal = {
            id_number: document.getElementById('idNumber').value,
            ethnicity: document.getElementById('ethnicity').value,
        };
        populateProfile({
            personal: { ...currentPersonal, ...extracted.personal },
            professional_profile: extracted.professional_profile || {},
            application_info: extracted.application_info || {},
            education: extracted.education || [],
            experience: extracted.experience || [],
            skills: extracted.skills || [],
            certifications: extracted.certifications || [],
            languages: extracted.languages || [],
            projects: extracted.projects || [],
            professional_memberships: extracted.professional_memberships || [],
            references: extracted.references || [],
            documents: extracted.documents || [],
        });

        statusEl.textContent = 'CV data extracted. Review the fields below, then click Save Profile.';
        statusEl.className = 'cv-upload-status success';
        showToast('CV data extracted - review and save', 'success');
    } catch (err) {
        console.error('Error parsing CV:', err);
        statusEl.textContent = 'Failed to extract data from CV';
        statusEl.className = 'cv-upload-status error';
        showToast('Failed to extract data from CV', 'error');
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = originalText;
    }
}

/* ── Save ──────────────────────────────────────────────────────────────── */

async function saveProfile(event) {
    event.preventDefault();
    const saveBtn = document.getElementById('saveProfileBtn');
    const originalText = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

    try {
        const personalPayload = {
            first_name: document.getElementById('firstName').value.trim(),
            last_name: document.getElementById('lastName').value.trim(),
            id_number: document.getElementById('idNumber').value.trim(),
            contact_number: document.getElementById('contactNumber').value.trim(),
            email: document.getElementById('email').value.trim(),
            country: document.getElementById('country').value.trim(),
            ethnicity: document.getElementById('ethnicity').value,
        };

        const professionalPayload = {
            professional_headline: document.getElementById('professionalHeadline').value.trim(),
            professional_summary: document.getElementById('professionalSummary').value.trim(),
            current_job_title: document.getElementById('currentJobTitle').value.trim(),
            current_company: document.getElementById('currentCompany').value.trim(),
            years_of_experience: document.getElementById('yearsOfExperience').value.trim(),
            career_level: document.getElementById('careerLevel').value,
            desired_job_title: document.getElementById('desiredJobTitle').value.trim(),
            desired_salary: document.getElementById('desiredSalary').value.trim(),
            currency: document.getElementById('currency').value.trim(),
            linkedin_profile: document.getElementById('linkedinProfile').value.trim(),
            github_profile: document.getElementById('githubProfile').value.trim(),
            portfolio_website: document.getElementById('portfolioWebsite').value.trim(),
        };

        const applicationPayload = {
            drivers_license: document.getElementById('driversLicense').value,
            license_type: document.getElementById('licenseType').value,
            own_transport: document.getElementById('ownTransport').value,
            willing_to_relocate: document.getElementById('willingToRelocate').value,
            willing_to_travel: document.getElementById('willingToTravel').value,
            notice_period: document.getElementById('noticePeriod').value.trim(),
            availability_date: document.getElementById('availabilityDate').value,
            preferred_job_location: document.getElementById('preferredJobLocation').value.trim(),
            preferred_work_arrangement: document.getElementById('preferredWorkArrangement').value,
            preferred_employment_type: document.getElementById('preferredEmploymentType').value,
            work_authorisation: document.getElementById('workAuthorisation').value,
            visa_status: document.getElementById('visaStatus').value.trim(),
        };

        const requests = [
            fetch('/api/profile/personal', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(personalPayload),
            }),
            fetch('/api/profile/professional', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(professionalPayload),
            }),
            fetch('/api/profile/application-info', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(applicationPayload),
            }),
        ];

        document.querySelectorAll('#educationList .repeatable-entry').forEach(wrapper => {
            const record = readEducationRow(wrapper);
            if (!record.institution && !record.qualification) return;
            if (record.id) {
                requests.push(fetch(`/api/profile/education/${record.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }));
            } else {
                requests.push(fetch('/api/profile/education', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }).then(async r => {
                    const d = await r.json();
                    if (d.success) wrapper.dataset.recordId = d.education.id;
                    return { ok: r.ok, json: async () => d };
                }));
            }
        });

        document.querySelectorAll('#experienceList .repeatable-entry').forEach(wrapper => {
            const record = readExperienceRow(wrapper);
            if (!record.company && !record.position) return;
            if (record.id) {
                requests.push(fetch(`/api/profile/experience/${record.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }));
            } else {
                requests.push(fetch('/api/profile/experience', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }).then(async r => {
                    const d = await r.json();
                    if (d.success) wrapper.dataset.recordId = d.experience.id;
                    return { ok: r.ok, json: async () => d };
                }));
            }
        });

        document.querySelectorAll('#skillsList .repeatable-entry').forEach(wrapper => {
            const record = readSkillRow(wrapper);
            if (!record.skill_name && !record.skill_category) return;
            if (record.id) {
                requests.push(fetch(`/api/profile/skills/${record.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }));
            } else {
                requests.push(fetch('/api/profile/skills', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }).then(async r => {
                    const d = await r.json();
                    if (d.success) wrapper.dataset.recordId = d.skill.id;
                    return { ok: r.ok, json: async () => d };
                }));
            }
        });

        document.querySelectorAll('#certificationsList .repeatable-entry').forEach(wrapper => {
            const record = readCertificationRow(wrapper);
            if (!record.certification_name && !record.issuing_organisation) return;
            if (record.id) {
                requests.push(fetch(`/api/profile/certifications/${record.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }));
            } else {
                requests.push(fetch('/api/profile/certifications', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }).then(async r => {
                    const d = await r.json();
                    if (d.success) wrapper.dataset.recordId = d.certification.id;
                    return { ok: r.ok, json: async () => d };
                }));
            }
        });

        document.querySelectorAll('#languagesList .repeatable-entry').forEach(wrapper => {
            const record = readLanguageRow(wrapper);
            if (!record.language) return;
            if (record.id) {
                requests.push(fetch(`/api/profile/languages/${record.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }));
            } else {
                requests.push(fetch('/api/profile/languages', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }).then(async r => {
                    const d = await r.json();
                    if (d.success) wrapper.dataset.recordId = d.language.id;
                    return { ok: r.ok, json: async () => d };
                }));
            }
        });

        document.querySelectorAll('#projectsList .repeatable-entry').forEach(wrapper => {
            const record = readProjectRow(wrapper);
            if (!record.project_name && !record.role) return;
            if (record.id) {
                requests.push(fetch(`/api/profile/projects/${record.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }));
            } else {
                requests.push(fetch('/api/profile/projects', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }).then(async r => {
                    const d = await r.json();
                    if (d.success) wrapper.dataset.recordId = d.project.id;
                    return { ok: r.ok, json: async () => d };
                }));
            }
        });

        document.querySelectorAll('#membershipsList .repeatable-entry').forEach(wrapper => {
            const record = readMembershipRow(wrapper);
            if (!record.organisation && !record.membership_type) return;
            if (record.id) {
                requests.push(fetch(`/api/profile/memberships/${record.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }));
            } else {
                requests.push(fetch('/api/profile/memberships', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }).then(async r => {
                    const d = await r.json();
                    if (d.success) wrapper.dataset.recordId = d.membership.id;
                    return { ok: r.ok, json: async () => d };
                }));
            }
        });

        document.querySelectorAll('#referencesList .repeatable-entry').forEach(wrapper => {
            const record = readReferenceRow(wrapper);
            if (!record.full_name && !record.company) return;
            if (record.id) {
                requests.push(fetch(`/api/profile/references/${record.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }));
            } else {
                requests.push(fetch('/api/profile/references', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }).then(async r => {
                    const d = await r.json();
                    if (d.success) wrapper.dataset.recordId = d.reference.id;
                    return { ok: r.ok, json: async () => d };
                }));
            }
        });

        document.querySelectorAll('#documentsList .repeatable-entry').forEach(wrapper => {
            const record = readDocumentRow(wrapper);
            if (!record.document_name && !record.document_url) return;
            if (record.id) {
                requests.push(fetch(`/api/profile/documents/${record.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }));
            } else {
                requests.push(fetch('/api/profile/documents', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(record),
                }).then(async r => {
                    const d = await r.json();
                    if (d.success) wrapper.dataset.recordId = d.document.id;
                    return { ok: r.ok, json: async () => d };
                }));
            }
        });

        const responses = await Promise.all(requests);
        const results = await Promise.all(responses.map(r => r.json()));
        const failed = results.find(r => !r.success);

        if (failed) {
            showToast(failed.error || 'Some changes failed to save', 'error');
        } else {
            showToast('Profile saved successfully', 'success');
        }
    } catch (err) {
        console.error('Error saving profile:', err);
        showToast('Failed to save profile', 'error');
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = originalText;
    }
}

/* ── Auth check (mirrors app.js) ───────────────────────────────────────── */

function initializeAuth() {
    const logoutBtn = document.getElementById('logoutBtn');
    const userInfo = document.getElementById('userInfo');

    fetch('/api/auth/user')
        .then(r => r.json())
        .then(userData => {
            if (userData.success && userData.user) {
                const firebaseUser = getStoredFirebaseUser();
                userInfo.textContent = firebaseUser?.displayName || userData.user.name || userData.user.email;
                loadProfileOptions().then(loadProfile);
            } else {
                window.location.href = '/login';
            }
        })
        .catch(err => {
            console.error('Auth check failed:', err);
            window.location.href = '/login';
        });

    logoutBtn.addEventListener('click', () => {
        sessionStorage.removeItem('firebaseUser');
        fetch('/api/auth/logout', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/login';
                }
            })
            .catch(() => { window.location.href = '/login'; });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initializeAuth();
    document.getElementById('addEducationBtn').addEventListener('click', () => {
        document.getElementById('educationList').appendChild(createEducationRow());
    });
    document.getElementById('addExperienceBtn').addEventListener('click', () => {
        document.getElementById('experienceList').appendChild(createExperienceRow());
    });
    document.getElementById('addSkillBtn').addEventListener('click', () => {
        document.getElementById('skillsList').appendChild(createSkillRow());
    });
    document.getElementById('addCertificationBtn').addEventListener('click', () => {
        document.getElementById('certificationsList').appendChild(createCertificationRow());
    });
    document.getElementById('addLanguageBtn').addEventListener('click', () => {
        document.getElementById('languagesList').appendChild(createLanguageRow());
    });
    document.getElementById('addProjectBtn').addEventListener('click', () => {
        document.getElementById('projectsList').appendChild(createProjectRow());
    });
    document.getElementById('addMembershipBtn').addEventListener('click', () => {
        document.getElementById('membershipsList').appendChild(createMembershipRow());
    });
    document.getElementById('addReferenceBtn').addEventListener('click', () => {
        document.getElementById('referencesList').appendChild(createReferenceRow());
    });
    document.getElementById('addDocumentBtn').addEventListener('click', () => {
        document.getElementById('documentsList').appendChild(createDocumentRow());
    });
    document.getElementById('uploadCvBtn').addEventListener('click', uploadAndParseCv);
    document.getElementById('profileForm').addEventListener('submit', saveProfile);
});
