# Tasks

## 1. Documentar drivers y diagrama

- [x] 1.1 Escribir `proposal.md` (why/what/capabilities) — Responsable: Claude | Estado: terminada | Depende de: ninguna. Verificación: archivo existe y cubre motivación, cambios y capacidad `system-architecture`.
- [x] 1.2 Escribir `specs/system-architecture/spec.md` con requirements testeables (latencia, escalabilidad, aislamiento de fallos, documentación de despliegue) — Responsable: Claude | Estado: terminada | Depende de: 1.1. Verificación: `npx @fission-ai/openspec@latest validate arquitectura-base --strict` no reporta errores de formato de spec.
- [x] 1.3 Escribir `design.md` con diagrama Mermaid de componentes y decisión de lenguaje/runtime — Responsable: Claude | Estado: terminada | Depende de: 1.1. Verificación: el diagrama renderiza en GitHub y las decisiones (Rust, WebSocket, Ollama local) quedan documentadas con alternativas y riesgos.

## 2. Revisión y confirmación

- [x] 2.1 Codex revisa `proposal.md`, `spec.md` y `design.md`; registra aceptación o ajustes — Responsable: Codex | Estado: terminada | Depende de: 1.1, 1.2, 1.3. Verificación: revisión del 2026-09-24 registrada abajo y correcciones en los cuatro artefactos; fuentes oficiales enlazadas en `design.md`.
- [x] 2.2 Usuario confirma el límite de latencia y el lenguaje del backend — Responsable: usuario (dnluc) | Estado: terminada | Depende de: ninguna. Verificación (2026-09-24): 3s p95 confirmado tal cual propuesto. Lenguaje: **Python**, no Rust — decisión tomada junto con Claude porque el cómputo pesado (Whisper, Ollama) corre como proceso/API externo sea cual sea el lenguaje orquestador, y Python reduce la fricción de iterar bajo el plazo del hackathon (ver razonamiento completo en `design.md` § "Lenguaje/runtime del backend"). Nota: esto contradice a `VISION.md`, que sigue nombrando Rust; pendiente de reconciliar (ver sección 4).
- [x] 2.3 Incorporar la visión del usuario y reconciliar los límites de arquitectura — Responsable: Codex | Estado: terminada | Depende de: 2.1. Verificación: `VISION.md` conserva los diez niveles y diferenciales; proposal/design enlazan la visión y reservan interfaces; el ejemplo de <1,5s no se presenta como una medición ni reemplaza 2.2.

## 3. Spike técnico: compatibilidad, calidad y capacidad de inferencia

- [x] 3.1 Comprobar modalidades y API del runtime instalado — Responsable: Claude | Estado: terminada (compatibilidad confirmada; falta transcripción real ES/EN y traducción EN→ES comparadas con referencias) | Depende de: ninguna. Verificación (2026-09-24): `ollama show gemma3n:e4b` reporta `Capabilities: completion` (sin audio/visión); `curl -s localhost:11434/api/show -d '{"model":"gemma3n:e4b"}'` confirma `"capabilities":["completion"]`. Ollama NO expone entrada de audio para este modelo en esta instalación. Siguiente paso: evaluar STT local separado (Whisper vía `whisper.cpp` o `faster-whisper`) + traducción de texto EN→ES con un modelo vía Ollama.
- [x] 3.2 ~~Medir inferencia, cola y calidad con dos fuentes~~ — movida a `openspec/changes/mvp-pipeline/tasks.md` 2.1-2.2 (Claude), 2026-09-24 | Estado: movida.
- [x] 3.3 ~~Registrar motor elegido~~ — movida a `openspec/changes/mvp-pipeline/tasks.md` 2.3 (Claude), 2026-09-24 | Estado: movida.

La prueba final de latencia hasta el navegador, reconexión, aislamiento y
sobrecarga corresponde al cambio de implementación del MVP — ver
`mvp-pipeline` grupo 6. No duplicar el seguimiento acá.

## 4. Cierre del cambio

- [ ] 4.1 Validar formato con OpenSpec y revisar coherencia tras resolver grupos 1-3; registrar la prueba end-to-end pendiente en el cambio de implementación — Responsable: Claude | Estado: pendiente | Depende de: grupos 1-3. Verificación: `openspec validate arquitectura-base --strict` sin errores y tarea de integración enlazada; el validador de formato no demuestra rendimiento ni calidad.
- [ ] 4.2 Archivar el cambio (`openspec archive arquitectura-base`) una vez validado y con el spike resuelto — Responsable: quien integre según `COLLABORATION.md` | Estado: pendiente | Depende de: 4.1.

## Revisión de Codex — 2026-09-24

**Resultado: drivers aprobados con correcciones; decisiones técnicas pendientes.**

- Corregida la dependencia de audio directo en Ollama: su catálogo identifica
  Gemma 3n como Text. Separada la capacidad del modelo de la del runtime.
- Recuperada calidad como driver central; solo el glosario es opcional.
- Precisada la propuesta de 3s p95 por sesión y por salida, con origen de
  tiempos, carga concurrente y evidencia reproducible. Pendiente 2.2.
- Sustituida la garantía absoluta de no degradación por capacidad medida;
  acotado aislamiento a errores locales y añadida gestión de sobrecarga.
- Corregido el argumento del GIL: Python puede coordinar I/O concurrente;
  Rust es una preferencia válida, no una prueba de menor latencia de inferencia.
- La revisión es documental; no se ejecutaron modelos, pruebas de audio,
  benchmarks ni validación visual del nuevo Mermaid. Los checks previos
  de Claude en 1.1–1.3 describen la versión original.

Validación de esta revisión: OpenSpec 1.13.2,
`validate arquitectura-base --strict` → `Change 'arquitectura-base' is valid`.
`git diff --check` sin errores. Esto valida formato, no comportamiento del MVP.

## Incorporación de la lluvia de ideas del usuario

Se conserva en `VISION.md` una síntesis identificada como tal, con dirección
de producto y etapas. La revisión anterior no debe interpretarse como un
recorte a un traductor convencional. Se amplió el diseño lógico con ASR
incremental, realimentación de límites semánticos, versiones de traducción,
contexto y políticas adaptativas, sin implementar ni prometer esos módulos.

Pendientes del contrato posterior: protocolo de revisión/confirmación,
límite de espera semántica, correcciones excepcionales y métricas de latencia
percibida. El reparto de implementación sigue sin asignar; esta actualización
no inicia el contrato en nombre de Claude ni marca su aceptación de la visión.

## Documento de arquitectura de la implementación — Codex, 2026-09-25

Pedido explícito del usuario: documento Markdown detallado con diagramas Mermaid.
Base inspeccionada `8a61dad`, incluyendo el PR #20. Se agrega
`docs/ARQUITECTURA.md` y un enlace desde README, conservando diseños históricos.
Documenta despliegue, módulos, ingreso PCM, segmentación, ASR provisional,
autodetección, proveedores, traducción, contratos, colas, UI, operación y CI.
Distingue implementación de visión y explicita límites: detección local incluso
en nube, capacidad nominal sin reserva durante detección, estado en RAM y falta
de evaluación sostenida. No cambia código, servidores ni configuración de demo,
ni ejecuta inferencia. El documento no completa ni archiva las tareas pendientes
de aceptación de calidad/latencia de este cambio.

Validación documental: 17 diagramas renderizados a SVG con Mermaid CLI 11,
todos los enlaces relativos del documento resuelven a archivos existentes,
`openspec validate arquitectura-base --strict` correcto y `git diff --check`
sin errores. No se repitieron tests de aplicación porque solo cambió documentación.
