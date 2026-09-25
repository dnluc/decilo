# Decilo

**¿Qué dice?** — Transcripción y traducción en vivo, open source, para conferencias.

Construido para Nerdearla Vibeathon 2026. Documentación sincronizada con
`e4b9f90` (PRs #21 y #22), 25/09/2026. [English quick start](#english).

[Arquitectura con Mermaid](docs/ARQUITECTURA.md) · [Guía del frontend](frontend/README.md) ·
[Índice documental](docs/README.md) · [CI](docs/ci.md) · [Estado OpenSpec](openspec/README.md)

## Qué funciona

- Captura autorizada de **audio de una pestaña** del navegador, con YouTube embebido.
- Transcripción original en inglés o español; traducción **inglés → español**.
- Selector por captura: local (Whisper + Gemma/Ollama) o nube (Gemini).
- Originales provisionales que se revisan y confirman; historial reciente y reconexión.
- Detección inicial de idioma opcional, controles de lectura y cortes inferidos por oración.
- API de sesiones/archivos y distribución de una transcripción a varios espectadores.

ES→EN, otros idiomas, diarización, análisis de video, exportación completa y
control adaptativo de latencia siguen pendientes. El video se reproduce en el
navegador: no se envían frames a modelos ni se captura el micrófono.

## Caminos de procesamiento

| Entrada y proveedor | Reconocimiento | Traducción EN→ES |
| --- | --- | --- |
| Captura local | Parciales con Whisper `base`; finales con `small` EN/ES | `gemma3n:e2b` en Ollama |
| Captura Gemini, Live habilitado | `gemini-3.5-transcribe-live`, PCM continuo | `gemini-3.5-flash-lite` mediante `generateContent`, thinking `MINIMAL` |
| Captura Gemini con Live apagado o fallo al conectar | WAV por segmento con `generateContent` | Mismo adaptador Gemini por texto |
| Archivo WAV | Procesamiento por segmentos, proveedor configurable | Ollama o Gemini; no usa Live |

Estos nombres son los defaults del código, no una garantía de disponibilidad
para todas las cuentas. Las variables exportadas y el `.env` elegido pueden
sustituirlos. `language=auto` usa **Whisper local**, incluso con Gemini.
Elegir EN/ES explícitamente evita esa dependencia durante la captura en nube.

## Levantar la demo

Requisitos: Python 3.12+, `uv`, Node.js 22.12+ y Chrome con captura de audio de
pestaña. Para inferencia local: Ollama y sus modelos; Whisper corre en CPU
int8 y descarga sus pesos cuando se necesitan. Memoria y capacidad dependen
del perfil; no se promete una cantidad de sesiones por tamaño de RAM.

```sh
git clone https://github.com/dnluc/decilo.git
cd decilo
uv sync --group dev
npm --prefix frontend ci
```

Crear `.env` en la raíz, excluido de Git. Configuración local de ejemplo:

```dotenv
DECILO_AI_PROVIDER=local
DECILO_DEMO_SESSIONS=1
DECILO_DEMO_AUTOSTART=0
DECILO_PREWARM=0
DECILO_SEGMENTATION=pause
DECILO_PARTIALS=1
DECILO_TRANSLATION_QUEUE=1
DECILO_STREAM_TRANSLATION=0
```

Para local, tener Ollama activo y descargar la traducción:

```sh
ollama pull gemma3n:e2b
# Si Ollama no está corriendo como servicio, ejecutarlo en otra terminal:
ollama serve
```

Para habilitar nube, agregar a `.env` la clave de la cuenta y, si se desea,
seleccionar Gemini como default del backend:

```dotenv
DECILO_AI_PROVIDER=gemini
GEMINI_API_KEY=tu_clave_local
DECILO_GEMINI_LIVE=1
DECILO_GEMINI_LIVE_MODEL=gemini-3.5-transcribe-live
DECILO_GEMINI_MODEL=gemini-3.5-flash-lite
DECILO_GEMINI_THINKING=MINIMAL
```

La clave permanece en backend. No hace falta Ollama para una captura con
ambas etapas en Gemini e idioma explícito. Las dependencias Python del
proyecto siguen incluyendo faster-whisper.

Backend, desde la raíz del worktree que lo operará:

```sh
DECILO_ENV_FILE="$PWD/.env" DECILO_DEMO_SESSIONS=1 DECILO_DEMO_AUTOSTART=0 \
  uv run uvicorn decilo.app:app --host 127.0.0.1 --port 8000
```

Frontend, en otra terminal:

```sh
npm --prefix frontend run dev
```

Abrir **http://localhost:5173/**:

1. Pegar el enlace de YouTube y pulsar **Cargar**.
2. Elegir idioma del audio y **Procesamiento**. Si no hay preferencia guardada,
   el selector adopta el default comunicado por el backend cuando hay clave.
3. Pulsar **Compartir audio de pestaña**, seleccionar la pestaña que reproduce
   el video y habilitar **Compartir audio** en Chrome.
4. Dar Play. Si el video no permite embedding, abrirlo en otra pestaña y compartirla.
5. **Detener** libera la captura y deja terminar el trabajo pendiente.

Video usado durante el desarrollo: [API Gateway — Vlad Tomashpolskyi](https://www.youtube.com/watch?v=IW0unWVDnrI).
Los tiempos se cuentan desde el inicio de captura, no desde el minuto de YouTube.
El cambio de proveedor afecta la próxima captura. La UI muestra el original
como provisional si todavía falta la traducción elegida; texto visible temprano
no equivale necesariamente a español disponible.

## Parámetros y comportamiento

- `.env` se carga al iniciar; variables exportadas tienen prioridad. Usar
  `DECILO_ENV_FILE` explícito al trabajar con varias carpetas.
- `DECILO_STT_PROVIDER` y `DECILO_TRANSLATION_PROVIDER` permiten un backend
  híbrido cuando el cliente omite `provider`; el selector explícito de la UI
  elige ambas etapas para esa captura.
- `DECILO_GEMINI_LIVE=0` vuelve al camino Gemini por segmentos. El fallo inicial
  de Live publica un error y cae a ese camino **en nube**, no a Whisper.
  Una falla durante Live intenta reconectar; no hay replay durable de audio.
- `DECILO_GEMINI_THINKING=` omite `thinkingConfig` para un modelo que no lo admita.
  No hay reintentos automáticos en `generateContent`; Live sí reconecta.
- `DECILO_WHISPER_FAST=base` configura el modelo provisional. `DECILO_WHISPER_ES=small`
  configura el final ES; `medium` permite volver al perfil histórico. EN final usa `small`.
  Cada modelo se construye con `max(4, cpu_count // 2)` threads; no es una reserva
  exclusiva de CPU ni un límite global entre modelos.
- `DECILO_PARTIALS=0` apaga parciales y señal textual local en el camino por segmentos.
  No apaga los interims de Live. El corte local textual necesita timestamps de Whisper;
  no existe ese corte en el fallback `generateContent`.
- El segmentador usa mínimo 1 s, pausa 0,4 s, máximo 6 s y RMS 0,01, configurables
  con `DECILO_MIN_SEGMENT_SECONDS`, `DECILO_PAUSE_SECONDS`,
  `DECILO_MAX_SEGMENT_SECONDS` y `DECILO_SILENCE_RMS`.
- El corte textual busca una oración terminada seguida de otra en la hipótesis.
  Es una heurística, no comprensión semántica validada. Actualmente emite motivo
  `pause`; Live corta texto y aproxima tiempos, no alinea palabras a muestras exactas.
- `DECILO_SEGMENTATION=fixed`: archivos en ventanas de 5 s; captura por paquete
  recibido. No usarlo como si ambos fueran el mismo baseline temporal.
- `DECILO_TRANSLATION_QUEUE=1`: dos originales pendientes y un traductor activo.
  Se frena al productor si la cola se llena; la inferencia no se vuelve ilimitada.
- `DECILO_STREAM_TRANSLATION=1`: streaming NDJSON de Ollama con revisiones cada
  ~300 ms; Gemini traduce con una respuesta final. Es independiente de Gemini Live STT.
- `DECILO_PREWARM=1`: prepara modelos finales de Whisper y Ollama, con presupuesto
  de 90 s. No prepara el modelo rápido `base` ni una conexión Live.
  `DECILO_OLLAMA_KEEP_ALIVE` controla residencia de preparación/streaming (default `5m`).

Ver los [detalles y límites de cada camino](docs/ARQUITECTURA.md), incluida la
confirmación local de hipótesis que hace Live al finalizar/reconectar, que no
siempre representa una final recibida de Google ni dispara traducción.

## Sesiones, muestras y capacidad

Hay admisión nominal de dos trabajos activos; las detecciones automáticas aún
no reservan cupo hasta crear sesión. No es aislamiento estricto frente a muchas
conexiones simultáneas. El catálogo tiene límites de demo y el historial retiene
hasta 100 segmentos/100 gaps, con snapshots de hasta 1 MiB; no es archivo completo.

Para probar dos fuentes, abrir dos pestañas de Decilo, cargar videos y compartir
cada fuente en una captura distinta; elegir idioma explícito para evitar la
fase de detección. Para compartir solo la audiencia, abrir
`http://localhost:5173/?session=<id>` con un ID del catálogo
`GET /api/v1/sessions`. Otra audiencia no genera otra inferencia.

Los [WAV sintéticos incluidos](samples/README.md) tienen referencias de texto.
El backend conserva `GET .../{id}/audio`, `POST .../{id}/runs` y
`POST .../{id}/start`; la UI actual **no** tiene reproductor de WAV ni botón
«Iniciar prueba». Para benchmark desde la raíz:

```sh
uv run python scripts/measure_latency.py --sessions both --warmup \
  --keep-all --overlap-translation --segmentation pause --output /tmp/decilo-benchmark.json
```

Ese comando ejecuta modelos reales: no forma parte de CI. Los scripts requieren
variables exportadas y no cargan automáticamente el `.env` de la app. Miden
archivos/publicación backend, no Gemini Live, ASR provisional de captura ni render.
Los resultados históricos en [docs/validation](docs/validation/README.md) conservan
sus modelos y configuración; no acreditan el rendimiento de los PRs #21/#22.

Escalar exige medir recursos y dirigir ingreso/audiencia al dueño de cada
sesión. `uvicorn --workers N` por sí solo separa registros en memoria y no
resuelve ese routing. No hay scheduler distribuido ni persistencia. El objetivo
de 3 s p95 con dos sesiones y audio humano sigue sin aceptación sostenida.

## Verificación y diagnóstico

```sh
uv run python -m pytest tests -q -m 'not model'
uv run python -m ruff check src scripts tests
npm --prefix frontend test
npm --prefix frontend run build
```

Pruebas de navegador e integración en [frontend/README.md](frontend/README.md).
La CI excluye inferencia real; no despliega, ni ejecuta Sonar o CodeRabbit.

- Página: Vite en 5173. API: `/health` en 8000.
- `/health/ready` comprueba preparación local; `disabled` no prueba disponibilidad de modelos.
- Nube deshabilitada: revisar `/api/v1/providers` y el `.env` del backend activo.
- Selecciona pestaña pero no empieza: comprobar modo demo, handshake, readiness y cupos.
- Modo `auto` tarda: detección/carga local; elegir EN/ES explícitamente si ya se conoce.

La demo no trae autenticación ni cuotas por usuario: usar la escucha local del
comando anterior. Para producción hacen falta servidor de estáticos, proxy WS,
TLS y controles de acceso. El audio «local» se procesa en la máquina del backend,
que puede ser distinta de la del navegador.

## English

Decilo captures authorized browser-tab audio, transcribes English/Spanish and
translates **English into Spanish**. Choose local Whisper + Ollama/Gemma or
Gemini per capture. Cloud capture uses Gemini Live by default; file processing
and cloud fallback use per-segment `generateContent`. Automatic language detection
still uses local Whisper; select English/Spanish explicitly for cloud-only inference.

Requirements: Python 3.12+, uv, Node.js 22.12+, Chrome. From the repository root:

```sh
uv sync --group dev
npm --prefix frontend ci
```

Create a Git-ignored `.env` using one of the configurations above. For local
translation run Ollama with `gemma3n:e2b`; for cloud configure `GEMINI_API_KEY`
on the backend. Exported environment variables override `.env`.

```sh
DECILO_ENV_FILE="$PWD/.env" DECILO_DEMO_SESSIONS=1 DECILO_DEMO_AUTOSTART=0 \
  uv run uvicorn decilo.app:app --host 127.0.0.1 --port 8000
```

In another terminal run `npm --prefix frontend run dev`. Open
http://localhost:5173/, paste a YouTube link, choose language/provider, share
the video tab **with audio enabled**, then play it. Stop capture when finished.

Local provisional ASR uses `base`, final EN/ES uses `small`, and translation
uses `gemma3n:e2b`. Cloud defaults are `gemini-3.5-transcribe-live` for live ASR
and `gemini-3.5-flash-lite` for translation. These are configurable code defaults;
account availability and sustained performance are not guaranteed by the docs.

The demo has a nominal two-job limit, recent in-memory history and no durable
replay/authentication. Two audience tabs do not test two audio sources. Multiple
server workers need session-aware routing; adding workers alone is insufficient.
Spanish→English, diarization and visual AI are not implemented. Historical
benchmarks do not validate current sustained quality or the 3 s p95 target.

## Licencia / License

[Apache-2.0](LICENSE).
