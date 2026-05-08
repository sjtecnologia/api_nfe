#!/usr/bin/env python3
"""
Centraliza e distribui uniformemente os botões de Ações Rápidas no dashboard.
"""

filepath = '/home/ubuntu/api_nfe/templates/cliente/dashboard.html'
content = open(filepath).read()

old = """                <div class="card-body py-3">
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
                </div>"""

new = """                <div class="card-body py-3">
                    <div class="d-flex flex-wrap justify-content-center gap-3">
                        {% if can_create() %}
                        <a href="{{ url_for('nfe.emitir_nfe') }}?cliente_id={{ cliente.cliente_id }}"
                           class="btn btn-success d-flex flex-column align-items-center justify-content-center py-3 px-4 gap-1" style="min-width:130px; min-height:80px;">
                            <i class="fas fa-plus-circle fa-lg"></i>
                            <span class="small fw-bold">Emitir NFe</span>
                        </a>
                        {% endif %}
                        <a href="{{ url_for('nfe.list_nfes') }}?cliente_id={{ cliente.cliente_id }}"
                           class="btn btn-primary d-flex flex-column align-items-center justify-content-center py-3 px-4 gap-1" style="min-width:130px; min-height:80px;">
                            <i class="fas fa-list fa-lg"></i>
                            <span class="small fw-bold">Ver NFes</span>
                        </a>
                        <a href="{{ url_for('admin.list_destinatarios', cliente_id=cliente.cliente_id) }}"
                           class="btn btn-warning d-flex flex-column align-items-center justify-content-center py-3 px-4 gap-1" style="min-width:130px; min-height:80px;">
                            <i class="fas fa-address-book fa-lg"></i>
                            <span class="small fw-bold">Destinatários</span>
                        </a>
                        {% if can_create() %}
                        <a href="{{ url_for('nfse.emitir_form') }}?cliente_id={{ cliente.cliente_id }}"
                           class="btn btn-primary d-flex flex-column align-items-center justify-content-center py-3 px-4 gap-1" style="min-width:130px; min-height:80px;">
                            <i class="fas fa-file-invoice fa-lg"></i>
                            <span class="small fw-bold">Emitir NFS-e</span>
                        </a>
                        {% endif %}
                        <a href="{{ url_for('nfse.list_nfse') }}?cliente_id={{ cliente.cliente_id }}"
                           class="btn btn-outline-primary d-flex flex-column align-items-center justify-content-center py-3 px-4 gap-1" style="min-width:130px; min-height:80px;">
                            <i class="fas fa-list-alt fa-lg"></i>
                            <span class="small fw-bold">Ver NFS-e</span>
                        </a>
                    </div>
                </div>"""

if old in content:
    content = content.replace(old, new, 1)
    open(filepath, 'w').write(content)
    print('[OK] Botoes centralizados com sucesso')
else:
    print('[!] Trecho nao encontrado - verificar manualmente')
