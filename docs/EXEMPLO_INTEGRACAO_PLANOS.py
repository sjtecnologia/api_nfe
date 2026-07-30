"""
EXEMPLO: Integração do Sistema de Planos na Emissão de NFe

Este arquivo mostra como integrar a verificação de limites e registro de consumo
na rota de emissão de NFe.

Copie e adapte este código para o seu routes/nfe_routes.py
"""

from flask import flash, redirect, url_for
from sqlalchemy import text

def exemplo_verificar_antes_emitir(db, cliente_id):
    """
    Verificar se cliente pode emitir NFe antes de processar
    Adicione este código NO INÍCIO da rota de emissão
    """
    
    # Verificar se cliente tem assinatura e pode emitir
    resultado = db.execute(
        text("SELECT * FROM pode_emitir_nfe(:cliente_id)"),
        {"cliente_id": cliente_id}
    ).fetchone()
    
    pode_emitir = resultado[0]
    mensagem = resultado[1]
    nfes_disponiveis = resultado[2]
    plano_nome = resultado[3]
    
    if not pode_emitir:
        # Cliente não pode emitir - mostrar mensagem e bloquear
        flash(f'❌ Não é possível emitir NFe: {mensagem}', 'danger')
        flash(f'Entre em contato para renovar ou fazer upgrade do plano.', 'info')
        return redirect(url_for('nfe.emitir_nfe', cliente_id=cliente_id))
    
    # Cliente pode emitir - mostrar aviso se estiver próximo do limite
    if nfes_disponiveis < 999999 and nfes_disponiveis <= 10:
        flash(f'⚠️ Atenção: Restam apenas {nfes_disponiveis} NFes no seu plano!', 'warning')
    
    # Continuar com o processamento normal da emissão
    return None  # Indica que pode continuar


def exemplo_registrar_apos_emitir(db, cliente_id):
    """
    Registrar emissão após sucesso
    Adicione este código APÓS a NFe ser emitida com sucesso
    """
    
    try:
        # Incrementar contador de NFes consumidas
        db.execute(
            text("SELECT registrar_emissao_nfe(:cliente_id)"),
            {"cliente_id": cliente_id}
        )
        db.commit()
        
        print(f"✅ Emissão registrada para cliente {cliente_id}")
        
    except Exception as e:
        print(f"⚠️ Erro ao registrar emissão: {e}")
        # Não bloquear a emissão por erro no registro
        # mas avisar no log


# ==============================================================================
# EXEMPLO COMPLETO DE INTEGRAÇÃO NA ROTA
# ==============================================================================

"""
@nfe_bp.route('/emitir', methods=['POST'])
@login_required
def emitir_nfe():
    db = next(get_db())
    cliente_id = request.form.get('cliente_id')
    
    # ========== ADICIONAR AQUI ==========
    # 1. VERIFICAR SE PODE EMITIR
    resultado_verificacao = exemplo_verificar_antes_emitir(db, cliente_id)
    if resultado_verificacao:  # Se retornou um redirect
        return resultado_verificacao
    # ====================================
    
    try:
        # ... seu código normal de emissão de NFe ...
        
        # Gerar XML
        xml_nfe = generate_nfe_xml(...)
        
        # Assinar
        xml_assinado = assinar_xml(...)
        
        # Enviar para SEFAZ
        resultado_sefaz = enviar_sefaz(...)
        
        # Salvar no banco
        salvar_nfe(...)
        
        if resultado_sefaz['success']:
            # ========== ADICIONAR AQUI ==========
            # 2. REGISTRAR EMISSÃO (após sucesso)
            exemplo_registrar_apos_emitir(db, cliente_id)
            # ====================================
            
            flash('NFe emitida com sucesso!', 'success')
            return redirect(url_for('nfe.visualizar', nfe_id=nfe_id))
        else:
            flash('Erro ao emitir NFe', 'danger')
            return redirect(url_for('nfe.emitir_nfe'))
            
    except Exception as e:
        db.rollback()
        flash(f'Erro: {str(e)}', 'danger')
        return redirect(url_for('nfe.emitir_nfe'))
"""


# ==============================================================================
# EXEMPLO: Mostrar informações do plano na tela
# ==============================================================================

