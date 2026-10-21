# Dong goi ban phat hanh v3 thanh file ZIP de gui/chuyen may.
# Dung: powershell -ExecutionPolicy Bypass -File packaging\make_zip_v3.ps1
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem

$root = Split-Path -Parent $PSScriptRoot
$appName = 'PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3'
$src = Join-Path $root "dist\$appName"
$zip = Join-Path $root "dist\$appName.zip"

if (-not (Test-Path $src)) { throw "Khong tim thay $src" }
if (Test-Path $zip) { Remove-Item $zip -Force }

Write-Host "[ZIP] Dang nen $appName ..."
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $src, $zip, [System.IO.Compression.CompressionLevel]::Optimal, $true)

$sizeMB = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "[ZIP] Xong: $zip ($sizeMB MB)"
