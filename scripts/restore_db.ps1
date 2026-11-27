# Restore PostgreSQL dari file .dump ke database TUJUAN.
# WAJIB konfirmasi bila target bukan DB uji. Contoh:
#   powershell -File scripts/restore_db.ps1 -DumpFile backups/clip_ai.dump `
#       -TargetUrl postgresql://postgres:password@localhost:5432/clip_ai_restore_test

param(
    [Parameter(Mandatory = $true)] [string] $DumpFile,
    [Parameter(Mandatory = $true)] [string] $TargetUrl,
    [switch] $Force
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'db_url.ps1')

$dump = [IO.Path]::GetFullPath($DumpFile)
if (-not (Test-Path $dump)) { throw "File dump tidak ditemukan: $dump" }

$db = Resolve-DbUrl -Url $TargetUrl
if ($db.Database -notlike '*restore*' -and -not $Force) {
    throw "Target '$($db.Database)' bukan DB uji. Tambahkan -Force jika Anda yakin."
}

$env:PGPASSWORD = $db.Password
try {
    # pastikan DB target ada (menggunakan DB postgres sebagai fallback)
    $admin = Resolve-DbUrl -Url ($TargetUrl -replace "/$($db.Database)", '/postgres')
    $env:PGPASSWORD = $admin.Password
    $exists = & psql -h $admin.Host -p $admin.Port -U $admin.User -d postgres -Atc `
        "SELECT 1 FROM pg_database WHERE datname='$($db.Database)'" 2>$null
    if ($exists -ne '1') {
        & createdb -h $admin.Host -p $admin.Port -U $admin.User $db.Database
        if ($LASTEXITCODE -ne 0) { throw "createdb gagal (exit $LASTEXITCODE)" }
    }

    $env:PGPASSWORD = $db.Password
    & pg_restore -h $db.Host -p $db.Port -U $db.User -d $db.Database `
        --clean --if-exists --no-owner --no-privileges $dump
    if ($LASTEXITCODE -ne 0) { throw "pg_restore gagal (exit $LASTEXITCODE)" }
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Output "Restore berhasil ke database '$($db.Database)'."
