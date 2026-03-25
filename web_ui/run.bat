@echo off
echo ==========================================
echo Killing existing backend and frontend processes...
echo ==========================================

:: Kill backend on Port 8000
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :8000') DO (
    echo Killing Backend PID: %%P
    taskkill /F /PID %%P 2>nul
)

:: Kill frontend on Port 3000
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :3000') DO (
    echo Killing Frontend PID: %%P
    taskkill /F /PID %%P 2>nul
)

echo.
echo ==========================================
echo Starting AI Video Factory Web UI...
echo ==========================================
python start.py
