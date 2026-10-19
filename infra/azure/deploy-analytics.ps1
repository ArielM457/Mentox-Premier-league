<#
.SYNOPSIS
Despliega en Azure todos los servicios de la analítica (Persona 2).

.DESCRIPTION
Crea o actualiza, en un grupo de recursos:
  - Event Hubs (match-events y match-insights) y Blob Storage (main.bicep y analytics.bicep).
  - Log Analytics, Azure Container Registry, una identidad administrada y sus roles.
  - Un entorno de Azure Container Apps con la API, la interfaz, el procesador continuo
    y el trabajo que repite un partido de Supabase en Event Hubs.

Pasos: comprueba herramientas y región, despliega la infraestructura (fase 1),
construye y publica las imágenes, opcionalmente carga los datos ficticios en
Supabase y despliega las aplicaciones (fase 2).

La cadena de Supabase se lee de $env:SUPABASE_DB_URL o se pide sin mostrarla.
Viaja a Azure en un archivo temporal que se borra al terminar; nunca se imprime.

.EXAMPLE
$env:SUPABASE_DB_URL = Read-Host 'Cadena del Session pooler de Supabase'
./infra/azure/deploy-analytics.ps1 -ResourceGroup rg-mentox-analytics -Location eastus2 -SeedDatabase

.EXAMPLE
./infra/azure/deploy-analytics.ps1 -ResourceGroup rg-mentox-analytics -WhatIf
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $ResourceGroup,

    [string] $Location = 'eastus2',

    [ValidatePattern('^[a-z0-9]{3,9}$')]
    [string] $Prefix = 'mentoxp2',

    [ValidateSet('dev', 'test', 'demo')]
    [string] $Environment = 'demo',

    # Etiqueta de las imágenes. Por defecto: commit actual y fecha.
    [string] $ImageTag,

    # Partido que repite el trabajo replay y su velocidad (1 = tiempo real).
    [string] $ReplayMatchId = 'synthetic-analytics-001',
    [ValidateRange(1, 32)]
    [int] $ReplaySpeed = 8,

    # Carga el esquema y los datos ficticios en Supabase antes de la fase 2.
    [switch] $SeedDatabase,

    # No despliega la interfaz.
    [switch] $SkipWeb,

    # Deja encendido el procesador continuo (cuesta cómputo mientras esté encendido).
    [switch] $WorkerOn,

    # Mantiene una réplica de la API (sin arranque en frío, útil el día de la demo).
    [switch] $ApiAlwaysOn,

    # Construye las imágenes en Azure (ACR Tasks) en lugar de Docker local.
    [switch] $UseAcrBuild,

    # Solo la fase 1: infraestructura, sin imágenes ni aplicaciones.
    [switch] $InfraOnly,

    # Muestra qué cambiaría la fase 1. Solo registra proveedores y crea el grupo vacío,
    # que no tienen costo.
    [switch] $WhatIf,

    # No pide confirmación.
    [switch] $Yes
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Template = Join-Path $PSScriptRoot 'analytics-platform.bicep'
$Providers = @(
    'Microsoft.App', 'Microsoft.OperationalInsights', 'Microsoft.ContainerRegistry',
    'Microsoft.ManagedIdentity', 'Microsoft.EventHub', 'Microsoft.Storage'
)

function Write-Step([string] $Text) {
    Write-Host ''
    Write-Host "==> $Text" -ForegroundColor Cyan
}

function Invoke-Az {
    # Ejecuta Azure CLI y falla si devuelve un código distinto de cero.
    $output = & az @args
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI falló: az $($args[0]) $($args[1]) (código $LASTEXITCODE)"
    }
    return $output
}

function Test-AzCommand {
    # Devuelve si el comando tuvo éxito, sin mostrar su salida ni detener el script.
    $ErrorActionPreference = 'Continue'
    & az @args *> $null
    return ($LASTEXITCODE -eq 0)
}

