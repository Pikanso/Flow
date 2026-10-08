@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe python -m venv .venv
.venv\Scripts\python.exe -c "import faster_whisper" >nul 2>nul
if errorlevel 1 .venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo Installation failed. Please check your network and Python installation.
  pause
  exit /b 1
)
.venv\Scripts\python.exe launch.py
pause
