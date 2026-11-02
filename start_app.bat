@echo off
chcp 65001 >nul
echo ========================================================
echo   Starting DDS One-Click Surveillance Application
echo   - Backend API: http://127.0.0.1:8000
echo   - Frontend Web UI: http://127.0.0.1:3000
echo ========================================================

start "DDS Backend (Port 8000)" cmd /k "cd /d "%~dp0backend" && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
start "DDS Frontend (Port 3000)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 3 >nul
start http://127.0.0.1:3000
