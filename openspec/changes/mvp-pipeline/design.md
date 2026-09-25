# Design

## Context

Ver `proposal.md`. Backend en Python (confirmado en `arquitectura-base`).
El wire format que este pipeline debe producir es el de
`contrato-sesiones-subtitulos` (specs `session-catalog`, `caption-stream`)
— no se repite aquí, se referencia. Ollama corre local en
`localhost:11434`; `gemma3n:e4b` está descargado pero confirmado **sin**
soporte de audio (`arquitectura-base`, hallazgo empírico vía
`ollama show`/`/api/show`). No hay GPU dedicada (CPU-only).

## Goals / Non-Goals

**Goals:**
- Implementar el servidor que expone `GET /api/v1/sessions`,
  `GET /api/v1/sessions/{id}` y `WS /api/v1/sessions/{id}/events` según el
  contrato ya aceptado.
- Procesar al menos dos sesiones simultáneas desde archivos de audio de
  prueba, aisladas entre sí.
- Medir latencia/calidad reales contra el objetivo de 3s p95
  (`system-architecture`) antes de dar el motor por definitivo.

**Non-Goals:**
- Vista de audiencia (Codex).
- Captura desde micrófono en vivo o navegador (se puede sumar después del
  camino con archivo si sobra tiempo).
- Glosario/contexto, diarización, video, segmentación semántica — quedan
  en `VISION.md` como niveles posteriores.

## Decisions

### Motor de STT: `faster-whisper`, modelo según idioma de origen (confirmado, 2026-09-24)

**Por qué:** bindings maduros de Python a Whisper (CTranslate2), buen
rendimiento en CPU sin GPU dedicada, y evita escribir un subprocess wrapper
alrededor del binario de `whisper.cpp`.

**Resultado del benchmark** (audio sintético de `samples/`, CPU-only, ver
`tasks.md` grupo 2 para el detalle): con clips largos (~40s) ambos modelos
rinden bien (`small` 0.09-0.10x tiempo real, `medium` 0.22-0.25x), pero con
segmentos cortos (~4s, el caso real del pipeline) el overhead fijo por
llamada domina: `medium` solo tarda ~3s en transcribir un segmento de 4s.
Sumado a la traducción, un flujo EN→ES con `medium` da ~5.7s totales — casi
el doble del objetivo de 3s p95. Con `small`, el mismo segmento transcribe
en ~1.06s, dejando margen para la traducción.

**Modelo por flujo:**
- **Audio en inglés (alimenta traducción a español)**: `small`. Necesita
  dejar presupuesto para la traducción dentro del mismo límite de 3s p95
  (la spec mide la traducción desde el audio original, no desde que
  termina el STT). Calidad de `small` en inglés es muy buena en el
  benchmark (transcripción casi perfecta).
- **Audio en español (solo transcripción, sin traducción después)**:
  `medium`. Sin traducción que sumar, el presupuesto de 3s es solo para
  STT — hay margen de sobra, y `medium` mejora notablemente los términos
  técnicos en inglés mezclados en español (Kubernetes, Prometheus, Grafana,
  Slack salieron correctos con `medium`; con `small` salieron muy
  distorsionados: "cubernete", "prometeucigrafana").

Cargar ambos modelos en memoria (RAM de sobra en esta notebook, 32GB) y
elegir cuál usar según el `source_language` configurado de la sesión.

**Alternativa considerada:** `whisper.cpp` vía subprocess — más liviano en
dependencias pero más trabajo de integración (parsear su output, manejar
el proceso) sin ganancia clara dado que ninguno de los dos corre en Rust.

