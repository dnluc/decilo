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

- [x] 4.1 Implementar el worker de sesión: lectura de audio por chunks, cola acotada, llamada a Whisper en thread pool — Responsable: Claude | Estado: terminada | Depende de: 2.3, 3.1. Verificación (2026-09-25): `src/decilo/pipeline.py`, verificado con audio real de punta a punta (`scripts/smoke_e2e.py` contra el servidor real). Limitación conocida: chunks de ventana fija (5s) cortan palabras en el borde, degradando calidad respecto al spike (ver `design.md` § Risks). No implementado por tiempo: VAD/corte en silencio.
- [x] 4.2 Implementar la llamada a Ollama para traducir cada segmento transcripto, con invalidación cuando el original avanza de revisión — Responsable: Claude | Estado: terminada | Depende de: 4.1. Verificación (2026-09-25): `src/decilo/translate.py` + invalidación en `SessionStream.upsert_caption` (`tests/test_stream.py::test_translation_invalidated_when_original_advances`); traducciones reales EN→ES observadas en `scripts/smoke_e2e.py`.
- [x] 4.3 Implementar el publicador de eventos (`session.snapshot`, `caption.upsert`, `session.status`, `session.error`, `session.gap`) con `seq`/`stream_id` y snapshot atómico al conectar, según `caption-stream` — Responsable: Claude | Estado: terminada | Depende de: 4.2, 3.3. Verificación (2026-09-25): `src/decilo/stream.py` + `tests/test_stream.py`/`tests/test_gateway.py` cubren los 5 criterios de la revisión de Codex — (a) snapshot+eventos en orden sin huecos de `seq` (`test_snapshot_seq_zero_and_not_consumed`, `test_publish_reaches_connected_subscriber`), (b) finales inmutables (`test_final_is_immutable`), (c) retiro de provisionales con gap sin tocar finales (`test_gap_discards_provisional_but_not_final`), (d) snapshot atómico sin `await` de por medio en `_register_and_snapshot` (`test_serve_sends_snapshot_first`), (e) `stream_id` nuevo por proceso (implícito: cada `SessionStream` genera el suyo al construirse). Verificado también con eventos reales vía `scripts/smoke_e2e.py`.
- [x] 4.4 Implementar cola acotada por cliente WebSocket y cierre `4008` ante espectador lento — Responsable: Claude | Estado: terminada | Depende de: 4.3. Verificación (2026-09-25): `SessionGateway.publish_nowait` en `src/decilo/gateway.py`; `tests/test_gateway.py::test_slow_subscriber_gets_close_signal_without_affecting_others` confirma que un suscriptor que no se drena recibe la señal de cierre sin afectar a otro que sí lee.

## 5. Aislamiento y sobrecarga

- [ ] 5.1 Verificar que dos sesiones en simultáneo no se degradan entre sí, y que la falla de una (archivo de audio corrupto/inexistente) no afecta a la otra — Responsable: Codex | Estado: bloqueada | Depende de: 4.4. Verificación: escenario de `specs/speech-pipeline` "Falla la fuente de audio de una sesión" reproducido.
- [ ] 5.2 Implementar la política de descarte/pausa cuando la inferencia no alcanza la velocidad del audio entrante, publicando `session.gap` — Responsable: Codex | Estado: bloqueada | Depende de: 4.4. Verificación: forzar sobrecarga (audio más rápido que la capacidad medida en 2.1) y confirmar que se emite el gap en vez de acumular retraso sin límite.

## 6. Medición end-to-end y documentación

- [ ] 6.1 Medir latencia p50/p95 real con dos sesiones activas, siguiendo el protocolo de `system-architecture` (10+ min, 100+ segmentos por sesión) — Responsable: Codex | Estado: bloqueada | Depende de: 5.1, 5.2. Verificación: informe con configuración, muestras, percentiles y pérdidas, igual que exige `specs/system-architecture`.
- [ ] 6.2 Escribir instrucciones en el README para levantar el backend y correr dos sesiones de prueba — Responsable: Codex | Estado: bloqueada | Depende de: 6.1. Verificación: alguien sin contexto puede seguir el README y ver el resultado.
- [ ] 6.3 Claude revisa el pipeline (código + resultados de 2.1/2.2/6.1) contra `speech-pipeline` y `caption-stream`, registra aceptación o ajustes — Responsable: Claude | Estado: bloqueada | Depende de: 6.1. Verificación: entrada de Claude en este archivo antes de integrar a `main` como definitivo.

## 7. Cierre del cambio

- [ ] 7.1 `openspec validate mvp-pipeline --strict` sin errores — Responsable: Codex | Estado: pendiente | Depende de: grupos 1-6. Verificación: salida del comando.
- [ ] 7.2 Archivar el cambio una vez validado y con la revisión de Codex registrada — Responsable: Codex | Estado: bloqueada | Depende de: 7.1, 6.3.

