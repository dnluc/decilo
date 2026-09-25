import { test, expect } from '@playwright/test';
import { sessions, snapshot, envelope, caption } from '../fixtures.js';

const session = sessions[0];
const YT = 'https://www.youtube.com/watch?v=IW0unWVDnrI';

// La captura de pestaña necesita permiso humano. Para probar la interfaz se
// entra por `?session=`, el mismo camino que usa alguien que recarga la
// página en medio de una charla.
async function openSession(page, { sockets = [] } = {}) {
  await page.route(`**/api/v1/sessions/${session.id}`, route => route.fulfill({ json: session }));
  await page.routeWebSocket('**/api/v1/sessions/*/events', ws => {
    sockets.push(ws);
    ws.send(JSON.stringify(snapshot(session, [], 0)));
  });
  await page.goto(`/?session=${session.id}`);
  await expect(page.locator('#connection')).toHaveText('Conectado');
  return sockets;
}

test('la página arranca pidiendo un link, sin restos de pruebas viejas', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  await expect(page.locator('#video-url')).toBeVisible();
  await expect(page.locator('.video-empty')).toBeVisible();
  // El andamiaje anterior (catálogo de archivos, "Iniciar prueba", modo
  // muestra) no debe quedar accesible.
  await expect(page.locator('#start-test')).toHaveCount(0);
  await expect(page.locator('.session-card')).toHaveCount(0);
  await expect(page.locator('#demo-banner')).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('carga el video del link pegado y rechaza uno inválido', async ({ page }) => {
  await page.route('https://www.youtube-nocookie.com/**', route =>
    route.fulfill({ body: '', contentType: 'text/html' }));
  await page.goto('/');

  await page.fill('#video-url', 'no es un link');
  await page.click('.url-bar button');
  await expect(page.locator('#video-error')).toContainText('no parece de YouTube');
  await expect(page.locator('#video-frame')).not.toHaveAttribute('data-loaded', 'true');

  await page.fill('#video-url', YT);
  await page.click('.url-bar button');
  await expect(page.locator('#video-error')).toHaveText('');
  await expect(page.locator('#video-frame iframe'))
    .toHaveAttribute('src', 'https://www.youtube-nocookie.com/embed/IW0unWVDnrI');
});

test('video a la izquierda, transcripción a la derecha, subtítulo abajo', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/');
  const video = await page.locator('#video-frame').boundingBox();
  const chat = await page.locator('.chat').boundingBox();
  const live = await page.locator('#live-caption').boundingBox();

  expect(chat.x).toBeGreaterThan(video.x + video.width - 1); // historial a la derecha
  expect(live.y).toBeGreaterThan(video.y + video.height - 1); // subtítulo debajo
  expect(video.width).toBeGreaterThan(700);
  // Todo lo esencial entra en pantalla sin scrollear.
  expect(live.y + live.height).toBeLessThanOrEqual(900);
});

test('los subtítulos se acumulan en el historial y el último va a la barra', async ({ page }) => {
  const sockets = await openSession(page);
  await page.selectOption('#language', 'en');
  await expect(page.locator('.chat-empty')).toBeVisible();

  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ text: 'First line.', status: 'final' }), 1)));
  await expect(page.locator('#live-caption')).toHaveText('First line.');

  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ segment_id: 'seg-2', segment_seq: 2, start_ms: 3500, end_ms: 6000,
      text: 'Second line.', status: 'final' }), 2)));
  // El historial conserva las dos, aunque la barra todavía muestre la primera.
  await expect(page.locator('.turn')).toHaveCount(2);
  await expect(page.locator('#transcript')).toContainText('First line.');
  await expect(page.locator('#transcript')).toContainText('Second line.');
  await expect(page.locator('#chat-count')).toContainText('2');
});

test('lo último dicho encabeza el historial', async ({ page }) => {
  const sockets = await openSession(page);
  await page.selectOption('#language', 'en');
  for (const [i, text] of ['Primera.', 'Segunda.', 'Tercera.'].entries()) {
    sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
      caption({ segment_id: `seg-${i + 1}`, segment_seq: i + 1, start_ms: i * 3000,
        end_ms: i * 3000 + 2500, text, status: 'final' }), i + 1)));
  }
  await expect(page.locator('.turn')).toHaveCount(3);
  await expect(page.locator('.turn').first()).toContainText('Tercera.');
  await expect(page.locator('.turn').last()).toContainText('Primera.');
  // La más reciente es además la marcada como actual.
  await expect(page.locator('.turn.current')).toContainText('Tercera.');
});

test('el historial no estira la página: se acota a la pantalla y scrollea solo', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const sockets = await openSession(page);
  await page.selectOption('#language', 'en');
  for (let i = 0; i < 40; i++) {
    sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
      caption({ segment_id: `seg-${i + 1}`, segment_seq: i + 1, start_ms: i * 3000,
        end_ms: i * 3000 + 2500, text: `Intervención número ${i + 1} de la charla.`, status: 'final' }), i + 1)));
  }
  await expect(page.locator('.turn')).toHaveCount(40);

  const chat = await page.locator('.chat').boundingBox();
  expect(chat.y + chat.height).toBeLessThanOrEqual(901);
  // El scroll es del historial, no de la página.
  expect(await page.evaluate(() => document.documentElement.scrollHeight <= innerHeight + 1)).toBe(true);
  expect(await page.evaluate(() => {
    const log = document.getElementById('transcript');
    return log.scrollHeight > log.clientHeight;
  })).toBe(true);
});

test('un subtítulo no desaparece antes de poder leerlo', async ({ page }) => {
  const sockets = await openSession(page);
  await page.selectOption('#language', 'en');
  // Dos seguidos, casi sin separación: sin ritmo de lectura el primero se
  // perdería en milisegundos.
  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ text: 'Primero.', status: 'final' }), 1)));
  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ segment_id: 'seg-2', segment_seq: 2, start_ms: 3500, end_ms: 6000,
      text: 'Segundo.', status: 'final' }), 2)));
  await expect(page.locator('#live-caption')).toHaveText('Primero.');
  await page.waitForTimeout(400);
  await expect(page.locator('#live-caption')).toHaveText('Primero.');
  // Y termina cediendo al siguiente por su cuenta.
  await expect(page.locator('#live-caption')).toHaveText('Segundo.', { timeout: 4000 });
});

test('el texto recibido se trata como texto, nunca como HTML', async ({ page }) => {
  const sockets = await openSession(page);
  await page.selectOption('#language', 'en');
  const hostile = '<img src=x onerror="window.injected=true">';
  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ text: hostile, status: 'final' }), 1)));
  await expect(page.locator('#live-caption')).toHaveText(hostile);
  await expect(page.locator('#transcript img')).toHaveCount(0);
  await expect(page.locator('#live-caption img')).toHaveCount(0);
  expect(await page.evaluate(() => window.injected)).toBeUndefined();
});

test('en pantalla angosta la transcripción pasa abajo sin desbordar', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const video = await page.locator('#video-frame').boundingBox();
  const chat = await page.locator('.chat').boundingBox();
  expect(chat.y).toBeGreaterThan(video.y);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
