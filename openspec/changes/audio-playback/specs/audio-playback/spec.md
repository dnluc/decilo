# Spec Delta

## Purpose

Permitir que la vista de audiencia reproduzca el audio original de una
sesión en el navegador, sincronizado con los subtítulos vía las marcas de
tiempo (`start_ms`/`end_ms`) que ya lleva `caption-stream`.

## ADDED Requirements

### Requirement: Servir el audio de la sesión
El sistema SHALL exponer `GET /api/v1/sessions/{session_id}/audio` que
devuelve el archivo de audio de esa sesión con soporte de peticiones
`Range`, para que el navegador pueda buscar/saltar en la reproducción sin
descargar el archivo completo de nuevo.

#### Scenario: Reproducir audio de una sesión existente
- **WHEN** el navegador pide el audio de una sesión con audio disponible,
  sin header `Range`
- **THEN** el servidor responde `200` con el archivo completo y
  `Content-Type` de audio

#### Scenario: El navegador busca un punto de la reproducción
- **WHEN** el navegador pide el audio con un header `Range`
- **THEN** el servidor responde `206` con el fragmento pedido y los
  headers de rango correspondientes

#### Scenario: Sesión sin audio disponible
- **WHEN** se pide el audio de una sesión inexistente o sin fuente de
  audio configurada
- **THEN** el servidor responde `404`