## Correcciones del PR #4 — asignadas a Codex por el usuario

- [x] R4.1 Corregir frames de texto, límites de cola/envío y limpieza al desconectar — Responsable: Codex | Estado: terminada | Depende de: revisión PR #4. Verificación: tests con snapshot bloqueado, consumidor rápido, 1000 publicaciones, timeout de envío, desconexión durante silencio/finalización y cancelación.
- [x] R4.2 Acotar snapshots por bytes, unificar estado HTTP/stream y validar revisiones/relación con el original — Responsable: Codex | Estado: terminada | Depende de: revisión PR #4. Verificación: 109 tests Python correctos; Unicode y evicción de pares completos hasta 1 MiB; idempotencia sin consumir secuencia; rechazo sin mutación; descarte de resultados tardíos; HTTP y snapshot coinciden en `ended`.
- [x] R4.3 Agregar prueba de navegador contra gateway real a la CI y documentar ejecución — Responsable: Codex | Estado: terminada | Depende de: R4.1, R4.2. Verificación: Playwright de integración correcto con conexión real HTTP/WebSocket vía proxy, revisión original/traducción, reconexión y limpieza. Fuentes sintéticas, sin IA. Ruff, compilación y actionlint correctos.
- [x] R4.4 Claude revisa las correcciones de Codex en PR #4 antes de integrar — Responsable: Claude | Estado: terminada | Depende de: R4.1-R4.3. Verificación (2026-09-25): leí el diff completo de `gateway.py` y `stream.py`. Confirmé: `send_text` en vez de `send_bytes` (frames como texto real, no Blob — reproduje con un cliente websockets real, `isinstance(raw, str)` da `True`); cola con `maxsize` real y una sola señal de overflow por suscriptor (no un `None` por evento); snapshot acotado a 1 MiB evictando segmentos completos y después gaps; `SessionStream` y `SessionRegistry` comparten el mismo `SessionRecord` (HTTP y WS ya no pueden divergir); validación de revisión/relación original-traducción antes de mutar estado, con resultados obsoletos/duplicados devolviendo `None` sin consumir `seq`. 109 tests pasan, ruff limpio. Repetí la prueba de punta a punta con Whisper/Ollama reales sobre las dos sesiones de muestra: funciona correctamente, incluida la verificación a nivel de wire de que los frames llegan como texto. Acepto. Pendientes: grupos 5/6 (aislamiento explícito, medición p95 real).

## Prueba integrada posterior al PR #4 — Codex

Se ejecutó el recorrido con Whisper/Ollama reales y dos páginas de audiencia
sobre `801f3a4`. Evidencia en `docs/validation/2026-09-25-two-sessions/`:
9 originales EN + 9 traducciones ES y 9 originales ES; ambas sesiones `ended`,
cero errores JS/protocolo reportados y reconexión sin duplicados.

Los WAV son sintéticos. EN (~41s de audio) terminó a ~81s y ES (~45s) a ~68s
desde el inicio del lanzador; no hay fuente pautada en tiempo real ni reloj
de captura. Hay cortes de palabras y agregados de traducción documentados.
**No se marcan completas 5.1/5.2/6.1 ni se aprueba calidad/latencia.**
La siguiente validación requiere mejorar/evaluar segmentación y traducción,
probar audio humano y medir la capacidad bajo una fuente a velocidad real.

## Cambio de responsables — 2026-09-25

Por pedido del usuario, Codex asume implementación y medición pendientes del
backend; Claude realiza la revisión cruzada. Se conserva la autoría histórica
de las tareas terminadas. Próximo objetivo: inicio a pedido y audio a ritmo
real para la demo audible, mediante un contrato compartido en OpenSpec.

## Continuación del handoff PR #5 — Codex, 2026-09-25

El usuario indicó que Claude dejó de trabajar y pidió continuar desde su PR.
Se conserva el pacing propuesto y se corrige la limpieza al cancelar durante
la espera. Se reemplaza el medidor basado en hora de conexión por uno con
origen monotónico compartido con cada worker; mide hasta publicación del
backend, no hasta navegador. 112 tests Python y Ruff correctos.

Corrida real y limitaciones en `docs/validation/2026-09-25-paced/`: nueve
segmentos por salida, p95 34.44s EN, 37.92s traducción ES y 31.20s original ES.
Había otro servidor de Claude activo; no es comparación aislada. Grupos 5/6
siguen pendientes. No se afirma cumplimiento de latencia ni revisión cruzada
de las correcciones nuevas de Codex. La propuesta `audio-playback` publicada
por Claude es la base de continuación del reproductor; aún necesita definir
inicio a pedido del worker para la demo con audio y generación concurrentes.

## Perfil de rendimiento por etapas — Codex

