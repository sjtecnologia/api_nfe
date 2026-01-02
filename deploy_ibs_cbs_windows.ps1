# ============================================================
# DEPLOY IBS/CBS - Windows PowerShell
# ============================================================

Write-Host ""
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  DEPLOY - Atualização Classificações IBS/CBS (Windows)" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

# Detectar diretório do projeto
$ProjectDir = Get-Location

if (-Not (Test-Path "app.py")) {
    if (Test-Path "..\app.py") {
        $ProjectDir = (Get-Item ..).FullName
        Set-Location $ProjectDir
    } else {
        Write-Host "❌ ERRO: Não foi possível detectar o diretório do projeto" -ForegroundColor Red
        Write-Host "Execute este script dentro do diretório api_nfe" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "📁 Diretório do projeto: $ProjectDir" -ForegroundColor Green
Write-Host ""

# Verificar se o arquivo existe
$ArquivoZip = "atualizacao_ibs_cbs_servidor.tar.gz"

if (-Not (Test-Path $ArquivoZip)) {
    Write-Host "❌ ERRO: Arquivo $ArquivoZip não encontrado" -ForegroundColor Red
    Write-Host ""
    Write-Host "Copie o arquivo para este diretório primeiro." -ForegroundColor Yellow
    exit 1
}

Write-Host "📦 Descompactando arquivos..." -ForegroundColor Yellow

# Extrair usando 7-Zip se disponível, senão usar Expand-Archive
$uso7zip = $false

if (Get-Command "7z" -ErrorAction SilentlyContinue) {
    Write-Host "   Usando 7-Zip..." -ForegroundColor Gray
    7z x $ArquivoZip -y | Out-Null
    $uso7zip = $true
} elseif (Get-Command "tar" -ErrorAction SilentlyContinue) {
    Write-Host "   Usando tar (Windows 10+)..." -ForegroundColor Gray
    tar -xzf $ArquivoZip
    $uso7zip = $true
} else {
    Write-Host "⚠️  Nem 7-Zip nem tar encontrados" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "OPÇÃO 1: Instalar 7-Zip (https://www.7-zip.org/)" -ForegroundColor Yellow
    Write-Host "OPÇÃO 2: Usar Windows 10/11 (tem tar nativo)" -ForegroundColor Yellow
    Write-Host "OPÇÃO 3: Extrair manualmente com WinRAR ou outro" -ForegroundColor Yellow
    Write-Host ""
    
    $resposta = Read-Host "Deseja tentar extrair com método alternativo? (S/N)"
    if ($resposta -eq "S" -or $resposta -eq "s") {
        Write-Host "Tentando método alternativo..." -ForegroundColor Yellow
        # Tentar descompactar como se fosse .tar primeiro, depois .gz
        try {
            # Isso pode não funcionar para .tar.gz, mas vamos tentar
            Write-Host "Este arquivo precisa ser extraído manualmente." -ForegroundColor Yellow
            Write-Host "Use 7-Zip, WinRAR ou extraia o .tar.gz em duas etapas." -ForegroundColor Yellow
            exit 1
        } catch {
            Write-Host "❌ Falha ao extrair" -ForegroundColor Red
            exit 1
        }
    } else {
        exit 1
    }
}

Write-Host "✅ Arquivos descompactados" -ForegroundColor Green
Write-Host ""

# Verificar estrutura
Write-Host "📋 Verificando arquivos..." -ForegroundColor Yellow
$ArquivosOK = $true

$arquivosNecessarios = @(
    "scripts\atualizar_ibs_cbs_servidor.py",
    "Documentacao\cClassTrib 2025-12-12.xlsx"
)

foreach ($arquivo in $arquivosNecessarios) {
    if (-Not (Test-Path $arquivo)) {
        Write-Host "❌ Falta: $arquivo" -ForegroundColor Red
        $ArquivosOK = $false
    }
}

if (-Not $ArquivosOK) {
    Write-Host ""
    Write-Host "❌ Alguns arquivos estão faltando. Verifique a extração." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Todos os arquivos presentes" -ForegroundColor Green
Write-Host ""

# Verificar Python
Write-Host "🐍 Verificando Python..." -ForegroundColor Yellow

$pythonCmd = $null
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command "python3" -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
}

if ($null -eq $pythonCmd) {
    Write-Host "❌ Python não encontrado" -ForegroundColor Red
    Write-Host "Instale Python de: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Marque a opção 'Add Python to PATH' durante instalação" -ForegroundColor Yellow
    exit 1
}

$pythonVersion = & $pythonCmd --version
Write-Host "✅ $pythonVersion" -ForegroundColor Green
Write-Host ""

# Verificar dependências
Write-Host "📦 Verificando dependências Python..." -ForegroundColor Yellow

$pandas_ok = & $pythonCmd -c "import pandas" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Pandas não instalado" -ForegroundColor Yellow
    $instalar = Read-Host "Deseja instalar agora? (S/N)"
    
    if ($instalar -eq "S" -or $instalar -eq "s") {
        Write-Host "Instalando dependências..." -ForegroundColor Yellow
        & $pythonCmd -m pip install pandas openpyxl sqlalchemy psycopg2-binary
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Dependências instaladas" -ForegroundColor Green
        } else {
            Write-Host "❌ Erro ao instalar dependências" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "❌ Dependências necessárias não instaladas" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ Dependências OK" -ForegroundColor Green
}

Write-Host ""
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  ✅ DEPLOY CONCLUÍDO" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 Para executar a atualização:" -ForegroundColor White
Write-Host "   $pythonCmd scripts\atualizar_ibs_cbs_servidor.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "📖 Documentação completa:" -ForegroundColor White
Write-Host "   Get-Content scripts\README_ATUALIZACAO_IBS_CBS.md" -ForegroundColor Yellow
Write-Host ""

$executar = Read-Host "Deseja executar a atualização agora? (S/N)"

if ($executar -eq "S" -or $executar -eq "s") {
    Write-Host ""
    & $pythonCmd scripts\atualizar_ibs_cbs_servidor.py
} else {
    Write-Host ""
    Write-Host "OK. Execute quando estiver pronto:" -ForegroundColor Yellow
    Write-Host "   $pythonCmd scripts\atualizar_ibs_cbs_servidor.py" -ForegroundColor Cyan
}
