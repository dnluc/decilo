# Spec Delta

## Purpose

Entregar subtítulos por sesión con revisiones explícitas, relación entre
original y traducción, recuperación de conexión y límites de memoria conocidos.

## ADDED Requirements

### Requirement: Flujo por sesión y protocolo versionado
Cada suscripción SHALL entregar exclusivamente eventos de la sesión seleccionada,
con versión de protocolo, generación del flujo y orden de eventos verificables.
Un cliente NO SHALL aplicar silenciosamente una versión incompatible.

#### Scenario: Cambiar de sala
- **WHEN** una persona cambia de sesión y llega un evento tardío de la anterior
- **THEN** ese evento no modifica los subtítulos de la sesión recién seleccionada

#### Scenario: Versión no soportada
- **WHEN** el cliente recibe una versión de protocolo incompatible
- **THEN** informa incompatibilidad y deja de aplicar mensajes de ese flujo

### Requirement: Revisar texto provisional sin duplicarlo
Cada subtítulo SHALL identificar segmento, idioma, tipo y revisión creciente,
y diferenciar texto provisional de definitivo. Una revisión SHALL reemplazar
el texto anterior de la misma entrada, nunca agregarlo como un nuevo segmento.

#### Scenario: Hipótesis que evoluciona
- **WHEN** un segmento pasa de "We need" a "We need another code review"
- **THEN** la audiencia muestra una sola entrada con el texto actualizado
- **AND** solo la marca definitiva cuando llega una revisión confirmada

#### Scenario: Revisión duplicada u obsoleta
- **WHEN** llega una revisión igual o menor que la ya aplicada
- **THEN** el texto visible no retrocede ni se duplica

### Requirement: Confirmación explícita e independiente
El texto definitivo SHALL permanecer inmutable en la versión inicial del
protocolo. La confirmación del original NO SHALL confirmar automáticamente
la traducción. Un proveedor sin parciales SHALL poder emitir directamente
un resultado definitivo sin simular incrementalidad.

#### Scenario: Traducción todavía provisional
- **WHEN** el original se confirma pero su traducción aún no fue verificada
- **THEN** la audiencia mantiene la traducción identificada como provisional

#### Scenario: Corrección de un resultado ya definitivo
- **WHEN** un proveedor intenta cambiar una entrada definitiva
- **THEN** el servicio rechaza la mutación y registra el error; no reescribe
  silenciosamente el texto que la audiencia ya vio confirmado

### Requirement: Traducción vinculada a la revisión original
Cada traducción SHALL indicar qué revisión del original utilizó. Una
traducción basada en un original reemplazado NO SHALL presentarse como actual.
Solo se podrá confirmar una traducción de la revisión definitiva vigente.

#### Scenario: El ASR cambia mientras se traduce
- **WHEN** el original avanza de revisión 1 a 2 mientras se procesa una traducción de 1
- **THEN** el resultado tardío de 1 se descarta y cualquier traducción visible
  basada en 1 deja de presentarse como vigente hasta recibir una de 2

#### Scenario: Traducir un segmento confirmado
- **WHEN** llega una traducción definitiva de la revisión final vigente
- **THEN** se confirma solo la entrada del idioma correspondiente de ese segmento

### Requirement: Recuperación mediante snapshot consistente
Cada conexión o reconexión SHALL comenzar con un snapshot autoritativo del
estado y subtítulos recientes de la sesión, seguido de eventos posteriores
sin un hueco entre snapshot y suscripción. El cliente SHALL reemplazar su
estado de esa sesión con el snapshot, incluyendo revisiones provisionales.

#### Scenario: Reconectar luego de perder actualizaciones
- **WHEN** un cliente se reconecta después de que un segmento fue actualizado
- **THEN** recibe la revisión vigente y no agrega copias de la anterior

#### Scenario: Reinicio del servidor
- **WHEN** la generación del flujo cambia por pérdida del estado del servidor
- **THEN** el cliente descarta cursores y estado de la generación anterior
- **AND** informa que el historial anterior puede no estar disponible

#### Scenario: Historial acotado
- **WHEN** la sesión tiene más segmentos que la ventana retenida
- **THEN** el snapshot indica que el historial está truncado; no promete la transcripción completa

### Requirement: Fallos y sobrecarga visibles
El servicio SHALL informar degradación, errores y discontinuidades de audio
sin bloquear otras sesiones. Un cliente lento SHALL ser desconectado antes
de que su cola de entrega pueda crecer sin límite.

#### Scenario: Se descarta audio pendiente
- **WHEN** la política de sobrecarga descarta un intervalo de audio
- **THEN** los clientes ven una discontinuidad identificable y no texto inventado para cubrirla

#### Scenario: Espectador lento
- **WHEN** se llena el buffer de salida de un espectador
- **THEN** su conexión se cierra y puede recuperar el estado reciente con otro snapshot
- **AND** las demás conexiones continúan consumiendo eventos

### Requirement: Metadatos opcionales y tiempos trazables
Los subtítulos SHALL incluir su intervalo en la línea temporal del audio
de la sesión. Identidad de hablante y motivo del límite semántico podrán
estar ausentes sin impedir la entrega de texto.

#### Scenario: Todavía no hay diarización
- **WHEN** el motor produce un subtítulo sin identidad de hablante
- **THEN** la audiencia muestra el texto sin inventar un nombre o una atribución

#### Scenario: Medir un segmento traducido
- **WHEN** una traducción se entrega después del original
- **THEN** conserva la referencia al intervalo original para medir su retraso
  desde el audio, sin reiniciar el reloj al terminar la transcripción
