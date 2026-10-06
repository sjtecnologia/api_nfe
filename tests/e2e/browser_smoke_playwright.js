#!/usr/bin/env node

const { chromium } = require('playwright');

const baseUrl = (process.env.E2E_BASE_URL || '').replace(/\/$/, '');
const username = process.env.E2E_USERNAME || '';
const password = process.env.E2E_PASSWORD || '';
const chromePath = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const artifactsDir = 'artifacts/e2e';
const quotaUiEnabled = process.env.E2E_QUOTA_UI === '1';
const commercialUxEnabled = process.env.E2E_COMMERCIAL_UX === '1';

if (!baseUrl || !username || !password) {
  console.error('BROWSER_SMOKE_PENDING_ENVIRONMENT');
  console.error('Configure E2E_BASE_URL, E2E_USERNAME and E2E_PASSWORD.');
  process.exit(78);
}

if (!/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(baseUrl) && process.env.E2E_ALLOW_NONLOCAL !== '1') {
  console.error('Browser smoke blocked: non-local URL requires E2E_ALLOW_NONLOCAL=1.');
  process.exit(1);
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: chromePath,
  });
  const page = await browser.newPage();
  const jsErrors = [];
  const requestFailures = [];
  const httpErrors = [];

  page.on('pageerror', (error) => {
    jsErrors.push(`pageerror: ${error.message}`);
  });
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('Failed to load resource')) {
      jsErrors.push(`console.error: ${message.text()}`);
    }
  });
  page.on('requestfailed', (request) => {
    requestFailures.push(`${request.method()} ${request.url()} - ${request.failure()?.errorText || 'failed'}`);
  });
  page.on('response', (response) => {
    if (response.status() >= 500 || (response.status() === 404 && !response.url().includes('/api/regras_tributacao/buscar'))) {
      httpErrors.push(`${response.status()} ${response.url()}`);
    }
  });

  try {
    await page.goto(`${baseUrl}/auth/login`, { waitUntil: 'domcontentloaded' });
    await page.locator('#username').fill(username);
    await page.locator('#passwordField').fill(password);
    await page.locator('#loginForm button[type="submit"]').click();
    await page.waitForLoadState('domcontentloaded');

    if (page.url().includes('/auth/login')) {
      throw new Error('Login não redirecionou; credencial ou ambiente inválido.');
    }

    if (commercialUxEnabled) {
      await runCommercialCatalogScenario(page);
      if (jsErrors.length) throw new Error(`Erros JavaScript: ${jsErrors.join(' | ')}`);
      if (requestFailures.length) throw new Error(`Requests falhos: ${requestFailures.join(' | ')}`);
      if (httpErrors.length) throw new Error(`Respostas HTTP críticas: ${httpErrors.join(' | ')}`);
      console.log('COMMERCIAL_UX_HOMOLOGATED');
      return;
    }

    const selectionLink = page.locator('a[href*="/select-client/"]').first();
    if (await selectionLink.count()) {
      await selectionLink.click();
      await page.waitForLoadState('domcontentloaded');
    }

    const dashboardResponse = await page.goto(`${baseUrl}/`, { waitUntil: 'domcontentloaded' });
    if (!dashboardResponse || dashboardResponse.status() < 200 || dashboardResponse.status() >= 400) {
      throw new Error(`Dashboard retornou HTTP ${dashboardResponse ? dashboardResponse.status() : 'sem resposta'}.`);
    }
    if (page.url().includes('/auth/login')) throw new Error('Dashboard redirecionou para login.');
    if (!page.url().includes('/cliente/dashboard') && !page.url().includes('/admin/dashboard')) {
      throw new Error(`Fluxo pós-login não abriu um dashboard: ${page.url()}`);
    }

    const listResponse = await page.goto(`${baseUrl}/admin/nfe/list`, { waitUntil: 'domcontentloaded' });
    if (!listResponse || listResponse.status() < 200 || listResponse.status() >= 400) {
      throw new Error(`Listagem NF-e retornou HTTP ${listResponse ? listResponse.status() : 'sem resposta'}.`);
    }
    if (page.url().includes('/auth/login')) throw new Error('Listagem NF-e redirecionou para login.');

    const emissionResponse = await page.goto(`${baseUrl}/admin/nfe/emitir`, { waitUntil: 'domcontentloaded' });
    if (!emissionResponse || emissionResponse.status() < 200 || emissionResponse.status() >= 400) {
      throw new Error(`Emissão retornou HTTP ${emissionResponse ? emissionResponse.status() : 'sem resposta'}.`);
    }
    if (page.url().includes('/auth/login')) throw new Error('Emissão redirecionou para login.');
    await page.locator('#nfeForm').waitFor();
    await page.locator('#btnEmitir').waitFor();
    const html = await page.content();
    if (!html.includes('/api/csrf-token') || !html.includes('directNativeEmit')) {
      throw new Error('Proteções críticas do formulário não foram carregadas.');
    }

    const numberResponse = await page.request.get(`${baseUrl}/admin/nfe/api/proximo-numero`);
    if (numberResponse.status() < 200 || numberResponse.status() >= 400) {
      throw new Error(`Próximo número retornou HTTP ${numberResponse.status()}.`);
    }

    // Mutations are opt-in and never call SEFAZ. A controlled fixture is required.
    if (process.env.E2E_ALLOW_MUTATIONS === '1') {
      console.log('Browser smoke: mutation phase explicitly enabled; use only isolated homologation data.');
    }

    await page.goto(`${baseUrl}/admin/nfce/list`, { waitUntil: 'domcontentloaded' });
    await page.goto(`${baseUrl}/admin/analise-vendas`, { waitUntil: 'domcontentloaded' });
    if (quotaUiEnabled) {
      await runQuotaUiScenario(page);
    }
    if (jsErrors.length) throw new Error(`Erros JavaScript: ${jsErrors.join(' | ')}`);
    if (requestFailures.length) throw new Error(`Requests falhos: ${requestFailures.join(' | ')}`);
    if (httpErrors.length) throw new Error(`Respostas HTTP críticas: ${httpErrors.join(' | ')}`);
    console.log('Browser smoke: PASS');
  } catch (error) {
    const fs = require('fs');
    fs.mkdirSync(artifactsDir, { recursive: true });
    await page.screenshot({ path: `${artifactsDir}/browser-smoke-failure.png`, fullPage: true });
    throw error;
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(`Browser smoke: FAIL - ${error.message}`);
  console.error(`Screenshot: ${artifactsDir}/browser-smoke-failure.png`);
  process.exit(1);
});

