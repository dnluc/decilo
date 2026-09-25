import { test, expect } from '@playwright/test';

// El worklet corre en el hilo de audio, así que se prueba en el navegador con
// un contexto offline: rinde determinístico y rápido, y deja verificar el
// formato exacto que espera el backend (offset uint32 LE + PCM16 LE).

const RATE = 16000;
const FRAME = 1600; // 100ms

async function capturePackets(page, { seconds, stop = false }) {
  return page.evaluate(async ({ seconds, stop, RATE }) => {
    const ctx = new OfflineAudioContext(1, RATE * seconds, RATE);
    await ctx.audioWorklet.addModule('/capture-worklet.js');
    const node = new AudioWorkletNode(ctx, 'capture-pcm');
    const packets = [];
    let stopped = false;
    node.port.onmessage = ({ data }) => {
      if (data.stopped) { stopped = true; return; }
      if (data.dropped) return;
      packets.push([...new Uint8Array(data.packet)]);
      node.port.postMessage('ack');
    };
    // Señal con valor conocido y distinto de cero para que no se confunda con
    // silencio ni con un buffer sin escribir.
    const buffer = ctx.createBuffer(1, RATE * seconds, RATE);
    buffer.getChannelData(0).fill(0.5);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(node);
    node.connect(ctx.destination);
    source.start();
    await ctx.startRendering();
    if (stop) {
      node.port.postMessage('stop');
      await new Promise(r => setTimeout(r, 200));
    }
    await new Promise(r => setTimeout(r, 100));
    return { packets, stopped };
  }, { seconds, stop, RATE });
}

function readOffset(bytes) {
  return new DataView(new Uint8Array(bytes).buffer).getUint32(0, true);
}

test('cada paquete lleva 100ms de PCM16 con su offset', async ({ page }) => {
  await page.goto('/');
  const { packets } = await capturePackets(page, { seconds: 1 });

  expect(packets.length).toBeGreaterThanOrEqual(9);
  for (const packet of packets) {
    // 4 bytes de offset + 1600 muestras de 2 bytes.
    expect(packet.length).toBe(4 + FRAME * 2);
  }
  // Offsets contiguos: sin huecos ni solapamiento al cambiar el tamaño de
  // paquete, que es justo lo que la spec pide no romper.
  packets.forEach((packet, index) => expect(readOffset(packet)).toBe(index * FRAME));
});

test('las muestras llegan intactas, no en silencio', async ({ page }) => {
  await page.goto('/');
  const { packets } = await capturePackets(page, { seconds: 1 });
  const view = new DataView(new Uint8Array(packets[1]).buffer);
  // 0.5 en float equivale a ~16383 en PCM16.
  expect(view.getInt16(4, true)).toBeGreaterThan(16000);
  expect(view.getInt16(4, true)).toBeLessThan(16500);
});

test('stop vacía el último fragmento parcial en vez de perderlo', async ({ page }) => {
  await page.goto('/');
  // 1.05s no es múltiplo de 100ms, así que queda un fragmento suelto al cortar.
  const { packets, stopped } = await capturePackets(page, { seconds: 1.05, stop: true });
  expect(stopped).toBe(true);

  // El contexto rinde en bloques de 128 muestras, así que entrega algo más que
  // el pedido; lo que importa es que no se pierda ni se duplique nada.
  const total = packets.reduce((sum, p) => sum + (p.length - 4) / 2, 0);
  const rendered = Math.ceil((RATE * 1.05) / 128) * 128;
  expect(total).toBe(rendered);

  const last = packets.at(-1);
  expect((last.length - 4) / 2).toBeLessThan(FRAME); // es el parcial, no un frame entero
  // Los offsets cubren el audio de punta a punta, sin huecos.
  expect(readOffset(last) + (last.length - 4) / 2).toBe(rendered);
  packets.reduce((expected, packet) => {
    expect(readOffset(packet)).toBe(expected);
    return expected + (packet.length - 4) / 2;
  }, 0);
});
