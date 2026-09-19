"""
Flask Web Application for Job Scraping Portal
==============================================
Serves the FindFast job search interface and handles API requests.
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from functools import wraps
import json
import logging
import threading
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import requests
import firebase_admin
from firebase_admin import credentials, auth, db as firebase_db
from assistant_browser import assistant_browser
from user_profile import service as profile_service
from user_profile.constants import (
    ETHNICITY_OPTIONS,
    GENDER_OPTIONS,
    WORK_ARRANGEMENTS,
    EMPLOYMENT_TYPES,
    INSTITUTION_TYPES,
    SKILL_CATEGORIES,
    PROFICIENCY_LEVELS,
    LANGUAGE_PROFICIENCY,
    CAREER_LEVELS,
    DOCUMENT_TYPES,
    MEMBERSHIP_TYPES,
    REFERENCE_RELATIONSHIPS,
    WORK_AUTHORIZATION_OPTIONS,
    DRIVING_LICENSE_TYPES,
    EMPLOYMENT_STATUSES,
)
from user_profile.cv_parser import extract_text, parse_cv, CVParseError

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app with correct paths
app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

# Secret key for session management - must be set in environment variable
if not os.environ.get('FLASK_SECRET_KEY'):
    raise ValueError("FLASK_SECRET_KEY environment variable must be set")
app.secret_key = os.environ.get('FLASK_SECRET_KEY')


@app.after_request
def allow_extension_profile_requests(response):
    """Allow the companion extension to read the logged-in profile session."""
    origin = request.headers.get('Origin', '')
    if request.path == '/api/profile' and origin.startswith('chrome-extension://'):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Vary'] = 'Origin'
    return response

# Configure logging (must be before Firebase init)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
try:
    # Check if running on Render or other cloud platform
    firebase_config = os.environ.get('FIREBASE_CONFIG')
    database_url = os.environ.get('FIREBASE_DATABASE_URL')
    
    if not database_url:
        raise ValueError("FIREBASE_DATABASE_URL environment variable must be set")
    
    if firebase_config:
        # Use environment variable (JSON string) for credentials
        cred_dict = json.loads(firebase_config)
        cred = credentials.Certificate(cred_dict)
    else:
        # Use local file for development
        cred = credentials.Certificate('firebase-service-account.json')
    
    firebase_admin.initialize_app(cred, {
        'databaseURL': database_url
    })
    log.info("Firebase Admin SDK initialized successfully")
except Exception as e:
    log.warning(f"Firebase initialization failed: {e}. Authentication will not work.")

# Data file paths
DATA_DIR = Path(__file__).parent / 'data'
COMBINED_JOBS_FILE = DATA_DIR / 'data_jobs_combined.json'
USER_CHECKED_FILE = DATA_DIR / 'user_checked.json'
USER_HISTORY_FILE = DATA_DIR / 'user_history.json'

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def api_login_required(f):
    """Like login_required, but returns JSON 401 instead of redirecting (for API routes)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Scraping status
scraping_status = {
    'running': False,
    'status': 'idle',
    'message': 'No scraping in progress',
    'progress': 0,
    'last_update': None
}


