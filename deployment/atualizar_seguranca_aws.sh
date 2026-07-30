#!/bin/bash
#
# Script de Deploy - Atualização de Segurança de Roles
# Branch: lc214-migration
# Data: 02/01/2026
#
# INSTRUÇÕES:
# 1. Copie este script para o servidor AWS
# 2. Execute: chmod +x atualizar_seguranca_aws.sh
# 3. Execute: ./atualizar_seguranca_aws.sh
#

set -e  # Encerra em caso de erro

echo "=========================================="
echo "DEPLOY: Atualização de Segurança de Roles"
echo "=========================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Diretório do projeto
PROJECT_DIR="/home/ubuntu/api_nfe"
cd "$PROJECT_DIR"

echo -e "${YELLOW}[1/7]${NC} Verificando branch atual..."
CURRENT_BRANCH=$(git branch --show-current)
echo "Branch atual: $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" != "lc214-migration" ]; then
    echo -e "${RED}ERRO: Branch incorreta. Esperado 'lc214-migration', encontrado '$CURRENT_BRANCH'${NC}"
    exit 1
fi

echo -e "${YELLOW}[2/7]${NC} Fazendo backup dos arquivos atuais..."
BACKUP_DIR="backups/pre-security-update-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp auth/decorators.py "$BACKUP_DIR/" 2>/dev/null || true
cp routes/admin_routes.py "$BACKUP_DIR/" 2>/dev/null || true
cp routes/nfe_routes.py "$BACKUP_DIR/" 2>/dev/null || true
cp routes/cliente_routes.py "$BACKUP_DIR/" 2>/dev/null || true
echo -e "${GREEN}✓${NC} Backup criado em: $BACKUP_DIR"

echo -e "${YELLOW}[3/7]${NC} Buscando atualizações do repositório..."
git fetch origin lc214-migration

echo -e "${YELLOW}[4/7]${NC} Verificando diferenças..."
git diff HEAD origin/lc214-migration --stat

echo -e "${YELLOW}[5/7]${NC} Aplicando atualizações (git pull)..."
git pull origin lc214-migration

echo -e "${YELLOW}[6/7]${NC} Verificando sintaxe dos arquivos Python..."
python3 -m py_compile auth/decorators.py
python3 -m py_compile routes/admin_routes.py
python3 -m py_compile routes/nfe_routes.py
python3 -m py_compile routes/cliente_routes.py
echo -e "${GREEN}✓${NC} Todos os arquivos compilam sem erros"

echo -e "${YELLOW}[7/7]${NC} Reiniciando serviços..."

# Verifica se os serviços existem
if systemctl list-units --full -all | grep -q "api_nfe_principal.service"; then
    echo "Reiniciando api_nfe_principal.service..."
    sudo systemctl restart api_nfe_principal.service
    sleep 3
    sudo systemctl status api_nfe_principal.service --no-pager || true
else
    echo -e "${YELLOW}⚠${NC} Serviço api_nfe_principal.service não encontrado"
fi

if systemctl list-units --full -all | grep -q "api_nfe_ia.service"; then
    echo "Reiniciando api_nfe_ia.service..."
    sudo systemctl restart api_nfe_ia.service
    sleep 3
    sudo systemctl status api_nfe_ia.service --no-pager || true
else
    echo -e "${YELLOW}⚠${NC} Serviço api_nfe_ia.service não encontrado"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "DEPLOY CONCLUÍDO COM SUCESSO!"
echo "==========================================${NC}"
echo ""
echo "Arquivos atualizados:"
echo "  ✓ auth/decorators.py (novos decorators)"
echo "  ✓ routes/admin_routes.py (~30 rotas protegidas)"
echo "  ✓ routes/nfe_routes.py (~12 rotas protegidas)"
echo "  ✓ routes/cliente_routes.py (imports atualizados)"
echo "  ✓ AUDITORIA_SEGURANCA.md (documentação)"
echo "  ✓ CORRECOES_APLICADAS.md (resumo)"
echo "  ✓ GUIA_IMPLEMENTACAO_SEGURANCA.md (guia)"
echo ""
echo "Correções de Segurança Ativas:"
echo "  ✓ Viewers NÃO podem mais emitir NFe"
echo "  ✓ Viewers NÃO podem mais editar/excluir dados"
echo "  ✓ Apenas Super_Admin gerencia usuários/roles"
echo "  ✓ Editor pode emitir NFe normalmente"
echo "  ✓ Viewer tem acesso read-only completo"
echo ""
echo -e "${YELLOW}PRÓXIMOS PASSOS:${NC}"
echo "1. Testar login com usuários de cada role"
echo "2. Verificar logs: sudo journalctl -u api_nfe_principal.service -f"
echo "3. Monitorar erros: tail -f logs/app.log"
echo "4. Consultar: cat CORRECOES_APLICADAS.md"
echo ""
echo "Backup dos arquivos anteriores em: $BACKUP_DIR"
echo ""
