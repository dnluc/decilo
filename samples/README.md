# Audios de prueba

Audio sintético generado con [`espeak-ng`](https://github.com/espeak-ng/espeak-ng)
(GPL-3.0) a partir de los textos en los `.txt` de esta carpeta, resampleado a
16kHz mono con `ffmpeg` (formato de entrada de Whisper). No hay grabaciones de
voz humana reales — se usó síntesis de voz precisamente para poder incluir el
audio en el repositorio sin restricciones de licencia ni de privacidad, y para
tener una transcripción de referencia exacta (el mismo texto que se le dio al
sintetizador) contra la cual comparar la salida de Whisper.

Contenido técnico deliberado (nombres propios, siglas, términos de
ingeniería) para poder evaluar cómo se comportan la transcripción y la
traducción con vocabulario técnico, como pide el criterio de "Calidad" del
jurado.

| Archivo | Idioma | Duración | Referencia |
| --- | --- | --- | --- |
| `en_tech_talk.wav` | Inglés | ~41s | `en_tech_talk.txt` |
| `es_tech_talk.wav` | Español | ~45s | `es_tech_talk.txt` |

## Regenerar

```sh
espeak-ng -v en-us -s 155 -f en_tech_talk.txt -w /tmp/en.wav
ffmpeg -y -i /tmp/en.wav -ar 16000 -ac 1 en_tech_talk.wav

espeak-ng -v es -s 155 -f es_tech_talk.txt -w /tmp/es.wav
ffmpeg -y -i /tmp/es.wav -ar 16000 -ac 1 es_tech_talk.wav
```

## Limitación conocida

Voz sintética: más artificial y con prosodia más plana que una charla real.
Sirve para medir el pipeline de forma reproducible (mismo audio, misma
referencia, siempre), pero antes de la demo final conviene probar también
con un fragmento de audio real de una charla de Nerdearla (permitido
explícitamente por las bases del desafío para el video demo).
