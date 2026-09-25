# Experimento: cola de traducción en memoria

Compara el worker secuencial con un productor ASR y un consumidor de traducción
por sesión. Capacidad: dos textos pendientes y una traducción activa. Una cola
llena aplica backpressure a ASR, sin crear tareas por segmento ni acumular texto
sin límite. El original se publica antes de encolar; la sesión termina después
de drenar traducciones. Ante cancelación/falla del productor, se cancela y espera
al consumidor. Se mantienen revisiones e invalidación del stream existente.

Opt-in: `run_file_session(..., overlap_translation=True)` o el flag del benchmark.
El camino secuencial continúa siendo el predeterminado; la captura de pestaña
no cambia en este experimento. No hay cambios en el contrato ni en el frontend.

## Comparación

Ejecutar secuencialmente, con las otras pruebas de audio pausadas:

```sh
uv run scripts/measure_latency.py --sessions both --warmup --keep-all --output /tmp/serial.json
uv run scripts/measure_latency.py --sessions both --warmup --keep-all --overlap-translation --output /tmp/overlap.json
```

Mismos WAV sintéticos EN/ES, small/medium, beam5 y Gemma3n:e2b, CPU local.
Warmup de ambos modelos y una traducción fuera de medición. `--keep-all` desactiva
el descarte por atraso para evitar confundir menor latencia con pérdida de audio.
Se conservan los límites de la cola de texto aun en ese modo.

`translation_queue` mide desde intento de enqueue hasta inicio de traducción;
incluye `translation_backpressure` (espera para entrar si está llena), por lo
que no se deben sumar ambas métricas. `translation` mide inferencia/HTTP.
La espera del productor puede hacer crecer el atraso de audio; una cola acotada
no equivale a garantizar una latencia final.

Los JSON conservan todos los eventos y métricas. p95 sobre nueve subtítulos
es el máximo; esto no valida el protocolo largo de 10 min/100 segmentos ni
calidad con audio humano. WER evalúa transcripción del corpus sintético, no la
fidelidad de Gemma. No se aísla el proceso del escritorio ni se instrumenta
internamente Whisper/Ollama.


## Resultado de esta corrida

| Salida | Secuencial p50 / p95 | Con cola p50 / p95 |
| --- | --- | --- |
| Original EN | 7.70s / 29.74s | 3.06s / 11.92s |
| Traducción ES | 11.93s / 33.51s | 10.86s / 19.60s |
| Original ES | 18.83s / 27.73s | 21.30s / 28.40s |

Ambas corridas terminaron con 9 originales EN, 9 traducciones ES y 9 originales
ES, sin errores/gaps ni audio descartado. La cola redujo el máximo observado de
traducción aproximadamente 42%, pero la mediana mejoró solo 9%. ES no mejoró:
la mediana empeoró unos 2.47s y el máximo 0.67s. Una única pareja de corridas no
separa bien ruido térmico/carga del escritorio de un cambio pequeño en ES.

Los tiempos de inferencia no bajaron: traducción p50 subió de 4.24s a 5.99s.
La mejora EN viene de quitar la dependencia entre ASR y traducción, pese a la
competencia por CPU. Espera del texto antes de traducir: p50 2.09s, máximo 5.22s;
no se llenó la cola hasta bloquear significativamente al productor en este corpus.
El test de sobrecarga sí fuerza y comprueba ese límite.

Se conserva el default secuencial: el experimento demuestra un beneficio para
EN, pero no resuelve capacidad de dos sesiones ni cumple 3s p95. Antes de adoptar
para captura de pestaña, repetir con audio humano más largo y validar equidad
entre sesiones, fallos y calidad de traducción. El callback/flag permite continuar
la evaluación sin modificar el contrato que consume Claude.

Validación: 130 tests Python, Ruff y OpenSpec correctos. Nuevas regresiones:
Whisper avanza mientras traducción está bloqueada; solo dos trabajos pendientes;
drenaje antes de ended y limpieza del consumidor al cancelar.

WER de transcripción igual en ambas corridas: EN 12/95 (12.63%), ES 19/107
(17.76%). Esto no prueba que la traducción conserve significado ni que los
errores de términos técnicos estén resueltos.
