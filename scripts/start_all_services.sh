#!/bin/bash

# ============================================
# Script de Inicialização - Todos os Serviços
# ============================================
# Inicia servidor principal + API de IA
# Data: 30/11/2025
# ============================================

set -e

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Diretório do projeto
PROJECT_DIR="/Users/renato/Documents/Developement/api_nfe"
cd "$PROJECT_DIR"

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  Iniciando Todos os Serviços${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Função para limpar processos ao sair
cleanup() {
    echo ""
    echo -e "${YELLOW}Encerrando serviços...${NC}"
    if [ ! -z "$PID_API_PRINCIPAL" ]; then
        kill $PID_API_PRINCIPAL 2>/dev/null || true
    fi
    if [ ! -z "$PID_API_IA" ]; then
        kill $PID_API_IA 2>/dev/null || true
    fi
    echo -e "${GREEN}✓ Serviços encerrados${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Verificar se já existe algo rodando nas portas
echo -e "${YELLOW}[1/4] Verificando portas...${NC}"

if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${RED}✗ Porta 8080 já está em uso!${NC}"
    echo "   Matando processo existente..."
    lsof -ti:8080 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

if lsof -Pi :9000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${RED}✗ Porta 9000 já está em uso!${NC}"
    echo "   Matando processo existente..."
    lsof -ti:9000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

echo -e "${GREEN}✓ Portas 8080 e 9000 disponíveis${NC}"
echo ""

# Ativar ambiente virtual se existir
if [ -d "venv" ]; then
    echo -e "${YELLOW}[2/4] Ativando ambiente virtual...${NC}"
    source venv/bin/activate
    echo -e "${GREEN}✓ Ambiente virtual ativado${NC}"
else
    echo -e "${YELLOW}[2/4] Ambiente virtual não encontrado, usando Python do sistema${NC}"
fi
echo ""

# Iniciar API de IA (porta 9000)
echo -e "${YELLOW}[3/4] Iniciando API de IA (porta 9000)...${NC}"
python3 scripts/utilitarios/api_ia_unificada.py > logs/api_ia.log 2>&1 &
PID_API_IA=$!

# Aguardar API de IA iniciar
sleep 3

if ps -p $PID_API_IA > /dev/null; then
    echo -e "${GREEN}✓ API de IA iniciada (PID: $PID_API_IA)${NC}"
    echo "   Porta: 9000"
    echo "   Log: logs/api_ia.log"
else
    echo -e "${RED}✗ Erro ao iniciar API de IA!${NC}"
    echo "   Verifique o log: logs/api_ia.log"
    exit 1
fi
echo ""

# Iniciar API Principal (porta 8080)
echo -e "${YELLOW}[4/4] Iniciando API Principal (porta 8080)...${NC}"
python3 app.py > logs/api_principal.log 2>&1 &
PID_API_PRINCIPAL=$!

# Aguardar API Principal iniciar
sleep 3

if ps -p $PID_API_PRINCIPAL > /dev/null; then
    echo -e "${GREEN}✓ API Principal iniciada (PID: $PID_API_PRINCIPAL)${NC}"
    echo "   Porta: 8080"
    echo "   Log: logs/api_principal.log"
else
    echo -e "${RED}✗ Erro ao iniciar API Principal!${NC}"
    echo "   Verifique o log: logs/api_principal.log"
    kill $PID_API_IA 2>/dev/null || true
    exit 1
fi
echo ""

# Salvar PIDs em arquivo para referência
mkdir -p logs
echo $PID_API_PRINCIPAL > logs/api_principal.pid
echo $PID_API_IA > logs/api_ia.pid

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ Todos os Serviços Iniciados!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📊 Status dos Serviços:"
echo ""
echo "  🌐 API Principal:"
echo "     URL: http://192.168.0.52:8080"
echo "     PID: $PID_API_PRINCIPAL"
echo "     Log: logs/api_principal.log"
echo ""
echo "  🤖 API de IA (Sugestões NCM/Tributação):"
echo "     URL: http://localhost:9000"
echo "     PID: $PID_API_IA"
echo "     Log: logs/api_ia.log"
echo ""
echo "📝 Comandos Úteis:"
echo ""
echo "  Ver logs em tempo real:"
echo "    tail -f logs/api_principal.log"
echo "    tail -f logs/api_ia.log"
echo ""
echo "  Parar todos os serviços:"
echo "    kill $PID_API_PRINCIPAL $PID_API_IA"
echo "    ou pressione Ctrl+C"
echo ""
echo "  Verificar se estão rodando:"
echo "    ps -p $PID_API_PRINCIPAL"
echo "    ps -p $PID_API_IA"
echo ""
echo -e "${YELLOW}⚠  Pressione Ctrl+C para encerrar todos os serviços${NC}"
echo ""

# Manter script rodando e exibir logs
echo "=========================================="
echo "  Logs em Tempo Real (últimas 10 linhas)"
echo "=========================================="
echo ""

# Função para exibir logs
tail -f logs/api_principal.log logs/api_ia.log &
TAIL_PID=$!

# Aguardar Ctrl+C
wait
