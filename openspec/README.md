# OpenSpec: estado y lectura de los cambios

Corte documental: `e4b9f90`, 25/09/2026, con PRs #20–#22 integrados.
La [arquitectura implementada](../docs/ARQUITECTURA.md) y el [README](../README.md)
son las guías operativas. Las propuestas/specs conservan objetivos y decisiones;
los tests de estructura y una casilla terminada no equivalen a aceptación de
rendimiento ni cumplimiento de todos los escenarios.

| Cambio | Implementación vigente | Pendiente o parte sustituida |
| --- | --- | --- |
| [arquitectura-base](changes/arquitectura-base/tasks.md) | Python/FastAPI, faster-whisper, Ollama y Gemini; arquitectura detallada publicada | Validación sostenida del objetivo 3 s p95; diagramas iniciales son históricos |
| [contrato-sesiones-subtitulos](changes/contrato-sesiones-subtitulos/design.md) | Catálogo y stream v1, snapshots, revisiones, límites por espectador | Políticas de finalización/gaps del motor no cumplen automáticamente toda la spec |
| [mvp-pipeline](changes/mvp-pipeline/tasks.md) | Archivos a ritmo real, cola opcional, captura y proveedores | Benchmark largo/aislamiento; modelos iniciales medium/e4b no son defaults actuales |
| [vista-audiencia](changes/vista-audiencia/tasks.md) | UI actual con video, captura, dock e historial; estado v1 conservado | Catálogo visual, demo sintética y presentación inicial fueron sustituidos |
| [audio-playback](changes/audio-playback/tasks.md) | Endpoints WAV/runs/start permanecen | Reproductor WAV y resaltado por audio retirados de la UI vigente |
| [captura-pestana](changes/captura-pestana/design.md) | PCM 100 ms, selección por captura, detección inicial y Live/segmentos | Permiso manual, validación con fuentes humanas y reserva durante detección |
| [backend-latencia-incremental](changes/backend-latencia-incremental/tasks.md) | Parciales base/small, cortes textuales, Ollama streaming y Gemini Live | Presupuesto semántico, aceptación A/B, finalización incierta y timestamps de cortes |
| [entrega-devpost](changes/entrega-devpost/tasks.md) | Seguimiento de formulario y borrador local | Estado externo no reconsultado en esta actualización; Markdown no implica envío |

## Diferencias que no deben ocultarse al marcar tareas

- La spec incremental prohíbe confirmar por mero cierre; Live hoy confirma la
  última provisional al terminar/reconectar o ante una reescritura no alineable.
  Ese método tampoco encola traducción. Documentado, no aprobado como cumplimiento.
- El corte textual local puede retroceder `end_ms` respecto de una hipótesis ya
  publicada; requiere prueba de integración con la validación de `SessionStream`.
- Los cortes textuales se etiquetan `pause`, aunque el contrato admite `semantic`.
  No hay controlador semántico con presupuesto adaptativo; Live no usa el tope local de 6 s.
- La detección automática usa Whisper incluso en nube y no reserva cupo hasta
  registrar la sesión. Dos trabajos nominales no son límite atómico de detecciones.
- HTTP Gemini reutiliza clientes, pero su cierre no está conectado al lifespan.
- Los smokes de PRs #21/#22 no sustituyen benchmark humano sostenido ni demuestran
  fidelidad equivalente tras cambiar modelo/hilos. Conservar mediciones anteriores.

## Actualizar sin reescribir evidencia

Registrar commit, responsable y validación en `tasks.md`; distinguir avance de
implementación, revisión y aceptación. No archivar cambios por una actualización
documental ni transformar automáticamente los pendientes en completos.
Los bloques de estado al inicio de cada artefacto separan el corte actual de su
contenido histórico/normativo. Ver [índice de evidencia](../docs/validation/README.md).
