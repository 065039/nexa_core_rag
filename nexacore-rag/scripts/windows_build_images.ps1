# Run on WINDOWS (PowerShell) where Docker Desktop and internet work.
# Builds the NexaCore image, pulls Qdrant, and saves both into one .tar file that Ubuntu (WSL) can load offline.
#
# Usage (from the project folder, e.g. C:\nexacore-rag):
#   powershell -ExecutionPolicy Bypass -File scripts\windows_build_images.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "==== 1/4 Checking Docker"
docker version

Write-Host "==== 2/4 Building nexacore-rag:latest (15 to 25 minutes the first time)"
docker build -t nexacore-rag:latest .

Write-Host "==== 3/4 Pulling Qdrant"
docker pull qdrant/qdrant:latest

Write-Host "==== 4/4 Saving images to docker-images\nexacore-images.tar"
New-Item -ItemType Directory -Force docker-images | Out-Null
docker save -o docker-images\nexacore-images.tar nexacore-rag:latest qdrant/qdrant:latest
Get-Item docker-images\nexacore-images.tar | Select-Object FullName, @{n="SizeGB";e={[math]::Round($_.Length/1GB,2)}}

Write-Host ""
Write-Host "Done. In Ubuntu run:  bash scripts/wsl_load_images.sh"
