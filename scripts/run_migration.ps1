param(
    [string]$Message = $(Read-Host 'Migration message (e.g. "add is_verified to users")')
)

Write-Host "Running Alembic autogenerate migration with message: '$Message'"

try {
    # Run alembic revision --autogenerate and capture output
    $output = & alembic revision --autogenerate -m $Message 2>&1
} catch {
    Write-Error "Failed to run 'alembic revision'. Make sure your virtualenv is activated and alembic is installed.`n$_"
    exit 2
}

Write-Host $output

# Try to extract the generated filename from alembic output
$genPath = $null
if ($output -match "Generating\s+([^\s]+alembic[\\/][vV]ersions[\\/][^\s]+)\s+\.\.\.\s+done") {
    $genPath = $Matches[1]
}

if (-not $genPath) {
    # Fallback: take the most recently modified file in alembic/versions
    $verDir = Join-Path $PSScriptRoot '..\alembic\versions' | Resolve-Path -ErrorAction SilentlyContinue
    if (-not $verDir) { $verDir = Join-Path (Get-Location) 'alembic\versions' }
    $latest = Get-ChildItem -Path $verDir -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latest) { $genPath = $latest.FullName }
}

if (-not $genPath) {
    Write-Error "Could not determine generated migration file path. See alembic output above."
    exit 3
}

Write-Host "Generated migration file: $genPath"

# Ensure the generated file contains Alembic revision identifiers. If not, inject them.
$content = Get-Content -Raw -Encoding UTF8 -Path $genPath
if ($content -notmatch "revision\s*=") {
    Write-Host "Migration file is missing 'revision' metadata. Injecting header based on filename..."

    # derive revision id from filename (first token before underscore)
    $fileName = [System.IO.Path]::GetFileName($genPath)
    $rev = ($fileName -split '_')[0]

    # try to pick a sensible down_revision: the most recently modified other migration that contains a revision variable
    $parentDir = Split-Path $genPath -Parent
    $others = Get-ChildItem -Path $parentDir -File |
              Where-Object { $_.FullName -ne $genPath } |
              Sort-Object LastWriteTime -Descending

    $down_rev = $null
    foreach ($f in $others) {
        $c = Get-Content -Raw -Encoding UTF8 -Path $f.FullName
        if ($c -match "revision\s*=\s*'([^']+)'") { $down_rev = $Matches[1]; break }
    }

    if (-not $down_rev) { $down_rev = $null }

    if ($down_rev) { $down_line = "down_revision = '$down_rev'" } else { $down_line = 'down_revision = None' }

    $header = "# revision identifiers, used by Alembic." + "`n"
    $header += "revision = '$rev'`n"
    $header += "$down_line`n"
    $header += "branch_labels = None`n"
    $header += "depends_on = None`n"

    # Insert header after leading docstring if present, else prepend
    if ($content -match '^(?s)\s*"""[\s\S]*?"""') {
        $doc = $Matches[0]
        $rest = $content.Substring($doc.Length)
        $newContent = $doc + "`n" + $header + "`n" + $rest
    } else {
        $newContent = $header + "`n" + $content
    }

    try {
        Set-Content -Path $genPath -Value $newContent -Encoding UTF8
        Write-Host "Injected Alembic metadata into $genPath"
    } catch {
        Write-Error "Failed to write updated migration file: $_"
        exit 4
    }
} else {
    Write-Host "Migration file already contains revision metadata. No changes needed."
}

Write-Host "Running: alembic upgrade head"
try {
    & alembic upgrade head
} catch {
    Write-Error "'alembic upgrade head' failed. Please inspect the alembic output above and run the command manually if needed.`n$_"
    exit 5
}

Write-Host "Migration generation and upgrade finished. Check alembic/versions and your DB to confirm changes."