function Get-AzQuiet {
    # Salida de un comando opcional; vacía si falla.
    $ErrorActionPreference = 'Continue'
    $output = & az @args 2> $null
    if ($LASTEXITCODE -ne 0 -or -not $output) { return }
    return $output
}

function Test-Docker {
    $ErrorActionPreference = 'Continue'
    & docker info --format '{{.ServerVersion}}' *> $null
    return ($LASTEXITCODE -eq 0)
}

function Invoke-Native([string] $Command, [string[]] $Arguments) {
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command $($Arguments[0]) falló (código $LASTEXITCODE)"
    }
}

function ConvertFrom-AzJson($Lines) {
    return ($Lines -join "`n") | ConvertFrom-Json
}

function Get-OutputValue($Outputs, [string] $Name) {
    return $Outputs.$Name.value
}

function Write-ParameterFile([hashtable] $Values) {
    $parameters = @{}
    foreach ($key in $Values.Keys) {
        $parameters[$key] = @{ value = $Values[$key] }
    }
    $document = @{
        '$schema'      = 'https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#'
        contentVersion = '1.0.0.0'
        parameters     = $parameters
    }
    # Puede contener la cadena de Supabase: va en una carpeta privada. En Windows, la
    # carpeta temporal del usuario ya es privada; en Linux y macOS se limita a 700/600
    # antes de escribir el secreto.
    $directory = Join-Path ([IO.Path]::GetTempPath()) ("mentox-analytics-{0}" -f [guid]::NewGuid())
    New-Item -ItemType Directory -Path $directory | Out-Null
    $path = Join-Path $directory 'parameters.json'
    New-Item -ItemType File -Path $path | Out-Null
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        Invoke-Native 'chmod' @('700', $directory)
        Invoke-Native 'chmod' @('600', $path)
    }
    $json = $document | ConvertTo-Json -Depth 6
    [IO.File]::WriteAllText($path, $json, (New-Object System.Text.UTF8Encoding $false))
    return $path
}

function Remove-ParameterFile([string] $Path) {
    Remove-Item (Split-Path -Parent $Path) -Recurse -Force -ErrorAction SilentlyContinue
}

function Get-PlainText([Security.SecureString] $Secure) {
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

function Get-PythonCommand {
    $venv = Join-Path $RepoRoot '.venv\Scripts\python.exe'
    if (Test-Path $venv) { return $venv }
    $venvUnix = Join-Path $RepoRoot '.venv/bin/python'
    if (Test-Path $venvUnix) { return $venvUnix }
    if (Get-Command python -ErrorAction SilentlyContinue) { return 'python' }
    throw 'No se encontró Python. Cree .venv e instale el backend con el extra db.'
}

# ----- 1. Herramientas --------------------------------------------------------
Write-Step 'Comprobando herramientas'
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw 'Falta Azure CLI. En Windows: winget install -e --id Microsoft.AzureCLI (y abra otra terminal).'
}
$useDocker = -not $UseAcrBuild
if ($useDocker -and -not $InfraOnly -and -not $WhatIf) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Falta Docker. Inicie Docker Desktop o use -UseAcrBuild.'
    }
    if (-not (Test-Docker)) {
        throw 'Docker no responde. Inicie Docker Desktop o use -UseAcrBuild.'
    }
}
if (-not (Test-AzCommand bicep version)) {
    Invoke-Az bicep install | Out-Null
}

# ----- 2. Cuenta y suscripción ------------------------------------------------
Write-Step 'Comprobando la sesión de Azure'
if (-not (Test-AzCommand account show --output none)) {
    Write-Host 'No hay sesión. Se abrirá el inicio de sesión de Azure.'
    Invoke-Az login --output none | Out-Null
}
$account = ConvertFrom-AzJson (Invoke-Az account show --output json)
Write-Host ("Suscripción: {0}" -f $account.name)
Write-Host ("Grupo: {0} · Región: {1} · Prefijo: {2} · Entorno: {3}" -f $ResourceGroup, $Location, $Prefix, $Environment)
if (-not $Yes -and -not $WhatIf) {
    $answer = Read-Host '¿Desplegar en esta suscripción? Crea recursos con costo (s/N)'
    if ($answer -notmatch '^(s|si|sí|y|yes)$') {
        Write-Host 'Cancelado.'
        exit 1
    }
}

