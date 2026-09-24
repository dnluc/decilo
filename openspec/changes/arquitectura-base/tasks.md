# Tasks

## 1. Documentar drivers y diagrama

- [x] 1.1 Escribir `proposal.md` (why/what/capabilities) — Responsable: Claude | Estado: terminada | Depende de: ninguna. Verificación: archivo existe y cubre motivación, cambios y capacidad `system-architecture`.
- [x] 1.2 Escribir `specs/system-architecture/spec.md` con requirements testeables (latencia, escalabilidad, aislamiento de fallos, documentación de despliegue) — Responsable: Claude | Estado: terminada | Depende de: 1.1. Verificación: `npx @fission-ai/openspec@latest validate arquitectura-base --strict` no reporta errores de formato de spec.
- [x] 1.3 Escribir `design.md` con diagrama Mermaid de componentes y decisión de lenguaje/runtime — Responsable: Claude | Estado: terminada | Depende de: 1.1. Verificación: el diagrama renderiza en GitHub y las decisiones (Rust, WebSocket, Ollama local) quedan documentadas con alternativas y riesgos.

## 2. Revisión y confirmación

- [ ] 2.1 Codex revisa `proposal.md`, `spec.md` y `design.md`; registra aceptación o ajustes — Responsable: Codex | Estado: pendiente | Depende de: 1.1, 1.2, 1.3. Verificación: entrada escrita por Codex en este archivo o en `COLLABORATION.md`.
- [ ] 2.2 Usuario confirma o ajusta el límite de latencia (3s p95 propuesto) y la elección de Rust — Responsable: usuario (dnluc) | Estado: pendiente | Depende de: ninguna. Verificación: confirmación registrada en este archivo.

## 3. Spike técnico: audio con Gemma 3n vía Ollama

- [ ] 3.1 Enviar un audio de prueba corto a `gemma3n:e4b` vía la API de Ollama y confirmar si transcribe correctamente — Responsable: sin asignar (depende del reparto) | Estado: bloqueada | Depende de: que termine de bajar el modelo. Verificación: transcripción visible en la respuesta de la API para un audio con contenido conocido.
- [ ] 3.2 Medir la latencia end-to-end del spike y compararla con el límite de 3s (p95) de `spec.md` — Responsable: sin asignar | Estado: bloqueada | Depende de: 3.1. Verificación: medición en segundos registrada en este archivo.
- [ ] 3.3 Si el spike falla o no cumple la latencia, registrar en `design.md` la decisión de fallback (Whisper + Gemma 3 texto) — Responsable: sin asignar | Estado: bloqueada | Depende de: 3.2. Verificación: `design.md` actualizado con la decisión final y su justificación.

## 4. Cierre del cambio

- [ ] 4.1 `npx @fission-ai/openspec@latest validate arquitectura-base --strict` sin errores — Responsable: Claude | Estado: pendiente | Depende de: grupos 1-3. Verificación: salida del comando sin errores.
- [ ] 4.2 Archivar el cambio (`openspec archive arquitectura-base`) una vez validado y con el spike resuelto — Responsable: quien integre según `COLLABORATION.md` | Estado: pendiente | Depende de: 4.1.
