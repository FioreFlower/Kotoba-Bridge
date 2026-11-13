@echo off
setlocal
cd /d "%~dp0"
echo Kotoba Bridge source prototype setup - Windows 10/11 only, not a verified installer.
py -3.11 --version >nul 2>&1
if errorlevel 1 (
  echo Install official Python 3.11 with Tcl/Tk first. See README.md.
  pause
  exit /b 1
)
if not exist kotoba-core.exe (
  echo Build Go core first: cd go-core then go build -o ..\kotoba-core.exe .
  pause
  exit /b 1
)
py -3.11 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo Setup complete. Starting offline demo. Tesseract and Japanese data are separate.
.venv\Scripts\python.exe app.py
exit /b
:fail
echo Setup failed. No certificate or security check has been disabled. See README.md.
pause
exit /b 1
