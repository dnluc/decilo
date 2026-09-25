Revisión de Codex sobre `c884ebe`. **Solicito cambios antes de integrar**: los tests actuales pasan, pero hay un bloqueo de conexión con la audiencia y casos del contrato que no ejercitan.

> **Lectura al 25/09/2026, PR #22 (`e4b9f90`):** Pipeline implementado e integrado. Whisper final small EN/ES, provisional base, Gemma e2b y Gemini Live/REST; las decisiones/mediciones previas conservan su fecha y configuración.
> [Estado global, divergencias y evidencia](../../README.md).

1. **[P1] Publicar JSON como frames de texto** — `src/decilo/gateway.py:66,73`. `send_bytes()` hace que el navegador entregue un Blob; `frontend/src/connection.js` exige `typeof data === 'string'` antes de parsear. La UI rechaza incluso el primer snapshot y reconecta indefinidamente. Reproduje el frame binario mediante el endpoint real con TestClient (`['type', 'bytes']`). Usar frames de texto y agregar una prueba del gateway con el consumidor real; los fakes actuales solo prueban bytes contra bytes.

2. **[P1] Detener y cerrar efectivamente al suscriptor desbordado** — `src/decilo/gateway.py:50-73`. Tras llenar la cola se agrega otro `None` por cada evento a una Queue sin maxsize. Reproduje **1000 elementos pendientes**, aunque el límite anunciado es 64. Además el cierre queda detrás del backlog y no se alcanza si `send_bytes` está bloqueado. Marcar/retirar al cliente una sola vez, acotar cola y send pendiente, y poder cerrar/cancelar el envío sin esperar a drenar todo el backlog. Probar un websocket cuyo envío se bloquea y comprobar memoria acotada y cierre 4008, además del consumidor rápido.

3. **[P2] Aplicar el límite de bytes al snapshot** — `src/decilo/stream.py:51-76`. Retener 100 segmentos no garantiza el máximo de 1 MiB. Con 100 originales y sus traducciones, cada texto válido de 8192 bytes, obtuve **1.678.898 bytes**. El cliente rechaza el snapshot y cada reconexión vuelve a recibirlo. Evictar segmentos completos y luego gaps según el presupuesto serializado, marcando `history_truncated`; incluir el snapshot en los límites del gateway.

4. **[P2] Unificar el estado del registro HTTP y el stream** — `src/decilo/pipeline.py:122-123` y `src/decilo/stream.py:105-106`. El worker termina actualizando solo `stream.session`, mientras el catálogo y detalle leen `registry`. Reproduje HTTP `live` y snapshot `ended` para el mismo ID. Los nuevos espectadores siguen viendo una charla en vivo ya terminada. Canalizar las transiciones por una fuente de estado común y validar transiciones también desde el worker, no solo en los tests aislados de SessionRecord.

5. **[P2] Validar revisiones y relación original/traducción antes de mutar el estado** — `src/decilo/stream.py:78-96`. `upsert_caption` permite retroceder un original de revisión 2 a 1 y confirmar una traducción de un original provisional. También acepta traducciones sin original/vinculadas a una revisión antigua y rechaza la repetición idéntica de un final que el contrato declara idempotente. Reproduje el retroceso y la confirmación inválida; una reconexión recibe ese estado autoritativo incorrecto. Validar relaciones, orden/revisiones e idempotencia antes de modificar retención o secuencia, con pruebas que usen el reductor de audiencia.

6. **[P2] Detectar desconexiones durante silencio o al terminar una charla** — `src/decilo/gateway.py:67-68`. El handler solo envía y espera `queue.get()`, nunca recibe `websocket.disconnect`. Si el espectador cambia de sala cuando no hay eventos, no sale del bucle ni se ejecuta el `finally`; quedan el handler y la suscripción retenidos hasta otro envío o apagado. Esperar también desconexión y cancelar la tarea complementaria al salir; probar conectar/desconectar sin publicar eventos.

Validación ejecutada:
- **95 tests correctos**, Ruff de `src`, `tests`, `scripts` sin errores. En NixOS se agregó la ruta de libstdc++ al entorno de prueba para cargar las dependencias nativas; no fue un fallo del PR.
- Endpoint WebSocket con TestClient: primer frame binario confirmado. Estado HTTP/snapshot divergente reproducido.
- Pruebas directas del stream/gateway: cola de 1000 elementos, snapshot de 1.678.898 bytes, revisión regresiva y traducción final de original provisional.
- No ejecuté inferencia ni repetí la medición de audio real. Los grupos 5/6 siguen pendientes como declara el PR; esta revisión no exige que este commit demuestre p95 ni sobrecarga de ingestión.

Antes del merge, cubrir estos casos como regresión y probar frontend + gateway juntos. La CI verde actual no valida esa integración: sus pruebas de navegador sustituyen el WebSocket con frames de texto simulados.
