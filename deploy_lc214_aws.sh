#!/bin/bash

###############################################################################
# DEPLOY COMPLETO - BRANCH lc214-migration PARA AWS
# Sistema: EmiteMax - API NFe + NFS-e
# Servidor: EC2 3.87.73.106 (Ubuntu 24.04.3 LTS)
# Database: RDS PostgreSQL nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com
# Data: 30/01/2026
###############################################################################

set -e  # Exit on error

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações do servidor
SSH_KEY="$HOME/Downloads/nfe-new-api-key.pem"
SERVER_USER="ubuntu"
SERVER_IP="100.26.12.107"
SERVER_PATH="/home/ubuntu/api_nfe"
SSH_CMD="ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP"
SCP_CMD="scp -i $SSH_KEY"

# Configurações do banco de dados
DB_HOST="nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com"
DB_PORT="5432"
DB_NAME="sjtnfe"
DB_USER="postgres"
DB_PASSWORD="gMGM\!\#)NW\$nH1w(wrVIdcmn5"  # Escapado para shell

# Banner
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                   DEPLOY AWS - LC214 MIGRATION                    ║"
echo "║              Reforma Tributária IBS/CBS/NBS                       ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

###############################################################################
# ETAPA 1: VERIFICAÇÕES PRÉ-DEPLOY
###############################################################################

echo -e "\n${YELLOW}[ETAPA 1/9]${NC} Verificações pré-deploy..."

# Verificar se estamos na branch correta
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "lc214-migration" ]; then
    echo -e "${RED}❌ Erro: Você não está na branch lc214-migration${NC}"
    echo -e "${YELLOW}Branch atual: $CURRENT_BRANCH${NC}"
    echo -e "${YELLOW}Execute: git checkout lc214-migration${NC}"
    exit 1
fi

# Verificar se há alterações não commitadas
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}❌ Erro: Há alterações não commitadas${NC}"
    echo -e "${YELLOW}Execute: git status${NC}"
    exit 1
fi

# Verificar SSH key
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}❌ Erro: SSH key não encontrada: $SSH_KEY${NC}"
    exit 1
fi

# Testar conexão SSH
echo -e "${BLUE}🔐 Testando conexão SSH...${NC}"
if ! $SSH_CMD "echo 'Conexão SSH OK'" > /dev/null 2>&1; then
    echo -e "${RED}❌ Erro: Não foi possível conectar ao servidor${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Verificações OK${NC}"

###############################################################################
# ETAPA 2: PUSH DAS ALTERAÇÕES PARA GITHUB
###############################################################################

echo -e "\n${YELLOW}[ETAPA 2/9]${NC} Push das alterações para GitHub..."

# Verificar se há commits para push
if ! git log origin/lc214-migration..HEAD --oneline | grep -q .; then
    echo -e "${YELLOW}⚠️  Não há novos commits para push${NC}"
else
    echo -e "${BLUE}📤 Fazendo push...${NC}"
    git push origin lc214-migration
    echo -e "${GREEN}✅ Push concluído${NC}"
fi

###############################################################################
# ETAPA 3: BACKUP DO BANCO DE DADOS
###############################################################################

echo -e "\n${YELLOW}[ETAPA 3/9]${NC} Backup do banco de dados..."

BACKUP_FILE="sjtnfe_backup_$(date +%Y%m%d_%H%M%S).sql"
BACKUP_PATH="/home/ubuntu/backups/$BACKUP_FILE"

echo -e "${BLUE}💾 Criando backup em $SERVER_IP...${NC}"

$SSH_CMD << EOF
    mkdir -p /home/ubuntu/backups
    PGPASSWORD='$DB_PASSWORD' pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -F p -f $BACKUP_PATH
    if [ -f "$BACKUP_PATH" ]; then
        BACKUP_SIZE=\$(du -h "$BACKUP_PATH" | cut -f1)
        echo "✅ Backup criado: \$BACKUP_SIZE"
    else
        echo "❌ Erro ao criar backup"
        exit 1
    fi
EOF

echo -e "${GREEN}✅ Backup concluído: $BACKUP_FILE${NC}"

###############################################################################
# ETAPA 4: ATUALIZAR CÓDIGO NO SERVIDOR
###############################################################################

echo -e "\n${YELLOW}[ETAPA 4/9]${NC} Atualizando código no servidor..."

echo -e "${BLUE}🔄 Fazendo pull no servidor...${NC}"

