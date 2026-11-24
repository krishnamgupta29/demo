# Packaging script for DENTRACE production ONNX model release assets
# Destination: C:\release\ (to keep physical D: free of large files)

$ErrorActionPreference = "Stop"

$releaseDir = "C:\release"
$stagingDir = "C:\release\staging_default"
$checkpointsDir = "models\checkpoints"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  DENTRACE Model Release Packager" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Ensure target directories exist
if (-not (Test-Path $releaseDir)) {
    New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
}
if (Test-Path $stagingDir) {
    Remove-Item -Path $stagingDir -Recurse -Force | Out-Null
}
New-Item -ItemType Directory -Path "$stagingDir\models\checkpoints" -Force | Out-Null

# 2. Required Default Flow Models
$defaultModels = @(
    "dentex_yolov8n_seg_static_qdq_int8.onnx",
    "dentex_yolov8n_seg_best.onnx",
    "dentex_fdi_yolov8s_best.onnx",
    "best.onnx"
)

Write-Host "`n[*] Staging required default models:" -ForegroundColor Yellow
$checksums = @()

foreach ($m in $defaultModels) {
    $srcPath = Join-Path $checkpointsDir $m
    if (-not (Test-Path $srcPath)) {
        Write-Error "Required model not found: $srcPath"
    }
    $destPath = Join-Path "$stagingDir\models\checkpoints" $m
    Copy-Item -Path $srcPath -Destination $destPath -Force
    
    $hash = (Get-FileHash -Path $srcPath -Algorithm SHA256).Hash.ToLower()
    $size = (Get-Item $srcPath).Length
    $checksums += "$hash  models/checkpoints/$m"
    Write-Host ("  + {0} ({1:N2} MB)" -f $m, ($size / 1MB))
}

# Write checksums file (UTF-8 without BOM)
$checksumFile = "$stagingDir\SHA256SUMS.txt"
[System.IO.File]::WriteAllLines($checksumFile, $checksums)
Write-Host "  + SHA256SUMS.txt written"

# 3. Zip default flow release package
$zipDefault = "$releaseDir\dentrace_models_default_v1.0.zip"
if (Test-Path $zipDefault) {
    Remove-Item -Path $zipDefault -Force
}

Write-Host "`n[*] Creating default models archive: $zipDefault" -ForegroundColor Yellow
Compress-Archive -Path "$stagingDir\*" -DestinationPath $zipDefault -CompressionLevel Optimal
$zipDefaultSize = (Get-Item $zipDefault).Length

Write-Host ("Default release zip created: {0:N2} MB" -f ($zipDefaultSize / 1MB)) -ForegroundColor Green
if ($zipDefaultSize -gt 2147483648) {
    Write-Error "Default zip exceeds 2 GB limit!"
}

# 4. Optional Root Canal Model Archive
$optModel = "8024.onnx"
$optSrc = Join-Path $checkpointsDir $optModel
if (Test-Path $optSrc) {
    Write-Host "`n[*] Packaging optional root canal model: $optModel" -ForegroundColor Yellow
    $stagingOpt = "C:\release\staging_rct"
    if (Test-Path $stagingOpt) {
        Remove-Item -Path $stagingOpt -Recurse -Force | Out-Null
    }
    New-Item -ItemType Directory -Path "$stagingOpt\models\checkpoints" -Force | Out-Null
    Copy-Item -Path $optSrc -Destination "$stagingOpt\models\checkpoints\$optModel" -Force
    $optHash = (Get-FileHash -Path $optSrc -Algorithm SHA256).Hash.ToLower()
    [System.IO.File]::WriteAllLines("$stagingOpt\SHA256SUMS.txt", @("$optHash  models/checkpoints/$optModel"))
    
    $zipOpt = "$releaseDir\dentrace_models_optional_rct_v1.0.zip"
    if (Test-Path $zipOpt) {
        Remove-Item -Path $zipOpt -Force
    }
    Compress-Archive -Path "$stagingOpt\*" -DestinationPath $zipOpt -CompressionLevel Optimal
    $zipOptSize = (Get-Item $zipOpt).Length
    Write-Host ("Optional RCT zip created: {0:N2} MB" -f ($zipOptSize / 1MB)) -ForegroundColor Green
    
    Remove-Item -Path $stagingOpt -Recurse -Force | Out-Null
}

# Clean staging
Remove-Item -Path $stagingDir -Recurse -Force | Out-Null

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "  Release Packaging Complete in C:\release\" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Get-ChildItem -Path $releaseDir -Filter "*.zip" | Select-Object Name, @{Name="Size (MB)"; Expression={"{0:N2}" -f ($_.Length / 1MB)}}
