#!/bin/bash

# Aliases e Funções Úteis para Gerenciamento da API NFe na AWS
# Cole este conteúdo no final do arquivo ~/.bashrc do servidor EC2

# ============================================
# ALIASES DE STATUS
# ============================================

alias nfe-status='sudo systemctl status api-nfe-principal api-nfe-ia ollama nginx'
alias nfe-status-full='systemctl list-units | grep -E "api-nfe|ollama|nginx"'

# ============================================
# ALIASES DE LOGS
# ============================================

alias nfe-logs='sudo journalctl -u api-nfe-principal -f'
alias ia-logs='sudo journalctl -u api-nfe-ia -f'
alias ollama-logs='sudo journalctl -u ollama -f'
alias nginx-logs='sudo tail -f /var/log/nginx/error.log'
alias nginx-access='sudo tail -f /var/log/nginx/access.log'

# Ver últimas 50 linhas de cada serviço
alias nfe-logs-last='sudo journalctl -u api-nfe-principal -n 50 --no-pager'
alias ia-logs-last='sudo journalctl -u api-nfe-ia -n 50 --no-pager'
alias ollama-logs-last='sudo journalctl -u ollama -n 50 --no-pager'

# ============================================
# ALIASES DE CONTROLE
# ============================================

alias nfe-restart='sudo systemctl restart api-nfe-principal api-nfe-ia ollama nginx'
alias nfe-stop='sudo systemctl stop api-nfe-principal api-nfe-ia'
alias nfe-start='sudo systemctl start api-nfe-principal api-nfe-ia'

alias nfe-restart-app='sudo systemctl restart api-nfe-principal'
alias nfe-restart-ia='sudo systemctl restart api-nfe-ia'
alias nfe-restart-nginx='sudo systemctl restart nginx'

# ============================================
# ALIASES DE BACKUP
# ============================================

alias nfe-backup='bash /home/ubuntu/backup-database.sh'
alias nfe-backup-logs='tail -f /home/ubuntu/api_nfe/logs/backup.log'
alias nfe-list-backups='ls -lh /home/ubuntu/api_nfe/backups/'

# ============================================
# ALIASES DE RECURSOS
# ============================================

alias nfe-resources='free -h && echo "" && df -h'
alias nfe-top='htop'
alias nfe-ports='sudo netstat -tulpn | grep -E "8080|8081|11434|80|443"'
alias nfe-processes='ps aux | grep -E "python|gunicorn|uvicorn|ollama|nginx" | grep -v grep'

# ============================================
# ALIASES DE ATUALIZAÇÃO
# ============================================

alias nfe-update='cd /home/ubuntu/api_nfe/deployment && bash atualizar_codigo_aws.sh'
alias nfe-git-pull='cd /home/ubuntu/api_nfe && git pull'
alias nfe-pip-install='cd /home/ubuntu/api_nfe && source venv/bin/activate && pip install -r requirements.txt'

# ============================================
# ALIASES DE DIAGNÓSTICO
# ============================================

alias nfe-check='curl -s http://localhost:8080/health && echo ""'
alias ia-check='curl -s http://localhost:8081/docs | head -20'
alias ollama-check='curl -s http://localhost:11434/api/tags | python3 -m json.tool'
alias nginx-check='sudo nginx -t'

# ============================================
# ALIASES DE AMBIENTE
# ============================================

alias nfe-env='cd /home/ubuntu/api_nfe && cat .env'
alias nfe-env-edit='nano /home/ubuntu/api_nfe/.env'
alias nfe-venv='cd /home/ubuntu/api_nfe && source venv/bin/activate'

# ============================================
# ALIASES DE CERTIFICADOS
# ============================================

alias ssl-renew='sudo certbot renew --force-renewal'
alias ssl-status='sudo certbot certificates'

# ============================================
# FUNÇÕES ÚTEIS
# ============================================

