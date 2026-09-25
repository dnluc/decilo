# Tasks

## Correcciones de la revisión del PR #3 — Codex

El usuario pidió a Codex aplicar las cuatro correcciones sobre la base
`96dc8fc` de Claude. Se publican en el mismo PR `claude/mvp-pipeline`.

- [x] R.1 Validar límite de texto en bytes UTF-8, intervalos de gaps completos/ordenados, enteros estrictos en rango seguro de JavaScript e idiomas de traducción únicos — Responsable: Codex | Estado: terminada | Depende de: revisión PR #3. Verificación: 64 casos pytest correctos; Ruff y compilación correctos. Regeneración de los 10 fixtures sin diferencias; catálogo y secuencia hasta `seq=6` consumidos correctamente por el reductor real de audiencia. No se ejecutó inferencia.
- [x] R.2 Revisar las correcciones de Codex antes de integrar PR #3 — Responsable: Claude | Estado: terminada | Depende de: R.1. Verificación (2026-09-24): revisé el diff completo de `models.py`; reproduje los 4 casos reportados por Codex (texto multibyte >8192 bytes, gap con intervalo invertido, gap con un solo lado nulo, `revision=True`) más `seq` fuera del rango seguro de JS e idiomas de traducción repetidos — los 6 se rechazan correctamente. `uv run pytest` (64 passed), `ruff check` sin errores, fixtures regeneradas sin diferencias. Acepto. El resto del pipeline conserva los responsables y pendientes de abajo.

## CI mínima — alcance agregado por el usuario (2026-09-24)

