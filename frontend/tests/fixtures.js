// Datos de prueba del protocolo v1. Viven acá y no en el código de la
// aplicación: son andamiaje de tests, no algo que se sirva al usuario.

export const sessions = [
  {
    id: 'cap-en',
    title: 'Charla capturada en inglés',
    source_language: 'en',
    translation_languages: ['es'],
    target_locale: 'es-AR',
    status: 'live',
  },
  {
    id: 'cap-es',
    title: 'Charla capturada en español',
    source_language: 'es',
    translation_languages: [],
    target_locale: 'es-AR',
    status: 'live',
  },
];

export function envelope(session, type, data, seq, streamId = 'run-1') {
  return {
    protocol_version: 1,
    session_id: session.id,
    stream_id: streamId,
    seq,
    emitted_at: '2026-09-25T01:00:00.000Z',
    type,
    data,
  };
}

export function snapshot(session, captions = [], seq = 0, streamId = 'run-1') {
  return envelope(session, 'session.snapshot',
    { session, captions, gaps: [], history_truncated: false }, seq, streamId);
}

export function caption(overrides = {}) {
  return {
    segment_id: 'seg-1',
    segment_seq: 1,
    kind: 'transcript',
    language: 'en',
    revision: 1,
    source_revision: null,
    text: 'Before merging the PR,',
    status: 'provisional',
    start_ms: 0,
    end_ms: 1400,
    speaker_id: null,
    boundary_reason: 'pause',
    ...overrides,
  };
}

// Secuencia típica: un original provisional, su traducción, el original
// corregido y confirmado, y la traducción de esa revisión definitiva.
// Sirve para verificar revisiones, invalidación y descarte de resultados
// tardíos sin reescribir el caso en cada test.
export function revisionSequence(session) {
  const finalOriginal = caption({
    revision: 2,
    text: 'Before merging the PR, we need another code review.',
    end_ms: 3200,
    status: 'final',
  });
  return [
    snapshot(session),
    envelope(session, 'caption.upsert', caption(), 1),
    envelope(session, 'caption.upsert', caption({
      kind: 'translation', language: 'es', source_revision: 1,
      text: 'Antes de hacer el merge del PR,',
    }), 2),
    envelope(session, 'caption.upsert', finalOriginal, 3),
    envelope(session, 'caption.upsert', {
      ...finalOriginal, kind: 'translation', language: 'es', source_revision: 2,
      text: 'Antes de hacer el merge del PR, necesitamos otro code review.',
    }, 4),
  ];
}
