# Proposal

> **Lectura al 25/09/2026, PR #22 (`e4b9f90`):** La UI vigente es captura de pestaña, video y dock. El catálogo visual y ?demo=1 pertenecen a una versión anterior; el reductor y contrato v1 continúan en uso.
> [Estado global, divergencias y evidencia](../../README.md).

## Why

El contrato de sesiones y subtítulos está aceptado; falta una vista que permita
seguir una charla e interpretar correctamente sus revisiones y desconexiones.
Construirla contra fixtures permite avanzar junto al backend de Claude.

## What Changes

- Cliente web de sesiones, idiomas y subtítulos del protocolo v1.
- Recuperación por snapshot, avisos de conexión e historial acotado.
- Muestra explícita sin modelos, pruebas automatizadas y build estático.

## Capabilities

### New Capabilities
- `audience-view`: lectura accesible de las sesiones y sus subtítulos.

### Modified Capabilities
Ninguna. Implementa `session-catalog` y `caption-stream` sin cambiar su contrato.

## Impact

Archivos propios en `frontend/` y workflow `audience.yml`. No cambia dependencias
Python ni código del backend. Codex implementa, Claude revisa antes de integrar.
