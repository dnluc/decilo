# Tasks

## 1. Contrato y baseline
- [x] 1.1 Revisar diseño/handoff y registrar objeciones concretas — Responsable: Claude | Estado: terminada | Depende de: ninguna. Ver «Objeciones de Claude» al final.
- [ ] 1.2 Inventario y baseline reproducible: reutilizar mediciones previas, incorporar audio humano, pérdidas y dos sesiones — Responsable: Codex | Estado: pendiente | Depende de: ninguna
- [ ] 1.3 Extender métricas por etapa y correlación temporal; definir corpus anotado y límites de recursos — Responsable: Codex | Estado: en curso | Depende de: 1.2

## 2. Recursos y traducción progresiva
- [x] 2.1 Cliente HTTP con lifespan, preparación de modelos y cierre/cancelación probados — Responsable: Codex | Estado: terminada | Depende de: instrumentación parcial de 1.3
- [x] 2.2 Consumir NDJSON y emitir revisiones de traducción sobre original final; tratar truncamiento/errores — Responsable: Codex | Estado: terminada (implementación opt-in; revisión 1.1 pendiente) | Depende de: 2.1
- [x] 2.3 Tests de revisiones tardías, stop, timeout, snapshot y aislamiento de sesiones — Responsable: Codex | Estado: terminada (etapa B: originales finales) | Depende de: 2.2

## 3. Reconocimiento y segmentación

Reasignado a Claude por el usuario el 2026-09-24 («tomalo vos todo esto
completo»), junto con el pedido de transcribir palabra por palabra y corregir
al cerrar la frase, sin mostrar nunca «traduciendo» ni estados de espera. El
«no tocar backend» del handoff queda superado por esa instrucción.

- [x] 3.1 ASR incremental del segmento abierto — Responsable: Claude | Estado: terminada (enfoque re-transcripción, sin ventana deslizante) | Verificación: `src/decilo/partials.py` re-transcribe el audio acumulado del segmento abierto (beam 1, anticipo barato) y publica revisiones provisionales del MISMO segmento que la pasada final (beam completo) corrige y confirma. No hay deduplicación de ventanas porque no hay ventanas solapadas: cada provisional es el segmento entero hasta ese punto. 5 tests en `tests/test_partials.py` + smoke con modelos reales: provisional «how Kubernetes markets» (rev=1) corregida por la final «how Kubernetes orchestrates containers at scale» (rev=2). Si la pasada final da texto vacío (VAD), las provisionales huérfanas se retiran con un gap `discard_captions`.
- [x] 3.2 Detector textual — Responsable: Claude | Estado: terminada (2026-09-25, pedido directo del usuario: oradores rápidos apilaban oraciones). Sin presupuesto/deadline propio: el corte textual solo dispara ante un límite INTERNO (una oración terminó y la siguiente ya empezó en la misma hipótesis), en el timestamp del segmento de Whisper (local, `split_open` del segmentador) o por posición del texto acumulado (Gemini Live, con prefijo confirmado para no republicar tras la final oficial). Un punto al final del texto a medias nunca corta: Whisper puntúa cualquier hipótesis (falso corte reproducido y testeado). Pausa/deadline acústicos siguen como respaldo. Tests en `test_partials.py`, `test_segmentation.py`, `test_gemini_live.py`; smoke real de ambos caminos.
- [x] 3.3 Scheduler: una revisión pendiente por unidad abierta — Responsable: Claude | Estado: terminada | Verificación: `PartialTranscriber` mantiene UNA transcripción provisional en vuelo y solo la instantánea más nueva pendiente (`test_latest_snapshot_wins_while_worker_is_busy`); una provisional que termina después del cierre se descarta sin publicarse (`test_stale_provisional_after_close_is_dropped`); la revisión de la pasada final se reserva al cerrar, antes de encolar, para que nunca choque con una provisional tardía. Kill switch: `DECILO_PARTIALS=0`.

