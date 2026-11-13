# Builds an unsigned app installer candidate. No paid API calls or automatic releases.
param(
    [string]$TesseractRoot = '',
    [string]$PythonExe = 'python',
    [switch]$SkipInstaller
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
if ($env:OS -ne 'Windows_NT') { throw 'Run this build on Windows x64.' }
if (-not [Environment]::Is64BitProcess) { throw 'Use a 64-bit PowerShell and Python installation.' }
& $PythonExe -c "import struct,sys; assert struct.calcsize('P')==8; assert sys.version_info[:2]==(3,11)"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 x64 is required.' }
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
& $buildPython -m pip install -r requirements.txt pyinstaller==6.22.3
if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed.' }
& $buildPython -W error::ResourceWarning -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Python tests failed.' }
& $buildPython -m PyInstaller --clean --noconfirm --onedir --windowed --name KotobaBridge app.py
if ($LASTEXITCODE -ne 0) { throw 'UI freezing failed.' }
$bundle = Join-Path $projectRoot 'dist\KotobaBridge'
Copy-Item kotoba-core.exe $bundle
Copy-Item README.md,INSTALLATION.md,DESIGN.md,COMPATIBILITY.md,THIRD_PARTY_NOTICES.md,LICENSE $bundle
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
$smoke = Start-Process -FilePath (Join-Path $bundle 'KotobaBridge.exe') -ArgumentList @('--self-test','--report',('"' + $report + '"')) -PassThru
if (-not $smoke.WaitForExit(30000)) { $smoke.Kill(); throw 'Frozen app self-test timed out.' }
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
    Get-FileHash dist\KotobaBridge-Setup-x64.exe -Algorithm SHA256 | ForEach-Object {
        "$($_.Hash.ToLower())  KotobaBridge-Setup-x64.exe"
    } | Set-Content dist\SHA256SUMS.txt -Encoding ascii
}
Write-Host 'Built unsigned development candidate. OCR is separate unless explicitly audited and bundled.'
Write-Host 'Installer/IPC smoke checks do not verify a real game, OCR quality, overlay, or low-spec performance.'
