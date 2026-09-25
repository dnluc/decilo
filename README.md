# Decilo

**¿Qué dice?** — Transcripción y traducción en vivo, open source, para conferencias.

Proyecto construido para la [Nerdearla Vibeathon 2026](https://nerdearla.com).

---

## Español

### ¿Qué es esto?

Decilo es una solución open source de transcripción simultánea a escala, pensada para conferencias como Nerdearla. Toma audio en vivo de un escenario y produce subtítulos en tiempo real: transcripción en el idioma original y traducción al español (y, opcionalmente, del español al inglés).

Está pensado para reemplazar el esquema actual de herramientas comerciales de transcripción/traducción, que es caro, depende de operación manual y no escala a múltiples sesiones en simultáneo.

### Objetivo del MVP

- Recibir audio en vivo de al menos una fuente (micrófono, archivo o stream).
- Generar transcripción en tiempo real del idioma original (español o inglés).
- Generar traducción en tiempo real de inglés a español.
- Mostrar los subtítulos en una vista para la audiencia (web, overlay, terminal).
- Procesar al menos dos sesiones en simultáneo.

### Modelo y requisitos

Corre 100% local usando [Gemma 3n](https://ai.google.dev/gemma) a través de [Ollama](https://ollama.com), sin depender de servicios en la nube.

- **Ollama** instalado y corriendo (`ollama serve`, expuesto en `localhost:11434`).
- Modelo `gemma3n:e4b` descargado (`ollama pull gemma3n:e4b`).
- Recomendado: 16GB+ de RAM. No requiere GPU dedicada (corre sobre CPU).

### Cómo levantarlo

```bash
# 1. Instalar Ollama (ver https://ollama.com/download)
# 2. Bajar el modelo
ollama pull gemma3n:e4b

# 3. Clonar este repo
git clone https://github.com/dnluc/decilo
cd decilo

# (instrucciones de ejecución del proyecto: en construcción durante la Vibeathon)
```

### Escalar a más sesiones

Cada sesión corre como un proceso/worker independiente que consume audio y llama a la misma instancia de Ollama. Para escalar a 5-10 escenarios en paralelo, se puede repartir la carga entre múltiples instancias de Ollama (una por máquina/GPU disponible) detrás de un balanceador simple.

### Licencia

[Apache 2.0](./LICENSE)

---

## English

### What is this?

Decilo is an open source, scalable live-transcription solution built for conferences like Nerdearla. It takes live audio from a stage and produces real-time captions: transcription in the original language and translation into Spanish (and optionally Spanish-to-English).

It's meant to replace the current setup of commercial transcription/translation tools, which is expensive, depends on manual operation, and doesn't scale to multiple simultaneous sessions.

### MVP goals

- Receive live audio from at least one source (microphone, file, or stream).
- Generate real-time transcription in the original language (Spanish or English).
- Generate real-time English-to-Spanish translation.
- Display captions in an audience-facing view (web, overlay, terminal).
- Handle at least two sessions running simultaneously.

### Model and requirements

Runs 100% locally using [Gemma 3n](https://ai.google.dev/gemma) via [Ollama](https://ollama.com), no cloud dependency.

- **Ollama** installed and running (`ollama serve`, exposed on `localhost:11434`).
- `gemma3n:e4b` model pulled (`ollama pull gemma3n:e4b`).
- Recommended: 16GB+ RAM. No dedicated GPU required (runs on CPU).

### Getting started

```bash
# 1. Install Ollama (see https://ollama.com/download)
# 2. Pull the model
ollama pull gemma3n:e4b

# 3. Clone this repo
git clone https://github.com/dnluc/decilo
cd decilo

# (run instructions: work in progress during the Vibeathon)
```

### Scaling to more sessions

Each session runs as an independent process/worker consuming audio and calling the same Ollama instance. To scale to 5-10 concurrent stages, load can be split across multiple Ollama instances (one per available machine/GPU) behind a simple load balancer.

### License

[Apache 2.0](./LICENSE)

### Prueba audible en el navegador

Con Whisper y Ollama configurados, iniciá el backend sin procesar los WAV
hasta que pulses Play:

```sh
DECILO_DEMO_SESSIONS=1 DECILO_DEMO_AUTOSTART=0 uv run uvicorn decilo.app:app --host 127.0.0.1 --port 8000
```

En otra terminal:

```sh
npm --prefix frontend install
npm --prefix frontend run dev
```

Abrí la URL de Vite, elegí una charla y pulsá **Iniciar prueba**. Se crea una
sesión nueva, comienza el audio y se solicita la transcripción/traducción real.
Si el navegador bloquea la reproducción automática, pulsá Play en el audio.
Los WAV incluidos son sintéticos. El audio no se retrasa para ocultar la demora
de inferencia; los subtítulos se muestran al llegar. El borde verde indica el
intervalo correspondiente al tiempo de reproducción, si su texto ya existe.

Pausar o buscar mueve solo el audio local; el procesamiento continúa. Los
controles del audio también permiten escuchar el historial de una sesión
terminada. **Iniciar prueba** vuelve a generar texto en otra sesión, sin
reutilizar subtítulos anteriores. Máximo dos workers simultáneos y veinte
sesiones con audio por proceso; reiniciar el servidor limpia las pruebas.

Este modo está pensado para uso local. El inicio de inferencia se solicita
cuando el navegador empieza a reproducir, con un desfase de red/scheduling;
no constituye una medición exacta de latencia hasta pantalla. La inferencia
actual puede quedar muy por detrás del audio en CPU.

### YouTube y audio de pestaña (experimental)

El reproductor incluye el video proporcionado para la prueba:
[API Gateway — Vlad Tomashpolskyi, Nerdearla](https://www.youtube.com/watch?v=IW0unWVDnrI).
Usá el mismo backend en modo demo local y el frontend de la sección anterior.

1. Pulsá **Cargar video**. Si YouTube no permite embeberlo, usá el enlace para
   abrirlo en otra pestaña.
2. Seleccioná el idioma original y pulsá **Compartir audio de pestaña**.
3. En Chrome elegí la pestaña donde se reproduce el video y marcá **Compartir
   audio**. Compartir una ventana o pantalla puede no ofrecer audio.
4. Dale Play al video; los subtítulos aparecen en una sesión nueva debajo.
5. **Detener captura** libera las pistas y deja terminar lo pendiente.

Se envía solo PCM mono de audio al backend local. El permiso de pantalla es
parte de la API del navegador; no se envían frames de video, no se usa micrófono
ni se descargan subtítulos de YouTube. La compatibilidad depende del navegador
([getDisplayMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia)).
Los timestamps parten del inicio de captura, no del minuto de YouTube.

Bloques de hasta 5s, dos bloques pendientes por sesión: si la inferencia no
alcanza, se descarta el pendiente más antiguo y aparece un aviso de interrupción.
Esto limita la cola, pero no garantiza baja latencia ni calidad. Máximo dos
workers simultáneos entre archivos/captura, captura de hasta una hora y veinte
sesiones en el catálogo para admitir nuevas capturas. El servidor cierra tras
15s sin recibir audio; al detener espera hasta 90s para drenar el trabajo.

Para acotar también los frames en la capa WebSocket del servidor, agregá a
uvicorn `--ws-max-size 160004 --ws-max-queue 4`. El formato se valida además en
la aplicación. Este ingreso es experimental y requiere revisión; no tiene
autenticación para desplegarlo públicamente.

Para probar la cola experimental también en captura de pestaña, iniciá el
backend con `DECILO_TRANSLATION_QUEUE=1` además de las variables anteriores.
El log de arranque muestra `Translation queue: True`. No requiere cambios del
frontend. Al detener, se espera a las traducciones pendientes antes de finalizar,
con un presupuesto total de 90s para drenar audio y texto. Sigue siendo un
experimento: benefició al inglés en el corpus corto, pero no mejoró español.

### Cortes por pausas (primera etapa hacia unidades de sentido)

El backend usa `DECILO_SEGMENTATION=pause` por defecto: busca una pausa de
400ms después de al menos 1s y fuerza corte a los 6s si el hablante continúa.
No entiende todavía si terminó una idea: es un detector acústico por energía.
Conserva timestamps y distingue `pause`, `deadline` y `end_of_stream` en el campo
`boundary_reason` existente. Silencios detectados no se envían a Whisper.

Configuración opcional: `DECILO_MIN_SEGMENT_SECONDS`, `DECILO_PAUSE_SECONDS`,
`DECILO_MAX_SEGMENT_SECONDS`, `DECILO_SILENCE_RMS` (defaults 1, .4, 6 y .01).
Voz débil puede confundirse con silencio; ajustar el umbral requiere evaluar el
audio real. `DECILO_SEGMENTATION=fixed` permite volver a los cortes anteriores.
El benchmark compara con `--segmentation fixed` y `--segmentation pause`.

La captura aún depende de cuándo recibe audio: si el frontend envía paquetes
cada 5s, no se puede emitir antes de recibirlos. Se admiten paquetes menores
sin cambiar la API. En modo pause, el presupuesto de audio pendiente es dos
veces la duración máxima de segmento (12s por defecto), con número de entradas
acotado; una sobrecarga se sigue notificando con gaps.

### Transcripción palabra por palabra (provisional → corrección final)

Mientras una frase sigue abierta, el backend re-transcribe su audio acumulado
(beam 1, anticipo barato) y publica revisiones **provisionales** del mismo
segmento; al cerrar la frase por pausa, la pasada final (beam completo) la
corrige y la **confirma**. La UI comunica el estado solo con color: texto
apagado mientras es provisional, pleno al confirmarse — nunca aparece
«traduciendo» ni ningún cartel de espera. Hay a lo sumo una transcripción
provisional en vuelo y solo se conserva la instantánea más reciente; una
provisional que termina después del cierre se descarta sin publicarse.

Activo por defecto en la captura con segmentación por pausas.
`DECILO_PARTIALS=0` lo apaga (útil en máquinas donde la CPU no acompaña:
las provisionales compiten con la pasada final y con Ollama).

### Autodetección del idioma de entrada

La captura acepta `language=auto` (opción por defecto en la UI). El backend
responde `{"type": "detecting"}`, junta ~2.5s de audio con voz (tope 12s; si
no llega voz cierra con código 4408), detecta el idioma con Whisper
restringido a en/es y recién entonces crea la sesión y envía `ready`. Ningún
paquete se pierde: el audio de la fase de detección también se transcribe.

### Traducción progresiva y preparación (experimental)

`DECILO_STREAM_TRANSLATION=1` consume el flujo real de Ollama y publica texto
provisional; confirma al recibir fin correcto de generación. Se publica el primer
contenido y se agrupan actualizaciones posteriores cada 300ms como mínimo, sin
retrasar el final. Timeout absoluto 30s, salida máxima 8192 bytes. Desconexión o
límite de generación deja el parcial sin confirmar y publica un error.
Default desactivado: quitar la variable restaura traducción solo final.

`DECILO_PREWARM=1` prepara Whisper EN/ES y Ollama en segundo plano antes de
permitir iniciar audio. `GET /health/ready` devuelve 503 mientras prepara o si
falla; catálogo y health siguen accesibles. Readiness desactivada por defecto;
`disabled` no acredita modelos calientes. Preparación limitada a 90s. La carga
síncrona de Whisper en un thread no puede abortarse forzosamente al vencer el
plazo; se mantiene la entrada cerrada y no se relanza en bucle.
Esta preparación carga pesos: no sustituye el warmup representativo del benchmark.
`DECILO_OLLAMA_KEEP_ALIVE` controla residencia de peticiones streaming/preparación
(default `5m`; `-1` solicita residencia indefinida a Ollama).

El cliente HTTP se comparte durante el lifespan del backend; los scripts deben
usar `ollama_lifespan()` para reutilizarlo a través de varias llamadas. Las dos
etapas son opt-in y no reinician ni modifican la instancia Ollama del sistema.

Medición: exportar `DECILO_STREAM_TRANSLATION=1` para comparar. El JSON separa
`first_summary` (primera aparición) de `summary` (final), sin contar revisiones
como nuevos subtítulos. `first_from_start`/`final_from_start` usan inicio del
intervalo fuente; métricas anteriores usan su fin. Mide publicación backend,
no renderizado ni utilidad semántica. Registra etapas internas Ollama (duraciones
convertidas de ns) y subtítulos sin confirmar. Para WAV humanos propios:

```sh
DECILO_STREAM_TRANSLATION=1 uv run python scripts/measure_latency.py \
  --sessions both --warmup --keep-all --overlap-translation --segmentation pause \
  --audio-en /ruta/charla-en.wav --reference-en /ruta/charla-en.txt \
  --audio-es /ruta/charla-es.wav --reference-es /ruta/charla-es.txt \
  --timeout 1500 --output /tmp/decilo-streaming.json
```

Los WAV deben ser PCM16 mono; referencia opcional (sin referencia no se calcula
WER). No ejecutar en paralelo con otra prueba de modelos; comparar el mismo
comando con el flag de streaming desactivado. WER no evalúa traducción.

### Proveedor local o Gemini

Desde la interfaz hay un selector **Procesamiento** con dos opciones: «En esta
máquina» (Whisper y Gemma locales, el audio no sale del equipo) y «En la nube
(Gemini)». La elección se fija al abrir cada captura y viaja en esa sesión, así
que dos capturas simultáneas pueden usar proveedores distintos y cambiar el
selector no altera una sesión ya en curso.

Si el servidor no tiene `GEMINI_API_KEY`, la opción de nube aparece
deshabilitada en vez de fallar al conectar. El navegador nunca recibe la clave:
`GET /api/v1/providers` solo informa si hay credenciales configuradas.


El backend carga `.env` de la raíz al iniciar; las variables exportadas tienen
prioridad. `DECILO_ENV_FILE` permite indicar otro archivo (útil para tests
aislados). El archivo `.env` está excluido de Git. Default: `local` (Whisper/Ollama).
Para usar nube, configurar y reiniciar el backend:

```dotenv
DECILO_AI_PROVIDER=gemini
GEMINI_API_KEY=tu_clave
DECILO_GEMINI_MODEL=gemini-3.5-flash-lite
```

Para mezclar: `DECILO_STT_PROVIDER=local` y
`DECILO_TRANSLATION_PROVIDER=gemini`; estos valores prevalecen sobre
`DECILO_AI_PROVIDER`. Aplican a archivos y capturas que omiten `provider`.
La elección explícita del navegador prevalece sobre ambos para esa captura:
`provider=local` o `provider=gemini` selecciona las dos etapas. Un fallo al
preparar modelos locales no bloquea una captura elegida en nube.
La clave queda solamente en el backend. Gemini recibe audio si se usa
para STT y texto si se usa para traducción; aplican cuotas/costos del proyecto.
No hay fallback automático ni reintentos ocultos. Timeout por petición: 30s.

### Nube en streaming: Gemini Live (el camino rápido)

Con proveedor `gemini`, la captura no espera pausas ni sube WAVs: cada paquete
de 100ms del navegador se reenvía tal cual (ya es PCM16 mono a 16kHz, el
formato exacto de la [Live API](https://ai.google.dev/gemini-api/docs/live-api/live-transcribe))
a `gemini-3.5-transcribe-live`, que devuelve la transcripción palabra por
palabra mientras se habla. Los resultados intermedios se publican como
revisiones provisionales y el resultado de cada frase como final, que dispara
la traducción con `gemini-3.5-flash-lite` y `thinkingLevel: MINIMAL` (medido:
~0.6s por frase contra ~1.5s del modelo anterior con thinking por defecto).

Latencias medidas de punta a punta en esta máquina: primera palabra visible
~1.3s después de empezar a hablar, revisiones cada ~0.5s, final ~0.8s después
de la pausa y traducción ~0.8s después del final. Antes (por segmento, CPU
local compitiendo): el texto aparecía recién al cerrar la frase y la
traducción llegaba 13–20s tarde.

- `DECILO_GEMINI_LIVE=0` desactiva el streaming y vuelve al envío por
  segmento con `generateContent`; si Google no responde al conectar, la
  captura cae sola a ese camino (se avisa con un error retryable).
- `DECILO_GEMINI_LIVE_MODEL` cambia el modelo de streaming.
- La sesión de Google se renueva sola antes de su límite de 10 minutos, sin
  perder la numeración de segmentos.
- La credencial viaja solo en el header, nunca en la URL.

Con proveedor local, o como fallback, se usa
[generateContent](https://ai.google.dev/api/generate-content) por segmento.
Se preservan el protocolo de subtítulos, las colas y los cortes por pausa.
Los scripts de medición requieren variables exportadas (la carga automática de
`.env` ocurre en el arranque de la app).
