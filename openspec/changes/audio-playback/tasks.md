# Tasks

## 1. Contrato y backend

- [ ] 1.1 Implementar `GET /api/v1/sessions/{session_id}/audio` con `FileResponse` (soporte `Range` incluido), 404 sin audio — Responsable: Codex | Estado: pendiente | Depende de: ninguna. Verificación: pedido sin `Range` da 200 con el archivo completo; con `Range` da 206; sesión inexistente/sin audio da 404.

## 2. Frontend

- [ ] 2.1 Agregar elemento `<audio controls>` en la vista de audiencia, apuntando al endpoint de la sesión seleccionada — Responsable: Claude | Estado: en curso | Depende de: 1.1 (probado localmente contra los WAV de muestra mientras tanto). Verificación: se puede reproducir, pausar y buscar en el audio de una sesión.
- [ ] 2.2 Resaltar/seguir el subtítulo correspondiente al punto de reproducción actual usando `start_ms`/`end_ms` — Responsable: Claude | Estado: pendiente | Depende de: 2.1. Verificación: al reproducir, el subtítulo resaltado avanza acorde al audio.

## 3. Integración

- [ ] 3.1 Codex revisa el frontend, Claude revisa el endpoint — Responsable: ambos | Estado: pendiente | Depende de: 1.1, 2.1, 2.2.

## Continuación por Codex solicitada por el usuario

Codex asume también el frontend tras el handoff de Claude. La propuesta se
amplía con inicio a pedido y sesiones nuevas; ver diseño y escenarios nuevos.

- [x] C1 Servir WAV/Range y crear/iniciar pruebas con límites — Responsable: Codex | Estado: terminada. 116 tests Python correctos: 200/206/404, controles deshabilitados fuera de demo, idempotencia, dos workers, veinte sesiones retenidas, rechazo de sesión terminal.
- [x] C2 Reproductor, inicio tras playing, historial independiente y resaltado temporal — Responsable: Codex | Estado: terminada. 14 tests Node, 5 pruebas de navegador y 2 de integración correctos. Integración reproduce WAV real con inferencia falsa explícita, verifica inicio, IDs distintos, resaltado y pausa al cambiar de sesión. Build y Ruff correctos.
- [ ] C3 Revisión cruzada de la implementación — Responsable: Claude | Estado: pendiente. Claude no está activo; no se afirma revisión ni se integra código propio automáticamente.

Las tareas 1.1/2.1/2.2 originales quedan cubiertas por C1/C2; autoría de la
implementación final Codex, propuesta inicial Claude. La integración 3.1 queda
pendiente de revisión. No se valida aquí calidad ni cumplimiento de latencia.

Prueba adicional con inferencia real: backend aislado 18767 y Vite 5176,
Whisper/Gemma locales. Playwright comprobó audio avanzando (`paused=false`,
`muted=false`, volumen 1, readyState 4) y traducción ES visible tras Iniciar
prueba. No equivale a confirmar el volumen del dispositivo físico ni p95.