### Alcance agregado por el usuario (2026-09-24)
- [x] A.1 Autodetección del idioma de entrada (`language=auto`) — Responsable: Claude | Estado: terminada. La sesión necesita idioma (contrato v1) y el idioma necesita audio: fase `detecting` que recibe paquetes antes de crear la sesión y los conserva completos, junta ≥2.5s con voz (tope 12s, cierre 4408 si no llega voz), detecta con argmax restringido a en/es sobre `all_language_probs` y recién entonces crea la sesión y envía `ready`. Verificación: 4 tests en `tests/test_language_detection.py` + smoke real (sample en español → sesión `es`).
- [x] A.3 Nube en streaming (pedido del usuario 2026-09-25: «reducir mucho más la latencia… busca el mejor modelo en la nube de gemini») — Responsable: Claude | Estado: terminada. Con proveedor gemini la captura reenvía el PCM del navegador directo a `gemini-3.5-transcribe-live` (Live API): interims → provisionales, finales → final + traducción con `gemini-3.5-flash-lite` + thinking MINIMAL (0.64s medidos vs 1.54s del 3.1). Medido E2E: primera palabra ~1.3s, final ~0.8s tras la pausa, traducción ~0.8s tras el final. Fallback automático al camino por segmento; `DECILO_GEMINI_LIVE=0` lo desactiva. 9 tests en `tests/test_gemini_live.py`.
- [x] A.2 Estado provisional/confirmado solo por color en la UI (sin «Traduciendo…» ni carteles de espera), rediseño con dock inferior — Responsable: Claude | Estado: terminada. Verificación: `frontend/tests/browser/ui.spec.js` (24 pruebas, incluye que el body no contenga «Traduciendo»), 3 de integración con backend real.

## 4. Frontend (handoff a Claude)
- [x] 4.1 Paquetes objetivo 100ms y flush antes de stop, offsets y backpressure; sin duplicar reproducción — Responsable: Claude | Estado: terminada | Depende de: ninguna. Verificación: `frontend/tests/browser/worklet.spec.js` (3 pruebas, contexto offline a 16kHz contra el worklet real) comprueba paquetes de 4+3200 bytes, offsets contiguos sin huecos ni solapamiento, muestras intactas (no silencio) y flush del fragmento parcial al `stop` cubriendo el audio de punta a punta. El formato (offset uint32 LE + PCM16 LE) no cambió; el audio capturado se sigue enrutando a una ganancia en 0, así que no se reproduce de nuevo.
- [x] 4.2 Validar/ajustar UI provisional/final contra v1 y casos de revisiones/invalidation/snapshot — Responsable: Claude | Estado: terminada | Depende de: 1.1. Verificación: 4 pruebas nuevas en `frontend/tests/browser/ui.spec.js` con fixtures deterministas (sin modelos): tres revisiones del mismo segmento siguen siendo una sola intervención y no se anexan como frases; una traducción tardía de una revisión reemplazada no vuelve a mostrarse; un `final` repetido es idempotente y no duplica; al reconectar por salto de `seq` el snapshot reemplaza el estado sin duplicar. No hizo falta cambiar la UI: el manejo por `(segment_id, kind, language)` + `revision` ya cumplía.
- [ ] 4.3 Medición de recepción/render y prueba navegador sin comparar relojes incompatibles — Responsable: Claude | Estado: pendiente | Depende de: 1.3, 4.1, 4.2
- [ ] 4.4 Revisar PR frontend preservando cambios ajenos — Responsable: Codex | Estado: pendiente | Depende de: 4.3

## 5. Evaluación y cierre
- [ ] 5.1 Experimentos A/B de parámetros uno por vez, luego combinación con dos sesiones durante 15–20min — Responsable: Codex | Estado: pendiente | Depende de: 3.3, 4.4
- [ ] 5.2 Publicar tabla de latencia, calidad, backlog, pérdidas, recursos, configuración y rollback; conservar experimental lo no validado — Responsable: Codex | Estado: pendiente | Depende de: 5.1
- [ ] 5.3 Revisión cruzada backend y reproducción de evidencia — Responsable: Claude | Estado: pendiente | Depende de: 5.2
- [ ] 5.4 Consolidar specs y archivar al cumplir aceptación — Responsable: Codex | Estado: pendiente | Depende de: 5.3

