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
