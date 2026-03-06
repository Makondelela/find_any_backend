# AI Filtering Feature Implementation

## Overview
Added intelligent AI-powered job filtering capabilities to the job board using Claude AI API.

## Features Implemented

### 1. **AI Filter Backend** (`ai_filtering.py`)
- `filter_jobs_by_criteria()`: Filters jobs based on natural language user criteria
- `get_ai_job_insights()`: Provides AI analysis of individual jobs
- Uses Anthropic Claude 3.5 Sonnet model
- Intelligent parsing of job listings based on user requests like:
  - "2 years experience"
  - "Remote positions"
  - "Entry level jobs"
  - "Python developers"
  - etc.

### 2. **Flask API Endpoint** (`app.py`)
- `POST /api/ai-filter`: Accepts user criteria and returns filtered jobs
  - Request: `{ "criteria": "user's search query" }`
  - Response: `{ "filtered_jobs": [...], "explanation": "why these were selected", "total_filtered": count }`

### 3. **Frontend UI** (`templates/index.html`)
- **Smart Filter Section** with:
  - Beautiful gradient background with gold accents
  - Input field for natural language criteria
  - "Search with AI" button
  - Result explanation display
  - Clear button to reset filter

### 4. **JavaScript Functionality** (`static/js/app.js`)
- `filterJobsWithAI()`: Handles AI filtering request
- `renderAIFilteredJobs()`: Displays filtered results
- `clearAIFilter()`: Resets to show all jobs
- Event listeners for:
  - Click on "Search with AI" button
  - Enter key to submit query
  - Clear button functionality

### 5. **Styling** (`static/css/styles.css`)
- Modern gradient design (#f5f3ff to #faf9ff)
- Gold accent color (#c09023) matching brand
- Responsive layout
- Light and dark mode support
- Smooth transitions and hover effects

## API Key
- Provider: Anthropic
- Model: Claude 3.5 Sonnet
- API Key: Configured in `ai_filtering.py`

## Dependencies
- `anthropic==0.84.0` (installed)
- Flask (existing)

## How It Works

1. User enters natural language criteria (e.g., "2 years experience")
2. Frontend sends request to `/api/ai-filter`
3. Backend uses Claude AI to analyze all jobs
4. AI filters based on understanding of job descriptions
5. Results are displayed with explanation
6. User can click "Clear" to see all jobs again

## Example Usage
- Input: "2 years of Python experience, remote work"
- Output: Jobs that match these criteria with explanation like "5 matching jobs: Senior Python developers with remote opportunities"

## Testing
To test the AI filter:
1. Start the Flask app: `python app.py`
2. Visit: http://localhost:5000
3. Scroll to "Smart Filter with AI" section
4. Enter a search criteria (e.g., "Data Engineer with 3 years experience")
5. Click "Search with AI"
6. View filtered results
