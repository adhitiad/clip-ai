# Backup PostgreSQL (clip_ai) ke file .dump.
# Jalankan dari root repo:
#   powershell -File scripts/backup_db.ps1
#   powershell -File scripts/backup_db.ps1 -OutputFile backups/clip_ai.dump

param(
    [string] $DatabaseUrl = $env:DATABASE_URL,
    [string] $OutputFile = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'db_url.ps1')

$db = Resolve-DbUrl -Url $DatabaseUrl
if (-not $OutputFile) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $dir = Join-Path (Get-Location) 'backups'
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $OutputFile = Join-Path $dir "$($db.Database)_$stamp.dump"
}

$OutputFile = [IO.Path]::GetFullPath($OutputFile)
New-Item -ItemType Directory -Force -Path (Split-Path $OutputFile -Parent) | Out-Null

$env:PGPASSWORD = $db.Password
try {
    & pg_dump -h $db.Host -p $db.Port -U $db.User -d $db.Database `
        --format=custom --no-owner --no-privileges --file=$OutputFile
    if ($LASTEXITCODE -ne 0) { throw "pg_dump gagal (exit $LASTEXITCODE)" }
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

$item = Get-Item $OutputFile
Write-Output "Backup berhasil: $($item.FullName) ($($item.Length) bytes)"
