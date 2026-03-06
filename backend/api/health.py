"""
Health API Routes
=================
API endpoints for health checks.
"""

from flask import Blueprint, jsonify, current_app
from backend.services import JobService

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    config = current_app.config['APP_CONFIG']
    job_service = JobService(config)
    
    data = job_service.load_jobs_data()
    
    return jsonify({
        'status': 'healthy',
        'jobs_available': len(data.get('jobs', [])),
    })
