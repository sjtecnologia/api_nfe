#!/bin/bash
# ===============================================
# COMANDOS RÁPIDOS - SISTEMA IBS/CBS
# Atalhos para tarefas comuns do sistema
# ===============================================

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ===============================================
# DASHBOARD E MONITORAMENTO
# ===============================================

alias ibs-dashboard='python3 dashboard_ibs.py'
alias ibs-status='python3 dashboard_ibs.py | head -50'

# ===============================================
# TESTES
# ===============================================

alias ibs-teste-completo='python3 teste_correcoes_completo.py'
alias ibs-teste-calculo='python3 teste_calculo_ibs.py'
alias ibs-testes-todos='python3 teste_correcoes_completo.py && python3 teste_calculo_ibs.py'

# ===============================================
# CONSULTAS SQL RÁPIDAS
# ===============================================

# Total de códigos cadastrados
ibs-total-codigos() {
    echo -e "${BLUE}Total de códigos LC 116/2003 cadastrados:${NC}"
    python3 -c "
from database.connection import get_db
from sqlalchemy import text

db = next(get_db())
result = db.execute(text('SELECT COUNT(*) FROM codigos_servico')).fetchone()
print(f'  ✅ {result[0]} códigos cadastrados')
db.close()
"
}

# Listar códigos por categoria
ibs-codigos-categoria() {
    echo -e "${BLUE}Códigos por categoria:${NC}"
    python3 -c "
from database.connection import get_db
from sqlalchemy import text

db = next(get_db())
result = db.execute(text('''
    SELECT 
        LEFT(codigo, 2) as categoria,
        COUNT(*) as total
    FROM codigos_servico
    GROUP BY LEFT(codigo, 2)
    ORDER BY LEFT(codigo, 2)
''')).fetchall()

for row in result:
    print(f'  • Categoria {row[0]}: {row[1]} códigos')
    
db.close()
"
}

# Histórico de cálculos
ibs-historico() {
    echo -e "${BLUE}Últimos 10 cálculos IBS:${NC}"
    python3 -c "
from database.connection import get_db
from sqlalchemy import text

db = next(get_db())
result = db.execute(text('''
    SELECT 
        tipo_operacao,
        valor_base,
        valor_ibs + valor_cbs as total_tributos,
        data_calculo
    FROM historico_calculo_ibs
    ORDER BY data_calculo DESC
    LIMIT 10
''')).fetchall()

if result:
    for row in result:
        print(f'  • {row[0]}: R$ {row[1]:.2f} → R$ {row[2]:.2f} em {row[3]}')
else:
    print('  ⚠️  Nenhum cálculo registrado ainda')
    
db.close()
"
}

# Buscar código de serviço
ibs-buscar-codigo() {
    if [ -z "$1" ]; then
        echo -e "${YELLOW}Uso: ibs-buscar-codigo <código>${NC}"
        echo "Exemplo: ibs-buscar-codigo 01.01"
        return 1
    fi
    
    echo -e "${BLUE}Buscando código $1:${NC}"
    python3 -c "
from database.connection import get_db
from sqlalchemy import text

db = next(get_db())
result = db.execute(text('''
    SELECT codigo, descricao, aliquota_padrao, ativo
    FROM codigos_servico
    WHERE codigo = :codigo
'''), {'codigo': '$1'}).fetchone()

if result:
    print(f'  Código: {result[0]}')
    print(f'  Descrição: {result[1]}')
    print(f'  Alíquota: {result[2]:.2f}%')
    print(f'  Status: {\"✅ Ativo\" if result[3] else \"❌ Inativo\"}')
else:
    print('  ❌ Código não encontrado')
    
db.close()
"
}

# ===============================================
# MANUTENÇÃO
# ===============================================

# Repopular códigos
ibs-repopular() {
    echo -e "${YELLOW}⚠️  Isso irá adicionar/atualizar códigos LC 116/2003${NC}"
    read -p "Deseja continuar? (s/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        python3 popular_codigos_completos.py
    fi
}

# Executar migração
ibs-migrar() {
    echo -e "${YELLOW}⚠️  Isso irá executar migrações no banco de dados${NC}"
    read -p "Deseja continuar? (s/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        python3 executar_migracao_ibs_v2.py
    fi
}

# Backup do banco
ibs-backup() {
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="backup_ibs_$TIMESTAMP.sql"
    
    echo -e "${BLUE}Criando backup das tabelas IBS...${NC}"
    
    # Você precisará ajustar as credenciais
    pg_dump -U postgres -h localhost -t codigos_servico -t aliquotas_ibs_municipio -t historico_calculo_ibs > $BACKUP_FILE
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Backup criado: $BACKUP_FILE${NC}"
    else
        echo -e "${YELLOW}❌ Erro ao criar backup${NC}"
    fi
}

# ===============================================
# INFORMAÇÕES
# ===============================================

ibs-ajuda() {
    echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  COMANDOS RÁPIDOS - SISTEMA IBS/CBS${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BLUE}Dashboard e Monitoramento:${NC}"
    echo "  ibs-dashboard           - Dashboard completo"
    echo "  ibs-status              - Status resumido"
    echo ""
    echo -e "${BLUE}Testes:${NC}"
    echo "  ibs-teste-completo      - Bateria completa de testes"
    echo "  ibs-teste-calculo       - Testes do serviço de cálculo"
    echo "  ibs-testes-todos        - Todos os testes"
    echo ""
    echo -e "${BLUE}Consultas:${NC}"
    echo "  ibs-total-codigos       - Total de códigos cadastrados"
    echo "  ibs-codigos-categoria   - Códigos agrupados por categoria"
    echo "  ibs-historico           - Últimos 10 cálculos"
    echo "  ibs-buscar-codigo XX.XX - Buscar código específico"
    echo ""
    echo -e "${BLUE}Manutenção:${NC}"
    echo "  ibs-repopular           - Repopular códigos LC 116/2003"
    echo "  ibs-migrar              - Executar migrações"
    echo "  ibs-backup              - Backup das tabelas IBS"
    echo ""
    echo -e "${BLUE}Informações:${NC}"
    echo "  ibs-ajuda               - Esta mensagem"
    echo "  ibs-info                - Informações sobre o sistema"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
}

ibs-info() {
    echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  INFORMAÇÕES DO SISTEMA IBS/CBS${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BLUE}Versão:${NC} 1.0"
    echo -e "${BLUE}Data implementação:${NC} 18/11/2025"
    echo -e "${BLUE}Status:${NC} ✅ FASE 1 Completa"
    echo ""
    echo -e "${BLUE}Estrutura:${NC}"
    echo "  • 3 tabelas principais"
    echo "  • 170 códigos LC 116/2003"
    echo "  • Serviço de cálculo funcional"
    echo "  • Dashboard executivo"
    echo ""
    echo -e "${BLUE}Próxima fase:${NC} Q1/2026 (aguardando alíquotas)"
    echo -e "${BLUE}Investimento total:${NC} R$ 55.000 (3 anos)"
    echo ""
    echo -e "${BLUE}Arquivos principais:${NC}"
    echo "  • dashboard_ibs.py"
    echo "  • services/calculo_ibs_v2.py"
    echo "  • migrations/001_preparacao_ibs_simples.sql"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
}

# ===============================================
# INICIALIZAÇÃO
# ===============================================

# Mostrar ajuda ao carregar
echo -e "${GREEN}✅ Comandos IBS carregados!${NC}"
echo -e "Digite ${BLUE}ibs-ajuda${NC} para ver todos os comandos disponíveis"
