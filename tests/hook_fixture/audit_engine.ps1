param([Parameter(Mandatory=$true)][string]$EngineRoot,[Parameter(Mandatory=$true)][string]$Report)
$ErrorActionPreference='Stop'
$records=@()
foreach($arch in @('x64','x86')) {
  $folder=Join-Path $EngineRoot $arch
  foreach($name in @('TextractorCLI.exe','texthook.dll','MSVCP140.dll','VCRUNTIME140.dll','VCRUNTIME140_1.dll')) {
    $file=Join-Path $folder $name
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
      $records+= [ordered]@{architecture=$arch;file=$name;present=$false;note='May require system Microsoft VC runtime; not auto-installed'}
      continue
    }
    $sig=Get-AuthenticodeSignature -LiteralPath $file
    $records+= [ordered]@{
      architecture=$arch;file=$name;present=$true
      sha256=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLower()
      signature_status=$sig.Status.ToString()
      signer_subject=if($sig.SignerCertificate){$sig.SignerCertificate.Subject}else{$null}
      signer_thumbprint=if($sig.SignerCertificate){$sig.SignerCertificate.Thumbprint}else{$null}
      timestamp_subject=if($sig.TimeStamperCertificate){$sig.TimeStamperCertificate.Subject}else{$null}
    }
    Write-Host "$arch $name signature=$($sig.Status)"
  }
}
[ordered]@{checked_at_utc=[DateTime]::UtcNow.ToString('o');scope='Read-only official distribution signature audit; no user/game files';records=$records;security_settings_changed=$false;trust_override=$false} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $Report -Encoding utf8
# A report is not an install/execute permit. CI synthetic execution is separately authorized.
