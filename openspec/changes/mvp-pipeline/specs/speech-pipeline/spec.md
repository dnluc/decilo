# Spec Delta

## Purpose

Produce transcripción y traducción en tiempo real a partir de audio de una
sesión, respetando el contrato de eventos de `caption-stream` y los drivers
de `system-architecture`, para alimentar la vista de audiencia sin acoplarse
a su implementación.

## ADDED Requirements

### Requirement: Transcripción del idioma original
El sistema SHALL transcribir el audio de una sesión en su idioma original
(ES o EN) usando el motor de STT seleccionado, emitiendo el resultado como
evento `caption.upsert` de `kind: transcript` según `caption-stream`.

#### Scenario: Transcribir audio de prueba en inglés
- **WHEN** se reproduce un archivo de audio de prueba en inglés para una sesión
- **THEN** el sistema emite al menos un evento `caption.upsert` de tipo
  `transcript`, `language: en`, con texto no vacío correspondiente al
  contenido hablado

### Requirement: Traducción EN→ES vinculada al original
El sistema SHALL traducir a español cada segmento transcripto en inglés,
referenciando la revisión del original utilizada, según `caption-stream`.

#### Scenario: Traducir un segmento confirmado
- **WHEN** un segmento en inglés se marca `final`
- **THEN** el sistema emite una traducción `final` en español para ese
  segmento, con `source_revision` apuntando a la revisión del original usada

#### Scenario: El original cambia mientras se traduce
- **WHEN** el original de un segmento avanza de revisión mientras su
  traducción está en curso
- **THEN** el sistema descarta la traducción basada en la revisión anterior
  y no la publica como vigente

### Requirement: Aislamiento de fallos por sesión
El pipeline SHALL contener una falla de captura o inferencia de una sesión
sin afectar el procesamiento de otras sesiones activas.

#### Scenario: Falla la fuente de audio de una sesión
- **WHEN** la fuente de audio de una sesión se interrumpe
- **THEN** el sistema emite `session.error` o `session.gap` para esa sesión
- **AND** las demás sesiones activas continúan procesando sin interrupción

### Requirement: Entrada reproducible desde archivo
El sistema SHALL aceptar un archivo de audio como fuente de una sesión,
para permitir pruebas reproducibles sin depender de un micrófono en vivo.

#### Scenario: Iniciar sesión desde archivo de audio
- **WHEN** se configura una sesión con un archivo de audio incluido en el
  repositorio
- **THEN** la sesión pasa a estado `live` y comienza a emitir transcripción

### Requirement: Manejo de sobrecarga por sesión
El pipeline SHALL aplicar los límites de cola definidos en
`contrato-sesiones-subtitulos` cuando la inferencia no alcanza la
velocidad de entrada de audio.

#### Scenario: Inferencia más lenta que el audio entrante
- **WHEN** el tiempo de procesamiento supera de forma sostenida la
  duración del audio entrante
- **THEN** el sistema aplica la política de descarte/pausa documentada y
  publica un `session.gap` en vez de acumular retraso sin límite
