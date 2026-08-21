#!/usr/bin/env node

const { chromium } = require('playwright');

const baseUrl = (process.env.E2E_BASE_URL || '').replace(/\/$/, '');
const username = process.env.E2E_USERNAME || '';
const password = process.env.E2E_PASSWORD || '';
const chromePath = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const artifactsDir = 'artifacts/e2e';

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

  page.on('pageerror', (error) => {
    jsErrors.push(`pageerror: ${error.message}`);
  });
  page.on('console', (message) => {
    if (message.type() === 'error') {
      jsErrors.push(`console.error: ${message.text()}`);
    }
  });
  page.on('requestfailed', (request) => {
    requestFailures.push(`${request.method()} ${request.url()} - ${request.failure()?.errorText || 'failed'}`);
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

    const selectionLink = page.locator('a[href*="/select-client/"]').first();
    if (await selectionLink.count()) {
      await selectionLink.click();
      await page.waitForLoadState('domcontentloaded');
    }

    const dashboardResponse = await page.goto(`${baseUrl}/admin/dashboard`, { waitUntil: 'domcontentloaded' });
    if (!dashboardResponse || dashboardResponse.status() < 200 || dashboardResponse.status() >= 400) {
      throw new Error(`Dashboard retornou HTTP ${dashboardResponse ? dashboardResponse.status() : 'sem resposta'}.`);
    }
    if (page.url().includes('/auth/login')) throw new Error('Dashboard redirecionou para login.');

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
    if (jsErrors.length) throw new Error(`Erros JavaScript: ${jsErrors.join(' | ')}`);
    if (requestFailures.length) throw new Error(`Requests falhos: ${requestFailures.join(' | ')}`);
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
