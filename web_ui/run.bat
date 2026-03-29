@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo Detecting ports from config.py...
echo ==========================================

:: Get Backend Port from config.py
for /f "tokens=*" %%i in ('python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd().parent)); import config; print(config.BACKEND_PORT)"') do set BACKEND_PORT=%%i
if not defined BACKEND_PORT set BACKEND_PORT=8000

:: Get Frontend Port from config.py
for /f "tokens=*" %%i in ('python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd().parent)); import config; print(config.FRONTEND_PORT)"') do set FRONTEND_PORT=%%i
if not defined FRONTEND_PORT set FRONTEND_PORT=3000

echo Backend Port: %BACKEND_PORT%
echo Frontend Port: %FRONTEND_PORT%
echo ==========================================
echo Killing existing backend and frontend processes...
echo ==========================================

:: Kill backend on dynamic Port
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :%BACKEND_PORT%') DO (
    echo Killing Backend PID: %%P
    taskkill /F /PID %%P 2>nul
)

:: Kill frontend on dynamic Port
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :%FRONTEND_PORT%') DO (
    echo Killing Frontend PID: %%P
    taskkill /F /PID %%P 2>nul
)

echo.
echo ==========================================
echo Starting AI Video Factory Web UI...
echo ==========================================
python start.py
