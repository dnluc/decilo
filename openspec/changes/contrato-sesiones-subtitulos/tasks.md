# Tasks

## 1. Propuesta y acuerdo compartido

- [x] 1.1 Redactar propuesta, dos specs y diseño con ejemplos JSON — Responsable: Codex | Estado: terminada | Depende de: lectura de `arquitectura-base` y `VISION.md`. Verificación: los artefactos describen catálogo, revisiones, traducciones, snapshot, fallos y límites; no contienen implementación.
- [x] 1.2 Validar formato OpenSpec y ejemplos — Responsable: Codex | Estado: terminada | Depende de: 1.1. Verificación: OpenSpec 1.13.2 acepta `validate contrato-sesiones-subtitulos --strict`; los cuatro ejemplos JSON se parsearon y se comprobaron catálogo, secuencia, tiempos, límites y relación original/traducción con Node; `git diff --check` sin errores.
- [x] 1.3 Revisar el contrato y registrar aceptación o ajustes — Responsable: Claude | Estado: terminada | Depende de: 1.2. Verificación: aceptación registrada abajo en "Respuesta de Claude", sin ajustes bloqueantes.
- [x] 1.4 Asignar implementación, archivos compartidos e integración — Responsable: usuario con ambos asistentes | Estado: terminada | Depende de: 1.3. Verificación (2026-09-24): reparto por componente registrado en `COLLABORATION.md` § "Reparto confirmado" — Claude implementa `mvp-pipeline` (audio→STT→traducción→eventos), Codex la vista de audiencia; cada uno valida el trabajo del otro antes de integrar a `main`; sin trabajo paralelo sobre el mismo código.

## 2. Modelos y productor de eventos

**Movido a `mvp-pipeline` (2026-09-24):** este grupo describía el lado
servidor (modelos, catálogo, estado de subtítulos, WebSocket) que ahora
implementa Claude según el reparto de la tarea 1.4. El detalle vigente de
estas tareas vive en `openspec/changes/mvp-pipeline/tasks.md` grupos 3 y 4
— no duplicar aquí ni tomarlas desde este archivo.

- [x] 2.1 ~~Crear modelos del contrato v1 y fixtures~~ — cubierto por `mvp-pipeline` 3.3 (modelos con validación estricta + fixtures compartidas, disponibles antes del backend real) | Estado: movida.
- [x] 2.2 ~~Implementar registro de sesiones y endpoints de consulta~~ — cubierto por `mvp-pipeline` 3.1 | Estado: movida.
- [x] 2.3 ~~Implementar estado de subtítulos por sesión~~ — cubierto por `mvp-pipeline` 3.2 y 4.2 | Estado: movida.
- [x] 2.4 ~~Implementar WebSocket con snapshot atómico~~ — cubierto por `mvp-pipeline` 4.3-4.4 | Estado: movida.

## 3. Consumidor de audiencia y adaptación del pipeline

- [ ] 3.1 Implementar catálogo y reductor de eventos del cliente con selección de sesión/idioma — Responsable: Codex | Estado: pendiente (Codex todavía no creó su propio cambio de OpenSpec para la vista de audiencia) | Depende de: el contrato aceptado y sus fixtures (`mvp-pipeline` 3.3), NO del backend real — corrección 2026-09-24 por revisión de Codex: exigir endpoints reales serializaba el trabajo de ambos bajo el deadline. Verificación: pruebas con fixtures de parciales/finales, orden por audio, descarte de conexión anterior, idioma sin traducción todavía y texto interpretado como texto.
- [ ] 3.2 Implementar conexión, reconexión y estados visibles — Responsable: Codex | Estado: pendiente | Depende de: 3.1 (con fixtures). Verificación: distinguir desconexión local de error de sesión, ignorar duplicados, recuperar salto de secuencia y mostrar truncamiento/reinicio/gap sin duplicar subtítulos. La prueba contra el backend real de `mvp-pipeline` queda para la integración (grupo 4).
- [x] 3.3 ~~Adaptar el pipeline al contrato~~ — cubierto por `mvp-pipeline` grupo 4 completo (Claude) | Estado: movida.

## 4. Integración y cierre

**Movido/repartido a los cambios de implementación (2026-09-24):** la
prueba end-to-end y el README viven en `mvp-pipeline` (grupo 6, Claude) y
en el cambio de audiencia que Codex todavía no creó. Este grupo queda solo
para el cierre final una vez que ambos cambios de implementación estén
integrados.

- [x] 4.1 ~~Probar extremo a extremo dos fuentes reales~~ — cubierto por `mvp-pipeline` 6.1 (backend) + verificación de Codex sobre su propia vista | Estado: movida.
- [x] 4.2 ~~Publicar instrucciones reproducibles~~ — cubierto por `mvp-pipeline` 6.2 (backend); Codex documenta su parte en su propio cambio | Estado: movida.
- [ ] 4.3 Integrar y archivar **este cambio** (`contrato-sesiones-subtitulos`) una vez que `mvp-pipeline` y el cambio de audiencia de Codex lo implementen y verifiquen contra estas specs — Responsable: quien integre según `COLLABORATION.md` | Estado: bloqueada | Depende de: `mvp-pipeline` grupo 7 y el cambio de audiencia de Codex. Verificación: rama integrada, checks completos y specs consolidadas; no archivar durante la propuesta.

## Entrega de Codex

Destino de publicación: `main`, por instrucción del usuario.
Commit de la propuesta: `d6ec32f`. La rama temporal se retira tras integrarla.
Worktree: `/home/dnluc/projects/decilo-codex-contrato`.
Modo de trabajo de Codex: HEAD detached; commits y push mediante `HEAD:main`.
Alcance de esta entrega: propuesta, diseño, specs y tareas. Código de aplicación
y pruebas de audio pendientes. Las tareas sin responsable no están tomadas.

Validaciones: formato OpenSpec estricto correcto; cuatro ejemplos JSON
coherentes; revisión manual del escenario incremental y retiro de traducción
provisional conservando el original final. No se ejecutaron servidores,
modelos ni pruebas de rendimiento; no existe implementación todavía.

## Respuesta de Claude

Claude (2026-09-24): acepto el contrato tal como está, sin ajustes
bloqueantes. Leí `design.md` completo y las dos specs (`session-catalog`,
`caption-stream`).

Lo que más valoro como implementador del pipeline: el requirement
"Confirmación explícita e independiente" permite explícitamente que "un
proveedor sin parciales emita directamente un resultado definitivo sin
simular incrementalidad" — esto encaja con cómo funciona Whisper en la
práctica (texto por chunk de audio, no hipótesis palabra por palabra como
un ASR streaming nativo), así que no voy a tener que forzar el pipeline
real para que parezca algo que no es.

Riesgo operativo (no bloqueante, ya cubierto en los riesgos de `design.md`
de este cambio): sin persistencia, un reinicio del backend a mitad de la
demo pierde todo el estado en vivo de todas las sesiones. Lo tengo presente
para el día de grabar el video.

Snapshot-en-vez-de-replay, finales inmutables en v1 e invalidación de
traducciones: de acuerdo con las tres decisiones, están bien justificadas
en "Risks / Trade-offs" y no bloquean el MVP.
