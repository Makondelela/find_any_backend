#!/usr/bin/env python3
"""
Full Job Scraping Pipeline Orchestrator
========================================
Runs the complete job scraping workflow:
1. Start LinkedIn scraper (Node.js)
2. Start Flask app
3. Trigger scraping via API
4. Wait for scraping to complete
5. Combine jobs from all sources
6. Scrape job descriptions
7. Extract experience requirements

Usage:
    python run_full_pipeline.py
"""

import os
import sys
import json
import time
import subprocess
import requests
import signal
from pathlib import Path
from datetime import datetime

# Configuration
LINKEDIN_SCRAPER_DIR = Path(__file__).parent.parent / "linked_in_scraper"
FLASK_APP_PATH = Path(__file__).parent / "app.py"
COMBINE_SCRIPT = Path(__file__).parent / "combine_jobs.py"
DESCRIPTION_SCRIPT = Path(__file__).parent / "backend" / "job_description_pipeline.py"
EXPERIENCE_SCRIPT = Path(__file__).parent / "backend" / "extract_experience.py"

LINKEDIN_SCRAPER_PORT = 3000
FLASK_PORT = 5000
FLASK_URL = f"http://127.0.0.1:{FLASK_PORT}"
SCRAPE_ENDPOINT = f"{FLASK_URL}/api/scrape"
SCRAPE_STATUS_ENDPOINT = f"{FLASK_URL}/api/scrape-status"

# Process tracking
processes = []
start_time = datetime.now()

def log(message, level="INFO"):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = f"[{timestamp}] [{level}]"
    print(f"{prefix} {message}")

def error(message):
    """Log error"""
    log(message, "ERROR")

def success(message):
    """Log success"""
    log(message, "SUCCESS")

def cleanup():
    """Terminate all background processes"""
    log("Cleaning up processes...")
    for proc in processes:
        try:
            if proc.poll() is None:  # Process still running
                proc.terminate()
                time.sleep(1)
                if proc.poll() is None:
                    proc.kill()
                log(f"Terminated process {proc.pid}")
        except Exception as e:
            error(f"Error terminating process: {e}")

def signal_handler(sig, frame):
    """Handle Ctrl+C"""
    log("\nInterrupt received, cleaning up...")
    cleanup()
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

def check_npm_available():
    """Check if npm is available in PATH"""
    try:
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False

