## ADDED Requirements

### Requirement: Capturar audio de pestaña
El sistema SHALL capturar solo audio autorizado y mostrar subtítulos nuevos.

#### Scenario: Permiso sin audio
- **WHEN** el navegador devuelve un stream sin pista de audio
- **THEN** libera las pistas y muestra un mensaje sin iniciar inferencia

#### Scenario: Cola llena
- **WHEN** hay dos bloques pendientes y llega otro
- **THEN** descarta el más antiguo y publica session.gap overload

#### Scenario: Detener captura
- **WHEN** el usuario pulsa Detener
- **THEN** libera la captura local y finaliza la sesión tras procesar lo pendiente

#### Scenario: Datos inválidos
- **WHEN** llegan frames fuera de formato, tamaño u orden
- **THEN** rechaza la entrada y finaliza la sesión sin procesar esos datos
