import { test, expect } from '@playwright/test';
import { demoSessions, snapshot, envelope, caption } from '../../src/demo.js';

const session = demoSessions[0];

async function openSession(page) {
  await page.route('**/api/v1/sessions', route => route.fulfill({ json: { sessions: [session] } }));
  const sockets = [];
  await page.routeWebSocket('**/api/v1/sessions/*/events', ws => {
    sockets.push(ws);
    ws.send(JSON.stringify(snapshot(session, [], 0)));
  });
  await page.goto('/');
  await page.getByRole('button', { name: /Building reliable/ }).click();
  await expect(page.locator('#connection')).toHaveText('Conectado');
  return sockets;
}

test('el video es el protagonista, no un recuadro en una columna', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.route('**/api/v1/sessions', route => route.fulfill({ json: { sessions: [] } }));
  await page.goto('/');

  const video = await page.locator('.video-frame').boundingBox();
  const main = await page.locator('main').boundingBox();
  // Antes el video vivía dentro del <aside> de 285px y quedaba diminuto.
  expect(video.width).toBeGreaterThan(700);
  expect(video.width).toBeGreaterThan(main.width * 0.5);

  // Video y subtítulos son una sola pieza: el texto va pegado abajo.
  const captionBox = await page.locator('#live-caption').boundingBox();
  expect(Math.abs(captionBox.y - (video.y + video.height))).toBeLessThan(2);
  expect(Math.abs(captionBox.width - video.width)).toBeLessThan(2);
});

test('video y subtítulos entran juntos en pantalla, sin scrollear', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.route('**/api/v1/sessions', route => route.fulfill({ json: { sessions: [] } }));
  await page.goto('/');
  const caption = await page.locator('#live-caption').boundingBox();
  // De nada sirve un video grande si hay que scrollear para leer lo que se dice.
  expect(caption.y + caption.height).toBeLessThanOrEqual(900);
});

test('la barra bajo el video muestra lo último dicho, en el idioma elegido', async ({ page }) => {
  const sockets = await openSession(page);
  await expect(page.locator('#live-caption')).toHaveAttribute('data-empty', 'true');

  // Por defecto se lee en español: hasta que llegue la traducción la barra
  // queda vacía. Nunca muestra mensajes de estado, solo subtítulos listos.
  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ text: 'We need another code review.', status: 'final' }), 1)));
  await expect(page.locator('#transcript')).toContainText('Esperando traducción');
  await expect(page.locator('#live-caption')).toHaveText('');

  await page.getByLabel('Idioma de los subtítulos').selectOption('en');
  await expect(page.locator('#live-caption')).toHaveText('We need another code review.');
  await expect(page.locator('#live-caption')).toHaveAttribute('data-empty', 'false');

  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ kind: 'translation', language: 'es', source_revision: 1, revision: 1,
      text: 'Necesitamos otra revisión de código.', status: 'final' }), 2)));
  await page.getByLabel('Idioma de los subtítulos').selectOption('es');
  await expect(page.locator('#live-caption')).toHaveText('Necesitamos otra revisión de código.');

  // Al avanzar la charla, la barra sigue al último segmento.
  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ segment_id: 'seg-2', segment_seq: 2, start_ms: 3500, end_ms: 6000,
      text: 'Small changes make systems easier to understand.', status: 'final' }), 3)));
  await page.getByLabel('Idioma de los subtítulos').selectOption('en');
  await expect(page.locator('#live-caption')).toHaveText('Small changes make systems easier to understand.');

  // Y el historial de abajo conserva todo lo dicho, no solo lo último.
  await expect(page.locator('.caption')).toHaveCount(2);
  await expect(page.locator('#transcript')).toContainText('We need another code review.');
  await expect(page.locator('#transcript')).toContainText('Small changes make systems easier to understand.');
});

test('la barra no muestra mensajes de estado, solo subtítulos listos', async ({ page }) => {
  const sockets = await openSession(page);
  // Recién conectado, sin nada dicho todavía: la barra está vacía.
  await expect(page.locator('#live-caption')).toHaveText('');

  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ text: 'Partial text', status: 'provisional' }), 1)));
  await page.getByLabel('Idioma de los subtítulos').selectOption('en');
  await expect(page.locator('#live-caption')).toHaveText('Partial text');
});

test('el historial queda debajo del video, no en otra columna', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.route('**/api/v1/sessions', route => route.fulfill({ json: { sessions: [] } }));
  await page.goto('/');
  const stage = await page.locator('.stage').boundingBox();
  const history = await page.locator('.reading-panel').boundingBox();
  expect(history.y).toBeGreaterThan(stage.y + stage.height);
  // A todo el ancho, no arrinconado junto a un catálogo lateral.
  expect(history.width).toBeGreaterThan(stage.width * 0.9);
});

test('el texto del subtítulo se interpreta como texto, no como HTML', async ({ page }) => {
  const sockets = await openSession(page);
  await page.getByLabel('Idioma de los subtítulos').selectOption('en');
  const hostile = '<img src=x onerror="window.injected=true">';
  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ text: hostile, status: 'final' }), 1)));
  await expect(page.locator('#live-caption')).toHaveText(hostile);
  await expect(page.locator('#live-caption img')).toHaveCount(0);
  expect(await page.evaluate(() => window.injected)).toBeUndefined();
});

test('en móvil el escenario no desborda y el video sigue siendo el protagonista', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route('**/api/v1/sessions', route => route.fulfill({ json: { sessions: [] } }));
  await page.goto('/');
  const video = await page.locator('.video-frame').boundingBox();
  expect(video.width).toBeGreaterThan(300);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('cargar el video oculta la portada y no deja el botón a medias', async ({ page }) => {
  await page.route('**/api/v1/sessions', route => route.fulfill({ json: { sessions: [] } }));
  // No cargar YouTube de verdad en los tests: solo comprobar el cableado.
  await page.route('https://www.youtube-nocookie.com/**', route => route.fulfill({ body: '', contentType: 'text/html' }));
  await page.goto('/');
  // El click puede caer en un hijo del botón (el ícono): igual debe ocultarse
  // el botón entero, no solo el ícono.
  await page.locator('#youtube-load .play').click();
  await expect(page.locator('#youtube-load')).toBeHidden();
  await expect(page.locator('#youtube-test iframe'))
    .toHaveAttribute('src', 'https://www.youtube-nocookie.com/embed/IW0unWVDnrI');
});
