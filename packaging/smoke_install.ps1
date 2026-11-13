# Disposable CI install/uninstall test; no game, screen capture, or external API.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
Set-Location (Split-Path $PSScriptRoot -Parent)
$installer = (Resolve-Path 'dist\KotobaBridge-Setup-x64.exe').Path
$target = Join-Path $env:TEMP ('KotobaBridge-Smoke-' + [guid]::NewGuid().ToString('N'))
$report = Join-Path (Get-Location) 'dist\installed-self-test.json'
$process = Start-Process -FilePath $installer -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/DIR="'+$target+'"')) -PassThru
if (-not $process.WaitForExit(120000)) { $process.Kill(); throw 'Installer timeout.' }
$process.Refresh()
if ($process.ExitCode -ne 0) { throw 'Installer returned failure.' }
try {
    $app = Join-Path $target 'KotobaBridge.exe'
    if (-not (Test-Path $app)) { throw 'Installed app missing.' }
    $check = Start-Process -FilePath $app -ArgumentList @('--self-test','--report',('"'+$report+'"')) -PassThru
    if (-not $check.WaitForExit(30000)) { $check.Kill(); throw 'Installed self-test timeout.' }
    $check.Refresh()
    if ($check.ExitCode -ne 0 -or -not (Test-Path $report)) { throw 'Installed self-test failed.' }
    if (-not (Get-Content -Raw -Encoding UTF8 $report | ConvertFrom-Json).ok) { throw 'Self-test reported failure.' }
} finally {
    $uninstaller = Join-Path $target 'unins000.exe'
    if (Test-Path $uninstaller) {
        $remove = Start-Process -FilePath $uninstaller -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -PassThru
        if (-not $remove.WaitForExit(120000)) { $remove.Kill(); throw 'Uninstaller timeout.' }
        $remove.Refresh()
        if ($remove.ExitCode -ne 0) { throw 'Uninstaller returned failure.' }
    }
}
if (Test-Path (Join-Path $target 'KotobaBridge.exe')) { throw 'App still present after uninstall.' }
Write-Host 'Installer, installed offline self-test, and uninstall smoke completed.'
