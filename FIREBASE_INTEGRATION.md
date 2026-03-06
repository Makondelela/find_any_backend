# Firebase Backend Integration

## Overview

The backend has been migrated from JSON files to Firebase Realtime Database with a complete scraper pipeline.

## Architecture

### Database Structure

```
/jobs
  /{source}  // linkedin, pnet, careerjunction, careers24, networkrecruitment
    /{jobId}
      title: string
      company: string
      location: string
      salary: string
      summary: string
      url: string
      description: string
      experience: string
      scrapedAt: ISO timestamp
      descriptionUpdatedAt: ISO timestamp
      experienceUpdatedAt: ISO timestamp
      updatedAt: ISO timestamp

/sources
  /{sourceId}
    name: string
    lastScraped: ISO timestamp
    jobCount: number
    updatedAt: ISO timestamp

/scrapeJobs
  /{scrapeJobId}
    source: string (comma-separated sources)
    status: 'pending' | 'running' | 'completed' | 'error'
    progress: number (0-100)
    startedAt: ISO timestamp
    completedAt: ISO timestamp
    updatedAt: ISO timestamp
    currentStep: string
    stats:
      totalJobs: number
      newJobs: number
      skippedJobs: number
      descriptionsProcessed: number
      experienceExtracted: number

/users
  /{userId}
    /viewedJobs
      /{source}/{jobId}
        viewedAt: ISO timestamp
```

## Setup Instructions

### 1. Firebase Service Account

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: **find-any-55a42**
3. Go to **Project Settings** > **Service Accounts**
4. Click **Generate New Private Key**
5. Save the JSON file as `firebase.config.json` in the `scrape` folder

### 2. Database Rules

Set these rules in Firebase Realtime Database:

```json
{
  "rules": {
    "jobs": {
      ".read": true,
      ".write": true
    },
    "sources": {
      ".read": true,
      ".write": true
    },
    "scrapeJobs": {
      ".read": true,
      ".write": true
    },
    "users": {
      "$uid": {
        ".read": "$uid === auth.uid || auth != null",
        ".write": "$uid === auth.uid || auth != null"
      }
    }
  }
}
```

### 3. Install Dependencies

Already installed:
- firebase-admin==7.2.0
- flask-cors==6.0.2

## Services

### FirebaseService (`backend/services/firebase_service.py`)

Main service for all Firebase operations:

**Job Operations:**
- `save_job(source, job_id, job_data)` - Save job with deduplication
- `job_exists(source, job_id)` - Check if job exists
- `get_job(source, job_id)` - Get specific job
- `get_all_jobs(source=None)` - Get all jobs or by source
- `update_job_description(source, job_id, description)` - Update description
- `update_job_experience(source, job_id, experience)` - Update experience

**Source Operations:**
- `update_source_metadata(source_id, metadata)` - Update after scraping
- `get_source_metadata(source_id)` - Get source info

**Scrape Job Operations:**
- `create_scrape_job(sources)` - Create new scrape job
- `update_scrape_job(job_id, updates)` - Update status/progress
- `get_scrape_job(job_id)` - Get scrape job status

**User Tracking:**
- `mark_job_viewed(user_id, source, job_id)` - Mark job as viewed
- `get_user_viewed_jobs(user_id)` - Get viewed job IDs

**Statistics:**
- `get_stats()` - Get database statistics

### ScraperPipeline (`backend/services/scraper_pipeline.py`)

Orchestrates the complete scraping pipeline:

1. **Source Scraping** - Runs scrapers for selected sources
2. **Description Extraction** - Extracts full job descriptions
3. **Experience Extraction** - Extracts experience requirements

Features:
- Background processing with threading
- Real-time progress updates in Firebase
- Automatic deduplication (skips existing jobs)
- Statistics tracking (total, new, skipped)
- Error handling and status reporting

## API Endpoints

### POST `/scrape`

Trigger scraping for selected sources.

**Request:**
```json
{
  "sources": ["linkedin", "pnet", "careers24"]
}
```

**Response:**
```json
{
  "status": "success",
  "jobId": "scrapeJobId",
  "message": "Scraping started for 3 source(s)"
}
```

### GET `/api/scrape-status/<jobId>`

Get status of scrape job.

**Response:**
```json
{
  "source": "linkedin,pnet",
  "status": "running",
  "progress": 45,
  "currentStep": "extracting_descriptions",
  "startedAt": "2024-01-15T10:30:00Z",
  "stats": {
    "totalJobs": 150,
    "newJobs": 50,
    "skippedJobs": 100,
    "descriptionsProcessed": 75,
    "experienceExtracted": 0
  }
}
```

### GET `/api/jobs`

Get jobs with filtering.

**Query Parameters:**
- `keyword` - Filter by keyword in title/company/summary
- `location` - Filter by location
- `source` - Filter by source (linkedin, pnet, etc.)
- `sort` - Sort by 'recent', 'company', 'title'
- `view_status` - Filter by 'all', 'viewed', 'not_viewed'
- `username` - Required for view status filtering

**Response:**
```json
{
  "success": true,
  "jobs": [...],
  "total": 150
}
```

### GET `/api/stats`

Get job statistics.