async function runQuotaUiScenario(page) {
  const fs = require('fs');
  const quotaScreenshot = `${artifactsDir}/nfe-quota-start-50-50.png`;
  fs.mkdirSync(artifactsDir, { recursive: true });
  const quotaErrors = [];
  const knownNonCriticalErrors = [];
  const quotaFailures = [];
  const responses = [];
  const onPageError = (error) => quotaErrors.push(`pageerror: ${error.message}`);
  const onConsole = (message) => {
    if (message.type() === 'error') {
      if (message.text().includes('Failed to load resource')) knownNonCriticalErrors.push(message.text());
      else quotaErrors.push(`console.error: ${message.text()}`);
    }
  };
  const onRequestFailed = (request) => quotaFailures.push(`${request.method()} ${request.url()} - ${request.failure()?.errorText || 'failed'}`);
  const onResponse = (response) => responses.push(response);
  page.on('pageerror', onPageError);
  page.on('console', onConsole);
  page.on('requestfailed', onRequestFailed);
  page.on('response', onResponse);

  try {
    const emissionResponse = await page.goto(`${baseUrl}/admin/nfe/emitir?cliente_id=${process.env.E2E_TENANT_ID || '1'}`, { waitUntil: 'domcontentloaded' });
    if (!emissionResponse || emissionResponse.status() >= 400) {
      throw new Error(`Quota UI: tela de emissão retornou HTTP ${emissionResponse?.status() || 'sem resposta'}.`);
    }
    await page.locator('#nfeForm').waitFor();
    await page.locator('#btnEmitir').waitFor();

    await page.locator('#modelo').selectOption('55');
    await page.locator('#serie').fill(process.env.E2E_NFE_SERIE || '1');
    await page.locator('#numero_nfe').fill(process.env.E2E_NFE_NUMBER || '900001');
    await page.locator('#tpNF').selectOption('1');
    await page.locator('#finNFe').selectOption('1');
    await page.locator('#indPres').selectOption('1');
    await page.locator('#natOp').fill('Venda');
    await page.locator('#destinatario').selectOption({ index: 1 });
    await page.locator('#formaPagamento').selectOption(process.env.E2E_PAYMENT_CODE || '01');
    await page.locator('input[name="valorPagamento"]').fill('10');
    await page.locator('#modFrete').selectOption('9');

    const item = page.locator('#itensContainer .card').first();
    await select2Search(page, item.locator('select[name^="produto_"]'), process.env.E2E_PRODUCT_SEARCH || 'Produto E2E');
    await item.locator('input[name^="unidade_"]').fill('UN');
    await item.locator('input[name^="quantidade_"]').fill('1');
    await item.locator('input[name^="valor_unitario_"]').fill('10');
    await select2Search(page, item.locator('select[name^="ncm_"]'), process.env.E2E_NCM_SEARCH || '84713000');
    await item.locator('select[name^="cfop_"]').selectOption(process.env.E2E_CFOP || '5102');
    await item.locator('select[name^="origem_"]').selectOption('0');
    const csosn = item.locator('select[name^="csosn_"]');
    if (await csosn.count()) await csosn.selectOption(process.env.E2E_CSOSN || '102');

    const beforeState = await page.locator('#nfeForm').evaluate((form) => Object.fromEntries(
      [...form.elements].filter((element) => element.name && !element.disabled).map((element) => [element.name, element.value])
    ));
    await page.waitForFunction(() => {
      const overlay = document.querySelector('#rascunhoLoadingOverlay');
      return !overlay || getComputedStyle(overlay).display === 'none' || getComputedStyle(overlay).visibility === 'hidden';
    });
    await page.locator('#natOp').fill('Venda');
    await page.locator('#btnEmitir').waitFor({ state: 'visible' });
    await page.waitForFunction(() => !document.querySelector('#btnEmitir')?.disabled);
    page.once('dialog', (dialog) => dialog.accept());
    await page.locator('#btnEmitir').click();
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(300);

    const bodyText = (await page.locator('body').innerText()).toLowerCase();
    const hasCommercialMessage = bodyText.includes('atingiu o limite de 50 nf-e')
      || (bodyText.includes('limite de 50') && bodyText.includes('plano start'));
    if (!hasCommercialMessage) throw new Error('Quota UI: mensagem comercial de limite 50/50 não apareceu.');
    if (bodyText.includes('rejeição sefaz') || bodyText.includes('erro 500') || bodyText.includes('traceback')) {
      throw new Error('Quota UI: a tela exibiu erro fiscal/técnico ao bloquear a emissão.');
    }

    await page.screenshot({ path: quotaScreenshot, fullPage: true });
    const afterState = await page.locator('#nfeForm').evaluate((form) => Object.fromEntries(
      [...form.elements].filter((element) => element.name && !element.disabled).map((element) => [element.name, element.value])
    )).catch(() => ({}));
    const preservedFields = Object.keys(beforeState).filter((name) => beforeState[name] && beforeState[name] === afterState[name]);
    console.log(`FORM_STATE=${preservedFields.length ? 'PRESERVED' : 'KNOWN_UX_LIMITATION'}`);

    const serverErrors = responses.filter((response) => response.status() >= 500);
    const optionalRuleLookup404s = responses.filter((response) => response.status() === 404 && response.url().includes('/api/regras_tributacao/buscar'));
    if (knownNonCriticalErrors.length > optionalRuleLookup404s.length) {
      quotaErrors.push(`console.error: ${knownNonCriticalErrors.length - optionalRuleLookup404s.length} recurso(s) não reconhecido(s)`);
    }
    if (quotaErrors.length || quotaFailures.length || serverErrors.length) {
      throw new Error(`Quota UI console/network: ${[...quotaErrors, ...quotaFailures, ...serverErrors.map((response) => `${response.status()} ${response.url()}`)].join(' | ')}`);
    }
    if (knownNonCriticalErrors.length) console.log(`UI_NONCRITICAL_RESOURCE_WARNINGS=${knownNonCriticalErrors.length}`);
    await assertQuotaDatabaseState();
    console.log(`UI_QUOTA_50_50=PASS screenshot=${quotaScreenshot}`);
  } finally {
    page.off('pageerror', onPageError);
    page.off('console', onConsole);
    page.off('requestfailed', onRequestFailed);
    page.off('response', onResponse);
  }
}

