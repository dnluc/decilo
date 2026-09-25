// Synthetic UI examples, never an ASR benchmark or a fallback for a failed API.
export const demoSessions = [
  { id: 'demo-systems', title: 'Building reliable systems', source_language: 'en', translation_languages: ['es'], target_locale: 'es-AR', status: 'live' },
  { id: 'demo-comunidad', title: 'Código abierto, comunidad abierta', source_language: 'es', translation_languages: [], target_locale: 'es-AR', status: 'live' },
];
export function envelope(session, type, data, seq, streamId = 'demo-run') {
  return { protocol_version: 1, session_id: session.id, stream_id: streamId, seq,
    emitted_at: '2026-09-25T01:00:00.000Z', type, data };
}
export function snapshot(session, captions = [], seq = 0, streamId = 'demo-run') {
  return envelope(session, 'session.snapshot', { session, captions, gaps: [], history_truncated: false }, seq, streamId);
}
export function caption(overrides = {}) {
  return { segment_id: 'seg-1', segment_seq: 1, kind: 'transcript', language: 'en',
    revision: 1, source_revision: null, text: 'Before merging the PR,', status: 'provisional',
    start_ms: 0, end_ms: 1400, speaker_id: null, boundary_reason: 'pause', ...overrides };
}
export function demoEvents(session) {
  if (session.source_language === 'es') return [snapshot(session),
    envelope(session, 'caption.upsert', caption({ language: 'es', text: 'El código abierto se construye en comunidad.', status: 'final' }), 1),
    envelope(session, 'caption.upsert', caption({ language: 'es', segment_id: 'seg-2', segment_seq: 2, start_ms: 1800, end_ms: 4200, text: 'Compartir lo que aprendemos también es contribuir.', status: 'final' }), 2),
  ];
  const original = caption({ revision: 2, text: 'Before merging the PR, we need another code review.', end_ms: 3200, status: 'final' });
  return [snapshot(session),
    envelope(session, 'caption.upsert', caption(), 1),
    envelope(session, 'caption.upsert', caption({ kind: 'translation', language: 'es', source_revision: 1, text: 'Antes de hacer el merge del PR,' }), 2),
    envelope(session, 'caption.upsert', original, 3),
    envelope(session, 'caption.upsert', { ...original, kind: 'translation', language: 'es', source_revision: 2, text: 'Antes de hacer el merge del PR, necesitamos otro code review.' }, 4),
    envelope(session, 'caption.upsert', caption({ segment_id: 'seg-2', segment_seq: 2, start_ms: 3500, end_ms: 6000, text: 'Small changes make systems easier to understand.', status: 'final' }), 5),
    envelope(session, 'caption.upsert', caption({ segment_id: 'seg-2', segment_seq: 2, start_ms: 3500, end_ms: 6000, kind: 'translation', language: 'es', source_revision: 1, text: 'Los cambios pequeños hacen que los sistemas sean más fáciles de entender.', status: 'final' }), 6),
  ];
}