# Diagnóstico completo do sistema
nfe-diagnostico() {
    echo "=========================================="
    echo "DIAGNÓSTICO COMPLETO - API NFe"
    echo "=========================================="
    echo ""
    
    echo "📊 STATUS DOS SERVIÇOS"
    echo "----------------------------------------"
    systemctl is-active api-nfe-principal && echo "✅ Flask App: RODANDO" || echo "❌ Flask App: PARADO"
    systemctl is-active api-nfe-ia && echo "✅ IA Service: RODANDO" || echo "❌ IA Service: PARADO"
    systemctl is-active ollama && echo "✅ Ollama: RODANDO" || echo "❌ Ollama: PARADO"
    systemctl is-active nginx && echo "✅ Nginx: RODANDO" || echo "❌ Nginx: PARADO"
    echo ""
    
    echo "🔌 PORTAS EM USO"
    echo "----------------------------------------"
    sudo netstat -tulpn | grep -E '8080|8081|11434|80|443'
    echo ""
    
    echo "💾 USO DE RECURSOS"
    echo "----------------------------------------"
    free -h
    echo ""
    df -h | grep -E 'Filesystem|/$'
    echo ""
    
    echo "🔍 PROCESSOS PYTHON"
    echo "----------------------------------------"
    ps aux | grep -E 'python|gunicorn|uvicorn' | grep -v grep | awk '{print $2, $3, $4, $11}'
    echo ""
    
    echo "📝 ÚLTIMOS LOGS (Flask App)"
    echo "----------------------------------------"
    sudo journalctl -u api-nfe-principal -n 5 --no-pager
    echo ""
    
    echo "📝 ÚLTIMOS LOGS (IA Service)"
    echo "----------------------------------------"
    sudo journalctl -u api-nfe-ia -n 5 --no-pager
    echo ""
}

# Verificar saúde do sistema
nfe-health() {
    echo "🏥 VERIFICAÇÃO DE SAÚDE"
    echo "========================"
    echo ""
    
    # Flask App
    if curl -s http://localhost:8080/health > /dev/null; then
        echo "✅ Flask App: OK"
    else
        echo "❌ Flask App: FALHA"
    fi
    
    # IA Service
    if curl -s http://localhost:8081/docs > /dev/null; then
        echo "✅ IA Service: OK"
    else
        echo "❌ IA Service: FALHA"
    fi
    
    # Ollama
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        echo "✅ Ollama: OK"
    else
        echo "❌ Ollama: FALHA"
    fi
    
    # Nginx
    if curl -s http://localhost > /dev/null; then
        echo "✅ Nginx: OK"
    else
        echo "❌ Nginx: FALHA"
    fi
    
    # Banco de dados
    cd /home/ubuntu/api_nfe
    source .env 2>/dev/null
    if psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
        echo "✅ Banco de Dados: OK"
    else
        echo "❌ Banco de Dados: FALHA"
    fi
    
    echo ""
}

# Limpar logs antigos
nfe-clean-logs() {
    echo "🧹 Limpando logs antigos..."
    sudo journalctl --vacuum-time=7d
    find /home/ubuntu/api_nfe/logs -name "*.log" -mtime +7 -delete
    echo "✅ Logs limpos!"
}

# Limpar backups antigos (mais de 30 dias)
nfe-clean-backups() {
    echo "🧹 Limpando backups antigos (>30 dias)..."
    find /home/ubuntu/api_nfe/backups -name "backup_*.dump" -mtime +30 -delete
    echo "✅ Backups antigos removidos!"
    echo "Backups restantes:"
    ls -lh /home/ubuntu/api_nfe/backups/
}

# Ver erros recentes
nfe-errors() {
    echo "🚨 ERROS RECENTES"
    echo "=================="
    echo ""
    echo "Flask App:"
    sudo journalctl -u api-nfe-principal --since "1 hour ago" --no-pager | grep -i error | tail -20
    echo ""
    echo "IA Service:"
    sudo journalctl -u api-nfe-ia --since "1 hour ago" --no-pager | grep -i error | tail -20
    echo ""
}

