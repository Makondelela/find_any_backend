# Full Job Scraping Pipeline

This orchestrates the complete job scraping workflow from start to finish.

## What It Does

The pipeline automatically executes these steps in order:

1. **Start LinkedIn Scraper** (Node.js) - Begins scraping LinkedIn jobs
2. **Start Flask App** - Launches the backend API server
3. **Trigger Scraping** - Initiates job scraping through the Flask API
4. **Wait for Scraping** - Polls the API until all scraping is complete
5. **Stop Services** - Terminates Node.js and Flask apps
6. **Combine Jobs** - Merges job data from all sources into one file
7. **Scrape Descriptions** - Fetches full job descriptions from each job URL
8. **Extract Experience** - Analyzes descriptions and extracts experience requirements
9. **Push to Git** - Commits and pushes all changes to the git repository

## How to Run

### Option 1: Windows Batch File (Easiest)
Double-click the batch file:
```
run_full_pipeline.bat
```

### Option 2: PowerShell
```powershell
.\run_full_pipeline.ps1
```

### Option 3: Python (Platform Independent)
```bash
python run_full_pipeline.py
```

## Requirements

- **Python 3.8+** with packages from `requirements.txt`
- **Node.js 14+** with packages from `linked_in_scraper/package.json`
- **.env file** configured with Firebase and API credentials

## Process Flow

```
┌─────────────────────────────┐
│ Start LinkedIn Scraper      │ (npm start)
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ Start Flask App             │ (app.py)
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ Trigger Scraping            │ (POST /api/scrape)
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ Wait for Completion         │ (Poll /api/scrape-status)
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ Stop Services               │ (Kill Node & Flask)
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ Combine Jobs                │ (combine_jobs.py)
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ Scrape Descriptions         │ (job_description_pipeline.py)
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ Extract Experience          │ (extract_experience.py)
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ Push to Git                 │ (git add . && git commit && git push)
└──────────────┬──────────────┘
               │
        ✓ COMPLETE
```

## Output Files

After completion, the following files are generated in `data/`:

- **data_jobs_combined.json** - All jobs from all sources combined and deduplicated
- **data_jobs_descriptions.json** - Job listings with full descriptions
- **data_jobs_experience.json** - Jobs with extracted experience requirements

## Troubleshooting

### "Flask app did not respond"
- Check that port 5000 is not in use
- Verify .env file exists with required variables
- Check that Firebase is properly configured

### "LinkedIn scraper failed to start"
- Run `npm install` in `linked_in_scraper/` directory
- Check that Node.js is installed and in PATH
- Verify package.json dependencies are correct

### "Scraping timed out"
- The default timeout is 1 hour
- This is normal for large datasets
- Check the Flask app logs for errors

### Process interrupted
- Press Ctrl+C to stop
- The script will clean up background processes
- All generated data up to that point is saved

## Monitoring

While running, the script displays:
- Timestamp of each step
- Current process status
- Progress percentage during scraping
- Detailed logs from each Python script

## Logs

To see detailed logs, check:
- Flask app output: shown in real-time during step 2-5
- Python scripts: output shown as each script runs
- Status messages: displayed throughout the pipeline

## Manual Steps (If Not Using Orchestrator)

If you need to run steps manually:

```bash
# Terminal 1: Start LinkedIn scraper
cd linked_in_scraper
npm start

# Terminal 2: Start Flask app
cd find_any_backend
python app.py

# Then trigger via browser:
# http://localhost:5000
# Click "Update Job Listings"

# After scraping completes, run in order:
python combine_jobs.py
python backend/job_description_pipeline.py
python backend/extract_experience.py
```

## Time Estimates

Typical execution times:
- LinkedIn scraping: 5-30 minutes (depending on number of jobs)
- Job descriptions: 10-60 minutes (depends on number of jobs)
- Experience extraction: 1-5 minutes
- Git push: 1-5 minutes (depends on internet speed and repo size)
- **Total: 20-100 minutes**

## Notes

- The pipeline cleans up Node.js and Flask processes after scraping completes
- If you need to monitor the scraping, keep the Flask app running manually
- All timestamps are in UTC
- Original data files are preserved; combined files are generated in `data/`
