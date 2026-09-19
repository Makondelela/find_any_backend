"""
CV / Resume Parsing
====================
Extracts raw text from an uploaded CV (PDF, DOCX, or plain text) and
structures it into the Profile shape programmatically (regex + section
heuristics) - no AI involved.
"""

import io
import logging
import re

logger = logging.getLogger(__name__)


class CVParseError(Exception):
    pass


EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
# SA-style and international phone numbers: +27..., 0XXXXXXXXX, (012) 345 6789
PHONE_RE = re.compile(r'(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)\d{3,4}[\s.-]?\d{3,4}')
# "2020 - 2023", "2019 – Present", "Jan 2020 - Dec 2021"
DATE_RANGE_RE = re.compile(
    r'(?P<start>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?(?P<start_year>\d{4})'
    r'\s*(?:[-–—]|to)\s+'
    r'(?P<end>(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?(?P<end_year>\d{4})|Present|Current|Now|Ongoing|Date)',
    re.IGNORECASE,
)

EDUCATION_KEYWORDS = [
    'education', 'qualification', 'academic', 'certification', 'training', 'studies',
]
EXPERIENCE_KEYWORDS = [
    'experience', 'employment', 'work history', 'career history', 'professional history',
    'work experience', 'positions held',
]
SKILL_OR_OTHER_KEYWORDS = [
    'skills', 'references', 'languages', 'interests', 'hobbies', 'projects',
    'summary', 'profile', 'about', 'objective', 'achievements', 'links', 'contact',
]
DEGREE_KEYWORDS = [
    'bsc', 'bcom', 'ba', 'beng', 'btech', 'bed', 'llb', 'mba', 'msc', 'ma', 'phd',
    'bachelor', 'master', 'doctor', 'diploma', 'certificate', 'degree', 'honours',
    'honors', 'national diploma', 'higher certificate', 'associate', 'matric',
    'grade 12', 'high school',
]


def extract_text(filename, file_bytes):
    """Extract plain text from an uploaded CV file based on its extension."""
    ext = (filename.rsplit('.', 1)[-1] if '.' in filename else '').lower()

    if ext == 'pdf':
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise CVParseError('PDF support is not installed on the server') from e
        reader = PdfReader(io.BytesIO(file_bytes))
        return '\n'.join(page.extract_text() or '' for page in reader.pages)

    if ext == 'docx':
        try:
            import docx
        except ImportError as e:
            raise CVParseError('DOCX support is not installed on the server') from e
        document = docx.Document(io.BytesIO(file_bytes))
        return '\n'.join(p.text for p in document.paragraphs)

    if ext == 'txt':
        return file_bytes.decode('utf-8', errors='ignore')

    raise CVParseError('Unsupported file type. Please upload a PDF, DOCX, or TXT file.')


def _clean_lines(text):
    return [line.strip() for line in text.replace('\r', '\n').split('\n') if line.strip()]


def _is_heading(line, keywords):
    lowered = line.lower().strip(':').strip()
    return any(lowered == kw or lowered.startswith(kw + ' ') for kw in keywords) and len(line) < 60


def _split_sections(lines):
    """Split CV lines into education/experience/other chunks by known section headings."""
    sections = {'education': [], 'experience': [], 'header': [], 'ignored': []}
    current = 'header'
    for line in lines:
        if _is_heading(line, EDUCATION_KEYWORDS):
            current = 'education'
            continue
        if _is_heading(line, EXPERIENCE_KEYWORDS):
            current = 'experience'
            continue
        if current != 'header' and _is_heading(line, SKILL_OR_OTHER_KEYWORDS):
            current = 'ignored'
            continue
        if current != 'ignored':
            sections[current].append(line)
    return sections


def _extract_personal(lines):
    personal = {k: '' for k in
                ('first_name', 'last_name', 'id_number', 'contact_number', 'email', 'country', 'ethnicity')}

    joined = '\n'.join(lines)
    email = EMAIL_RE.search(joined)
    if email:
        personal['email'] = email.group(0)

    for line in lines[:20]:
        match = PHONE_RE.search(line)
        if match:
            digits = re.sub(r'\D', '', match.group(0))
            if 9 <= len(digits) <= 13:
                personal['contact_number'] = match.group(0).strip()
                break

    # SA ID number: 13 digits (YYMMDD + SSSS + citizenship + A + checksum)
    id_match = re.search(r'\b\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{4}[01]\d{3}\d\b', joined)
    if id_match:
        personal['id_number'] = id_match.group(0)

    # Name guess: first non-contact, non-heading line made of 2+ capitalized words
    for line in lines[:5]:
        if EMAIL_RE.search(line) or PHONE_RE.search(line):
            continue
        words = [w for w in re.split(r'\s+', line) if w.isalpha() or "'" in w]
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
            personal['first_name'] = words[0]
            personal['last_name'] = words[-1]
            break

    if re.search(r'\bsouth africa\b', joined, re.IGNORECASE):
        personal['country'] = 'South Africa'

    return personal


