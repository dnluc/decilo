# Decilo — borrador local actualizado para Devpost

**Base de este texto:** PRs #21/#22 (`e4b9f90`), 25/09/2026. Este borrador
actualiza la documentación del repositorio; **no se ha copiado al formulario**
en esta tarea y no se realizó envío final.

La última comprobación externa registrada fue **DRAFT, 4/5 steps done**, con
video vacío. Nombre, pitch, historia y campos adicionales se habían guardado
sobre versiones anteriores (`0bbdfd9`/`c884ebe`); país y aceptación fueron
confirmados por el usuario. Ese estado es histórico, no una consulta actual.
[Seguimiento](../openspec/changes/entrega-devpost/tasks.md).

[Formulario de Decilo](https://devpost.com/submit-to/31268-nerdearla-vibeathon-2026/manage/submissions/1196509-decilo/project-overview).
Evento: [Nerdearla Vibeathon 2026](https://nerdearla26.devpost.com/).

## Nombre del proyecto

Decilo

## Descripción breve

Subtítulos para que más personas puedan seguir una charla técnica. Un proyecto abierto de transcripción y traducción para conferencias.

## Inspiración

Una charla técnica puede abrirte una puerta, pero el idioma o la dificultad para
seguir el audio pueden dejarte afuera. Decilo nace para ayudar a que más personas
puedan participar de conferencias como Nerdearla y elegir cómo seguir cada charla.
Queremos que los organizadores puedan operar una solución abierta, adaptable y
pensada desde el principio para varios escenarios.

## Qué hace

Decilo toma audio autorizado de una pestaña del navegador y genera subtítulos
originales en inglés o español y traducción de inglés a español. Se puede
reproducir una charla de YouTube, elegir procesamiento local o nube y compartir
la pestaña con audio. Cada captura crea su sesión; otras audiencias pueden
adjuntarse al mismo ID sin repetir inferencia.

La interfaz muestra texto provisional que se revisa y confirma, con historial
reciente, controles de lectura y recuperación por snapshot. Cuando todavía falta
una traducción, muestra el original con estilo provisional. Hay detección inicial
EN/ES opcional y cortes inferidos por oración para oradores sin pausas claras.

El camino local usa Whisper; el de nube usa Gemini Live. La capacidad mínima
se administra con un límite nominal de dos trabajos activos, con una reserva
pendiente durante autodetección. Todavía falta aceptación sostenida de calidad
y latencia con dos charlas humanas. Español→inglés, otros idiomas, diarización
y contexto visual son ampliaciones previstas, no funcionalidades demostradas.

## Cómo lo construimos

Construimos la interfaz con JavaScript, HTML y CSS, usando Vite para desarrollo y
generación de archivos estáticos. Separamos la presentación, el estado de los
subtítulos y el cliente HTTP/WebSocket. El protocolo versiona los segmentos y
vincula cada traducción a la revisión del original, para evitar mostrar una
traducción desactualizada cuando cambia la transcripción. El cliente recupera
el estado mediante snapshots después de una desconexión o un salto de secuencia.

El backend usa Python, FastAPI, asyncio y un contrato v1 de eventos. El audio
viaja en PCM16 mono a 16 kHz, en paquetes de 100 ms. Localmente usa
faster-whisper base para parciales y small para finales EN/ES, con Gemma 3n e2b
en Ollama para traducir. En nube, Gemini Live transcribe de forma continua y
Gemini REST traduce los originales cerrados. Los defaults del código son
`gemini-3.5-transcribe-live` y `gemini-3.5-flash-lite`, con configuración por entorno.

La autodetección sigue usando Whisper local aun en nube. Hay fallback inicial
de Live a Gemini por segmentos, no cambio oculto de nube a local. Las claves
permanecen en el backend. Colas y revisiones evitan trabajo/publicación sin límites,
pero el estado no es durable ni la arquitectura es ya un scheduler distribuido.

Usamos OpenSpec para acordar contratos y registrar decisiones, avances y
validaciones. Claude y Codex colaboran en worktrees separados, con reparto por
componente y revisión cruzada prevista antes de integrar código.

## Desafíos

Los subtítulos necesitan conservar el orden y el sentido mientras llegan nuevas
revisiones, traducciones y reconexiones. Implementamos invalidación de traducciones
obsoletas, descarte de eventos de conexiones anteriores y recuperación de estado
para que cambiar de charla no mezcle contenidos.

Otro desafío es separar mejora percibida de fidelidad. Los cortes locales usan
pausas y límites textuales inferidos; Live puede cerrar texto antes de la final
oficial. Esas decisiones reducen espera en algunos casos pero requieren evaluar
calidad, tiempos y correcciones. Las mediciones históricas se conservan con sus
modelos, sin presentarlas como garantía de la configuración nueva.

## Logros

Integramos captura real de pestaña, proveedor por sesión, STT provisional/final,
traducción, snapshots y una UI de lectura. La CI ejecuta pruebas Python/Node,
compilación/build y navegador/integración con inferencia simulada. El repositorio
conserva pruebas cortas con modelos reales y avances registrados de Gemini Live;
esos registros no reemplazan la evaluación larga con dos fuentes humanas.

## Qué aprendimos

La calidad de los subtítulos también depende de cómo se presentan: conservar
texto confirmado, distinguir una traducción pendiente y avisar de una interrupción
ayuda a seguir la charla. Separar el contrato del motor permitió construir y
probar esa experiencia en paralelo al desarrollo del procesamiento de audio.

También aprendimos a tratar las metas de latencia como hipótesis que deben
medirse. La arquitectura y los tests de interfaz no sustituyen una prueba del
recorrido completo con audio real.

## Próximos pasos

Completar la validación de dos sesiones simultáneas con audio hasta el navegador
y publicar instrucciones reproducibles y mediciones de calidad y latencia.
Ampliar la configuración de origen y destino con traducción español a inglés
y más idiomas, conservando inglés a español como parte del alcance inicial.
Después queremos validar los cortes heurísticos hacia unidades de sentido, añadir glosarios técnicos,
perfiles regionales y control adaptativo del retraso. Diarización y contexto
visual forman parte de la exploración futura, no de las capacidades demostradas.

## Tecnologías

Implementadas en el frontend: JavaScript, HTML, CSS, Vite, WebSocket.
Herramientas de verificación: Node.js, Playwright. Especificación: OpenSpec.

Backend implementado: Python, FastAPI, asyncio, faster-whisper, Whisper, Ollama,
Gemma 3n (`gemma3n:e2b`), Gemini Live, Gemini REST y WebSocket. Traducción actual: inglés a español.

## Enlaces y materiales

- Repositorio indicado por el README: https://github.com/dnluc/decilo
- Licencia del repositorio: Apache-2.0.
- Video demo v2 publicado (25/09/2026), no listado: https://youtu.be/mrHqqAIPJkQ
  Voz argentina, música original, subtítulos EN y dos sesiones en nube. Falta
  incorporar el enlace al formulario: no se modificó Devpost durante la subida.
- Sitio público: no se encontró una URL de despliegue en el checkout.
- Imágenes y logo disponibles en [material de demo](DEMO.md); falta cargarlos
  en la galería del formulario.
- Equipo existente en Devpost conservado sin cambios. País: Argentina,
  confirmado por el usuario.

Etiquetas guardadas en la última revisión externa (todavía sin actualizar las de Gemini): javascript, html5, css3, vite, websocket,
node.js, playwright, openspec, python, fastapi, faster-whisper, ollama, gemma.

## Revisión necesaria antes de la entrega final

Las [bases del evento](https://nerdearla26.devpost.com/) exigen un proyecto
funcional, repositorio público con instrucciones y licencia abierta, y video de
1–2 minutos en YouTube con audio real. El MVP debe transcribir, traducir EN→ES,
mostrar subtítulos y procesar al menos dos sesiones simultáneas. El cierre es el
25/09/2026 a las 15:00 UTC (12:00 de Argentina).

Actualizar este texto al completar la validación conjunta. Verificar acceso público al
repositorio, instrucciones completas y video. No presentar como resultados
medidos los objetivos de 3s p95 o menos de 1,5s, ni las pruebas sintéticas como
validación de una charla humana. El README y la arquitectura describen las rutas
actuales y sus límites; revisar material de demo real antes del envío.
