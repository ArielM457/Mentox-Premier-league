$ErrorActionPreference = 'Stop'

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$environmentFile = Join-Path $repositoryRoot 'apps/backend/.env'

if (-not (Test-Path -LiteralPath $environmentFile)) {
    throw 'No existe apps/backend/.env.'
}

$values = @{}
foreach ($line in Get-Content -LiteralPath $environmentFile) {
    if ($line -match '^\s*([A-Z][A-Z0-9_]*)=(.*)$') {
        $values[$matches[1]] = $matches[2].Trim().Trim('"').Trim("'")
    }
}

$required = 'SUPABASE_URL', 'SUPABASE_SECRET_KEY', 'SUPABASE_DB_PASSWORD'
$missing = $required | Where-Object { -not $values[$_] }
if ($missing) {
    throw "Completa estas variables en apps/backend/.env: $($missing -join ', ')"
}

$projectRef = $values['SUPABASE_PROJECT_REF']
if (-not $projectRef) {
    $supabaseUri = [Uri]$values['SUPABASE_URL']
    if ($supabaseUri.Host -notmatch '^([a-z0-9]{20})\.supabase\.co$') {
        throw 'No se pudo obtener SUPABASE_PROJECT_REF desde SUPABASE_URL. Agrégalo manualmente al .env.'
    }
    $projectRef = $matches[1]
}

$env:SUPABASE_DB_PASSWORD = $values['SUPABASE_DB_PASSWORD']

Push-Location $repositoryRoot
try {
    npx --yes supabase@latest link --project-ref $projectRef
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo enlazar el proyecto de Supabase.' }

    npx --yes supabase@latest db push --linked
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo aplicar la migración de Supabase.' }

    & (Join-Path $PSScriptRoot 'test-supabase-connection.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'La migración terminó, pero la Data API no aceptó la conexión.' }

    Write-Host 'Supabase enlazado, migración aplicada y Data API verificada.'
    Write-Host 'Ya puedes cambiar SUPABASE_ENABLED=true y reiniciar el backend.'
}
finally {
    Pop-Location
    Remove-Item Env:SUPABASE_DB_PASSWORD -ErrorAction SilentlyContinue
}
