# Medición con archivo a ritmo real — PR #5

Codex continuó el handoff de Claude. El worker espera hasta el fin de cada
chunk antes de inferir; `started_at` permite compartir el reloj monotónico
con el medidor. La espera está dentro del `try/finally` para eliminar el
archivo temporal si se cancela antes de inferir.

El script original restaba la hora de conexión, que no es el origen del
audio. Se reemplazó por una medición desde el final del intervalo de audio
hasta la publicación del backend. No incluye WebSocket ni renderizado.

Reproducir desde el repo, con Whisper y Ollama instalados:

```sh
uv run scripts/measure_latency.py --output /tmp/decilo-latency.json
```

El script inicia sus propios dos workers y no necesita un servidor HTTP.
No debe ejecutarse junto con otras inferencias para una comparación controlada.
El JSON contiene todos los eventos y tiempos desde el origen de cada sesión.

## Resultado exploratorio

Mismos WAV sintéticos, Whisper small EN / medium ES, Gemma3n:e2b, CPU local.
Incluye carga inicial de modelos. Durante esta corrida existía además un
servidor `scripts.dev_audio_stub:app` de Claude en el puerto 8000, compartiendo
CPU y Ollama. Se preservó ese proceso ajeno. Por eso NO es un benchmark aislado
ni demuestra la capacidad exclusiva de dos sesiones. No se atribuye la causa
a threads, al executor o a Ollama sin un experimento controlado.

| Salida | n | p50 (s) | p95 (s) | máximo (s) |
| --- | --- | --- | --- | --- |
| Original EN | 9 | 12.35 | 34.44 | 34.44 |
| Traducción ES | 9 | 17.18 | 37.92 | 37.92 |
| Original ES | 9 | 18.82 | 31.20 | 31.20 |

p95 usa nearest-rank; con nueve muestras equivale al máximo. Ambas sesiones
terminaron sin `session.error` ni `session.gap`. El retraso se acumula; la
espera de ritmo real no resuelve la sobrecarga. No se acreditan calidad,
latencia en navegador, aislamiento de fallos ni el protocolo de 10 minutos y
100 segmentos por sesión. Evidencia completa: `events.json`.

## Validación y continuación

112 tests Python pasan, incluyendo disponibilidad temporal del audio,
procesamiento sin espera extra cuando va atrasado y limpieza al cancelar
la espera. Ruff correcto.

Pendientes: prueba controlada sin otras inferencias, política de sobrecarga,
segmentación que no corte palabras y fidelidad de traducción. El contrato
`audio-playback` de Claude permite escuchar el archivo y resaltar el historial;
aún no define iniciar el worker desde el botón de reproducción. Ese inicio
compartido debe especificarse para demostrar generación mientras se escucha,
sin presentar una reproducción posterior como latencia en vivo.