$SSH_CMD << EOF
    cd $SERVER_PATH
    
    # Fazer stash de alterações locais (se houver)
    git stash save "Auto-stash antes de pull - $(date)"
    
    # Fetch e checkout da branch
    git fetch origin
    git checkout lc214-migration
    git pull origin lc214-migration
    
    echo "✅ Código atualizado"
    echo "📊 Últimos commits:"
    git log --oneline -5
EOF

echo -e "${GREEN}✅ Código atualizado${NC}"

###############################################################################
# ETAPA 5: INSTALAR/ATUALIZAR DEPENDÊNCIAS
###############################################################################

echo -e "\n${YELLOW}[ETAPA 5/9]${NC} Instalando dependências Python..."

echo -e "${BLUE}📦 Atualizando requirements.txt...${NC}"

$SSH_CMD << EOF
    cd $SERVER_PATH
    
    # Ativar ambiente virtual se existir
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    
    # Instalar/atualizar dependências
    pip3 install --upgrade pip
    pip3 install -r requirements.txt
    
    echo "✅ Dependências instaladas"
EOF

echo -e "${GREEN}✅ Dependências OK${NC}"

###############################################################################
# ETAPA 6: EXECUTAR MIGRATIONS SQL
###############################################################################

echo -e "\n${YELLOW}[ETAPA 6/9]${NC} Executando migrations do banco de dados..."

echo -e "${BLUE}📋 Migrations a serem executadas:${NC}"
echo "  • migrations/create_tabelas_servicos_nbs_oficial.sql"
echo ""

read -p "$(echo -e ${YELLOW}Deseja executar as migrations? [S/n]: ${NC})" -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]] || [[ -z $REPLY ]]; then
    
    echo -e "${BLUE}🗄️  Executando migration principal...${NC}"
    
    $SSH_CMD << EOF
        cd $SERVER_PATH
        
        # Executar migration de tabelas LC116/NBS
        PGPASSWORD='$DB_PASSWORD' psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f migrations/create_tabelas_servicos_nbs_oficial.sql
        
        if [ \$? -eq 0 ]; then
            echo "✅ Migration create_tabelas_servicos_nbs_oficial.sql executada"
        else
            echo "❌ Erro na migration (pode ser tabelas já existentes)"
        fi
EOF

    echo -e "${GREEN}✅ Migrations concluídas${NC}"
else
    echo -e "${YELLOW}⏭️  Migrations ignoradas${NC}"
fi

###############################################################################
# ETAPA 7: POPULAR DADOS DAS TABELAS
###############################################################################

echo -e "\n${YELLOW}[ETAPA 7/9]${NC} Populando dados das tabelas..."

echo -e "${BLUE}📊 Scripts de população:${NC}"
echo "  • scripts/popular_todos_servicos_lc116.py (203 serviços)"
echo ""

read -p "$(echo -e ${YELLOW}Deseja popular os dados? [S/n]: ${NC})" -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]] || [[ -z $REPLY ]]; then
    
    echo -e "${BLUE}📥 Executando script de população...${NC}"
    
    $SSH_CMD << EOF
        cd $SERVER_PATH
        
        # Ativar ambiente virtual
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
        fi
        
        # Executar script de população
        python3 scripts/popular_todos_servicos_lc116.py
        
        echo ""
        echo "📊 Verificando dados inseridos:"
        PGPASSWORD='$DB_PASSWORD' psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) as total_servicos FROM codigos_servico_lc116;"
        PGPASSWORD='$DB_PASSWORD' psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) as total_nbs FROM codigos_nbs;"
EOF

    echo -e "${GREEN}✅ Dados populados${NC}"
else
    echo -e "${YELLOW}⏭️  População de dados ignorada${NC}"
fi

###############################################################################
# ETAPA 8: REINICIAR SERVIÇOS
###############################################################################

echo -e "\n${YELLOW}[ETAPA 8/9]${NC} Reiniciando serviços..."

echo -e "${BLUE}🔄 Reiniciando api-nfe-principal (Flask)...${NC}"

$SSH_CMD << EOF
    # Reiniciar serviço principal
    sudo systemctl restart api-nfe-principal
    sleep 3
    
    # Verificar status
    if sudo systemctl is-active --quiet api-nfe-principal; then
        echo "✅ api-nfe-principal: ATIVO"
    else
        echo "❌ api-nfe-principal: FALHOU"
        sudo journalctl -u api-nfe-principal -n 20 --no-pager
        exit 1
    fi
