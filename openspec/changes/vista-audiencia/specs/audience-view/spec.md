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
