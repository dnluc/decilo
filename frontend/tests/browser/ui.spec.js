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

// Casos del contrato v1 que el ASR incremental va a ejercitar mucho más
// seguido (backend-latencia-incremental, tarea 4.2): la UI debe reemplazar
// la entrada por (segment_id, kind, language) + revision, nunca anexar cada
// revisión como una frase nueva.

test('una revisión reemplaza el texto en lugar de agregar otra línea', async ({ page }) => {
  const sockets = await openSession(page);
  await page.selectOption('#language', 'en');

  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ text: 'We need', status: 'provisional' }), 1)));
  await expect(page.locator('.turn')).toHaveCount(1);

  for (const [i, text] of ['We need another', 'We need another code review.'].entries()) {
    sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
      caption({ revision: i + 2, text, status: 'provisional' }), i + 2)));
  }
  // Tres revisiones del mismo segmento siguen siendo una sola intervención.
  await expect(page.locator('#transcript')).toContainText('We need another code review.');
  await expect(page.locator('.turn')).toHaveCount(1);
  await expect(page.locator('#live-caption')).toHaveText('We need another code review.');
});

test('una traducción obsoleta no reemplaza a la vigente', async ({ page }) => {
  const sockets = await openSession(page);
  const send = (data, seq) => sockets[0].send(JSON.stringify(
    envelope(session, 'caption.upsert', data, seq)));

  send(caption({ text: 'We need', status: 'provisional' }), 1);
  send(caption({ kind: 'translation', language: 'es', source_revision: 1,
    text: 'Necesitamos', status: 'provisional' }), 2);
  await expect(page.locator('#transcript')).toContainText('Necesitamos');

  // Avanza el original: su traducción anterior deja de ser vigente.
  send(caption({ revision: 2, text: 'We need a code review.', status: 'final' }), 3);
  await expect(page.locator('#transcript')).not.toContainText('Necesitamos');

  // Una traducción tardía de la revisión vieja no debe volver a aparecer.
  send(caption({ kind: 'translation', language: 'es', source_revision: 1, revision: 2,
    text: 'Traducción vieja', status: 'provisional' }), 4);
  send(caption({ kind: 'translation', language: 'es', source_revision: 2, revision: 2,
    text: 'Necesitamos una revisión de código.', status: 'final' }), 5);
  await expect(page.locator('#transcript')).toContainText('Necesitamos una revisión de código.');
  await expect(page.locator('#transcript')).not.toContainText('Traducción vieja');
});

test('un final no se reescribe y una revisión repetida no duplica', async ({ page }) => {
  const sockets = await openSession(page);
  await page.selectOption('#language', 'en');
  const final = caption({ text: 'Confirmado.', status: 'final' });
  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert', final, 1)));
  await expect(page.locator('.turn.final')).toContainText('Confirmado.');
  // Repetir la misma revisión es idempotente.
  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert', final, 2)));
  await expect(page.locator('.turn')).toHaveCount(1);
  await expect(page.locator('#transcript')).toContainText('Confirmado.');
});

test('al reconectar, el snapshot reemplaza el estado sin duplicar', async ({ page }) => {
  const sockets = [];
  await page.route(`**/api/v1/sessions/${session.id}`, route => route.fulfill({ json: session }));
  await page.routeWebSocket('**/api/v1/sessions/*/events', ws => {
    sockets.push(ws);
    // La segunda conexión trae el historial ya acumulado.
    const previas = sockets.length === 1 ? [] : [caption({ text: 'Ya dicho.', status: 'final' })];
    ws.send(JSON.stringify(snapshot(session, previas, sockets.length === 1 ? 0 : 4)));
  });
  await page.goto(`/?session=${session.id}`);
  await expect(page.locator('#connection')).toHaveText('Conectado');
  await page.selectOption('#language', 'en');

  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ text: 'Ya dicho.', status: 'final' }), 1)));
  await expect(page.locator('.turn')).toHaveCount(1);

  // Un salto de secuencia fuerza reconexión; el snapshot manda.
  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ segment_id: 'seg-9', segment_seq: 9, text: 'Perdido', status: 'final' }), 99)));
  await expect.poll(() => sockets.length).toBe(2);
  await expect(page.locator('#connection')).toHaveText('Conectado');
  await expect(page.locator('.turn')).toHaveCount(1);
  await expect(page.locator('#transcript')).toContainText('Ya dicho.');
});

// Selector de procesamiento local / nube.

test('la elección de procesamiento viaja en la sesión de captura', async ({ page }) => {
  await page.route('**/api/v1/providers', route =>
    route.fulfill({ json: { default: 'local', cloud_available: true } }));
  const urls = [];
  page.on('websocket', ws => urls.push(ws.url()));
  // La captura necesita permiso humano: se simula el stream para llegar a
  // abrir el WebSocket, que es lo que se quiere verificar.
  await page.addInitScript(() => {
    navigator.mediaDevices.getDisplayMedia = async () => {
      const ctx = new AudioContext();
      const destination = ctx.createMediaStreamDestination();
      const oscillator = ctx.createOscillator();
      oscillator.connect(destination);
      oscillator.start();
      return destination.stream;
    };
  });
  await page.goto('/');
  await page.selectOption('#provider', 'gemini');
  await page.getByRole('button', { name: 'Compartir audio de pestaña', exact: true }).click();
  await expect.poll(() => urls.filter(u => u.includes('/capture?')).length).toBeGreaterThan(0);
  expect(urls.find(u => u.includes('/capture?'))).toContain('provider=gemini');
});

