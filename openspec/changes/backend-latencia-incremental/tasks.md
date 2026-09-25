# Tasks

## 1. Contrato y baseline
- [ ] 1.1 Revisar diseño/handoff y registrar objeciones concretas — Responsable: Claude | Estado: pendiente | Depende de: ninguna
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
- [ ] 4.1 Paquetes objetivo 100ms y flush antes de stop, offsets y backpressure; sin duplicar reproducción — Responsable: Claude | Estado: pendiente | Depende de: ninguna
- [ ] 4.2 Validar/ajustar UI provisional/final contra v1 y casos de revisiones/invalidation/snapshot — Responsable: Claude | Estado: pendiente | Depende de: 1.1
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
