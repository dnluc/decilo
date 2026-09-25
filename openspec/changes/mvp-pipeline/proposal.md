# Proposal

## Why

`arquitectura-base` fijó los drivers y `contrato-sesiones-subtitulos` fijó
el contrato de eventos que consume la audiencia. Falta la pieza que
produce esos eventos a partir de audio real: sin ella no hay MVP
demostrable para la Vibeathon. Este cambio construye esa pieza (captura de
audio, transcripción y traducción) del lado de Claude, según el reparto
confirmado en `COLLABORATION.md`.

## What Changes

- Ingerir audio de al menos una fuente (archivo de audio como entrada
  mínima reproducible; micrófono si el tiempo lo permite).
- Transcribir el audio en su idioma original (ES o EN) con Whisper local.
- Traducir EN→ES el texto transcripto, usando un modelo de texto vía Ollama.
- Producir los eventos `session.snapshot`, `caption.upsert`,
  `session.status`, `session.error` y `session.gap` tal como los define
  `contrato-sesiones-subtitulos` (specs `session-catalog` y
  `caption-stream`), incluyendo revisiones, invalidación de traducciones
  obsoletas y manejo de sobrecarga con cola acotada por sesión.
- Exponer `GET /api/v1/sessions`, `GET /api/v1/sessions/{id}` y
  `WS /api/v1/sessions/{id}/events` para que la vista de audiencia (a
  cargo de Codex) pueda consumirlos de forma independiente.
- Aislar cada sesión para que la caída de una no afecte a las demás
  (driver de `system-architecture`).

## Capabilities

### New Capabilities
- `speech-pipeline`: ingesta de audio, transcripción y traducción por
  sesión, con la lógica de revisión/invalidación y aislamiento de fallos
  necesaria para alimentar los eventos de `caption-stream`.

### Modified Capabilities
Ninguna. No hay specs consolidadas todavía (`arquitectura-base` y
`contrato-sesiones-subtitulos` siguen sin archivar); este cambio implementa
contra sus artefactos vigentes sin alterar sus requirements.

## Impact

Introduce el primer código de aplicación del repo (hasta ahora solo había
documentación y specs). Implementa el lado servidor de
`GET /api/v1/sessions`, `GET /api/v1/sessions/{id}` y
`WS /api/v1/sessions/{id}/events` definidos en `contrato-sesiones-subtitulos`.
Depende de Ollama corriendo localmente (`localhost:11434`) y de un motor de
STT local (Whisper vía `faster-whisper` o `whisper.cpp`) todavía por
seleccionar con evidencia (tarea pendiente de `arquitectura-base` 3.2/3.3).
No incluye la vista de audiencia (frontend), que Codex implementa por
separado contra el mismo contrato.
