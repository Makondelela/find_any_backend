from assistant_browser import AssistantBrowser


def test_profile_values_are_derived_from_saved_profile():
    profile = {
        'personal': {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'email': 'jane@example.com',
            'contact_number': '0821234567',
            'city': 'Cape Town',
        },
        'professional_profile': {
            'current_job_title': 'Senior Developer',
            'current_company': 'Acme Labs',
        },
    }

    values = AssistantBrowser.profile_to_fill_values(profile)

    assert values['first name'] == 'Jane'
    assert values['full name'] == 'Jane'
    assert values['surname'] == 'Doe'
    assert values['last name'] == 'Doe'
    assert values['email'] == 'jane@example.com'
    assert values['cell'] == '0821234567'
    assert values['job title'] == 'Senior Developer'
    assert values['company name'] == 'Acme Labs'
    assert values['city'] == 'Cape Town'
