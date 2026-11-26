#!/bin/bash

# 🛑 Script para Parar todas as APIs

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${YELLOW}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo "🛑 Parando APIs de IA..."
echo

# Função para matar processo em uma porta
kill_port() {
    PORT=$1
    NAME=$2
    
    if lsof -i :$PORT > /dev/null 2>&1; then
        print_info "Encerrando $NAME na porta $PORT..."
        lsof -ti :$PORT | xargs kill -9 2>/dev/null || true
        sleep 1
        
        if ! lsof -i :$PORT > /dev/null 2>&1; then
            print_success "$NAME encerrado"
        else
            print_error "Falha ao encerrar $NAME"
        fi
    else
        print_info "$NAME não está rodando na porta $PORT"
    fi
}

# Parar API NCM (porta 8081)
kill_port 8081 "API NCM"

# Parar API IA Unificada (porta 9000)
kill_port 9000 "API IA Unificada"

# Remover arquivos de PID
rm -f ncm_api.pid ia_api.pid

# Limpar logs se desejar
read -p "Deseja limpar os logs? (s/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    rm -f ncm_api.log ia_api.log
    print_success "Logs removidos"
fi

echo
print_success "Todas as APIs foram encerradas!"
