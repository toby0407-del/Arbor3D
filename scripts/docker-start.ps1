param(
    [string]$StorageRoot = '',
    [ValidateSet('full', 'web')][string]$Target = 'full',
    [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repo
$envFile = Join-Path $repo '.env.docker'
if (!(Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath (Join-Path $repo 'docker/env.example') -Destination $envFile
}
if (!$StorageRoot) {
    $line = Get-Content -LiteralPath $envFile | Where-Object { $_ -match '^ARBOR3D_STORAGE_ROOT=' } | Select-Object -First 1
    if ($line) { $StorageRoot = $line.Split('=', 2)[1].Trim() }
    else { $StorageRoot = Join-Path $repo 'docker-data' }
}
if (![IO.Path]::IsPathRooted($StorageRoot)) { $StorageRoot = Join-Path $repo $StorageRoot }
$StorageRoot = [IO.Path]::GetFullPath($StorageRoot)
foreach ($folder in @('inbox', 'scans', 'data', 'cache', 'runtime')) {
    New-Item -ItemType Directory -Force -Path (Join-Path $StorageRoot $folder) | Out-Null
}
# Seed media only on first launch. Never overwrite inventories produced later.
$marker = Join-Path $StorageRoot 'scans/.arbor3d-seeded'
if (!(Test-Path -LiteralPath $marker)) {
    & robocopy (Join-Path $repo 'app/public/scans') (Join-Path $StorageRoot 'scans') /E /XC /XN /XO /NFL /NDL /NJH /NJS | Out-Null
    if ($LASTEXITCODE -ge 8) { throw 'Could not initialize scan media.' }
    Set-Content -LiteralPath $marker -Value 'Arbor3D initial media copied' -Encoding utf8
}
$env:ARBOR3D_STORAGE_ROOT = $StorageRoot.Replace('\', '/')
$env:ARBOR3D_BUILD_TARGET = $Target
if ($PrepareOnly) {
    Write-Host "Persistent storage initialized: $StorageRoot"
    return
}
$docker = Get-Command docker -ErrorAction SilentlyContinue
$dockerPath = if ($docker) { $docker.Source } else { '' }
if (!$docker) {
    foreach ($candidate in @('D:/DockerDesktop/resources/bin/docker.exe', "$env:LOCALAPPDATA/Programs/DockerDesktop/resources/bin/docker.exe", 'C:/Program Files/Docker/Docker/resources/bin/docker.exe')) {
        if (Test-Path -LiteralPath $candidate) { $dockerPath = $candidate; break }
    }
}
if (!$dockerPath) { throw 'Docker Desktop is not installed. See docker/README.md.' }
& $dockerPath info --format '{{.OSType}}'
if ($LASTEXITCODE -ne 0) { throw 'Docker engine unavailable. Enable BIOS virtualization and start Docker Desktop.' }
& $dockerPath compose --env-file $envFile config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose configuration is invalid.' }
& $dockerPath compose --env-file $envFile up -d --build --wait --wait-timeout 180
if ($LASTEXITCODE -ne 0) { throw 'Container build or health check failed.' }
Write-Host 'Arbor3D is ready. Default URL: http://localhost:8080'
