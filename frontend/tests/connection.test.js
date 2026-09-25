import test from 'node:test';
import assert from 'node:assert/strict';
import { CaptionConnection, loadSessions } from '../src/connection.js';
import { demoSessions, snapshot, envelope, caption } from '../src/demo.js';
function harness() {
  const sockets = [], updates = [], timers = new Map();
  let id = 0;
  const client = new CaptionConnection({ origin: 'https://decilo.test', random: () => 1,
    socketFactory(url) { const socket = { url, close() { this.closed = true; } }; sockets.push(socket); return socket; },
    onUpdate: (state, connection) => updates.push({ state, connection }),
    schedule(fn, delay) { const key = ++id; timers.set(key, { fn, delay }); return key; },
    cancel(key) { timers.delete(key); },
  });
  const emit = (socket, event) => socket.onmessage({ data: JSON.stringify(event) });
  return { client, sockets, updates, timers, emit };
}
test('switching sessions or connections ignores all late callbacks', () => {
  const h = harness();
  h.client.select(demoSessions[0].id);
  const old = h.sockets[0];
  h.client.select(demoSessions[1].id);
  h.emit(old, snapshot(demoSessions[0]));
  old.onclose({ code: 1006 });
  assert.equal(h.client.state.sessionId, demoSessions[1].id);
  assert.equal(h.client.state.awaitingSnapshot, true);
  h.emit(h.sockets[1], snapshot(demoSessions[1]));
  assert.equal(h.client.state.session.id, demoSessions[1].id);
  assert.ok(h.sockets[1].url.startsWith('wss://'));
});
test('sequence loss reconnects with backoff and requests a fresh snapshot', () => {
  const h = harness();
  h.client.select(demoSessions[0].id);
  h.emit(h.sockets[0], snapshot(demoSessions[0]));
  h.emit(h.sockets[0], envelope(demoSessions[0], 'caption.upsert', caption(), 2));
  assert.equal(h.updates.at(-1).connection.kind, 'disconnected');
  const retry = [...h.timers.values()][0];
  assert.equal(retry.delay, 500);
  retry.fn();
  assert.equal(h.sockets.length, 2);
  h.emit(h.sockets[1], snapshot(demoSessions[0], [], 2));
  assert.equal(h.client.state.seq, 2);
});
test('incompatible version stops retries and ended sessions do not reconnect', () => {
  const h = harness();
  h.client.select(demoSessions[0].id);
  h.emit(h.sockets[0], { ...snapshot(demoSessions[0]), protocol_version: 99 });
  assert.equal(h.updates.at(-1).connection.kind, 'incompatible');
  assert.equal(h.timers.size, 0);
  h.client.select(demoSessions[0].id);
  h.emit(h.sockets[1], snapshot({ ...demoSessions[0], status: 'ended' }));
  h.sockets[1].onclose({ code: 1000 });
  assert.equal(h.updates.at(-1).connection.kind, 'ended');
  assert.equal(h.timers.size, 0);
});
test('initial snapshot timeout and slow-client close recover, stop cancels pending retry', () => {
  const h = harness();
  h.client.select(demoSessions[0].id);
  [...h.timers.values()][0].fn();
  assert.equal(h.updates.at(-1).connection.kind, 'disconnected');
  h.client.stop();
  assert.equal(h.timers.size, 0);
  h.client.select(demoSessions[0].id);
  h.emit(h.sockets[1], snapshot(demoSessions[0]));
  h.sockets[1].onclose({ code: 4008 });
  assert.match(h.updates.at(-1).connection.message, /quedó atrás/);
});
test('catalog errors stay errors, never switch to sample data', async () => {
  await assert.rejects(loadSessions({ fetcher: async () => ({ ok: false }) }));
  const sessions = await loadSessions({ fetcher: async () => ({ ok: true, json: async () => ({ sessions: [] }) }) });
  assert.deepEqual(sessions, []);
});
