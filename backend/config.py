"""
Application Configuration
=========================
Environment-based configuration for the Flask API.
"""

import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    JSON_SORT_KEYS = False
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / 'data'
    LOGS_DIR = BASE_DIR / 'logs'
    
    # Data files
    COMBINED_DATA = DATA_DIR / 'data_jobs_combined.json'
    DESCRIPTIONS_DATA = DATA_DIR / 'data_jobs_descriptions.json'
    USER_JOBS_FILE = DATA_DIR / 'user_checked.json'
    
    # Firebase
    FIREBASE_CREDENTIALS = BASE_DIR / 'firebase.config.json'
    FIREBASE_DATABASE_URL = 'https://find-any-55a42-default-rtdb.firebaseio.com'
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:4200').split(',')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    
    # AI Filtering
    CHUNK_SIZE = 100  # Process jobs in chunks
    
    # Scraping
    SCRAPE_TIMEOUT = 300  # 5 minutes
    SCRAPE_POLL_INTERVAL = 2  # 2 seconds


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True


# Configuration dictionary
config: Dict[str, Any] = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env: str = None) -> Config:
    """Get configuration based on environment."""
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
