#!/bin/bash
#
# GUIA RÁPIDO DE DEPLOY - Atualização IBS/CBS
# Execute este arquivo no SERVIDOR após fazer upload
#

echo "=================================================="
echo "  DEPLOY - Atualização Classificações IBS/CBS"
echo "=================================================="
echo ""

# Detectar diretório do projeto
if [ -f "app.py" ]; then
    PROJECT_DIR="$(pwd)"
elif [ -f "../app.py" ]; then
    PROJECT_DIR="$(cd .. && pwd)"
else
    echo "❌ ERRO: Não foi possível detectar o diretório do projeto"
    echo "Execute este script dentro do diretório api_nfe"
    exit 1
fi

echo "📁 Diretório do projeto: $PROJECT_DIR"
echo ""

# Verificar se o arquivo compactado existe
if [ ! -f "atualizacao_ibs_cbs_servidor.tar.gz" ]; then
    echo "❌ ERRO: Arquivo atualizacao_ibs_cbs_servidor.tar.gz não encontrado"
    echo ""
    echo "Faça upload do arquivo primeiro:"
    echo "  scp atualizacao_ibs_cbs_servidor.tar.gz usuario@servidor:~/api_nfe/"
    exit 1
fi

echo "📦 Descompactando arquivos..."
tar -xzf atualizacao_ibs_cbs_servidor.tar.gz

if [ $? -ne 0 ]; then
    echo "❌ ERRO ao descompactar"
    exit 1
fi

echo "✅ Arquivos descompactados"
echo ""

# Verificar estrutura
echo "📋 Verificando arquivos..."
ARQUIVOS_OK=true

if [ ! -f "scripts/atualizar_ibs_cbs_servidor.py" ]; then
    echo "❌ Falta: scripts/atualizar_ibs_cbs_servidor.py"
    ARQUIVOS_OK=false
fi

if [ ! -f "scripts/atualizar_ibs_cbs.sh" ]; then
    echo "❌ Falta: scripts/atualizar_ibs_cbs.sh"
    ARQUIVOS_OK=false
fi

if [ ! -f "Documentacao/cClassTrib 2025-12-12.xlsx" ]; then
    echo "❌ Falta: Documentacao/cClassTrib 2025-12-12.xlsx"
    ARQUIVOS_OK=false
fi

if [ "$ARQUIVOS_OK" = false ]; then
    echo ""
    echo "❌ Alguns arquivos estão faltando. Verifique o upload."
    exit 1
fi

echo "✅ Todos os arquivos presentes"
echo ""

# Tornar scripts executáveis
echo "🔧 Configurando permissões..."
chmod +x scripts/atualizar_ibs_cbs.sh
chmod +x scripts/atualizar_ibs_cbs_servidor.py

echo "✅ Permissões configuradas"
echo ""

# Verificar Python
echo "🐍 Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 não encontrado"
    echo "Instale com: sudo apt install python3 python3-pip"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✅ $PYTHON_VERSION"
echo ""

# Verificar dependências
echo "📦 Verificando dependências Python..."
python3 -c "import pandas" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Pandas não instalado"
    read -p "Deseja instalar agora? (s/N): " INSTALAR
    if [ "$INSTALAR" = "s" ] || [ "$INSTALAR" = "S" ]; then
        echo "Instalando dependências..."
        pip3 install pandas openpyxl sqlalchemy psycopg2-binary
        if [ $? -eq 0 ]; then
            echo "✅ Dependências instaladas"
        else
            echo "❌ Erro ao instalar dependências"
            exit 1
        fi
    else
        echo "❌ Dependências necessárias não instaladas"
        exit 1
    fi
else
    echo "✅ Dependências OK"
fi

echo ""
echo "=================================================="
echo "  ✅ DEPLOY CONCLUÍDO"
echo "=================================================="
echo ""
echo "📝 Para executar a atualização:"
echo "   ./scripts/atualizar_ibs_cbs.sh"
echo ""
echo "📖 Documentação completa:"
echo "   cat scripts/README_ATUALIZACAO_IBS_CBS.md"
echo ""
echo "🔍 Para ver um resumo do que será feito:"
echo "   python3 scripts/atualizar_ibs_cbs_servidor.py --help"
echo ""

read -p "Deseja executar a atualização agora? (s/N): " EXECUTAR

if [ "$EXECUTAR" = "s" ] || [ "$EXECUTAR" = "S" ]; then
    echo ""
    ./scripts/atualizar_ibs_cbs.sh
else
    echo ""
    echo "OK. Execute quando estiver pronto:"
    echo "   ./scripts/atualizar_ibs_cbs.sh"
fi