**Response:**
```json
{
  "total_jobs": 500,
  "jobs_by_source": {
    "linkedin": 200,
    "pnet": 150,
    "careers24": 100,
    "careerjunction": 50
  },
  "combined_at": "2024-01-15T10:30:00Z"
}
```

### POST `/api/track-job`

Track a job view.

**Request:**
```json
{
  "username": "user123",
  "job_id": "job456",
  "source": "linkedin"
}
```

### GET `/api/user-history/<username>`

Get user's viewed jobs.

**Response:**
```json
{
  "success": true,
  "viewed_jobs": ["job1", "job2", "job3"],
  "total": 3
}
```

## Scraper Pipeline Flow

1. **User Action**: User clicks Refresh button in UI
2. **Source Selection**: Modal opens with available sources
3. **API Call**: Frontend calls `POST /scrape` with selected sources
4. **Job Creation**: Backend creates scrape job in `/scrapeJobs`
5. **Pipeline Start**: Background thread starts pipeline

### Pipeline Steps:

**Step 1: Source Scraping (Progress: 5-30%)**
- For each source:
  - Run scraper (main.py with --source flag)
  - Load scraped jobs from JSON output
  - Check if job exists in Firebase
  - If new: Save to `/jobs/{source}/{jobId}`
  - If exists: Skip (deduplication)
  - Update stats (totalJobs, newJobs, skippedJobs)
  - Update source metadata

**Step 2: Description Extraction (Progress: 40-60%)**
- Run job_description_pipeline.py
- Extract full descriptions from job URLs
- Update existing jobs with descriptions
- Skip if description already exists
- Update stats (descriptionsProcessed)

**Step 3: Experience Extraction (Progress: 70-90%)**
- Run extract_experience.py
- Parse experience requirements from descriptions
- Update jobs with experience field
- Skip if experience already exists
- Update stats (experienceExtracted)

**Step 4: Completion (Progress: 100%)**
- Update scrape job status to 'completed'
- Set completedAt timestamp
- Frontend monitors via polling

## Frontend Integration

The frontend monitors scrape jobs:

```typescript
// Start scrape
const response = await this.jobService.triggerScrape(sources);
const jobId = response.jobId;

// Monitor progress
this.monitorScrapeJob(jobId);

// Polling function
private monitorScrapeJob(jobId: string) {
  const interval = setInterval(async () => {
    const job = await this.firebaseDb.getScrapeJob(jobId);
    
    if (job.status === 'completed' || job.status === 'error') {
      clearInterval(interval);
      this.loadJobs(); // Refresh job list
    }
    
    this.updateProgress(job.progress);
  }, 3000);
}
```

## Deduplication Strategy

Jobs are deduplicated at multiple levels:

1. **Source-level**: Jobs are organized by source
2. **ID-level**: Each job has unique ID within its source
3. **Existence check**: Before saving, check `job_exists(source, job_id)`
4. **Field updates**: Descriptions and experience only updated if missing

## Error Handling

- **Firebase initialization errors**: Logged and raised
- **Scraper errors**: Logged, pipeline continues to next source
- **Timeout errors**: Scrapers have 5-minute timeout
- **Status tracking**: All errors recorded in scrape job

## Testing

Test Firebase connection:
```bash
cd c:\Users\Wanga\Desktop\Mako\Work\scrape
.\.venv\Scripts\activate
python -c "from backend.services.firebase_service import FirebaseService; from backend.config import Config; fs = FirebaseService(Config()); print('Firebase connected')"
```

Test scraper pipeline:
```bash
# Test scraping
curl -X POST http://localhost:5000/scrape -H "Content-Type: application/json" -d "{\"sources\": [\"careers24\"]}"

# Check status
curl http://localhost:5000/api/scrape-status/{jobId}

# Get jobs
curl http://localhost:5000/api/jobs?source=careers24
```

## Migration Notes

### What Changed:

1. **Data Storage**: JSON files → Firebase Realtime Database
2. **Job Retrieval**: File reads → Firebase queries
3. **Job Saving**: File writes → Firebase sets/updates
4. **Deduplication**: In-memory → Firebase existence checks
5. **User Tracking**: user_checked.json → /users/{userId}/viewedJobs
6. **Statistics**: File parsing → Firebase aggregation

### What Stayed the Same:

1. **Scrapers**: Still run as subprocesses (main.py)
2. **Description Extraction**: Still uses job_description_pipeline.py
3. **Experience Extraction**: Still uses extract_experience.py
4. **Flask API**: Same endpoint structure
5. **Frontend**: Same component interfaces

## Next Steps

1. ✅ Create firebase.config.json with service account credentials
2. Test Firebase connection
3. Test scrape pipeline with one source
4. Verify deduplication works
5. Test frontend integration
6. Monitor scrape job progress
7. Verify job filtering and sorting
8. Test user tracking

## Troubleshooting

### "Firebase config not found"
- Create `firebase.config.json` from template
- Add service account credentials

### "Permission denied"
- Check Firebase Database Rules
- Verify service account has correct permissions

### "Scraper timeout"
- Increase SCRAPE_TIMEOUT in config.py
- Check network connectivity

### "Jobs not showing"
- Check Firebase console for data
- Verify GET /api/jobs returns data
- Check browser console for errors
