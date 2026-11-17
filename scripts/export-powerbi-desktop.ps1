param(
  [Parameter(Mandatory=$true)][int]$Port,
  [Parameter(Mandatory=$true)][string]$Output,
  [string]$ClientDll
)
$ErrorActionPreference = 'Stop'
if ($Port -lt 1 -or $Port -gt 65535) { throw 'Invalid local Desktop port' }
if (!$ClientDll) {
  $package = Get-AppxPackage Microsoft.MicrosoftPowerBIDesktop
  if (!$package) { throw 'Specify -ClientDll for your installed ADOMD client' }
  $ClientDll = Join-Path $package.InstallLocation 'bin/Microsoft.PowerBI.AdomdClient.dll'
}
Add-Type -Path $ClientDll
$connection = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$Port;Application Name=Arbor3D Local Export")
function Read-Dax([string]$Query) {
  $command = $connection.CreateCommand()
  $command.CommandText = $Query
  $command.CommandTimeout = 60
  $reader = $command.ExecuteReader()
  $rows = [System.Collections.Generic.List[object]]::new()
  try {
    while ($reader.Read()) {
      $row = [ordered]@{}
      for ($i=0; $i -lt $reader.FieldCount; $i++) {
        $name = $reader.GetName($i) -replace '^.*\[([^\]]+)\]$', '$1'
        $value = $reader.GetValue($i)
        if ($value -is [DBNull]) { $value = $null }
        elseif ($value -is [DateTime]) { $value = $value.ToString('yyyy-MM-dd') }
        $row[$name] = $value
      }
      $rows.Add($row)
    }
  } finally { $reader.Close(); $command.Dispose() }
  return ,$rows.ToArray()
}
try {
  $connection.Open()
  $tables = [ordered]@{}
  foreach ($table in @('DimScan','FactObservation','FactEstimate','FactGrowth')) {
    $tables[$table] = Read-Dax "EVALUATE '$table'"
  }
  $query = @'
EVALUATE SUMMARIZECOLUMNS(DimScan[scan_id],
 "observations", [Observations], "paired_count", [Valid Pairs],
 "mae_cm", [MAE cm], "rmse_cm", [RMSE cm], "bias_cm", [Bias cm],
 "mape_pct", [MAPE percent], "review_count", [Review Observations],
 "average_dbh_cm", [Average DBH cm], "co2_ton", [Estimated CO2 Snapshot ton],
 "demo_pairs", [Demo Pairs], "demo_mae_cm", [Demo MAE cm])
'@
  $overview = Read-Dax 'EVALUATE ROW("trees", [Observed Trees], "observations", [Observations], "latest_review_trees", [Latest Review Trees], "latest_review_rate", [Latest Review Rate], "latest_co2_ton", [Latest CO2 Snapshot ton], "growth_records", [Growth Records], "formal_pairs", [Valid Pairs], "formal_mae", [MAE cm])'
  $result = [ordered]@{engine='Power BI Desktop / Analysis Services'; queried_at=[DateTime]::UtcNow.ToString('o'); tables=$tables; metrics=(Read-Dax $query); overview=$overview}
  $full = [IO.Path]::GetFullPath($Output)
  [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($full)) | Out-Null
  [IO.File]::WriteAllText($full, ($result | ConvertTo-Json -Depth 30), [Text.UTF8Encoding]::new($false))
  Write-Output "Desktop DAX results saved: $($result.metrics.Count) scans."
} finally { $connection.Close(); $connection.Dispose() }
