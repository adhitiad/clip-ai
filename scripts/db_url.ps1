# Helper bersama: parse DATABASE_URL menjadi komponen pg_dump/pg_restore.
# Jangan pernah menampilkan password.

function Resolve-DbUrl {
    param([string] $Url)

    if ([string]::IsNullOrWhiteSpace($Url)) {
        throw 'DATABASE_URL kosong. Set di .env atau parameter -DatabaseUrl.'
    }

    $uri = [Uri] $Url
    $user = [Uri]::UnescapeDataString($uri.UserInfo.Split(':', 2)[0])
    $password = ''
    if ($uri.UserInfo.Contains(':')) {
        $password = [Uri]::UnescapeDataString($uri.UserInfo.Split(':', 2)[1])
    }
    $database = $uri.AbsolutePath.TrimStart('/')
    if ([string]::IsNullOrWhiteSpace($database)) {
        throw 'DATABASE_URL tidak menyertakan nama database.'
    }

    return @{
        Host     = $uri.Host
        Port     = if ($uri.IsDefaultPort) { 5432 } else { $uri.Port }
        User     = $user
        Password = $password
        Database = $database
        Url      = $Url
    }
}
