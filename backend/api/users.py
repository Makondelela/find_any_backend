"""
Users API Routes
================
API endpoints for user operations.
"""

import logging
from flask import Blueprint, jsonify, request, current_app
from backend.services import UserService

logger = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__, url_prefix='/api')


@users_bp.route('/track-job', methods=['POST'])
def track_job():
    """Track a job view for a user."""
    firebase_service = current_app.config['FIREBASE_SERVICE']
    
    data = request.json
    username = data.get('username', '').strip()
    job_id = data.get('job_id', '').strip()
    source = data.get('source', '').strip()
    
    if not username or not job_id or not source:
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        }), 400
    
    try:
        firebase_service.mark_job_viewed(username, source, job_id)
        return jsonify({
            'success': True,
            'message': 'Job tracked successfully'
        })
    except Exception as e:
        logger.error(f"Error tracking job: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@users_bp.route('/user-history/<username>', methods=['GET'])
def get_user_history(username: str):
    """Get viewed jobs for a user."""
    firebase_service = current_app.config['FIREBASE_SERVICE']
    
    try:
        viewed_ids = firebase_service.get_user_viewed_jobs(username.strip())
        return jsonify({
            'success': True,
            'viewed_jobs': viewed_ids,
            'total': len(viewed_ids)
        })
    except Exception as e:
        logger.error(f"Error getting user history: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
