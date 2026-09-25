const statuses = ['starting', 'live', 'degraded', 'error', 'ended'];
const encoder = new TextEncoder();
const object = x => x !== null && typeof x === 'object' && !Array.isArray(x);
const id = x => typeof x === 'string' && x.trim().length > 0;
const integer = x => Number.isSafeInteger(x) && x >= 0;
const key = c => `${c.kind}:${c.language}`;

export class ProtocolError extends Error {
  constructor(message, incompatible = false) {
    super(message);
    this.incompatible = incompatible;
  }
}
function requireValue(condition, message = 'El servidor envió datos incompatibles.') {
  if (!condition) throw new ProtocolError(message);
}

export function validateSession(s) {
  requireValue(object(s) && id(s.id) && id(s.title) && ['en', 'es'].includes(s.source_language));
  requireValue(Array.isArray(s.translation_languages) && s.translation_languages.every(id));
  requireValue(new Set(s.translation_languages).size === s.translation_languages.length
    && !s.translation_languages.includes(s.source_language));
  requireValue(s.target_locale === null || id(s.target_locale));
  requireValue(statuses.includes(s.status));
  return s;
}
export function validateCatalog(data) {
  requireValue(object(data) && Array.isArray(data.sessions));
  data.sessions.forEach(validateSession);
  requireValue(new Set(data.sessions.map(s => s.id)).size === data.sessions.length);
  return data.sessions;
}
export function initialState(sessionId) {
  return { sessionId, session: null, streamId: null, seq: -1, awaitingSnapshot: true,
    segments: new Map(), gaps: [], historyTruncated: false, restarted: false,
    error: null, evictionFloor: -1 };
}
export function beginConnection(state) {
  return { ...state, awaitingSnapshot: true };
}
function validateCaption(c, session) {
  requireValue(object(c) && id(c.segment_id) && integer(c.segment_seq)
    && integer(c.revision) && c.revision > 0);
  requireValue(['transcript', 'translation'].includes(c.kind)
    && ['provisional', 'final'].includes(c.status));
  requireValue(id(c.text) && encoder.encode(c.text).length <= 8192);
  requireValue(integer(c.start_ms) && integer(c.end_ms) && c.start_ms <= c.end_ms);
  requireValue(c.speaker_id == null || id(c.speaker_id));
  requireValue(c.boundary_reason == null || ['pause', 'semantic', 'deadline', 'end_of_stream'].includes(c.boundary_reason));
  requireValue(c.kind === 'transcript'
    ? c.language === session.source_language && c.source_revision === null
    : session.translation_languages.includes(c.language) && integer(c.source_revision) && c.source_revision > 0);
}
function upsert(state, c) {
  validateCaption(c, state.session);
  if (c.segment_seq <= state.evictionFloor) return;
  let segment = state.segments.get(c.segment_id);
  if (segment) {
    requireValue(segment.seq === c.segment_seq);
  } else {
    requireValue(![...state.segments.values()].some(s => s.seq === c.segment_seq));
    segment = { seq: c.segment_seq, entries: new Map(), revisions: new Map() };
  }
  segment = { ...segment, entries: new Map(segment.entries), revisions: new Map(segment.revisions) };
  const entryKey = key(c);
  const old = segment.entries.get(entryKey);
  if (c.revision <= (segment.revisions.get(entryKey) || 0)) return;
  requireValue(old?.status !== 'final', 'Se intentó modificar un subtítulo confirmado.');
  if (old) requireValue(old.start_ms === c.start_ms && old.end_ms <= c.end_ms);
  if (c.kind === 'translation') {
    const original = segment.entries.get(`transcript:${state.session.source_language}`);
    // A late result must never resurrect a translation of an outdated original.
    if (!original || c.source_revision < original.revision) return;
    requireValue(c.source_revision === original.revision);
    requireValue(c.start_ms === original.start_ms && c.end_ms === original.end_ms);
    requireValue(c.status !== 'final' || original.status === 'final');
  } else {
    for (const [k, value] of segment.entries) {
      if (value.kind === 'translation' && value.source_revision !== c.revision) segment.entries.delete(k);
    }
  }
  segment.entries.set(entryKey, c);
  segment.revisions.set(entryKey, c.revision);
  state.segments.set(c.segment_id, segment);
}
function validateGap(g) {
  requireValue(object(g) && id(g.gap_id)
    && ['overload', 'source_disconnect', 'processing_error'].includes(g.reason));
  requireValue((g.start_ms === null && g.end_ms === null)
    || (integer(g.start_ms) && integer(g.end_ms) && g.start_ms <= g.end_ms));
  requireValue(Array.isArray(g.discard_captions) && g.discard_captions.every(c =>
    object(c) && id(c.segment_id) && ['transcript', 'translation'].includes(c.kind) && id(c.language)));
}
function applyGap(state, gap) {
  validateGap(gap);
  for (const c of gap.discard_captions) {
    const segment = state.segments.get(c.segment_id);
    const value = segment?.entries.get(key(c));
    if (!value || value.status === 'final') continue;
    const updated = { ...segment, entries: new Map(segment.entries) };
    updated.entries.delete(key(c));
    if (c.kind === 'transcript') {
      for (const [k, v] of updated.entries) if (v.kind === 'translation') updated.entries.delete(k);
    }
    state.segments.set(c.segment_id, updated);
  }
  const gaps = [...state.gaps.filter(g => g.gap_id !== gap.gap_id), gap];
  if (gaps.length > 100) state.historyTruncated = true;
  state.gaps = gaps.slice(-100);
}
function retain(state) {
  const ordered = [...state.segments.entries()].sort((a, b) => a[1].seq - b[1].seq);
  for (const [segmentId, segment] of ordered.slice(0, Math.max(0, ordered.length - 100))) {
    state.segments.delete(segmentId);
    state.evictionFloor = Math.max(state.evictionFloor, segment.seq);
    state.historyTruncated = true;
  }
}

