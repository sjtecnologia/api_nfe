/**
 * error_utils.js — Utilitários globais de tratamento de erros e feedback ao usuário.
 * Incluído via base.html para disponibilidade em todos os templates.
 */

const __apiCache = new Map();

function __sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function __cacheKey(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    return `${method}:${url}`;
}

function __readCache(key) {
    const cached = __apiCache.get(key);
    if (!cached) return null;
    if (Date.now() > cached.expiresAt) {
        __apiCache.delete(key);
        return null;
    }
    return cached.data;
}

function __writeCache(key, data, ttlMs) {
    if (!ttlMs || ttlMs <= 0) return;
    __apiCache.set(key, {
        data,
        expiresAt: Date.now() + ttlMs,
    });
}

function __recordMetric(metric) {
    if (!window.__apiMetrics) {
        window.__apiMetrics = {
            requests: [],
            summary: { total: 0, ok: 0, failed: 0, avgMs: 0 },
        };
    }
    const metrics = window.__apiMetrics;
    metrics.requests.push(metric);
    if (metrics.requests.length > 200) metrics.requests.shift();

    metrics.summary.total += 1;
    if (metric.ok) metrics.summary.ok += 1;
    else metrics.summary.failed += 1;

    const durations = metrics.requests.map(r => r.durationMs);
    const totalDuration = durations.reduce((sum, val) => sum + val, 0);
    metrics.summary.avgMs = Math.round(totalDuration / durations.length);
}

function __stripPayload(value) {
    if (Array.isArray(value)) {
        return value
            .filter(v => v !== undefined)
            .map(v => __stripPayload(v));
    }

    if (value && typeof value === 'object') {
        const out = {};
        Object.entries(value).forEach(([k, v]) => {
            if (v !== undefined && v !== null && v !== '') {
                out[k] = __stripPayload(v);
            }
        });
        return out;
    }

    return value;
}

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
        showErrorToast = true,
        retries = 0,
        retryBaseDelayMs = 300,
        retryMaxDelayMs = 4000,
        retryJitter = true,
        cacheTtlMs = 0,
        forceRefresh = false,
        trimPayload = false,
        optimisticUpdate,
        rollbackUpdate,
        commitUpdate,
        signal,
        monitor = true,
    } = uiOptions;

    const originalHtml = btnEl ? btnEl.innerHTML : null;
    const method = (options.method || 'GET').toUpperCase();
    const cacheable = method === 'GET';
    const key = __cacheKey(url, options);

    if (cacheable && cacheTtlMs > 0 && !forceRefresh) {
        const cached = __readCache(key);
        if (cached !== null) {
            if (monitor) {
                __recordMetric({
                    url,
                    method,
                    ok: true,
                    status: 200,
                    durationMs: 0,
                    fromCache: true,
                    ts: Date.now(),
                });
            }
            return cached;
        }
    }

    if (trimPayload && options && options.body && typeof options.body === 'string') {
        try {
            const parsed = JSON.parse(options.body);
            options.body = JSON.stringify(__stripPayload(parsed));
        } catch (_) {
            // payload nao-json: ignora trim
        }
    }

    if (btnEl) {
        btnEl.disabled = true;
        if (loadingText) {
            btnEl.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>${loadingText}`;
        }
    }

    const optimisticContext = optimisticUpdate ? optimisticUpdate() : null;

    let lastError = null;
    const maxAttempts = Math.max(1, retries + 1);
    const startAt = performance.now();

    try {
        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                const response = await fetch(url, { ...options, signal });

                if (!response.ok) {
                    let serverMsg = errorMsg;
                    try {
                        const errBody = await response.json();
                        serverMsg = errBody.message || errBody.error || errBody.erro || errorMsg;
                    } catch (_) {}
                    const e = new Error(serverMsg);
                    e.status = response.status;
                    throw e;
                }

                const data = await response.json();
                if (cacheable && cacheTtlMs > 0) __writeCache(key, data, cacheTtlMs);
                if (commitUpdate) commitUpdate(data, optimisticContext);

                if (monitor) {
                    __recordMetric({
                        url,
                        method,
                        ok: true,
                        status: response.status,
                        durationMs: Math.round(performance.now() - startAt),
                        fromCache: false,
                        attempts: attempt,
                        ts: Date.now(),
                    });
                }

                return data;

            } catch (error) {
                lastError = error;

                if (error.name === 'AbortError') throw error;

                const retryableStatus = [408, 425, 429, 500, 502, 503, 504];
                const status = error.status || 0;
                const retryable = status === 0 || retryableStatus.includes(status);
                const shouldRetry = attempt < maxAttempts && retryable;

                if (!shouldRetry) throw error;

                const exp = Math.min(retryMaxDelayMs, retryBaseDelayMs * (2 ** (attempt - 1)));
                const jitter = retryJitter ? Math.floor(Math.random() * 150) : 0;
                await __sleep(exp + jitter);
            }
        }

        throw lastError || new Error(errorMsg);

    } catch (error) {
        if (rollbackUpdate) rollbackUpdate(optimisticContext, error);

        if (monitor) {
            __recordMetric({
                url,
                method,
                ok: false,
                status: error.status || 0,
                durationMs: Math.round(performance.now() - startAt),
                fromCache: false,
                attempts: maxAttempts,
                error: error.message,
                ts: Date.now(),
            });
        }

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

function createRequestController() {
    return new AbortController();
}

async function apiFetchParallel(requests = []) {
    const tasks = requests.map(({ url, options = {}, uiOptions = {} }) =>
        apiFetch(url, options, uiOptions)
    );
    return Promise.all(tasks);
}

function startSmartPolling(fetcher, cfg = {}) {
    const {
        intervalMs = 15000,
        hiddenIntervalMs = 60000,
        shouldPoll = () => true,
        onError = null,
    } = cfg;

    let timer = null;
    let running = false;
    let stopped = false;

    const schedule = () => {
        if (stopped) return;
        const wait = document.hidden ? hiddenIntervalMs : intervalMs;
        timer = setTimeout(tick, wait);
    };

    const tick = async () => {
        if (stopped || running || !navigator.onLine || !shouldPoll()) {
            schedule();
            return;
        }

        running = true;
        try {
            await fetcher();
        } catch (err) {
            if (onError) onError(err);
        } finally {
            running = false;
            schedule();
        }
    };

    const onVis = () => {
        if (!stopped) {
            clearTimeout(timer);
            schedule();
        }
    };

    document.addEventListener('visibilitychange', onVis);
    schedule();

    return {
        stop() {
            stopped = true;
            clearTimeout(timer);
            document.removeEventListener('visibilitychange', onVis);
        }
    };
}

window.apiFetch = apiFetch;
window.apiFetchParallel = apiFetchParallel;
window.createRequestController = createRequestController;
window.startSmartPolling = startSmartPolling;

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
