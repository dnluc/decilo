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
