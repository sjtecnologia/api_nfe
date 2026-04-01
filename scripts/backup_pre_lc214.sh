#!/bin/bash

# ========================================
# Script de Backup Completo - LC 214/2025
# ========================================
# Cria backup do banco antes da migração
# Data: 30/11/2025
# ========================================

set -e  # Para na primeira falha

# Configurações
BACKUP_DIR="/Users/renato/Documents/Developement/api_nfe/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="backup_pre_lc214_${TIMESTAMP}"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  BACKUP PRÉ-MIGRAÇÃO LC 214/2025${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Criar diretório de backup se não existir
mkdir -p "$BACKUP_DIR"
echo -e "${GREEN}✓${NC} Diretório de backup criado/verificado"

# Ler credenciais do .env ou pedir ao usuário
if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} Arquivo .env encontrado, carregando configurações..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${YELLOW}⚠${NC}  Arquivo .env não encontrado"
    echo ""
    read -p "Host do PostgreSQL [localhost]: " DB_HOST
    DB_HOST=${DB_HOST:-localhost}
    
    read -p "Porta [5432]: " DB_PORT
    DB_PORT=${DB_PORT:-5432}
    
    read -p "Nome do banco: " DB_NAME
    read -p "Usuário: " DB_USER
    read -sp "Senha: " DB_PASSWORD
    echo ""
fi

# Validar variáveis essenciais
if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ]; then
    echo -e "${RED}✗${NC} Erro: DB_NAME ou DB_USER não definidos"
    exit 1
fi

DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}

echo ""
echo -e "${YELLOW}Configurações:${NC}"
echo "  Host: $DB_HOST"
echo "  Porta: $DB_PORT"
echo "  Banco: $DB_NAME"
echo "  Usuário: $DB_USER"
echo ""

# Exportar senha para pg_dump
export PGPASSWORD="$DB_PASSWORD"

# 1. Backup completo do banco (schema + dados)
echo -e "${YELLOW}[1/5]${NC} Criando backup completo (SQL)..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -F p -f "$BACKUP_DIR/${BACKUP_NAME}_full.sql"
echo -e "${GREEN}✓${NC} Backup SQL completo: ${BACKUP_NAME}_full.sql"

# 2. Backup apenas do schema (estrutura)
echo -e "${YELLOW}[2/5]${NC} Criando backup do schema..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -s -F p -f "$BACKUP_DIR/${BACKUP_NAME}_schema_only.sql"
echo -e "${GREEN}✓${NC} Backup schema: ${BACKUP_NAME}_schema_only.sql"

# 3. Backup apenas dos dados (formato custom - comprimido)
echo -e "${YELLOW}[3/5]${NC} Criando backup dos dados (comprimido)..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -a -F c -f "$BACKUP_DIR/${BACKUP_NAME}_data_only.dump"
echo -e "${GREEN}✓${NC} Backup dados: ${BACKUP_NAME}_data_only.dump"

# 4. Exportar regras tributárias específicas (para documentação)
echo -e "${YELLOW}[4/5]${NC} Exportando regras tributárias atuais..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -c "COPY (
        SELECT 
            rt.regra_tributacao_id,
            rt.descricao_regra,
            rt.ativo,
            rt.prioridade,
            c.razao_social as cliente,
            reg.nome as regime_tributario,
            cfop.cfop,
            ncm.codigo as ncm,
            rt.uf_origem,
            rt.uf_destino,
            rt.csosn_icms,
            rt.cst_icms,
            rt.aliquota_icms,
            rt.cst_pis,
            rt.aliquota_pis,
            rt.cst_cofins,
            rt.aliquota_cofins,
            rt.cst_ipi,
            rt.aliquota_ipi,
            rt.data_inicio_vigencia,
            rt.data_fim_vigencia
        FROM regras_tributacao rt
            LEFT JOIN clientes c ON rt.cliente_id = c.cliente_id
            LEFT JOIN regimes_tributarios reg ON rt.regime_tributario_id = reg.regime_tributario_id
            LEFT JOIN cfops cfop ON rt.cfop_id = cfop.cfop_id
            LEFT JOIN ncms ncm ON rt.ncm_id = ncm.ncm_id
        ORDER BY rt.prioridade DESC, rt.regra_tributacao_id
    ) TO STDOUT WITH CSV HEADER" > "$BACKUP_DIR/${BACKUP_NAME}_regras_tributarias.csv"
