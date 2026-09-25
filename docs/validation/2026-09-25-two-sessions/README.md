# Prueba de dos sesiones en navegador con modelos reales

> Evidencia histórica: conserva modelos, parámetros y resultados de esta corrida.
> No describe por sí sola el perfil actual de PRs #21/#22; ver [índice de evidencia](../README.md).

Codex verificó el commit `801f3a4` después del merge del PR #4. Resultado:
**el recorrido archivo → Whisper → Gemma → WebSocket → navegador funciona;
la calidad y la capacidad de tiempo real aún no están acreditadas.**

## Alcance y entorno

- Dos WAV simultáneos del repositorio, de voz **sintética**: inglés (40,877s)
  con traducción y español (45,165s) sin traducción. No son charlas humanas.
- Whisper `small` para EN y `medium` para ES, CPU/int8; Ollama `gemma3n:e2b`.
  Chunks fijos de 5s, tal como está implementado el worker.
- Intel Core i7-1360P, 16 CPUs lógicas, 30 GiB de RAM reportados por el SO.
- faster-whisper 1.2.1, CTranslate2 4.8.2, FastAPI 0.141.1,
  Pydantic 2.13.5, httpx 0.28.1, Uvicorn 0.53.0.
- Backend separado en 18765; proxy Vite en 5175; dos páginas de Chrome.
  No se modificaron ni detuvieron los servidores de Claude en 8000/8001.
  Esos procesos permanecían residentes; no fue un benchmark aislado de recursos.
- Cachés de modelos ya disponibles; carga de Whisper incluida en la ejecución.

Audios identificados por SHA-256:

```text
c06a4bc3ef544b29786c35f3ee02cd87168c52539d78ab133568092c5389dc96  en_tech_talk.wav
3c245f288e1db2c7d5eaed551e5893ae877fe2d41b73991f60b2e774405f697e  es_tech_talk.wav
```

## Evidencia funcional

[events.json](./events.json) conserva frames observados por el navegador,
texto visible, catálogo final y resultado de reconexión. `elapsed_ms` mide
reloj de pared desde el inicio del lanzador de la prueba (incluye arranque
local), **no latencia desde captura de audio**.

| Salida | Subtítulos | Primero observado | Último observado |
| --- | ---: | ---: | ---: |
| Original EN | 9 | 5,029s | 79,149s |
| Traducción ES de EN | 9 | 17,218s | 81,383s |
| Original ES | 9 | 8,080s | 62,179s |

- Sesión EN finalizada a 81,386s; ES a 68,146s desde el inicio del lanzador.
- Ambos estados HTTP terminaron en `ended` y se reflejaron en la vista.
- Cero errores JavaScript y cero eventos `session.error` en esta ejecución.
- Cambiar de sesión y volver a EN recuperó los 9 segmentos, sin duplicación;
  cambiar idioma permitió leer el original. Los IDs de las sesiones se
  mantuvieron separados.
- Servidores propios de la prueba detenidos al terminar.

## Revisión manual de calidad

No se calcula WER ni se afirma precisión general con dos audios sintéticos.
Ejemplos de fallos observados, comparados con los `.txt` de referencia:

- EN: `Kubernetes` quedó cortado como `Kubern...`; `control plane` se convirtió
  en `Troll plane`; `Grafana` en `Prefana`. La última palabra `questions` se
  repitió como un segmento adicional.
- ES: `nodos` apareció como `nomos`; `mergear` como `emergir`; `cada commit`
  como `Kavakommi`. Hay pérdida de continuidad al separar palabras por ventana.
- Traducción: la frase sobre latencia/error rates y autoescalado agregó
  «son un desafío constante» y «para mantener la disponibilidad y rendimiento»,
  contenido ausente del original. `Troll plane` también se propagó con un
  significado incorrecto.

Por estos casos, no dar la calidad por aprobada para la demo. Próximo trabajo
para el backend: evaluar límites de segmento en silencio/solapamiento y
reconciliación, y acotar/evaluar la traducción para evitar agregados. Mantener
la evidencia de calidad al comparar cambios, sin atribuir mejoras antes de medir.

## Límite de la medición

El worker procesa archivos tan rápido como puede: **no reproduce una fuente
pautada en tiempo real ni registra el reloj de captura**. Aquí EN (~41s de
contenido) termina después de ~81s de pared y ES (~45s) después de ~68s,
incluyendo arranque y competencia de recursos. Es evidencia de que esta
configuración necesita mejoras; no alcanza para calcular p50/p95 de subtítulos.

Siguen pendientes grupos 5/6 de `mvp-pipeline`: fallo de una fuente aislado,
política de sobrecarga y medición a velocidad real, con 10+ minutos y 100+
segmentos por sesión. También falta audio humano representativo para calidad.
Esta prueba no cierra esas tareas ni certifica la meta de 3s p95.

## Repetir el recorrido manual

Con dependencias y modelos ya instalados, desde la raíz:

```sh
DECILO_DEMO_SESSIONS=1 uv run uvicorn decilo.app:app --host 127.0.0.1 --port 18765
```

En otra terminal:

```sh
cd frontend
DECILO_BACKEND_URL=http://127.0.0.1:18765 npm run dev -- --port 5175
```

Abrir dos páginas en `http://127.0.0.1:5175/`, elegir una charla distinta en
cada una y verificar texto/estado. No usar `?demo=1`: ese modo simula texto.
Las sesiones comienzan al arrancar el backend; detener solo estos procesos
y volver a iniciarlos para repetir. Los tiempos concretos de arriba se
capturaron con Playwright, escuchando los frames WebSocket y leyendo el DOM.
