# Pinned source build; no third-party prebuilt OCR installers or unverified DLLs.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Split-Path $PSScriptRoot -Parent
$pin = 'fe8e78fac7df2793f9848ed0d27aa59d9c035998'
$modelPin = '87416418657359cb625c412a48b6e1d6d41c29bd'
$modelHash = '1f5de9236d2e85f5fdf4b3c500f2d4926f8d9449f28f5394472d9e8d83b91b4d'
$work = Join-Path $root '.ocr-build'
$repo = Join-Path $work 'vcpkg'
$out = Join-Path $root '.ocr-bundle'
if (Test-Path $out) { throw 'OCR output already exists. Use a clean worktree to avoid mixing dependencies.' }
New-Item -ItemType Directory -Force $work | Out-Null
if (-not (Test-Path $repo)) {
    git init $repo
    if ($LASTEXITCODE -ne 0) { throw 'vcpkg repository init failed.' }
    git -C $repo remote add origin https://github.com/microsoft/vcpkg.git
    if ($LASTEXITCODE -ne 0) { throw 'vcpkg remote setup failed.' }
    git -C $repo fetch --depth 1 origin $pin
    if ($LASTEXITCODE -ne 0) { throw 'Pinned vcpkg fetch failed.' }
    git -C $repo checkout --detach FETCH_HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Pinned vcpkg checkout failed.' }
}
if ((git -C $repo rev-parse HEAD).Trim() -ne $pin) { throw 'Unexpected vcpkg revision.' }
if (git -C $repo status --porcelain) { throw 'vcpkg source has unreviewed changes.' }
& (Join-Path $repo 'bootstrap-vcpkg.bat') -disableMetrics
if ($LASTEXITCODE -ne 0) { throw 'vcpkg bootstrap failed.' }
$manifest = Join-Path $PSScriptRoot 'ocr-source'
$install = Join-Path $work 'installed'
$env:VCPKG_DISABLE_METRICS='1'
# Disable external binary caches: OCR and libraries must be built from pinned sources.
& (Join-Path $repo 'vcpkg.exe') install "--x-manifest-root=$manifest" "--x-install-root=$install" "--overlay-triplets=$manifest\triplets" --triplet x64-kotoba-static --binarysource=clear
if ($LASTEXITCODE -ne 0) { throw 'Pinned OCR source build failed.' }
$target = Join-Path $install 'x64-kotoba-static'
$engine = Join-Path $target 'tools\tesseract\tesseract.exe'
if (-not (Test-Path $engine)) { throw 'Source-built Tesseract CLI is missing.' }
New-Item -ItemType Directory -Force "$out\tessdata", "$out\licenses", "$out\provenance" | Out-Null
Copy-Item $engine "$out\tesseract.exe"
# Static dependency build must not silently acquire a separate third-party DLL runtime.
if (Get-ChildItem "$target\tools\tesseract" -Filter '*.dll' -ErrorAction SilentlyContinue) { throw 'Unexpected OCR DLLs need explicit review.' }
# Record and ship all built-port copyright files, SPDX SBOMs, and exact recipes.
$allowedPorts = @('tesseract','leptonica','giflib','libjpeg-turbo','libpng','libwebp','openjpeg','tiff','zlib','liblzma','libspng','vcpkg-cmake','vcpkg-cmake-config','vcpkg-cmake-get-vars')
$ports = Get-ChildItem "$target\share" -Directory
foreach ($port in $ports) {
    if ($port.Name -notin $allowedPorts) { throw "Unreviewed dependency $($port.Name): update license review before packaging." }
    $copyright = Join-Path $port.FullName 'copyright'
    if (-not (Test-Path $copyright)) { throw "Missing license notice for $($port.Name)" }
    $dest = Join-Path "$out\licenses" $port.Name
    New-Item -ItemType Directory -Force $dest | Out-Null
    Copy-Item $copyright $dest
    Get-ChildItem $port.FullName -Filter '*.spdx.json' | Copy-Item -Destination $dest
    $recipe = Join-Path $repo "ports\$($port.Name)"
    if (Test-Path $recipe) { Copy-Item $recipe (Join-Path "$out\provenance" $port.Name) -Recurse }
}
Copy-Item "$repo\LICENSE.txt" "$out\licenses\vcpkg-LICENSE.txt"
Copy-Item "$install\vcpkg\status" "$out\provenance\vcpkg-status.txt"
Copy-Item "$manifest\vcpkg.json", "$manifest\triplets\x64-kotoba-static.cmake" "$out\provenance"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/$modelPin/jpn.traineddata" -OutFile "$out\tessdata\jpn.traineddata"
if ((Get-FileHash "$out\tessdata\jpn.traineddata" -Algorithm SHA256).Hash.ToLower() -ne $modelHash) { throw 'Japanese model hash mismatch.' }
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/$modelPin/LICENSE" -OutFile "$out\licenses\tessdata_fast-LICENSE.txt"
# Reject non-system imports even when the developer runner happens to have a runtime installed.
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path $vswhere)) { throw 'Visual Studio vswhere is required for runtime dependency audit.' }
$vsPath = (& $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath).Trim()
$dumpbin = Get-ChildItem "$vsPath\VC\Tools\MSVC\*\bin\Hostx64\x64\dumpbin.exe" | Sort-Object FullName -Descending | Select-Object -First 1
if (-not $dumpbin) { throw 'dumpbin is required to audit OCR runtime dependencies.' }
$imports = & $dumpbin.FullName /dependents "$out\tesseract.exe"
if ($LASTEXITCODE -ne 0) { throw 'OCR import inspection failed.' }
$imports | Set-Content "$out\provenance\pe-imports.txt" -Encoding utf8
$systemDlls = @('kernel32.dll','user32.dll','gdi32.dll','advapi32.dll','shell32.dll','ole32.dll','oleaut32.dll','ws2_32.dll','shlwapi.dll','version.dll','comdlg32.dll','comctl32.dll','imm32.dll','winmm.dll','rpcrt4.dll','bcrypt.dll','ntdll.dll','ucrtbase.dll')
$importNames = @($imports | ForEach-Object { if ($_ -match '^\s*([A-Za-z0-9_.-]+\.dll)\s*$') { $Matches[1].ToLower() } })
if ($importNames.Count -eq 0) { throw 'Could not parse OCR PE imports.' }
foreach ($name in $importNames) {
    if ($name -notin $systemDlls -and $name -notmatch '^api-ms-win-[a-z0-9-]+\.dll$') { throw "Unbundled OCR runtime dependency: $name" }
}
& "$out\tesseract.exe" --version
if ($LASTEXITCODE -ne 0) { throw 'Bundled OCR engine cannot execute.' }
& "$out\tesseract.exe" --tessdata-dir "$out\tessdata" --list-langs
if ($LASTEXITCODE -ne 0) { throw 'Bundled OCR language check failed.' }
@"
# OCR source build provenance
vcpkg: https://github.com/microsoft/vcpkg/tree/$pin
Model: https://github.com/tesseract-ocr/tessdata_fast/tree/$modelPin
jpn SHA256: $modelHash
Build: x64 Windows, static CRT/libraries, release, no Tesseract curl/libarchive/training tools.
Recipes include source archive hashes and patches. License text per built port is in licenses/.
No UB Mannheim installer content is used. Actual versions are in provenance/vcpkg-status.txt.
This record proves build inputs, not game OCR quality or low-spec performance.
"@ | Set-Content "$out\REDISTRIBUTION_REVIEW.md" -Encoding utf8
Get-ChildItem $out -File -Recurse | Sort-Object FullName | ForEach-Object {
    $relative = [IO.Path]::GetRelativePath($out, $_.FullName).Replace('\','/')
    "$((Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower())  $relative"
} | Set-Content "$work\OCR-SHA256SUMS.txt" -Encoding ascii
Copy-Item "$work\OCR-SHA256SUMS.txt" $out
Write-Host 'Pinned OCR source bundle ready. Actual recognition must pass app smoke tests before artifact upload.'