# Azure for Students limita las regiones permitidas con una política.
$allowed = @(Get-AzQuiet policy assignment list --query '[].parameters.listOfAllowedLocations.value[]' --output tsv)
if ($allowed.Count -gt 0 -and $allowed -notcontains $Location) {
    throw ("La región {0} no está permitida en esta suscripción. Regiones permitidas: {1}" -f $Location, ($allowed -join ', '))
}

# ----- 3. Supabase ------------------------------------------------------------
$databaseUrl = $env:SUPABASE_DB_URL
if (-not $databaseUrl -and -not $Yes -and -not $InfraOnly -and -not $WhatIf) {
    $secure = Read-Host -AsSecureString 'Cadena del Session pooler de Supabase (Enter para usar solo partidos sintéticos)'
    $databaseUrl = Get-PlainText $secure
}
if ($databaseUrl) {
    if ($databaseUrl -notmatch '^postgres(ql)?://') {
        throw 'La cadena de Supabase debe empezar por postgresql://'
    }
    if ($databaseUrl -match '@db\.[a-z0-9]+\.supabase\.co') {
        Write-Warning 'Es la conexión directa (solo IPv6). Container Apps necesita la del Session pooler (pooler.supabase.com).'
    }
    Write-Host 'Supabase: configurado (la cadena no se muestra).'
}
else {
    Write-Host 'Supabase: no configurado. La API usará los partidos sintéticos y no se crea el trabajo replay.'
    if ($SeedDatabase) { throw '-SeedDatabase necesita la cadena de Supabase.' }
}

# ----- 4. Proveedores y grupo -------------------------------------------------
Write-Step 'Registrando proveedores de recursos'
foreach ($provider in $Providers) {
    $state = Invoke-Az provider show --namespace $provider --query registrationState --output tsv
    if ($state -ne 'Registered') {
        Write-Host "Registrando $provider (puede tardar unos minutos)..."
        Invoke-Az provider register --namespace $provider --wait | Out-Null
    }
}

Write-Step "Grupo de recursos $ResourceGroup"
$groupExists = Invoke-Az group exists --name $ResourceGroup
if ($groupExists -ne 'true') {
    Invoke-Az group create --name $ResourceGroup --location $Location --tags project=mentox-premier-league workload=analytics --output none | Out-Null
}

# Un entorno creado sin modo explícito queda en Express, que no admite el trabajo
# replay y apaga lo que no recibe HTTP. El modo no se puede cambiar: se recrea con
# sus aplicaciones, que no guardan datos propios.
$environmentName = "cae-$Prefix-$Environment"
$subscriptionId = $account.id
$environmentUrl = "https://management.azure.com/subscriptions/$subscriptionId/resourceGroups/$ResourceGroup" +
    "/providers/Microsoft.App/managedEnvironments/${environmentName}?api-version=2026-07-01"
$existing = Get-AzQuiet rest --method get --url $environmentUrl --output json
if ($existing) {
    $properties = (ConvertFrom-AzJson $existing).properties
    $mode = $null
    if ($properties.PSObject.Properties['environmentMode']) { $mode = $properties.environmentMode }
    if ($mode -eq 'Express') {
        Write-Warning "El entorno $environmentName está en modo Express: no admite el trabajo replay y puede apagar el procesador."
        if ($WhatIf) {
            Write-Host 'La vista previa no lo cambia. El despliegue real lo recreará en modo WorkloadProfiles.'
        }
        else {
            if (-not $Yes) {
                $answer = Read-Host "¿Borrar y recrear $environmentName con sus aplicaciones? (s/N)"
                if ($answer -notmatch '^(s|si|sí|y|yes)$') {
                    Write-Host 'Cancelado.'
                    exit 1
                }
            }
            Write-Step "Recreando $environmentName"
            $query = "[?ends_with(properties.managedEnvironmentId, '/$environmentName')].name"
            foreach ($app in @(Get-AzQuiet containerapp list --resource-group $ResourceGroup --query $query --output tsv)) {
                Write-Host "Borrando la aplicación $app..."
                Invoke-Az containerapp delete --name $app --resource-group $ResourceGroup --yes --output none | Out-Null
            }
            $jobQuery = "[?ends_with(properties.environmentId, '/$environmentName')].name"
            foreach ($job in @(Get-AzQuiet containerapp job list --resource-group $ResourceGroup --query $jobQuery --output tsv)) {
                Write-Host "Borrando el trabajo $job..."
                Invoke-Az containerapp job delete --name $job --resource-group $ResourceGroup --yes --output none | Out-Null
            }
            Write-Host "Borrando el entorno $environmentName (tarda unos minutos)..."
            Invoke-Az containerapp env delete --name $environmentName --resource-group $ResourceGroup --yes --output none | Out-Null
        }
    }
}

