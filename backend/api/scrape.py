"""
Scrape API Routes
=================
API endpoints for scraping operations.
"""

import logging
from flask import Blueprint, jsonify, request, current_app

logger = logging.getLogger(__name__)

scrape_bp = Blueprint('scrape', __name__)


@scrape_bp.route('/scrape', methods=['POST'])
def trigger_scrape():
    """Trigger scraping process for selected sources."""
    firebase_service = current_app.config['FIREBASE_SERVICE']
    scraper_pipeline = current_app.config['SCRAPER_PIPELINE']
    
    # Get sources and search terms from request
    data = request.get_json() or {}
    sources = data.get('sources', [])
    search_terms = data.get('searchTerms', 'Data Engineer, Data Analyst')
    
    if not sources:
        return jsonify({
            'status': 'error',
            'message': 'No sources specified'
        }), 400
    
    # Validate sources
    valid_sources = ['linkedin', 'pnet', 'careerjunction', 'careers24', 'networkrecruitment']
    invalid = [s for s in sources if s.lower() not in valid_sources]
    if invalid:
        return jsonify({
            'status': 'error',
            'message': f'Invalid sources: {", ".join(invalid)}'
        }), 400
    
    # Normalize sources to lowercase
    sources = [s.lower() for s in sources]
    
    try:
        # Create scrape job in Firebase
        job_id = firebase_service.create_scrape_job(sources)
        
        # Start pipeline in background with search terms
        scraper_pipeline.start_scrape(job_id, sources, search_terms)
        
        logger.info(f"Started scrape job {job_id} for sources: {sources} with terms: {search_terms}")
        
        return jsonify({
            'status': 'success',
            'jobId': job_id,
            'message': f'Scraping started for {len(sources)} source(s)'
        })
        
    except Exception as e:
        logger.error(f"Error starting scrape: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@scrape_bp.route('/api/scrape-status/<job_id>', methods=['GET'])
def scrape_status_endpoint(job_id):
    """Get status of a specific scrape job."""
    firebase_service = current_app.config['FIREBASE_SERVICE']
    
    try:
        job = firebase_service.get_scrape_job(job_id)
        
        if not job:
            return jsonify({
                'status': 'error',
                'message': 'Job not found'
            }), 404
        
        return jsonify(job)
        
    except Exception as e:
        logger.error(f"Error getting scrape status: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

