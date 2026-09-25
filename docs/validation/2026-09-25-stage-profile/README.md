# Perfil del backend: espera, Whisper y Gemma

> Evidencia histórica: conserva modelos, parámetros y resultados de esta corrida.
> No describe por sí sola el perfil actual de PRs #21/#22; ver [índice de evidencia](../README.md).

Instrumentación interna optativa; sin cambios en HTTP/WebSocket ni frontend.
`run_file_session(..., observe=callback)` entrega muestras por bloque:

- `backlog`: desde disponibilidad del bloque hasta inicio de procesamiento.
- `asr`: transcripción, incluyendo despacho al thread y carga si no se precalienta.
- `translation`: llamada completa a Ollama, incluyendo HTTP.

Los errores también producen muestras marcadas. El total hasta publicación
continúa midiéndose con el mismo origen monotónico del audio. No es latencia
hasta el navegador. El transporte, captura y límites semánticos no se miden aquí.

## Reproducción

Con las demás pruebas de audio pausadas, ejecutar secuencialmente:

```sh
uv run scripts/measure_latency.py --sessions en --warmup --keep-all --output /tmp/single-en.json
uv run scripts/measure_latency.py --sessions es --warmup --keep-all --output /tmp/single-es.json
uv run scripts/measure_latency.py --sessions both --warmup --keep-all --beam-size 5 --output /tmp/both-beam5.json
uv run scripts/measure_latency.py --sessions both --warmup --keep-all --beam-size 1 --output /tmp/both-beam1.json
```

El calentamiento transcribe el primer bloque de cada idioma y traduce el EN,
fuera de la ventana medida. Se comparan los mismos WAV sintéticos de 41/45s,
Whisper small EN/medium ES, Gemma3n:e2b y ventanas de 5s. CPU de la notebook,
sin GPU; no hay aislamiento de CPU del escritorio. El usuario confirmó pausar
los ensayos; el servidor de Claude en 8000 mostraba ambas sesiones `ended`.
No se detuvieron procesos ajenos. Es un ensayo corto, no el protocolo de
10 minutos/100 segmentos; p95 de nueve resultados equivale al máximo.

El experimento `beam_size=1` reduce candidatos de decodificación en Whisper;
no cambia de modelo ni de cantidad de threads. WER normaliza minúsculas y
puntuación y compara contra `samples/*.txt`. Es diagnóstico del corpus
sintético, no una validación de calidad en charlas humanas ni de traducción.

También se protege la carga del caché de modelos con un lock: dos sesiones
frías del mismo idioma no deben construir dos modelos. Prueba concurrente
sin modelos confirma una única construcción; esto reduce duplicación de
memoria al arrancar, sin afirmar mejora del benchmark precalentado.


## Resultados sin descarte (base de comparación)

| Corrida | ASR EN p50 | Traducción p50 | ASR ES p50 | Atraso EN→ES p95 | Atraso ES p95 |
| --- | --- | --- | --- | --- | --- |
| EN sola | 1.34s | 2.82s | — | 12.45s | — |
| ES sola | — | — | 3.62s | — | 4.05s |
| Dos, beam 5 | 2.94s | 4.00s | 8.30s | 35.85s | 35.23s |
| Dos, beam 1 | 2.99s | 4.84s | 8.47s | 33.44s | 34.19s |

ASR ES tiene diez bloques (incluye silencio final), nueve subtítulos. EN tiene
nueve bloques. El último fragmento EN dura menos de un segundo y su ASR beam5
registró picos (5.45s sola, 10s concurrente); no debe esconderse ese outlier.
El p50 del atraso EN→ES empeoró de 11.95s a 15.41s con beam1 aunque el máximo
bajó un poco. No hay evidencia suficiente para cambiar el default beam5.

WER de transcript: beam5 EN 12/95 = 12.63%, ES 19/107 = 17.76%; beam1 EN
11/95 = 11.58%, ES 19/107 = 17.76%. La calidad técnica sigue pendiente, y WER
no evalúa agregados inventados por la traducción. No se reconfiguraron threads
ni modelos; el experimento previo de Claude no se repitió.

Conclusión limitada: la concurrencia de inferencia en CPU eleva los tiempos
de ambas etapas. ES ya necesita más tiempo que los 5s de audio entrantes por
bloque. En esta configuración solo EN llama a Ollama: serializar dos requests
de traducción de estas sesiones no explica el resultado (la otra sesión solo
transcribe). No se ha identificado a nivel de profiler nativo la causa exacta
(cache, ancho de banda, threads o competencia con Ollama).

## Corrección de sobrecarga

El worker de archivos ahora descarta un bloque si lleva más de 10s esperando
desde el fin de su audio, emite `session.gap` de tipo `overload` y elimina el
WAV temporal. Es análogo al presupuesto de dos bloques pendientes de captura.
No limita la duración de una inferencia ya iniciada ni promete 10s de latencia
final. El descarte evita seguir procesando todos los bloques viejos; **omite
contenido**, que se contabiliza en el informe y se avisa en la audiencia.
No es una mejora de velocidad o precisión del modelo.

`--keep-all` desactiva este descarte exclusivamente para diagnóstico. Para
probar el comportamiento nuevo:

```sh
uv run scripts/measure_latency.py --sessions both --warmup --output /tmp/bounded.json
```

El medidor escribe el JSON y devuelve error si hubo gaps/errores, incluso si
el descarte fue deliberado: no presenta una corrida con pérdidas como éxito
completo. Cada resultado incluye segundos omitidos cuando se usa el script
actual. Las primeras corridas precedieron a ese campo; conservar sus JSON
originales evita reinterpretar la configuración medida.


Resultado con descarte (`both-bounded.json`): 7 originales/traducciones EN y
7 originales ES. Máximo de espera previo a inferencia: 9.72s EN y 9.30s ES;
los bloques más atrasados se descartaron. p95 de salida: 17.57s traducción y
18.14s original ES. Se omitieron 5.877s EN y
10.165s ES (cinco gaps en total).
No comparar esos percentiles como mejora gratuita: cambió el conjunto de audio
procesado. La corrida devolvió exit 1 por las pérdidas, según lo previsto.

Verificación de código: 127 tests Python pasan, Ruff y OpenSpec correctos;
regresiones cubren tiempos por etapa y errores, descarte sin inferencia con gap
y eliminación temporal, y carga concurrente única del mismo modelo. Los locks
son por modelo, sin serializar por diseño la carga de modelos diferentes.

Próxima prioridad: evaluar un backend/modelo con menor costo total de inferencia
contra audio humano y referencias técnicas, o capacidad de cómputo adicional.
No se justifica cambiar solo beam_size con estos resultados. Segmentación y
contexto siguen pendientes para corregir palabras cortadas y fidelidad.
