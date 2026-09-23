param(
    [string]$ResourceGroup = "rg-zava-demo",
    [string]$ServerName = ""
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "💤 PUTTING ZAVA CLOUD ENVIRONMENT TO SLEEP ($0 COMPUTE)" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# Auto-detect PostgreSQL server if not passed
if (-not $ServerName) {
    $ServerName = az postgres flexible-server list --resource-group $ResourceGroup --query "[0].name" -o tsv
}

if (-not $ServerName) {
    Write-Host "❌ No PostgreSQL server found in resource group '$ResourceGroup'." -ForegroundColor Red
    exit 1
}

Write-Host ">> Stopping PostgreSQL Flexible Server: $ServerName ..." -ForegroundColor Yellow
az postgres flexible-server stop --resource-group $ResourceGroup --name $ServerName

Write-Host ""
Write-Host "✅ PostgreSQL server stopped. Container App will sleep automatically." -ForegroundColor Green
Write-Host "💰 Cloud compute billing has stopped ($0 compute)." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