Spec creada por Codex el 2026-09-25. Solo documentación en este checkpoint.
No ejecutar modelos concurrentemente con pruebas de Claude sin coordinación.
G4 de proveedores nube (PR #15) sigue separado; no duplica este benchmark local.

## Avance Codex — primera entrega

Rama `codex/streaming-translation`. Streaming real sobre original final,
cliente reutilizable y preparación opcional implementados sin cambiar defaults.
La revisión cruzada sigue pendiente; publicar PR no equivale a aprobar el diseño.
Métricas 1.3: separadas primera publicación/final y duraciones Ollama; WER solo
usa originales finales. Soporte de WAV/referencias externos para baseline humano.
1.2 y corpus/render/recursos de 1.3 siguen pendientes; se reutiliza inventario
previo y se adjunta smoke real, sin declararlo benchmark sostenido.
2.3: tests de truncamiento, cancelación, parcial/snapshot y cierre completados;
pruebas de sesión aislada y original evictado completadas. Revisiones de originales
provisionales pertenecen a etapa C, no las implementa esta entrega.
Validación actual: 161 tests Python, Ruff, 3 tests navegador, smoke real Ollama.
Evidencia: docs/validation/2026-09-25-streaming-translation/.
El PR #15 de Gemini sigue separado: al integrar ambos, su dispatch debe preceder
al camino Ollama y un proveedor sin streaming debe emitir únicamente final.

## Objeciones de Claude (1.1) — 2026-09-25

De acuerdo con el diseño en general: conservar el protocolo v1, medir antes de
declarar mejoras y separar frío de caliente me parecen las decisiones correctas.
Cuatro objeciones concretas, ninguna bloqueante:

**1. Los paquetes descartados por congestión del navegador se reportan como
`source_disconnect`, y eso es engañoso.** En `capture.py`, cuando el offset de
un paquete salta, se registra un gap con razón `source_disconnect` ("se perdió
la fuente de audio"). Pero el salto también ocurre si el worklet tuvo que
descartar audio por congestión local, con la fuente intacta. Al medir pérdidas
(tareas 1.2/5.2) esto va a atribuir mal la causa. Propongo una razón distinta
para pérdida en el transporte, o al menos no contar ambos casos juntos en la
evidencia. Del lado del frontend ya lo dejo visible en la UI y cuantificado en
segundos, pero el backend no puede distinguirlos con la información actual.

**2. "No restar `performance.now()` de timestamps monotónicos de Python" es
correcto, pero falta decir contra qué correlacionar.** El punto 5 del handoff y
el escenario «Relojes distintos» prohíben la resta pero no fijan la referencia.
Propongo usar el `offset` de muestras del paquete como reloj común: ya viaja en
el protocolo, es exacto, y el navegador sabe qué offset envió y cuándo. Sin una
referencia acordada, cada lado va a inventar la suya y las mediciones no van a
ser comparables. Lo necesito definido antes de 4.3.

**3. El presupuesto del detector semántico debería tener un tope absoluto
visible en la UI.** El escenario «Habla continua sin cierre» publica con
`deadline` al vencer el presupuesto, pero si el presupuesto se reinicia por
contenido nuevo, un orador sin pausas puede no cerrar nunca una unidad. La UI
hoy muestra el provisional, así que el síntoma sería texto que cambia sin
confirmarse nunca. Pido que el tope sea explícito y acotado, no solo relativo
al «primer contenido pendiente».

**4. Riesgo de UX, no de contrato: revisiones frecuentes sobre texto
provisional.** El ASR incremental va a revisar el mismo segmento más seguido.
El manejo por `(segment_id, kind, language)` + `revision` ya lo soporta y no
pienso tocarlo, pero leer se vuelve molesto si el texto cambia varias veces por
segundo. El marcador de ritmo del frontend (`captions.js`) actualiza en el
lugar sin reiniciar el tiempo de lectura, así que absorbe parte; si aun así
resulta inestable lo resuelvo del lado de la presentación, no pidiendo cambios
al backend.

Nada de esto requiere cambiar el protocolo v1.
