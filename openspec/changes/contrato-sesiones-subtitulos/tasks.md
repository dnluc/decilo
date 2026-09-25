# Tasks

## 1. Propuesta y acuerdo compartido

- [x] 1.1 Redactar propuesta, dos specs y diseño con ejemplos JSON — Responsable: Codex | Estado: terminada | Depende de: lectura de `arquitectura-base` y `VISION.md`. Verificación: los artefactos describen catálogo, revisiones, traducciones, snapshot, fallos y límites; no contienen implementación.
- [x] 1.2 Validar formato OpenSpec y ejemplos — Responsable: Codex | Estado: terminada | Depende de: 1.1. Verificación: OpenSpec 1.13.2 acepta `validate contrato-sesiones-subtitulos --strict`; los cuatro ejemplos JSON se parsearon y se comprobaron catálogo, secuencia, tiempos, límites y relación original/traducción con Node; `git diff --check` sin errores.
- [ ] 1.3 Revisar el contrato y registrar aceptación o ajustes — Responsable: Claude (revisión solicitada, pendiente de respuesta) | Estado: pendiente | Depende de: 1.2. Verificación: respuesta escrita en este archivo, sin aceptación en nombre del otro.
- [ ] 1.4 Asignar implementación, archivos compartidos e integración — Responsable: usuario con ambos asistentes | Estado: pendiente | Depende de: 1.3. Verificación: responsables anotados en tareas y `COLLABORATION.md`; cada asistente trabaja en su worktree.

## 2. Modelos y productor de eventos

- [ ] 2.1 Crear modelos del contrato v1 y fixtures de catálogo, snapshot, originales, traducciones, errores y gaps — Responsable: por asignar | Estado: pendiente | Depende de: 1.4. Verificación: aceptar los ejemplos válidos y rechazar idioma/tipo/revisión/tiempos/tamaños inválidos; documentar validación y defaults.
- [ ] 2.2 Implementar registro de sesiones y endpoints de consulta — Responsable: por asignar | Estado: pendiente | Depende de: 2.1. Verificación: lista vacía, dos sesiones independientes y sesión desconocida, sin exponer URLs ni credenciales internas.
- [ ] 2.3 Implementar estado de subtítulos por sesión y publicación ordenada — Responsable: por asignar | Estado: pendiente | Depende de: 2.1. Verificación: duplicados, revisiones antiguas, traducciones obsoletas, finales inmutables y retiro de provisionales con gap.
- [ ] 2.4 Implementar WebSocket con snapshot atómico, retención y cola acotada por cliente — Responsable: por asignar | Estado: pendiente | Depende de: 2.2, 2.3. Verificación: evento concurrente al snapshot no se pierde, reconexión reemplaza estado, nuevo stream reinicia generación y un cliente lento no bloquea otro.

## 3. Consumidor de audiencia y adaptación del pipeline

- [ ] 3.1 Implementar catálogo y reductor de eventos del cliente con selección de sesión/idioma — Responsable: por asignar | Estado: pendiente | Depende de: 2.1. Verificación: pruebas con fixtures de parciales/finales, orden por audio, descarte de conexión anterior, idioma sin traducción todavía y texto interpretado como texto.
- [ ] 3.2 Implementar conexión, reconexión y estados visibles — Responsable: por asignar | Estado: pendiente | Depende de: 3.1, 2.4. Verificación: distinguir desconexión local de error de sesión, ignorar duplicados, recuperar salto de secuencia y mostrar truncamiento/reinicio/gap sin duplicar subtítulos.
- [ ] 3.3 Adaptar el pipeline al contrato y cancelar/descartar resultados obsoletos — Responsable: por asignar | Estado: pendiente | Depende de: 2.3 y motor real elegido en `arquitectura-base`. Verificación: original antes de traducción, referencia a revisión vigente, tiempos desde audio, error aislado y fin con drenaje acotado; no simular streaming de un motor por lotes.

## 4. Integración y cierre

- [ ] 4.1 Probar extremo a extremo dos fuentes reales, reconexión, fallo de una fuente y espectador lento — Responsable: por asignar | Estado: pendiente | Depende de: 2.4, 3.2, 3.3. Verificación: registrar configuración, calidad, p50/p95 hasta navegador, pérdidas y límites según `arquitectura-base`; ejemplos simulados no acreditan rendimiento real.
- [ ] 4.2 Publicar instrucciones reproducibles y revisar contrato final — Responsable: por asignar | Estado: pendiente | Depende de: 4.1. Verificación: README permite iniciar ambas sesiones, seleccionar idioma y repetir la prueba; no presenta video/diarización como implementados si solo hay metadatos.
- [ ] 4.3 Integrar y archivar el cambio — Responsable: quien integre | Estado: pendiente | Depende de: 4.2. Verificación: rama integrada, checks completos y specs consolidadas; no archivar durante la propuesta.

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

Pendiente. Revisar especialmente snapshot en vez de replay, finales inmutables
en v1, invalidación de traducciones y límites propuestos. Registrar ajustes
y aceptación antes de repartir implementación. Video sigue en el roadmap;
este contrato reserva datos opcionales de hablante sin implementar análisis visual.
