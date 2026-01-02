#!/bin/bash
#
# Script para atualizar classificações IBS/CBS no servidor
# Uso: ./atualizar_ibs_cbs.sh
#

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Diretório do script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Atualização IBS/CBS - Servidor${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Verificar se o arquivo Excel existe
EXCEL_FILE="$PROJECT_DIR/Documentacao/cClassTrib 2025-12-12.xlsx"
if [ ! -f "$EXCEL_FILE" ]; then
    echo -e "${RED}❌ ERRO: Arquivo Excel não encontrado!${NC}"
    echo -e "   Esperado: $EXCEL_FILE"
    echo ""
    echo "Por favor, faça upload do arquivo para o servidor:"
    echo "  scp 'cClassTrib 2025-12-12.xlsx' usuario@servidor:$PROJECT_DIR/Documentacao/"
    exit 1
fi

echo -e "${GREEN}✅ Arquivo Excel encontrado${NC}"
echo ""

# Verificar se o Python está disponível
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ ERRO: Python3 não está instalado${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python3 disponível${NC}"
echo ""

# Verificar se as dependências estão instaladas
echo "📦 Verificando dependências Python..."
python3 -c "import pandas; import sqlalchemy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Dependências faltando. Instalando...${NC}"
    pip3 install pandas openpyxl sqlalchemy psycopg2-binary
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ ERRO: Falha ao instalar dependências${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Dependências OK${NC}"
echo ""

# Ativar ambiente virtual se existir
if [ -d "$PROJECT_DIR/venv" ]; then
    echo "🔧 Ativando ambiente virtual..."
    source "$PROJECT_DIR/venv/bin/activate"
    echo -e "${GREEN}✅ Ambiente virtual ativado${NC}"
    echo ""
fi

# Executar o script Python
cd "$PROJECT_DIR"
echo "🚀 Executando atualização..."
echo ""

python3 "$SCRIPT_DIR/atualizar_ibs_cbs_servidor.py" "$@"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  ✅ Atualização concluída com sucesso!${NC}"
    echo -e "${GREEN}============================================${NC}"
elif [ $EXIT_CODE -eq 2 ]; then
    echo -e "${YELLOW}============================================${NC}"
    echo -e "${YELLOW}  Operação cancelada pelo usuário${NC}"
    echo -e "${YELLOW}============================================${NC}"
else
    echo -e "${RED}============================================${NC}"
    echo -e "${RED}  ❌ Atualização falhou!${NC}"
    echo -e "${RED}============================================${NC}"
    echo ""
    echo "Verifique os logs acima para mais detalhes."
    echo "O backup dos dados antigos está em: $PROJECT_DIR/backups/"
fi

exit $EXIT_CODE
