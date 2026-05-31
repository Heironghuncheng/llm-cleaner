$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$gitDir = Join-Path $repoRoot ".git"

if (-not (Test-Path -LiteralPath $gitDir)) {
    throw "Expected a git repository at $repoRoot"
}

$pathsToRemove = @(
    (Join-Path $repoRoot "scan"),
    (Join-Path $repoRoot ".scan_old"),
    (Join-Path $repoRoot ".agents\skills"),
    (Join-Path $repoRoot ".claude\skills")
)

foreach ($path in $pathsToRemove) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
        Write-Host "Removed $path"
    }
}

Get-ChildItem -LiteralPath $repoRoot -Filter "report-*.md" -File | ForEach-Object {
    Remove-Item -LiteralPath $_.FullName -Force
    Write-Host "Removed $($_.FullName)"
}

$localClaudeSettings = Join-Path $repoRoot ".claude\settings.local.json"
if (Test-Path -LiteralPath $localClaudeSettings) {
    Remove-Item -LiteralPath $localClaudeSettings -Force
    Write-Host "Removed $localClaudeSettings"
}

foreach ($container in @((Join-Path $repoRoot ".agents"), (Join-Path $repoRoot ".claude"))) {
    if ((Test-Path -LiteralPath $container) -and -not (Get-ChildItem -LiteralPath $container -Force)) {
        Remove-Item -LiteralPath $container -Force
        Write-Host "Removed empty $container"
    }
}

$factsTemplate = Join-Path $repoRoot "facts.template.md"
$factsPath = Join-Path $repoRoot "facts.md"

if (-not (Test-Path -LiteralPath $factsTemplate)) {
    throw "Missing facts template: $factsTemplate"
}

Copy-Item -LiteralPath $factsTemplate -Destination $factsPath -Force
Write-Host "Reset $factsPath from template"
Write-Host "Repository reset to an unused state."
