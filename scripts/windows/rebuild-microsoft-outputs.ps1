# Windows：重建 Microsoft Analytics / Power BI 產出
# 從 repo 根目錄執行：
#   powershell -ExecutionPolicy Bypass -File scripts/windows/rebuild-microsoft-outputs.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Out = Join-Path $RepoRoot "outputs\windows-microsoft-$Stamp"
$SchemaCache = Join-Path $RepoRoot "outputs\powerbi-schema-cache"
$AnalyticsOut = Join-Path $Out "analytics"
$PowerBiOut = Join-Path $Out "powerbi"
New-Item -ItemType Directory -Force -Path $Out | Out-Null

Write-Host "== npm ci (app) =="
npm ci --prefix app

Write-Host "== Import pipeline tests =="
node --test app/tests/importPipeline.test.ts

Write-Host "== Analytics from 逢甲示範 inventory =="
$Report = "app/src/data/inventories/20260818092855.json"
python -m analytics --report $Report --site-id fengchia --out $AnalyticsOut

Write-Host "== Power BI project =="
python -m powerbi.build_project --analytics $AnalyticsOut --out $PowerBiOut

if (Test-Path $SchemaCache) {
  Write-Host "== Validate PBIP against schema cache =="
  python -m powerbi.validate_project $PowerBiOut --cache $SchemaCache
} else {
  Write-Host "== Schema cache missing; skip validate (optional download later) =="
}

Write-Host "== Done =="
Write-Host "Output: $Out"
Write-Host "Open the .pbip in Power BI Desktop on this Windows machine to set desktop_validated=true later."