**Modo de operación:** Whisper no da streaming nativo palabra por palabra;
se lo alimenta por chunks de audio (definidos por VAD o por ventana fija) y
cada chunk produce texto que se publica directamente como `final` cuando el
chunk está completo — el contrato de `caption-stream` ya contempla
explícitamente este caso ("un proveedor sin parciales puede emitir un
resultado definitivo sin simular incrementalidad").

### Motor de traducción: `gemma3n:e2b` vía Ollama (confirmado, 2026-09-24)

**Resultado del benchmark** (5 repeticiones por modelo, segmentos cortos
reales, ver `tasks.md` grupo 2): `gemma3n:e4b` da p50=5.12s, max=5.97s
**solo de traducción** — ya excede el presupuesto total de 3s p95 (que
incluye STT) por sí solo. `gemma3n:e2b` da p50=2.81s, max=3.41s — todavía
ajustado, pero combinado con `small` de Whisper (~1.06s) el total ronda
2.4-2.5s, con margen. Calidad de `e2b` en la traducción es equivalente a
`e4b` en este benchmark: términos técnicos (Kubernetes, Prometheus,
Grafana, Slack, pull request, commit, autoscaling) se mantienen
correctamente, español natural. Se eligió `e2b` por el margen de latencia,
no por diferencia de calidad observada.

**Riesgo pendiente:** estas mediciones son con una sola sesión activa, sin
contención. Con dos sesiones simultáneas compitiendo por la misma CPU
(Whisper y Ollama son ambos CPU-bound), el p95 real puede empeorar — se
mide en la tarea 6.1 de este cambio antes de dar el objetivo de 3s por
confirmado bajo carga concurrente.

### Estructura del pipeline por sesión

Cada sesión es una tarea `asyncio` independiente con:
1. Lector de audio (archivo, dividido en chunks por VAD/ventana fija).
2. Cola acotada de chunks pendientes (aislamiento + control de sobrecarga).
3. Llamada a `faster-whisper` (posiblemente en un thread/process pool para
   no bloquear el loop de asyncio — `faster-whisper` es CPU-bound).
4. Llamada a Ollama (HTTP, `reqwest`-equivalente en Python: `httpx`) para
   traducir cada segmento transcripto.
5. Publicador de eventos: mantiene `seq`/`stream_id` de la sesión, arma los
   envelopes de `caption-stream` y los entrega a las conexiones WebSocket
   suscriptas, aplicando la cola acotada por cliente (64 mensajes / 2 MiB)
   y cerrando con `4008` a un cliente lento, tal como especifica el
   contrato.

Un registro de sesiones en memoria (`dict` protegido por lock/asyncio)
resuelve `GET /api/v1/sessions` y el catálogo; sin Redis/Kafka, según lo
ya decidido en `arquitectura-base`.

### Servidor HTTP/WebSocket: FastAPI

**Por qué:** soporte nativo de WebSocket, tipado con Pydantic (útil para
validar los envelopes del contrato antes de publicarlos — el contrato exige
rechazar datos inválidos, no truncarlos en silencio), y arranque rápido de
desarrollo, coherente con la decisión de priorizar velocidad de desarrollo
sobre Rust.

## Nota de entorno de desarrollo (NixOS, no aplica a otras distros)

En esta notebook (NixOS), las extensiones compiladas de wheels de PyPI
(`av`/PyAV que usa `faster-whisper`, y transitivamente `onnxruntime`/
`ctranslate2`) fallan al hacer `dlopen()` de `libz.so.1`/`libstdc++.so.6`
porque NixOS no tiene rutas FHS estándar. `nix-ld` (habilitado en
`/etc/nixos/configuration.nix`) no alcanza por sí solo porque el problema
es un `dlopen()` en tiempo de ejecución, no el exec de un binario — hace
falta exportar `LD_LIBRARY_PATH=/run/current-system/sw/share/nix-ld/lib`
antes de correr `uv run ...`. No es necesario en Linux/macOS estándar
(Ubuntu, etc.), así que no va en el README del proyecto — solo queda acá
para no volver a perder tiempo redescubriéndolo en esta máquina.

## Risks / Trade-offs

- [Riesgo] `faster-whisper` + Ollama en CPU-only pueden no cumplir 3s p95
  con dos sesiones simultáneas → medir en la tarea 2 de este cambio antes
  de comprometer el resto del pipeline; si no alcanza, evaluar modelo
  Whisper más chico o reducir sesiones concurrentes soportadas y
  documentarlo.
- [Riesgo] Procesar por chunks fijos (no streaming real) puede introducir
  latencia percibida mayor a la de un ASR streaming nativo → mitigar con
  chunks cortos (medir el tamaño óptimo) y aceptar que v1 no tiene
  parciales verdaderos, como permite el contrato.
- [Riesgo] `faster-whisper` es CPU-bound y puede bloquear el loop de
  asyncio si se llama directo → ejecutarlo en un thread/process pool
  (`asyncio.to_thread` o `ProcessPoolExecutor`).
- [Riesgo, confirmado con audio real 2026-09-24] Los chunks de ventana fija
  (5s) cortan palabras a la mitad en el borde de cada chunk, degradando la
  transcripción ("control plane" → "Troll plane", "Grafana" → "Prefana").
  El pipeline funciona de punta a punta (verificado con `scripts/smoke_e2e.py`
  contra Whisper/Ollama reales, eventos correctos según el contrato), pero
  la calidad en los bordes es peor que la medida en el spike (que usaba el
  audio completo, sin cortar). Mitigación no implementada por tiempo:
  VAD o corte en silencio en vez de ventana fija — ya está en `VISION.md`
  como diferencial futuro ("segmentación semántica"). Aceptado como
  limitación conocida de v1; documentar en el README de la demo.

## Open Questions

- ¿`medium` o `small` de Whisper, y qué modelo de Ollama para traducción?
  Se resuelve con el benchmark de la tarea 2 de este cambio, con audio real
  ES/EN y referencias conocidas (protocolo ya definido en
  `system-architecture`). No cambia la arquitectura de este documento,
  solo qué modelo concreto se configura.

## Correcciones de integración del PR #4 (Codex)

Por pedido del usuario, se corrigen los hallazgos de `review-codex-pr4.md`:

- Gateway emite JSON en frames de texto y monitoriza desconexión en paralelo.
  Cuenta snapshot, cola y mensaje en envío contra 64 mensajes/2 MiB. Retira al
  suscriptor una sola vez al exceder el presupuesto y cancela el envío antes
  de cerrar con 4008. Timeout de envío: 10s; cierre: hasta 1s. No se agregan
  sentinelas a una cola ilimitada.
- Snapshot serializado hasta 1 MiB: evicta segmentos completos, luego gaps,
  marcando historial truncado. Conserva como máximo 100 segmentos/100 gaps.
- Stream y catálogo comparten `SessionRecord`; las transiciones del worker
  pasan por las mismas reglas que la API, incluyendo terminalidad de `ended`.
- Publicar revisiones idénticas/obsoletas y resultados evictados es un no-op
  sin consumir `seq`. No se permite confirmar traducción de un original
  provisional, modificar un final o cambiar identidad/tiempos base del segmento.
  Gaps retiran también traducciones de originales descartados; los metadatos
  de revisión/retiro se liberan al evictar el segmento.
- Playwright prueba UI + gateway real sin modelos en puertos aislados. Esta
  prueba ahora corre en CI; el benchmark de audio de grupos 5/6 sigue pendiente.

## Segmentación acústica por pausas — 2026-09-25

Primera etapa solicitada por el usuario hacia unidades de sentido. No se
presenta como detector semántico: RMS de PCM16 mono en ventanas de 20ms,
umbral normalizado 0.01, mínimo 1s, pausa 400ms y máximo 6s. Configurable por
entorno; se valida mínimo >=0.5s y máximo <=15s. Se conserva modo fixed como
referencia. `PauseSegmenter` mantiene estado entre paquetes y limita su buffer;
no corta por fronteras de transporte ni une audio separado por un gap.

Se usa en archivos y captura. `boundary_reason` ya existente informa pause,
deadline o end_of_stream; nunca semantic. La misma razón se propaga a la
traducción. Los segmentos sin voz según esta heurística no invocan ASR; el
archivo respeta igualmente su tiempo de audio. Habla débil/ruido pueden engañar
el umbral: no es un VAD neuronal ni valida comprensión de frase.

Captura mantiene presupuesto de dos segmentos máximos en audio pendiente
(12s con defaults), además del activo y el buffer de segmentación. También
limita el número de entradas según mínimo/máximo. Así un paquete de 5s con
varias frases cortas no provoca pérdidas solo por superar dos entradas.
Al superar el presupuesto descarta el pendiente más antiguo y publica gap.
Al recibir discontinuidad vacía el fragmento previo antes de marcar el gap;
al detener procesa el último fragmento parcial antes de drenar traducciones.

Default en app: DECILO_SEGMENTATION=pause; fixed vuelve al modo anterior.
DECILO_MIN_SEGMENT_SECONDS=1, DECILO_PAUSE_SECONDS=.4,
DECILO_MAX_SEGMENT_SECONDS=6, DECILO_SILENCE_RMS=.01.

Handoff a Claude: el worklet actual envía 80000 muestras cada 5s. El backend
acepta paquetes menores sin cambiar el protocolo; emitir cada 100–200ms hará
visibles las pausas antes. Este cambio no toca frontend ni promete menor
latencia con el transporte actual. La detección semántica con texto parcial,
contexto entre fragmentos forzados y validación de calidad quedan pendientes.

## Proveedores de IA configurables — 2026-09-25

Codex: `DECILO_AI_PROVIDER=local|gemini`, default local. Overrides por etapa:
`DECILO_STT_PROVIDER`, `DECILO_TRANSLATION_PROVIDER`. Se carga .env al arrancar
sin sobrescribir entorno; validar proveedor/clave antes de iniciar sesiones.
Gemini usa generateContent por segmento WAV inline y traducción de texto,
modelo configurable DECILO_GEMINI_MODEL (default gemini-3.8-flash).
No cambia contrato público ni frontend. Whisper se importa al usar proveedor
local. No fallback ni retries automáticos; errores sanitizados sin contenido,
headers o credenciales. Timeout 30s, respuesta completa STOP requerida.
No acredita streaming Live, comprensión semántica ni menor latencia sostenida.
