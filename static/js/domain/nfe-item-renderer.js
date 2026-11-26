/**
 * static/js/domain/nfe-item-renderer.js
 *
 * Centraliza a geração do HTML de itens da NFe.
 * Separa a lógica de renderização de componentes da função adicionarItem().
 *
 * Depende de: nfe-calculator.js
 *
 * Uso:
 *   const renderer = new NFeItemRenderer({ isSimplesnacional: true, cstOptions: [...], csosnOptions: [...] });
 *   const html = renderer.renderItem(itemId);
 *   document.getElementById('itensContainer').insertAdjacentHTML('beforeend', html);
 */
class NFeItemRenderer {
    /**
     * @param {object} config
     * @param {boolean} config.isSimplesnacional  Se true, exibe CSOSN; senão CST ICMS
     * @param {Array}   config.cstOptions    [{ codigo, descricao }]
     * @param {Array}   config.csosnOptions  [{ codigo, descricao }]
     * @param {boolean} [config.showIbsCbs=false]  Se true, exibe campo classificação IBS/CBS
     */
    constructor(config = {}) {
        this.isSimplesnacional = config.isSimplesnacional ?? false;
        this.cstOptions        = config.cstOptions   ?? [];
        this.csosnOptions      = config.csosnOptions ?? [];
        this.showIbsCbs        = config.showIbsCbs   ?? false;
    }

    // ── HTML Helpers ───────────────────────────────────────────────────────

    _optionsHTML(list, selected = '') {
        return list.map(o =>
            `<option value="${o.codigo}"${o.codigo == selected ? ' selected' : ''}>${o.codigo} - ${o.descricao}</option>`
        ).join('');
    }

    _origemOptions() {
        const opts = [
            [0, '0 - Nacional'],
            [1, '1 - Estrangeira - Importação direta'],
            [2, '2 - Estrangeira - Adquirida no mercado interno'],
            [3, '3 - Nacional, Conteúdo de Importação > 40%'],
            [4, '4 - Nacional, processos produtivos básicos'],
            [5, '5 - Nacional, Conteúdo de Importação ≤ 40%'],
            [6, '6 - Estrangeira - Importação direta, sem similar'],
            [7, '7 - Estrangeira - Mercado interno, sem similar'],
            [8, '8 - Nacional, Conteúdo de Importação > 70%'],
        ];
        return opts.map(([v, l]) => `<option value="${v}"${v === 0 ? ' selected' : ''}>${l}</option>`).join('');
    }

    _taxFieldHTML(id) {
        if (this.isSimplesnacional) {
            return `
            <div class="col-md-3">
                <div class="form-group">
                    <label>CSOSN *</label>
                    <select name="csosn_${id}" class="form-control js-select2-csosn" required
                            onchange="atualizarItemJSON(${id})">
                        <option value="">Selecione o CSOSN...</option>
                        ${this._optionsHTML(this.csosnOptions)}
                    </select>
                </div>
            </div>`;
        }
        return `
            <div class="col-md-3">
                <div class="form-group">
                    <label>CST ICMS *</label>
                    <select name="cst_icms_${id}" class="form-control js-select2-cst" required
                            onchange="atualizarItemJSON(${id})">
                        <option value="">Selecione o CST...</option>
                        ${this._optionsHTML(this.cstOptions)}
                    </select>
                </div>
            </div>`;
    }

    _ibsCbsFieldHTML(id) {
        if (!this.showIbsCbs) return '';
        return `
            <div class="col-md-12 item-ibs-cbs mt-2">
                <div class="form-group">
                    <label>Classificação IBS/CBS</label>
                    <select name="classificacao_ibs_cbs_${id}"
                            class="form-control js-select2-classificacao-ibs"
                            onchange="atualizarItemJSON(${id})">
                        <option value="">Nenhuma (opcional)</option>
                    </select>
                </div>
            </div>`;
    }

    // ── Renderização principal ─────────────────────────────────────────────

