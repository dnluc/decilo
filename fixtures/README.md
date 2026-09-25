# Fixtures del contrato

Generadas desde `src/decilo/models.py` (`scripts/gen_fixtures.py`), que
implementa el envelope y los eventos de
`openspec/changes/contrato-sesiones-subtitulos/`. Sirven para construir y
probar la vista de audiencia sin esperar al backend real — el contrato ya
está aceptado, estas fixtures son válidas contra los modelos.

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
