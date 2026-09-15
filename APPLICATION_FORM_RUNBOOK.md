# Job Application Browser Runbook

## Purpose
This document is the reusable operating guide for completing job applications using the CV in this project and the browser-based app. The goal is to use the candidate CV as the source of truth, open multiple application windows clearly, and pause at the exact stages where the user must provide missing information or confirm the next step.

## Relevant project files
- CV source: [data/Makondelela_Mutshinya_FlowCV_Resume_2026-06-23.pdf](data/Makondelela_Mutshinya_FlowCV_Resume_2026-06-23.pdf)
- App entry: the FindFast web app in the browser (login page, then job listings)
- This project is built around a job-aggregator UI, so the browser workflow is manual and external employer portals are treated as separate application pages

## Objective
1. Open the app in the browser and review the jobs list.
2. Select two job opportunities.
3. Open them in two separate browser windows and label them clearly as Window 1 and Window 2.
4. Review each application form structure before filling it in.
5. Complete the form using the CV data.
6. Pause when a missing field requires user input, such as an ID number.
7. Ask the user to review the page and click Next when they are done.
8. When the attachments page appears, add the required document(s) and move to the next step.
9. Continue only after the user confirms they are ready.

## Browser workflow

### Step 1: Open the app and inspect jobs
- Open the FindFast app in the browser.
- Log in if required.
- Review the available jobs in the job listings screen.
- Select two relevant jobs that the user wants to apply for.
- Keep the job list open in the main browser window if needed for comparison.

### Step 2: Open two separate application windows
- Open Job 1 in a new browser window and label it: Window 1.
- Open Job 2 in another new browser window and label it: Window 2.
- Keep both windows visible at the same time.
- Do not mix fields between the two windows.
- Each window should represent one full job application.

### Step 3: Inspect the application form structure
Before entering data, scroll through the form in each window and identify all sections.
Typical sections may include:
- Personal details
- Contact details
- ID / passport / tax number
- Address / location
- Education
- Work experience
- Skills / competencies
- Availability / notice period
- Employment history summary
- References
- Attachments / CV upload
- Declaration / consent

This review is important because the form may be split across multiple pages. Use the structure to decide where to pause and where to ask the user for input.

### Step 4: Fill the form from the CV
Use the CV as the primary source of truth for every section the candidate can answer from the document.

The following fields should be populated from the CV unless there is a form-specific requirement for exact wording:
- Full name
- Surname / last name
- Email address
- Phone number
- Nationality / citizenship
- Residential address
- Province / city / postal code
- Education history
- Qualification names and institutions
- Work history
- Duties and responsibilities
- Skills
- Languages
- Certifications or licences
- Experience summary
- LinkedIn / website / portfolio if requested

### Step 5: Handle missing data by asking the user directly
Some values are not always present in the CV and must be confirmed by the user.

When a field is missing or uncertain, do not guess. Ask the user for it in plain language and wait for a response.

Use this exact style when asking for ID information:

> Please enter your ID number in Window 1 and send me the value before I continue.

This is the required hold point for identification data. Do not proceed until the user has supplied it.

### Step 6: Ask the user to review and proceed to the next page
After the main application details are entered, ask the user to review the page and continue.

Use this prompt:

> I am done filling in the data. Please review the page and click Next to move to the next page or submit the form if this is the final step.

This tells the user the form has been completed and the next action is to move forward.

### Step 7: Handle attachments page correctly
When the application moves to the attachment section, do not treat this as the final step. The system will usually require uploaded documents before continuing.

Use this prompt:

> I have reached the attachments page. Please upload the required document(s), including the CV, add any other required attachments, and then move to the next page. Let me know when you are done so I can continue.

This is the required checkpoint for: 
- CV upload
- Cover letter upload
- ID copy upload
- Other documents requested by the employer
- Final review before submission

### Step 8: Keep both windows synchronized
- Window 1 = the main job application being actively completed.
- Window 2 = the second application being filled in parallel.
- If one page requires the user to pause, stop only that window and continue the other only after the user confirms.
- Do not submit a form without the user checking the final page.

## Required user prompts
These prompts should be reused exactly whenever the workflow pauses for user input.

### Prompt 1: ID number
> Please enter your ID number in Window 1 and send me the value before I continue.

### Prompt 2: Review and continue
> I am done filling in the data. Please review the page and click Next to move to the next page or submit the form if this is the final step.

### Prompt 3: Attachments and next page
> I have reached the attachments page. Please upload the required document(s), including the CV, add any other required attachments, and then move to the next page. Let me know when you are done so I can continue.

## Rules for the operator
- Use the CV as the source of truth.
- Never invent missing data.
- Ask the user for values that are not in the CV.
- Keep Window 1 and Window 2 separate at all times.
- Review the form before entering data to understand the layout and page flow.
- If a page has a Next button, wait for the user to click it.
- If the form requires attachments, do not move ahead without uploading the documents.
- Only continue after the user confirms the page has been completed and the next action has been taken.
- If the application is denied or an error appears, record it and stop before making assumptions.

## Expected outcome
The workflow should end with:
- both jobs opened in separate windows,
- both forms reviewed and partially or fully completed using the CV,
- missing value(s) requested from the user and entered only after confirmation,
- user review and Next/Submit action triggered,
- attachment page handled and completed before moving to the next stage.

## Short version
1. Open the app.
2. Pick 2 jobs.
3. Open them in Window 1 and Window 2.
4. Review the application form structure.
5. Fill from the CV.
6. Ask for ID number in Window 1.
7. Ask the user to review and click Next.
8. When attachments are required, upload documents and move to the next page.
9. Ask the user to continue only after confirmation.

## Final note
This runbook is designed for a human-assisted browser workflow, not a fully automated scrape. The CV file in the project is the trusted source for personal and professional data, while the browser flow is intentionally paused for user confirmation at the exact moments where human input is necessary.
