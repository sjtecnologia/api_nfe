/**
 * error_utils.js — Utilitários globais de tratamento de erros e feedback ao usuário.
 * Incluído via base.html para disponibilidade em todos os templates.
 */

// ─────────────────────────────────────────────
//  showToast — notificação não-bloqueante
// ─────────────────────────────────────────────
/**
 * Exibe um toast Bootstrap 5 na parte inferior direita da tela.
 *
 * @param {string} message  Texto da mensagem
 * @param {string} type     Tipo Bootstrap: 'success' | 'danger' | 'warning' | 'info'
 * @param {number} duration Duração em ms (padrão 5000)
 */
function showToast(message, type = 'info', duration = 5000) {
    const icons = { success: '✅', danger: '❌', warning: '⚠️', info: 'ℹ️' };

    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '10500';
        document.body.appendChild(container);
    }

    const id = 'toast-' + Date.now();
    container.insertAdjacentHTML('beforeend', `
        <div id="${id}" class="toast align-items-center text-bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">${icons[type] || ''} ${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Fechar"></button>
            </div>
        </div>
    `);

    const el = document.getElementById(id);
    const toast = new bootstrap.Toast(el, { delay: duration });
    toast.show();
    el.addEventListener('hidden.bs.toast', () => el.remove());
}

// ─────────────────────────────────────────────
//  showFormError / clearFormError — erro inline em formulário
// ─────────────────────────────────────────────
/**
 * Exibe ou atualiza uma mensagem de erro inline no topo de um formulário.
 *
 * @param {HTMLElement|string} formElOrSelector Elemento form ou seletor CSS
 * @param {string} message  Mensagem de erro
 */
function showFormError(formElOrSelector, message) {
    const form = typeof formElOrSelector === 'string'
        ? document.querySelector(formElOrSelector)
        : formElOrSelector;
    if (!form) return;

    let alertEl = form.querySelector('.js-form-error');
    if (!alertEl) {
        alertEl = document.createElement('div');
        alertEl.className = 'alert alert-danger js-form-error mt-2 mb-0';
        alertEl.setAttribute('role', 'alert');
        form.prepend(alertEl);
    }
    alertEl.innerHTML = '❌ ' + message;
    alertEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Remove a mensagem de erro inline de um formulário.
 *
 * @param {HTMLElement|string} formElOrSelector
 */
function clearFormError(formElOrSelector) {
    const form = typeof formElOrSelector === 'string'
        ? document.querySelector(formElOrSelector)
        : formElOrSelector;
    if (!form) return;
    form.querySelector('.js-form-error')?.remove();
}

// ─────────────────────────────────────────────
//  apiFetch — wrapper seguro para fetch com loading state
// ─────────────────────────────────────────────
/**
 * Wrapper para fetch com tratamento centralizado de erros e loading state.
 *
 * @param {string} url
 * @param {RequestInit} options          Opções padrão do fetch
 * @param {object}  uiOptions
 * @param {HTMLElement} [uiOptions.btnEl]        Botão a desabilitar durante a request
 * @param {string}      [uiOptions.loadingText]  Texto do botão durante loading
 * @param {string}      [uiOptions.errorMsg]     Mensagem de erro padrão
 * @param {boolean}     [uiOptions.showErrorToast=true]  Mostrar toast automático em erro
 * @returns {Promise<any>}  JSON da resposta
 * @throws  Error em caso de falha (após exibir toast)
 */
async function apiFetch(url, options = {}, uiOptions = {}) {
    const {
        btnEl,
        loadingText,
        errorMsg = 'Erro de comunicação. Tente novamente.',
        showErrorToast = true
    } = uiOptions;

    const originalHtml = btnEl ? btnEl.innerHTML : null;

    if (btnEl) {
        btnEl.disabled = true;
        if (loadingText) {
            btnEl.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>${loadingText}`;
        }
    }

    try {
        const response = await fetch(url, options);

        if (!response.ok) {
            let serverMsg = errorMsg;
            try {
                const errBody = await response.json();
                serverMsg = errBody.message || errBody.error || errBody.erro || errorMsg;
            } catch (_) {}
            throw new Error(serverMsg);
        }

        return await response.json();

    } catch (error) {
        if (showErrorToast) {
            const msg = error.name === 'TypeError'
                ? 'Sem conexão com o servidor. Verifique sua rede.'
                : (error.message || errorMsg);
            showToast(msg, 'danger');
        }
        throw error;  // re-throw para o chamador reagir se necessário

    } finally {
        if (btnEl && originalHtml !== null) {
            btnEl.disabled = false;
            btnEl.innerHTML = originalHtml;
        }
    }
}

// ─────────────────────────────────────────────
//  setButtonLoading / resetButton — helpers de estado de botão
// ─────────────────────────────────────────────
/**
 * Desabilita botão e mostra spinner com texto.
 * Retorna o HTML original para posterior restauração.
 */
function setButtonLoading(btn, text = 'Aguarde...') {
    if (!btn) return '';
    const original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>${text}`;
    return original;
}

/**
 * Restaura botão ao estado original.
 */
function resetButton(btn, originalHtml) {
    if (!btn) return;
    btn.disabled = false;
    if (originalHtml !== undefined) btn.innerHTML = originalHtml;
}
