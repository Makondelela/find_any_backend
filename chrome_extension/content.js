(() => {
  if (window.__findFastAssistantLoaded) return;
  window.__findFastAssistantLoaded = true;

  const normalise = value => String(value || '').trim().toLowerCase().replace(/\s+/g, ' ');
  const compact = value => normalise(value).replace(/[^a-z0-9]/g, '');

  function fieldLabel(field) {
    const labels = [];
    if (field.id) {
      const linked = document.querySelector(`label[for="${CSS.escape(field.id)}"]`);
      if (linked) labels.push(linked.innerText);
    }
    const parentLabel = field.closest('label');
    if (parentLabel) labels.push(parentLabel.innerText);
    ['aria-label', 'placeholder', 'name'].forEach(attribute => {
      if (field.getAttribute(attribute)) labels.push(field.getAttribute(attribute));
    });
    const row = field.closest('tr, .form-group, .field, .form-row, .form-field');
    if (row) labels.push(row.innerText);
    return normalise(labels.join(' '));
  }

  function profileValues(profile) {
    const personal = profile.personal || {};
    const professional = profile.professional_profile || {};
    const application = profile.application_info || {};
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
    };
  }

  function valueForLabel(label, values) {
    const text = compact(label);
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
      [['currentjobtitle', 'jobtitle', 'position', 'role'], values.jobTitle],
      [['currentemployer', 'employer', 'company', 'companyname'], values.company],
      [['summary', 'professionalprofile', 'aboutyou'], values.summary],
      [['linkedin'], values.linkedin],
      [['github'], values.github],
      [['portfolio', 'website'], values.portfolio],
      [['eligibletowork', 'workauthorisation', 'workauthorization', 'visa'], values.workAuthorisation],
      [['noticeperiod'], values.noticePeriod],
      [['preferredlocation', 'joblocation'], values.preferredLocation],
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

  function inspectAndFill(profile) {
    const values = profileValues(profile);
    const fields = [...document.querySelectorAll('input, textarea, select')];
    const result = { inspected: fields.length, filled: [], skipped: [] };

    fields.forEach(field => {
      const type = normalise(field.type);
      if (['hidden', 'submit', 'button', 'reset', 'file'].includes(type) || field.disabled) return;
      const value = valueForLabel(fieldLabel(field), values);
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

    return result;
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type !== 'FILL_PROFILE') return undefined;
    try {
      sendResponse({ ok: true, result: inspectAndFill(message.profile || {}) });
    } catch (error) {
      sendResponse({ ok: false, error: error.message });
    }
    return true;
  });
})();
