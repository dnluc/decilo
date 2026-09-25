# Design

## Context

Ver `proposal.md`. Las sesiones de muestra ya tienen su audio en
`samples/*.wav`; el worker (`pipeline.py`) ya conoce ese path por sesión.
Los eventos de `caption-stream` ya llevan `start_ms`/`end_ms` en
milisegundos relativos al inicio del audio de la sesión — el reproductor
no necesita ningún campo nuevo para sincronizarse, solo leer los que ya
existen.

## Goals / Non-Goals

**Goals:**
- Servir el audio real de cada sesión para reproducción en el navegador.
- Reproductor con controles nativos (play/pausa, volumen, progreso) en la
  vista de audiencia, que resalta/sigue el subtítulo correspondiente al
  punto de reproducción actual.

**Non-Goals:**
- Streaming en vivo desde micrófono (sigue siendo archivo, como el resto
  del MVP).
- Transcodificación o normalización de audio — se sirve el archivo tal
  cual está.
- Sincronización estricta con la generación del subtítulo (el resaltado
  es aproximado, basado en `start_ms`/`end_ms`, no un requisito de
  precisión de frames).

## Decisions

### Backend: `FileResponse` de FastAPI/Starlette

Starlette's `FileResponse` ya maneja `Range` (206) automáticamente al
servir un archivo, así que no hace falta implementarlo a mano — solo
resolver el path del audio por `session_id` y devolverlo con
`FileResponse(path, media_type="audio/wav")`, 404 si no existe.

### Frontend: `<audio>` nativo + resaltado por tiempo

Usar el elemento `<audio controls>` nativo (controles de play/pausa/
volumen/progreso gratis, accesibles) apuntando a
`/api/v1/sessions/{id}/audio`. Escuchar su evento `timeupdate` y usar
`audio.currentTime * 1000` para encontrar qué subtítulo mostrar como
"actual" (el que tiene `start_ms <= currentTime*1000 < end_ms`),
resaltándolo en la transcripción sin cambiar la lógica de `state.js`
existente. Si el usuario no interactúa, el audio no arranca solo
(los navegadores bloquean autoplay con sonido) — el control nativo ya
resuelve eso.

## Risks / Trade-offs

- [Riesgo] El resaltado por tiempo puede desincronizarse un poco de la
  llegada real del subtítulo (que depende de cuándo se procesó, no de
  cuándo se escuchó) → aceptado para v1, es solo una ayuda visual, no
  una garantía del contrato.
- [Riesgo] Servir el WAV sin comprimir es pesado para conexiones lentas →
  aceptado para el MVP/demo; no bloquea el objetivo del hackathon.
