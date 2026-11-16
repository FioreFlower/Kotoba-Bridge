@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe -c "import sys; assert sys.version_info[:2]==(3,14) and sys.version_info[:3]>=(3,14,10)" >nul 2>&1
if errorlevel 1 (
  echo Run setup_windows.cmd with official Python 3.14.10+ x64 first. Existing environments are not deleted.
  pause
  exit /b 1
)
.venv\Scripts\python.exe app.py
if errorlevel 1 pause