def load_jobs():
    """Load jobs from the combined data file"""
    try:
        if COMBINED_JOBS_FILE.exists():
            with open(COMBINED_JOBS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('jobs', [])
        return []
    except Exception as e:
        log.error(f"Error loading jobs: {e}")
        return []


def load_user_checked():
    """Load user checked jobs"""
    try:
        if USER_CHECKED_FILE.exists():
            with open(USER_CHECKED_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        log.error(f"Error loading user checked data: {e}")
        return {}


def save_user_checked(data):
    """Save user checked jobs"""
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(USER_CHECKED_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log.error(f"Error saving user checked data: {e}")
        return False


def load_user_history():
    """Load user history data"""
    try:
        if USER_HISTORY_FILE.exists():
            with open(USER_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        log.error(f"Error loading user history: {e}")
        return {}


def save_user_history(data):
    """Save user history data"""
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(USER_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log.error(f"Error saving user history: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

ASSISTANT_ENDPOINTS = {'open', 'reset', 'fill', 'status', 'screenshot', 'click', 'select', 'key', 'scroll'}


@app.route('/assistant/api/<endpoint>', methods=['GET', 'POST', 'OPTIONS'])
@login_required
def assistant_proxy(endpoint):
    """Control the in-process Render-hosted assistant browser."""
    if endpoint not in ASSISTANT_ENDPOINTS:
        return jsonify({'ok': False, 'error': 'Unknown assistant endpoint'}), 404
    if request.method == 'OPTIONS':
        return ('', 204)

    try:
        data = request.get_json(silent=True) or {}
        if endpoint == 'open':
            result = assistant_browser.open((data.get('url') or '').strip())
        elif endpoint == 'reset':
            result = {'reset': assistant_browser.reset(), **assistant_browser.status()}
        elif endpoint == 'status':
            result = assistant_browser.status()
        elif endpoint == 'screenshot':
            result = assistant_browser.screenshot()
        elif endpoint == 'click':
            result = assistant_browser.click(float(data.get('x', 0)), float(data.get('y', 0)))
        elif endpoint == 'select':
            result = assistant_browser.select_option(
                field_id=data.get('fieldId', ''),
                field_name=data.get('fieldName', ''),
                index=int(data.get('index', 0)),
            )
        elif endpoint == 'key':
            result = assistant_browser.press_key(data.get('key', ''))
        elif endpoint == 'scroll':
            result = assistant_browser.scroll(float(data.get('deltaX', 0)), float(data.get('deltaY', 0)))
        elif endpoint == 'fill':
            uid = session.get('user', {}).get('uid')
            profile = profile_service.get_profile(uid) if uid else {}
            result = assistant_browser.fill(profile=profile, user=session.get('user'))
        else:
            result = assistant_browser.status()
        return jsonify({'ok': True, **result})
    except Exception as exc:  # noqa: BLE001
        log.warning('Assistant browser error: %s', exc)
        return jsonify({
            'ok': False,
            'error': str(exc),
        }), 502

@app.route('/')
@login_required
def index():
    """Main page - requires authentication"""
    return render_template('index.html')


@app.route('/login')
def login():
    """Login page"""
    # Redirect to home if already logged in
    if 'user' in session:
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/profile')
@login_required
def profile_page():
    """Profile page - requires authentication"""
    return render_template('profile.html')


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Verify Firebase token and create session"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'No token provided'
            }), 400
        
        # Verify the token with Firebase Admin
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')
        name = decoded_token.get('name', email.split('@')[0])
        
        # Create session
        session['user'] = {
            'uid': uid,
            'email': email,
            'name': name
        }
        
        log.info(f"User logged in: {email}")
        
        return jsonify({
            'success': True,
            'user': {
                'email': email,
                'name': name
            }
        })
        
    except Exception as e:
        log.error(f"Authentication error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 401


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """Logout user"""
    if 'user' in session:
        log.info(f"User logged out: {session['user']['email']}")
        session.pop('user', None)
    
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })


@app.route('/api/auth/user')
def get_current_user():
    """Get current logged-in user"""
    if 'user' in session:
        return jsonify({
            'success': True,
            'user': session['user']
        })
    else:
        return jsonify({
            'success': False,
            'user': None
        })


@app.route('/api/firebase-config')
def get_firebase_config():
    """Get Firebase client configuration (public data only)"""
    try:
        # These values are safe to expose to the frontend
        # They're needed for Firebase client SDK initialization
        firebase_config = os.environ.get('FIREBASE_CONFIG')
        
        if not firebase_config:
            return jsonify({
                'success': False,
                'error': 'Firebase configuration not available'
            }), 500
        
        # Parse the full config to extract client-safe values
        cred_dict = json.loads(firebase_config)
        
        project_id = cred_dict.get('project_id', '')
        client_id = cred_dict.get('client_id', '')
        
        # Use the GOOGLE_API_KEY from environment (this is the actual web API key)
        api_key = os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            log.error("GOOGLE_API_KEY environment variable not set")
            return jsonify({
                'success': False,
                'error': 'Firebase API key not configured'
            }), 500
        
        # The messaging sender ID is derived from the numeric project ID
        messaging_sender_id = os.environ.get('FIREBASE_MESSAGING_SENDER_ID', client_id)
        
        # App ID is typically from Firebase console, but we can use project_id as fallback
        app_id = os.environ.get('FIREBASE_APP_ID', f"1:{client_id}:web:{project_id[:10]}")
        
        # Extract only the public client configuration
        client_config = {
            'apiKey': api_key,
            'authDomain': f"{project_id}.firebaseapp.com",
            'projectId': project_id,
            'storageBucket': f"{project_id}.firebasestorage.app",
            'messagingSenderId': messaging_sender_id,
            'appId': app_id,
            'databaseURL': os.environ.get('FIREBASE_DATABASE_URL')
        }
        
        log.info(f"Providing Firebase config for project: {project_id}")
        
        return jsonify({
            'success': True,
            'config': client_config
        })
        
    except Exception as e:
        log.error(f"Error getting Firebase config: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load configuration'
        }), 500


@app.route('/api/admin-email')
def get_admin_email():
    """Get admin email for frontend checks"""
    admin_email = os.environ.get('ADMIN_EMAIL', '')
    return jsonify({
        'success': True,
        'adminEmail': admin_email
    })

# ══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/jobs')
def get_jobs():
    """API endpoint to get all jobs with optional filters"""
    try:
        jobs = load_jobs()
        user_checked = load_user_checked()
        
        # Get filter parameters
        keyword = request.args.get('keyword', '').lower()
        location = request.args.get('location', '')
        source = request.args.get('source', '')
        sort = request.args.get('sort', 'recent')
        
        # Apply filters
        filtered_jobs = jobs
        
        # Filter by keyword (search in title, company, description)
        if keyword:
            filtered_jobs = [
                job for job in filtered_jobs
                if keyword in job.get('title', '').lower()
                or keyword in job.get('company', '').lower()
                or keyword in job.get('description', '').lower()
            ]
        
        # Filter by location
        if location:
            filtered_jobs = [
                job for job in filtered_jobs
                if job.get('location', '') == location
            ]
        
        # Filter by source
        if source:
            filtered_jobs = [
                job for job in filtered_jobs
                if job.get('source', '') == source
            ]
        
        # Sort jobs
        if sort == 'recent':
            # Most recent first (assuming posted_date exists)
            filtered_jobs.sort(key=lambda x: x.get('posted_date', ''), reverse=True)
        elif sort == 'company':
            # Company A-Z
            filtered_jobs.sort(key=lambda x: x.get('company', '').lower())
        elif sort == 'salary':
            # Highest salary first (if salary data exists)
            filtered_jobs.sort(key=lambda x: extract_salary(x.get('salary', '')), reverse=True)
        
        # Add checked status to jobs
        for job in filtered_jobs:
            job_id = job.get('id', '')
            if job_id in user_checked:
                job['checked'] = user_checked[job_id]
        
        log.info(f"Jobs API: Total={len(jobs)}, Filtered={len(filtered_jobs)}, keyword='{keyword}', location='{location}', source='{source}', sort='{sort}'")
        
        return jsonify({
            'success': True,
            'jobs': filtered_jobs,
            'total': len(filtered_jobs)
        })
    except Exception as e:
        log.error(f"Error in get_jobs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def extract_salary(salary_str):
    """Extract numeric salary value for sorting"""
    if not salary_str:
        return 0
    # Try to extract numbers from salary string
    import re
    numbers = re.findall(r'\d+', str(salary_str))
    if numbers:
        return int(numbers[0])
    return 0


@app.route('/api/jobs/checked', methods=['POST'])
def update_checked():
    """Update checked status for a job"""
    try:
        data = request.get_json()
        job_id = data.get('job_id')
        user = data.get('user')
        checked = data.get('checked', False)
        
        if not job_id or not user:
            return jsonify({
                'success': False,
                'error': 'Missing job_id or user'
            }), 400
        
        user_checked = load_user_checked()
        
        if job_id not in user_checked:
            user_checked[job_id] = {}
        
        user_checked[job_id][user] = {
            'checked': checked,
            'timestamp': datetime.now().isoformat()
        }
        
        if save_user_checked(user_checked):
            return jsonify({
                'success': True,
                'message': 'Checked status updated'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save'
            }), 500
            
    except Exception as e:
        log.error(f"Error in update_checked: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats')
def get_stats():
    """API endpoint to get job statistics"""
    try:
        jobs = load_jobs()
        
        # Calculate stats
        jobs_by_source = {}
        jobs_by_location = {}
        
        for job in jobs:
            source = job.get('source', 'Unknown')
            location = job.get('location', 'Unknown')
            
            jobs_by_source[source] = jobs_by_source.get(source, 0) + 1
            jobs_by_location[location] = jobs_by_location.get(location, 0) + 1
        
        # Get combined_at timestamp from meta
        combined_at = 'Unknown'
        try:
            if COMBINED_JOBS_FILE.exists():
                with open(COMBINED_JOBS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    meta = data.get('meta', {})
                    combined_at = meta.get('combined_at', 'Unknown')
        except:
            pass
        
        return jsonify({
            'success': True,
            'total_jobs': len(jobs),
            'jobs_by_source': jobs_by_source,
            'jobs_by_location': jobs_by_location,
            'combined_at': combined_at
        })
    except Exception as e:
        log.error(f"Error in get_stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ai-filter-chunked', methods=['POST'])
def ai_filter_chunked():
    """AI filter endpoint that processes jobs with AI"""
    try:
        data = request.get_json()
        criteria = data.get('criteria', '')
        location = data.get('location', '')
        source = data.get('source', '')
        keyword = data.get('keyword', '')
        
        if not criteria:
            return jsonify({
                'success': False,
                'message': 'Please provide search criteria'
            }), 400
        
        # Load all jobs
        all_jobs = load_jobs()
        
        # Apply basic filters first
        filtered_jobs = all_jobs
        
        if location:
            filtered_jobs = [j for j in filtered_jobs if location.lower() in j.get('location', '').lower()]
        
        if source:
            filtered_jobs = [j for j in filtered_jobs if source.lower() in j.get('source', '').lower()]
        
        if keyword:
            filtered_jobs = [j for j in filtered_jobs if 
                           keyword.lower() in j.get('title', '').lower() or
                           keyword.lower() in j.get('description', '').lower()]
        
        # Try to use AI filtering if available
        try:
            from backend.ai_filtering import filter_jobs_by_criteria
            
            # Use AI to filter jobs based on criteria
            result = filter_jobs_by_criteria(filtered_jobs, criteria)
            
            return jsonify({
                'success': True,
                'filtered_jobs': result.get('filtered_jobs', []),
                'total_filtered': len(result.get('filtered_jobs', [])),
                'explanation': result.get('explanation', 'AI matched jobs based on your criteria')
            })
        except ImportError as ie:
            # Fallback to keyword matching if AI is not available
            log.warning(f"AI filtering not available: {ie}, using keyword matching")
            
            # Simple keyword-based filtering
            keywords = criteria.lower().split()
            matched_jobs = []
            
            for job in filtered_jobs:
                title = job.get('title', '').lower()
                description = job.get('description', '').lower()
                
                # Check if any keyword matches
                if any(kw in title or kw in description for kw in keywords):
                    matched_jobs.append(job)
            
            return jsonify({
                'success': True,
                'filtered_jobs': matched_jobs,
                'total_filtered': len(matched_jobs),
                'explanation': f'Found {len(matched_jobs)} jobs matching your keywords'
            })
            
    except Exception as e:
        log.error(f"Error in ai_filter_chunked: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/scrape', methods=['GET', 'POST'])
def trigger_scrape():
    """Trigger a new scraping job or get status"""
    # Handle GET request - return status
    if request.method == 'GET':
        return jsonify({
            'status': scraping_status['status'],
            'running': scraping_status['running'],
            'success': True,
            'message': scraping_status['message'],
            'progress': scraping_status['progress']
        })
    
    # Handle POST request - trigger scraping
    if scraping_status['running']:
        return jsonify({
            'status': 'running',
            'success': True,
            'message': 'Scraping already in progress'
        })
    
    # Start scraping in background thread
    def run_scraper():
        global scraping_status
        try:
            import subprocess
            import sys
            from pathlib import Path
            
            scraping_status.update({
                'running': True,
                'status': 'running',
                'message': 'Starting scrapers...',
                'progress': 0,
                'last_update': datetime.now().isoformat()
            })
            
            log.info("POST /api/scrape - Starting scrape request")
            
            # Get the correct path to main.py
            base_dir = Path(__file__).parent
            main_script = base_dir / 'backend' / 'main.py'
            
            log.info(f"Base directory: {base_dir}")
            log.info(f"Main script path: {main_script}")
            
            if not main_script.exists():
                log.error(f"Script not found: {main_script}")
                scraping_status.update({
                    'running': False,
                    'status': 'error',
                    'message': f'Script not found: {main_script}',
                    'last_update': datetime.now().isoformat()
                })
                return
            
            # Get search terms
            search_terms = (
                'Data Engineer, Data Analyst, Data Scientist, Data Architect, '
                'Business Intelligence, BI Developer, Machine Learning Engineer, '
                'Analytics Engineer, ETL Developer, Data Warehouse Developer, '
                'Data Quality Analyst, Data Governance Specialist, Business Analyst, '
                'Software Developer, Developer, Software Engineer, Programmer, '
                'Software Tester, software'
            )
            
            log.info(f"Running scraper with {len(search_terms.split(','))} job types")
            
            scraping_status.update({
                'message': 'Scraping jobs from multiple sources...',
                'progress': 10,
                'last_update': datetime.now().isoformat()
            })
            
            # Run the scraper script with streaming output
            process = subprocess.Popen(
                [sys.executable, str(main_script), '--json', '--search', search_terms],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                cwd=str(base_dir)
            )
            
            # Track progress
            last_scraper = None
            progress_map = {'careers24': 20, 'careerjunction': 40, 'pnet': 60, 'nri': 80, 'linkedin': 90}
            
            # Read output line by line
            for line in process.stdout:
                line_lower = line.lower()
                
                # Update status based on scraper output
                if 'careers24' in line_lower:
                    last_scraper = 'Careers24'
                    scraping_status.update({
                        'message': f'Scraping {last_scraper}...',
                        'progress': progress_map.get('careers24', 20),
                        'last_update': datetime.now().isoformat()
                    })
                elif 'careerjunction' in line_lower or 'career junction' in line_lower:
                    last_scraper = 'CareerJunction'
                    scraping_status.update({
                        'message': f'Scraping {last_scraper}...',
                        'progress': progress_map.get('careerjunction', 40),
                        'last_update': datetime.now().isoformat()
                    })
                elif 'pnet' in line_lower:
                    last_scraper = 'Pnet'
                    scraping_status.update({
                        'message': f'Scraping {last_scraper}...',
                        'progress': progress_map.get('pnet', 60),
                        'last_update': datetime.now().isoformat()
                    })
                elif 'nri' in line_lower or 'network' in line_lower:
                    last_scraper = 'NRI'
                    scraping_status.update({
                        'message': f'Scraping {last_scraper}...',
                        'progress': progress_map.get('nri', 80),
                        'last_update': datetime.now().isoformat()
                    })
                elif 'linkedin' in line_lower:
                    last_scraper = 'LinkedIn'
                    scraping_status.update({
                        'message': f'Scraping {last_scraper}...',
                        'progress': progress_map.get('linkedin', 90),
                        'last_update': datetime.now().isoformat()
                    })
                elif 'found' in line_lower and 'jobs' in line_lower:
                    # Extract job count from lines like "Found 42 jobs"
                    try:
                        import re
                        match = re.search(r'(\d+)\s+jobs?', line_lower)
                        if match and last_scraper:
                            job_count = match.group(1)
                            scraping_status.update({
                                'message': f'{last_scraper}: Found {job_count} jobs',
                                'last_update': datetime.now().isoformat()
                            })
                    except:
                        pass
                elif 'combining' in line_lower or 'merged' in line_lower:
                    scraping_status.update({
                        'message': 'Combining results...',
                        'progress': 95,
                        'last_update': datetime.now().isoformat()
                    })
                
                log.info(line.rstrip())
            
            # Wait for process to complete (no timeout - let it finish)
            process.wait()
            
            log.info(f"Scraper completed with return code: {process.returncode}")
            
            if process.returncode == 0:
                # Update status to combining
                scraping_status.update({
                    'running': True,
                    'status': 'combining',
                    'message': 'Combining jobs from all sources...',
                    'progress': 95,
                    'last_update': datetime.now().isoformat()
                })
                
                log.info("Starting combine_jobs.py...")
                
                # Run combine_jobs.py
                combine_script = base_dir / 'combine_jobs.py'
                
                if not combine_script.exists():
                    log.error(f"combine_jobs.py not found: {combine_script}")
                    scraping_status.update({
                        'running': False,
                        'status': 'error',
                        'message': f'combine_jobs.py not found',
                        'progress': 0,
                        'last_update': datetime.now().isoformat()
                    })
                    return
                
                # Run the combine script
                combine_process = subprocess.Popen(
                    [sys.executable, str(combine_script)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    cwd=str(base_dir)
                )
                
                combine_process.wait()
                combine_stdout = combine_process.stdout.read()
                
                log.info(f"combine_jobs.py completed with return code: {combine_process.returncode}")
                log.info(f"combine_jobs.py output: {combine_stdout}")
                
                if combine_process.returncode == 0:
                    scraping_status.update({
                        'running': False,
                        'status': 'complete',
                        'message': 'Scraping and combining completed successfully!',
                        'progress': 100,
                        'last_update': datetime.now().isoformat()
                    })
                else:
                    combine_stderr = combine_process.stderr.read()
                    error_msg = combine_stderr[:500] if combine_stderr else 'Unknown error'
                    log.error(f"combine_jobs.py failed: {error_msg}")
                    scraping_status.update({
                        'running': False,
                        'status': 'error',
                        'message': f'Combining failed: {error_msg}',
                        'progress': 0,
                        'last_update': datetime.now().isoformat()
                    })
            else:
                stderr_output = process.stderr.read()
                error_msg = stderr_output[:500] if stderr_output else 'Unknown error'
                log.error(f"Scraper failed: {error_msg}")
                scraping_status.update({
                    'running': False,
                    'status': 'error',
                    'message': f'Scraping failed: {error_msg}',
                    'progress': 0,
                    'last_update': datetime.now().isoformat()
                })
                
        except Exception as e:
            log.error(f"Error in scraper: {e}", exc_info=True)
            scraping_status.update({
                'running': False,
                'status': 'error',
                'message': f'Error: {str(e)}',
                'progress': 0,
                'last_update': datetime.now().isoformat()
            })
    
    # Start background thread
    thread = threading.Thread(target=run_scraper, daemon=True)
    thread.start()
    
    return jsonify({
        'status': 'success',
        'success': True,
        'message': 'Scraping started in background'
    })


@app.route('/api/scrape-status')
def scrape_status():
    """Check scraping status"""
    return jsonify({
        'success': True,
        'status': scraping_status['status'],
        'running': scraping_status['running'],
        'message': scraping_status['message'],
        'progress': scraping_status['progress'],
        'last_update': scraping_status['last_update']
    })


@app.route('/api/user-history/<username>')
def get_user_history(username):
    """Get user's job viewing history from Firebase"""
    try:
        if not username:
            return jsonify({
                'success': False,
                'error': 'Missing username'
            }), 400
        
        # Get viewed jobs from Firebase
        ref = firebase_db.reference(f'user_job_views/{username}')
        viewed_jobs_data = ref.get()
        
        if not viewed_jobs_data:
            return jsonify({
                'success': True,
                'username': username,
                'viewed_jobs': [],
                'total_viewed': 0
            })
        
        # Convert to list format
        viewed_jobs = []
        for job_id, job_data in viewed_jobs_data.items():
            viewed_jobs.append({
                'job_id': job_id,
                'job_url': job_data.get('job_url', ''),
                'viewed_at': job_data.get('viewed_at', '')
            })
        
        log.info(f"Retrieved {len(viewed_jobs)} viewed jobs for user {username}")
        
        return jsonify({
            'success': True,
            'username': username,
            'viewed_jobs': viewed_jobs,
            'total_viewed': len(viewed_jobs)
        })
        
    except Exception as e:
        log.error(f"Error in get_user_history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/track-job', methods=['POST'])
def track_job():
    """Track when a user views a job - saves only to Firebase"""
    try:
        data = request.get_json()
        username = data.get('username')  # This should be the Firebase UID
        job_id = data.get('job_id')
        job_url = data.get('job_url')
        
        if not username or not job_id:
            return jsonify({
                'success': False,
                'error': 'Missing username or job_id'
            }), 400
        
        # Hash the job_id if it's a LinkedIn URL (contains 'http://' or 'https://')
        import hashlib
        firebase_node_id = job_id
        if job_id.startswith('http://') or job_id.startswith('https://'):
            # Hash the URL to create a valid Firebase node name
            firebase_node_id = hashlib.md5(job_id.encode('utf-8')).hexdigest()
            log.info(f"Hashed LinkedIn URL: {job_id} -> {firebase_node_id}")
        
        # Check if already viewed in Firebase (prevent duplicates)
        try:
            ref = firebase_db.reference(f'user_job_views/{username}/{firebase_node_id}')
            existing = ref.get()
            
            if existing:
                log.info(f"Job already viewed: user={username}, job={job_id}")
                return jsonify({
                    'success': True,
                    'message': 'Job already tracked'
                })
            
            # Save to Firebase Realtime Database
            ref.set({
                'job_id': job_id,
                'job_url': job_url,
                'viewed_at': datetime.now().isoformat()
            })
            log.info(f"Job view saved to Firebase: user={username}, job={job_id}, firebase_node={firebase_node_id}")
            
            return jsonify({
                'success': True,
                'message': 'Job view tracked'
            })
            
        except Exception as firebase_error:
            log.error(f"Failed to save to Firebase: {firebase_error}")
            return jsonify({
                'success': False,
                'error': f'Firebase error: {str(firebase_error)}'
            }), 500
            
    except Exception as e:
        log.error(f"Error in track_job: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404


# ══════════════════════════════════════════════════════════════════════════════
# PROFILE API ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/profile/constants')
def get_profile_constants():
    """Shared dropdown options for the comprehensive profile form."""
    return jsonify({
        'success': True,
        'ethnicity_options': ETHNICITY_OPTIONS,
        'gender_options': GENDER_OPTIONS,
        'work_arrangement_options': WORK_ARRANGEMENTS,
        'employment_type_options': EMPLOYMENT_TYPES,
        'institution_type_options': INSTITUTION_TYPES,
        'skill_category_options': SKILL_CATEGORIES,
        'proficiency_level_options': PROFICIENCY_LEVELS,
        'language_proficiency_options': LANGUAGE_PROFICIENCY,
        'career_level_options': CAREER_LEVELS,
        'document_type_options': DOCUMENT_TYPES,
        'membership_type_options': MEMBERSHIP_TYPES,
        'reference_relationship_options': REFERENCE_RELATIONSHIPS,
        'work_authorisation_options': WORK_AUTHORIZATION_OPTIONS,
        'driving_license_type_options': DRIVING_LICENSE_TYPES,
        'employment_status_options': EMPLOYMENT_STATUSES,
    })


@app.route('/api/profile', methods=['GET'])
@api_login_required
def get_profile():
    """Get the current user's full profile (personal info, education, experience)."""
    try:
        uid = session['user']['uid']
        return jsonify({'success': True, 'profile': profile_service.get_profile(uid)})
    except Exception as e:
        log.error(f"Error in get_profile: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/personal', methods=['PUT'])
@api_login_required
def update_profile_personal():
    """Create/update the current user's personal information."""
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        personal = profile_service.save_personal(uid, data)
        return jsonify({'success': True, 'personal': personal})
    except Exception as e:
        log.error(f"Error in update_profile_personal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/professional', methods=['PUT'])
@api_login_required
def update_profile_professional():
    """Create/update the professional profile section for the current user."""
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.save_professional(uid, data)
        return jsonify({'success': True, 'professional_profile': record})
    except Exception as e:
        log.error(f"Error in update_profile_professional: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/application-info', methods=['PUT'])
@api_login_required
def update_profile_application_info():
    """Create/update the additional application information section for the current user."""
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.save_application_info(uid, data)
        return jsonify({'success': True, 'application_info': record})
    except Exception as e:
        log.error(f"Error in update_profile_application_info: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


CV_UPLOAD_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


@app.route('/api/profile/parse-cv', methods=['POST'])
@api_login_required
def parse_profile_cv():
    """Upload a CV (PDF/DOCX/TXT) and extract profile data instead of manual entry."""
    try:
        uploaded = request.files.get('cv')
        if not uploaded or not uploaded.filename:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        file_bytes = uploaded.read()
        if len(file_bytes) > CV_UPLOAD_MAX_BYTES:
            return jsonify({'success': False, 'error': 'File is too large (max 5MB)'}), 400

        cv_text = extract_text(uploaded.filename, file_bytes)
        extracted = parse_cv(cv_text)

        return jsonify({'success': True, 'extracted': extracted})
    except CVParseError as e:
        return jsonify({'success': False, 'error': str(e)}), 422
    except Exception as e:
        log.error(f"Error in parse_profile_cv: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/education', methods=['POST'])
@api_login_required
def create_profile_education():
    """Add a new education record for the current user."""
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.add_education(uid, data)
        return jsonify({'success': True, 'education': record})
    except Exception as e:
        log.error(f"Error in create_profile_education: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/education/<edu_id>', methods=['PUT'])
@api_login_required
def update_profile_education(edu_id):
    """Update an education record for the current user."""
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.update_education(uid, edu_id, data)
        if record is None:
            return jsonify({'success': False, 'error': 'Education record not found'}), 404
        return jsonify({'success': True, 'education': record})
    except Exception as e:
        log.error(f"Error in update_profile_education: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/education/<edu_id>', methods=['DELETE'])
@api_login_required
def delete_profile_education(edu_id):
    """Remove an education record for the current user."""
    try:
        uid = session['user']['uid']
        deleted = profile_service.delete_education(uid, edu_id)
        if not deleted:
            return jsonify({'success': False, 'error': 'Education record not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        log.error(f"Error in delete_profile_education: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/experience', methods=['POST'])
@api_login_required
def create_profile_experience():
    """Add a new work experience record for the current user."""
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.add_experience(uid, data)
        return jsonify({'success': True, 'experience': record})
    except Exception as e:
        log.error(f"Error in create_profile_experience: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/experience/<exp_id>', methods=['PUT'])
@api_login_required
def update_profile_experience(exp_id):
    """Update a work experience record for the current user."""
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.update_experience(uid, exp_id, data)
        if record is None:
            return jsonify({'success': False, 'error': 'Experience record not found'}), 404
        return jsonify({'success': True, 'experience': record})
    except Exception as e:
        log.error(f"Error in update_profile_experience: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/experience/<exp_id>', methods=['DELETE'])
@api_login_required
def delete_profile_experience(exp_id):
    """Remove a work experience record for the current user."""
    try:
        uid = session['user']['uid']
        deleted = profile_service.delete_experience(uid, exp_id)
        if not deleted:
            return jsonify({'success': False, 'error': 'Experience record not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        log.error(f"Error in delete_profile_experience: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/skills', methods=['POST'])
@api_login_required
def create_profile_skill():
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.add_skill(uid, data)
        return jsonify({'success': True, 'skill': record})
    except Exception as e:
        log.error(f"Error in create_profile_skill: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/skills/<skill_id>', methods=['PUT'])
@api_login_required
def update_profile_skill(skill_id):
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.update_skill(uid, skill_id, data)
        if record is None:
            return jsonify({'success': False, 'error': 'Skill not found'}), 404
        return jsonify({'success': True, 'skill': record})
    except Exception as e:
        log.error(f"Error in update_profile_skill: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/skills/<skill_id>', methods=['DELETE'])
@api_login_required
def delete_profile_skill(skill_id):
    try:
        uid = session['user']['uid']
        deleted = profile_service.delete_skill(uid, skill_id)
        if not deleted:
            return jsonify({'success': False, 'error': 'Skill not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        log.error(f"Error in delete_profile_skill: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/certifications', methods=['POST'])
@api_login_required
def create_profile_certification():
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.add_certification(uid, data)
        return jsonify({'success': True, 'certification': record})
    except Exception as e:
        log.error(f"Error in create_profile_certification: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/certifications/<cert_id>', methods=['PUT'])
@api_login_required
def update_profile_certification(cert_id):
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.update_certification(uid, cert_id, data)
        if record is None:
            return jsonify({'success': False, 'error': 'Certification not found'}), 404
        return jsonify({'success': True, 'certification': record})
    except Exception as e:
        log.error(f"Error in update_profile_certification: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/certifications/<cert_id>', methods=['DELETE'])
@api_login_required
def delete_profile_certification(cert_id):
    try:
        uid = session['user']['uid']
        deleted = profile_service.delete_certification(uid, cert_id)
        if not deleted:
            return jsonify({'success': False, 'error': 'Certification not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        log.error(f"Error in delete_profile_certification: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/languages', methods=['POST'])
@api_login_required
def create_profile_language():
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.add_language(uid, data)
        return jsonify({'success': True, 'language': record})
    except Exception as e:
        log.error(f"Error in create_profile_language: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/languages/<lang_id>', methods=['PUT'])
@api_login_required
def update_profile_language(lang_id):
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.update_language(uid, lang_id, data)
        if record is None:
            return jsonify({'success': False, 'error': 'Language not found'}), 404
        return jsonify({'success': True, 'language': record})
    except Exception as e:
        log.error(f"Error in update_profile_language: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/languages/<lang_id>', methods=['DELETE'])
@api_login_required
def delete_profile_language(lang_id):
    try:
        uid = session['user']['uid']
        deleted = profile_service.delete_language(uid, lang_id)
        if not deleted:
            return jsonify({'success': False, 'error': 'Language not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        log.error(f"Error in delete_profile_language: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/projects', methods=['POST'])
@api_login_required
def create_profile_project():
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.add_project(uid, data)
        return jsonify({'success': True, 'project': record})
    except Exception as e:
        log.error(f"Error in create_profile_project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/projects/<project_id>', methods=['PUT'])
@api_login_required
def update_profile_project(project_id):
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.update_project(uid, project_id, data)
        if record is None:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        return jsonify({'success': True, 'project': record})
    except Exception as e:
        log.error(f"Error in update_profile_project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/projects/<project_id>', methods=['DELETE'])
@api_login_required
def delete_profile_project(project_id):
    try:
        uid = session['user']['uid']
        deleted = profile_service.delete_project(uid, project_id)
        if not deleted:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        log.error(f"Error in delete_profile_project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/memberships', methods=['POST'])
@api_login_required
def create_profile_membership():
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.add_membership(uid, data)
        return jsonify({'success': True, 'membership': record})
    except Exception as e:
        log.error(f"Error in create_profile_membership: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/memberships/<membership_id>', methods=['PUT'])
@api_login_required
def update_profile_membership(membership_id):
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.update_membership(uid, membership_id, data)
        if record is None:
            return jsonify({'success': False, 'error': 'Membership not found'}), 404
        return jsonify({'success': True, 'membership': record})
    except Exception as e:
        log.error(f"Error in update_profile_membership: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/memberships/<membership_id>', methods=['DELETE'])
@api_login_required
def delete_profile_membership(membership_id):
    try:
        uid = session['user']['uid']
        deleted = profile_service.delete_membership(uid, membership_id)
        if not deleted:
            return jsonify({'success': False, 'error': 'Membership not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        log.error(f"Error in delete_profile_membership: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/references', methods=['POST'])
@api_login_required
def create_profile_reference():
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.add_reference(uid, data)
        return jsonify({'success': True, 'reference': record})
    except Exception as e:
        log.error(f"Error in create_profile_reference: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/references/<reference_id>', methods=['PUT'])
@api_login_required
def update_profile_reference(reference_id):
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.update_reference(uid, reference_id, data)
        if record is None:
            return jsonify({'success': False, 'error': 'Reference not found'}), 404
        return jsonify({'success': True, 'reference': record})
    except Exception as e:
        log.error(f"Error in update_profile_reference: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/references/<reference_id>', methods=['DELETE'])
@api_login_required
def delete_profile_reference(reference_id):
    try:
        uid = session['user']['uid']
        deleted = profile_service.delete_reference(uid, reference_id)
        if not deleted:
            return jsonify({'success': False, 'error': 'Reference not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        log.error(f"Error in delete_profile_reference: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/documents', methods=['POST'])
@api_login_required
def create_profile_document():
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.add_document(uid, data)
        return jsonify({'success': True, 'document': record})
    except Exception as e:
        log.error(f"Error in create_profile_document: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/documents/<document_id>', methods=['PUT'])
@api_login_required
def update_profile_document(document_id):
    try:
        uid = session['user']['uid']
        data = request.get_json(silent=True) or {}
        record = profile_service.update_document(uid, document_id, data)
        if record is None:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        return jsonify({'success': True, 'document': record})
    except Exception as e:
        log.error(f"Error in update_profile_document: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/profile/documents/<document_id>', methods=['DELETE'])
@api_login_required
def delete_profile_document(document_id):
    try:
        uid = session['user']['uid']
        deleted = profile_service.delete_document(uid, document_id)
        if not deleted:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        log.error(f"Error in delete_profile_document: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('500.html'), 500


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    log.info("Starting FindFast Flask application...")
    log.info(f"Template folder: {app.template_folder}")
    log.info(f"Static folder: {app.static_folder}")
    log.info(f"Data directory: {DATA_DIR}")
    
    # Run the Flask development server
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True
    )