# Estatísticas de uso
nfe-stats() {
    echo "📊 ESTATÍSTICAS DE USO"
    echo "======================"
    echo ""
    
    # Uptime dos serviços
    echo "⏱️  Uptime:"
    systemctl show api-nfe-principal --property=ActiveEnterTimestamp --no-pager
    
    echo ""
    echo "💾 Uso de Disco:"
    du -sh /home/ubuntu/api_nfe 2>/dev/null
    du -sh /home/ubuntu/api_nfe/logs 2>/dev/null
    du -sh /home/ubuntu/api_nfe/backups 2>/dev/null
    
    echo ""
    echo "📦 Últimos Backups:"
    ls -lht /home/ubuntu/api_nfe/backups/ | head -5
    
    echo ""
    echo "🔗 Requisições Nginx (últimas 24h):"
    sudo cat /var/log/nginx/access.log | wc -l
}

# Atualizar tudo
nfe-update-all() {
    echo "🔄 ATUALIZAÇÃO COMPLETA"
    echo "======================="
    echo ""
    
    # Atualizar sistema
    echo "1️⃣ Atualizando sistema Ubuntu..."
    sudo apt update && sudo apt upgrade -y
    
    # Atualizar código
    echo ""
    echo "2️⃣ Atualizando código da aplicação..."
    cd /home/ubuntu/api_nfe
    git pull
    
    # Atualizar dependências
    echo ""
    echo "3️⃣ Atualizando dependências Python..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Reiniciar serviços
    echo ""
    echo "4️⃣ Reiniciando serviços..."
    sudo systemctl restart api-nfe-principal api-nfe-ia
    
    echo ""
    echo "✅ Atualização completa!"
}

# Reiniciar apenas se necessário
nfe-restart-if-needed() {
    if ! systemctl is-active --quiet api-nfe-principal; then
        echo "Reiniciando Flask App..."
        sudo systemctl restart api-nfe-principal
    fi
    
    if ! systemctl is-active --quiet api-nfe-ia; then
        echo "Reiniciando IA Service..."
        sudo systemctl restart api-nfe-ia
    fi
    
    echo "✅ Verificação concluída"
}

# Monitorar logs de todos os serviços
nfe-logs-all() {
    sudo journalctl -u api-nfe-principal -u api-nfe-ia -u ollama -f
}

# IP público da instância
nfe-ip() {
    curl -s http://169.254.169.254/latest/meta-data/public-ipv4
    echo ""
}

# Informações do sistema
nfe-info() {
    echo "ℹ️  INFORMAÇÕES DO SISTEMA"
    echo "=========================="
    echo ""
    echo "IP Público: $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
    echo "IP Privado: $(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)"
    echo "Instance ID: $(curl -s http://169.254.169.254/latest/meta-data/instance-id)"
    echo "Instance Type: $(curl -s http://169.254.169.254/latest/meta-data/instance-type)"
    echo "Availability Zone: $(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)"
    echo ""
    echo "Sistema: $(lsb_release -d | cut -f2)"
    echo "Kernel: $(uname -r)"
    echo "Uptime: $(uptime -p)"
    echo ""
}

# ============================================
# MENSAGEM DE BOAS-VINDAS
# ============================================

echo ""
echo "🚀 Comandos API NFe carregados!"
echo ""
echo "Comandos disponíveis:"
echo "  nfe-status        - Ver status de todos os serviços"
echo "  nfe-logs          - Ver logs em tempo real (Flask)"
echo "  ia-logs           - Ver logs em tempo real (IA)"
echo "  nfe-restart       - Reiniciar todos os serviços"
echo "  nfe-backup        - Fazer backup manual do banco"
echo "  nfe-update        - Atualizar código da aplicação"
echo "  nfe-diagnostico   - Diagnóstico completo do sistema"
echo "  nfe-health        - Verificar saúde de todos os serviços"
echo "  nfe-info          - Informações do sistema"
echo ""
echo "Para lista completa: grep '^alias nfe' ~/.bashrc"
echo ""
