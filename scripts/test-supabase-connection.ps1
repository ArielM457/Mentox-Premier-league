$ErrorActionPreference = 'Stop'

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$environmentFile = Join-Path $repositoryRoot 'apps/backend/.env'

if (-not (Test-Path -LiteralPath $environmentFile)) {
    Write-Error 'No existe apps/backend/.env.'
    exit 1
}

$values = @{}
foreach ($line in Get-Content -LiteralPath $environmentFile) {
    if ($line -match '^\s*([A-Z][A-Z0-9_]*)=(.*)$') {
        $values[$matches[1]] = $matches[2].Trim().Trim('"').Trim("'")
    }
}

$required = 'SUPABASE_URL', 'SUPABASE_SECRET_KEY'
$missing = $required | Where-Object { -not $values[$_] }
if ($missing) {
    Write-Error "Completa estas variables en apps/backend/.env: $($missing -join ', ')"
    exit 1
}

$headers = @{ apikey = $values['SUPABASE_SECRET_KEY'] }
$tables = @(
    'matches',
    'match_events',
    'moments',
    'assistant_messages',
    'match_summaries',
    'community_votes',
    'community_messages',
    'action_callouts'
)
$failed = $false

foreach ($table in $tables) {
    $uri = $values['SUPABASE_URL'].TrimEnd('/') + "/rest/v1/$table?select=*&limit=1"
    try {
        $response = Invoke-WebRequest -Uri $uri -Headers $headers -Method Get -UseBasicParsing
        Write-Host "[OK] $table ($([int]$response.StatusCode))"
    }
    catch {
        $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 'sin respuesta' }
        Write-Host "[ERROR] $table ($status)"
        $failed = $true
    }
}

if ($failed) {
    Write-Error 'Supabase no acepto una o mas consultas. Revisa la URL, la clave secreta y que las migraciones esten aplicadas.'
    exit 1
}

Write-Host 'Conexion de solo lectura verificada. Ninguna clave fue mostrada.'
exit 0
