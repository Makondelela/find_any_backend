"""
Flask Web Application for Job Scraping Portal
==============================================
Serves the FindFast job search interface and handles API requests.
"""

from flask import Flask, render_template, jsonify, request, send_from_directory, session, redirect, url_for
from functools import wraps
import json
import logging
import threading
import os
from pathlib import Path
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, auth, db as firebase_db

# Initialize Flask app with correct paths
app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

# Secret key for session management - use environment variable in production
app.secret_key = os.environ.get('FLASK_SECRET_KEY', '5ede7d51b89678fb948fe097ccc119f471e9ce163f869e3f24a26bb4a3d9a25a')

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
    database_url = os.environ.get('FIREBASE_DATABASE_URL', 'https://find-any-55a42-default-rtdb.firebaseio.com/')
    
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
                scraping_status.update({
                    'running': False,
                    'status': 'complete',
                    'message': 'Scraping completed successfully!',
                    'progress': 100,
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
        
        # Check if already viewed in Firebase (prevent duplicates)
        try:
            ref = firebase_db.reference(f'user_job_views/{username}/{job_id}')
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
            log.info(f"Job view saved to Firebase: user={username}, job={job_id}")
            
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
