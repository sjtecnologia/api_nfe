#!/usr/bin/env python3
"""
Reescreve o template dashboard.html com layout responsivo correto para Bootstrap 5.
"""

NOVA_DASHBOARD = """\
{% extends "base.html" %}

{% block title %}Dashboard - {{ cliente.razao_social }}{% endblock %}

{% block content %}
<div class="container-fluid px-3 px-md-4">

    <!-- Header do Cliente -->
    <div class="row mb-4">
        <div class="col-12">
            <div class="card bg-primary text-white shadow-sm">
                <div class="card-body py-3">
                    <div class="d-flex flex-column flex-sm-row align-items-sm-center justify-content-between gap-3">
                        <div>
                            <h4 class="mb-1 fw-bold"><i class="fas fa-building me-2"></i>{{ cliente.razao_social }}</h4>
                            {% if cliente.nome_fantasia and cliente.nome_fantasia != cliente.razao_social %}
                            <p class="mb-1 opacity-75"><small><strong>Nome Fantasia:</strong> {{ cliente.nome_fantasia }}</small></p>
                            {% endif %}
                            <p class="mb-0">
                                <small>
                                    {% if cliente.produtor_rural and cliente.cpf %}
                                    <strong>CPF:</strong> {{ cliente.cpf[:3] }}.{{ cliente.cpf[3:6] }}.{{ cliente.cpf[6:9] }}-{{ cliente.cpf[9:] }}
                                    {% elif cliente.cnpj %}
                                    <strong>CNPJ:</strong> {{ cliente.cnpj[:2] }}.{{ cliente.cnpj[2:5] }}.{{ cliente.cnpj[5:8] }}/{{ cliente.cnpj[8:12] }}-{{ cliente.cnpj[12:] }}
                                    {% endif %}
                                    {% if cliente.ie %}
                                    &nbsp;|&nbsp;<strong>IE:</strong> {{ cliente.ie }}
                                    {% endif %}
                                </small>
                            </p>
                        </div>
                        <div class="flex-shrink-0">
                            <a href="{{ url_for('cliente.resumo', cliente_id=cliente.cliente_id) }}" class="btn btn-light btn-sm">
                                <i class="fas fa-info-circle me-1"></i>Detalhes
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Estatísticas Principais -->
    <div class="row g-3 mb-4">
        <div class="col-6 col-sm-4 col-md-3 col-xl-2">
            <div class="card border-start border-primary border-4 shadow-sm h-100">
                <div class="card-body py-3">
                    <div class="d-flex align-items-center justify-content-between">
                        <div>
                            <div class="text-xs fw-bold text-primary text-uppercase mb-1">Total Notas</div>
                            <div class="h5 mb-0 fw-bold text-dark">{{ stats.total_nfes }}</div>
                        </div>
                        <i class="fas fa-file-invoice fa-2x text-secondary opacity-50"></i>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-6 col-sm-4 col-md-3 col-xl-2">
            <div class="card border-start border-success border-4 shadow-sm h-100">
                <div class="card-body py-3">
                    <div class="d-flex align-items-center justify-content-between">
                        <div>
                            <div class="text-xs fw-bold text-success text-uppercase mb-1">Notas Ano</div>
                            <div class="h5 mb-0 fw-bold text-dark">{{ stats.nfes_ano }}</div>
                        </div>
                        <i class="fas fa-calendar fa-2x text-secondary opacity-50"></i>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-6 col-sm-4 col-md-3 col-xl-2">
            <div class="card border-start border-info border-4 shadow-sm h-100">
                <div class="card-body py-3">
                    <div class="d-flex align-items-center justify-content-between">
                        <div>
                            <div class="text-xs fw-bold text-info text-uppercase mb-1">NFes Mês</div>
                            <div class="h5 mb-0 fw-bold text-dark">{{ stats.nfes_mes }}</div>
                        </div>
                        <i class="fas fa-calendar-day fa-2x text-secondary opacity-50"></i>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-6 col-sm-4 col-md-3 col-xl-2">
            <div class="card border-start border-warning border-4 shadow-sm h-100">
                <div class="card-body py-3">
                    <div class="d-flex align-items-center justify-content-between">
                        <div>
                            <div class="text-xs fw-bold text-warning text-uppercase mb-1">Produtos</div>
                            <div class="h5 mb-0 fw-bold text-dark">{{ stats.total_produtos }}</div>
                        </div>
                        <i class="fas fa-boxes fa-2x text-secondary opacity-50"></i>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-6 col-sm-4 col-md-3 col-xl-2">
            <div class="card border-start border-secondary border-4 shadow-sm h-100">
                <div class="card-body py-3">
                    <div class="d-flex align-items-center justify-content-between">
                        <div>
                            <div class="text-xs fw-bold text-secondary text-uppercase mb-1">Destinatários</div>
                            <div class="h5 mb-0 fw-bold text-dark">{{ stats.total_destinatarios }}</div>
                        </div>
                        <i class="fas fa-address-book fa-2x text-secondary opacity-50"></i>
                    </div>
                </div>
            </div>
        </div>
        {% if current_user.is_admin() or current_user.is_super_admin() %}
        <div class="col-6 col-sm-4 col-md-3 col-xl-2">
            <div class="card border-start border-dark border-4 shadow-sm h-100">
                <div class="card-body py-3">
                    <div class="d-flex align-items-center justify-content-between">
                        <div>
                            <div class="text-xs fw-bold text-dark text-uppercase mb-1">Certificados</div>
                            <div class="h5 mb-0 fw-bold text-dark">{{ stats.total_certificados }}</div>
                        </div>
                        <i class="fas fa-certificate fa-2x text-secondary opacity-50"></i>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}
    </div>

    <!-- Ações Rápidas -->
    <div class="row mb-4">
        <div class="col-12">
            <div class="card shadow-sm">
                <div class="card-header bg-success text-white py-2">
                    <h6 class="mb-0"><i class="fas fa-bolt me-2"></i>Ações Rápidas</h6>
                </div>
                <div class="card-body py-3">
                    <div class="row g-2">
                        {% if can_create() %}
                        <div class="col-6 col-sm-4 col-md-3 col-lg-2">
                            <a href="{{ url_for('nfe.emitir_nfe') }}?cliente_id={{ cliente.cliente_id }}"
                               class="btn btn-success w-100 h-100 d-flex flex-column align-items-center justify-content-center py-3 gap-1">
                                <i class="fas fa-plus-circle fa-lg"></i>
                                <span class="small fw-bold lh-sm text-center">Emitir NFe</span>
                            </a>
                        </div>
                        {% endif %}
                        <div class="col-6 col-sm-4 col-md-3 col-lg-2">
                            <a href="{{ url_for('nfe.list_nfes') }}?cliente_id={{ cliente.cliente_id }}"
                               class="btn btn-primary w-100 h-100 d-flex flex-column align-items-center justify-content-center py-3 gap-1">
                                <i class="fas fa-list fa-lg"></i>
                                <span class="small fw-bold lh-sm text-center">Ver NFes</span>
                            </a>
                        </div>
                        <div class="col-6 col-sm-4 col-md-3 col-lg-2">
                            <a href="{{ url_for('admin.list_destinatarios', cliente_id=cliente.cliente_id) }}"
                               class="btn btn-warning w-100 h-100 d-flex flex-column align-items-center justify-content-center py-3 gap-1">
                                <i class="fas fa-address-book fa-lg"></i>
                                <span class="small fw-bold lh-sm text-center">Destinatários</span>
                            </a>
                        </div>
                        {% if can_create() %}
                        <div class="col-6 col-sm-4 col-md-3 col-lg-2">
                            <a href="{{ url_for('nfse.emitir_form') }}?cliente_id={{ cliente.cliente_id }}"
                               class="btn btn-primary w-100 h-100 d-flex flex-column align-items-center justify-content-center py-3 gap-1">
                                <i class="fas fa-file-invoice fa-lg"></i>
                                <span class="small fw-bold lh-sm text-center">Emitir NFS-e</span>
                            </a>
                        </div>
                        {% endif %}
                        <div class="col-6 col-sm-4 col-md-3 col-lg-2">
                            <a href="{{ url_for('nfse.list_nfse') }}?cliente_id={{ cliente.cliente_id }}"
                               class="btn btn-outline-primary w-100 h-100 d-flex flex-column align-items-center justify-content-center py-3 gap-1">
                                <i class="fas fa-list-alt fa-lg"></i>
                                <span class="small fw-bold lh-sm text-center">Ver NFS-e</span>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Últimas Notas + Gráfico -->
    <div class="row g-4">
        <!-- Últimas Notas Emitidas -->
        <div class="col-12 col-lg-7">
            <div class="card shadow-sm h-100">
                <div class="card-header py-2">
                    <h6 class="mb-0"><i class="fas fa-history me-2"></i>Últimas Notas Emitidas</h6>
                </div>
                <div class="card-body p-0">
                    {% if ultimas_nfes %}
                    <div class="table-responsive">
                        <table class="table table-striped table-hover table-sm mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th class="ps-3">Tipo</th>
                                    <th>Número</th>
                                    <th>Data</th>
                                    <th>Valor</th>
                                    <th>Status</th>
                                    <th class="pe-3">Ação</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for nfe in ultimas_nfes %}
                                <tr>
                                    <td class="ps-3">
                                        {% if nfe.tipo_documento == 'NFS-e' %}
                                            <span class="badge bg-info">NFS-e</span>
                                        {% elif nfe.tipo_nfe == 'NFCE' %}
                                            <span class="badge bg-warning text-dark">NFC-e</span>
                                        {% else %}
                                            <span class="badge bg-primary">NF-e</span>
                                        {% endif %}
                                    </td>
                                    <td><strong>#{{ nfe.numero if nfe.numero else nfe.id }}</strong></td>
                                    <td class="text-nowrap">{{ nfe.data_criacao.strftime('%d/%m/%Y %H:%M') if nfe.data_criacao else '-' }}</td>
                                    <td class="text-nowrap">R$ {{ "%.2f"|format(nfe.valor_total or 0) }}</td>
                                    <td>
                                        {% if nfe.status|upper == 'AUTORIZADA' %}
                                            <span class="badge bg-success">Autorizada</span>
                                        {% elif nfe.status|upper == 'REJEITADA' %}
                                            <span class="badge bg-danger"
                                                  {% if nfe.mensagem_sefaz %}data-bs-toggle="tooltip" data-bs-placement="top" title="{{ nfe.mensagem_sefaz }}"{% endif %}>
                                                Rejeitada
                                            </span>
                                        {% elif nfe.status|upper == 'PROCESSANDO' %}
                                            <span class="badge bg-warning">Processando</span>
                                        {% elif nfe.status|upper == 'RASCUNHO' %}
                                            <span class="badge bg-secondary">Rascunho</span>
                                        {% else %}
                                            <span class="badge bg-secondary">{{ nfe.status|title if nfe.status else 'N/A' }}</span>
                                        {% endif %}
                                    </td>
                                    <td class="pe-3">
                                        {% if nfe.tipo_documento == 'NFS-e' %}
                                            <a href="{{ url_for('nfse.visualizar', nfse_id=nfe.id) }}" class="btn btn-sm btn-outline-primary"><i class="fas fa-eye"></i></a>
                                        {% elif nfe.tipo_nfe == 'NFCE' %}
                                            <a href="{{ url_for('nfce.consultar_nfce', nfce_id=nfe.id) }}" class="btn btn-sm btn-outline-primary"><i class="fas fa-eye"></i></a>
                                        {% else %}
                                            <a href="{{ url_for('nfe.view', nfe_id=nfe.id) }}" class="btn btn-sm btn-outline-primary"><i class="fas fa-eye"></i></a>
                                        {% endif %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                    <div class="text-center p-3">
                        <a href="{{ url_for('nfe.list_nfes') }}?cliente_id={{ cliente.cliente_id }}" class="btn btn-outline-primary btn-sm">
                            <i class="fas fa-list me-1"></i>Ver Todas as Notas
                        </a>
                    </div>
                    {% else %}
                    <div class="text-center py-5">
                        <i class="fas fa-file-invoice fa-3x text-muted mb-3 d-block"></i>
                        <h6 class="text-muted">Nenhuma nota emitida ainda</h6>
                        <p class="text-muted small">Comece emitindo sua primeira nota fiscal!</p>
                        <a href="{{ url_for('nfe.emitir_nfe') }}?cliente_id={{ cliente.cliente_id }}" class="btn btn-success btn-sm">
                            <i class="fas fa-plus me-1"></i>Emitir Primeira NFe
                        </a>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>

        <!-- Gráfico NFes por Mês -->
        <div class="col-12 col-lg-5">
            <div class="card shadow-sm h-100">
                <div class="card-header py-2 d-flex align-items-center justify-content-between gap-2">
                    <h6 class="mb-0"><i class="fas fa-chart-line me-2"></i>Notas por Mês</h6>
                    <select id="periodoSelect" name="periodo" class="form-select form-select-sm" style="width:auto;">
                        <option value="6" {% if periodo == '6' %}selected{% endif %}>Últimos 6 meses</option>
                        <option value="12" {% if periodo == '12' %}selected{% endif %}>Últimos 12 meses</option>
                        <option value="24" {% if periodo == '24' %}selected{% endif %}>Últimos 24 meses</option>
                        <option value="ano_atual" {% if periodo == 'ano_atual' %}selected{% endif %}>Ano atual</option>
                        <option value="ano_anterior" {% if periodo == 'ano_anterior' %}selected{% endif %}>Ano anterior</option>
                    </select>
                </div>
                <div class="card-body d-flex align-items-center justify-content-center">
                    {% if nfes_por_mes and nfes_por_mes|length > 0 %}
                    <canvas id="nfesChart"></canvas>
                    {% else %}
                    <div class="text-center py-4">
                        <i class="fas fa-chart-line fa-3x text-muted mb-3 d-block"></i>
                        <h6 class="text-muted">Sem dados para gráfico</h6>
                        <p class="text-muted small">Emita algumas NFes para ver as estatísticas.</p>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>

</div>

{% if nfes_por_mes and nfes_por_mes|length > 0 %}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
let nfesChartInstance = null;

function renderNfesChart(chartData) {
    const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
    const labels = [];
    const data = [];

    if (!chartData || chartData.length === 0) return;

    chartData.forEach(function(item) {
        const mes = parseInt(item.mes) || parseInt(item.month) || 1;
        const ano = item.ano || item.year || new Date().getFullYear();
        labels.push(meses[mes - 1] + '/' + ano);
        data.push(item.quantidade || item.count || 0);
    });

    const ctx = document.getElementById('nfesChart');
    if (!ctx) return;

    if (nfesChartInstance) nfesChartInstance.destroy();

    nfesChartInstance = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Notas Emitidas',
                data: data,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                tension: 0.3,
                fill: true,
                borderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: true, labels: { color: '#000', font: { size: 12, weight: 'bold' } } },
                tooltip: { backgroundColor: 'rgba(0,0,0,0.8)', titleColor: '#fff', bodyColor: '#fff', borderColor: 'rgb(75,192,192)', borderWidth: 1 }
            },
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1, color: '#000', font: { size: 11 } }, grid: { color: 'rgba(0,0,0,0.1)' } },
                x: { ticks: { color: '#000', font: { size: 11 } }, grid: { display: false } }
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    try {
        var initialData = {{ nfes_por_mes | tojson | safe }};
        renderNfesChart(initialData);
    } catch (e) {
        console.error('Erro ao renderizar gráfico:', e);
    }

    var periodoSelect = document.getElementById('periodoSelect');
    if (periodoSelect) {
        periodoSelect.addEventListener('change', function() {
            fetch('/cliente/api/nfes_por_mes/{{ cliente.cliente_id }}?periodo=' + periodoSelect.value)
                .then(r => r.json())
                .then(data => renderNfesChart(data))
                .catch(e => console.error('Erro ao buscar dados:', e));
        });
    }

    // Tooltips
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => new bootstrap.Tooltip(el));
});
</script>
{% else %}
<script>
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => new bootstrap.Tooltip(el));
});
</script>
{% endif %}
{% endblock %}
"""

with open('/home/ubuntu/api_nfe/templates/cliente/dashboard.html', 'w') as f:
    f.write(NOVA_DASHBOARD)

print("[OK] dashboard.html reescrito com layout responsivo Bootstrap 5")
