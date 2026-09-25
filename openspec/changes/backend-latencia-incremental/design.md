# Design

> **Lectura al 25/09/2026, PR #22 (`e4b9f90`):** PRs #20–#22 integrados: parciales, heurística textual y Live. Requisitos de presupuesto semántico, finalización incierta y evaluación sostenida siguen abiertos; diseño original es el objetivo, no una declaración de cumplimiento.
> [Estado global, divergencias y evidencia](../../README.md).

## Estado y etapas

Diseño objetivo por etapas. Claude registró revisión/objeciones en tasks.md;
PRs #20–#22 implementaron parte de A–C. Consultar el estado al inicio: lo
implementado no acredita automáticamente todos los requisitos de este diseño.
Se reutilizan la cola opt-in, segmentador por pausas, modelo residente, worker
fuera del event loop y controles de revisión existentes. Preservar VAD y filtros
de no-habla de PR #14. No duplicar sus implementaciones.

A: medir y mejorar residencia/conexiones; mantener salida final actual.
B: streaming de traducción de originales ya confirmados; permite probar UI
provisional sin depender del nuevo reconocedor.
C: ASR incremental, acuerdo entre hipótesis y compuerta semántica; habilitar
traducción de originales provisionales con límites de trabajo.
D: evaluación sostenida y selección explícita de perfiles.
Cada etapa tiene un flag/configuración reversible documentada al implementarla;
no se cambia el default de producción antes de medir y revisar esa etapa.

## Transporte, reconocimiento y significado

Transporte: PCM16 LE mono 16kHz, paquetes objetivo de 100ms (1600 muestras),
ajustable 40–200ms para comparar; no dispara inferencia por paquete. Conservar
uint32 LE inicial de offset, límite actual 80000 muestras y duración de 1 hora.
El offset avanza por muestras capturadas; una pérdida debe quedar como salto.
Mantener flush antes de stop, sin rellenar ni duplicar muestras.

ASR: estado por sesión, audio nuevo pendiente y contexto histórico acotado.
Una ejecución activa por sesión. La siguiente ventana debe incluir todo el audio
nuevo no reconocido; sustituir una petición redundante no autoriza tirar audio.
Probar cadencia mínima de 400–700ms solo si la capacidad medida la sostiene;
ajustarla al costo por audio NUEVO, evitando recodificación permanente del pasado.
Ventanas solapadas requieren alineación/deduplicación por tiempos y texto.
Definir límites de buffer y política de saturación antes de activar el modo.

Compuerta: recibe hipótesis ASR, estabilidad entre revisiones, puntuación y pausas.
No llama a otro LLM por cada paquete. Una pausa es evidencia acústica; `semantic`
solo se usa cuando interviene el detector textual. Evaluar negaciones, cifras,
nombres y expresiones que atraviesan ventanas. El detector no garantiza comprender.
Experimentar con espera de 1000–1500ms desde el primer contenido pendiente de la
unidad; revisiones posteriores no reinician indefinidamente el plazo. Ese plazo
limita la espera adicional de segmentación, no garantiza el tiempo total de ASR.
Al vencer, emitir lo disponible como provisional con reason=deadline; no inventar
continuación. Una unidad puede seguir abierta con contexto hasta estabilizarse.
Si acaba el audio y no se puede confirmar con fidelidad, mantener provisional y
emitir error explícito; terminar la sesión no convierte hipótesis en hechos.

## Contrato de subtítulos v1

Reutilizar session_id, stream_id, seq y CaptionData. Identidad de entrada:
(segment_id, kind, language); revision creciente. segment_seq/start_ms estables,
end_ms no decrece. Los tiempos de traducción coinciden con su original vigente.
No introducir unit_id/revision_id públicos duplicados: unit_id interno corresponde
a segment_id y revision_id a revision. Para una unidad abierta puede sustituirse
todo su texto provisional; final es inmutable. No hay campo de prefijo estable:
no inventarlo en el frontend. Un prefijo confirmado se representa como segmento
cerrado separado, con intervalos sin duplicación.

