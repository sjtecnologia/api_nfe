#!/bin/bash

# 🚀 Script de Inicialização Completa - APIs de IA
# Gerencia todos os serviços necessários para a API IA Unificada

set -e  # Sair em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para imprimir com cores
print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Verifica se está no diretório correto
if [ ! -f "api_ia_unificada.py" ]; then
    print_error "Arquivo api_ia_unificada.py não encontrado!"
    print_info "Execute este script do diretório /Users/renato/Documents/Developement/api_nfe"
    exit 1
fi

# Função para verificar se uma porta está em uso
check_port() {
    lsof -i :"$1" > /dev/null 2>&1
}

# Função para matar processo em uma porta
kill_port() {
    if check_port "$1"; then
        print_warning "Porta $1 em uso. Encerrando processo..."
        lsof -ti :"$1" | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
}

# Limpar logs antigos
cleanup_logs() {
    print_info "Limpando logs antigos..."
    rm -f ncm_api.log ia_api.log
}

# Verificar dependências
check_dependencies() {
    print_header "Verificando Dependências"
    
    # Verifica Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 não encontrado!"
        exit 1
    fi
    print_success "Python 3: $(python3 --version)"
    
    # Verifica venv
    if [ ! -d "venv" ]; then
        print_warning "Virtual environment não encontrado. Criando..."
        python3 -m venv venv
    fi
    print_success "Virtual environment: OK"
    
    # Ativa venv
    source venv/bin/activate
    
    # Verifica pacotes necessários
    print_info "Verificando pacotes Python..."
    pip install -q flask flask-cors requests 2>/dev/null || true
    print_success "Pacotes Python: OK"
    
    # Verifica arquivos de dados
    if [ ! -f "Tabela_NCM_Vigente_20251029.json" ] && [ ! -f "ncms_training_data.json" ]; then
        print_error "Arquivo de dados NCM não encontrado!"
        print_info "Necessário: Tabela_NCM_Vigente_20251029.json ou ncms_training_data.json"
        exit 1
    fi
    print_success "Arquivo de dados NCM: OK"
    
    echo
}

# Iniciar API NCM
start_ncm_api() {
    print_header "Iniciando API NCM (Porta 8081)"
    
    # Mata processo na porta se existir
    kill_port 8081
    
    # Inicia API NCM em background
    source venv/bin/activate
    nohup python3 api_ncm_standalone.py > ncm_api.log 2>&1 &
    NCM_PID=$!
    
    print_info "Aguardando API NCM inicializar..."
    sleep 3
    
    # Verifica se iniciou
    if check_port 8081; then
        print_success "API NCM rodando na porta 8081 (PID: $NCM_PID)"
        
        # Testa endpoint
        if curl -s http://localhost:8081/health > /dev/null; then
            TOTAL_NCMS=$(curl -s http://localhost:8081/health | python3 -c "import sys, json; print(json.load(sys.stdin)['total_ncms'])")
            print_success "API NCM respondendo! Total NCMs: $TOTAL_NCMS"
        fi
    else
        print_error "Falha ao iniciar API NCM. Verifique ncm_api.log"
        cat ncm_api.log
        exit 1
    fi
    
    echo
}

# Verificar LLM
check_llm() {
    print_header "Verificando LLM (192.168.0.52:1234)"
    
    if curl -s http://192.168.0.52:1234/v1/models > /dev/null 2>&1; then
        MODEL=$(curl -s http://192.168.0.52:1234/v1/models | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['data'][0]['id'] if data.get('data') else 'N/A')" 2>/dev/null || echo "N/A")
        print_success "LLM respondendo! Modelo: $MODEL"
    else
        print_warning "LLM não está acessível em http://192.168.0.52:1234"
        print_info "A API funcionará em modo fallback (sem LLM)"
    fi
    
    echo
}

# Iniciar API IA Unificada
start_ia_api() {
    print_header "Iniciando API IA Unificada (Porta 9000)"
    
    # Mata processo na porta se existir
    kill_port 9000
    
    # Inicia API IA em background
    source venv/bin/activate
    nohup python3 api_ia_unificada.py > ia_api.log 2>&1 &
    IA_PID=$!
    
    print_info "Aguardando API IA inicializar..."
    sleep 3
    
    # Verifica se iniciou
    if check_port 9000; then
        print_success "API IA Unificada rodando na porta 9000 (PID: $IA_PID)"
        
        # Testa endpoint
        if curl -s http://localhost:9000/health > /dev/null; then
            print_success "API IA respondendo!"
        fi
    else
        print_error "Falha ao iniciar API IA. Verifique ia_api.log"
        cat ia_api.log
        exit 1
    fi
    
    echo
}

# Exibir resumo
show_summary() {
    print_header "🎉 Serviços Iniciados com Sucesso!"
    
    echo -e "${GREEN}📡 SERVIÇOS RODANDO:${NC}"
    echo "   • API NCM: http://localhost:8081"
    echo "   • API IA Unificada: http://localhost:9000"
    echo
    
    echo -e "${BLUE}📚 ENDPOINTS DISPONÍVEIS:${NC}"
    echo "   • GET  http://localhost:9000/ - Documentação"
    echo "   • POST http://localhost:9000/api/sugestao - Sugestão tributária"
    echo "   • GET  http://localhost:9000/api/ncm/search?q={termo} - Buscar NCM"
    echo "   • GET  http://localhost:9000/health - Health check"
    echo "   • GET  http://localhost:9000/api/status - Status detalhado"
    echo
    
    echo -e "${YELLOW}🧪 TESTE RÁPIDO:${NC}"
    echo '   curl -X POST http://localhost:9000/api/sugestao \'
    echo '     -H "Content-Type: application/json" \'
    echo '     -d '"'"'{"descricao": "Smartphone Samsung", "tipo_item": "Produto", "uf_origem": "SP"}'"'"
    echo
    
    echo -e "${BLUE}📊 MONITORAMENTO:${NC}"
    echo "   • tail -f ncm_api.log - Logs API NCM"
    echo "   • tail -f ia_api.log - Logs API IA"
    echo
    
    echo -e "${RED}🛑 PARAR SERVIÇOS:${NC}"
    echo "   • ./stop_apis.sh - Parar todas as APIs"
    echo "   • kill $NCM_PID - Parar apenas API NCM"
    echo "   • kill $IA_PID - Parar apenas API IA"
    echo
    
    # Salvar PIDs
    echo "$NCM_PID" > ncm_api.pid
    echo "$IA_PID" > ia_api.pid
    
    print_success "PIDs salvos em ncm_api.pid e ia_api.pid"
}

# Função principal
main() {
    clear
    print_header "🚀 Inicializando APIs de IA"
    echo
    
    cleanup_logs
    check_dependencies
    start_ncm_api
    check_llm
    start_ia_api
    show_summary
}

# Executa
main
