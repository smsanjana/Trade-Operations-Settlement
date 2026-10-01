# Frontend startup script for Trade Operations & Settlement Console
param(
    [int]$Port = 3000
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$FrontendDir = Join-Path $ProjectRoot "frontend"

Write-Host "Starting Trade Operations & Settlement Frontend on port ${Port}..."

Set-Location $FrontendDir
$env:PORT = $Port
& npm.cmd run dev -- -p $Port
