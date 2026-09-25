# Tasks
- [x] 1. Compartir inferencia entre archivos y captura — Responsable: Codex
- [x] 2. Implementar ingreso PCM, límites, gaps y cierre — Responsable: Codex
- [x] 3. Embeber video y capturar pestaña con permiso — Responsable: Codex
- [ ] 4. Verificar protocolo, navegador e inferencia real — Responsable: Codex
- [ ] 5. Revisión cruzada — Responsable: Claude (pendiente de disponibilidad)


Validación: 123 tests Python, 14 Node, 5 de navegador, 4 de integración,
Ruff, build y OpenSpec correctos. La integración simula el permiso con un
MediaStream de oscilador, pero usa AudioWorklet, PCM, WS y gateway reales.
Verifica recepción, falta de pista de audio y liberación al detener. Tests
Python cubren tamaño/orden/duración, cola con descarte y fin de sesión.

Prueba adicional con Whisper/Gemma reales: un WAV conocido se inyectó como
MediaStream (permiso simulado), pasó por el worklet y produjo traducción ES
visible. La sesión llegó a ended al detener. No se prueba así el selector de
Chrome, el audio humano de YouTube ni la calidad/latencia. Tarea 4 parcialmente
verificada: falta la autorización y prueba manual del usuario sobre YouTube.
Metadata del enlace verificada mediante oEmbed de YouTube: API Gateway: On
Contracts, Doors and Dangers of the Outside — Vlad Tomashpolskyi, Nerdearla.

## Revisión del selector del PR #18 — Codex, 2026-09-25

Base revisada: `f209397`, PR de Claude ya integrado al comenzar la revisión.
Correcciones en `codex/review-provider-selector`, con integración solicitada
expresamente por el usuario. Esto no acredita revisión cruzada de Claude sobre
las correcciones nuevas.

- [x] S1 Revisar selector, privacidad de credenciales y aislamiento por sesión — Responsable: Codex | Estado: terminada. La selección se propaga a tareas/threads; la API solo publica presencia de clave.
- [x] S2 Conservar configuración por etapa si falta provider y restaurar contexto al terminar — Responsable: Codex | Estado: terminada. Regresiones cubren defaults nube, híbridos, selección explícita y fallo de captura.
- [x] S3 Permitir nube aunque falle preparación local — Responsable: Codex | Estado: terminada. Tests de captura y archivo verifican aceptación nube y rechazo local.
- [x] S4 Aislar pruebas de .env y servicios pagos — Responsable: Codex | Estado: terminada. Tests unitarios bloquean transportes HTTP reales; fixture de integración usa proveedores simulados y configuración propia.

Validación: 186 tests Python, 23 Node, 20 navegador y 3 de integración correctos;
Ruff y build frontend correctos. Inferencia simulada: no se hicieron llamadas
pagas ni se acredita calidad/latencia de Gemini 3.1 con estos tests. Servidores
de backend, frontend y Ollama detenidos por pedido del usuario.

## Incidente de arranque durante la prueba manual — 2026-09-25

El usuario pudo abrir el selector de Chrome, pero no iniciar captura. El proceso
en 8000 se había iniciado desde el worktree de Claude sin
`DECILO_DEMO_SESSIONS=1` y sin la configuración de nube: catálogo vacío,
`cloud_available=false`, conexión de captura rechazada con HTTP 403.

Codex sincronizó el PR #20 integrado (`a24071a`) y reinició solo el backend
desde su worktree, fijando `DECILO_ENV_FILE` a su `.env`, modo demo habilitado,
autostart y prewarm desactivados. El frontend de Claude en 5173 se conserva.
Verificación a través de su proxy: captura con `provider=local` y con
`provider=gemini` recibe `ready`/`live` y cierra con código 1000 al enviar `stop`.
No se envió PCM ni se invocaron modelos; no se consumió saldo. Nube vuelve a
estar disponible en `/api/v1/providers`. La selección real de pestaña/audio
continúa siendo una prueba manual del usuario.

Para futuros arranques compartidos, usar la configuración explícita del backend
de Codex: `DECILO_ENV_FILE=/home/dnluc/projects/decilo-codex/.env`.
No copiar claves al repo ni iniciar otro backend sin modo demo en el mismo puerto.