// Pure transition: failed messages cannot partially change the visible state.
export function applyEvent(previous, event) {
  requireValue(object(event));
  if (event.session_id !== previous.sessionId && id(event.session_id)) return previous;
  if (event.protocol_version !== 1) throw new ProtocolError('Versión de subtítulos no compatible. Actualizá la página.', true);
  requireValue(event.session_id === previous.sessionId && id(event.stream_id) && integer(event.seq)
    && typeof event.emitted_at === 'string' && Number.isFinite(Date.parse(event.emitted_at)) && object(event.data));
  if (event.type === 'session.snapshot') {
    requireValue(previous.awaitingSnapshot, 'Snapshot inesperado: recuperando la conexión.');
    const { session, captions, gaps, history_truncated } = event.data;
    validateSession(session);
    requireValue(session.id === previous.sessionId && Array.isArray(captions) && Array.isArray(gaps)
      && typeof history_truncated === 'boolean');
    const state = { ...initialState(previous.sessionId), session, streamId: event.stream_id,
      seq: event.seq, awaitingSnapshot: false, historyTruncated: history_truncated,
      restarted: previous.restarted || (previous.streamId !== null && previous.streamId !== event.stream_id) };
    // Snapshot order is not guaranteed to put the original before its translations.
    captions.forEach(c => validateCaption(c, session));
    for (const c of [...captions].sort((a, b) => (a.kind === 'translation') - (b.kind === 'translation'))) upsert(state, c);
    gaps.forEach(g => applyGap(state, g));
    retain(state);
    return state;
  }
  requireValue(!previous.awaitingSnapshot, 'Falta el snapshot inicial.');
  requireValue(event.stream_id === previous.streamId, 'El flujo se reinició: recuperando historial.');
  if (event.seq <= previous.seq) return previous;
  requireValue(event.seq === previous.seq + 1, 'Se perdieron actualizaciones: recuperando historial.');
  const state = { ...previous, seq: event.seq, segments: new Map(previous.segments), gaps: [...previous.gaps] };
  switch (event.type) {
    case 'caption.upsert': upsert(state, event.data); break;
    case 'session.status':
      validateSession(event.data.session);
      requireValue(event.data.session.id === previous.sessionId);
      state.session = event.data.session;
      break;
    case 'session.error':
      requireValue(id(event.data.code) && id(event.data.message) && typeof event.data.retryable === 'boolean');
      state.error = event.data;
      break;
    case 'session.gap': applyGap(state, event.data); break;
    default: throw new ProtocolError('Tipo de evento no compatible: recuperando la conexión.');
  }
  retain(state);
  return state;
}
export function visibleCaptions(state, language) {
  return [...state.segments.entries()].sort((a, b) => a[1].seq - b[1].seq).flatMap(([segmentId, s]) => {
    const original = s.entries.get(`transcript:${state.session?.source_language}`);
    if (!original) return [];
    const caption = language === original.language ? original : s.entries.get(`translation:${language}`);
    return [{ segmentId, original, caption: caption || null }];
  });

}
