/**
 * static/js/services/api-service.js
 *
 * Camada de acesso à API do backend — sem lógica de negócio, sem DOM.
 * Todos os templates que precisem chamar o backend devem usar este módulo
 * em vez de escrever fetch() inline.
 *
 * Depende de: error_utils.js (apiFetch / showToast)
 *
 * Uso:
 *   const api = new APIService();
 *   const data = await api.fetchNextNumber(clienteId, modelo, serie);
 */
class APIService {

    // ── Assistente IA ──────────────────────────────────────────────────────

    /**
     * Envia pergunta ao assistente de IA contextual.
     * @param {string} pergunta
     * @param {object} contexto  { empresa: {crt, uf, regime}, nfe: {...} }
     * @returns {Promise<{success: boolean, resposta: string}>}
     */
    async fetchChat(pergunta, contexto) {
        return apiFetch('/api/assistente-ia', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pergunta, contexto }),
        }, { errorMsg: 'Erro ao contactar assistente IA', showErrorToast: false });
    }

    /**
     * Valida NFe com IA e retorna resultado de validação.
     * @param {object} nfeData  Dados da NFe para validação
     * @returns {Promise<object>}
     */
    async validateNFeIA(nfeData) {
        return apiFetch('/api/llm/validar-nfe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(nfeData),
        }, { errorMsg: 'Erro ao validar NFe com IA' });
    }

    // ── NFe ────────────────────────────────────────────────────────────────

    /**
     * Busca o próximo número disponível para a NFe.
     * @param {number} clienteId
     * @param {string|number} modelo  55 ou 65
     * @param {string|number} serie
     * @returns {Promise<{success: boolean, proximo_numero: number, serie: string}>}
     */
    async fetchNextNumber(clienteId, modelo, serie) {
        const params = new URLSearchParams({ cliente_id: clienteId, modelo, serie });
        return apiFetch(`/admin/nfe/api/proximo-numero?${params}`, {}, {
            errorMsg: 'Erro ao buscar próximo número da NFe',
        });
    }

    /**
     * Classifica produto automaticamente via IA.
     * @param {object} payload  { descricao, uf_origem, regime_tributario, tipo_item }
     * @param {HTMLElement} [btnEl]  Botão a desabilitar durante a chamada
     * @returns {Promise<object>}
     */
    async classifyProductIA(payload, btnEl = null) {
        const formData = new FormData();
        Object.entries(payload).forEach(([k, v]) => formData.append(k, v));
        return apiFetch('/admin/api/classificar-produto-ia', {
            method: 'POST',
            body: formData,
        }, { btnEl, loadingText: 'Classificando...', errorMsg: 'Erro ao classificar produto' });
    }

    // ── Tributação ─────────────────────────────────────────────────────────

    /**
     * Retorna o regime tributário do emitente (CRT, requer_ibs_cbs, etc.).
     * @param {number} clienteId
     * @returns {Promise<object>}
     */
    async fetchRegimeTributario(clienteId) {
        return apiFetch(`/admin/api/regime-tributario/${clienteId}`, {}, {
            errorMsg: 'Erro ao buscar regime tributário',
        });
    }

    /**
     * Retorna todas as classificações IBS/CBS cadastradas.
     * @returns {Promise<{success: boolean, data: Array}>}
     */
    async fetchClassificacoesIBS() {
        return apiFetch('/admin/api/classificacoes-ibs-cbs', {}, {
            errorMsg: 'Erro ao carregar classificações IBS/CBS',
        });
    }

    /**
     * Busca regra tributária de serviço.
     * @param {number} clienteId
     * @param {string} codigoServico
     * @param {string} ufDestino
     * @returns {Promise<object>}
     */
    async fetchRegraTributaria(clienteId, codigoServico, ufDestino) {
        const params = new URLSearchParams({
            cliente_id: clienteId,
            codigo_servico: codigoServico,
            uf_destino: ufDestino,
        });
        return apiFetch(`/admin/regras-servicos/api/buscar-regra?${params}`, {}, {
            errorMsg: 'Erro ao buscar regra tributária',
            showErrorToast: false,
        });
    }

    // ── Produtos ───────────────────────────────────────────────────────────

    /**
     * Busca produtos paginados para Select2.
     * @param {number} clienteId
     * @param {string} term       Termo de busca
     * @param {number} page
     * @returns {Promise<{results: Array, pagination: {more: boolean}}>}
     */
    async searchProdutos(clienteId, term = '', page = 1) {
        const params = new URLSearchParams({ cliente_id: clienteId, q: term, page });
        return apiFetch(`/admin/nfe/api/produtos?${params}`, {}, {
            errorMsg: 'Erro ao buscar produtos',
        });
    }
}

// Exporta instância global para uso direto em templates
window.apiService = new APIService();
