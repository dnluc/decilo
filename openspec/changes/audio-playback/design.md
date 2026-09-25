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

## Continuación por Codex: generación audible a pedido

Claude dejó de trabajar; el usuario pidió a Codex continuar frontend y backend.
La reproducción del historial es distinta de una prueba de generación en vivo.
Para esta última, con `DECILO_DEMO_SESSIONS=1 DECILO_DEMO_AUTOSTART=0`, las
muestras se registran en `starting` sin ejecutar modelos.

`POST /api/v1/sessions/{id}/start` inicia una muestra preparada, idempotente
mientras siga live/degraded. Una sesión terminal devuelve 409. El navegador
lo solicita tras `playing`, cuando el audio realmente comenzó. El origen
monotónico del worker es la recepción de esa solicitud: hay un desfase de
red y scheduling respecto al navegador, por lo que esta UI no mide p95.
Los subtítulos se muestran al llegar; no se retrasa el audio para ocultar lag.

`POST /api/v1/sessions/{id}/runs` crea una nueva sesión `starting` con el mismo
WAV y un ID nuevo. No borra ni reinicia sesiones existentes. Máximo 20 sesiones
con audio retenidas por proceso, 2 workers de archivo activos; exceso devuelve
429. Solo se sirven archivos registrados por el servidor (sin paths del usuario).
GET audio soporta Range y 404. Las rutas de control requieren el modo demo
explícito; son para ejecución local, sin servicio público de administración.

Pausar, buscar o cambiar de sesión pausa únicamente la reproducción local;
el worker continúa. La UI lo indica. Una nueva prueba pide otra sesión; no
mezcla subtítulos previos. Al cerrar el servidor se cancelan sus tareas.
