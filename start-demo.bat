@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
    echo Python was not found. Install Python for Windows and add it to PATH.
    pause
    exit /b 1
)
python -m backend.scripts.start_local_demo
if errorlevel 1 (
    pause
    exit /b 1
)
