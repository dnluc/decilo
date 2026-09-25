# Proposal

## Why

Backend y audiencia necesitan un contrato común para implementar en paralelo
sin mezclar sesiones ni sobrescribir traducciones con resultados obsoletos.
Definirlo ahora conserva la incrementalidad de `VISION.md` y permite probar
la interfaz mientras se valida el motor de audio en `arquitectura-base`.

## What Changes

- Definir consulta de sesiones, idiomas disponibles y estados de operación.
- Proponer eventos WebSocket versionados con snapshot inicial y recuperación
  tras desconexión, con historial reciente acotado.
- Identificar segmentos, revisiones y relación entre original y traducción;
  diferenciar provisional y definitivo, descartando resultados obsoletos.
- Definir errores visibles, discontinuidades y espectadores lentos sin
  bloquear otras sesiones.
- Reservar metadatos opcionales para hablantes y segmentación semántica sin
  exigir que esos experimentos existan para producir subtítulos.

## Capabilities

### New Capabilities

- `session-catalog`: consulta de sesiones, idiomas y estado para la audiencia.
- `caption-stream`: entrega incremental, consistencia y recuperación de subtítulos.

### Modified Capabilities

Ninguna. No hay specs consolidadas; los drivers de `arquitectura-base` siguen
vigentes y este cambio concreta el límite entre backend y audiencia.

## Impact

Se especifican `GET /api/v1/sessions`, `GET /api/v1/sessions/{id}` y
`WS /api/v1/sessions/{id}/events`. No existe implementación actual a migrar.
Los ejemplos de `design.md` sirven como fixtures de referencia para ambos lados.

Esta entrega redacta la propuesta, no implementa los endpoints ni valida
Whisper/Gemma. No define ingestión de audio, administración/autenticación,
persistencia completa, framework de UI ni reparto de implementación.
El contrato queda pendiente de revisión de Claude según `COLLABORATION.md`.
