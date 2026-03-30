# Script PowerShell para limpar cache Python no Windows Server
# Execute este script no diretório raiz do projeto api_nfe
# Para executar: powershell -ExecutionPolicy Bypass -File limpar_cache_windows.ps1

Write-Host "========================================"
Write-Host "Limpando cache Python..." -ForegroundColor Cyan
Write-Host "========================================"
Write-Host ""

# Obter diretório atual
$projectDir = Get-Location

# Contar itens removidos
$pycRemoved = 0
$pycacheRemoved = 0

# 1. Remover arquivos .pyc
Write-Host "[1/4] Removendo arquivos .pyc..." -ForegroundColor Yellow
Get-ChildItem -Path $projectDir -Filter *.pyc -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        Remove-Item $_.FullName -Force -ErrorAction Stop
        $pycRemoved++
        Write-Host "  Removido: $($_.FullName)" -ForegroundColor Gray
    }
    catch {
        Write-Host "  ERRO ao remover: $($_.FullName)" -ForegroundColor Red
    }
}
Write-Host "OK - $pycRemoved arquivos .pyc removidos" -ForegroundColor Green
Write-Host ""

# 2. Remover diretórios __pycache__
Write-Host "[2/4] Removendo diretórios __pycache__..." -ForegroundColor Yellow
Get-ChildItem -Path $projectDir -Filter __pycache__ -Directory -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        Remove-Item $_.FullName -Recurse -Force -ErrorAction Stop
        $pycacheRemoved++
        Write-Host "  Removido: $($_.FullName)" -ForegroundColor Gray
    }
    catch {
        Write-Host "  AVISO: Não foi possível remover: $($_.FullName)" -ForegroundColor Red
    }
}
Write-Host "OK - $pycacheRemoved diretórios __pycache__ removidos" -ForegroundColor Green
Write-Host ""

# 3. Limpar cache específico de models
Write-Host "[3/4] Limpando cache de models..." -ForegroundColor Yellow
$modelsCache = Join-Path $projectDir "models\__pycache__"
if (Test-Path $modelsCache) {
    Remove-Item $modelsCache -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "OK - Cache de models removido" -ForegroundColor Green
} else {
    Write-Host "OK - Nenhum cache em models" -ForegroundColor Green
}
Write-Host ""

# 4. Limpar cache específico de auth
Write-Host "[4/4] Limpando cache de auth..." -ForegroundColor Yellow
$authCache = Join-Path $projectDir "auth\__pycache__"
if (Test-Path $authCache) {
    Remove-Item $authCache -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "OK - Cache de auth removido" -ForegroundColor Green
} else {
    Write-Host "OK - Nenhum cache em auth" -ForegroundColor Green
}
Write-Host ""

# Resumo
Write-Host "========================================"
Write-Host "Cache limpo com sucesso!" -ForegroundColor Green
Write-Host "========================================"
Write-Host ""
Write-Host "Resumo:" -ForegroundColor Cyan
Write-Host "  - Arquivos .pyc removidos: $pycRemoved"
Write-Host "  - Diretórios __pycache__ removidos: $pycacheRemoved"
Write-Host ""

# Instruções para reiniciar serviço
Write-Host "IMPORTANTE: Reinicie o serviço Flask:" -ForegroundColor Yellow
Write-Host "  Opção 1 (Command Prompt como Admin):"
Write-Host "    net stop api_nfe_principal && net start api_nfe_principal"
Write-Host ""
Write-Host "  Opção 2 (PowerShell como Admin):"
Write-Host "    Restart-Service api_nfe_principal"
Write-Host ""
Write-Host "  Opção 3 (Services.msc):"
Write-Host "    1. Abra Services (services.msc)"
Write-Host "    2. Localize 'api_nfe_principal'"
Write-Host "    3. Clique com botão direito > Restart"
Write-Host ""

# Pausa para ler o resultado
Write-Host "Pressione qualquer tecla para continuar..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
