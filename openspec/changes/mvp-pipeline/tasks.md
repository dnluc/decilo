# Tasks

## CI mínima — alcance agregado por el usuario (2026-09-24)

- [x] CI.1 Preparar workflow de push/PR con Python 3.12, compilación, Ruff y pytest — Responsable: Codex | Estado: terminada | Depende de: ninguna. Rama: `codex/ci-minima`. Validación: actionlint 1.7.12 sin errores, herramientas instaladas y `pip check` correcto; detección ensayada con/sin `src/` y ausencia de tests comprobada como fallo. No se ejecutaron tests de aplicación: todavía no hay backend en esta revisión. Convenciones y límites en `docs/ci.md`.
- [ ] CI.2 Revisar el workflow y sus convenciones antes de integrar el PR — Responsable: Claude | Estado: pendiente | Depende de: CI.1. El usuario eligió PRs para código/configuración; Sonar y CodeRabbit se postergan.
- [ ] CI.3 Confirmar ejecución de los tests reales del backend en Actions — Responsable: Codex | Estado: bloqueada | Depende de: 1.1 y tests del pipeline. La etapa inicial sin `src/` solo informa que el backend está pendiente; no acredita compilación ni pruebas de aplicación.

## 1. Base del proyecto Python

- [ ] 1.1 Estructurar el proyecto Python (`pyproject.toml` o `requirements.txt`, carpeta `src/`) e instalar `faster-whisper`, `httpx`, `fastapi`, `uvicorn`, `pydantic` — Responsable: Claude | Estado: pendiente | Depende de: ninguna. Verificación: `python -m src.app --help` (o equivalente) corre sin error de import.
- [ ] 1.2 Conseguir/generar 2 audios de prueba cortos (ES y EN) con contenido técnico conocido, incluidos en el repo con su licencia de uso indicada — Responsable: Claude | Estado: pendiente | Depende de: ninguna. Verificación: archivos en `samples/` con transcripción de referencia anotada a mano en un `.txt` al lado.

## 2. Spike de calidad y latencia (resuelve arquitectura-base 3.2/3.3)

- [ ] 2.1 Medir `faster-whisper` (small y medium) transcribiendo los audios de prueba: tiempo de proceso vs. duración de audio, y comparar texto contra la referencia — Responsable: Claude | Estado: pendiente | Depende de: 1.1, 1.2. Verificación: tabla con modelo, tiempo, errores de transcripción (omisiones, nombres, números) registrada en este archivo.
- [ ] 2.2 Medir traducción EN→ES con `gemma3n:e4b` vía Ollama sobre las transcripciones del paso anterior: tiempo de respuesta y revisión manual de calidad (sentido, términos técnicos) — Responsable: Claude | Estado: pendiente | Depende de: 2.1. Verificación: tabla de latencia + revisión de calidad registrada en este archivo.
- [ ] 2.3 Con los datos de 2.1/2.2, fijar el modelo de Whisper y confirmar (o cambiar) el modelo de Ollama para traducción; actualizar `design.md` con la decisión final — Responsable: Claude | Estado: bloqueada | Depende de: 2.1, 2.2. Verificación: `design.md` ya no dice "a definir/a confirmar" para el motor.

## 3. Registro de sesiones y catálogo

- [ ] 3.1 Implementar el registro de sesiones en memoria y `GET /api/v1/sessions`, `GET /api/v1/sessions/{id}` según `specs/session-catalog` — Responsable: Claude | Estado: bloqueada | Depende de: 1.1. Verificación: request a ambos endpoints con 0, 1 y 2 sesiones configuradas, incluyendo 404 para sesión inexistente.
- [ ] 3.2 Implementar las transiciones de estado (`starting`, `live`, `degraded`, `error`, `ended`) según las reglas de `session-catalog` — Responsable: Claude | Estado: bloqueada | Depende de: 3.1. Verificación: prueba unitaria de las transiciones permitidas/rechazadas.
- [ ] 3.3 Modelar los envelopes del contrato (Pydantic) con validación estricta y publicar fixtures de catálogo/snapshot/eventos en un path compartido (ej. `fixtures/`) — Responsable: Claude | Estado: pendiente | Depende de: 1.1. Verificación (restaurada de la revisión de Codex sobre el commit `4bf2c28`): acepta los ejemplos válidos de `session-catalog`/`caption-stream` y rechaza idioma/tipo/revisión/tiempos/tamaños inválidos con error, no truncamiento silencioso; las fixtures quedan disponibles para que Codex construya y pruebe la audiencia sin esperar el backend real (ver ajuste en `contrato-sesiones-subtitulos` tarea 3.1).

