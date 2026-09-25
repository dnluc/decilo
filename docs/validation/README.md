# Evidencia de validación

Los subdirectorios conservan corridas históricas, no un certificado del estado
actual. No se regeneraron audios, JSON, tiempos ni inferencias para actualizar
esta documentación. Base actual: PRs #21/#22 (`e4b9f90`, 25/09/2026).

| Informe | Qué representa | Límite de interpretación |
| --- | --- | --- |
| [Dos sesiones](2026-09-25-two-sessions/README.md) | Primer recorrido Whisper/Ollama y audiencia | WAV sintéticos; anterior al pacing y perfil actual |
| [Pacing](2026-09-25-paced/README.md) | Audio alimentado a ritmo real | Corrida corta y carga externa documentada |
| [Perfil por etapas](2026-09-25-stage-profile/README.md) | Contención ASR/traducción en CPU | Modelos/threads históricos; no prueba base/small actual |
| [Cola de traducción](2026-09-25-translation-queue/README.md) | Comparación serial/solapamiento | Audio y configuración específicos, no garantía por sesión |
| [Pausas](2026-09-25-pause-segmentation/README.md) | Fronteras acústicas y conservación de muestras | Sin comprensión semántica ni validación del corte textual PR #22 |
| [Streaming Ollama](2026-09-25-streaming-translation/README.md) | Primera salida antes del final con modelo real | Arranque frío; no end-to-end de captura ni Gemini Live |
| [Nube REST](2026-09-25-cloud-backend/README.md) | Fragmento sintético de 3 s con Gemini 3.8 Flash | Dos solicitudes; no prueba 3.1, 3.5 ni Live |

Los smokes más recientes de Claude se registran en
[backend-latencia-incremental/tasks.md](../../openspec/changes/backend-latencia-incremental/tasks.md).
Sus cifras reportadas se distinguen de una comparación sostenida: falta medir
con el mismo audio humano, una/dos fuentes, calidad, pérdidas, primer español y
final hasta navegador. La revisión documental no repitió llamadas pagas.
