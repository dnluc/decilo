import { test, expect } from '@playwright/test';

// Estas pruebas corren contra la app y el gateway reales (WebSocket, estado,
// suscriptores), con la inferencia explícitamente falsa: verifican la
// integración, no la calidad ni la latencia de los modelos.
//
// Las pruebas del catálogo de archivos y del reproductor de muestras se
// retiraron junto con esa funcionalidad, que el usuario pidió sacar de la
// interfaz: la aplicación ahora es solo el flujo de captura de pestaña.

const origin = 'http://127.0.0.1:18764';
const caption = overrides => ({ segment_id: 'seg-1', segment_seq: 1, kind: 'transcript',
  language: 'en', revision: 1, source_revision: null, text: 'We need',
  status: 'provisional', start_ms: 0, end_ms: 100, ...overrides });

test('el gateway real entrega revisiones, descarta tardías y libera conexiones', async ({ page, request }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const publish = async data => {
    const response = await request.post(`${origin}/api/_test/integration-en/publish`, { data });
    expect(response.ok()).toBe(true);
    return response.json();
  };

  await page.goto('/?session=integration-en');
  await expect(page.locator('#connection')).toHaveText('Conectado');
  await page.locator('#language').selectOption('es');

  await publish({ type: 'caption', data: caption() });
  await publish({ type: 'caption', data: caption({ kind: 'translation', language: 'es', source_revision: 1, text: 'Necesitamos' }) });
  await expect(page.locator('.turn.provisional')).toContainText('Necesitamos');

  await publish({ type: 'caption', data: caption({ revision: 2, status: 'final', text: 'We need a code review.' }) });
  // Leyendo en español el inglés nunca se muestra: al revisarse el original
  // la traducción provisional vieja se retira y la fila espera invisible.
  await expect(page.locator('#transcript')).not.toContainText('We need a code review.');

  // Una traducción de la revisión vieja no debe volver a mostrarse.
  const late = await publish({ type: 'caption', data: caption({ kind: 'translation', language: 'es', source_revision: 1, revision: 2, text: 'Traducción vieja' }) });
  expect(late.seq).toBe(3);
  await publish({ type: 'caption', data: caption({ kind: 'translation', language: 'es', source_revision: 2, revision: 2, status: 'final', text: 'Necesitamos un code review.' }) });
  await expect(page.locator('.turn.final')).toContainText('Necesitamos un code review.');
  await expect(page.locator('#transcript')).not.toContainText('Traducción vieja');

  await publish({ type: 'status', status: 'ended' });
  expect((await (await request.get(`${origin}/api/v1/sessions/integration-en`)).json()).status).toBe('ended');

  // Al irse, la suscripción se libera: no quedan conexiones colgadas.
  await page.goto('about:blank');
  await expect.poll(async () => Object.values(await (await request.get(`${origin}/api/_test/subscribers`)).json()).every(n => n === 0)).toBe(true);
  expect(errors).toEqual([]);
});

test('la captura envía PCM real del worklet y libera el audio al detener', async ({ page }) => {
  await page.addInitScript(() => {
    navigator.mediaDevices.getDisplayMedia = async () => {
      const ctx = new AudioContext();
      const oscillator = ctx.createOscillator();
      const destination = ctx.createMediaStreamDestination();
      oscillator.connect(destination);
      oscillator.start();
      await ctx.resume();
      window.testCapture = { ctx, stream: destination.stream };
      return destination.stream;
    };
  });
  await page.goto('/');
  await page.selectOption('#capture-language', 'en');
  await page.getByRole('button', { name: 'Compartir audio de pestaña', exact: true }).click();
  await expect(page.locator('#capture-message')).toContainText('Capturando audio');
  await page.locator('#language').selectOption('en');
  await expect(page.locator('.turn')).toContainText('Captured audio test', { timeout: 15000 });
  // Y lo capturado también llega a la barra bajo el video.
  await expect(page.locator('#live-caption')).toContainText('Captured audio test');
  await page.getByRole('button', { name: 'Detener', exact: true }).click();
  await expect.poll(() => page.evaluate(() => window.testCapture.stream.getTracks().every(t => t.readyState === 'ended'))).toBe(true);
  await expect(page.locator('#capture-start')).toBeEnabled();
  await page.evaluate(() => window.testCapture.ctx.close());
});

test('sin audio compartido se avisa y no se crea ninguna sesión', async ({ page }) => {
  await page.addInitScript(() => { navigator.mediaDevices.getDisplayMedia = async () => new MediaStream(); });
  const starts = [];
  page.on('websocket', ws => { if (ws.url().includes('/capture?')) starts.push(ws.url()); });
  await page.goto('/');
  await page.locator('#capture-start').click();
  await expect(page.locator('#capture-message')).toContainText('No se compartió audio');
  await expect(page.locator('#capture-start')).toBeEnabled();
  expect(starts).toEqual([]);
});
