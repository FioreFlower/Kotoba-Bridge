# Builds an unsigned app installer candidate. No paid API calls or automatic releases.
param(
    [string]$TesseractRoot = '.ocr-bundle',
    [string]$PythonExe = 'python',
    [switch]$SkipInstaller
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
if ($env:OS -ne 'Windows_NT') { throw 'Run this build on Windows x64.' }
if (-not [Environment]::Is64BitProcess) { throw 'Use a 64-bit PowerShell and Python installation.' }
& $PythonExe -c "import struct,sys; assert struct.calcsize('P')==8; assert sys.version_info[:2]==(3,14) and sys.version_info[:3]>=(3,14,10); import tkinter; print('Python',sys.version,'Tcl/Tk',tkinter.TclVersion,tkinter.TkVersion)"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.14.10+ x64 (3.14 series) with Tcl/Tk is required.' }
if (-not $TesseractRoot) { throw 'An audited OCR source bundle is required.' }
if ($TesseractRoot) {
    $TesseractRoot = (Resolve-Path $TesseractRoot).Path
    foreach ($required in @('tesseract.exe','tessdata\jpn.traineddata','REDISTRIBUTION_REVIEW.md')) {
        if (-not (Test-Path (Join-Path $TesseractRoot $required))) { throw "Audited OCR input is missing $required" }
    }
    # The review must include every DLL/model's source, version, checksum and notices.
    # Its existence is a release gate, not a substitute for human license review.
}
$oldGOOS = $env:GOOS; $oldGOARCH = $env:GOARCH; $oldCGO = $env:CGO_ENABLED
try {
    $env:GOOS='windows'; $env:GOARCH='amd64'; $env:CGO_ENABLED='0'
    Push-Location go-core
    try {
        go test ./...
        if ($LASTEXITCODE -ne 0) { throw 'Go tests failed.' }
        go build -buildvcs=false -trimpath -o ..\kotoba-core.exe .
        if ($LASTEXITCODE -ne 0) { throw 'Go build failed.' }
    } finally { Pop-Location }
} finally {
    $env:GOOS=$oldGOOS; $env:GOARCH=$oldGOARCH; $env:CGO_ENABLED=$oldCGO
}
& $PythonExe -m venv .build-venv
if ($LASTEXITCODE -ne 0) { throw 'Python venv failed.' }
$buildPython = Join-Path $projectRoot '.build-venv\Scripts\python.exe'
& $buildPython -m pip install --require-hashes -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Runtime dependency hash verification failed.' }
& $buildPython -m pip install pyinstaller==6.22.3
if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed.' }
& $buildPython -W error::ResourceWarning -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Python tests failed.' }
& $buildPython -m PyInstaller --clean --noconfirm --onedir --windowed --name KotobaBridge app.py
if ($LASTEXITCODE -ne 0) { throw 'UI freezing failed.' }
$bundle = Join-Path $projectRoot 'dist\KotobaBridge'
Copy-Item kotoba-core.exe $bundle
Copy-Item README.md,INSTALLATION.md,DESIGN.md,COMPATIBILITY.md,THIRD_PARTY_NOTICES.md,LICENSE $bundle
Copy-Item docs (Join-Path $bundle 'docs') -Recurse -Force
& $buildPython packaging\collect_notices.py --output (Join-Path $bundle 'THIRD_PARTY_LICENSES')
if ($LASTEXITCODE -ne 0) { throw 'License collection failed.' }
$goRoot = (go env GOROOT).Trim()
Copy-Item (Join-Path $goRoot 'LICENSE') (Join-Path $bundle 'THIRD_PARTY_LICENSES\Go-LICENSE.txt')
if ($TesseractRoot) {
    New-Item -ItemType Directory -Force (Join-Path $bundle 'ocr') | Out-Null
    Copy-Item (Join-Path $TesseractRoot '*') (Join-Path $bundle 'ocr') -Recurse -Force
}
# --windowed has no usable stdout; the process exit code and explicit report are checked.
$report = Join-Path $projectRoot 'dist\package-self-test.json'
$smoke = Start-Process -FilePath (Join-Path $bundle 'KotobaBridge.exe') -ArgumentList @('--self-test','--require-ocr','--report',('"' + $report + '"')) -PassThru
if (-not $smoke.WaitForExit(60000)) { $smoke.Kill(); throw 'Frozen app self-test timed out.' }
$smoke.Refresh()
if ($smoke.ExitCode -ne 0 -or -not (Test-Path $report)) { throw 'Frozen app self-test failed.' }
$smokeResult = Get-Content -Raw -Encoding UTF8 $report | ConvertFrom-Json
if (-not $smokeResult.ok) { throw 'Frozen app reported a failed self-test.' }
if (-not $SkipInstaller) {
    $compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    $iscc = if ($compiler) { $compiler.Source } else { Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe' }
    if (-not (Test-Path $iscc)) { throw 'Install Inno Setup 6 from its official site; no automatic download or policy bypass is performed.' }
    & $iscc packaging\installer.iss
    if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
}
# Separate portable tree: the installer must never inherit portable.flag or user data.
$portable = Join-Path $projectRoot 'dist\KotobaBridge-Portable'
if (Test-Path $portable) { throw 'Portable output already exists; use a clean build.' }
Copy-Item $bundle $portable -Recurse
New-Item -ItemType File (Join-Path $portable 'portable.flag') | Out-Null
$portableReport = Join-Path $projectRoot 'dist\portable-self-test.json'
$portableSmoke = Start-Process -FilePath (Join-Path $portable 'KotobaBridge.exe') -ArgumentList @('--self-test','--require-ocr','--report',('"'+$portableReport+'"')) -PassThru
if (-not $portableSmoke.WaitForExit(60000)) { $portableSmoke.Kill(); throw 'Portable OCR smoke timed out.' }
$portableSmoke.Refresh()
if ($portableSmoke.ExitCode -ne 0 -or -not (Test-Path $portableReport)) { throw 'Portable OCR smoke failed.' }
if (-not (Get-Content -Raw -Encoding UTF8 $portableReport | ConvertFrom-Json).ok) { throw 'Portable self-test reported failure.' }
Compress-Archive -Path $portable -DestinationPath 'dist\KotobaBridge-Portable-x64.zip' -CompressionLevel Optimal
$outputs = @('dist\KotobaBridge-Portable-x64.zip')
if (-not $SkipInstaller) { $outputs += 'dist\KotobaBridge-Setup-x64.exe' }
Get-ChildItem $outputs -ErrorAction Stop | ForEach-Object {
    "$((Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower())  $($_.Name)"
} | Set-Content dist\SHA256SUMS.txt -Encoding ascii
Write-Host 'Built unsigned installer and portable candidate with source-built OCR and Japanese model.'
Write-Host 'Installer/IPC smoke checks do not verify a real game, OCR quality, overlay, or low-spec performance.'
