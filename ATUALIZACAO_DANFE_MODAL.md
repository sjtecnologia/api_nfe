# Atualização - Modal DANFE após Emissão

## Problema
Erro 500 ao tentar redirecionar após emitir NFe com DANFE gerado:
```
TypeError: '<' not supported between instances of 'int' and 'str'
```

## Arquivos a Atualizar no Servidor

### 1. routes/nfe_routes.py (Linha ~448-460)

**LOCALIZAR:**
```python
                    print(" Redirecionando para lista de NFes...")
                    try:
                        # Se DANFE foi gerado, adicionar parâmetros para abrir modal
                        if danfe_gerado_com_sucesso:
                            return redirect(url_for('nfe.list_nfes', 
                                                   cliente_id=emitente_cliente_id,
                                                   danfe_gerado='true',
                                                   nfe_id=nfe_id,
                                                   danfe_path=caminho_danfe))
                        else:
                            return redirect(url_for('nfe.list_nfes', cliente_id=emitente_cliente_id))
```

**SUBSTITUIR POR:**
```python
                    print(" Redirecionando para lista de NFes...")
                    try:
                        # Se DANFE foi gerado, adicionar parâmetros para abrir modal
                        if danfe_gerado_com_sucesso:
                            # Converter cliente_id para int e garantir que nfe_id também é int
                            return redirect(url_for('nfe.list_nfes', 
                                                   cliente_id=int(emitente_cliente_id),
                                                   danfe_gerado='true',
                                                   nfe_id=int(nfe_id),
                                                   danfe_path=caminho_danfe.replace('\\', '/')))
                        else:
                            return redirect(url_for('nfe.list_nfes', cliente_id=int(emitente_cliente_id)))
```

### 2. templates/admin/nfes/list.html

**Adicionar o modal ANTES de `{% endblock %}`:**

```html
<!-- Modal de Ações Pós-DANFE -->
<div class="modal fade" id="modalAcoesDanfe" tabindex="-1" role="dialog" aria-labelledby="modalAcoesDanfeLabel" aria-hidden="true" data-backdrop="static" data-keyboard="false">
    <div class="modal-dialog modal-dialog-centered" role="document">
        <div class="modal-content">
            <div class="modal-header bg-success text-white">
                <h5 class="modal-title" id="modalAcoesDanfeLabel">
                    <i class="fas fa-check-circle"></i> DANFE Gerado com Sucesso!
                </h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Fechar"></button>
            </div>
            <div class="modal-body text-center py-4">
                <p class="lead mb-4">O que deseja fazer com o DANFE?</p>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <button type="button" class="btn btn-primary btn-lg w-100 shadow-sm" onclick="imprimirDanfe()" style="height: 120px;">
                            <i class="fas fa-print fa-3x mb-2"></i>
                            <br>
                            <strong>Imprimir</strong>
                        </button>
                    </div>
                    <div class="col-md-6 mb-3">
                        <button type="button" class="btn btn-info btn-lg w-100 shadow-sm" onclick="enviarEmailDanfe()" style="height: 120px;">
                            <i class="fas fa-envelope fa-3x mb-2"></i>
                            <br>
                            <strong>Enviar por Email</strong>
                        </button>
                    </div>
                </div>
                <div class="row mt-2">
                    <div class="col-md-12">
                        <button type="button" class="btn btn-secondary btn-sm w-100" data-bs-dismiss="modal">
                            <i class="fas fa-times"></i> Fechar
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
```

**Substituir o bloco `{% block extra_js %}` completo:**

