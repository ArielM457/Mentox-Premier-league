<#
.SYNOPSIS
Apaga o borra el despliegue de la analítica para no consumir créditos.

.DESCRIPTION
-StopOnly deja en cero réplicas la API, la interfaz y el procesador. Event Hubs,
el registro y Storage siguen cobrando: es una pausa corta, no un ahorro total.

Sin -StopOnly borra el grupo de recursos completo. Pide escribir su nombre para
confirmar, porque la eliminación no se puede deshacer. Los datos de Supabase no
se tocan.

.EXAMPLE
./infra/azure/remove-analytics.ps1 -ResourceGroup rg-mentox-analytics -StopOnly

.EXAMPLE
./infra/azure/remove-analytics.ps1 -ResourceGroup rg-mentox-analytics
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $ResourceGroup,

    [switch] $StopOnly
)

$ErrorActionPreference = 'Stop'

function Invoke-Az {
    $output = & az @args
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI falló: az $($args[0]) $($args[1]) (código $LASTEXITCODE)"
    }
    return $output
}

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw 'Falta Azure CLI.'
}
if ((Invoke-Az group exists --name $ResourceGroup) -ne 'true') {
    Write-Host "El grupo $ResourceGroup no existe."
    exit 0
}

if ($StopOnly) {
    $apps = @(Invoke-Az containerapp list --resource-group $ResourceGroup --query '[].name' --output tsv)
    foreach ($app in $apps) {
        Write-Host "Apagando $app..."
        Invoke-Az containerapp update --name $app --resource-group $ResourceGroup --min-replicas 0 --max-replicas 1 --output none | Out-Null
    }
    Write-Host 'Aplicaciones en cero réplicas. Event Hubs, el registro y Storage siguen activos.'
    exit 0
}

Write-Host "Recursos en ${ResourceGroup}:"
Invoke-Az resource list --resource-group $ResourceGroup --query '[].{nombre:name, tipo:type}' --output table
$typed = Read-Host "Para borrar TODO el grupo, escriba su nombre ($ResourceGroup)"
if ($typed -ne $ResourceGroup) {
    Write-Host 'El nombre no coincide. No se borró nada.'
    exit 1
}
Invoke-Az group delete --name $ResourceGroup --yes --no-wait | Out-Null
Write-Host "Borrado iniciado. Compruebe con: az group exists --name $ResourceGroup"
