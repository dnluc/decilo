# Tasks

## 1. Contrato y backend

- [ ] 1.1 Implementar `GET /api/v1/sessions/{session_id}/audio` con `FileResponse` (soporte `Range` incluido), 404 sin audio — Responsable: Codex | Estado: pendiente | Depende de: ninguna. Verificación: pedido sin `Range` da 200 con el archivo completo; con `Range` da 206; sesión inexistente/sin audio da 404.
  **Importante (verificado por Claude 2026-09-25)**: el soporte de `Range`
  no es opcional. Sin `Accept-Ranges`/206 el navegador deja `seekable`
  vacío y **no permite mover la reproducción** (lo comprobé: con un mock
  sin Range, `audio.currentTime = 7` queda en 0). `FileResponse` de
  Starlette ya lo resuelve solo.
  Mientras tanto hay un stub de desarrollo en `scripts/dev_audio_stub.py`
  (solo para poder desarrollar el frontend; **no es parte de la app**).
  Codex: reemplazalo por el endpoint real en `src/decilo/app.py` y borrá
  el stub.

## 2. Frontend

- [x] 2.1 Agregar elemento `<audio controls>` en la vista de audiencia, apuntando al endpoint de la sesión seleccionada — Responsable: Claude | Estado: terminada | Depende de: 1.1 (probado contra el stub de desarrollo). Verificación (2026-09-25): `frontend/src/player.js` + `#audio-player` en `index.html`; test de navegador `player.spec.js` confirma que carga metadata y se puede mover la reproducción. Se oculta en modo `?demo=1` (la muestra no tiene audio real) y muestra un aviso legible si el audio no carga.
- [x] 2.2 Resaltar/seguir el subtítulo correspondiente al punto de reproducción actual usando `start_ms`/`end_ms` — Responsable: Claude | Estado: terminada | Depende de: 2.1. Verificación (2026-09-25): `player.spec.js` cubre que el resaltado sigue la posición del audio, que no resalta nada antes de reproducir ni más allá del último subtítulo, y que sobrevive a un render completo cuando llegan subtítulos nuevos. El resaltado se aplica sin redibujar la transcripción (`timeupdate` dispara varias veces por segundo y pelearía con el scroll).

## 3. Integración

- [ ] 3.1 Codex revisa el frontend, Claude revisa el endpoint — Responsable: ambos | Estado: pendiente | Depende de: 1.1, 2.1, 2.2.

## Nota de entorno (Claude, 2026-09-25)

El Chrome de automatización que usé para inspeccionar la UI **no carga
media** (falla incluso un WAV embebido como `data:` URI), así que la
reproducción audible no se pudo verificar por esa vía. Sí se verificó:
el endpoint responde correctamente (`curl`: 200, 206 con `Range`, 404),
y los tests de Playwright — que corren en el Chrome del sistema — cargan
el audio de verdad (`readyState 4`, `duration` correcta) y validan el
resaltado. Queda pendiente una escucha manual del audio antes de grabar
el video.
