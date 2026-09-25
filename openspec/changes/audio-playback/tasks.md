# Tasks

## 1. Contrato y backend

- [ ] 1.1 Implementar `GET /api/v1/sessions/{session_id}/audio` con `FileResponse` (soporte `Range` incluido), 404 sin audio — Responsable: Codex | Estado: pendiente | Depende de: ninguna. Verificación: pedido sin `Range` da 200 con el archivo completo; con `Range` da 206; sesión inexistente/sin audio da 404.

## 2. Frontend

- [ ] 2.1 Agregar elemento `<audio controls>` en la vista de audiencia, apuntando al endpoint de la sesión seleccionada — Responsable: Claude | Estado: en curso | Depende de: 1.1 (probado localmente contra los WAV de muestra mientras tanto). Verificación: se puede reproducir, pausar y buscar en el audio de una sesión.
- [ ] 2.2 Resaltar/seguir el subtítulo correspondiente al punto de reproducción actual usando `start_ms`/`end_ms` — Responsable: Claude | Estado: pendiente | Depende de: 2.1. Verificación: al reproducir, el subtítulo resaltado avanza acorde al audio.

## 3. Integración

- [ ] 3.1 Codex revisa el frontend, Claude revisa el endpoint — Responsable: ambos | Estado: pendiente | Depende de: 1.1, 2.1, 2.2.