## 4. Pipeline de audio por sesión

- [ ] 4.1 Implementar el worker de sesión: lectura de audio por chunks, cola acotada, llamada a Whisper en thread pool — Responsable: Claude | Estado: bloqueada | Depende de: 2.3, 3.1. Verificación: procesa un audio de prueba completo y produce texto por chunk en orden.
- [ ] 4.2 Implementar la llamada a Ollama para traducir cada segmento transcripto, con invalidación cuando el original avanza de revisión — Responsable: Claude | Estado: bloqueada | Depende de: 4.1. Verificación: escenario "el original cambia mientras se traduce" de `specs/speech-pipeline` reproducido con un test.
- [ ] 4.3 Implementar el publicador de eventos (`session.snapshot`, `caption.upsert`, `session.status`, `session.error`, `session.gap`) con `seq`/`stream_id` y snapshot atómico al conectar, según `caption-stream` — Responsable: Claude | Estado: bloqueada | Depende de: 4.2, 3.3. Verificación (ampliada tras la revisión de Codex sobre el commit `4bf2c28`, que señaló que esta tarea había perdido criterios de las antiguas 2.1-2.4 del contrato): (a) cliente WebSocket de prueba recibe snapshot + eventos en orden, sin huecos de `seq`; (b) una revisión `final` repetida es idempotente y una revisión distinta posterior se rechaza (finales inmutables); (c) al publicar un `session.gap`, las entradas provisionales indicadas se retiran sin tocar finales; (d) un evento producido mientras se arma el snapshot no se pierde ni se duplica (snapshot + suscripción sin hueco, sin lock durante I/O); (e) al perder el estado del proceso se emite un `stream_id` nuevo y el cliente lo detecta como reinicio de generación.
- [ ] 4.4 Implementar cola acotada por cliente WebSocket y cierre `4008` ante espectador lento — Responsable: Claude | Estado: bloqueada | Depende de: 4.3. Verificación: simular un cliente que no lee y confirmar que se lo desconecta sin bloquear a los demás.

## 5. Aislamiento y sobrecarga

- [ ] 5.1 Verificar que dos sesiones en simultáneo no se degradan entre sí, y que la falla de una (archivo de audio corrupto/inexistente) no afecta a la otra — Responsable: Claude | Estado: bloqueada | Depende de: 4.4. Verificación: escenario de `specs/speech-pipeline` "Falla la fuente de audio de una sesión" reproducido.
- [ ] 5.2 Implementar la política de descarte/pausa cuando la inferencia no alcanza la velocidad del audio entrante, publicando `session.gap` — Responsable: Claude | Estado: bloqueada | Depende de: 4.4. Verificación: forzar sobrecarga (audio más rápido que la capacidad medida en 2.1) y confirmar que se emite el gap en vez de acumular retraso sin límite.

## 6. Medición end-to-end y documentación

- [ ] 6.1 Medir latencia p50/p95 real con dos sesiones activas, siguiendo el protocolo de `system-architecture` (10+ min, 100+ segmentos por sesión) — Responsable: Claude | Estado: bloqueada | Depende de: 5.1, 5.2. Verificación: informe con configuración, muestras, percentiles y pérdidas, igual que exige `specs/system-architecture`.
- [ ] 6.2 Escribir instrucciones en el README para levantar el backend y correr dos sesiones de prueba — Responsable: Claude | Estado: bloqueada | Depende de: 6.1. Verificación: alguien sin contexto puede seguir el README y ver el resultado.
- [ ] 6.3 Codex revisa el pipeline (código + resultados de 2.1/2.2/6.1) contra `speech-pipeline` y `caption-stream`, registra aceptación o ajustes — Responsable: Codex | Estado: bloqueada | Depende de: 6.1. Verificación: entrada de Codex en este archivo antes de integrar a `main` como definitivo.

## 7. Cierre del cambio

- [ ] 7.1 `openspec validate mvp-pipeline --strict` sin errores — Responsable: Claude | Estado: pendiente | Depende de: grupos 1-6. Verificación: salida del comando.
- [ ] 7.2 Archivar el cambio una vez validado y con la revisión de Codex registrada — Responsable: Claude | Estado: bloqueada | Depende de: 7.1, 6.3.
