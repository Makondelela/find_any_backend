@echo off
REM Full Job Scraping Pipeline Batch Script for Windows
REM This script runs the complete job scraping workflow

echo.
echo ============================================================
echo FULL JOB SCRAPING PIPELINE
echo ============================================================
echo.

REM Get Python executable
for /f "tokens=*" %%i in ('where python.exe') do set PYTHON_EXE=%%i

if "%PYTHON_EXE%"=="" (
    echo ERROR: Python not found in PATH
    exit /b 1
)

echo Using Python: %PYTHON_EXE%
echo.

REM Run the orchestrator script
%PYTHON_EXE% run_full_pipeline.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Pipeline failed!
    exit /b 1
)

echo.
echo Pipeline completed successfully!
pause
