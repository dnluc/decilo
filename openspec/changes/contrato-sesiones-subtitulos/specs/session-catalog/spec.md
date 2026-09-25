# Spec Delta

## Purpose

Permitir que la audiencia descubra sesiones, seleccione una y conozca sus
idiomas y estado sin depender del proveedor de transcripción o traducción.

## ADDED Requirements

### Requirement: Consultar sesiones e idiomas
El servicio SHALL ofrecer un catálogo de sesiones con identificador estable,
título, idioma original, idiomas de traducción disponibles y estado actual.
El identificador SHALL ser único y no reutilizarse para una charla diferente.

#### Scenario: Dos sesiones disponibles
- **WHEN** hay dos sesiones configuradas y la audiencia consulta el catálogo
- **THEN** recibe ambas con identificadores distintos y sus idiomas disponibles
- **AND** puede consultar individualmente cada sesión sin obtener datos de la otra

#### Scenario: No hay sesiones
- **WHEN** no existen sesiones configuradas
- **THEN** el catálogo devuelve una lista vacía como resultado exitoso

#### Scenario: Sesión inexistente
- **WHEN** se consulta un identificador desconocido
- **THEN** el servicio responde con un error de sesión no encontrada

### Requirement: Distinguir estado de sesión y conexión
El sistema SHALL distinguir inicio, transmisión activa, degradación, error
y finalización de la sesión. La audiencia SHALL diferenciar estos estados
de su propia desconexión de red. El silencio por sí solo NO SHALL indicar error.

#### Scenario: Silencio durante una charla
- **WHEN** una fuente conectada no contiene voz durante un intervalo
- **THEN** la sesión sigue activa y no genera subtítulos inventados para aparentar actividad

#### Scenario: Error limitado a una sesión
- **WHEN** una fuente deja de funcionar mientras otra sesión continúa
- **THEN** la sesión afectada informa el error y la otra conserva su estado independiente

#### Scenario: Termina la charla
- **WHEN** una sesión termina
- **THEN** la audiencia ve su estado final y conserva el historial reciente disponible
- **AND** una nueva charla utiliza un identificador de sesión nuevo
