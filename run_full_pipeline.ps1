# Full Job Scraping Pipeline PowerShell Script for Windows
# This script runs the complete job scraping workflow

Write-Host ""
Write-Host "============================================================"
Write-Host "FULL JOB SCRAPING PIPELINE"
Write-Host "============================================================"
Write-Host ""

# Get Python executable
$pythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source

if (-not $pythonExe) {
    Write-Host "ERROR: Python not found in PATH" -ForegroundColor Red
    exit 1
}

Write-Host "Using Python: $pythonExe" -ForegroundColor Green
Write-Host ""

# Get the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Run the orchestrator script
& $pythonExe "$scriptDir\run_full_pipeline.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Pipeline failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Pipeline completed successfully!" -ForegroundColor Green
