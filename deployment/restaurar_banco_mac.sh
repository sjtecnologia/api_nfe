#!/bin/bash
################################################################################
# SCRIPT DE RESTAURAÇÃO DO BANCO DE DADOS - macOS
# Sistema: EmiteMax v2.0
# Ambiente: Desenvolvimento Local
################################################################################

echo ""
echo "============================================================"
echo "  RESTAURAÇÃO BANCO DE DADOS PostgreSQL"
echo "  EmiteMax v2.0 - Ambiente Local (Mac)"
echo "============================================================"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configurações do PostgreSQL Local
PGHOST="localhost"
PGPORT="5432"
PGDATABASE="sjtnfe"
PGUSER="postgres"

# Configurar senha do PostgreSQL
export PGPASSWORD="Mo2505"

# Pasta onde o backup deve estar
BACKUP_DIR="$HOME/Documents/Developement/api_nfe/deployment/backups"

# Criar pasta de backups se não existir
mkdir -p "$BACKUP_DIR"

echo -e "${YELLOW}[INFO]${NC} Procurando arquivos de backup..."
echo ""

# Listar backups disponíveis
if [ -d "$BACKUP_DIR" ] && [ "$(ls -A $BACKUP_DIR/*.sql 2>/dev/null)" ]; then
    echo "BACKUPS DISPONÍVEIS:"
    echo "----------------------------------------------------------"
    ls -lh "$BACKUP_DIR"/*.sql 2>/dev/null | awk '{print NR". "$9" ("$5")"}'
    echo "----------------------------------------------------------"
    echo ""
    
    # Solicitar qual backup usar
    read -p "Digite o número do backup para restaurar (ou caminho completo): " ESCOLHA
    
    if [[ "$ESCOLHA" =~ ^[0-9]+$ ]]; then
        # Se digitou número, pegar arquivo da lista
        BACKUP_FILE=$(ls "$BACKUP_DIR"/*.sql 2>/dev/null | sed -n "${ESCOLHA}p")
    else
        # Se digitou caminho, usar diretamente
        BACKUP_FILE="$ESCOLHA"
    fi
else
    echo -e "${YELLOW}[AVISO]${NC} Nenhum backup encontrado em: $BACKUP_DIR"
    echo ""
    read -p "Digite o caminho completo do arquivo de backup: " BACKUP_FILE
fi

# Verificar se arquivo existe
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}[ERRO]${NC} Arquivo não encontrado: $BACKUP_FILE"
    exit 1
fi

echo ""
echo -e "${GREEN}[OK]${NC} Arquivo selecionado: $BACKUP_FILE"
echo ""

# Mostrar informações do backup
if [ -f "${BACKUP_FILE}.info" ]; then
    echo "INFORMAÇÕES DO BACKUP:"
    echo "----------------------------------------------------------"
    cat "${BACKUP_FILE}.info"
    echo "----------------------------------------------------------"
    echo ""
fi

# Calcular tamanho
TAMANHO=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
echo -e "${YELLOW}[INFO]${NC} Tamanho do backup: $TAMANHO"
echo ""

# Confirmação
echo -e "${YELLOW}[ATENÇÃO]${NC} Esta operação irá:"
echo "  1. Fazer backup do banco LOCAL atual"
echo "  2. DROPAR o banco de dados: $PGDATABASE"
echo "  3. Recriar o banco vazio"
echo "  4. Restaurar dados do arquivo: $(basename $BACKUP_FILE)"
echo ""
read -p "Deseja continuar? (digite SIM para confirmar): " CONFIRMA

if [ "$CONFIRMA" != "SIM" ]; then
    echo -e "${YELLOW}[INFO]${NC} Operação cancelada pelo usuário."
    exit 0
fi

echo ""
echo "============================================================"
echo "  INICIANDO RESTAURAÇÃO"
echo "============================================================"
echo ""

# 1. Fazer backup do banco local ANTES de dropar
echo -e "${YELLOW}[INFO]${NC} Criando backup de segurança do banco local..."
BACKUP_LOCAL="$BACKUP_DIR/sjtnfe_local_pre_restore_$(date +%Y%m%d_%H%M%S).sql"
pg_dump -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE > "$BACKUP_LOCAL" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}[OK]${NC} Backup local salvo: $BACKUP_LOCAL"
else
    echo -e "${YELLOW}[AVISO]${NC} Não foi possível criar backup local (normal se banco não existir)"
fi

echo ""

# 2. Encerrar conexões ativas
echo -e "${YELLOW}[INFO]${NC} Encerrando conexões ativas no banco..."
psql -h $PGHOST -p $PGPORT -U $PGUSER -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$PGDATABASE' AND pid <> pg_backend_pid();" > /dev/null 2>&1

# 3. Dropar banco se existir
echo -e "${YELLOW}[INFO]${NC} Removendo banco existente..."
dropdb -h $PGHOST -p $PGPORT -U $PGUSER --if-exists $PGDATABASE

if [ $? -eq 0 ]; then
    echo -e "${GREEN}[OK]${NC} Banco removido"
else
    echo -e "${RED}[ERRO]${NC} Falha ao remover banco"
    exit 1
fi

# 4. Criar banco novo
echo -e "${YELLOW}[INFO]${NC} Criando banco vazio..."
createdb -h $PGHOST -p $PGPORT -U $PGUSER $PGDATABASE

if [ $? -eq 0 ]; then
    echo -e "${GREEN}[OK]${NC} Banco criado"
else
    echo -e "${RED}[ERRO]${NC} Falha ao criar banco"
    exit 1
fi

# 5. Restaurar backup
echo ""
echo -e "${YELLOW}[INFO]${NC} Restaurando dados do backup..."
echo -e "${YELLOW}[INFO]${NC} Isso pode levar alguns minutos..."
echo ""

psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -f "$BACKUP_FILE" > restore.log 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}[OK]${NC} Dados restaurados com sucesso!"
else
    echo -e "${YELLOW}[AVISO]${NC} Restauração concluída com avisos (verifique restore.log)"
fi

# 6. Verificar restauração
echo ""
echo -e "${YELLOW}[INFO]${NC} Verificando dados restaurados..."
echo ""

# Contar tabelas
TOTAL_TABELAS=$(psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")
echo -e "${GREEN}[OK]${NC} Total de tabelas: $TOTAL_TABELAS"

# Verificar tabelas principais
echo ""
echo "TABELAS PRINCIPAIS:"
psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -c "
SELECT 
    schemaname AS schema,
    tablename AS tabela,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = tablename) AS colunas
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('clientes', 'nfe_emitidas', 'produtos', 'regimes_tributarios', 'classificacoes_ibs_cbs')
ORDER BY tablename;
"

# Verificar registros
echo ""
echo "CONTAGEM DE REGISTROS:"
echo "----------------------------------------------------------"

TABELAS=("clientes" "nfe_emitidas" "produtos" "regimes_tributarios" "classificacoes_ibs_cbs" "autorizacoes_xml_nfe")

for TABELA in "${TABELAS[@]}"; do
    COUNT=$(psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -t -c "SELECT COUNT(*) FROM $TABELA;" 2>/dev/null)
    if [ $? -eq 0 ]; then
        printf "%-30s: %s registros\n" "$TABELA" "$COUNT"
    else
        printf "%-30s: ${YELLOW}[tabela não existe]${NC}\n" "$TABELA"
    fi
done

echo "----------------------------------------------------------"

# 7. Verificar implementação CRT=3
echo ""
echo -e "${YELLOW}[INFO]${NC} Verificando implementação CRT=3..."
echo ""

# Verificar campo crt
CAMPO_CRT=$(psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'regimes_tributarios' AND column_name = 'crt';" 2>/dev/null)

if [ "$CAMPO_CRT" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Campo 'crt' existe em regimes_tributarios"
    
    # Mostrar valores de CRT
    psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -c "SELECT id, nome, crt FROM regimes_tributarios ORDER BY id;"
else
    echo -e "${YELLOW}⚠${NC} Campo 'crt' NÃO existe em regimes_tributarios"
    echo -e "${YELLOW}[INFO]${NC} Execute atualizacao_crt3.sql para adicionar suporte CRT=3"
fi

echo ""

# Verificar tabela classificacoes_ibs_cbs
TABELA_IBS=$(psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'classificacoes_ibs_cbs';" 2>/dev/null)

if [ "$TABELA_IBS" -gt 0 ]; then
    COUNT_CLASS=$(psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -t -c "SELECT COUNT(*) FROM classificacoes_ibs_cbs;")
    echo -e "${GREEN}✓${NC} Tabela 'classificacoes_ibs_cbs' existe com $COUNT_CLASS registros"
else
    echo -e "${YELLOW}⚠${NC} Tabela 'classificacoes_ibs_cbs' NÃO existe"
    echo -e "${YELLOW}[INFO]${NC} Execute atualizacao_crt3.sql para criar tabela"
fi

echo ""
echo "============================================================"
echo "  RESTAURAÇÃO CONCLUÍDA!"
echo "============================================================"
echo ""
echo -e "${GREEN}[OK]${NC} Banco de dados: $PGDATABASE"
echo -e "${GREEN}[OK]${NC} Backup original: $(basename $BACKUP_FILE)"
echo -e "${GREEN}[OK]${NC} Backup local salvo em: $BACKUP_LOCAL"
echo ""
echo "PRÓXIMOS PASSOS:"
echo "1. Testar conexão com o banco"
echo "2. Iniciar aplicação Flask: python app.py"
echo "3. Acessar: http://localhost:8080"
echo ""
echo "LOGS:"
echo "- Detalhes da restauração: restore.log"
echo "- Backup local antes da restauração: $BACKUP_LOCAL"
echo ""

# Limpar arquivo de erro se vazio
if [ -f "restore.log" ]; then
    if [ ! -s "restore.log" ]; then
        rm restore.log
    fi
fi
