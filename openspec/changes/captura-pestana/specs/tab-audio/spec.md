## ADDED Requirements

> **Lectura al 25/09/2026, PR #22 (`e4b9f90`):** Ingreso actual de 100 ms, provider por captura y language auto/en/es. Hay caminos distintos Live y por segmentos; consultar design.md actualizado para sus límites.
> [Estado global, divergencias y evidencia](../../../../README.md).

### Requirement: Capturar audio de pestaña
El sistema SHALL capturar solo audio autorizado y mostrar subtítulos nuevos.

#### Scenario: Permiso sin audio
- **WHEN** el navegador devuelve un stream sin pista de audio
- **THEN** libera las pistas y muestra un mensaje sin iniciar inferencia

#### Scenario: Cola llena
- **WHEN** el camino por segmentos excede su presupuesto de audio pendiente
- **THEN** descarta segmentos antiguos y publica session.gap overload
- **AND** el presupuesto depende de la segmentación configurada; Live tiene otro flujo

#### Scenario: Detener captura
- **WHEN** el usuario pulsa Detener
- **THEN** libera la captura local y finaliza la sesión tras procesar lo pendiente

#### Scenario: Datos inválidos
- **WHEN** llegan frames fuera de formato, tamaño u orden
- **THEN** rechaza la entrada y finaliza la sesión sin procesar esos datos

### Requirement: Selección aislada de proveedor
El sistema SHALL aplicar la selección explícita local/nube a la transcripción
y traducción de una captura sin modificar otras sesiones ni el entorno global.

#### Scenario: Elección explícita
- **WHEN** se abre una captura con provider=local o provider=gemini
- **THEN** sus workers conservan ese proveedor en ambas etapas durante toda la captura

#### Scenario: Cliente sin selección
- **WHEN** se abre una captura sin el parámetro provider
- **THEN** cada etapa conserva el proveedor configurado en el entorno del backend

#### Scenario: Nube sin credenciales
- **WHEN** una captura necesita Gemini y no hay clave configurada
- **THEN** el backend rechaza la conexión con código 4403 antes de iniciar inferencia

#### Scenario: Preparación local fallida
- **WHEN** los modelos locales no están listos y una captura elige Gemini
- **THEN** la preparación local no bloquea esa captura de nube

### Requirement: Ruteo de captura en nube
El sistema SHALL seleccionar Live para STT Gemini si está habilitado y conservar
el contrato v1 de audiencia con independencia del proveedor de reconocimiento.

#### Scenario: Live desactivado
- **WHEN** DECILO_GEMINI_LIVE es 0 y se selecciona Gemini
- **THEN** la captura procesa segmentos mediante Gemini REST

#### Scenario: Falla de setup Live
- **WHEN** la conexión inicial Live no puede completarse
- **THEN** se informa un error y se continúa por segmentos con el proveedor Gemini
- **AND** no se afirma con este fallback una recuperación sin pérdidas durante una sesión Live ya iniciada
