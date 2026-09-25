# Spec Delta

## ADDED Requirements

### Requirement: Ingesta independiente de la inferencia
El backend SHALL aceptar paquetes del protocolo PCM vigente independientemente
de las ventanas ASR y unidades de traducción, manteniendo muestras y tiempos.

#### Scenario: Paquetes pequeños
- **WHEN** llega el mismo audio en paquetes de 100ms en vez de 5s
- **THEN** no se ejecuta ASR obligatoriamente por cada paquete
- **AND** no se pierden ni duplican muestras por cambiar fronteras de transporte

### Requirement: Recursos reutilizables y preparación explícita
El backend SHALL reutilizar modelos y clientes HTTP, liberar recursos al cerrar
y registrar calentamiento separado de la inferencia estable.

#### Scenario: Primera sesión
- **WHEN** se solicita una sesión con modelos aún fríos
- **THEN** informa preparación sin bloquear el event loop
- **AND** no inicia consumo de audio como si el proveedor ya estuviera listo

### Requirement: Traducción progresiva versionada
El backend SHALL publicar contenido incremental real como provisional, vinculado
a la revisión fuente, y confirmar solo al completar correctamente la generación
sobre el original final vigente.

#### Scenario: Respuesta truncada
- **WHEN** el proveedor termina por límite de tokens o timeout tras emitir contenido
- **THEN** ese contenido no se confirma como traducción completa
- **AND** se informa un error sin exponer secretos

#### Scenario: Respuesta obsoleta
- **WHEN** termina una traducción basada en una revisión del original reemplazada
- **THEN** no sobrescribe ni se presenta como traducción vigente

### Requirement: Reconocimiento incremental con contexto acotado
El backend SHALL preservar audio nuevo pendiente, usar contexto acotado por sesión
y deduplicar ventanas solapadas antes de publicar texto.

#### Scenario: Término atraviesa una ventana
- **WHEN** una expresión técnica comienza en una ventana y termina en la siguiente
- **THEN** las hipótesis pueden corregirse mientras sean provisionales
- **AND** la publicación no duplica el tramo solapado ni modifica texto final

### Requirement: Decisión semántica con espera limitada
El backend SHALL decidir límites sobre hipótesis textuales y señales acústicas,
distinguir pause/semantic/deadline y limitar la espera adicional del detector.

#### Scenario: Habla continua sin cierre
- **WHEN** vence el presupuesto desde el primer contenido pendiente
- **THEN** publica la hipótesis disponible como provisional con deadline
- **AND** conserva contexto sin inventar continuación ni reiniciar indefinidamente el plazo

#### Scenario: Detener con contenido incierto
- **WHEN** termina la fuente sin evidencia suficiente para confirmar una hipótesis
- **THEN** no la convierte automáticamente a final y comunica el resultado incompleto

### Requirement: Planificación acotada y justa
El backend SHALL limitar trabajo activo y pendiente por sesión, reemplazar solo
revisiones pendientes de la misma unidad abierta y conservar el orden de unidades
cerradas distintas dentro de una cola acotada.

#### Scenario: Tres revisiones de una unidad
- **WHEN** la primera está en ejecución y llegan otras dos
- **THEN** mantiene solo la revisión pendiente más nueva de esa unidad
- **AND** no elimina una unidad distinta ni cancela continuamente el activo

### Requirement: Sobrecarga y pérdidas contabilizadas
El backend SHALL informar degradación y gaps por pérdida inevitable, limitar
memoria y contabilizar muestras descartadas sin presentarlas como optimización.

#### Scenario: Capacidad insuficiente
- **WHEN** dos sesiones producen audio más rápido que la capacidad sostenida
- **THEN** la evidencia registra atraso, pérdida y límites alcanzados
- **AND** no declara que el perfil cumple procesamiento sostenible sin pérdidas

### Requirement: Evaluación reproducible de latencia y calidad
Cada perfil candidato SHALL compararse con baseline usando el mismo audio humano
a velocidad real con una y dos sesiones, distinguiendo frío/caliente, primer
texto español, final, fidelidad, pérdidas y tendencia del backlog.

#### Scenario: Provisional más rápido pero traducción peor
- **WHEN** baja la demora inicial pero aumentan omisiones, errores o atraso final
- **THEN** se documenta el tradeoff y no se activa como perfil ganador por defecto

#### Scenario: Relojes distintos
- **WHEN** se correlacionan captura en navegador y ejecución Python
- **THEN** se usan posiciones de audio e IDs y una referencia temporal explícita
- **AND** no se restan directamente relojes monotónicos de orígenes diferentes
