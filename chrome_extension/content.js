(() => {
  if (window.__findFastAssistantLoaded) return;
  window.__findFastAssistantLoaded = true;

  const normalise = value => String(value || '').trim().toLowerCase().replace(/\s+/g, ' ');
  const compact = value => normalise(value).replace(/[^a-z0-9]/g, '');

  function fieldLabel(field) {
    const directLabels = [];
    if (field.id) {
      const linked = document.querySelector(`label[for="${CSS.escape(field.id)}"]`);
      if (linked) directLabels.push(linked.innerText);
    }
    const parentLabel = field.closest('label');
    if (parentLabel) directLabels.push(parentLabel.innerText);
    ['aria-label', 'placeholder'].forEach(attribute => {
      if (field.getAttribute(attribute)) directLabels.push(field.getAttribute(attribute));
    });

    // Only use a nearby label when the control has no direct metadata. Never
    // use the entire row/container text because it contains other fields'
    // labels and can make every control look like the same field.
    const container = field.closest('tr, .form-group, .field, .form-row, .form-field');
    const nearbyLabel = container?.querySelector('label, .label, .field-label');
    if (nearbyLabel && !nearbyLabel.contains(field)) {
      directLabels.unshift(nearbyLabel.innerText);
    }
    ['name', 'id'].forEach(attribute => {
      if (field.getAttribute(attribute)) directLabels.push(field.getAttribute(attribute));
    });
    return normalise(directLabels.join(' '));
  }

  function profileValues(profile) {
    const personal = profile.personal || {};
    const professional = profile.professional_profile || {};
    const application = profile.application_info || {};
    const experience = Array.isArray(profile.experience) ? profile.experience : [];
    const education = Array.isArray(profile.education) ? profile.education : [];
    const latestExperience = experience[experience.length - 1] || {};
    const latestEducation = education[education.length - 1] || {};
    const latestSkill = (profile.skills || [])[((profile.skills || []).length || 1) - 1] || {};
    const latestCertification = (profile.certifications || [])[((profile.certifications || []).length || 1) - 1] || {};
    const latestLanguage = (profile.languages || [])[((profile.languages || []).length || 1) - 1] || {};
    const latestProject = (profile.projects || [])[((profile.projects || []).length || 1) - 1] || {};
    const latestMembership = (profile.professional_memberships || [])[((profile.professional_memberships || []).length || 1) - 1] || {};
    const latestReference = (profile.references || [])[((profile.references || []).length || 1) - 1] || {};
    const latestDocument = (profile.documents || [])[((profile.documents || []).length || 1) - 1] || {};
    const firstName = personal.first_name || personal.preferred_name || '';
    const lastName = personal.last_name || '';
    const fullName = [firstName, lastName].filter(Boolean).join(' ');
    return {
      firstName,
      lastName,
      fullName,
      email: personal.email || '',
      phone: personal.contact_number || '',
      idNumber: personal.id_number || '',
      dateOfBirth: personal.date_of_birth || '',
      gender: personal.gender || '',
      ethnicity: personal.ethnicity || '',
      nationality: personal.nationality || '',
      country: personal.country || personal.country_of_residence || '',
      city: personal.city || '',
      province: personal.province || '',
      postalCode: personal.postal_code || '',
      address: personal.street_address || '',
      jobTitle: professional.current_job_title || '',
      company: professional.current_company || '',
      summary: professional.professional_summary || '',
      linkedin: professional.linkedin_profile || '',
      github: professional.github_profile || '',
      portfolio: professional.portfolio_website || '',
      workAuthorisation: application.work_authorisation || personal.work_authorisation || '',
      noticePeriod: application.notice_period || personal.notice_period || '',
      preferredLocation: application.preferred_job_location || '',
      experienceCompany: latestExperience.company || professional.current_company || '',
      experiencePosition: latestExperience.position || professional.current_job_title || '',
      experienceStartDate: latestExperience.start_date || '',
      experienceEndDate: latestExperience.end_date || '',
      experienceDescription: latestExperience.description || '',
      experienceResponsibilities: latestExperience.responsibilities || '',
      experienceAchievements: latestExperience.achievements || '',
      experienceEmploymentType: latestExperience.employment_type || '',
      educationInstitution: latestEducation.institution || '',
      educationQualification: latestEducation.qualification || '',
      educationFieldOfStudy: latestEducation.field_of_study || '',
      educationStartDate: latestEducation.start_date || '',
      educationEndDate: latestEducation.end_date || '',
      educationDescription: latestEducation.description || '',
      ...personal,
      ...professional,
      ...application,
      education_institution: latestEducation.institution || '',
      education_qualification: latestEducation.qualification || '',
      education_field_of_study: latestEducation.field_of_study || '',
      education_start_date: latestEducation.start_date || '',
      education_end_date: latestEducation.end_date || '',
      education_description: latestEducation.description || '',
      education_institution_type: latestEducation.institution_type || '',
      education_specialisation: latestEducation.specialisation || '',
      education_currently_studying: latestEducation.currently_studying || '',
      education_country: latestEducation.country || '',
      education_province: latestEducation.province || '',
      education_city: latestEducation.city || '',
      education_grade: latestEducation.grade || '',
      experience_company: latestExperience.company || '',
      experience_position: latestExperience.position || '',
      experience_start_date: latestExperience.start_date || '',
      experience_end_date: latestExperience.end_date || '',
      experience_responsibilities: latestExperience.responsibilities || '',
      experience_achievements: latestExperience.achievements || '',
      experience_description: latestExperience.description || '',
      experience_employment_type: latestExperience.employment_type || '',
      experience_country: latestExperience.country || '',
      experience_province: latestExperience.province || '',
      experience_city: latestExperience.city || '',
      experience_currently_working_here: latestExperience.currently_working_here || '',
      project_name: latestProject.project_name || '',
      project_description: latestProject.description || '',
      project_role: latestProject.role || '',
      project_start_date: latestProject.start_date || '',
      project_end_date: latestProject.end_date || '',
      membership_organisation: latestMembership.organisation || '',
      membership_type: latestMembership.membership_type || '',
      membership_number: latestMembership.membership_number || '',
      membership_start_date: latestMembership.start_date || '',
      membership_end_date: latestMembership.end_date || '',
      reference_full_name: latestReference.full_name || '',
      reference_job_title: latestReference.job_title || '',
      reference_company: latestReference.company || '',
      reference_relationship: latestReference.relationship || '',
      reference_email: latestReference.email || '',
      reference_contact_number: latestReference.contact_number || '',
      document_name: latestDocument.document_name || '',
      document_type: latestDocument.document_type || '',
      document_url: latestDocument.document_url || '',
      file_name: latestDocument.file_name || '',
      ...latestSkill,
      ...latestCertification,
      ...latestLanguage,
      ...latestProject,
      ...latestMembership,
      ...latestReference,
      ...latestDocument,
    };
  }

  function aliasMatches(text, alias) {
    const compactAlias = compact(alias);
    return compactAlias === 'name'
      ? text === compactAlias
      : text.includes(compactAlias);
  }

  function valueForLabel(label, values, fieldMappings = {}) {
    const text = compact(label);
    const valueKeyMap = {
      first_name: 'firstName', last_name: 'lastName', full_name: 'fullName',
      contact_number: 'phone', id_number: 'idNumber', date_of_birth: 'dateOfBirth',
      street_address: 'address', current_job_title: 'jobTitle', current_company: 'company',
      professional_summary: 'summary', linkedin_profile: 'linkedin', github_profile: 'github',
      portfolio_website: 'portfolio', work_authorisation: 'workAuthorisation',
      notice_period: 'noticePeriod', preferred_job_location: 'preferredLocation',
      education_institution: 'educationInstitution', education_qualification: 'educationQualification',
      education_field_of_study: 'educationFieldOfStudy', education_start_date: 'educationStartDate',
      education_end_date: 'educationEndDate', education_description: 'educationDescription',
      experience_company: 'experienceCompany', experience_position: 'experiencePosition',
      experience_start_date: 'experienceStartDate', experience_end_date: 'experienceEndDate',
      experience_responsibilities: 'experienceResponsibilities', experience_achievements: 'experienceAchievements',
      experience_description: 'experienceDescription', experience_employment_type: 'experienceEmploymentType',
    };
    const mappingEntries = Object.entries(fieldMappings).sort(
      ([, left], [, right]) => Math.max(...right.map(alias => compact(alias).length))
        - Math.max(...left.map(alias => compact(alias).length))
    );
    for (const [standardKey, aliases] of mappingEntries) {
      const value = values[valueKeyMap[standardKey] || standardKey];
      if (value && aliases.some(alias => aliasMatches(text, alias))) return value;
    }
    const matches = [
      [['firstname', 'givenname'], values.firstName],
      [['surname', 'lastname', 'familyname'], values.lastName],
      [['fullname', 'applicantname'], values.fullName],
      [['email', 'emailaddress'], values.email],
      [['cell', 'mobile', 'telephone', 'phone', 'contactnumber'], values.phone],
      [['idnumber', 'identitynumber', 'passportnumber'], values.idNumber],
      [['dateofbirth', 'birthdate'], values.dateOfBirth],
      [['gender', 'sex'], values.gender],
      [['race', 'ethnicity', 'employment equity'], values.ethnicity],
      [['nationality', 'citizenship'], values.nationality],
      [['country'], values.country],
      [['province', 'state'], values.province],
      [['city', 'town', 'suburb'], values.city],
      [['postalcode', 'postcode', 'zipcode'], values.postalCode],
      [['streetaddress', 'residentialaddress', 'address'], values.address],
      [['currentjobtitle', 'currentposition', 'jobtitle', 'positiontitle', 'roletitle'], values.jobTitle],
      [['currentemployer', 'currentcompany'], values.company],
      [['employer', 'employername', 'company', 'companyname', 'organisation', 'organization'], values.experienceCompany],
      [['jobtitle', 'position', 'positiontitle', 'roletitle', 'role'], values.experiencePosition],
      [['startdate', 'fromdate', 'employmentstart'], values.experienceStartDate],
      [['enddate', 'todate', 'employmentend'], values.experienceEndDate],
      [['responsibilities', 'duties'], values.experienceResponsibilities],
      [['achievements', 'accomplishments'], values.experienceAchievements],
      [['workdescription', 'jobdescription', 'description'], values.experienceDescription],
      [['employmenttype', 'typeofemployment'], values.experienceEmploymentType],
      [['summary', 'professionalprofile', 'aboutyou'], values.summary],
      [['linkedin'], values.linkedin],
      [['github'], values.github],
      [['portfolio', 'website'], values.portfolio],
      [['eligibletowork', 'workauthorisation', 'workauthorization', 'visa'], values.workAuthorisation],
      [['noticeperiod'], values.noticePeriod],
      [['preferredlocation', 'joblocation'], values.preferredLocation],
      [['institution', 'school', 'college', 'university'], values.educationInstitution],
      [['qualification', 'degree', 'highestqualification'], values.educationQualification],
      [['fieldofstudy', 'major', 'specialization', 'specialisation'], values.educationFieldOfStudy],
      [['educationstartdate', 'studystartdate', 'fromdate'], values.educationStartDate],
      [['educationenddate', 'studyenddate', 'todate'], values.educationEndDate],
      [['educationdescription', 'coursedescription'], values.educationDescription],
    ];
    const match = matches.find(([keys, value]) => value && keys.some(key => text.includes(compact(key))));
    return match ? match[1] : '';
  }

  function setNativeValue(field, value) {
    const prototype = field.tagName === 'TEXTAREA'
      ? HTMLTextAreaElement.prototype
      : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set;
    if (setter) setter.call(field, value);
    else field.value = value;
    field.dispatchEvent(new Event('input', { bubbles: true }));
    field.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function selectValue(field, value) {
    const wanted = normalise(value);
    const option = [...field.options].find(item =>
      normalise(item.textContent) === wanted || normalise(item.value) === wanted
    ) || [...field.options].find(item =>
      normalise(item.textContent).includes(wanted) || wanted.includes(normalise(item.textContent))
    );
    if (!option) return false;
    field.value = option.value;
    field.dispatchEvent(new Event('input', { bubbles: true }));
    field.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }

  const SECTION_KEYS = {
    education: ['education_', 'institution', 'qualification', 'degree', 'field of study', 'school'],
    experience: ['experience_', 'employer', 'company', 'job title', 'position', 'responsibilities', 'employment'],
  };

  function sectionForLabel(label, field = null) {
    const text = normalise(label);
    if (SECTION_KEYS.education.some(token => text.includes(token))) return 'education';
    if (['employer', 'employment', 'responsibilities', 'experience', 'work history'].some(token => text.includes(token))) return 'experience';
    if (['job title', 'position', 'role'].some(token => text.includes(token))) {
      const containerText = normalise(field?.closest('tr, .form-row, [data-experience], .experience-entry, .experience-item')?.innerText);
      if (/experience|employment|work history/.test(containerText)) return 'experience';
    }
    return null;
  }

  function rowContainer(field) {
    return field.closest(
      '[data-education], [data-experience], .education-entry, .experience-entry,' +
      ' .education-item, .experience-item, .education-row, .experience-row,' +
      ' .work-experience, .work-history, .form-row, tr'
    ) || field.parentElement;
  }

  function addButtonFor(section) {
    const words = section === 'education'
      ? /add\s+(education|qualification|school|degree)|add another education/i
      : /add\s+(experience|employment|work)|add another (job|experience)/i;
    return [...document.querySelectorAll('button, a, input[type="button"], input[type="submit"]')]
      .find(button => words.test(normalise(button.innerText || button.value || button.getAttribute('aria-label'))));
  }

  function recordValues(baseValues, record, section) {
    const values = { ...baseValues };
    const prefix = section === 'education' ? 'education' : 'experience';
    const fieldMap = section === 'education'
      ? {
        institution: 'educationInstitution', qualification: 'educationQualification',
        field_of_study: 'educationFieldOfStudy', start_date: 'educationStartDate',
        end_date: 'educationEndDate', description: 'educationDescription',
        institution_type: 'education_institution_type', specialisation: 'education_specialisation',
        currently_studying: 'education_currently_studying', country: 'education_country',
        province: 'education_province', city: 'education_city', grade: 'education_grade',
      }
      : {
        company: 'experienceCompany', position: 'experiencePosition', start_date: 'experienceStartDate',
        end_date: 'experienceEndDate', responsibilities: 'experienceResponsibilities',
        achievements: 'experienceAchievements', description: 'experienceDescription',
        employment_type: 'experienceEmploymentType', country: 'experience_country',
        province: 'experience_province', city: 'experience_city',
        currently_working_here: 'experience_currently_working_here',
      };
    Object.entries(record).forEach(([key, value]) => {
      values[`${prefix}_${key}`] = value;
      values[fieldMap[key] || `${prefix}_${key}`] = value;
    });
    return values;
  }

  async function fillRepeatedSection(section, records, baseValues, fieldMappings, result) {
    if (!records.length) return;
    const orderedRecords = [...records].reverse();
    let fields = [...document.querySelectorAll('input, textarea, select')]
      .filter(field => sectionForLabel(fieldLabel(field), field) === section && !field.disabled);
    const addButton = addButtonFor(section);
    let attempts = 0;
    while (addButton && attempts < orderedRecords.length - 1) {
      const containers = new Set(fields.map(rowContainer));
      if (containers.size >= orderedRecords.length) break;
      addButton.click();
      await new Promise(resolve => setTimeout(resolve, 150));
      fields = [...document.querySelectorAll('input, textarea, select')]
        .filter(field => sectionForLabel(fieldLabel(field), field) === section && !field.disabled);
      attempts += 1;
    }

    const containers = [...new Set(fields.map(rowContainer))];
    for (let index = 0; index < Math.min(containers.length, orderedRecords.length); index += 1) {
      const values = recordValues(baseValues, orderedRecords[index], section);
      const rowFields = [...containers[index].querySelectorAll('input, textarea, select')]
        .filter(field => !field.disabled);
      rowFields.forEach(field => {
        const label = fieldLabel(field);
        const value = valueForLabel(label, values, fieldMappings);
        if (!value) return;
        const filled = field.tagName === 'SELECT' ? selectValue(field, value) : (setNativeValue(field, value), true);
        if (filled) result.filled.push(label);
      });
    }
  }

  async function inspectAndFill(profile, fieldMappings) {
    const values = profileValues(profile);
    const fields = [...document.querySelectorAll('input, textarea, select')];
    const result = { inspected: fields.length, filled: [], skipped: [] };

    fields.forEach(field => {
      const type = normalise(field.type);
      if (sectionForLabel(fieldLabel(field), field)) return;
      if (['hidden', 'submit', 'button', 'reset', 'file'].includes(type) || field.disabled) return;
      const value = valueForLabel(fieldLabel(field), values, fieldMappings);
      if (!value) {
        result.skipped.push(fieldLabel(field) || field.name || field.id || 'unlabelled field');
        return;
      }
      const filled = field.tagName === 'SELECT'
        ? selectValue(field, value)
        : (setNativeValue(field, value), true);
      if (filled) result.filled.push(fieldLabel(field) || field.name || field.id);
      else result.skipped.push(fieldLabel(field) || field.name || field.id);
    });

    await fillRepeatedSection('education', profile.education || [], values, fieldMappings, result);
    await fillRepeatedSection('experience', profile.experience || [], values, fieldMappings, result);
    return result;
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type !== 'FILL_PROFILE') return undefined;
    try {
      inspectAndFill(message.profile || {}, message.fieldMappings || {})
        .then(result => sendResponse({ ok: true, result }))
        .catch(error => sendResponse({ ok: false, error: error.message }));
    } catch (error) {
      sendResponse({ ok: false, error: error.message });
    }
    return true;
  });
})();