```html
{% block extra_js %}
{{ super() }}
<script>
// Variáveis globais para o modal DANFE
let nfeIdAtual = null;
let danfeCaminhoAtual = null;

document.addEventListener('DOMContentLoaded', function() {
    // Verificar se há parâmetros de DANFE gerado na URL
    const urlParams = new URLSearchParams(window.location.search);
    const danfeGerado = urlParams.get('danfe_gerado');
    const nfeId = urlParams.get('nfe_id');
    const danfePath = urlParams.get('danfe_path');
    
    if (danfeGerado === 'true' && nfeId && danfePath) {
        console.log('[DEBUG] DANFE gerado detectado, abrindo modal...');
        mostrarModalAcoesDanfe(nfeId, danfePath);
        
        // Limpar URL sem recarregar a página
        const cleanUrl = window.location.pathname + (urlParams.get('cliente_id') ? '?cliente_id=' + urlParams.get('cliente_id') : '');
        window.history.replaceState({}, document.title, cleanUrl);
    }
    
    document.querySelectorAll('.btn-gerar-danfe').forEach(function(button) {
        button.addEventListener('click', function() {
            const nfeId = this.getAttribute('data-nfe-id');
            console.log('[DEBUG] Gerar DANFE para NFe:', nfeId);
            gerarDANFE(nfeId, this);
        });
    });
});

function gerarDANFE(nfeId, buttonEl) {
    const originalHtml = buttonEl.innerHTML;
    buttonEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    buttonEl.disabled = true;

    fetch('/admin/nfe/generate-danfe/' + nfeId, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nfe_id: nfeId })
    })
    .then(response => {
        console.log('[DEBUG] Resposta do backend:', response);
        return response.json();
    })
    .then(data => {
        console.log('[DEBUG] JSON recebido:', data);
        buttonEl.innerHTML = originalHtml;
        buttonEl.disabled = false;

        if (data.success) {
            window.open(data.pdf_url, '_blank');
        } else {
            alert('Erro: ' + (data.message || 'Erro ao gerar DANFE.'));
        }
    })
    .catch(error => {
        buttonEl.innerHTML = originalHtml;
        buttonEl.disabled = false;
        console.error('[DEBUG] Erro ao gerar DANFE:', error);
        alert('Erro ao gerar DANFE. Tente novamente mais tarde.');
    });
}

// Função para mostrar modal de ações pós-DANFE
function mostrarModalAcoesDanfe(nfeId, danfeCaminho) {
    nfeIdAtual = nfeId;
    danfeCaminhoAtual = danfeCaminho;
    const modal = new bootstrap.Modal(document.getElementById('modalAcoesDanfe'));
    modal.show();
}

// Função para imprimir DANFE
function imprimirDanfe() {
    if (!danfeCaminhoAtual) {
        alert('Erro: Caminho do DANFE não encontrado');
        return;
    }
    
    // Abrir DANFE em nova janela para impressão
    const danfeUrl = danfeCaminhoAtual.startsWith('http') 
        ? danfeCaminhoAtual 
        : `${window.location.origin}/${danfeCaminhoAtual}`;
    
    const printWindow = window.open(danfeUrl, '_blank');
    
    if (printWindow) {
        // Aguardar carregamento e imprimir automaticamente
        printWindow.onload = function() {
            setTimeout(function() {
                printWindow.print();
            }, 500);
        };
        
        // Fechar modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalAcoesDanfe'));
        if (modal) modal.hide();
        
        // Mostrar mensagem de sucesso
        alert('DANFE aberto para impressão!');
    } else {
        alert('Não foi possível abrir o DANFE. Verifique se o bloqueador de pop-ups está desabilitado.');
    }
}

// Função para enviar DANFE por email
async function enviarEmailDanfe() {
    if (!nfeIdAtual) {
        alert('Erro: ID da NFe não encontrado');
        return;
    }
    
    // Solicitar email do destinatário
    const emailDestinatario = prompt('Digite o email do destinatário:');
    
    if (!emailDestinatario || !emailDestinatario.includes('@')) {
        alert('Email inválido!');
        return;
    }
    
    try {
        // Fazer requisição para enviar email
        const response = await fetch(`/admin/nfes/${nfeIdAtual}/enviar-danfe`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email_destinatario: emailDestinatario
            })
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            // Fechar modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalAcoesDanfe'));
            if (modal) modal.hide();
            
            // Mostrar mensagem de sucesso
            alert(`DANFE enviado com sucesso para ${emailDestinatario}!`);
        } else {
            alert(`Erro ao enviar email: ${result.message || 'Erro desconhecido'}`);
        }
        
    } catch (error) {
        console.error('Erro ao enviar email:', error);
        alert(`Erro ao enviar email: ${error.message}`);
    }
}
</script>
{% endblock %}
```

## Resultado Esperado

Após atualizar esses 2 arquivos no servidor Windows:
1. ✅ NFe será emitida com sucesso
2. ✅ DANFE será gerado automaticamente
3. ✅ Modal aparecerá perguntando: Imprimir ou Enviar por Email
4. ✅ Usuário pode escolher a ação ou fechar o modal

## Como Testar

1. Marcar checkbox "Gerar DANFE automaticamente"
2. Emitir uma NFe
3. Modal deve aparecer automaticamente com opções