def start_linkedin_scraper():
    """Start Node.js LinkedIn scraper"""
    log("Starting LinkedIn scraper (Node.js)...")
    
    if not LINKEDIN_SCRAPER_DIR.exists():
        error(f"LinkedIn scraper directory not found: {LINKEDIN_SCRAPER_DIR}")
        return False
    
    # Check if npm is available
    if not check_npm_available():
        error("npm is not installed or not in PATH")
        error("To install Node.js and npm:")
        error("  Windows: Download from https://nodejs.org/")
        error("  Or use: choco install nodejs (if using Chocolatey)")
        error("")
        log("Continuing pipeline without LinkedIn scraper...")
        return True  # Return True to continue without LinkedIn scraper
    
    try:
        # Check if node_modules exists, if not run npm install
        if not (LINKEDIN_SCRAPER_DIR / "node_modules").exists():
            log("Installing Node dependencies...")
            result = subprocess.run(
                ["npm", "install"],
                cwd=LINKEDIN_SCRAPER_DIR,
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode != 0:
                error(f"npm install failed: {result.stderr}")
                return False
            log("Node dependencies installed")
        
        # Start the scraper
        proc = subprocess.Popen(
            ["npm", "start"],
            cwd=LINKEDIN_SCRAPER_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        processes.append(proc)
        time.sleep(2)  # Give it time to start
        
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            error(f"LinkedIn scraper failed to start: {stderr}")
            return False
        
        success(f"LinkedIn scraper started (PID: {proc.pid})")
        return True
    except Exception as e:
        error(f"Failed to start LinkedIn scraper: {e}")
        return False

def start_flask_app():
    """Start Flask application"""
    log("Starting Flask app...")
    
    if not FLASK_APP_PATH.exists():
        error(f"Flask app not found: {FLASK_APP_PATH}")
        return False
    
    try:
        # Get Python executable
        python_exe = sys.executable
        
        proc = subprocess.Popen(
            [python_exe, str(FLASK_APP_PATH)],
            cwd=FLASK_APP_PATH.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        processes.append(proc)
        time.sleep(3)  # Give Flask time to start
        
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            error(f"Flask app failed to start: {stderr}")
            return False
        
        success(f"Flask app started (PID: {proc.pid})")
        return True
    except Exception as e:
        error(f"Failed to start Flask app: {e}")
        return False

def wait_for_flask():
    """Wait for Flask app to be ready"""
    log("Waiting for Flask app to be ready...")
    max_retries = 60
    for i in range(max_retries):
        try:
            response = requests.get(f"{FLASK_URL}/api/admin-email", timeout=10)
            if response.status_code == 200:
                success("Flask app is ready")
                return True
        except requests.RequestException:
            pass
        
        if i % 10 == 0:
            log(f"Still waiting... ({i}/{max_retries})")
        time.sleep(1)
    
    error("Flask app did not respond in time")
    return False

def trigger_scraping():
    """Trigger scraping via Flask API"""
    log("Triggering scraping...")
    
    try:
        response = requests.post(SCRAPE_ENDPOINT, timeout=30)
        data = response.json()
        
        if data.get('success') or data.get('status') == 'success':
            success("Scraping triggered successfully")
            return True
        else:
            error(f"Scraping failed: {data}")
            return False
    except Exception as e:
        error(f"Failed to trigger scraping: {e}")
        return False

def wait_for_scraping_complete():
    """Poll scraping status until complete with frequent updates showing progress"""
    log("Waiting for scraping to complete...")
    max_wait = 3600  # 1 hour timeout
    poll_interval = 2  # Check every 2 seconds for more frequent updates
    elapsed = 0
    consecutive_errors = 0
    max_consecutive_errors = 5
    last_progress = -1
    last_message = ""
    start_wait_time = datetime.now()
    
    while elapsed < max_wait:
        try:
            # Use longer timeout for the status check
            response = requests.get(SCRAPE_STATUS_ENDPOINT, timeout=15)
            response.raise_for_status()
            status_data = response.json()
            
            running = status_data.get('running', False)
            message = status_data.get('message', 'No message')
            progress = status_data.get('progress', 0)
            
            consecutive_errors = 0  # Reset error counter on success
            
            # Calculate elapsed wait time
            elapsed_wait = (datetime.now() - start_wait_time).total_seconds()
            
            # Only log if progress or message changed (to reduce spam but show frequent updates)
            if progress != last_progress or message != last_message:
                # Show detailed progress with elapsed time
                log(f"[{int(elapsed_wait)}s] {message} (Progress: {progress}%)")
                last_progress = progress
                last_message = message
            elif elapsed_wait % 5 == 0:
                # Every 5 seconds, show progress even if it hasn't changed
                log(f"[{int(elapsed_wait)}s] Still scraping... (Progress: {progress}%)")
            
            if not running:
                success("Scraping completed!")
                return True
            
            time.sleep(poll_interval)
            elapsed += poll_interval
            
        except requests.exceptions.Timeout:
            consecutive_errors += 1
            elapsed_wait = (datetime.now() - start_wait_time).total_seconds()
            log(f"[{int(elapsed_wait)}s] Status check timed out (attempt {consecutive_errors}/{max_consecutive_errors})... retrying")
            if consecutive_errors >= max_consecutive_errors:
                error(f"Too many consecutive timeouts. Flask app may be unresponsive.")
                return False
            time.sleep(poll_interval)
            elapsed += poll_interval
            
        except requests.exceptions.ConnectionError as e:
            error(f"Connection error: {e}")
            return False
            
        except Exception as e:
            consecutive_errors += 1
            elapsed_wait = (datetime.now() - start_wait_time).total_seconds()
            log(f"[{int(elapsed_wait)}s] Error checking scraping status (attempt {consecutive_errors}/{max_consecutive_errors}): {e}")
            if consecutive_errors >= max_consecutive_errors:
                error(f"Too many errors checking status")
                return False
            time.sleep(poll_interval)
            elapsed += poll_interval
    
    error("Scraping timed out after 1 hour")
    return False

def run_python_script(script_path, script_name):
    """Run a Python script"""
    log(f"Running {script_name}...")
    
    if not script_path.exists():
        error(f"{script_name} not found: {script_path}")
        return False
    
    try:
        python_exe = sys.executable
        result = subprocess.run(
            [python_exe, str(script_path)],
            cwd=script_path.parent,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        if result.returncode == 0:
            success(f"{script_name} completed successfully")
            return True
        else:
            error(f"{script_name} failed with exit code {result.returncode}")
            return False
    except subprocess.TimeoutExpired:
        error(f"{script_name} timed out after 1 hour")
        return False
    except Exception as e:
        error(f"Failed to run {script_name}: {e}")
        return False

def push_to_git():
    """Push changes to git repository"""
    log("Pushing changes to git...")
    
    repo_path = FLASK_APP_PATH.parent
    
    try:
        # Git add
        result = subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            error(f"git add failed: {result.stderr}")
            return False
        log("git add completed")
        
        # Git commit
        result = subprocess.run(
            ["git", "commit", "-m", "updates"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            # Commit might fail if there's nothing to commit - that's ok
            if "nothing to commit" not in result.stderr.lower():
                error(f"git commit failed: {result.stderr}")
                return False
            log("Nothing to commit (no changes)")
        else:
            log("git commit completed")
        
        # Git push
        result = subprocess.run(
            ["git", "push"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            error(f"git push failed: {result.stderr}")
            return False
        
        success("Changes pushed to git repository")
        return True
    except Exception as e:
        error(f"Failed to push to git: {e}")
        return False

def main():
    """Main orchestration function - follows manual workflow with proper waits"""
    print("\n" + "="*70)
    print("FULL JOB SCRAPING PIPELINE ORCHESTRATOR")
    print("="*70 + "\n")
    
    try:
        # Step 1: Start LinkedIn scraper (npm start)
        log("Step 1: Starting LinkedIn scraper...")
        start_linkedin_scraper()  # Try to start, but continue if npm not available
        time.sleep(1)
        
        # Step 2: Start Flask app and wait for it to be ready
        log("Step 2: Starting Flask app...")
        if not start_flask_app():
            error("Failed to start Flask app. Exiting.")
            cleanup()
            sys.exit(1)
        
        if not wait_for_flask():
            error("Flask app did not respond. Exiting.")
            cleanup()
            sys.exit(1)
        time.sleep(1)
        
        # Step 3: Trigger scraping and wait for completion
        log("Step 3: Triggering scraping...")
        if not trigger_scraping():
            error("Failed to trigger scraping. Exiting.")
            cleanup()
            sys.exit(1)
        
        log("Step 4: Waiting for scraping to complete...")
        if not wait_for_scraping_complete():
            error("Scraping did not complete in time. Exiting.")
            cleanup()
            sys.exit(1)
        
        success("Scraping completed!")
        time.sleep(1)
        
        # Clean up Flask and Node apps
        log("Cleaning up background processes...")
        cleanup()
        time.sleep(2)
        
        # Step 5: Combine jobs and wait for completion
        log("Step 5: Combining jobs...")
        if not run_python_script(COMBINE_SCRIPT, "combine_jobs.py"):
            error("Failed to combine jobs. Exiting.")
            sys.exit(1)
        time.sleep(1)
        
        # Step 6: Scrape job descriptions and wait for completion
        log("Step 6: Scraping job descriptions...")
        if not run_python_script(DESCRIPTION_SCRIPT, "job_description_pipeline.py"):
            error("Failed to scrape job descriptions. Exiting.")
            sys.exit(1)
        time.sleep(1)
        
        # Step 7: Extract experience and wait for completion
        log("Step 7: Extracting experience requirements...")
        if not run_python_script(EXPERIENCE_SCRIPT, "extract_experience.py"):
            error("Failed to extract experience. Exiting.")
            sys.exit(1)
        time.sleep(1)
        
        # Step 8: Push to git and wait for completion
        log("Step 8: Pushing to git...")
        if not push_to_git():
            error("Failed to push to git. Exiting.")
            sys.exit(1)
        
        # Success!
        elapsed_time = datetime.now() - start_time
        print("\n" + "="*70)
        print("PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*70)
        print(f"Total time: {elapsed_time}")
        print("="*70 + "\n")
        
    except KeyboardInterrupt:
        log("\nPipeline interrupted by user")
        cleanup()
        sys.exit(1)
    except Exception as e:
        error(f"Unexpected error in pipeline: {e}")
        cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()
