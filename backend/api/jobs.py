"""
Jobs API Routes
===============
API endpoints for job operations.
"""

import logging
from flask import Blueprint, jsonify, request, current_app
from backend.services import JobService, AIFilterService, UserService
from backend.utils import truncate_text, get_location_display

logger = logging.getLogger(__name__)

jobs_bp = Blueprint('jobs', __name__, url_prefix='/api')


@jobs_bp.route('/jobs', methods=['GET'])
def get_jobs():
    """Get jobs with filters and sorting."""
    firebase_service = current_app.config['FIREBASE_SERVICE']
    
    # Get filter parameters
    keyword = request.args.get('keyword', '').strip()
    location = request.args.get('location', '').strip()
    source = request.args.get('source', '').strip()
    sort_by = request.args.get('sort', 'recent')
    view_status = request.args.get('view_status', 'all')
    username = request.args.get('username', '').strip()
    
    logger.info(f"Filter request - keyword: {keyword}, location: {location}, source: {source}, sort: {sort_by}, view_status: {view_status}")
    
    try:
        # Get jobs from Firebase
        if source:
            jobs = firebase_service.get_all_jobs(source=source.lower())
        else:
            jobs = firebase_service.get_all_jobs()
        
        # Get viewed jobs if needed
        viewed_job_ids = []
        if view_status != 'all' and username:
            viewed_job_ids = firebase_service.get_user_viewed_jobs(username)
            logger.info(f"User {username} has {len(viewed_job_ids)} viewed jobs")
        
        # Apply filters
        filtered_jobs = jobs
        
        # Keyword filter
        if keyword:
            keyword_lower = keyword.lower()
            filtered_jobs = [
                job for job in filtered_jobs
                if keyword_lower in job.get('title', '').lower() or
                   keyword_lower in job.get('company', '').lower() or
                   keyword_lower in job.get('summary', '').lower()
            ]
        
        # Location filter
        if location:
            location_lower = location.lower()
            filtered_jobs = [
                job for job in filtered_jobs
                if location_lower in job.get('location', '').lower()
            ]
        
        # View status filter
        if view_status != 'all' and username:
            if view_status == 'viewed':
                filtered_jobs = [job for job in filtered_jobs if job.get('id') in viewed_job_ids]
            elif view_status == 'not_viewed':
                filtered_jobs = [job for job in filtered_jobs if job.get('id') not in viewed_job_ids]
        
        # Sort jobs
        if sort_by == 'recent':
            filtered_jobs.sort(key=lambda x: x.get('scrapedAt', ''), reverse=True)
        elif sort_by == 'company':
            filtered_jobs.sort(key=lambda x: x.get('company', '').lower())
        elif sort_by == 'title':
            filtered_jobs.sort(key=lambda x: x.get('title', '').lower())
        
        # Format response
        return jsonify({
            'success': True,
            'jobs': filtered_jobs,
            'total': len(filtered_jobs)
        })
        
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@jobs_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get job statistics."""
    firebase_service = current_app.config['FIREBASE_SERVICE']
    
    try:
        stats = firebase_service.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@jobs_bp.route('/ai-filter', methods=['POST'])
def ai_filter_jobs():
    """Filter jobs using AI based on user criteria."""
    config = current_app.config['APP_CONFIG']
    job_service = JobService(config)
    ai_service = AIFilterService(config)
    
    criteria = request.json.get('criteria', '')
    if not criteria:
        return jsonify({
            'success': False,
            'message': 'Please provide filter criteria'
        }), 400
    
    logger.info(f"AI Filter request: '{criteria}'")
    
    # Load jobs and descriptions
    data = job_service.load_jobs_data()
    jobs = data.get('jobs', [])
    descriptions_data = job_service.load_descriptions_data()
    
    if descriptions_data:
        logger.info(f"Loaded {len(descriptions_data.get('descriptions', []))} job descriptions")
    
    # Apply AI filtering
    result = ai_service.filter_jobs(jobs, criteria, descriptions_data)
    
    if not result.get('success'):
        return jsonify(result), 500
    
    # Format jobs for response
    filtered_jobs = []
    for job in result.get('filtered_jobs', [])[:100]:
        filtered_jobs.append({
            'title': job.get('title', 'Untitled'),
            'company': job.get('company', 'Unknown'),
            'location': get_location_display(job),
            'source': job.get('source', 'Unknown'),
            'salary': job.get('salary', 'Not specified'),
            'posted': job.get('posted', 'Recently'),
            'summary': truncate_text(job.get('summary', ''), 150),
            'url': job.get('url', '#'),
            'job_type': job.get('job_type', 'Not specified'),
            'job_id': job.get('job_id', ''),
        })
    
    logger.info(f"AI Filter result: {len(filtered_jobs)} jobs matched")
    
    return jsonify({
        'success': True,
        'filtered_jobs': filtered_jobs,
        'explanation': result.get('explanation', ''),
        'total_filtered': len(filtered_jobs),
        'experience_query': result.get('experience_query', False),
        'user_experience_years': result.get('user_experience_years'),
    })


@jobs_bp.route('/ai-filter-chunked', methods=['POST'])
def ai_filter_jobs_chunked():
    """Filter jobs using AI with chunked processing."""
    config = current_app.config['APP_CONFIG']
    job_service = JobService(config)
    user_service = UserService(config)
    ai_service = AIFilterService(config)
    
    criteria = request.json.get('criteria', '')
    location_filter = request.json.get('location', '')
    source_filter = request.json.get('source', '')
    keyword_filter = request.json.get('keyword', '')
    view_status = request.json.get('view_status', 'all')
    username = request.json.get('username', '')
    
    if not criteria:
        return jsonify({
            'success': False,
            'message': 'Please provide filter criteria'
        }), 400
    
    # Load jobs
    data = job_service.load_jobs_data()
    jobs = data.get('jobs', [])
    
    if not jobs:
        return jsonify({
            'success': False,
            'message': 'No jobs available to filter'
        }), 400
    
    # Apply pre-filters
    if location_filter:
        jobs = [j for j in jobs if j.get('location', '').lower() == location_filter.lower()]
    
    if source_filter:
        jobs = [j for j in jobs if j.get('source', '').lower() == source_filter.lower()]
    
    if keyword_filter:
        keyword_lower = keyword_filter.lower()
        jobs = [j for j in jobs if keyword_lower in (j.get('title', '') or '').lower() 
                or keyword_lower in (j.get('company', '') or '').lower()
                or keyword_lower in (j.get('summary', '') or '').lower()]
    
    # Apply view status filter
    if view_status != 'all' and username:
        viewed_job_ids = user_service.get_viewed_job_ids(username)
        
        if view_status == 'viewed':
            jobs = [j for j in jobs if (j.get('job_id', '') or j.get('url', '')) in viewed_job_ids]
        elif view_status == 'not_viewed':
            jobs = [j for j in jobs if (j.get('job_id', '') or j.get('url', '')) not in viewed_job_ids]
    
    logger.info(f"Starting chunked AI filtering with {len(jobs)} jobs (after pre-filters)")
    
    # Process with chunking
    result = ai_service.filter_jobs_chunked(jobs, criteria)
    
    return jsonify(result)
