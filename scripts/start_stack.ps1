param(
    [switch]$Build
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir

Push-Location $repoRoot
try {
    $profiles = @(
        "--profile", "ingestion",
        "--profile", "ai_worker",
        "--profile", "analytics",
        "--profile", "dispatcher"
    )
    $composeArgs = $profiles + @("up", "-d")
    if ($Build) {
        $composeArgs += "--build"
    }

    Write-Host "Starting ReSync backend, AI pipeline, and dashboard..."
    & docker compose @composeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "ReSync is starting."
    Write-Host "Dashboard: http://localhost:3000"
    Write-Host "API:       http://localhost:8000"
    Write-Host "HLS:       http://localhost:8888"
    Write-Host ""
    Write-Host "Follow logs with:"
    Write-Host "  docker compose logs -f"
    Write-Host ""
    Write-Host "Rebuild images on demand with:"
    Write-Host "  .\\scripts\\start_stack.cmd -Build"
}
finally {
    Pop-Location
}
