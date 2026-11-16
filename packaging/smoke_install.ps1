# Disposable CI install/uninstall test; no game, screen capture, or external API.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
Set-Location (Split-Path $PSScriptRoot -Parent)
$installer = (Resolve-Path 'dist\KotobaBridge-Setup-x64.exe').Path
$target = Join-Path $env:TEMP ('KotobaBridge-Smoke-' + [guid]::NewGuid().ToString('N'))
$report = Join-Path (Get-Location) 'dist\installed-self-test.json'
# Synthetic retention fixtures only, never overwrite existing user data.
$dataRoot = Join-Path $env:LOCALAPPDATA 'KotobaBridge'
$fixtures = @('models\qwen2.5-1.5b-instruct-q4_k_m.gguf','deepl-key.dpapi','settings.json','overlay.json','cards\uninstall-test-card.json')
$createdFixtures = @()
$process = Start-Process -FilePath $installer -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/DIR="'+$target+'"')) -PassThru
if (-not $process.WaitForExit(120000)) { $process.Kill(); throw 'Installer timeout.' }
$process.Refresh()
if ($process.ExitCode -ne 0) { throw 'Installer returned failure.' }
try {
    $app = Join-Path $target 'KotobaBridge.exe'
    if (-not (Test-Path $app)) { throw 'Installed app missing.' }
    $check = Start-Process -FilePath $app -ArgumentList @('--self-test','--require-ocr','--report',('"'+$report+'"')) -PassThru
    if (-not $check.WaitForExit(60000)) { $check.Kill(); throw 'Installed self-test timeout.' }
    $check.Refresh()
    if ($check.ExitCode -ne 0 -or -not (Test-Path $report)) { throw 'Installed self-test failed.' }
    if (-not (Get-Content -Raw -Encoding UTF8 $report | ConvertFrom-Json).ok) { throw 'Self-test reported failure.' }
    foreach ($relative in $fixtures) {
        $fixture = Join-Path $dataRoot $relative
        if (Test-Path $fixture) { throw 'Retention fixture would overwrite existing data.' }
        New-Item -ItemType Directory -Force (Split-Path $fixture -Parent) | Out-Null
        [IO.File]::WriteAllText($fixture,'KOTOBA-SYNTHETIC-RETENTION-FIXTURE')
        $createdFixtures += $fixture
    }
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

foreach ($fixture in $createdFixtures) {
    if (-not (Test-Path $fixture)) { throw 'Uninstall unexpectedly deleted retained data.' }
    if ([IO.File]::ReadAllText($fixture) -ne 'KOTOBA-SYNTHETIC-RETENTION-FIXTURE') { throw 'Retained data changed.' }
}
foreach ($fixture in $createdFixtures) { Remove-Item -LiteralPath $fixture }
Write-Host 'Silent uninstall preserved model, API-key, settings, overlay and card synthetic fixtures.'
