"""
FindFast Job Search API
=======================
Well-structured Flask REST API backend for the FindFast job search application.

Run: python run.py
"""

import logging
from flask import Flask
from flask_cors import CORS
from backend.config import get_config
from backend.api import jobs_bp, users_bp, scrape_bp, health_bp
from backend.services.firebase_service import FirebaseService
from backend.services.scraper_pipeline import ScraperPipeline


def create_app(config_name: str = None) -> Flask:
    """
    Application factory.
    
    Args:
        config_name: Configuration name (development, production, testing)
        
    Returns:
        Flask application
    """
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)
    app.config['APP_CONFIG'] = config
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT
    )
    
    # Enable CORS
    CORS(app, origins=config.CORS_ORIGINS, supports_credentials=True)
    
    # Initialize services (singleton instances)
    firebase_service = FirebaseService(config)
    app.config['FIREBASE_SERVICE'] = firebase_service
    
    scraper_pipeline = ScraperPipeline(config, firebase_service)
    app.config['SCRAPER_PIPELINE'] = scraper_pipeline
    
    # Register blueprints
    app.register_blueprint(jobs_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(scrape_bp)
    app.register_blueprint(health_bp)
    
    # Log startup info
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("FindFast Job Search API - Backend")
    logger.info("="*60)
    logger.info(f"Environment: {config_name or 'development'}")
    logger.info(f"Debug mode: {config.DEBUG}")
    logger.info(f"CORS origins: {config.CORS_ORIGINS}")
    logger.info("="*60)
    
    return app


# Create app instance for gunicorn
app = create_app()


if __name__ == '__main__':
    print("\n" + "="*60)
    print("FindFast Job Search API")
    print("="*60)
    print("\nStarting server...")
    print("[*] API URL: http://localhost:5000")
    print("[*] Frontend: http://localhost:4200")
    print("\nPress Ctrl+C to stop the server\n")
    
    app.run(
        debug=True,
        host='127.0.0.1',
        port=5000
    )
