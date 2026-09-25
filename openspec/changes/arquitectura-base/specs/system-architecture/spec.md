# Spec Delta

## Purpose

Define los atributos de calidad (no funcionales) exigidos al sistema
Decilo en su conjunto, para que sirvan de criterio de aceptación
transversal a las capacidades funcionales (captura de audio,
transcripción, distribución de subtítulos, vista de audiencia) que se
especifiquen en cambios posteriores.

Estado: propuesta revisada por Codex el 2026-09-24. La meta numérica de
3s p95 sigue pendiente de confirmación del usuario; no es una exigencia
numérica del concurso ni un rendimiento ya demostrado.
La aspiración de <1,5s en `VISION.md` requiere acordar métrica y salida;
no sustituye esta meta provisional. Las capacidades incrementales y
multimodales tendrán sus propios requisitos en cambios posteriores.

## ADDED Requirements

### Requirement: Latencia end-to-end de subtítulos
El sistema SHALL medir la latencia de transcripción definitiva y traducción
por separado y por sesión, desde la captura de la última muestra de voz
del segmento hasta que el texto correspondiente es visible en el navegador.
La medición SHALL incluir espera de cierre de segmento, colas, procesamiento
y entrega. La meta propuesta es p95 ≤ 3 segundos en cada flujo, bajo la
configuración de capacidad documentada y con dos sesiones activas.

#### Scenario: Subtítulo dentro del límite de latencia
- **WHEN** dos sesiones procesan audio a velocidad real en régimen estable
  bajo el protocolo reproducible de `design.md`
- **THEN** al menos el 95% de los segmentos esperados de cada sesión SHALL
  tener su transcripción definitiva visible dentro de 3 segundos y el
  flujo EN→ES SHALL cumplir la misma meta para su traducción, medida desde
  el audio original, no desde que terminó el STT
- **AND** el informe SHALL identificar configuración, tamaño de muestra,
  duración de segmentos, demora desde su inicio, percentiles, pérdidas y
  tiempo de arranque; los segmentos perdidos cuentan como incumplimientos

### Requirement: Escalabilidad horizontal de sesiones
El sistema SHALL soportar al menos dos sesiones simultáneas en la
configuración de capacidad documentada, y el repositorio SHALL documentar cómo escalar a más
sesiones agregando recursos (procesos, instancias del motor de inferencia)
sin rediseñar la arquitectura.

#### Scenario: Dos sesiones concurrentes independientes
- **WHEN** dos fuentes de audio independientes están activas al mismo
  tiempo
- **THEN** cada una SHALL producir sus propios flujos de
  transcripción/traducción/subtítulos, sin mezcla de texto entre sesiones,
  cumpliendo la meta de latencia acordada bajo esa carga concurrente

#### Scenario: Camino de escalado documentado
- **WHEN** una conferencia necesita correr más de dos sesiones en
  simultáneo
- **THEN** el repositorio SHALL documentar cómo agregar capacidad (por
  ejemplo, instancias adicionales del motor de inferencia) sin cambiar la
  arquitectura central

### Requirement: Aislamiento de fallos por sesión
El sistema SHALL contener errores locales de captura o procesamiento de
una sesión para que las demás continúen bajo la capacidad documentada.
Este alcance no incluye caída del host, OOM del proceso ni caída del motor
compartido; el MVP no promete alta disponibilidad de esas dependencias.

#### Scenario: Falla una sesión, las demás continúan
- **WHEN** la fuente de audio de una sesión se desconecta o su worker
  devuelve un error o agota su timeout, con las dependencias comunes sanas
- **THEN** las demás sesiones activas SHALL seguir produciendo subtítulos
  dentro de la meta acordada y la sesión afectada SHALL mostrar su estado de error

#### Scenario: Falla el motor compartido
- **WHEN** el motor usado por varias sesiones deja de responder
- **THEN** las sesiones afectadas SHALL informar indisponibilidad sin
  presentar texto anterior como si fuera nuevo ni reintentar sin límite

### Requirement: Sobrecarga y espectadores lentos
El sistema SHALL limitar el trabajo pendiente y mostrar cualquier pérdida
de audio o interrupción que cause la sobrecarga. Un espectador lento NO SHALL
bloquear la captura ni la entrega a otros espectadores.

#### Scenario: La inferencia no alcanza la velocidad de entrada
- **WHEN** se supera la capacidad configurada o el límite de cola de una sesión
- **THEN** el sistema SHALL aplicar la política documentada de rechazo,
  pausa o descarte con discontinuidad visible, manteniendo acotada la cola

#### Scenario: Un espectador deja de consumir eventos
- **WHEN** un cliente agota su buffer de salida
- **THEN** el sistema SHALL desconectarlo o aplicar la política documentada
  de recuperación sin detener el flujo de los demás clientes

### Requirement: Evaluación reproducible de calidad
El proyecto SHALL evaluar transcripción ES/EN y traducción EN→ES con audio
representativo y referencias conocidas, incluyendo términos técnicos,
nombres, números y silencios. El glosario es opcional; evaluar calidad no lo es.

#### Scenario: Comparar un motor candidato
- **WHEN** se evalúa un motor para el MVP
- **THEN** el informe SHALL conservar entradas identificables, referencias,
  salidas reales, configuración y errores de transcripción y traducción
- **AND** una revisión manual SHALL registrar omisiones, invenciones,
  errores de nombres/números y cambios de sentido, con una conclusión de
  aptitud para la demo; la mera presencia de texto no acredita calidad

### Requirement: Documentación de despliegue reproducible
El repositorio SHALL incluir documentación suficiente para que una
persona sin conocimiento previo del sistema pueda levantar una sesión de
extremo a extremo y reproducir la prueba con dos fuentes distintas,
incluyendo hardware, versiones, modelos, credenciales y preparación offline.

#### Scenario: Levantar una sesión desde cero siguiendo el README
- **WHEN** alguien sigue las instrucciones del README sin haber visto el
  código antes
- **THEN** puede levantar una sesión con audio de prueba y ver los
  subtítulos generados, sin depender de pasos no documentados

#### Scenario: Reproducir la capacidad mínima
- **WHEN** alguien sigue la sección de prueba concurrente del README
- **THEN** puede iniciar dos fuentes distintas a velocidad real y ver sus
  subtítulos por separado, usando audios incluidos o un procedimiento
  reproducible documentado para obtenerlos y con sus permisos de uso indicados
