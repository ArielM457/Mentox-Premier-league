$ErrorActionPreference = 'Stop'

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$environmentFile = Join-Path $repositoryRoot 'apps/backend/.env'

if (-not (Test-Path -LiteralPath $environmentFile)) {
    throw 'No existe apps/backend/.env.'
}

$values = @{}
foreach ($line in Get-Content -LiteralPath $environmentFile) {
    if ($line -match '^\s*([A-Z][A-Z0-9_]*)=(.*)$') {
        $values[$matches[1]] = $matches[2].Trim()
    }
}

$required = 'SUPABASE_URL', 'SUPABASE_SECRET_KEY', 'SUPABASE_PROJECT_REF', 'SUPABASE_DB_PASSWORD'
$missing = $required | Where-Object { -not $values[$_] }
if ($missing) {
    throw "Completa estas variables en apps/backend/.env: $($missing -join ', ')"
}

$env:SUPABASE_DB_PASSWORD = $values['SUPABASE_DB_PASSWORD']

Push-Location $repositoryRoot
try {
    npx --yes supabase@latest link --project-ref $values['SUPABASE_PROJECT_REF']
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo enlazar el proyecto de Supabase.' }

    npx --yes supabase@latest db push --linked
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo aplicar la migración de Supabase.' }

    Write-Host 'Supabase enlazado y migración aplicada. Cambia SUPABASE_ENABLED=true para activar las escrituras.'
}
finally {
    Pop-Location
    Remove-Item Env:SUPABASE_DB_PASSWORD -ErrorAction SilentlyContinue
}