Trabajo solicitado tras devolver el frontend a Claude. Instrumentación optativa
interna en el worker, sin modificar contratos de audiencia. El benchmark permite
una/dos sesiones, warmup explícito y comparar beam_size 5/1; reporta backlog,
ASR y traducción por segmento, incluidos errores. Se agrega diagnóstico WER
contra referencias sintéticas. Caché de modelos protegido frente a doble carga
concurrente del mismo modelo. Evidencia en docs/validation/2026-09-25-stage-profile/.
No se marcan completas las tareas de medición larga, calidad o aislamiento.

Resultados publicados: dos sesiones precalentadas elevan ASR ES p50 de 3.62s
a 8.30s y traducción EN→ES de 2.82s a 4.00s. Beam1 no mejora de forma convincente;
se conserva beam5. El worker de archivos ahora descarta bloques con atraso
mayor a 10s, con gap y contabilidad de audio omitido (benchmark --keep-all para
comparación). Corrida con pérdidas: p95 17.57s traducción, 18.14s ES; no cumple
objetivo. 127 tests correctos, Ruff/OpenSpec válidos. Sin cambios frontend ni
contrato de eventos. Pendiente revisión cruzada; no declarar benchmark largo
ni calidad aprobados.

## Experimento de cola en memoria — Codex

Autorizado por el usuario: separar ASR y traducción, sin cambiar frontend ni
contratos. Cola de dos textos pendientes + una traducción activa por sesión;
backpressure si se llena, drenaje antes de ended y cancelación del consumidor
si falla/cancela el productor. Opt-in por parámetro interno/flag del benchmark;
no cambia el default ni la captura de pestaña mientras se evalúa. Comparación
sin descartes (--keep-all) y con warmup, mismos WAV/modelos. Evidencia en
`docs/validation/2026-09-25-translation-queue/`.

Resultado: sin pérdidas en ninguna corrida, máximo EN→ES de 33.51s a 19.60s
(~42% menos); mediana de 11.93s a 10.86s. ES no mejora (p50 18.83s→21.30s,
p95 27.73s→28.40s). 130 tests pasan; Ruff/OpenSpec correctos. Se conserva la
cola como experimento opt-in para archivos, no se activa automáticamente en
captura ni se declara cumplido el objetivo. Pendiente revisión de Claude.

## Integración autorizada por el usuario — 2026-09-25

Por instrucción explícita «integrá todos los PR», Codex integró en main los
PR #5, #6, #8, #9 y #10, en orden de dependencias. Commit de integración final:
7495473. Se preservan las mejoras de frontend de Claude incluidas en #8.
Los checks de cada head estaban correctos antes de integrar. Esta autorización
no se registra como revisión cruzada de Claude ni como aprobación de calidad
o latencia. La cola de traducción sigue experimental y opt-in para archivos.
El PR #7 ya estaba cerrado sin merge; no se reabrió ni se duplicó su propuesta.

## Activación para pruebas del frontend — Codex

El usuario pidió encender el experimento mientras prueba desde el frontend de
Claude. Se agrega DECILO_TRANSLATION_QUEUE=1 en el backend: activa la cola en
archivos y captura de pestaña. Default desactivado si falta la variable.
La captura drena audio y traducciones con un único presupuesto de 90s después
de Stop, antes de ended/cierre. La autorización de pruebas no acredita calidad
ni mejoras de rendimiento en captura real. El frontend mantiene sus contratos.
Backend local de Codex en puerto 8000, consumido por Vite de Claude (5173).

## Cortes por pausas y límite máximo — Codex

- [x] P1 Segmentador incremental PCM16 por energía/pausas, mínimo/máximo y motivos de corte; conservar muestras y tiempos — Responsable: Codex. Tests de invariancia por transporte, máximo exacto, silencio y parámetros inválidos.
- [x] P2 Integrar archivos y captura con presupuesto de audio pendiente, gaps, flush al detener y boundary_reason existente — Responsable: Codex. 143 tests Python y 4 pruebas de integración con navegador correctos. Rama: `codex/pause-segmentation`, basada en PR #11. Segmentador por pausas activado por defecto en app; modo fixed reproducible.
- ~~P3 Adaptar tamaño de paquetes~~ — Movida a `backend-latencia-incremental` tarea 4.1; responsable Claude.
- ~~P4 Calidad, demora y detector semántico~~ — Movida a `backend-latencia-incremental` tareas 1.2, 3.2 y 5.1–5.2; responsable Codex.
- [ ] P5 Revisión cruzada — Responsable: Claude.

Evidencia de límites sobre ambos WAV sin inferencia en
`docs/validation/2026-09-25-pause-segmentation/boundaries.json`. Los tests usan
voz/silencio sintéticos, no prueban que una pausa complete una idea. No se
modificó el frontend de Claude; el último fragmento se drena al detener captura.
