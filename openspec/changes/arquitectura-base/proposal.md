# Proposal

## Why

Antes de repartir tareas entre Claude y Codex o de elegir un stack, hace
falta un acuerdo explícito sobre qué exige el sistema: cuánta latencia
tolera, cuántas sesiones simultáneas debe soportar, qué pasa si una sesión
falla. Sin esto, cada asistente puede optimizar por objetivos distintos
(uno por simplicidad, el otro por rendimiento) y las piezas no van a
encajar cuando se integren. Este cambio deja registrados los drivers de
arquitectura (atributos de calidad) y un diagrama de componentes de alto
nivel que sirvan de referencia para todas las specs y decisiones de stack
posteriores.

La visión aportada después por el usuario está sintetizada en
[`VISION.md`](../../../VISION.md): traducción por unidades de sentido,
incrementalidad, especulación, control de latencia y contexto multimodal.
Este cambio conserva puntos de extensión para esa dirección; las capacidades
funcionales se especificarán en cambios posteriores sin darlas por implementadas.

## What Changes

- Definir y priorizar los drivers de arquitectura (no funcionales) de
  Decilo: latencia, escalabilidad horizontal, tolerancia a fallos por
  sesión, precisión de transcripción/traducción con términos técnicos,
  simplicidad de despliegue/operación, costo operativo, extensibilidad y
  velocidad de desarrollo bajo el plazo del hackathon.
- Documentar un diagrama de componentes de alto nivel (Mermaid) con el
  flujo: fuente de audio → captura → motor intercambiable de
  transcripción/traducción → distribución de eventos → vista de audiencia,
  para N sesiones. La ejecución local es preferida; el soporte de audio
  del proveedor y su capacidad se verifican antes de seleccionarlo.
- Definir mediciones reproducibles de latencia y calidad, límites de
  cola y comportamiento ante saturación, sin prometer recursos ilimitados.
- Preservar límites de componentes para segmentación semántica, hipótesis
  revisables, contexto, hablantes y video; separar latencia percibida de
  tiempo hasta resultado definitivo.
- Dejar registrada la evaluación de lenguaje/runtime del backend (Rust
  propuesto por el usuario por velocidad y nativo) frente a los drivers
  anteriores, incluyendo el trade-off con velocidad de desarrollo.

## Capabilities

### New Capabilities
- `system-architecture`: atributos de calidad exigidos al sistema completo
  (latencia p95, calidad, sesiones concurrentes soportadas,
  aislamiento de fallos, sobrecarga y despliegue). Sirve como criterio de aceptación
  transversal para las specs de capacidades funcionales que se definan
  después (captura de audio, transcripción, distribución de subtítulos,
  vista de audiencia).

### Modified Capabilities
(ninguna — proyecto greenfield, sin specs previas)

## Impact

No afecta código todavía (todavía no hay implementación). Afecta:
- La decisión de lenguaje/runtime del backend, que se registrará en
  `design.md` de este cambio.
- El contrato de eventos de sesión/subtítulos que Claude y Codex acuerden
  en un cambio posterior (`COLLABORATION.md`), que deberá cumplir estos
  drivers (en particular latencia y aislamiento de fallos).
- ~~El reparto de tareas entre Claude y Codex, todavía pendiente de decisión
  del usuario~~ — resuelto 2026-09-24: ver `COLLABORATION.md` § "Reparto
  confirmado".
