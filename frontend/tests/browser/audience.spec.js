import { test, expect } from '@playwright/test';
import { demoSessions, snapshot, envelope, caption } from '../../src/demo.js';

test('demo distinguishes provisional text, selects language and isolates sessions on mobile', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/?demo=1');
  await expect(page.locator('#demo-banner')).toBeVisible();
  await page.getByRole('button', { name: /Building reliable/ }).click();
  await expect(page.locator('.caption.provisional')).toBeVisible();
  await expect(page.locator('#transcript')).toContainText('Antes de hacer el merge del PR, necesitamos otro code review.', { timeout: 10000 });
  await page.getByLabel('Idioma de los subtítulos').selectOption('en');
  await expect(page.locator('#transcript')).toContainText('Before merging the PR, we need another code review.');
  await page.getByRole('button', { name: /Código abierto/ }).click();
  await expect(page.locator('#transcript')).toContainText('El código abierto se construye en comunidad.');
  await expect(page.locator('#transcript')).not.toContainText('merging');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

test('HTTP and websocket UI renders untrusted text safely and recovers from sequence loss', async ({ page }) => {
  await page.route('**/api/v1/sessions', route => route.fulfill({ json: { sessions: demoSessions } }));
  const sockets = [];
  await page.routeWebSocket('**/api/v1/sessions/*/events', ws => {
    sockets.push(ws);
    ws.send(JSON.stringify(snapshot(demoSessions[0], [], sockets.length === 1 ? 0 : 5)));
  });
  await page.goto('/');
  await page.getByRole('button', { name: /Building reliable/ }).click();
  await expect(page.locator('#connection')).toHaveText('Conectado');
  await page.getByLabel('Idioma de los subtítulos').selectOption('en');
  const text = '<img src=x onerror="window.injected=true">';
  sockets[0].send(JSON.stringify(envelope(demoSessions[0], 'caption.upsert', caption({ text, status: 'final' }), 1)));
  await expect(page.locator('#transcript')).toContainText(text);
  await expect(page.locator('#transcript img')).toHaveCount(0);
  expect(await page.evaluate(() => window.injected)).toBeUndefined();
  sockets[0].send(JSON.stringify(envelope(demoSessions[0], 'caption.upsert', caption(), 5)));
  await expect.poll(() => sockets.length).toBe(2);
  await expect(page.locator('#connection')).toHaveText('Conectado');
  await expect(page.locator('#transcript')).not.toContainText(text);
});

test('catalog failure has an explicit retry and never presents simulated sessions', async ({ page }) => {
  await page.route('**/api/v1/sessions', route => route.fulfill({ status: 503 }));
  await page.goto('/');
  await expect(page.locator('#catalog-message')).toContainText('No pudimos cargar');
  await expect(page.locator('.session-card')).toHaveCount(0);
  await expect(page.locator('#demo-banner')).toBeHidden();
  await page.route('**/api/v1/sessions', route => route.fulfill({ json: { sessions: [] } }));
  await page.getByRole('button', { name: 'Actualizar' }).click();
  await expect(page.locator('#catalog-message')).toContainText('Todavía no hay sesiones');
});

test('reading preferences persist text size and focus mode preserves the active stream', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route('**/api/v1/sessions', route => route.fulfill({ json: { sessions: demoSessions } }));
  const sockets = [];
  await page.routeWebSocket('**/api/v1/sessions/*/events', ws => {
    sockets.push(ws);
    ws.send(JSON.stringify(snapshot(demoSessions[0], [caption({ status: 'final' })])));
  });
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Solo subtítulos' })).toBeDisabled();
  await page.getByRole('button', { name: /Building reliable/ }).click();
  await page.getByLabel('Idioma de los subtítulos').selectOption('en');
  const text = page.locator('.caption p').first();
  const normal = await text.evaluate(el => parseFloat(getComputedStyle(el).fontSize));
  await page.getByLabel('Tamaño del texto').selectOption('extra');
  expect(await text.evaluate(el => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThan(normal);
  await page.getByRole('button', { name: 'Solo subtítulos' }).click();
  await expect(page.locator('.sessions-panel')).toBeHidden();
  await expect(page.getByRole('button', { name: 'Volver a las charlas' })).toBeFocused();
  sockets[0].send(JSON.stringify(envelope(demoSessions[0], 'caption.upsert', caption({
    segment_id: 'seg-2', segment_seq: 2, text: 'Still connected.', status: 'final',
  }), 1)));
  await expect(page.locator('#transcript')).toContainText('Still connected.');
  expect(sockets).toHaveLength(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.keyboard.press('Escape');
  await expect(page.locator('.sessions-panel')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Solo subtítulos' })).toBeFocused();
  await page.reload();
  await expect(page.getByLabel('Tamaño del texto')).toHaveValue('extra');
  await expect(page.locator('.sessions-panel')).toBeVisible();
});

test('blocked storage does not prevent reading controls and demo stays identified in focus mode', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'localStorage', { get() { throw new Error('Storage blocked'); } });
  });
  await page.goto('/?demo=1');
  await page.getByRole('button', { name: /Código abierto/ }).click();
  await page.getByLabel('Tamaño del texto').selectOption('large');
  await page.getByRole('button', { name: 'Solo subtítulos' }).click();
  await expect(page.locator('#demo-banner')).toBeVisible();
  await expect(page.locator('#transcript')).toContainText('El código abierto');
  await page.getByRole('button', { name: 'Volver a las charlas' }).click();
  await expect(page.locator('.sessions-panel')).toBeVisible();
});
