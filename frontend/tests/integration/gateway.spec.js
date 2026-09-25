import { test, expect } from '@playwright/test';

test('real gateway delivers revisions, shares HTTP status, restores snapshots and cleans connections', async ({ page, request }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const origin = 'http://127.0.0.1:18764';
  const caption = overrides => ({ segment_id: 'seg-1', segment_seq: 1, kind: 'transcript',
    language: 'en', revision: 1, source_revision: null, text: 'We need',
    status: 'provisional', start_ms: 0, end_ms: 100, ...overrides });
  const publish = async data => {
    const response = await request.post(`${origin}/api/_test/integration-en/publish`, { data });
    expect(response.ok()).toBe(true);
    return response.json();
  };
  await page.goto('/');
  await page.getByRole('button', { name: /Integración en/ }).click();
  await expect(page.locator('#connection')).toHaveText('Conectado');
  await publish({ type: 'caption', data: caption() });
  await publish({ type: 'caption', data: caption({ kind: 'translation', language: 'es', source_revision: 1, text: 'Necesitamos' }) });
  await expect(page.locator('.caption.provisional')).toContainText('Necesitamos');
  await publish({ type: 'caption', data: caption({ revision: 2, status: 'final', text: 'We need a code review.' }) });
  await expect(page.locator('.caption.pending')).toContainText('Esperando traducción');
  const late = await publish({ type: 'caption', data: caption({ kind: 'translation', language: 'es', source_revision: 1, revision: 2, text: 'Traducción vieja' }) });
  expect(late.seq).toBe(3);
  await publish({ type: 'caption', data: caption({ kind: 'translation', language: 'es', source_revision: 2, revision: 2, status: 'final', text: 'Necesitamos un code review.' }) });
  await expect(page.locator('.caption.final')).toContainText('Necesitamos un code review.');
  await publish({ type: 'status', status: 'ended' });
  await expect(page.locator('#session-status')).toHaveText('Charla finalizada');
  expect((await (await request.get(`${origin}/api/v1/sessions/integration-en`)).json()).status).toBe('ended');
  await page.getByRole('button', { name: /Integración es/ }).click();
  await expect(page.locator('#connection')).toHaveText('Conectado');
  await expect(page.locator('.caption')).toHaveCount(0);
  await expect.poll(async () => (await (await request.get(`${origin}/api/_test/subscribers`)).json())['integration-en']).toBe(0);
  await page.getByRole('button', { name: /Integración en/ }).click();
  await expect(page.locator('#connection')).toHaveText('Conectado');
  await expect(page.locator('.caption')).toHaveCount(1);
  await expect(page.locator('.caption.final')).toContainText('Necesitamos un code review.');
  await expect(page.locator('#session-status')).toHaveText('Charla finalizada');
  await page.goto('about:blank');
  await expect.poll(async () => Object.values(await (await request.get(`${origin}/api/_test/subscribers`)).json()).every(n => n === 0)).toBe(true);
  expect(errors).toEqual([]);
});
