/**
 * static/js/domain/nfe-calculator.js
 *
 * Lógica de cálculo fiscal da NFe — sem DOM, sem chamadas de rede.
 * Testável de forma isolada.
 *
 * Uso:
 *   const calc = new NFeCalculator();
 *   const total = calc.calculateItemTotal(5, 10.50);  // => 52.50
 *   const nfeTotal = calc.calculateNFeTotal(items);
 */
class NFeCalculator {

    // ── Parsing / Formatação ───────────────────────────────────────────────

    /**
     * Converte string monetária brasileira ("1.234,56") ou float para número.
     * @param {string|number} value
     * @returns {number}
     */
    parseCurrency(value) {
        if (typeof value === 'number') return value;
        if (!value) return 0;
        // Remove separadores de milhar e converte vírgula decimal
        const clean = String(value).replace(/\./g, '').replace(',', '.');
        const num = parseFloat(clean);
        return isNaN(num) ? 0 : num;
    }

    /**
     * Formata número como moeda brasileira: "1.234,56".
     * @param {number} value
     * @param {number} decimals  Casas decimais (padrão 2)
     * @returns {string}
     */
    formatCurrency(value, decimals = 2) {
        if (isNaN(value) || value === null) return '0,' + '0'.repeat(decimals);
        return value.toLocaleString('pt-BR', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        });
    }

    /**
     * Formata para exibição com R$: "R$ 1.234,56".
     */
    formatCurrencyBRL(value, decimals = 2) {
        return 'R$ ' + this.formatCurrency(value, decimals);
    }

    // ── Cálculos de Item ───────────────────────────────────────────────────

    /**
     * Calcula o valor total de um item (quantidade × valor unitário).
     * @param {number|string} quantidade
     * @param {number|string} valorUnitario
     * @returns {number}  Arredondado para 2 casas
     */
    calculateItemTotal(quantidade, valorUnitario) {
        const qty = parseFloat(quantidade) || 0;
        const price = this.parseCurrency(valorUnitario);
        return Math.round(qty * price * 100) / 100;
    }

    /**
     * Calcula desconto monetário a partir de percentual.
     * @param {number} baseValue
     * @param {number} percentual  0-100
     * @returns {number}
     */
    calculateDiscount(baseValue, percentual) {
        return Math.round(baseValue * (percentual / 100) * 100) / 100;
    }

    // ── Cálculos de NFe ────────────────────────────────────────────────────

    /**
     * Soma os totais dos itens passados.
     * @param {Array<{total: number}>} items
     * @returns {number}
     */
    calculateNFeTotal(items) {
        return items.reduce((sum, item) => sum + (parseFloat(item.total) || 0), 0);
    }

    /**
     * Lê todos os campos valor_total_N do formulário e retorna a soma.
     * @returns {number}
     */
    calculateNFeTotalFromDOM() {
        let total = 0;
        document.querySelectorAll('[name^="valor_total_"]').forEach(input => {
            total += parseFloat(input.value) || 0;
        });
        return Math.round(total * 100) / 100;
    }

    // ── Cálculos NFS-e / ISS ──────────────────────────────────────────────

    /**
     * Calcula ISS com base em valor do serviço, deduções e alíquota.
     * @param {number} valorServico
     * @param {number} deducoes
     * @param {number} aliquotaISS  Percentual (ex: 5 para 5%)
     * @param {boolean} issRetido
     * @returns {{ baseCalculo: number, valorISS: number, valorLiquido: number }}
     */
    calculateISS(valorServico, deducoes, aliquotaISS, issRetido) {
        const base = Math.max(0, valorServico - deducoes);
        const aliquota = aliquotaISS / 100;
        const valorISS = issRetido ? Math.round(base * aliquota * 100) / 100 : 0;
        const valorLiquido = valorServico - valorISS;
        return { baseCalculo: base, valorISS, valorLiquido };
    }

    /**
     * Calcula valor de IBS/CBS sobre base tributável.
     * @param {number} baseValue
     * @param {number} aliquotaIbsUf   Percentual
     * @param {number} aliquotaIbsMun  Percentual
     * @param {number} aliquotaCbs     Percentual
     * @returns {{ ibs: number, cbs: number, total: number }}
     */
    calculateIBSCBS(baseValue, aliquotaIbsUf, aliquotaIbsMun, aliquotaCbs) {
        const toRate = (p) => (parseFloat(p) || 0) / 100;
        const ibs = Math.round(baseValue * (toRate(aliquotaIbsUf) + toRate(aliquotaIbsMun)) * 100) / 100;
        const cbs = Math.round(baseValue * toRate(aliquotaCbs) * 100) / 100;
        return { ibs, cbs, total: ibs + cbs };
    }

    // ── Comparação / Validação ─────────────────────────────────────────────

    /**
     * Verifica se dois valores monetários são iguais (tolerância de ±0.01).
     */
    isCurrencyEqual(a, b) {
        return Math.abs(a - b) < 0.015;
    }

    /**
     * Valida que quantidade é positiva.
     */
    isValidQuantidade(value) {
        const v = parseFloat(value);
        return !isNaN(v) && v > 0;
    }

    /**
     * Valida que valor unitário é positivo.
     */
    isValidValorUnitario(value) {
        const v = this.parseCurrency(value);
        return !isNaN(v) && v > 0;
    }
}

window.NFeCalculator = NFeCalculator;
window.nfeCalc = new NFeCalculator();
