# Tasks

## 1. Contrato y baseline
- [x] 1.1 Revisar diseño/handoff y registrar objeciones concretas — Responsable: Claude | Estado: terminada | Depende de: ninguna. Ver «Objeciones de Claude» al final.
- [ ] 1.2 Inventario y baseline reproducible: reutilizar mediciones previas, incorporar audio humano, pérdidas y dos sesiones — Responsable: Codex | Estado: pendiente | Depende de: ninguna
- [ ] 1.3 Extender métricas por etapa y correlación temporal; definir corpus anotado y límites de recursos — Responsable: Codex | Estado: pendiente | Depende de: 1.2

## 2. Recursos y traducción progresiva
- [ ] 2.1 Cliente HTTP con lifespan, preparación de modelos y cierre/cancelación probados — Responsable: Codex | Estado: pendiente | Depende de: 1.3
- [ ] 2.2 Consumir NDJSON y emitir revisiones de traducción sobre original final; tratar truncamiento/errores — Responsable: Codex | Estado: pendiente | Depende de: 1.1, 2.1
- [ ] 2.3 Tests de revisiones tardías, stop, timeout, snapshot y aislamiento de sesiones — Responsable: Codex | Estado: pendiente | Depende de: 2.2

## 3. Reconocimiento y segmentación
- [ ] 3.1 Buffer de audio nuevo/contexto, límites, alineación y ASR incremental con pruebas de conservación — Responsable: Codex | Estado: pendiente | Depende de: 1.3
- [ ] 3.2 Detector textual con presupuesto, confirmación y deadline provisional; evaluar negaciones/cifras/nombres — Responsable: Codex | Estado: pendiente | Depende de: 3.1
- [ ] 3.3 Scheduler justo con una revisión pendiente por unidad abierta y FIFO de unidades cerradas; source_revision — Responsable: Codex | Estado: pendiente | Depende de: 2.3, 3.2

## 4. Frontend (handoff a Claude)
- [x] 4.1 Paquetes objetivo 100ms y flush antes de stop, offsets y backpressure; sin duplicar reproducción — Responsable: Claude | Estado: terminada | Depende de: ninguna. Verificación: `frontend/tests/browser/worklet.spec.js` (3 pruebas, contexto offline a 16kHz contra el worklet real) comprueba paquetes de 4+3200 bytes, offsets contiguos sin huecos ni solapamiento, muestras intactas (no silencio) y flush del fragmento parcial al `stop` cubriendo el audio de punta a punta. El formato (offset uint32 LE + PCM16 LE) no cambió; el audio capturado se sigue enrutando a una ganancia en 0, así que no se reproduce de nuevo.
- [x] 4.2 Validar/ajustar UI provisional/final contra v1 y casos de revisiones/invalidation/snapshot — Responsable: Claude | Estado: terminada | Depende de: 1.1. Verificación: 4 pruebas nuevas en `frontend/tests/browser/ui.spec.js` con fixtures deterministas (sin modelos): tres revisiones del mismo segmento siguen siendo una sola intervención y no se anexan como frases; una traducción tardía de una revisión reemplazada no vuelve a mostrarse; un `final` repetido es idempotente y no duplica; al reconectar por salto de `seq` el snapshot reemplaza el estado sin duplicar. No hizo falta cambiar la UI: el manejo por `(segment_id, kind, language)` + `revision` ya cumplía.
- [ ] 4.3 Medición de recepción/render y prueba navegador sin comparar relojes incompatibles — Responsable: Claude | Estado: pendiente | Depende de: 1.3, 4.1, 4.2
- [ ] 4.4 Revisar PR frontend preservando cambios ajenos — Responsable: Codex | Estado: pendiente | Depende de: 4.3

## 5. Evaluación y cierre
- [ ] 5.1 Experimentos A/B de parámetros uno por vez, luego combinación con dos sesiones durante 15–20min — Responsable: Codex | Estado: pendiente | Depende de: 3.3, 4.4
- [ ] 5.2 Publicar tabla de latencia, calidad, backlog, pérdidas, recursos, configuración y rollback; conservar experimental lo no validado — Responsable: Codex | Estado: pendiente | Depende de: 5.1
- [ ] 5.3 Revisión cruzada backend y reproducción de evidencia — Responsable: Claude | Estado: pendiente | Depende de: 5.2
- [ ] 5.4 Consolidar specs y archivar al cumplir aceptación — Responsable: Codex | Estado: pendiente | Depende de: 5.3

Spec creada por Codex el 2026-09-25. Solo documentación en este checkpoint.
No ejecutar modelos concurrentemente con pruebas de Claude sin coordinación.
G4 de proveedores nube (PR #15) sigue separado; no duplica este benchmark local.

## Objeciones de Claude (1.1) — 2026-09-25

De acuerdo con el diseño en general: conservar el protocolo v1, medir antes de
declarar mejoras y separar frío de caliente me parecen las decisiones correctas.
Cuatro objeciones concretas, ninguna bloqueante:

**1. Los paquetes descartados por congestión del navegador se reportan como
`source_disconnect`, y eso es engañoso.** En `capture.py`, cuando el offset de
un paquete salta, se registra un gap con razón `source_disconnect` ("se perdió
la fuente de audio"). Pero el salto también ocurre si el worklet tuvo que
descartar audio por congestión local, con la fuente intacta. Al medir pérdidas
(tareas 1.2/5.2) esto va a atribuir mal la causa. Propongo una razón distinta
para pérdida en el transporte, o al menos no contar ambos casos juntos en la
evidencia. Del lado del frontend ya lo dejo visible en la UI y cuantificado en
segundos, pero el backend no puede distinguirlos con la información actual.

**2. "No restar `performance.now()` de timestamps monotónicos de Python" es
correcto, pero falta decir contra qué correlacionar.** El punto 5 del handoff y
el escenario «Relojes distintos» prohíben la resta pero no fijan la referencia.
Propongo usar el `offset` de muestras del paquete como reloj común: ya viaja en
el protocolo, es exacto, y el navegador sabe qué offset envió y cuándo. Sin una
referencia acordada, cada lado va a inventar la suya y las mediciones no van a
ser comparables. Lo necesito definido antes de 4.3.

**3. El presupuesto del detector semántico debería tener un tope absoluto
visible en la UI.** El escenario «Habla continua sin cierre» publica con
`deadline` al vencer el presupuesto, pero si el presupuesto se reinicia por
contenido nuevo, un orador sin pausas puede no cerrar nunca una unidad. La UI
hoy muestra el provisional, así que el síntoma sería texto que cambia sin
confirmarse nunca. Pido que el tope sea explícito y acotado, no solo relativo
al «primer contenido pendiente».

**4. Riesgo de UX, no de contrato: revisiones frecuentes sobre texto
provisional.** El ASR incremental va a revisar el mismo segmento más seguido.
El manejo por `(segment_id, kind, language)` + `revision` ya lo soporta y no
pienso tocarlo, pero leer se vuelve molesto si el texto cambia varias veces por
segundo. El marcador de ritmo del frontend (`captions.js`) actualiza en el
lugar sin reiniciar el tiempo de lectura, así que absorbe parte; si aun así
resulta inestable lo resuelvo del lado de la presentación, no pidiendo cambios
al backend.

Nada de esto requiere cambiar el protocolo v1.
