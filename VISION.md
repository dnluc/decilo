# Decilo: visión de producto

Síntesis de la lluvia de ideas compartida por el usuario el 2026-09-24.
Conserva su dirección y sus capacidades propuestas; no es una transcripción
literal ni una afirmación de funcionalidades implementadas. Las decisiones
verificables y el alcance de cada entrega se mantienen en OpenSpec.

## Idea central

**No traducir bloques de audio. Traducir unidades de sentido.**

Decilo busca ser un traductor simultáneo semántico, adaptativo y multimodal
para conferencias técnicas. Debe usar contexto para decidir cuándo avanzar,
cuándo esperar y cómo expresar lo dicho con naturalidad para la audiencia.
Baja latencia percibida y múltiples sesiones concurrentes son prioridades.

Regla del usuario para ambos asistentes: construir primero el camino mínimo
funcional y luego sumar capacidades experimentales, conservando interfaces
que permitan hacerlo sin reemplazar el núcleo. No eliminar los diferenciales
solo porque un pipeline convencional resulte más sencillo.

## Capacidades que hay que preservar

### Segmentación semántica e incrementalidad

Combinar actividad de voz, pausas, entonación cuando esté disponible,
puntuación, sintaxis, estabilidad de hipótesis y contexto para encontrar
unidades de sentido de duración variable. Una pausa es una señal, no una
prueba de que terminó una idea.

El ASR produce hipótesis mientras llega audio. El sistema conserva texto
provisional revisable y confirma segmentos cuando hay evidencia suficiente.
La interfaz diferencia ambos estados sin reescribir constantemente la charla.

La traducción puede anticiparse a la finalización del original y verificarse
con contexto posterior. Su parte estable se determina de forma independiente:
estabilidad de palabras en inglés no implica estabilidad de sus posiciones en español.

### Presupuesto de latencia y dos caminos

Un controlador observa retraso respecto al audio, colas, tiempos de ASR y
traducción, recursos, sesiones y estabilidad. Ajusta contexto, frecuencia de
revisión y esfuerzo de verificación dentro de un presupuesto de calidad.

La idea incluye un camino rápido provisional y otro más preciso que verifica
y propone correcciones. Es una posibilidad experimental cuya ganancia debe
medirse contra el trabajo extra y la competencia por CPU/GPU.

El ejemplo de **menos de 1,5s** expresa una aspiración de la lluvia de ideas;
todavía hay que definir qué salida y percentil mide. No reemplaza de forma
automática la propuesta previa de **3s p95 para resultados definitivos**.
Medir aparición inicial, retraso del contenido y tiempo hasta estabilización,
además de calidad y cantidad de revisiones visibles.

### Dominio, glosario y región

Reconocer tecnologías, productos, compañías, nombres, siglas y expresiones
técnicas. Combinar glosario global, del evento y de la sesión, más una memoria
temporal acotada de contexto y correcciones, sin reentrenar modelos.

Permitir un perfil explícito como `es-AR`, `es-MX` o `es-ES`. La conservación
de anglicismos debe ser configurable por audiencia y término; una región no
determina por sí sola la preferencia de todas las personas.

Ejemplo deseado para un perfil técnico configurado:

> Before merging the PR, we need another code review.

> Antes de hacer el merge del PR, necesitamos otro code review.

Los términos aprendidos automáticamente son candidatos: una hipótesis errónea
repetida no debe convertirse sin verificación en una regla del glosario.

### Hablantes y contexto multimodal

Conservar identidad lógica de hablantes dentro de cada sesión, incluyendo
conversaciones, paneles, interrupciones y solapamientos. Admitir hablante
desconocido o atribución incierta; diarización no implica conocer su nombre.

Explorar video selectivo para contexto visual y hablante activo, usando
posición, movimiento de labios, cabeza e historial. Lectura de labios como
apoyo al reconocimiento, gestos, énfasis, risa e ironía quedan como experimentos.
Sincronizar audio y video y evaluar su contribución antes de depender de ellos.

Las señales contextuales no autorizan inventar intención ni alterar lo dicho.
Anotaciones como `[risas]`, `[aplausos]` o emojis son una capa opcional y
separada del texto. No afirmar estados psicológicos a partir de gestos.

### Contexto y presentación

Un componente lógico de contexto reúne historial, glosario, perfil regional,
hablantes, señales visuales disponibles e incertidumbre. Cada dato conserva
sesión, tiempo y procedencia; contexto y video enriquecen la traducción sin
bloquear el audio cuando no están disponibles.

