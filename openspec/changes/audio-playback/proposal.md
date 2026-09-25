# Proposal

> **Lectura al 25/09/2026, PR #22 (`e4b9f90`):** Las rutas WAV/runs/start siguen implementadas; el reproductor de archivos y su resaltado se retiraron de la UI. Este artefacto conserva el alcance histórico de esa entrega.
> [Estado global, divergencias y evidencia](../../README.md).

## Why

Para el video demo y para que la vista de audiencia sea más convincente,
hace falta poder escuchar el audio real de la sesión mientras se leen los
subtítulos, no solo verlos en silencio. Los eventos de `caption-stream` ya
llevan `start_ms`/`end_ms` relativos al audio de la sesión — falta el
endpoint que sirva ese audio al navegador.

## What Changes

- Nuevo endpoint `GET /api/v1/sessions/{session_id}/audio` que sirve el
  archivo de audio de la sesión, con soporte de `Range` (necesario para
  que el elemento `<audio>` del navegador pueda buscar/saltar).
- La vista de audiencia agrega un reproductor con controles nativos,
  sincronizado con los subtítulos existentes usando `start_ms`/`end_ms`
  (ya presentes en el contrato, sin campos nuevos).

## Capabilities

### New Capabilities
- `audio-playback`: servir el audio de una sesión para reproducción en el
  navegador, sincronizable con los subtítulos ya existentes.

### Modified Capabilities
Ninguna. No cambia `session-catalog` ni `caption-stream`.

## Impact

Backend (Codex): un endpoint HTTP nuevo, de solo lectura, sin tocar el
worker de sesión ni los eventos. Frontend (Claude): reproductor de audio
y controles en la vista de audiencia, usando los timestamps ya presentes
en los subtítulos para resaltar/seguir el texto en reproducción.
