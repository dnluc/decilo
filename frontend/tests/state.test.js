import test from 'node:test';
import assert from 'node:assert/strict';
import { applyEvent, initialState, beginConnection, visibleCaptions, validateCatalog } from '../src/state.js';
import { sessions, snapshot, envelope, caption, revisionSequence } from './fixtures.js';
const session = sessions[0];
const start = () => applyEvent(initialState(session.id), snapshot(session));
const send = (state, value) => applyEvent(state, envelope(session, 'caption.upsert', value, state.seq + 1));

test('original revisions replace text, invalidate translation, and discard late results', () => {
  const events = revisionSequence(session);
  let state = events.slice(0, 3).reduce(applyEvent, initialState(session.id));
  assert.equal(visibleCaptions(state, 'es')[0].caption.text, 'Antes de hacer el merge del PR,');
  state = applyEvent(state, events[3]);
  assert.equal(visibleCaptions(state, 'es')[0].caption, null);
  state = send(state, caption({ kind: 'translation', language: 'es', source_revision: 1, text: 'Viejo' }));
  assert.equal(visibleCaptions(state, 'es')[0].caption, null);
  state = send(state, events[4].data);
  assert.equal(visibleCaptions(state, 'es')[0].caption.status, 'final');
  assert.equal(state.segments.size, 1);
});
test('duplicates are ignored and confirmed captions cannot be rewritten', () => {
  const state = send(start(), caption({ status: 'final' }));
  assert.equal(send(state, caption()).segments.get('seg-1').entries.get('transcript:en').status, 'final');
  assert.throws(() => send(state, caption({ revision: 2 })), /confirmado/);
  assert.equal(applyEvent(state, envelope(session, 'caption.upsert', caption(), state.seq)), state);
});
test('a translation cannot become final before its original', () => {
  const state = send(start(), caption());
  assert.throws(() => send(state, caption({ kind: 'translation', language: 'es', source_revision: 1, status: 'final' })));
});
test('snapshot replaces history, handles reverse entry order and signals a new generation', () => {
  const original = caption({ status: 'final' });
  const translation = caption({ kind: 'translation', language: 'es', source_revision: 1, status: 'final' });
  const state = applyEvent(beginConnection(send(start(), original)), snapshot(session, [translation, original], 20, 'new-run'));
  assert.equal(visibleCaptions(state, 'es')[0].caption.status, 'final');
  assert.equal(state.restarted, true);
  const cleared = applyEvent(beginConnection(state), snapshot(session, [], 21, 'new-run'));
  assert.equal(cleared.segments.size, 0);
});
test('missing snapshot, skipped seq, unknown version/type and changed generation fail visibly', () => {
  const event = envelope(session, 'caption.upsert', caption(), 1);
  assert.throws(() => applyEvent(initialState(session.id), event), /snapshot/);
  assert.throws(() => applyEvent(start(), { ...event, seq: 2 }), /perdieron/);
  assert.throws(() => applyEvent(start(), { ...event, stream_id: 'new' }), /reinició/);
  assert.throws(() => applyEvent(start(), { ...event, protocol_version: 2 }), /Versión/);
  assert.throws(() => applyEvent(start(), { ...event, type: 'unknown' }), /Tipo/);
  assert.equal(applyEvent(start(), { ...event, session_id: 'other' }).seq, 0);
});
test('gaps remove only provisional entries, including dependent translations', () => {
  let state = send(start(), caption({ status: 'final' }));
  state = send(state, caption({ kind: 'translation', language: 'es', source_revision: 1 }));
  state = applyEvent(state, envelope(session, 'session.gap', { gap_id: 'gap', start_ms: null, end_ms: null,
    reason: 'processing_error', discard_captions: [{ segment_id: 'seg-1', kind: 'translation', language: 'es' },
      { segment_id: 'seg-1', kind: 'transcript', language: 'en' }] }, state.seq + 1));
  assert.equal(visibleCaptions(state, 'en')[0].caption.status, 'final');
  assert.equal(visibleCaptions(state, 'es')[0].caption, null);
  assert.equal(state.gaps.length, 1);
});
test('bounded retention orders by audio and ignores results for evicted segments', () => {
  let state = start();
  for (let i = 1; i <= 105; i++) state = send(state, caption({ segment_id: `s${i}`, segment_seq: i }));
  assert.equal(state.segments.size, 100);
  assert.equal(state.historyTruncated, true);
  assert.equal(visibleCaptions(state, 'en')[0].segmentId, 's6');
  state = send(state, caption({ segment_id: 's1', segment_seq: 1, revision: 2 }));
  assert.equal(state.segments.has('s1'), false);
});
test('invalid captions cannot corrupt state; text stays data and errors do not change session status', () => {
  const state = start();
  assert.throws(() => send(state, caption({ text: 'á'.repeat(4097) })));
  assert.throws(() => send(state, caption({ start_ms: -1 })));
  assert.throws(() => send(state, caption({ language: 'xx' })));
  assert.equal(state.segments.size, 0);
  const text = '<img src=x onerror=alert(1)>';
  const next = send(state, caption({ text }));
  assert.equal(visibleCaptions(next, 'en')[0].caption.text, text);
  const failed = applyEvent(next, envelope(session, 'session.error', { code: 'source_unavailable', message: 'Sin audio', retryable: true }, 2));
  assert.equal(failed.session.status, 'live');
});
test('catalog accepts no sessions but rejects duplicate identifiers', () => {
  assert.deepEqual(validateCatalog({ sessions: [] }), []);
  assert.throws(() => validateCatalog({ sessions: [session, session] }));
});
