## ADDED Requirements

### Requirement: Selección y lectura accesible
La vista SHALL permitir elegir sesión e idioma habilitado, mostrar texto como
texto y diferenciar provisional, definitivo y traducción pendiente.

#### Scenario: Cambiar de idioma
- **WHEN** la persona cambia a un idioma de traducción habilitado
- **THEN** ve las traducciones vigentes ordenadas por audio o un estado pendiente
- **AND** no se muestran traducciones basadas en una revisión reemplazada

### Requirement: Recuperación visible sin mezcla de sesiones
La vista SHALL implementar la recuperación por snapshot del contrato v1 y
separar la desconexión local del estado de la sesión.

#### Scenario: Evento tardío de otra conexión
- **WHEN** llega un evento de una conexión anterior tras cambiar de sesión
- **THEN** no modifica el estado ni los subtítulos actuales

### Requirement: Muestra identificada
La muestra sin backend SHALL identificarse como simulación y requerir una
selección explícita del usuario.

#### Scenario: Backend no disponible
- **WHEN** falla la consulta del catálogo real
- **THEN** se informa el error con una opción de reintento sin presentar fixtures

### Requirement: Lectura adaptable sin interrumpir la sesión
La audiencia SHALL poder ampliar el texto y ocultar elementos ajenos a la
lectura sin reiniciar la suscripción. El modo de lectura SHALL conservar los
avisos de conexión y de simulación, y ofrecer una salida por botón y teclado.

#### Scenario: Ampliar texto y seguir recibiendo eventos
- **WHEN** la persona elige texto grande y activa Solo subtítulos
- **THEN** las actualizaciones continúan en la misma sesión y conexión
- **AND** puede volver al catálogo con el botón visible o Escape

#### Scenario: Preferencia local no disponible
- **WHEN** el navegador impide guardar preferencias
- **THEN** los controles siguen funcionando durante la visita sin bloquear la lectura