    /**
     * Gera o HTML completo de um item da NFe.
     * @param {number} id  Identificador numérico do item (itemCounter)
     * @returns {string}  HTML do card de item
     */
    renderItem(id) {
        return `
<div class="card mb-3" id="item-${id}">
    <div class="card-header d-flex justify-content-between align-items-center">
        <h6 class="mb-0">Item ${id}</h6>
        <button type="button" class="btn btn-danger btn-sm" onclick="removerItem(${id})">
            <i class="fas fa-trash"></i> Remover
        </button>
    </div>
    <div class="card-body">

        <!-- Produto -->
        <div class="row">
            <div class="col-md-6">
                <div class="form-group">
                    <label>Produto *</label>
                    <select name="produto_${id}" class="form-control js-select2-produto" required>
                        <option value="">Selecione um produto...</option>
                    </select>
                </div>
            </div>
            <div class="col-md-6">
                <div class="form-group">
                    <label>Código do Produto</label>
                    <input type="text" name="codigo_produto_${id}" class="form-control" readonly>
                </div>
            </div>
        </div>

        <!-- Quantidade e Valores -->
        <div class="row">
            <div class="col-md-3">
                <div class="form-group">
                    <label>Unidade *</label>
                    <input type="text" name="unidade_${id}" class="form-control"
                           value="UN" maxlength="6" required>
                </div>
            </div>
            <div class="col-md-3">
                <div class="form-group">
                    <label>Quantidade *</label>
                    <input type="number" step="0.0001" name="quantidade_${id}"
                           class="form-control" min="0.0001"
                           oninput="calcularTotal(${id})" onchange="calcularTotal(${id})" required>
                </div>
            </div>
            <div class="col-md-3">
                <div class="form-group">
                    <label>Valor Unitário *</label>
                    <input type="number" step="0.01" name="valor_unitario_${id}"
                           class="form-control" min="0.01"
                           oninput="calcularTotal(${id})" onchange="calcularTotal(${id})" required>
                </div>
            </div>
            <div class="col-md-3">
                <div class="form-group">
                    <label>Valor Total</label>
                    <input type="number" step="0.01" name="valor_total_${id}"
                           class="form-control" readonly>
                </div>
            </div>
        </div>

        <!-- Informações Fiscais -->
        <div class="row">
            <div class="col-md-3">
                <div class="form-group">
                    <label>NCM *</label>
                    <select name="ncm_${id}" class="form-control js-select2-ncm" required
                            onchange="atualizarItemJSON(${id})">
                        <option value="">Selecione o NCM...</option>
                    </select>
                </div>
            </div>
            <div class="col-md-3">
                <div class="form-group">
                    <label>CFOP *</label>
                    <select name="cfop_${id}" class="form-control js-select2-cfop" required
                            onchange="atualizarItemJSON(${id})">
                        <option value="">Selecione o CFOP...</option>
                    </select>
                </div>
            </div>
            <div class="col-md-3">
                <div class="form-group">
                    <label>Origem *</label>
                    <select name="origem_${id}" class="form-control" required
                            onchange="atualizarItemJSON(${id})">
                        ${this._origemOptions()}
                    </select>
                </div>
            </div>
            ${this._taxFieldHTML(id)}
        </div>

        <!-- IBS/CBS (Reforma Tributária) -->
        <div class="row">
            ${this._ibsCbsFieldHTML(id)}
        </div>

        <!-- CEST (oculto, preenchido automaticamente) -->
        <input type="hidden" name="cest_${id}" value="">
        <input type="hidden" name="item_json_${id}" value="">

    </div>
</div>`;
    }

    /**
     * Renderiza e insere o item no container, depois inicializa Select2.
     * @param {number} id
     * @param {string} [containerId='itensContainer']
     */
    insertItem(id, containerId = 'itensContainer') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error('NFeItemRenderer: container não encontrado:', containerId);
            return;
        }
        container.insertAdjacentHTML('beforeend', this.renderItem(id));
        this._initSelect2(id);
    }

    _initSelect2(id) {
        if (!window.jQuery || !jQuery.fn.select2) return;

        // Produto
        jQuery(`select[name="produto_${id}"]`).select2({
            ajax: {
                url: `/admin/nfe/api/produtos`,
                dataType: 'json',
                delay: 300,
                data: (params) => ({
                    q: params.term,
                    page: params.page || 1,
                    cliente_id: jQuery('#cliente_id').val() || window._nfeClienteId,
                }),
                processResults: (data) => ({ results: data.results, pagination: data.pagination }),
            },
            placeholder: 'Selecione um produto...',
            allowClear: true,
            width: '100%',
        }).on('select2:select', (e) => {
            if (typeof preencherCamposProduto === 'function') {
                preencherCamposProduto(id, e.params.data);
            }
        });

        // NCM
        jQuery(`select[name="ncm_${id}"]`).select2({
            ajax: {
                url: '/admin/api/search-ncms',
                dataType: 'json',
                delay: 300,
                data: (params) => ({ q: params.term, page: params.page || 1 }),
                processResults: (data) => ({
                    results: (data.ncms || []).map(n => ({ id: n.codigo, text: `${n.codigo} - ${n.descricao}` })),
                    pagination: { more: data.has_more },
                }),
            },
            placeholder: 'Selecione o NCM...',
            allowClear: true,
            width: '100%',
        });

        // CFOP
        jQuery(`select[name="cfop_${id}"]`).select2({
            ajax: {
                url: '/admin/api/search-cfops',
                dataType: 'json',
                delay: 300,
                data: (params) => ({ q: params.term, page: params.page || 1 }),
                processResults: (data) => ({
                    results: (data.cfops || []).map(c => ({ id: c.cfop, text: `${c.cfop} - ${c.descricao}` })),
                    pagination: { more: data.has_more },
                }),
            },
            placeholder: 'Selecione o CFOP...',
            allowClear: true,
            width: '100%',
        });
    }
}

window.NFeItemRenderer = NFeItemRenderer;
