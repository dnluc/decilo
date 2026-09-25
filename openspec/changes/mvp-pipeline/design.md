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

### Motor de STT: `faster-whisper`

**Por qué:** bindings maduros de Python a Whisper (CTranslate2), buen
rendimiento en CPU sin GPU dedicada, y evita escribir un subprocess wrapper
alrededor del binario de `whisper.cpp`. Modelo inicial: `small` o `medium`
(a definir con el benchmark de la tarea 2 de este cambio — `medium` da más
calidad con términos técnicos, `small` es más rápido; medir antes de fijar).

**Alternativa considerada:** `whisper.cpp` vía subprocess — más liviano en
dependencias pero más trabajo de integración (parsear su output, manejar
el proceso) sin ganancia clara dado que ninguno de los dos corre en Rust.

**Modo de operación:** Whisper no da streaming nativo palabra por palabra;
se lo alimenta por chunks de audio (definidos por VAD o por ventana fija) y
cada chunk produce texto que se publica directamente como `final` cuando el
chunk está completo — el contrato de `caption-stream` ya contempla
explícitamente este caso ("un proveedor sin parciales puede emitir un
resultado definitivo sin simular incrementalidad").

### Motor de traducción: modelo de texto vía Ollama (a confirmar cuál)

`gemma3n:e4b` (ya descargado) sirve para texto puro (confirmado
`"capabilities":["completion"]`). Falta medir su calidad de traducción
EN→ES con términos técnicos contra el protocolo de `system-architecture`
antes de fijarlo — es la tarea 2 de este cambio. Alternativa si la calidad
no alcanza: un modelo de Ollama más orientado a traducción, o `gemma3n:e2b`
si `e4b` es demasiado lento en CPU.

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

## Open Questions

- ¿`medium` o `small` de Whisper, y qué modelo de Ollama para traducción?
  Se resuelve con el benchmark de la tarea 2 de este cambio, con audio real
  ES/EN y referencias conocidas (protocolo ya definido en
  `system-architecture`). No cambia la arquitectura de este documento,
  solo qué modelo concreto se configura.