echo -e "${GREEN}✓${NC} Regras exportadas: ${BACKUP_NAME}_regras_tributarias.csv"

# 5. Estatísticas do banco
echo -e "${YELLOW}[5/5]${NC} Gerando estatísticas do banco..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t \
    -c "
    SELECT 
        'Total de Clientes' as metrica, COUNT(*)::text as valor FROM clientes
    UNION ALL
    SELECT 'Total de Produtos', COUNT(*)::text FROM produtos
    UNION ALL
    SELECT 'Total de NFes Emitidas', COUNT(*)::text FROM nfes WHERE status = 'AUTORIZADA'
    UNION ALL
    SELECT 'Total de Regras Tributárias', COUNT(*)::text FROM regras_tributacao WHERE ativo = true
    UNION ALL
    SELECT 'Total de NCMs Cadastrados', COUNT(*)::text FROM ncms
    UNION ALL
    SELECT 'Total de CFOPs Cadastrados', COUNT(*)::text FROM cfops
    UNION ALL
    SELECT 'Tamanho do Banco (MB)', pg_size_pretty(pg_database_size('$DB_NAME'))
    " > "$BACKUP_DIR/${BACKUP_NAME}_estatisticas.txt"
echo -e "${GREEN}✓${NC} Estatísticas: ${BACKUP_NAME}_estatisticas.txt"

# Limpar senha da memória
unset PGPASSWORD

# Compactar backups
echo ""
echo -e "${YELLOW}Compactando backups...${NC}"
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}_completo.tar.gz" \
    "${BACKUP_NAME}_full.sql" \
    "${BACKUP_NAME}_schema_only.sql" \
    "${BACKUP_NAME}_data_only.dump" \
    "${BACKUP_NAME}_regras_tributarias.csv" \
    "${BACKUP_NAME}_estatisticas.txt"

BACKUP_SIZE=$(du -h "${BACKUP_NAME}_completo.tar.gz" | cut -f1)
echo -e "${GREEN}✓${NC} Backup compactado: ${BACKUP_NAME}_completo.tar.gz (${BACKUP_SIZE})"

# Exibir estatísticas
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  BACKUP CONCLUÍDO COM SUCESSO!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📦 Arquivos criados:"
echo "   1. ${BACKUP_NAME}_full.sql (backup completo)"
echo "   2. ${BACKUP_NAME}_schema_only.sql (apenas estrutura)"
echo "   3. ${BACKUP_NAME}_data_only.dump (apenas dados)"
echo "   4. ${BACKUP_NAME}_regras_tributarias.csv (regras exportadas)"
echo "   5. ${BACKUP_NAME}_estatisticas.txt (métricas do banco)"
echo "   6. ${BACKUP_NAME}_completo.tar.gz (tudo compactado)"
echo ""
echo "📊 Estatísticas:"
cat "$BACKUP_DIR/${BACKUP_NAME}_estatisticas.txt"
echo ""
echo -e "${YELLOW}⚠  IMPORTANTE:${NC}"
echo "   • Guarde este backup em local seguro"
echo "   • Considere fazer backup externo (nuvem)"
echo "   • Teste a restauração antes de prosseguir"
echo ""
echo "🔄 Para restaurar este backup:"
echo "   psql -h HOST -p PORT -U USER -d DATABASE < ${BACKUP_NAME}_full.sql"
echo ""
echo -e "${GREEN}Backup salvo em:${NC} $BACKUP_DIR"
echo ""

# Opcional: enviar para nuvem (S3, Google Drive, etc)
# Descomente e configure se desejar backup automático na nuvem
# aws s3 cp "${BACKUP_NAME}_completo.tar.gz" s3://seu-bucket/backups/

exit 0
