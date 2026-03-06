# FindFast Job Search - Backend API

A well-structured Flask REST API backend for the FindFast job search application.

## 🏗️ Project Structure

```
scrape/
├── backend/                    # Backend application code
│   ├── api/                   # API route blueprints
│   │   ├── jobs.py           # Job-related endpoints
│   │   ├── users.py          # User tracking endpoints
│   │   ├── scrape.py         # Scraping endpoints
│   │   └── health.py         # Health check endpoints
│   ├── models/               # Data models and schemas
│   ├── services/             # Business logic layer
│   │   ├── job_service.py    # Job operations
│   │   ├── user_service.py   # User operations
│   │   ├── ai_filter_service.py  # AI filtering
│   │   └── scrape_service.py # Scraping operations
│   ├── utils/                # Helper functions
│   ├── config.py             # Configuration management
│   ├── ai_filtering.py       # AI filtering logic
│   ├── main.py               # Scraping orchestration
│   └── __init__.py
├── scrapers/                  # Individual web scrapers
│   ├── career24_scraper.py
│   ├── careerjunction_scraper.py
│   ├── linkedIn_scraper.py
│   ├── network_recruit_scraper.py
│   └── pnet_scraper.py
├── data/                      # Data storage
│   ├── data_jobs_combined.json
│   ├── data_jobs_descriptions.json
│   └── user_checked.json
├── tests/                     # Unit tests
├── logs/                      # Application logs
├── docs/                      # Documentation
├── .venv/                     # Virtual environment
├── run.py                     # Application entry point
├── requirements.txt           # Python dependencies
└── .env.example              # Environment variables template

```

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

1. **Create virtual environment:**
   ```bash
   python -m venv .venv
   ```

2. **Activate virtual environment:**
   - Windows PowerShell:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - Windows CMD:
     ```cmd
     .venv\Scripts\activate.bat
     ```
   - Linux/Mac:
     ```bash
     source .venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

### Running the Application

**Development Server:**
```bash
python run.py
```

The API will be available at: `http://localhost:5000`

**Production (using Gunicorn):**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "run:create_app()"
```

## 📚 API Endpoints

### Jobs
- `GET /api/jobs` - Get jobs with filters
- `GET /api/stats` - Get job statistics
- `POST /api/ai-filter` - AI-powered job filtering
- `POST /api/ai-filter-chunked` - Chunked AI filtering

### Users
- `POST /api/track-job` - Track viewed job
- `GET /api/user-history/<username>` - Get user's viewed jobs

### Scraping
- `POST /scrape` - Trigger job scraping
- `GET /api/scrape-status` - Get scraping status

### Health
- `GET /health` - Health check

## ⚙️ Configuration

Configuration is managed through environment variables and the `backend/config.py` file.

**Environment Variables (.env):**
```env
FLASK_ENV=development          # development, production, testing
SECRET_KEY=your-secret-key
CORS_ORIGINS=http://localhost:4200
LOG_LEVEL=INFO
```

## 🧪 Testing

Run tests:
```bash
python -m pytest tests/
```

## 📦 Dependencies

### Core
- Flask 3.0.0 - Web framework
- Flask-CORS 4.0.0 - CORS support

### Scraping
- requests 2.31.0 - HTTP client
- beautifulsoup4 4.12.2 - HTML parsing
- playwright 1.58.0 - Browser automation

### AI
- google-genai 0.1.0 - AI filtering

## 🏛️ Architecture

### Layered Architecture
```
API Layer (Flask Blueprints)
    ↓
Service Layer (Business Logic)
    ↓
Data Layer (JSON files)
```

### Design Patterns
- **Factory Pattern**: Application creation
- **Blueprint Pattern**: Route organization
- **Service Layer Pattern**: Business logic separation
- **Repository Pattern**: Data access abstraction

## 🔒 Security

- CORS enabled for frontend communication
- Input validation on all endpoints
- Secret key management via environment variables
- Debug mode disabled in production

## 📝 Development

### Adding a New Endpoint

1. Create route in appropriate blueprint (`backend/api/`)
2. Add business logic in service (`backend/services/`)
3. Update models if needed (`backend/models/`)
4. Add tests (`tests/`)

### Code Style
- Follow PEP 8
- Use type hints
- Document functions with docstrings

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Write tests
4. Submit pull request

## 📄 License

Proprietary - All rights reserved

## 👥 Authors

- Development Team

## 🔗 Related Projects

- **Frontend**: Angular application in `../find.any/`
