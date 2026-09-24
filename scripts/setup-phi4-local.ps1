param(
  [string]$Model = "phi-4-mini"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repoRoot "app\.env.local"

function Resolve-FoundryCommand {
  $command = Get-Command foundry -ErrorAction SilentlyContinue
  if ($command) { return $command.Source }

  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "找不到 winget。請先安裝或更新 Microsoft App Installer。"
  }

  Write-Host "Installing Microsoft Foundry Local..."
  winget install --id Microsoft.FoundryLocal --exact --accept-package-agreements --accept-source-agreements

  $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
  $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
  $env:Path = "$machinePath;$userPath"
  $command = Get-Command foundry -ErrorAction SilentlyContinue
  if (-not $command) {
    throw "Foundry Local 已安裝，但目前終端機尚未取得新 PATH。請關閉 PowerShell、重新開啟後再執行此腳本。"
  }
  return $command.Source
}

function Set-EnvValue([string]$Path, [string]$Name, [string]$Value) {
  $content = if (Test-Path $Path) { Get-Content -Raw -Path $Path } else { "" }
  $line = "$Name=$Value"
  $pattern = "(?m)^" + [regex]::Escape($Name) + "=.*$"
  if ($content -match $pattern) {
    $content = [regex]::Replace($content, $pattern, $line)
  } else {
    if ($content.Length -gt 0 -and -not $content.EndsWith("`n")) { $content += "`r`n" }
    $content += "$line`r`n"
  }
  Set-Content -Path $Path -Value $content -Encoding utf8NoBOM
}

$foundry = Resolve-FoundryCommand
Write-Host "Preparing model $Model (the first download can be several GB)..."

# Current Foundry Local supports model download; newer releases can use model load.
& $foundry model download $Model
if ($LASTEXITCODE -ne 0) {
  Write-Host "Trying the newer Foundry Local model load command..."
  & $foundry model load $Model
  if ($LASTEXITCODE -ne 0) { throw "無法下載或載入 $Model" }
}

& $foundry server start
if ($LASTEXITCODE -ne 0) { throw "Foundry Local server 啟動失敗" }

$status = (& $foundry server status 2>&1 | Out-String)
Write-Host $status
$endpointMatch = [regex]::Match($status, 'https?://(?:127\.0\.0\.1|localhost|\[::1\]):\d+')
if (-not $endpointMatch.Success) {
  throw "模型已準備完成，但無法從 server status 自動辨識 endpoint。請將上方 localhost URL 填入 app\.env.local 的 FOUNDRY_LOCAL_ENDPOINT。"
}

Set-EnvValue -Path $envFile -Name "ARBOR_AI_PROVIDER" -Value "phi4"
Set-EnvValue -Path $envFile -Name "FOUNDRY_LOCAL_ENDPOINT" -Value $endpointMatch.Value
Set-EnvValue -Path $envFile -Name "FOUNDRY_LOCAL_MODEL" -Value $Model

Write-Host "Phi-4 is ready. Local configuration updated: $envFile"
Write-Host "Next: cd app; npm ci; npm run dev"
