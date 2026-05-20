@echo off
for /f "tokens=*" %%i in ('python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd().parent)); import config; print(config.BACKEND_PORT)"') do set BACKEND_PORT=%%i
if not defined BACKEND_PORT set BACKEND_PORT=8000
for /f "tokens=*" %%i in ('python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd().parent)); import config; print(config.FRONTEND_PORT)"') do set FRONTEND_PORT=%%i
if not defined FRONTEND_PORT set FRONTEND_PORT=3000
for /f "tokens=*" %%i in ('python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd().parent)); import config; print(config.BACKEND_BIND_HOST)"') do set BACKEND_BIND_HOST=%%i
if not defined BACKEND_BIND_HOST set BACKEND_BIND_HOST=0.0.0.0

npx kill-port %BACKEND_PORT%
npx kill-port %FRONTEND_PORT%
python -B -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd().parent)); import uvicorn; uvicorn.run('web_ui.backend.main:app', host='%BACKEND_BIND_HOST%', port=%BACKEND_PORT%, reload=False)"