# scan-packages.ps1
# Query all package managers and output as JSON to stdout.
# Used by packages.py as a fallback or for winget/choco which need PowerShell encoding.

$ErrorActionPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$result = @{}

# Scoop
try {
    $scoopList = scoop list 2>$null | Select-Object -Skip 3 | ForEach-Object {
        ($_ -split '\s+')[0]
    } | Where-Object { $_ -and $_ -ne "Name" }
    $result.scoop = @($scoopList)
} catch {
    $result.scoop = @()
}

# Winget
try {
    $wingetList = winget list --accept-source-agreements 2>$null | Out-String
    $names = @()
    foreach ($line in ($wingetList -split "`n")) {
        $line = $line.Trim()
        if (-not $line -or $line -match "^-+$" -or $line -match "^Name\s+") { continue }
        # Extract first part as name (before version-like pattern)
        $parts = $line -split '\s{2,}'
        if ($parts.Count -ge 1 -and $parts[0]) {
            $names += $parts[0].Trim()
        }
    }
    $result.winget = $names
} catch {
    $result.winget = @()
}

# Chocolatey
try {
    $chocoList = choco list 2>$null | ForEach-Object {
        $parts = $_ -split '\s+'
        if ($parts.Count -ge 1 -and $parts[0] -and $parts[0] -notmatch "^Chocolatey" -and $parts[0] -notmatch "^packages") {
            $parts[0]
        }
    }
    $result.choco = @($chocoList)
} catch {
    $result.choco = @()
}

# Mise
try {
    $miseList = mise list 2>$null | ForEach-Object {
        ($_ -split '\s+')[0]
    } | Where-Object { $_ }
    $result.mise = @($miseList)
} catch {
    $result.mise = @()
}

# UV tool
try {
    $uvList = uv tool list 2>$null | ForEach-Object {
        $line = $_.Trim()
        if ($line -and $line -notmatch "^-") {
            ($line -split '\s+')[0]
        }
    } | Where-Object { $_ }
    $result.uv_tool = @($uvList)
} catch {
    $result.uv_tool = @()
}

$result | ConvertTo-Json -Depth 3