La vista de audiencia permite elegir sesión e idioma, diferencia provisional
y confirmado, muestra conexión y, cuando exista evidencia, hablante. Un
indicador numérico de confianza solo tiene sentido si la medida está validada.

## Dirección tecnológica propuesta

- Python como núcleo de ingestión, buffers, sesiones y distribución. La
  implementación usa FastAPI/asyncio y faster-whisper en threads dentro del
  mismo proceso; Ollama corre como servicio y Gemini es externo. No se deduce
  aislamiento de CPU del lenguaje elegido.
- faster-whisper es el ASR local implementado: parciales `base`, finales
  `small` EN/ES al PR #22, configurables en los puntos documentados. whisper.cpp
  fue un candidato inicial, no el motor actual. Gemma `gemma3n:e2b` vía Ollama
  traduce texto; Gemini Live ofrece la alternativa de STT continuo en nube.
- Interfaces conceptuales `Transcriber`, `Translator`, `ContextProvider`,
  `SpeakerDetector` y `VisualAnalyzer`, junto con políticas reemplazables de
  segmentación y latencia. Pueden ser módulos del mismo proceso.
- Go es opcional para administración si aparece una necesidad concreta;
  no requiere crear otro servicio para la primera demo.
- Opus es una opción para cliente→servidor, decodificando una vez al formato
  interno acordado. El transporte actual usa PCM16 sobre WebSocket; Opus/WebRTC siguen siendo
  opciones futuras, evitando ciclos redundantes de compresión y descompresión.
- Colas pequeñas y acotadas, métricas, backpressure y cancelación por sesión.
  Compartir resultados de una sesión entre espectadores en vez de repetir
  inferencia por usuario. Kafka no es necesario para el primer alcance.

## Progresión deseada

| Nivel | Capacidad | Evidencia que buscar |
| --- | --- | --- |
| 1 | Audio → Python → ASR → traducción → WebSocket → subtítulo | Audio real, ES/EN, EN→ES y dos sesiones separadas |
| 2 | Transcripción incremental | Parciales reales que se estabilizan; no simular tokens de una respuesta ya terminada |
| 3 | Segmentación semántica | Comparación con segmentación temporal, incluyendo discurso sin pausas |
| 4 | Traducción especulativa | Menor espera visible sin cambios de sentido ocultos ni reescritura continua |
| 5 | Control de latencia | Recuperación ante carga, colas acotadas y calidad registrada |
| 6 | Glosario técnico | Términos y nombres del corpus conservados o traducidos según configuración |
| 7 | Regionalización | Diferencia reproducible entre perfiles explícitos |
| 8 | Múltiples hablantes | Cambios y solapamientos comparados con etiquetas de referencia |
| 9 | Video | Mejora medida frente al mismo caso con audio solo |
| 10 | Labios, gestos y otras señales | Experimentos identificados como tales y anotaciones separadas |

Estos niveles expresan el orden de construcción solicitado, no tareas ya
asignadas ni promesas de completar los diez antes del deadline. La demo debe
mostrar el camino real y los diferenciales efectivamente implementados.
Exportación SRT/VTT, overlays OBS/vMix y panel de producción también conservan
su lugar como extensiones del desafío.

## Condiciones para que los diferenciales funcionen

1. Acotar cuánto se espera por un límite semántico: si vence el presupuesto,
   emitir una unidad incompleta marcada como tal y conservar contexto.
2. No depender de una traducción terminada para decidir si se permite iniciar
   ASR. Usar hipótesis incrementales para realimentar la segmentación.
3. Versionar segmentos y vincular cada traducción a la revisión de su original.
   Descartar resultados tardíos obsoletos de cualquiera de los dos caminos.
4. Definir en el contrato cuándo se confirma texto y cómo se expresa una
   corrección excepcional: no modificar silenciosamente texto ya confirmado.
5. Acotar la especulación: más llamadas o chunks menores pueden aumentar la
   cola. Comparar siempre contra un camino único como referencia.
6. Cambiar de modelo solo si el costo de carga y la memoria lo permiten;
   incorporar histéresis para no oscilar continuamente entre estrategias.

Estas condiciones son objetivos de la visión. El contrato v1 y varios parámetros
ya existen; su aceptación completa no está acreditada. Al PR #22 hay cortes
heurísticos por oración, sin controlador semántico adaptativo; Live puede
confirmar la última provisional al cerrar/reconectar, lo que difiere del criterio
1/4 de conservar explícitamente la incertidumbre. Es una divergencia a resolver,
no una eliminación de ese objetivo. Ver [arquitectura](docs/ARQUITECTURA.md) y
[estado OpenSpec](openspec/README.md) para implementación y límites vigentes.