def _parse_education(lines):
    records = []
    current = None

    for line in lines:
        lowered = line.lower()
        date_match = DATE_RANGE_RE.search(line)
        is_degree_line = any(kw in lowered for kw in DEGREE_KEYWORDS)
        # An institution line is a short title-case line without a date or degree keyword
        is_institution = (
            not date_match and not is_degree_line
            and 3 <= len(line) <= 80 and not line.endswith('.')
        )

        if is_institution and (current is None or current['qualification']):
            if current and current['qualification']:
                records.append(current)
            current = {'institution': line, 'qualification': '', 'field_of_study': '',
                       'start_year': '', 'end_year': '', 'country': ''}
            continue

        if current is None:
            if date_match or is_degree_line:
                current = {'institution': '', 'qualification': '', 'field_of_study': '',
                           'start_year': '', 'end_year': '', 'country': ''}
            else:
                continue

        if date_match:
            current['start_year'] = current['start_year'] or date_match.group('start_year')
            if date_match.group('end_year'):
                current['end_year'] = date_match.group('end_year')

        if is_degree_line:
            if current['qualification']:
                records.append(current)
                current = {'institution': '', 'qualification': '', 'field_of_study': '',
                           'start_year': '', 'end_year': '', 'country': ''}
            current['qualification'] = line
            # Qualification text often contains the field, e.g. "BSc in Computer Science"
            field_match = re.search(r'(?:\bin\b|\bof\b)\s+(.+?)(?:\s*[-|,;(]|$)', line)
            if field_match and len(field_match.group(1)) < 60:
                current['field_of_study'] = field_match.group(1).strip()

    if current and (current['institution'] or current['qualification']):
        records.append(current)

    return [r for r in records if r['institution'] or r['qualification']]


def _split_title(text):
    """Split a title line into (company, position). Handles 'Position at Company' and dash-separated forms."""
    at_match = re.search(r'(.+?)\s+(?:at|@)\s+(.+)', text, re.IGNORECASE)
    if at_match:
        return at_match.group(2).strip(), at_match.group(1).strip()
    dash_match = re.search(r'(.+?)\s*[-–—|]\s*(.+)', text)
    if dash_match:
        return dash_match.group(2).strip(), dash_match.group(1).strip()
    return '', text.strip()


def _parse_experience(lines):
    records = []
    current = None
    pending = ''  # title line(s) seen before their date line

    for line in lines:
        date_match = DATE_RANGE_RE.search(line)

        if date_match:
            if current:
                records.append(current)
            title_part = DATE_RANGE_RE.sub('', line).strip(' -–—|,.')
            company, position = _split_title(title_part) if title_part else ('', '')
            current = {
                'company': company,
                'position': position,
                'start_year': date_match.group('start_year'),
                'end_year': date_match.group('end_year') or '',
                'country': '',
                'description': '',
                'current_job': date_match.group('end_year') is None,
            }
            if pending:
                # Title/company was written on the line(s) before the dates
                p_company, p_position = _split_title(pending)
                current['company'] = current['company'] or p_company
                current['position'] = current['position'] or p_position
                pending = ''
            continue

        if current is None:
            pending = line
            continue

        is_short_title = 3 <= len(line) <= 60 and not line.endswith('.')
        if is_short_title and current['description']:
            # A new title line after description bullets means the next job starts here
            records.append(current)
            current = None
            pending = line
            continue
        if not current['company'] and is_short_title:
            company, position = _split_title(line)
            current['company'] = company or line
            current['position'] = current['position'] or position
            continue
        if not current['position'] and is_short_title:
            current['position'] = line
            continue

        bullet = line.lstrip('•*-– ').strip()
        current['description'] = (current['description'] + ' ' + bullet).strip()

    if current:
        records.append(current)

    return [r for r in records if r['company'] or r['position']]


def parse_cv(cv_text):
    """Structure extracted CV text into the profile shape (no AI)."""
    cv_text = (cv_text or '').strip()
    if not cv_text:
        raise CVParseError('No readable text found in the uploaded file')

    lines = _clean_lines(cv_text)
    sections = _split_sections(lines)

    return {
        'personal': _extract_personal(lines[:30]),
        'education': _parse_education(sections['education']),
        'experience': _parse_experience(sections['experience']),
    }
