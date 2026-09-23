param(
    [string]$ResourceGroup = "rg-zava-demo",
    [string]$ServerName = ""
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🚀 STARTING ZAVA CLOUD DEMO ENVIRONMENT" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

# Auto-detect PostgreSQL server if not passed
if (-not $ServerName) {
    $ServerName = az postgres flexible-server list --resource-group $ResourceGroup --query "[0].name" -o tsv
}

if (-not $ServerName) {
    Write-Host "❌ No PostgreSQL server found in resource group '$ResourceGroup'." -ForegroundColor Red
    exit 1
}

Write-Host ">> Starting PostgreSQL Flexible Server: $ServerName ..." -ForegroundColor Yellow
az postgres flexible-server start --resource-group $ResourceGroup --name $ServerName

# Retrieve Container App FQDN
$AppUrl = az containerapp list --resource-group $ResourceGroup --query "[0].properties.configuration.ingress.fqdn" -o tsv

Write-Host ""
Write-Host "✅ DEMO IS LIVE AND READY FOR PRESENTATION!" -ForegroundColor Green
Write-Host "👉 Public URL: https://$AppUrl" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
