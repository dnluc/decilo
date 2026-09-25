import { test, expect } from '@playwright/test';
import { demoSessions, snapshot, envelope, caption } from '../../src/demo.js';

// WAV real y reproducible (silencio PCM 16 kHz mono), para que el navegador
// cargue metadata y se pueda mover `currentTime`. Un stub vacío no sirve: sin
// duración el elemento no admite buscar una posición.
function silentWav(seconds) {
  const rate = 16000;
  const samples = rate * seconds;
  const buffer = Buffer.alloc(44 + samples * 2);
  buffer.write('RIFF', 0);
  buffer.writeUInt32LE(36 + samples * 2, 4);
  buffer.write('WAVE', 8);
  buffer.write('fmt ', 12);
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20); // PCM
  buffer.writeUInt16LE(1, 22); // mono
  buffer.writeUInt32LE(rate, 24);
  buffer.writeUInt32LE(rate * 2, 28);
  buffer.writeUInt16LE(2, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write('data', 36);
  buffer.writeUInt32LE(samples * 2, 40);
  return buffer;
}

// El backend real sirve el audio con soporte de Range (FileResponse responde
// 206). Sin eso el navegador deja `seekable` vacío y no permite mover la
// reproducción — un mock que ignore Range no representaría al servidor.
function serveAudio(seconds) {
  const body = silentWav(seconds);
  return route => {
    const range = route.request().headers().range;
    if (!range) {
      return route.fulfill({
        status: 200,
        contentType: 'audio/wav',
        headers: { 'Accept-Ranges': 'bytes', 'Content-Length': String(body.length) },
        body,
      });
    }
    const [, from, to] = /bytes=(\d+)-(\d*)/.exec(range);
    const start = Number(from);
    const end = to ? Number(to) : body.length - 1;
    const chunk = body.subarray(start, end + 1);
    return route.fulfill({
      status: 206,
      contentType: 'audio/wav',
      headers: {
        'Accept-Ranges': 'bytes',
        'Content-Range': `bytes ${start}-${end}/${body.length}`,
        'Content-Length': String(chunk.length),
      },
      body: chunk,
    });
  };
}

const session = demoSessions[0];

async function openSessionWithAudio(page, { captions }) {
  await page.route('**/api/v1/sessions', route => route.fulfill({ json: { sessions: [session] } }));
  await page.route('**/api/v1/sessions/*/audio', serveAudio(30));
  await page.routeWebSocket('**/api/v1/sessions/*/events', ws => {
    ws.send(JSON.stringify(snapshot(session, [], 0)));
    captions.forEach((data, index) =>
      ws.send(JSON.stringify(envelope(session, 'caption.upsert', data, index + 1))));
  });
  await page.goto('/');
  await page.getByRole('button', { name: /Building reliable/ }).click();
}

test('reproduce el audio de la sesión y resalta el subtítulo que suena', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await openSessionWithAudio(page, {
    captions: [
      caption({ segment_id: 'seg-1', segment_seq: 1, status: 'final', text: 'Primer tramo', start_ms: 0, end_ms: 5000 }),
      caption({ segment_id: 'seg-2', segment_seq: 2, status: 'final', text: 'Segundo tramo', start_ms: 5000, end_ms: 10000 }),
      caption({ segment_id: 'seg-3', segment_seq: 3, status: 'final', text: 'Tercer tramo', start_ms: 10000, end_ms: 15000 }),
    ],
  });
  await page.getByLabel('Idioma de los subtítulos').selectOption('en');

  const player = page.locator('#audio-player');
  await expect(player).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.getElementById('audio').readyState)).toBeGreaterThan(0);

  // Sin reproducir nada, ningún subtítulo debe figurar como "sonando".
  await expect(page.locator('.caption.now-playing')).toHaveCount(0);

  await page.evaluate(() => { document.getElementById('audio').currentTime = 7; });
  await expect(page.locator('.caption.now-playing')).toContainText('Segundo tramo');
  await expect(page.locator('.caption.now-playing')).toHaveCount(1);

  await page.evaluate(() => { document.getElementById('audio').currentTime = 12; });
  await expect(page.locator('.caption.now-playing')).toContainText('Tercer tramo');

  // Más allá del último subtítulo no se resalta nada por inercia.
  await page.evaluate(() => { document.getElementById('audio').currentTime = 25; });
  await expect(page.locator('.caption.now-playing')).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('el resaltado sobrevive a la llegada de nuevos subtítulos', async ({ page }) => {
  await page.route('**/api/v1/sessions', route => route.fulfill({ json: { sessions: [session] } }));
  await page.route('**/api/v1/sessions/*/audio', serveAudio(30));
  const sockets = [];
  await page.routeWebSocket('**/api/v1/sessions/*/events', ws => {
    sockets.push(ws);
    ws.send(JSON.stringify(snapshot(session, [], 0)));
    ws.send(JSON.stringify(envelope(session, 'caption.upsert',
      caption({ segment_id: 'seg-1', segment_seq: 1, status: 'final', text: 'Primer tramo', start_ms: 0, end_ms: 5000 }), 1)));
  });
  await page.goto('/');
  await page.getByRole('button', { name: /Building reliable/ }).click();
  await page.getByLabel('Idioma de los subtítulos').selectOption('en');
  await expect.poll(() => page.evaluate(() => document.getElementById('audio').readyState)).toBeGreaterThan(0);

  await page.evaluate(() => { document.getElementById('audio').currentTime = 2; });
  await expect(page.locator('.caption.now-playing')).toContainText('Primer tramo');

  // Un render completo reemplaza los nodos: el resaltado debe reaplicarse.
  sockets[0].send(JSON.stringify(envelope(session, 'caption.upsert',
    caption({ segment_id: 'seg-2', segment_seq: 2, status: 'final', text: 'Segundo tramo', start_ms: 5000, end_ms: 10000 }), 2)));
  await expect(page.locator('#transcript')).toContainText('Segundo tramo');
  await expect(page.locator('.caption.now-playing')).toContainText('Primer tramo');
});

test('la muestra no ofrece un reproductor de audio que no existe', async ({ page }) => {
  await page.goto('/?demo=1');
  await page.getByRole('button', { name: /Building reliable/ }).click();
  await expect(page.locator('#transcript')).toContainText('Antes de hacer el merge');
  await expect(page.locator('#audio-player')).toBeHidden();
});
