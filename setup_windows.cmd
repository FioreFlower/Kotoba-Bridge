@echo off
setlocal
cd /d "%~dp0"
echo Kotoba Bridge developer-source setup - Windows 10 22H2 x64 / Windows 11 x64.
echo For non-developers, prefer a reviewed installer candidate described in INSTALLATION.md.
py -3.13 --version >nul 2>&1
if errorlevel 1 (
  echo Install official Python 3.13 x64 with Tcl/Tk first. See INSTALLATION.md.
  pause
  exit /b 1
)
if not exist kotoba-core.exe (
  where go >nul 2>&1
  if errorlevel 1 (
    echo Go core is missing. Install Go for a source build, or use the app installer.
    pause
    exit /b 1
  )
  pushd go-core
  go build -o ..\kotoba-core.exe .
  if errorlevel 1 (
    popd
    goto fail
  )
  popd
)
py -3.13 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo Setup complete. Starting offline demo. Tesseract and Japanese data are separate.
.venv\Scripts\python.exe app.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo Setup failed. No certificate or security check has been disabled. See INSTALLATION.md.
pause
exit /b 1
