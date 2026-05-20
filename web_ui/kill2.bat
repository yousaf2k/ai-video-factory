@echo off
for /f "tokens=*" %%i in ('python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd().parent)); import config; print(config.FRONTEND_PORT)"') do set FRONTEND_PORT=%%i
if not defined FRONTEND_PORT set FRONTEND_PORT=3000

npx kill-port %FRONTEND_PORT%