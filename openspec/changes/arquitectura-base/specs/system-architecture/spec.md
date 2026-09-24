# Spec Delta

## Purpose

Define los atributos de calidad (no funcionales) exigidos al sistema
Decilo en su conjunto, para que sirvan de criterio de aceptación
transversal a las capacidades funcionales (captura de audio,
transcripción, distribución de subtítulos, vista de audiencia) que se
especifiquen en cambios posteriores.

## ADDED Requirements

### Requirement: Latencia end-to-end de subtítulos
El sistema SHALL entregar cada segmento de subtítulo en la vista de
audiencia dentro de un límite de latencia medido desde que se capturó el
audio correspondiente, para que sea utilizable siguiendo una charla en
vivo.

#### Scenario: Subtítulo dentro del límite de latencia
- **WHEN** se captura audio para una sesión activa
- **THEN** el segmento de subtítulo correspondiente SHALL estar visible en
  la vista de audiencia dentro de 3 segundos, en al menos el 95% de los
  segmentos de esa sesión

### Requirement: Escalabilidad horizontal de sesiones
El sistema SHALL soportar al menos dos sesiones simultáneas sin
degradación cruzada, y el repositorio SHALL documentar cómo escalar a más
sesiones agregando recursos (procesos, instancias del motor de inferencia)
sin rediseñar la arquitectura.

#### Scenario: Dos sesiones concurrentes independientes
- **WHEN** dos fuentes de audio independientes están activas al mismo
  tiempo
- **THEN** cada una SHALL producir sus propios flujos de
  transcripción/traducción/subtítulos sin degradación de latencia
  atribuible a la otra sesión

#### Scenario: Camino de escalado documentado
- **WHEN** una conferencia necesita correr más de dos sesiones en
  simultáneo
- **THEN** el repositorio SHALL documentar cómo agregar capacidad (por
  ejemplo, instancias adicionales del motor de inferencia) sin cambiar la
  arquitectura central

### Requirement: Aislamiento de fallos por sesión
El sistema SHALL aislar fallos de manera que un error, desconexión o
caída en el pipeline de audio/transcripción de una sesión NO SHALL
interrumpir ni degradar ninguna otra sesión activa en simultáneo.

#### Scenario: Falla una sesión, las demás continúan
- **WHEN** la fuente de audio de una sesión se desconecta o su worker de
  transcripción falla
- **THEN** las demás sesiones activas SHALL seguir produciendo subtítulos
  sin interrupción

### Requirement: Documentación de despliegue reproducible
El repositorio SHALL incluir documentación suficiente para que una
persona sin conocimiento previo del sistema pueda levantar al menos una
sesión de extremo a extremo, incluyendo qué modelos y credenciales
necesita.

#### Scenario: Levantar una sesión desde cero siguiendo el README
- **WHEN** alguien sigue las instrucciones del README sin haber visto el
  código antes
- **THEN** puede levantar una sesión con audio de prueba y ver los
  subtítulos generados, sin depender de pasos no documentados