async function runCommercialCatalogScenario(page) {
  const fs = require('fs');
  const screenshotDir = `${artifactsDir}/commercial`;
  fs.mkdirSync(screenshotDir, { recursive: true });
  const startCases = [
    [201, 0, 'NORMAL'], [202, 39, 'NORMAL'], [203, 40, 'APPROACHING_LIMIT'],
    [204, 49, 'APPROACHING_LIMIT'], [205, 50, 'LIMIT_REACHED'],
  ];
  for (const [clientId, usage, state] of startCases) {
    await page.goto(`${baseUrl}/select-client/${clientId}`, { waitUntil: 'domcontentloaded' });
    const response = await page.goto(`${baseUrl}/admin/meu-plano`, { waitUntil: 'domcontentloaded' });
    if (!response || response.status() >= 400) throw new Error(`Meu plano Start ${usage}/50 retornou HTTP ${response?.status()}`);
    const text = (await page.locator('body').innerText()).toLowerCase();
    if (!text.includes('start') || !text.includes(`${usage} / 50`) || !text.includes(state === 'LIMIT_REACHED' ? 'limite atingido' : state === 'APPROACHING_LIMIT' ? 'atenção ao consumo' : 'uso normal')) {
      throw new Error(`Estado visual Start inválido para ${usage}/50; esperado ${state}.`);
    }
    await page.screenshot({ path: `${screenshotDir}/start-${usage}-50.png`, fullPage: true });
  }

  for (const [clientId, users] of [[211, 2], [213, 3]]) {
    await page.goto(`${baseUrl}/select-client/${clientId}`, { waitUntil: 'domcontentloaded' });
    await page.goto(`${baseUrl}/admin/meu-plano`, { waitUntil: 'domcontentloaded' });
    const currentPlanText = (await page.locator('section[aria-labelledby="plano-atual-heading"]').innerText()).toLowerCase();
    const text = (await page.locator('body').innerText()).toLowerCase();
    if (!currentPlanText.includes('condição comercial preservada') || currentPlanText.includes('start_v1') || currentPlanText.includes('legacy_60_v1') || currentPlanText.includes('50 nf-e/mês') || currentPlanText.includes('manual_business_decision')) {
      throw new Error(`Apresentação legacy inválida para ${clientId}.`);
    }
    if (!currentPlanText.includes(`${users} / ${users}`)) throw new Error(`Capacidade legacy de usuários não exibida para ${clientId}.`);
    await page.screenshot({ path: `${screenshotDir}/legacy-${clientId}.png`, fullPage: true });
  }

  await page.goto(`${baseUrl}/admin/meu-plano#planos-disponiveis`, { waitUntil: 'domcontentloaded' });
  const comparisonText = (await page.locator('body').innerText()).toLowerCase();
  for (const name of ['start', 'essencial', 'profissional', 'premium', 'enterprise']) {
    if (!comparisonText.includes(name)) throw new Error(`Plano ${name} ausente na comparação.`);
  }
  if (comparisonText.includes('legacy_60_v1') || comparisonText.includes('empresas ilimitadas') || comparisonText.includes('usuários ilimitados')) {
    throw new Error('Comparação expôs plano legacy ou capacidade ilimitada indevida.');
  }
  if (!comparisonText.includes('uso justo') || !comparisonText.includes('5 empresa') || !comparisonText.includes('10 usuário')) {
    throw new Error('Informações Premium/fair use incompletas.');
  }
  await page.screenshot({ path: `${screenshotDir}/comparison.png`, fullPage: true });
  await page.locator('#upgrade-info').scrollIntoViewIfNeeded();
  await page.locator('a[href="#upgrade-info"]').first().click();
  if (!page.url().includes('#upgrade-info')) throw new Error('CTA de upgrade não abriu fluxo informativo.');
  await page.reload({ waitUntil: 'domcontentloaded' });
  if (!(await page.locator('body').innerText()).includes('Nenhuma alteração de plano')) throw new Error('Estado informativo de upgrade não persistiu após refresh.');

  await page.goto(`${baseUrl}/select-client/215`, { waitUntil: 'domcontentloaded' });
  await page.goto(`${baseUrl}/admin/meu-plano`, { waitUntil: 'domcontentloaded' });
  if (!(await page.locator('body').innerText()).includes('Não foi possível carregar os dados do seu plano agora.')) throw new Error('Fallback sem assinatura não apareceu.');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${baseUrl}/select-client/203`, { waitUntil: 'domcontentloaded' });
  await page.goto(`${baseUrl}/admin/meu-plano`, { waitUntil: 'domcontentloaded' });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) throw new Error('UX comercial possui overflow horizontal no mobile.');
  await page.screenshot({ path: `${screenshotDir}/mobile.png`, fullPage: true });
}

async function select2Search(page, selectLocator, searchTerm) {
  const selectName = await selectLocator.getAttribute('name');
  if (!selectName) throw new Error('Quota UI: select Select2 sem atributo name.');
  await page.locator(`select[name="${selectName}"] + span.select2`).click();
  const searchInput = page.locator('.select2-container--open input.select2-search__field');
  await searchInput.fill(searchTerm);
  await page.locator('.select2-container--open .select2-results__option--selectable').first().click();
}

async function assertQuotaDatabaseState() {
  const databaseUrl = process.env.DATABASE_URL || '';
  if (!databaseUrl) throw new Error('Quota UI: DATABASE_URL local E2E não configurado para validar counter/eventos.');
  const { execFileSync } = require('child_process');
  const query = "SELECT (SELECT quantity FROM billing_usage_counters WHERE metric_key = 'NFE_ISSUED' ORDER BY updated_at DESC LIMIT 1), (SELECT COUNT(*) FROM billing_usage_events WHERE metric_key = 'NFE_ISSUED' AND status = 'COUNTED'), (SELECT COUNT(*) FROM billing_usage_reservations WHERE metric_key = 'NFE_ISSUED' AND status IN ('PENDING', 'PENDING_RECONCILIATION'))";
  const result = execFileSync('psql', [databaseUrl, '-At', '-c', query], { encoding: 'utf8' }).trim();
  const [counter, countedEvents, activeReservations] = result.split('|').map(Number);
  if (counter !== 50 || countedEvents !== 0 || activeReservations !== 0) {
    throw new Error(`Quota UI: estado DB inválido counter=${counter} counted_events=${countedEvents} active_reservations=${activeReservations}`);
  }
  console.log(`QUOTA_DB_STATE=PASS counter=${counter} counted_events=${countedEvents} active_reservations=${activeReservations}`);
}