def exemplo_get_info_plano_cliente(db, cliente_id):
    """
    Buscar informações do plano do cliente para exibir na tela
    Use isso para mostrar saldo disponível, nome do plano, etc.
    """
    
    from database.models import AssinaturaCliente, PlanoNFe
    
    # Buscar assinatura ativa
    assinatura = db.query(AssinaturaCliente).filter(
        AssinaturaCliente.cliente_id == cliente_id,
        AssinaturaCliente.status == 'ATIVA'
    ).join(PlanoNFe).first()
    
    if not assinatura:
        return {
            'tem_plano': False,
            'mensagem': 'Cliente sem plano ativo'
        }
    
    # Calcular disponíveis
    if assinatura.plano.tipo_plano == 'AVULSO':
        disponiveis = 'Ilimitado (cobrança por NFe)'
        percentual = 0
    elif assinatura.plano.quantidade_nfes is None:
        disponiveis = 'Ilimitado'
        percentual = 0
    else:
        disponiveis = assinatura.plano.quantidade_nfes - assinatura.nfes_consumidas
        percentual = (assinatura.nfes_consumidas / assinatura.plano.quantidade_nfes) * 100
    
    return {
        'tem_plano': True,
        'plano_nome': assinatura.plano.nome,
        'plano_tipo': assinatura.plano.tipo_plano,
        'nfes_consumidas': assinatura.nfes_consumidas,
        'nfes_limite': assinatura.plano.quantidade_nfes,
        'nfes_disponiveis': disponiveis,
        'percentual_uso': round(percentual, 1),
        'periodo_inicio': assinatura.periodo_ref_inicio,
        'periodo_fim': assinatura.periodo_ref_fim,
        'status_cor': 'danger' if percentual >= 90 else ('warning' if percentual >= 70 else 'success')
    }


# ==============================================================================
# EXEMPLO: Widget para exibir no template
# ==============================================================================

"""
No seu template de emissão (emitir.html), adicione:

{% set plano_info = get_info_plano_cliente(cliente_id) %}

{% if plano_info.tem_plano %}
<div class="alert alert-{{ plano_info.status_cor }} mb-3">
    <div class="d-flex justify-content-between align-items-center">
        <div>
            <h6 class="mb-1">
                <i class="fas fa-box"></i> Plano: {{ plano_info.plano_nome }}
            </h6>
            <p class="mb-0">
                <strong>Consumo:</strong> 
                {{ plano_info.nfes_consumidas }}
                {% if plano_info.nfes_limite %}
                    / {{ plano_info.nfes_limite }}
                {% endif %}
                NFes
            </p>
        </div>
        <div class="text-end">
            {% if plano_info.nfes_disponiveis != 'Ilimitado' %}
            <h4 class="mb-0">{{ plano_info.nfes_disponiveis }}</h4>
            <small>disponíveis</small>
            {% else %}
            <h4 class="mb-0"><i class="fas fa-infinity"></i></h4>
            <small>{{ plano_info.nfes_disponiveis }}</small>
            {% endif %}
        </div>
    </div>
    
    {% if plano_info.nfes_limite %}
    <div class="progress mt-2" style="height: 10px;">
        <div class="progress-bar bg-{{ plano_info.status_cor }}" 
             style="width: {{ plano_info.percentual_uso }}%"></div>
    </div>
    {% endif %}
</div>
{% endif %}
"""


# ==============================================================================
# EXEMPLO: Alerta antes de emitir (JavaScript)
# ==============================================================================

"""
Adicione no seu template de emissão:

<script>
// Verificar limite antes de enviar formulário
document.getElementById('form-emitir-nfe').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const clienteId = document.getElementById('cliente_id').value;
    
    // Verificar via API
    fetch(`/admin/planos/api/verificar-limite/${clienteId}`)
        .then(response => response.json())
        .then(data => {
            if (!data.pode_emitir) {
                alert(`❌ ${data.mensagem}\\n\\nEntre em contato para renovar ou fazer upgrade.`);
                return;
            }
            
            // Avisar se estiver próximo do limite
            if (data.nfes_disponiveis < 10 && data.nfes_disponiveis > 0) {
                if (!confirm(`⚠️ Restam apenas ${data.nfes_disponiveis} NFes!\\n\\nDeseja continuar?`)) {
                    return;
                }
            }
            
            // Tudo OK - submeter formulário
            this.submit();
        })
        .catch(error => {
            console.error('Erro ao verificar limite:', error);
            // Em caso de erro, permitir emissão (fail-safe)
            this.submit();
        });
});
</script>
"""
