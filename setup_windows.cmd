@echo off
setlocal
cd /d "%~dp0"
echo Kotoba Bridge developer-source setup - Windows 10 22H2 x64 / Windows 11 x64.
echo For non-developers, prefer a reviewed installer candidate described in INSTALLATION.md.
py -3.14 -c "import sys,struct,tkinter; assert sys.version_info[:3]>=(3,14,10); assert struct.calcsize('P')==8" >nul 2>&1
if errorlevel 1 (
  echo Install official Python 3.14.10+ x64 with Tcl/Tk first. See INSTALLATION.md.
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
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -c "import sys; assert sys.version_info[:2]==(3,14)" >nul 2>&1
  if errorlevel 1 (
    echo Existing .venv is a different Python series. Rename it to .venv-backup, then run setup again.
    echo User settings and study data are not inside .venv. No files were deleted.
    pause
    exit /b 1
  )
)
py -3.14 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-lock.txt
if errorlevel 1 goto fail
echo Setup complete. Starting offline demo. Tesseract and Japanese data are separate.
.venv\Scripts\python.exe app.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo Setup failed. No certificate or security check has been disabled. See INSTALLATION.md.
pause
exit /b 1