La traducción lleva source_revision. Si cambia el original, invalidar la traducción
anterior mediante el comportamiento existente del stream; rechazar salida tardía.
Original final no finaliza automáticamente traducción. Solo publicar traducción
final con original final vigente y generación completada correctamente. Timeout,
cancelación o límite de tokens no autorizan confirmar una salida truncada.

## Traducción y recursos

Cliente HTTP compartido por proceso/event loop, creado/cerrado con lifespan e
inyectable en pruebas. No compartir cliente async entre loops. Cancelación cierra
streams y recursos. Ollama sigue en el servidor existente; no lanzar otro daemon.
Precarga explícita con timeout, métricas y readiness antes de consumir audio;
no cargar modelos al importar módulos ni en tests sin modelos. Sesiones siguen
pudiendo consultarse mientras se preparan; fallo de precarga se informa.

Consumir NDJSON real de Ollama. Publicar contenido acumulado provisional con
revisiones, agrupar actualizaciones para no emitir un evento por token; probar
300–500ms sin agregar espera al final. Un proveedor sin parciales puede seguir
emitiendo únicamente finales: no simular streaming. Mantener glosario, números,
negaciones, nombres y es-AR. Contexto reciente y prompt acotados por sesión.

Opciones a comparar por separado: beam_size=1 y temperatura fija en Whisper;
keep_alive, num_ctx 2048/4096, salida limitada con detección de truncamiento en
Ollama. Valores son experimentos, no defaults aprobados. No repetir la reducción
de hilos que ya empeoró resultados sin una hipótesis y evidencia nuevas.

Scheduler: por sesión/etapa un activo; para la MISMA unidad abierta, una revisión
pendiente reemplazable por la más reciente. Unidades cerradas distintas van a una
cola FIFO acotada aparte: no son reemplazables. Reparto justo entre sesiones.
No cancelar una generación por cada revisión. Descartar una respuesta vieja no
implica haber liberado inferencia remota. Video/enriquecimientos nunca bloquean.

## Saturación y medición honesta

Memoria limitada, audio ilimitado y capacidad insuficiente no pueden coexistir
sin pérdida o atraso. En operación conservar gaps explícitos y estado degraded
ante descartes inevitables; registrar segundos perdidos. No declarar ese perfil
sostenible sin pérdida. En benchmark reproducible, usar archivo de origen durable
para prueba sin descartes; detener con diagnóstico si se alcanza el límite de
recursos declarado. No introducir una cola RAM ilimitada para conservar todo.
La política de recuperación tras saturación debe probarse, no esconder el atraso.

## Métricas y aceptación de perfiles

Extender measure_latency y evidencia existente. Registrar versiones, CPU/GPU
real, modelo/digest, cuantización, flags, muestras, sesiones, calentamiento y carga.
Correlacionar captura/recepción/ASR/cola/traducción/envío/render por IDs y muestras.
Relojes locales monotónicos para duraciones; no restar reloj navegador y Python.
Prueba de navegador con reloj común o estimación de desfase con incertidumbre.

Reportar p50/p95/máximo del primer texto español visible y final, tanto desde inicio
como final del intervalo fuente cuando estén disponibles. Si una hipótesis aparece
antes de terminar la unidad, registrar esa diferencia sin confundirla con error de
reloj. Primer texto no demuestra utilidad: evaluar fidelidad humana por separado.
Desglosar carga, prompt/generación, tokens, cola, backlog, memoria, gaps y revisiones.
No sumar duraciones concurrentes ni contar inglés como traducción española.

Mismo audio técnico humano, 1 y 2 sesiones, silencio/música/aplausos, habla continua,
negaciones/cifras/nombres, cambios de hablante, desconexión y stop. Prueba sostenida
15–20min. Aceptar perfil si reduce p95 del primer español frente a baseline, no
empeora p95 final, no crece sostenidamente backlog, no pierde audio ni empeora
errores de contenido en corpus anotado. Registrar variabilidad y resultados mixtos;
si no cumple, mantenerlo experimental. Nube se mide aparte con modelo/cuota/costo.
