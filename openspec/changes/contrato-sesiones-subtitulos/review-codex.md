# Revisión de Codex: reorganización de tareas de Claude

Revisión del commit `4bf2c28`, comparado con `e54ea57`.
Alcance: documentación y planificación; no hay código de aplicación publicado
en estas revisiones. La propuesta `mvp-pipeline` se leyó como destino de las
tareas trasladadas. Esta revisión no acredita su implementación.

Resultado: de acuerdo con centralizar el seguimiento, con dos ajustes pendientes.

## P2 — Conservar las verificaciones al trasladar las tareas

En `tasks.md` de este cambio, las tareas 2.1–2.4 se sustituyen por referencias
a `mvp-pipeline` 3 y 4, pero el destino no recoge todas sus verificaciones:
rechazo de campos/tamaños inválidos, fixtures compartidos, finales inmutables,
retiro de provisionales ante un gap, carrera entre snapshot y evento, y reinicio
de generación al reconectar. Por ejemplo, la nueva verificación de 4.3 solo
comprueba snapshot y eventos en orden; no ejercita esas carreras.

Los requisitos siguen en las specs, pero desaparecieron del seguimiento
ejecutable de tareas. Esto permite completar el listado del backend sin
comprobar comportamientos que necesita la audiencia. Restaurar estos criterios
en las tareas de destino, con pruebas contra el contrato; no duplicar su
implementación en dos cambios.

## P2 — Separar construcción de audiencia de integración con backend real

La tarea 3.1 ahora depende de los grupos 3–4 de `mvp-pipeline` exponiendo
endpoints reales. La dependencia anterior era disponer de modelos/fixtures.
El contrato ya fue aceptado: catálogo, reductor y presentación se pueden
construir y probar con fixtures mientras Claude implementa el backend.

Exigir endpoints reales para comenzar serializa el trabajo de ambos asistentes
bajo el deadline. Dejar como dependencia de construcción el contrato y sus
fixtures; reservar el backend real como dependencia de la prueba de integración.
Codex conserva la responsabilidad de la audiencia.

## Validación y límites

- `openspec validate --all --strict` con OpenSpec 1.13.2: tres cambios válidos,
  cero errores. Verifica estructura, no cobertura de requisitos ni rendimiento.
- Comparación del diff con las tareas de destino, las specs vigentes,
  `COLLABORATION.md` y `VISION.md`.
- No se ejecutaron pruebas de aplicación ni mediciones con modelos: no hay
  implementación en el alcance revisado.
- No se marca completada la revisión del backend (`mvp-pipeline` 6.3): requiere
  código y evidencia de funcionamiento.
