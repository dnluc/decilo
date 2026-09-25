# Traducción progresiva: verificación de integración

Etapa B de backend-latencia-incremental. Conserva VAD de Claude (PR #14), contratos
v1 y default solo final. Implementa cliente HTTP por lifespan/event loop,
preparación opt-in, streaming NDJSON, provisionales y confirmación explícita.

Prueba corta REAL contra Ollama 0.32.3 y gemma3n:e2b en CPU:
- Antes de solicitar traducción Ollama no tenía modelos residentes.
- Primer contenido: 6.5561s desde solicitud; final: 7.7048s.
- El flujo real llegó antes de completarse la respuesta (1.1487s de diferencia).
- Esto incluye arranque frío; no mide micrófono, Whisper, red del navegador ni render.
- No hay comparación A/B sostenida ni garantía de mejora de calidad.
- La salida tradujo términos que nuestro ejemplo prefería conservar; el glosario
  sigue requiriendo evaluación, no se acredita fidelidad técnica por completar la llamada.

`smoke.json` contiene entrada, salida, tiempos, versiones, digest y residencia
antes/después. No contiene credenciales. Única petición corta de inferencia,
realizada con las sesiones locales sin audio activo; no benchmark concurrente.

Verificación: 161 tests Python, Ruff y 3 pruebas actuales de integración navegador
correctos. Cubren fragmentación NDJSON, errores/timeout/truncamiento, cierre por
cancelación, respuesta provisional visible antes del final, snapshot, reuse de
cliente y preparación fallida. La integración navegador usa inferencia simulada.

Pendiente: baseline de charla humana de 15–20min con dos sesiones, métricas de
render/CPU/RAM durante esa prueba, revisión cruzada y ASR incremental (etapa C).
No se cambió el servidor de demo activo ni sus flags.
