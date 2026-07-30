#!/bin/bash

# ============================================
# Script para Parar Todos os Serviços
# ============================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Parando todos os serviços...${NC}"
echo ""

# Parar pela porta 8080 (API Principal)
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}Parando API Principal (porta 8080)...${NC}"
    lsof -ti:8080 | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}✓ API Principal parada${NC}"
else
    echo -e "${YELLOW}API Principal não está rodando${NC}"
fi

# Parar pela porta 9000 (API de IA)
if lsof -Pi :9000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}Parando API de IA (porta 9000)...${NC}"
    lsof -ti:9000 | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}✓ API de IA parada${NC}"
else
    echo -e "${YELLOW}API de IA não está rodando${NC}"
fi

# Remover arquivos PID
rm -f logs/api_principal.pid logs/api_ia.pid 2>/dev/null

echo ""
echo -e "${GREEN}✓ Todos os serviços foram parados${NC}"
