# Proposal

> **Lectura al 25/09/2026, PR #22 (`e4b9f90`):** PRs #20–#22 integrados: parciales, heurística textual y Live. Requisitos de presupuesto semántico, finalización incierta y evaluación sostenida siguen abiertos; diseño original es el objetivo, no una declaración de cumplimiento.
> [Estado global, divergencias y evidencia](../../README.md).

## Why

Decilo necesita reducir la demora del primer subtítulo español útil sin ocultar
pérdidas ni degradar fidelidad. El backend actual reconoce después del corte
acústico y espera la traducción completa. Cortar por pausa no demuestra que una
idea esté completa. Ya existen mediciones, colas acotadas y contratos versionados:
se deben extender, preservando trabajo previo y el filtro VAD integrado en PR #14.

Base: VISION.md, contratos activos y el informe del usuario
`instrucciones_latencia_whisper_gemma.md`, leído el 2026-09-25. El informe propone
experimentos; sus cifras no son mediciones de esta máquina. Este cambio registra
las decisiones aplicables sin depender del archivo privado de Descargas.

## What Changes

- Instrumentar primer texto español, confirmación, colas, pérdidas e inferencia.
- Reutilizar clientes HTTP, preparar modelos y consumir traducción progresiva.
- Incorporar ASR incremental con contexto acotado y límites semánticos sobre texto.
- Planificar revisiones sin borrar unidades distintas ni saturar la CPU.
- Definir el handoff de transporte y presentación para Claude, conservando v1.
- Comparar perfiles reversibles con una y dos sesiones y audio humano.

## Capabilities

### New Capabilities
- `incremental-backend`: ejecución incremental, planificación y evaluación de
  latencia sostenible sobre los contratos de captura y subtítulos existentes.

### Modified Capabilities
Ninguna consolidada. Se implementa contra los cambios activos `mvp-pipeline`,
`captura-pestana` y `contrato-sesiones-subtitulos`; cualquier necesidad de alterar
su protocolo requiere una decisión compartida antes de implementar.

## Impact

Codex: backend, proveedores, métricas, tests y benchmark. Claude: paquetes de
captura y UI provisional/final, con revisión cruzada. PR #15 de proveedores nube
se integra por separado: esta spec no presupone su aprobación ni disponibilidad.

## Non-goals

No reescribir en Rust, instalar múltiples motores a ciegas, implementar video,
diarización o lectura de labios en este cambio. Sus interfaces/extensiones se
preservan fuera del camino crítico. No prometer <1.5s ni declarar calidad por
pasar tests sintéticos. No iniciar inferencia real prolongada al escribir la spec.
