# 🛠️ ESPECIFICAÇÕES TÉCNICAS - GAPS PRIORITÁRIOS

> **Documento Técnico para Implementação**  
> **Data:** 06/11/2025  
> **Autor:** Analista de Negócios + Arquiteto de Sistema

---

## 📋 ÍNDICE DE IMPLEMENTAÇÕES

1. [Dashboard Analytics](#gap-1-dashboard-analytics)
2. [Backup Automático](#gap-3-backup-automático)
3. [Relatórios Fiscais](#gap-2-relatórios-fiscais)
4. [Sistema de Logs e Auditoria](#gap-4-sistema-de-logs-e-auditoria)
5. [Importação em Lote](#gap-5-importação-em-lote)
6. [Cancelamento NFe](#gap-13-cancelamento-nfe)
7. [Inutilização de Numeração](#gap-14-inutilização-de-numeração)
8. [Carta de Correção](#gap-12-carta-de-correção)

---

## GAP 1: DASHBOARD ANALYTICS

### Objetivo
Criar dashboard interativo com KPIs principais e gráficos de tendência.

### Wireframe/Layout
```
┌─────────────────────────────────────────────────────────┐
│                    DASHBOARD NFe                        │
├────────┬────────┬────────┬────────┬────────────────────┤
│ NFes   │ Valor  │ Taxa   │ Cert.  │ Filtros:          │
│ Mês    │ Total  │ Erro   │ Vence  │ [Período] [UF]    │
│ 156    │ 89.5k  │ 0.8%   │ 45d    │                   │
├────────┴────────┴────────┴────────┴────────────────────┤
│ 📊 Emissões por Mês (Últimos 12 meses)                │
│ [Gráfico de linha com Chart.js]                        │
├──────────────────────────────┬──────────────────────────┤
│ 🏆 Top 5 Produtos           │ 📈 Status das NFes      │
│ [Tabela com quantidade]      │ [Gráfico pizza]         │
├──────────────────────────────┴──────────────────────────┤
│ 🤖 Performance da IA                                    │
│ Taxa Acerto NCM: 85% | CEST: 82% | Sugestões: 1.245   │
└─────────────────────────────────────────────────────────┘
```

### Estrutura de Dados

#### Queries SQL Necessárias

**1. KPIs Principais**
```sql
-- NFes do mês atual
SELECT COUNT(*) as total_nfes,
       SUM(valor_total) as valor_total,
       AVG(CASE WHEN status = 'AUTORIZADA' THEN 1 ELSE 0 END) * 100 as taxa_sucesso
FROM nfe_emitidas
WHERE cliente_id = :cliente_id
  AND EXTRACT(MONTH FROM data_criacao) = EXTRACT(MONTH FROM CURRENT_DATE)
  AND EXTRACT(YEAR FROM data_criacao) = EXTRACT(YEAR FROM CURRENT_DATE);

-- Certificado mais próximo do vencimento
SELECT MIN(validade_fim) as proxima_expiracao,
       EXTRACT(DAY FROM MIN(validade_fim) - CURRENT_DATE) as dias_restantes
FROM certificados_digitais
WHERE cliente_id = :cliente_id
  AND ativo = true
  AND validade_fim > CURRENT_DATE;
```

**2. Gráfico Mensal (12 meses)**
```sql
SELECT 
    TO_CHAR(data_criacao, 'YYYY-MM') as mes,
    COUNT(*) as quantidade,
    SUM(valor_total) as valor
FROM nfe_emitidas
WHERE cliente_id = :cliente_id
  AND data_criacao >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY TO_CHAR(data_criacao, 'YYYY-MM')
ORDER BY mes;
```

**3. Top 5 Produtos**
```sql
SELECT 
    p.descricao,
    COUNT(DISTINCT n.nfe_emitida_id) as qtd_nfes,
    SUM(CAST(n.json_nfe->'produtos'->0->>'vProd' AS NUMERIC)) as valor_total
FROM produtos p
JOIN nfe_emitidas n ON n.cliente_id = p.cliente_id
WHERE p.cliente_id = :cliente_id
  AND n.data_criacao >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY p.produto_id, p.descricao
ORDER BY qtd_nfes DESC
LIMIT 5;
```

**4. Status das NFes (Pizza)**
```sql
SELECT 
    status,
    COUNT(*) as quantidade
FROM nfe_emitidas
WHERE cliente_id = :cliente_id
  AND data_criacao >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY status;
```

**5. Performance IA**
```sql
-- Será necessário criar tabela de auditoria de sugestões IA
CREATE TABLE IF NOT EXISTS sugestoes_ia (
    sugestao_id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL,
    produto_descricao TEXT NOT NULL,
    ncm_sugerido VARCHAR(8),
    ncm_selecionado VARCHAR(8),
    cest_sugerido VARCHAR(7),
    cest_selecionado VARCHAR(7),
    acertou_ncm BOOLEAN,
    acertou_cest BOOLEAN,
    data_sugestao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id)
);

-- Query para taxa de acerto
SELECT 
    COUNT(*) as total_sugestoes,
    SUM(CASE WHEN acertou_ncm THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as taxa_acerto_ncm,
    SUM(CASE WHEN acertou_cest THEN 1 ELSE 0 END)::FLOAT / NULLIF(SUM(CASE WHEN cest_sugerido IS NOT NULL THEN 1 ELSE 0 END), 0) * 100 as taxa_acerto_cest
FROM sugestoes_ia
WHERE cliente_id = :cliente_id;
```

### Implementação Frontend

**1. Route (admin_routes.py)**
```python
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal com analytics"""
    cliente_id = session.get('cliente_id')
    
    if not cliente_id:
        flash('Selecione um cliente primeiro', 'warning')
        return redirect(url_for('home.index'))
    
    db = next(get_db())
    
    # KPIs principais
    kpis = db.execute(text("""
        SELECT 
            COUNT(*) as total_nfes,
            COALESCE(SUM(valor_total), 0) as valor_total,
            AVG(CASE WHEN status = 'AUTORIZADA' THEN 1 ELSE 0 END) * 100 as taxa_sucesso
        FROM nfe_emitidas
        WHERE cliente_id = :cliente_id
          AND EXTRACT(MONTH FROM data_criacao) = EXTRACT(MONTH FROM CURRENT_DATE)
          AND EXTRACT(YEAR FROM data_criacao) = EXTRACT(YEAR FROM CURRENT_DATE)
    """), {'cliente_id': cliente_id}).fetchone()
    
    # Certificado expirando
    certificado = db.execute(text("""
        SELECT MIN(validade_fim) as proxima_expiracao,
               EXTRACT(DAY FROM MIN(validade_fim) - CURRENT_DATE) as dias_restantes
        FROM certificados_digitais
        WHERE cliente_id = :cliente_id
          AND ativo = true
          AND validade_fim > CURRENT_DATE
    """), {'cliente_id': cliente_id}).fetchone()
    
    # Dados para gráfico mensal
    grafico_mensal = db.execute(text("""
        SELECT 
            TO_CHAR(data_criacao, 'Mon/YY') as mes,
            COUNT(*) as quantidade,
            COALESCE(SUM(valor_total), 0) as valor
        FROM nfe_emitidas
        WHERE cliente_id = :cliente_id
          AND data_criacao >= CURRENT_DATE - INTERVAL '12 months'
        GROUP BY TO_CHAR(data_criacao, 'YYYY-MM'), TO_CHAR(data_criacao, 'Mon/YY')
        ORDER BY TO_CHAR(data_criacao, 'YYYY-MM')
    """), {'cliente_id': cliente_id}).fetchall()
    
    # Top produtos
    top_produtos = db.execute(text("""
        SELECT 
            p.descricao,
            COUNT(DISTINCT n.nfe_emitida_id) as qtd_nfes
        FROM produtos p
        JOIN nfe_emitidas n ON n.cliente_id = p.cliente_id
        WHERE p.cliente_id = :cliente_id
          AND n.data_criacao >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY p.produto_id, p.descricao
        ORDER BY qtd_nfes DESC
        LIMIT 5
    """), {'cliente_id': cliente_id}).fetchall()
    
    # Status NFes
    status_nfes = db.execute(text("""
        SELECT 
            status,
            COUNT(*) as quantidade
        FROM nfe_emitidas
        WHERE cliente_id = :cliente_id
          AND data_criacao >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY status
    """), {'cliente_id': cliente_id}).fetchall()
    
    return render_template('admin/dashboard.html',
                         kpis=kpis,
                         certificado=certificado,
                         grafico_mensal=grafico_mensal,
                         top_produtos=top_produtos,
                         status_nfes=status_nfes)
```

**2. Template (templates/admin/dashboard.html)**
```html
{% extends "base.html" %}

{% block content %}
<div class="container-fluid">
    <h1 class="mb-4">📊 Dashboard</h1>
    
    <!-- KPIs Cards -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h5 class="card-title">NFes este Mês</h5>
                    <h2 class="text-primary">{{ kpis.total_nfes or 0 }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h5 class="card-title">Valor Total</h5>
                    <h2 class="text-success">R$ {{ "%.2f"|format(kpis.valor_total or 0) }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h5 class="card-title">Taxa de Sucesso</h5>
                    <h2 class="text-info">{{ "%.1f"|format(kpis.taxa_sucesso or 0) }}%</h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center {% if certificado and certificado.dias_restantes < 30 %}border-danger{% endif %}">
                <div class="card-body">
                    <h5 class="card-title">Certificado Vence em</h5>
                    <h2 class="{% if certificado and certificado.dias_restantes < 30 %}text-danger{% else %}text-secondary{% endif %}">
                        {{ certificado.dias_restantes|int if certificado else '∞' }} dias
                    </h2>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Gráfico Mensal -->
    <div class="row mb-4">
        <div class="col-md-12">
            <div class="card">
                <div class="card-header">
                    <h5>📈 Emissões dos Últimos 12 Meses</h5>
                </div>
                <div class="card-body">
                    <canvas id="graficoMensal" height="80"></canvas>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Top Produtos e Status -->
    <div class="row">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5>🏆 Top 5 Produtos (Últimos 30 dias)</h5>
                </div>
                <div class="card-body">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Produto</th>
                                <th class="text-end">Quantidade NFes</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for produto in top_produtos %}
                            <tr>
                                <td>{{ produto.descricao[:50] }}</td>
                                <td class="text-end"><span class="badge bg-primary">{{ produto.qtd_nfes }}</span></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5>📊 Status das NFes (Últimos 30 dias)</h5>
                </div>
                <div class="card-body">
                    <canvas id="graficoStatus" height="200"></canvas>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
<script>
// Gráfico Mensal (Linha)
const dadosMensal = {
    labels: [{% for item in grafico_mensal %}'{{ item.mes }}'{% if not loop.last %},{% endif %}{% endfor %}],
    datasets: [{
        label: 'Quantidade de NFes',
        data: [{% for item in grafico_mensal %}{{ item.quantidade }}{% if not loop.last %},{% endif %}{% endfor %}],
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1,
        fill: false
    }]
};

new Chart(document.getElementById('graficoMensal'), {
    type: 'line',
    data: dadosMensal,
    options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                display: true
            }
        }
    }
});

// Gráfico Status (Pizza)
const dadosStatus = {
    labels: [{% for item in status_nfes %}'{{ item.status }}'{% if not loop.last %},{% endif %}{% endfor %}],
    datasets: [{
        data: [{% for item in status_nfes %}{{ item.quantidade }}{% if not loop.last %},{% endif %}{% endfor %}],
        backgroundColor: [
            'rgb(75, 192, 192)',
            'rgb(255, 99, 132)',
            'rgb(255, 205, 86)',
            'rgb(54, 162, 235)'
        ]
    }]
};

new Chart(document.getElementById('graficoStatus'), {
    type: 'pie',
    data: dadosStatus,
    options: {
        responsive: true,
        maintainAspectRatio: false
    }
});
</script>
{% endblock %}
```

### Checklist de Implementação
- [ ] Criar queries SQL otimizadas
- [ ] Implementar route `/dashboard`
- [ ] Criar template HTML com Bootstrap 5
- [ ] Integrar Chart.js para gráficos
- [ ] Adicionar filtros de período (última semana, mês, ano)
- [ ] Implementar cache para queries pesadas
- [ ] Criar tabela `sugestoes_ia` para tracking
- [ ] Testar performance com grande volume de dados
- [ ] Adicionar responsividade mobile

**Estimativa:** 3-5 dias úteis  
**Prioridade:** P0 - URGENTE

---

## GAP 3: BACKUP AUTOMÁTICO

### Objetivo
Sistema de backup automático diário com rotação e notificações.

### Arquitetura
```
┌─────────────────────────────────────────────┐
│           SISTEMA DE BACKUP                  │
├─────────────────────────────────────────────┤
│ 1. Cron Job (diário 3h da manhã)           │
│    └─> Executa script backup_database.sh   │
│                                             │
│ 2. Script de Backup                         │
│    ├─> pg_dump (PostgreSQL)                │
│    ├─> Compressão gzip                     │
│    ├─> Upload para storage                 │
│    └─> Notificação (email/webhook)         │
│                                             │
│ 3. Rotação de Backups                      │
│    ├─> Manter últimos 7 dias (diário)     │
│    ├─> Manter últimas 4 semanas (semanal) │
│    └─> Manter últimos 12 meses (mensal)   │
│                                             │
│ 4. Storage                                  │
│    ├─> Local: /backups/                   │
│    ├─> S3/MinIO (opcional)                │
│    └─> FTP remoto (opcional)              │
└─────────────────────────────────────────────┘
```

### Script de Backup (backup_database.sh)

```bash
#!/bin/bash

# Configurações
DB_NAME="sjtnfedb"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"
BACKUP_DIR="/opt/backups/nfe"
S3_BUCKET="s3://meu-bucket-nfe/backups"  # Opcional
EMAIL_NOTIFY="admin@empresa.com"
RETENTION_DAYS=7
RETENTION_WEEKS=4
RETENTION_MONTHS=12

# Criar diretórios
mkdir -p $BACKUP_DIR/daily
mkdir -p $BACKUP_DIR/weekly
mkdir -p $BACKUP_DIR/monthly

# Data atual
DATE=$(date +%Y%m%d_%H%M%S)
DAY_OF_WEEK=$(date +%u)
DAY_OF_MONTH=$(date +%d)

# Nome do arquivo
BACKUP_FILE="nfe_backup_$DATE.sql.gz"

# Executar backup
echo "🔄 Iniciando backup em $DATE..."
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/daily/$BACKUP_FILE

# Verificar sucesso
if [ $? -eq 0 ]; then
    echo "✅ Backup criado: $BACKUP_FILE"
    SIZE=$(du -h $BACKUP_DIR/daily/$BACKUP_FILE | cut -f1)
    echo "📦 Tamanho: $SIZE"
    
    # Backup semanal (domingo)
    if [ "$DAY_OF_WEEK" -eq 7 ]; then
        cp $BACKUP_DIR/daily/$BACKUP_FILE $BACKUP_DIR/weekly/
        echo "📅 Backup semanal criado"
    fi
    
    # Backup mensal (dia 1)
    if [ "$DAY_OF_MONTH" -eq "01" ]; then
        cp $BACKUP_DIR/daily/$BACKUP_FILE $BACKUP_DIR/monthly/
        echo "📆 Backup mensal criado"
    fi
    
    # Upload para S3 (opcional)
    if command -v aws &> /dev/null; then
        aws s3 cp $BACKUP_DIR/daily/$BACKUP_FILE $S3_BUCKET/daily/
        echo "☁️ Backup enviado para S3"
    fi
    
    # Rotação de backups
    find $BACKUP_DIR/daily -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
    find $BACKUP_DIR/weekly -name "*.sql.gz" -mtime +$((RETENTION_WEEKS * 7)) -delete
    find $BACKUP_DIR/monthly -name "*.sql.gz" -mtime +$((RETENTION_MONTHS * 30)) -delete
    
    # Notificação de sucesso
    echo "✅ Backup concluído com sucesso em $DATE" | mail -s "Backup NFe OK - $DATE" $EMAIL_NOTIFY
    
else
    echo "❌ ERRO no backup!"
    echo "❌ FALHA no backup em $DATE" | mail -s "ERRO Backup NFe - $DATE" $EMAIL_NOTIFY
    exit 1
fi

echo "✅ Processo de backup finalizado"
```

### Configurar Cron Job

```bash
# Editar crontab
crontab -e

# Adicionar linha (executa todos os dias às 3h da manhã)
0 3 * * * /opt/scripts/backup_database.sh >> /var/log/backup_nfe.log 2>&1
```

### Script de Restore (restore_database.sh)

```bash
#!/bin/bash

# Uso: ./restore_database.sh /caminho/para/backup.sql.gz

BACKUP_FILE=$1
DB_NAME="sjtnfedb"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Uso: $0 <arquivo_backup.sql.gz>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Arquivo não encontrado: $BACKUP_FILE"
    exit 1
fi

echo "⚠️ ATENÇÃO: Esta operação vai SOBRESCREVER o banco de dados atual!"
read -p "Tem certeza? (digite 'CONFIRMAR' para continuar): " CONFIRMACAO

if [ "$CONFIRMACAO" != "CONFIRMAR" ]; then
    echo "❌ Operação cancelada"
    exit 1
fi

echo "🔄 Iniciando restore..."

# Dropar banco (cuidado!)
# dropdb -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME

# Criar banco novamente
# createdb -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME

# Restaurar backup
gunzip -c $BACKUP_FILE | psql -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME

if [ $? -eq 0 ]; then
    echo "✅ Restore concluído com sucesso!"
else
    echo "❌ ERRO no restore!"
    exit 1
fi
```

### Interface Admin (Opcional)

**Route para listar backups**
```python
@admin_bp.route('/backups')
@login_required
def list_backups():
    """Lista backups disponíveis"""
    backup_dir = "/opt/backups/nfe"
    
    backups = []
    for folder in ['daily', 'weekly', 'monthly']:
        folder_path = os.path.join(backup_dir, folder)
        if os.path.exists(folder_path):
            for file in os.listdir(folder_path):
                if file.endswith('.sql.gz'):
                    file_path = os.path.join(folder_path, file)
                    stat = os.stat(file_path)
                    backups.append({
                        'nome': file,
                        'tipo': folder,
                        'tamanho': stat.st_size,
                        'data': datetime.fromtimestamp(stat.st_mtime),
                        'caminho': file_path
                    })
    
    backups.sort(key=lambda x: x['data'], reverse=True)
    
    return render_template('admin/backups.html', backups=backups)

@admin_bp.route('/backups/download/<path:filename>')
@login_required
def download_backup(filename):
    """Download de backup"""
    # Apenas super_admin pode fazer download
    if not current_user.is_super_admin():
        flash('Acesso negado', 'danger')
        return redirect(url_for('admin.list_backups'))
    
    backup_dir = "/opt/backups/nfe"
    return send_from_directory(backup_dir, filename, as_attachment=True)

@admin_bp.route('/backups/executar', methods=['POST'])
@login_required
def executar_backup_manual():
    """Executar backup manualmente"""
    if not current_user.is_super_admin():
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    # Executar script de backup
    result = subprocess.run(['/opt/scripts/backup_database.sh'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        return jsonify({'success': True, 'message': 'Backup executado com sucesso'})
    else:
        return jsonify({'success': False, 'message': 'Erro no backup', 'error': result.stderr}), 500
```

### Checklist de Implementação
- [ ] Criar script backup_database.sh
- [ ] Criar script restore_database.sh
- [ ] Configurar cron job
- [ ] Criar diretórios de backup
- [ ] Configurar permissões (chmod 700)
- [ ] Testar backup manual
- [ ] Testar restore em ambiente de desenvolvimento
- [ ] Configurar notificações por email
- [ ] (Opcional) Integrar com S3/MinIO
- [ ] (Opcional) Criar interface admin
- [ ] Documentar procedimento de restore

**Estimativa:** 2-3 dias úteis  
**Prioridade:** P0 - URGENTE (RISCO LEGAL)

---

## GAP 5: IMPORTAÇÃO EM LOTE

### Objetivo
Permitir importação de produtos e destinatários via CSV/Excel com validação.

### Fluxo de Importação

```
┌─────────────────────────────────────────────┐
│ 1. Upload do Arquivo                        │
│    ├─> CSV (separado por vírgula)          │
│    └─> Excel (.xlsx)                       │
├─────────────────────────────────────────────┤
│ 2. Validação Prévia                         │
│    ├─> Formato correto                     │
│    ├─> Campos obrigatórios                 │
│    ├─> NCM existe na base                  │
│    ├─> CFOP válido                         │
│    └─> Duplicatas (código interno)         │
├─────────────────────────────────────────────┤
│ 3. Pré-visualização                         │
│    ├─> Mostrar primeiras 10 linhas        │
│    ├─> Destacar erros                      │
│    └─> Opção de corrigir ou cancelar      │
├─────────────────────────────────────────────┤
│ 4. Processamento                            │
│    ├─> Inserir no banco em lote           │
│    ├─> Barra de progresso                  │
│    └─> Tratamento de erros por linha      │
├─────────────────────────────────────────────┤
│ 5. Relatório Final                          │
│    ├─> Total processado                    │
│    ├─> Sucesso vs Erros                   │
│    ├─> Lista de erros (download CSV)      │
│    └─> Opção de reprocessar erros         │
└─────────────────────────────────────────────┘
```

### Formato CSV/Excel - Produtos

**Template (produtos_importacao.csv)**
```csv
codigo_interno,descricao,ncm_codigo,cest,cfop_codigo,unidade_comercial,preco_unitario,origem_mercadoria,tipo_item
PROD001,Notebook Dell Inspiron 15,84713000,,5101,UN,3500.00,0,Produto
PROD002,Mouse USB Logitech,84716053,,5101,UN,45.90,0,Produto
PROD003,Serviço de Desenvolvimento,21069000,,5101,UN,1500.00,0,Serviço
```

**Campos:**
- `codigo_interno` (obrigatório): Código único do produto
- `descricao` (obrigatório): Descrição do produto
- `ncm_codigo` (obrigatório): Código NCM (8 dígitos)
- `cest` (opcional): Código CEST (7 dígitos)
- `cfop_codigo` (opcional): Código CFOP
- `unidade_comercial` (obrigatório): UN, KG, M, etc.
- `preco_unitario` (obrigatório): Preço em formato decimal
- `origem_mercadoria` (obrigatório): 0-8 (tabela SEFAZ)
- `tipo_item` (obrigatório): Produto ou Serviço

### Implementação Backend

**Route para upload**
```python
@admin_bp.route('/produtos/importar', methods=['GET', 'POST'])
@login_required
def importar_produtos():
    """Importação em lote de produtos"""
    cliente_id = session.get('cliente_id')
    
    if not cliente_id:
        flash('Selecione um cliente', 'warning')
        return redirect(url_for('home.index'))
    
    if request.method == 'GET':
        return render_template('admin/produtos/importar.html')
    
    # POST - processar arquivo
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(request.url)
    
    arquivo = request.files['arquivo']
    
    if arquivo.filename == '':
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(request.url)
    
    # Validar extensão
    if not arquivo.filename.endswith(('.csv', '.xlsx')):
        flash('Formato inválido. Use CSV ou XLSX', 'danger')
        return redirect(request.url)
    
    try:
        # Processar arquivo
        import pandas as pd
        import io
        
        if arquivo.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(arquivo.read()))
        else:
            df = pd.read_excel(io.BytesIO(arquivo.read()))
        
        # Validar colunas obrigatórias
        colunas_obrigatorias = ['codigo_interno', 'descricao', 'ncm_codigo', 
                               'unidade_comercial', 'preco_unitario', 
                               'origem_mercadoria', 'tipo_item']
        
        colunas_faltando = set(colunas_obrigatorias) - set(df.columns)
        if colunas_faltando:
            flash(f'Colunas faltando: {", ".join(colunas_faltando)}', 'danger')
            return redirect(request.url)
        
        # Validar dados
        erros = []
        produtos_validos = []
        
        db = next(get_db())
        
        for idx, row in df.iterrows():
            linha = idx + 2  # +2 porque pandas começa em 0 e CSV tem cabeçalho
            
            # Validações
            if pd.isna(row['codigo_interno']) or str(row['codigo_interno']).strip() == '':
                erros.append(f'Linha {linha}: Código interno vazio')
                continue
            
            if pd.isna(row['descricao']) or str(row['descricao']).strip() == '':
                erros.append(f'Linha {linha}: Descrição vazia')
                continue
            
            # Validar NCM existe
            ncm_codigo = str(row['ncm_codigo']).strip().zfill(8)
            ncm = db.execute(text("SELECT ncm_id FROM ncms WHERE codigo = :codigo"), 
                           {'codigo': ncm_codigo}).fetchone()
            
            if not ncm:
                erros.append(f'Linha {linha}: NCM {ncm_codigo} não encontrado na base')
                continue
            
            # Validar preço
            try:
                preco = float(row['preco_unitario'])
                if preco <= 0:
                    erros.append(f'Linha {linha}: Preço deve ser maior que zero')
                    continue
            except (ValueError, TypeError):
                erros.append(f'Linha {linha}: Preço inválido')
                continue
            
            # Validar origem mercadoria
            origem = str(row['origem_mercadoria']).strip()
            if origem not in ['0', '1', '2', '3', '4', '5', '6', '7', '8']:
                erros.append(f'Linha {linha}: Origem mercadoria inválida (deve ser 0-8)')
                continue
            
            origem_obj = db.execute(text("SELECT origem_id FROM origens_mercadoria WHERE codigo = :codigo"), 
                                  {'codigo': origem}).fetchone()
            
            if not origem_obj:
                erros.append(f'Linha {linha}: Origem {origem} não encontrada')
                continue
            
            # Validar tipo item
            tipo_item = str(row['tipo_item']).strip()
            if tipo_item not in ['Produto', 'Serviço']:
                erros.append(f'Linha {linha}: Tipo item deve ser "Produto" ou "Serviço"')
                continue
            
            # Produto válido
            produtos_validos.append({
                'codigo_interno': str(row['codigo_interno']).strip(),
                'descricao': str(row['descricao']).strip(),
                'ncm_id': ncm.ncm_id,
                'cest': str(row['cest']).strip() if not pd.isna(row.get('cest')) else None,
                'unidade_comercial': str(row['unidade_comercial']).strip().upper(),
                'preco_unitario': preco,
                'origem_mercadoria': origem_obj.origem_id,
                'tipo_item': tipo_item,
                'ativo': True,
                'cliente_id': cliente_id,
                'created_by_user_id': current_user.id
            })
        
        # Se houver erros, mostrar relatório
        if erros:
            session['erros_importacao'] = erros
            session['produtos_validos'] = len(produtos_validos)
            flash(f'{len(erros)} erros encontrados. {len(produtos_validos)} produtos válidos.', 'warning')
            return render_template('admin/produtos/importar_resultado.html', 
                                 erros=erros, 
                                 total=len(df),
                                 validos=len(produtos_validos))
        
        # Inserir produtos válidos
        from database.models import Produto
        
        produtos_inseridos = 0
        for produto_data in produtos_validos:
            try:
                db.execute(text("""
                    INSERT INTO produtos 
                    (cliente_id, codigo_interno, descricao, ncm_id, cest, 
                     unidade_comercial, preco_unitario_padrao, origem_mercadoria, 
                     tipo_item, ativo, created_by_user_id)
                    VALUES 
                    (:cliente_id, :codigo_interno, :descricao, :ncm_id, :cest,
                     :unidade_comercial, :preco_unitario, :origem_mercadoria,
                     :tipo_item, :ativo, :created_by_user_id)
                    ON CONFLICT (cliente_id, codigo_interno) DO UPDATE SET
                        descricao = EXCLUDED.descricao,
                        ncm_id = EXCLUDED.ncm_id,
                        cest = EXCLUDED.cest,
                        preco_unitario_padrao = EXCLUDED.preco_unitario_padrao
                """), produto_data)
                produtos_inseridos += 1
            except Exception as e:
                erros.append(f'Erro ao inserir {produto_data["codigo_interno"]}: {str(e)}')
        
        db.commit()
        
        flash(f'{produtos_inseridos} produtos importados com sucesso!', 'success')
        return redirect(url_for('admin.list_produtos'))
        
    except Exception as e:
        flash(f'Erro ao processar arquivo: {str(e)}', 'danger')
        import traceback
        traceback.print_exc()
        return redirect(request.url)
```

### Template de Importação

**templates/admin/produtos/importar.html**
```html
{% extends "base.html" %}

{% block content %}
<div class="container">
    <h1 class="mb-4">📤 Importar Produtos em Lote</h1>
    
    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5>Upload de Arquivo</h5>
                </div>
                <div class="card-body">
                    <form method="POST" enctype="multipart/form-data">
                        <div class="mb-3">
                            <label for="arquivo" class="form-label">Arquivo CSV ou Excel</label>
                            <input type="file" class="form-control" id="arquivo" name="arquivo" 
                                   accept=".csv,.xlsx" required>
                            <div class="form-text">
                                Formatos aceitos: .csv, .xlsx (máx 10MB)
                            </div>
                        </div>
                        
                        <div class="alert alert-info">
                            <strong>ℹ️ Importante:</strong>
                            <ul class="mb-0">
                                <li>O arquivo deve conter cabeçalho com nomes das colunas</li>
                                <li>Produtos duplicados (mesmo código interno) serão atualizados</li>
                                <li>NCMs devem existir na base de dados</li>
                                <li>Validação é feita antes da importação</li>
                            </ul>
                        </div>
                        
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-upload"></i> Importar
                        </button>
                        <a href="{{ url_for('admin.list_produtos') }}" class="btn btn-secondary">
                            Cancelar
                        </a>
                    </form>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h5>📥 Template</h5>
                </div>
                <div class="card-body">
                    <p>Baixe o template de exemplo para garantir o formato correto:</p>
                    <a href="{{ url_for('admin.download_template_produtos') }}" 
                       class="btn btn-success btn-block">
                        <i class="fas fa-download"></i> Baixar Template CSV
                    </a>
                    <a href="{{ url_for('admin.download_template_produtos_xlsx') }}" 
                       class="btn btn-success btn-block mt-2">
                        <i class="fas fa-download"></i> Baixar Template Excel
                    </a>
                </div>
            </div>
            
            <div class="card mt-3">
                <div class="card-header">
                    <h5>📋 Colunas Obrigatórias</h5>
                </div>
                <div class="card-body">
                    <ul class="list-unstyled">
                        <li>✅ codigo_interno</li>
                        <li>✅ descricao</li>
                        <li>✅ ncm_codigo (8 dígitos)</li>
                        <li>⚠️ cest (opcional)</li>
                        <li>⚠️ cfop_codigo (opcional)</li>
                        <li>✅ unidade_comercial</li>
                        <li>✅ preco_unitario</li>
                        <li>✅ origem_mercadoria (0-8)</li>
                        <li>✅ tipo_item (Produto/Serviço)</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### Route para Download de Template

```python
@admin_bp.route('/produtos/template/csv')
@login_required
def download_template_produtos():
    """Download template CSV"""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Cabeçalho
    writer.writerow(['codigo_interno', 'descricao', 'ncm_codigo', 'cest', 
                    'cfop_codigo', 'unidade_comercial', 'preco_unitario', 
                    'origem_mercadoria', 'tipo_item'])
    
    # Exemplos
    writer.writerow(['PROD001', 'Notebook Dell Inspiron 15', '84713000', '', 
                    '5101', 'UN', '3500.00', '0', 'Produto'])
    writer.writerow(['PROD002', 'Mouse USB Logitech', '84716053', '', 
                    '5101', 'UN', '45.90', '0', 'Produto'])
    writer.writerow(['SERV001', 'Serviço de Desenvolvimento', '21069000', '', 
                    '5101', 'UN', '1500.00', '0', 'Serviço'])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=template_produtos.csv'}
    )

@admin_bp.route('/produtos/template/xlsx')
@login_required
def download_template_produtos_xlsx():
    """Download template Excel"""
    import pandas as pd
    import io
    
    data = {
        'codigo_interno': ['PROD001', 'PROD002', 'SERV001'],
        'descricao': ['Notebook Dell Inspiron 15', 'Mouse USB Logitech', 'Serviço de Desenvolvimento'],
        'ncm_codigo': ['84713000', '84716053', '21069000'],
        'cest': ['', '', ''],
        'cfop_codigo': ['5101', '5101', '5101'],
        'unidade_comercial': ['UN', 'UN', 'UN'],
        'preco_unitario': [3500.00, 45.90, 1500.00],
        'origem_mercadoria': [0, 0, 0],
        'tipo_item': ['Produto', 'Produto', 'Serviço']
    }
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Produtos')
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=template_produtos.xlsx'}
    )
```

### Checklist de Implementação
- [ ] Instalar dependências (pandas, openpyxl)
- [ ] Criar route de importação
- [ ] Implementar validações robustas
- [ ] Criar templates de upload e resultado
- [ ] Implementar download de templates
- [ ] Adicionar barra de progresso (JavaScript)
- [ ] Implementar tratamento de erros por linha
- [ ] Criar relatório de erros (download CSV)
- [ ] Testar com arquivos grandes (1000+ linhas)
- [ ] Adicionar limite de tamanho de arquivo
- [ ] Documentar processo de importação

**Estimativa:** 4-5 dias úteis  
**Prioridade:** P1 - ALTA

---

## 📊 RESUMO DE ESFORÇO TOTAL

| Gap | Dias Úteis | Prioridade | Dependências |
|-----|-----------|------------|--------------|
| Dashboard Analytics | 3-5 | P0 | Chart.js, queries SQL |
| Backup Automático | 2-3 | P0 | Cron, pg_dump, email |
| Relatórios Fiscais | 5-7 | P1 | Dashboard, queries complexas |
| Logs e Auditoria | 4-6 | P1 | Triggers SQL, middleware |
| Importação em Lote | 4-5 | P1 | pandas, openpyxl |
| Cancelamento NFe | 2 | P2 | SEFAZ service |
| Inutilização | 1 | P2 | SEFAZ service |
| Carta de Correção | 2 | P2 | SEFAZ service |

**TOTAL ESTIMADO: 23-31 dias úteis (~5-6 semanas)**

---

*Documento técnico criado por: Analista de Negócios + Arquiteto*  
*Data: 06/11/2025*  
*Para implementação: Equipe de Desenvolvimento*
