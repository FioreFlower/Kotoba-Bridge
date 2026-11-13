# Windows-only release recipe; NOT executed or certified on Windows in this task.
param([Parameter(Mandatory=$true)][string]$TesseractRoot)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path "$TesseractRoot\tesseract.exe")) { throw 'Missing OCR executable.' }
if (-not (Test-Path "$TesseractRoot\tessdata\jpn.traineddata")) { throw 'Missing Japanese model.' }
if (-not (Test-Path "$TesseractRoot\LICENSE")) { throw 'Supply audited OCR distribution with LICENSE and dependency notices.' }
Push-Location go-core
go test ./...
if ($LASTEXITCODE -ne 0) { throw 'Go tests failed.' }
$env:GOOS='windows'; $env:GOARCH='amd64'; $env:CGO_ENABLED='0'
go build -buildvcs=false -trimpath -o ..\kotoba-core.exe .
if ($LASTEXITCODE -ne 0) { throw 'Go build failed.' }
Pop-Location
py -3.11 -m venv .build-venv
if ($LASTEXITCODE -ne 0) { throw 'Python venv failed.' }
& .build-venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller==6.11.1
if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed.' }
& .build-venv\Scripts\python.exe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
& .build-venv\Scripts\python.exe -m PyInstaller --clean --noconfirm --onedir --windowed --name KotobaBridge app.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
Copy-Item kotoba-core.exe dist\KotobaBridge
New-Item -ItemType Directory -Force dist\KotobaBridge\ocr | Out-Null
Copy-Item "$TesseractRoot\*" dist\KotobaBridge\ocr -Recurse -Force
Copy-Item README.md,DESIGN.md,COMPATIBILITY.md,LICENSE dist\KotobaBridge
Write-Host 'Unsigned build only. Audit bundled DLL/model licenses, run Windows tests, then sign app and installer.'
Write-Host 'Compile packaging\installer.iss with Inno Setup after validation.'
