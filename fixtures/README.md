# Fixtures del contrato

Generadas desde `src/decilo/models.py` (`scripts/gen_fixtures.py`), que
implementa el envelope y los eventos de
`openspec/changes/contrato-sesiones-subtitulos/`. Sirven para probar la vista de audiencia sin inferencia. El backend ya está
implementado: las fixtures son ejemplos sintéticos del contrato, no resultados
de modelos ni evidencia de rendimiento.

| Archivo | Qué es |
| --- | --- |
| `catalog.json` | `GET /api/v1/sessions` con 2 sesiones (una EN, una ES) |
| `session_detail.json` | `GET /api/v1/sessions/{id}` de una sesión |
| `snapshot_empty.json` | `session.snapshot` de una sesión recién arrancada |
| `caption_transcript_provisional.json` | Transcripción provisional |
| `caption_transcript_final.json` | Misma entrada, confirmada (revisión 2) |
| `caption_translation_final.json` | Traducción de esa entrada, vinculada por `source_revision` |
| `session_status_degraded.json` | Cambio de estado de la sesión |
| `session_error.json` | Error de sesión (motor no disponible) |
| `session_gap.json` | Discontinuidad con retiro de un provisional |
| `event_sequence.json` | Secuencia completa (snapshot → provisional → final → traducción) para probar un reductor de eventos de punta a punta |

Regenerar tras cambiar `src/decilo/models.py`:

```sh
uv run scripts/gen_fixtures.py
```

El contrato público v1 se conserva con Gemini Live y Whisper. `detecting` y
`ready` pertenecen al socket de captura y no a estos envelopes de audiencia.
El manejo de mensajes Live se prueba en `tests/test_gemini_live.py`; un evento
`final` válido estructuralmente no demuestra calidad ni finalización oficial del
proveedor. Ver [arquitectura](../docs/ARQUITECTURA.md).
