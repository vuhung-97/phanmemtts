param(
    [switch]$NoLaunch,
    [switch]$Quiet,
    [string]$AppDir = ""
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms | Out-Null

$Pkg = $PSScriptRoot
$Title = "Cập nhật phần mềm"

function Show-Info([string]$text) {
    if ($Quiet) { Write-Host $text } else {
        [System.Windows.Forms.MessageBox]::Show($text, $Title, "OK", "Information") | Out-Null
    }
}
function Show-Error([string]$text) {
    if ($Quiet) { Write-Host "LOI: $text" } else {
        [System.Windows.Forms.MessageBox]::Show($text, $Title, "OK", "Error") | Out-Null
    }
}

$manifestPath = Join-Path $Pkg "manifest_update.json"
if (-not (Test-Path $manifestPath)) {
    Show-Error "Thiếu manifest_update.json trong gói cập nhật."
    exit 1
}
try {
    $manifest = Get-Content $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    Show-Error "manifest_update.json bị hỏng."
    exit 1
}

$appName = $manifest.app
$newVersion = $manifest.version

# Xác định thư mục cài (mặc định: thư mục cha của gói cập nhật)
if (-not $AppDir) {
    $parent = Split-Path $Pkg -Parent
    if (Test-Path (Join-Path $parent "$appName.exe")) {
        $AppDir = $parent
    }
}
if (-not $AppDir -or -not (Test-Path (Join-Path $AppDir "$appName.exe"))) {
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = "Chọn thư mục cài phần mềm (nơi có $appName.exe)"
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
    $AppDir = $dialog.SelectedPath
}
if (-not (Test-Path (Join-Path $AppDir "$appName.exe"))) {
    Show-Error "Không thấy $appName.exe trong:`n$AppDir"
    exit 1
}
# Chuẩn hoá thành đường dẫn tuyệt đối (backup/rollback dùng Substring trên FullName)
$AppDir = (Resolve-Path -LiteralPath $AppDir).Path

# Phải đóng phần mềm trước khi ghi đè
$procName = [System.IO.Path]::GetFileNameWithoutExtension("$appName.exe")
$running = @(Get-Process -Name $procName -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) {
    Show-Info "Phần mềm đang chạy. Hãy đóng phần mềm rồi bấm OK để tiếp tục."
    $running = @(Get-Process -Name $procName -ErrorAction SilentlyContinue)
    if ($running.Count -gt 0) {
        Show-Error "Phần mềm vẫn đang chạy — chưa cập nhật."
        exit 1
    }
}

# Phiên bản hiện tại
$oldVersion = "?"
$curManifest = Join-Path $AppDir "manifest.json"
if (Test-Path $curManifest) {
    try {
        $oldVersion = (Get-Content $curManifest -Raw -Encoding UTF8 | ConvertFrom-Json).version
    } catch { }
}
if ($oldVersion -eq $newVersion) {
    Show-Info "Phần mềm đã là phiên bản $newVersion."
    exit 0
}

$payload = Join-Path $Pkg "payload"
if (-not (Test-Path $payload)) {
    Show-Error "Gói cập nhật thiếu thư mục payload."
    exit 1
}

# Sao lưu các file sắp ghi đè
$backup = Join-Path $AppDir ("backup\" + $oldVersion + "_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $backup | Out-Null

$files = New-Object System.Collections.Generic.List[string]
Get-ChildItem $payload -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($payload.Length + 1)
    $key = $rel -replace '\\', '/'
    $files.Add($key)
    $target = Join-Path $AppDir $key
    if (Test-Path $target) {
        $bdir = Split-Path (Join-Path $backup $key) -Parent
        New-Item -ItemType Directory -Force -Path $bdir | Out-Null
        Copy-Item $target (Join-Path $backup $key) -Force
    }
}

# Copy đè
Get-ChildItem $payload -Force | ForEach-Object {
    Copy-Item $_.FullName $AppDir -Recurse -Force
}

# Xoá file không còn dùng
$deleteFile = Join-Path $Pkg "delete.txt"
if (Test-Path $deleteFile) {
    Get-Content $deleteFile -Encoding UTF8 | Where-Object { $_.Trim() } | ForEach-Object {
        $rel = $_.Trim()
        $target = Join-Path $AppDir $rel
        if (Test-Path $target) {
            $bdir = Split-Path (Join-Path $backup $rel) -Parent
            New-Item -ItemType Directory -Force -Path $bdir | Out-Null
            Copy-Item $target (Join-Path $backup $rel) -Force -ErrorAction SilentlyContinue
            Remove-Item $target -Force
        }
    }
}

# Kiểm tra sha256
$bad = New-Object System.Collections.Generic.List[string]
foreach ($rel in $files) {
    $entry = $manifest.files.PSObject.Properties[$rel]
    if ($null -eq $entry) { continue }
    $expected = [string]$entry.Value.sha256
    $target = Join-Path $AppDir $rel
    if (-not (Test-Path $target)) {
        $bad.Add("thiếu: $rel")
        continue
    }
    $actual = (Get-FileHash $target -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $expected.ToLower()) {
        $bad.Add("sai hash: $rel")
    }
}

if ($bad.Count -gt 0) {
    Get-ChildItem $backup -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($backup.Length + 1)
        $target = Join-Path $AppDir $rel
        $tdir = Split-Path $target -Parent
        New-Item -ItemType Directory -Force -Path $tdir | Out-Null
        Copy-Item $_.FullName $target -Force
    }
    Show-Error ("Cập nhật lỗi, đã khôi phục bản cũ:`n" + ($bad -join "`n"))
    exit 1
}

Copy-Item $manifestPath (Join-Path $AppDir "manifest.json") -Force

Show-Info "Đã cập nhật lên phiên bản $newVersion.`nBản sao lưu: $backup"

if (-not $NoLaunch) {
    Start-Process (Join-Path $AppDir "$appName.exe")
}
exit 0