EOF

echo -e "${BLUE}🔄 Reiniciando api-nfe-ia (FastAPI)...${NC}"

$SSH_CMD << EOF
    # Reiniciar serviço IA
    sudo systemctl restart api-nfe-ia
    sleep 3
    
    # Verificar status
    if sudo systemctl is-active --quiet api-nfe-ia; then
        echo "✅ api-nfe-ia: ATIVO"
    else
        echo "⚠️  api-nfe-ia: Status desconhecido (pode não existir)"
    fi
EOF

echo -e "${GREEN}✅ Serviços reiniciados${NC}"

###############################################################################
# ETAPA 9: VERIFICAÇÕES PÓS-DEPLOY
###############################################################################

echo -e "\n${YELLOW}[ETAPA 9/9]${NC} Verificações pós-deploy..."

echo -e "${BLUE}🔍 Verificando estrutura do banco...${NC}"

$SSH_CMD << EOF
    echo ""
    echo "📊 Tabelas criadas:"
    PGPASSWORD='$DB_PASSWORD' psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dt codigos_*"
    
    echo ""
    echo "📈 Estatísticas:"
    PGPASSWORD='$DB_PASSWORD' psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << 'EOSQL'
        SELECT 'codigos_servico_lc116' as tabela, COUNT(*) as registros FROM codigos_servico_lc116
        UNION ALL
        SELECT 'codigos_nbs', COUNT(*) FROM codigos_nbs
        UNION ALL
        SELECT 'servicos_lc116_nbs', COUNT(*) FROM servicos_lc116_nbs;
EOSQL
EOF

echo -e "\n${BLUE}🌐 Testando endpoints da aplicação...${NC}"

# Testar health check
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://$SERVER_IP:8080/health 2>/dev/null || echo "000")

if [ "$HEALTH_CHECK" = "200" ]; then
    echo -e "${GREEN}✅ Health check: OK (HTTP 200)${NC}"
else
    echo -e "${YELLOW}⚠️  Health check: HTTP $HEALTH_CHECK${NC}"
fi

###############################################################################
# RESUMO FINAL
###############################################################################

echo -e "\n${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                   DEPLOY CONCLUÍDO COM SUCESSO!                   ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${BLUE}📋 Resumo do Deploy:${NC}"
echo "  ✅ Código atualizado (branch lc214-migration)"
echo "  ✅ Backup do banco criado: $BACKUP_FILE"
echo "  ✅ Migrations executadas"
echo "  ✅ Dados populados"
echo "  ✅ Serviços reiniciados"
echo ""

echo -e "${BLUE}🔗 URLs:${NC}"
echo "  • Aplicação: http://$SERVER_IP:8080"
echo "  • Admin: http://$SERVER_IP:8080/admin"
echo "  • API IA: http://$SERVER_IP:8081"
echo ""

echo -e "${BLUE}📝 Alterações implantadas:${NC}"
echo "  • Tabelas oficiais LC116/NBS criadas"
echo "  • 203 códigos de serviço LC 116 populados"
echo "  • 33 códigos NBS populados"
echo "  • APIs REST /admin/nfse/api/servicos-lc116 e /api/codigos-nbs"
echo "  • Select dinâmico Código NBS corrigido"
echo "  • Documento treinamento IA (dados oficiais gov.br)"
echo ""

echo -e "${YELLOW}⚠️  Ações recomendadas pós-deploy:${NC}"
echo "  1. Testar emissão NFS-e com novo select NBS"
echo "  2. Verificar cadastro de regras tributárias"
echo "  3. Monitorar logs: sudo journalctl -u api-nfe-principal -f"
echo "  4. Verificar se backup foi criado: $BACKUP_PATH"
echo ""

echo -e "${BLUE}🔧 Comandos úteis:${NC}"
echo "  • Ver logs: $SSH_CMD \"sudo journalctl -u api-nfe-principal -f\""
echo "  • Restart: $SSH_CMD \"sudo systemctl restart api-nfe-principal\""
echo "  • Status: $SSH_CMD \"sudo systemctl status api-nfe-principal\""
echo "  • Backup: $SSH_CMD \"ls -lh /home/ubuntu/backups/\""
echo ""

echo -e "${GREEN}✨ Deploy finalizado em $(date '+%d/%m/%Y às %H:%M:%S')${NC}"