$baseParameters = @{
    projectPrefix   = $Prefix
    environmentName = $Environment
    location        = $Location
}

# ----- 5. Fase 1: infraestructura ---------------------------------------------
if ($WhatIf) {
    Write-Step 'What-if de la fase 1 (no crea nada)'
    $file = Write-ParameterFile ($baseParameters + @{ deployApps = $false })
    try {
        Invoke-Native 'az' @('deployment', 'group', 'what-if', '--resource-group', $ResourceGroup,
            '--template-file', $Template, '--parameters', "@$file")
    }
    finally {
        Remove-ParameterFile $file
    }
    exit 0
}

Write-Step 'Fase 1: Event Hubs, Storage, registro, identidad y entorno de Container Apps'
$file = Write-ParameterFile ($baseParameters + @{ deployApps = $false })
try {
    $infra = ConvertFrom-AzJson (Invoke-Az deployment group create --name 'mentox-analytics-infra' `
            --resource-group $ResourceGroup --template-file $Template --parameters "@$file" `
            --query properties.outputs --output json)
}
finally {
    Remove-ParameterFile $file
}
$registryName = Get-OutputValue $infra 'registryName'
$loginServer = Get-OutputValue $infra 'registryLoginServer'
Write-Host "Registro: $loginServer"

if ($InfraOnly) {
    Write-Host 'Fase 1 terminada (-InfraOnly).'
    exit 0
}

# ----- 6. Imágenes ------------------------------------------------------------
if (-not $ImageTag) {
    $commit = $null
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $ErrorActionPreference = 'Continue'
        $commit = (& git -C $RepoRoot rev-parse --short HEAD 2> $null)
        $ErrorActionPreference = 'Stop'
    }
    if (-not $commit) { $commit = 'local' }
    $ImageTag = '{0}-{1}' -f $commit, (Get-Date -Format 'yyyyMMddHHmmss')
}
$apiImage = "$loginServer/match-intelligence-api:$ImageTag"
$webImage = "$loginServer/match-intelligence-web:$ImageTag"
$builds = @(@{ Image = $apiImage; Name = "match-intelligence-api:$ImageTag"; Context = (Join-Path $RepoRoot 'apps/backend') })
if (-not $SkipWeb) {
    $builds += @{ Image = $webImage; Name = "match-intelligence-web:$ImageTag"; Context = (Join-Path $RepoRoot 'apps/frontend') }
}

Write-Step "Construyendo y publicando imágenes ($ImageTag)"
if ($useDocker) {
    Invoke-Az acr login --name $registryName | Out-Null
}
foreach ($build in $builds) {
    if ($useDocker) {
        Invoke-Native 'docker' @('build', '--platform', 'linux/amd64', '--tag', $build.Image, $build.Context)
        Invoke-Native 'docker' @('push', $build.Image)
    }
    else {
        # Algunas suscripciones de estudiante no permiten ACR Tasks; en ese caso use Docker.
        Invoke-Native 'az' @('acr', 'build', '--registry', $registryName, '--image', $build.Name,
            '--platform', 'linux/amd64', $build.Context)
    }
}

