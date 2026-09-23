# Install Azure CLI (requires Administrator / UAC approval)
# powershell -ExecutionPolicy Bypass -File scripts/windows/install-azure-cli.ps1

$ErrorActionPreference = "Stop"
$msi = Join-Path $env:TEMP "azure-cli.msi"
$log = Join-Path $env:TEMP "azure-cli-install.log"
$uri = "https://aka.ms/installazurecliwindowsx64"

Write-Host "Downloading Azure CLI..."
Invoke-WebRequest -Uri $uri -OutFile $msi -UseBasicParsing
Write-Host "Installing (UAC prompt may appear)..."
$p = Start-Process msiexec.exe -Verb RunAs -ArgumentList "/i `"$msi`" /qn /norestart /l*v `"$log`"" -PassThru -Wait
Write-Host "msiexec exit: $($p.ExitCode)"
$az = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
if (Test-Path $az) {
  & $az version
  Write-Host "OK. Open a new terminal, then: az login"
} else {
  Write-Host "az.cmd not found. Check log: $log"
  if (Test-Path $log) {
    Select-String -Path $log -Pattern "error|return value 3|Installation success" | Select-Object -Last 15
  }
  exit 1
}