test('sin credenciales en el servidor, la nube no se ofrece como disponible', async ({ page }) => {
  await page.route('**/api/v1/providers', route =>
    route.fulfill({ json: { default: 'local', cloud_available: false } }));
  await page.goto('/');
  // `toBeDisabled` no cubre <option>; se verifica la propiedad real.
  await expect(page.locator('#provider option[value="gemini"]')).toHaveJSProperty('disabled', true);
  await expect(page.locator('#provider')).toHaveValue('local');
  await expect(page.locator('#provider-note')).toContainText('GEMINI_API_KEY');
});

test('la elección se recuerda entre visitas', async ({ page }) => {
  await page.route('**/api/v1/providers', route =>
    route.fulfill({ json: { default: 'local', cloud_available: true } }));
  await page.goto('/');
  await page.selectOption('#provider', 'gemini');
  await page.reload();
  await expect(page.locator('#provider')).toHaveValue('gemini');
});

test('sin preferencia propia se adopta el default del servidor', async ({ page }) => {
  await page.route('**/api/v1/providers', route =>
    route.fulfill({ json: { default: 'gemini', cloud_available: true } }));
  await page.goto('/');
  await expect(page.locator('#provider')).toHaveValue('gemini');
  await expect(page.locator('#provider-note')).toContainText('se envía a Google');
});

test('la preferencia guardada le gana al default del servidor', async ({ page }) => {
  await page.route('**/api/v1/providers', route =>
    route.fulfill({ json: { default: 'gemini', cloud_available: true } }));
  await page.goto('/');
  await page.selectOption('#provider', 'local');
  await page.reload();
  await expect(page.locator('#provider')).toHaveValue('local');
});

test('cada opción explica qué implica, incluido dónde va el audio', async ({ page }) => {
  await page.route('**/api/v1/providers', route =>
    route.fulfill({ json: { default: 'local', cloud_available: true } }));
  await page.goto('/');
  await expect(page.locator('#provider-note')).toContainText('no sale de acá');
  await page.selectOption('#provider', 'gemini');
  await expect(page.locator('#provider-note')).toContainText('se envía a Google');
});

// Transcripción palabra por palabra: estados por color, nunca por carteles.

test('la barra distingue provisional de confirmado solo por color', async ({ page }) => {
  const sockets = await openSession(page);
  await page.selectOption('#language', 'en');

  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ text: 'We are', status: 'provisional' }), 1)));
  await expect(page.locator('#live-caption')).toHaveText('We are');
  await expect(page.locator('#live-caption')).toHaveAttribute('data-state', 'provisional');

  // La revisión crece en el lugar, sin reiniciar el tiempo de lectura.
  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ revision: 2, text: 'We are shipping', status: 'provisional' }), 2)));
  await expect(page.locator('#live-caption')).toHaveText('We are shipping');
  await expect(page.locator('#live-caption')).toHaveAttribute('data-state', 'provisional');

  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ revision: 3, text: 'We are shipping today.', status: 'final' }), 3)));
  await expect(page.locator('#live-caption')).toHaveText('We are shipping today.');
  await expect(page.locator('#live-caption')).toHaveAttribute('data-state', 'final');

  // En ningún momento un cartel de proceso.
  expect(await page.locator('body').textContent()).not.toContain('Traduciendo');
});

test('sin traducción lista, el original ocupa su lugar como provisional', async ({ page }) => {
  const sockets = await openSession(page);
  // Vista en español; llega solo el original en inglés.
  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ text: 'Original english line.', status: 'final' }), 1)));
  await expect(page.locator('#live-caption')).toHaveText('Original english line.');
  await expect(page.locator('#live-caption')).toHaveAttribute('data-state', 'provisional');
  await expect(page.locator('.turn.provisional')).toContainText('Original english line.');

  // Llega el español: reemplaza y se confirma.
  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ kind: 'translation', language: 'es', source_revision: 1,
      text: 'Línea original en español.', status: 'final' }), 2)));
  await expect(page.locator('#live-caption')).toHaveText('Línea original en español.');
  await expect(page.locator('#live-caption')).toHaveAttribute('data-state', 'final');
});

test('el dock vive en el borde inferior y el video ocupa el resto', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.route('**/api/v1/providers', route =>
    route.fulfill({ json: { default: 'local', cloud_available: true } }));
  await page.goto('/');
  const dock = await page.locator('.dock').boundingBox();
  const video = await page.locator('#video-frame').boundingBox();
  // El dock (subtítulo + controles) termina en el borde de la ventana.
  expect(Math.round(dock.y + dock.height)).toBeGreaterThanOrEqual(898);
  // Y el video aprovecha el alto que queda por encima.
  expect(video.height).toBeGreaterThan(400);
  expect(video.y + video.height).toBeLessThanOrEqual(dock.y + 1);
});

test('detectar idioma automáticamente es la opción por defecto', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#capture-language')).toHaveValue('auto');
});