# ----- 7. Datos ficticios -----------------------------------------------------
if ($SeedDatabase) {
    Write-Step 'Cargando el esquema y los datos ficticios en Supabase'
    $python = Get-PythonCommand
    $previous = $env:SUPABASE_DB_URL
    $env:SUPABASE_DB_URL = $databaseUrl
    try {
        Invoke-Native $python @((Join-Path $RepoRoot 'apps/backend/scripts/supabase_seed.py'), '--schema')
    }
    finally {
        $env:SUPABASE_DB_URL = $previous
    }
}

# ----- 8. Fase 2: aplicaciones -------------------------------------------------
Write-Step 'Fase 2: API, interfaz, procesador continuo y trabajo replay'
$appParameters = $baseParameters + @{
    deployApps     = $true
    apiImage       = $apiImage
    webImage       = $(if ($SkipWeb) { '' } else { $webImage })
    supabaseDbUrl  = $(if ($databaseUrl) { $databaseUrl } else { '' })
    apiMinReplicas = $(if ($ApiAlwaysOn) { 1 } else { 0 })
    workerReplicas = $(if ($WorkerOn) { 1 } else { 0 })
    replayMatchId  = $ReplayMatchId
    replaySpeed    = [string] $ReplaySpeed
}
$file = Write-ParameterFile $appParameters
try {
    $apps = ConvertFrom-AzJson (Invoke-Az deployment group create --name 'mentox-analytics-apps' `
            --resource-group $ResourceGroup --template-file $Template --parameters "@$file" `
            --query properties.outputs --output json)
}
finally {
    Remove-ParameterFile $file
}
$apiUrl = Get-OutputValue $apps 'apiUrl'
$webUrl = Get-OutputValue $apps 'webUrl'
$workerApp = Get-OutputValue $apps 'workerAppName'
$replayJob = Get-OutputValue $apps 'replayJobName'

# ----- 9. Verificación ----------------------------------------------------------
Write-Step 'Esperando a la API (el primer arranque puede tardar un par de minutos)'
$loaded = $null
for ($attempt = 1; $attempt -le 18; $attempt++) {
    try {
        $loaded = Invoke-RestMethod -Uri "$apiUrl/api/v1/matches" -TimeoutSec 60
        break
    }
    catch {
        Start-Sleep -Seconds 10
    }
}
if ($null -eq $loaded) {
    Write-Warning "La API todavía no responde. Revise: az containerapp logs show -n $(Get-OutputValue $apps 'apiAppName') -g $ResourceGroup"
}
else {
    Write-Host ('Partidos cargados: {0}' -f (($loaded | ForEach-Object { $_.match_id }) -join ', '))
}

# ----- 10. Resumen ----------------------------------------------------------------
Write-Step 'Listo'
Write-Host "API:        $apiUrl  (documentación en $apiUrl/docs)"
if ($webUrl) { Write-Host "Interfaz:   $webUrl" }
Write-Host "Imágenes:   $ImageTag"
Write-Host ''
Write-Host 'Comandos útiles:'
Write-Host "  Encender el procesador:  az containerapp update -n $workerApp -g $ResourceGroup --min-replicas 1 --max-replicas 1"
Write-Host "  Apagar el procesador:    az containerapp update -n $workerApp -g $ResourceGroup --min-replicas 0 --max-replicas 1"
if ($databaseUrl) {
    Write-Host "  Repetir un partido:      az containerapp job start -n $replayJob -g $ResourceGroup"
}
Write-Host "  Ver registros:           az containerapp logs show -n $workerApp -g $ResourceGroup --follow"
Write-Host "  Borrar todo:             ./infra/azure/remove-analytics.ps1 -ResourceGroup $ResourceGroup"
Write-Host ''
Write-Host 'Costo aproximado: cerca de 1 USD al día con el procesador apagado (Event Hubs Standard y el registro),'
Write-Host 'hasta unos 45 USD al mes con todo encendido. Borre el grupo al terminar la demo para cuidar los créditos.'
