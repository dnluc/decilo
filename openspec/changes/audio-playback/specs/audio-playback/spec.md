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

### Requirement: Inicio de prueba audible
El modo demo local SHALL permitir iniciar una sesión preparada mediante POST
`/api/v1/sessions/{id}/start`, con un único worker por sesión y límite de dos
workers activos. El navegador SHALL pedir el inicio tras comenzar el audio.

#### Scenario: Iniciar dos veces
- **WHEN** se repite start en una sesión live
- **THEN** responde con la misma sesión sin crear otro worker

#### Scenario: Repetir una prueba
- **WHEN** se pide POST `/api/v1/sessions/{id}/runs`
- **THEN** se crea una sesión starting con ID nuevo y el mismo audio
- **AND** no se mezclan los subtítulos de la sesión anterior

#### Scenario: Presupuesto de recursos agotado
- **WHEN** hay dos workers activos al iniciar otro, o 20 sesiones con audio al crear otra
- **THEN** devuelve 429 sin iniciar trabajo adicional

#### Scenario: Reproducción local alterada
- **WHEN** se pausa o busca en el reproductor
- **THEN** la interfaz informa que la inferencia sigue y la reproducción ya no representa el ritmo original de la prueba