- [x] CI.1 Preparar workflow de push/PR con Python 3.12, compilación, Ruff y pytest — Responsable: Codex | Estado: terminada | Depende de: ninguna. Rama: `codex/ci-minima`. Validación: actionlint 1.7.12 sin errores, herramientas instaladas y `pip check` correcto; detección ensayada con/sin `src/` y ausencia de tests comprobada como fallo. No se ejecutaron tests de aplicación: todavía no hay backend en esta revisión. Convenciones y límites en `docs/ci.md`.
- [x] CI.2 Revisar el workflow y sus convenciones antes de integrar el PR — Responsable: Claude | Estado: terminada | Depende de: CI.1. Verificación (2026-09-24): revisé `.github/workflows/ci.yml` y `docs/ci.md` completos; aprobado sin ajustes (comentario en PR #1, mergeado a `main`, rama `codex/ci-minima` eliminada).
- [ ] CI.3 Confirmar ejecución de los tests reales del backend en Actions — Responsable: Codex | Estado: bloqueada | Depende de: 1.1 y tests del pipeline. La etapa inicial sin `src/` solo informa que el backend está pendiente; no acredita compilación ni pruebas de aplicación.

## 1. Base del proyecto Python

- [x] 1.1 Estructurar el proyecto Python (`pyproject.toml` con `uv`, carpeta `src/decilo/`) e instalar `faster-whisper`, `httpx`, `fastapi`, `uvicorn`, `pydantic` (+ `pytest`, `pytest-asyncio`, `ruff` como dev) — Responsable: Claude | Estado: terminada | Depende de: ninguna. Verificación (2026-09-24): `uv run python -c "import decilo.app"` sin error; `uv run uvicorn decilo.app:app` sirve `/health` con 200 OK.
- [x] 1.2 Conseguir/generar 2 audios de prueba cortos (ES y EN) con contenido técnico conocido, incluidos en el repo con su licencia de uso indicada — Responsable: Claude | Estado: terminada | Depende de: ninguna. Verificación (2026-09-24): `samples/en_tech_talk.wav` (~41s) y `samples/es_tech_talk.wav` (~45s), sintéticos vía `espeak-ng` (GPL-3.0, sin restricción de privacidad/copyright), 16kHz mono, con su texto de referencia exacto en el `.txt` al lado y licencia/limitaciones documentadas en `samples/README.md`.

## 2. Spike de calidad y latencia (resuelve arquitectura-base 3.2/3.3)

- [x] 2.1 Medir `faster-whisper` (small y medium) transcribiendo los audios de prueba — Responsable: Claude | Estado: terminada | Depende de: 1.1, 1.2. Verificación (2026-09-24, `scripts/bench_whisper.py`):

  | Modelo | Audio (~40-45s) | Tiempo | Factor | Calidad EN | Calidad ES |
  | --- | --- | --- | --- | --- | --- |
  | small | en_tech_talk (40.9s) | 3.56s | 0.09x | Casi perfecta (1 error: Grafana→Brafana) | — |
  | small | es_tech_talk (45.2s) | 4.33s | 0.10x | — | Varios errores en préstamos técnicos (Kubernetes→"cubernete", Prometheus/Grafana→"prometeucigrafana") |
  | medium | en_tech_talk (40.9s) | 9.11s | 0.22x | Casi perfecta (1 error: Grafana→Prefana) | — |
  | medium | es_tech_talk (45.2s) | 11.31s | 0.25x | — | Mucho mejor: Kubernetes, Prometheus y Grafana, Slack correctos |

  Con **segmentos cortos (~4s, caso real)**: `medium` tarda ~2.97s solo en
  STT (overhead fijo por llamada domina en clips cortos); `small` tarda
  ~1.06s. Ver decisión de modelo-por-idioma en `design.md`.

- [x] 2.2 Medir traducción EN→ES con `gemma3n:e4b` y `gemma3n:e2b` vía Ollama — Responsable: Claude | Estado: terminada | Depende de: 2.1. Verificación (2026-09-24, 5 repeticiones por modelo sobre segmentos cortos reales):

  | Modelo | p50 | max | avg | Calidad |
  | --- | --- | --- | --- | --- |
  | gemma3n:e4b | 5.12s | 5.97s | 5.30s | Buena, términos técnicos correctos |
  | gemma3n:e2b | 2.81s | 3.41s | 2.70s | Igual de buena que e4b en este benchmark |

  `e4b` solo de traducción ya excede el presupuesto total de 3s p95 (que
  incluye STT). `e2b` dentro de rango con margen ajustado.

- [x] 2.3 Fijar modelo de Whisper y de Ollama para traducción; actualizar `design.md` — Responsable: Claude | Estado: terminada | Depende de: 2.1, 2.2. Verificación (2026-09-24): `design.md` actualizado — **Whisper `small` para audio en inglés** (deja presupuesto a la traducción), **Whisper `medium` para audio en español** (sin traducción que sumar, más margen, mejor con préstamos técnicos), **`gemma3n:e2b`** para la traducción EN→ES. Medición real de punta a punta (audio→STT→traducción) sobre un segmento de ~4s: **small+e2b = ~2.4-2.5s total**, dentro del objetivo de 3s p95. Riesgo pendiente: medido con una sola sesión, sin contención — falta validar bajo 2 sesiones simultáneas (tarea 6.1).

## 3. Registro de sesiones y catálogo

- [x] 3.1 Implementar el registro de sesiones en memoria y `GET /api/v1/sessions`, `GET /api/v1/sessions/{id}` según `specs/session-catalog` — Responsable: Claude | Estado: terminada | Depende de: 1.1. Verificación (2026-09-24): `src/decilo/sessions.py` + endpoints en `app.py`; tests con 0, 1 y 2 sesiones (independientes, sin filtrar datos entre sí) y 404 para sesión inexistente.
- [x] 3.2 Implementar las transiciones de estado (`starting`, `live`, `degraded`, `error`, `ended`) según las reglas de `session-catalog` — Responsable: Claude | Estado: terminada | Depende de: 3.1. Verificación (2026-09-24): 14 casos parametrizados cubriendo las transiciones permitidas y rechazadas (incluye `error→error` y `ended→*` correctamente rechazados, no listados como permitidos en la spec).
- [x] 3.3 Modelar los envelopes del contrato (Pydantic) con validación estricta y publicar fixtures de catálogo/snapshot/eventos en un path compartido (ej. `fixtures/`) — Responsable: Claude | Estado: terminada | Depende de: 1.1. Verificación (2026-09-24): `src/decilo/models.py` con validación estricta (idioma, tiempos, revisión, traducción sin `source_revision`, etc.) probada con 5 casos inválidos, todos rechazados. 10 fixtures generadas y validadas en `fixtures/` (ver `fixtures/README.md`), incluyendo una secuencia completa (`event_sequence.json`) para probar un reductor de eventos de punta a punta. Codex puede construir y probar la audiencia contra esto sin esperar el backend real (ver ajuste en `contrato-sesiones-subtitulos` tarea 3.1).

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
