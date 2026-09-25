# Decilo — borrador para Devpost

Revisión inicial del 24/09/2026 sobre `0bbdfd9`, actualizada el 25/09/2026
con el pipeline disponible en `c884ebe`. Contenido guardado en
el borrador de Devpost: nombre, descripción breve, historia (Inspiración hasta
Próximos pasos), tecnologías y repositorio. También se guardaron los campos
adicionales de repositorio, stack, Argentina y aceptación de términos de la
Vibeathon; el usuario confirmó explícitamente país y aceptación.

Estado verificado mediante una segunda carga: **DRAFT, 4/5 steps done**.
El usuario confirmó que todavía no tiene video. No se hizo el envío final.

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

Decilo es un proyecto abierto de transcripción y traducción para conferencias.
Cada sesión tiene un idioma de origen configurado y cada espectador elige la
charla y el idioma de los subtítulos entre las salidas disponibles. La visión
es ampliar los idiomas de origen y destino que puede ofrecer cada sesión.

El alcance inicial cubre transcripción en el idioma original, español o inglés,
y traducción de inglés a español, el par obligatorio del MVP de la Vibeathon.
Español a inglés y otros pares, como portugués, son ampliaciones previstas y
permitidas por las bases; todavía no se presentan como traducciones implementadas.

La vista web distingue subtítulos provisionales y confirmados, conserva un
historial reciente y muestra avisos de conexión. Se adapta a móviles y ofrece
tamaños de texto ajustables y un modo de lectura centrado en los subtítulos.
El pipeline actual procesa archivos de audio por segmentos y produce
transcripciones y traducciones confirmadas. Su validación completa con dos
sesiones hasta el navegador y la medición de latencia siguen pendientes.
La interfaz también ofrece una muestra rotulada con textos sintéticos,
independiente del procesamiento de audio.

## Cómo lo construimos

Construimos la interfaz con JavaScript, HTML y CSS, usando Vite para desarrollo y
generación de archivos estáticos. Separamos la presentación, el estado de los
subtítulos y el cliente HTTP/WebSocket. El protocolo versiona los segmentos y
vincula cada traducción a la revisión del original, para evitar mostrar una
traducción desactualizada cuando cambia la transcripción. El cliente recupera
el estado mediante snapshots después de una desconexión o un salto de secuencia.

El backend está implementado con Python y FastAPI. Usa Whisper mediante
faster-whisper para transcribir archivos de audio y Gemma 3n (`gemma3n:e2b`)
servido por Ollama para traducir de inglés a español. Las sesiones declaran su
idioma de origen y las salidas disponibles; el selector de audiencia consume
esa información. Ofrecer un nuevo destino requiere que el traductor lo soporte
y validar su calidad, además de mostrarlo en la interfaz.

Usamos OpenSpec para acordar contratos y registrar decisiones, avances y
validaciones. Claude y Codex colaboran en worktrees separados, con reparto por
componente y revisión cruzada prevista antes de integrar código.

## Desafíos

Los subtítulos necesitan conservar el orden y el sentido mientras llegan nuevas
revisiones, traducciones y reconexiones. Implementamos invalidación de traducciones
obsoletas, descarte de eventos de conexiones anteriores y recuperación de estado
para que cambiar de charla no mezcle contenidos.

Otro desafío fue distinguir las capacidades de un modelo de las que expone su
runtime: la comprobación documentada de Gemma 3n en Ollama mostró entrada de texto,
sin audio. Por eso el diseño separa reconocimiento de voz y traducción. El
siguiente desafío es medir calidad y latencia con dos sesiones simultáneas
hasta el navegador. La segmentación actual por ventanas fijas puede cortar
palabras y degradar la transcripción en los bordes; mejorar esos cortes es
parte del trabajo pendiente.

## Logros

Tenemos una vista de audiencia, un pipeline de audio implementado y un contrato
compartido que contempla revisiones, traducciones, fallos y reconexión. La
interfaz incluye controles de lectura, navegación por teclado y avisos visibles
de interrupciones. El desarrollo del backend registra pruebas con Whisper y
Ollama ejecutando inferencia sobre archivos de audio. En la revisión del
frontend del 24 de septiembre, `npm test` y `npm run build` finalizaron
correctamente; las pruebas de navegador registradas cubren móvil, cambios de
sesión e idioma y reconexiones con una API simulada. Falta completar la
validación conjunta y demostrar el rendimiento bajo carga concurrente.

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
Después queremos avanzar hacia unidades de sentido, glosarios técnicos,
perfiles regionales y control adaptativo del retraso. Diarización y contexto
visual forman parte de la exploración futura, no de las capacidades demostradas.

## Tecnologías

Implementadas en el frontend: JavaScript, HTML, CSS, Vite, WebSocket.
Herramientas de verificación: Node.js, Playwright. Especificación: OpenSpec.

Backend implementado: Python, FastAPI, faster-whisper, Whisper, Ollama,
Gemma 3n (`gemma3n:e2b`). Traducción actual: inglés a español.

## Enlaces y materiales

- Repositorio indicado por el README: https://github.com/dnluc/decilo
- Licencia del repositorio: Apache-2.0.
- Video demo: pendiente de URL de YouTube con audio real; el usuario confirmó
  que no lo tiene todavía. Campo vacío en Devpost.
- Sitio público: no se encontró una URL de despliegue en el checkout.
- Imágenes: pendientes de elegir según los campos del formulario.
- Equipo existente en Devpost conservado sin cambios. País: Argentina,
  confirmado por el usuario.

Etiquetas de «Built with»: javascript, html5, css3, vite, websocket,
node.js, playwright, openspec, python, fastapi, faster-whisper, ollama, gemma.

## Revisión necesaria antes de la entrega final

Las [bases del evento](https://nerdearla26.devpost.com/) exigen un proyecto
funcional, repositorio público con instrucciones y licencia abierta, y video de
1–2 minutos en YouTube con audio real. El MVP debe transcribir, traducir EN→ES,
mostrar subtítulos y procesar al menos dos sesiones simultáneas. El cierre es el
25/09/2026 a las 15:00 UTC (12:00 de Argentina).

Actualizar este texto al completar la validación conjunta. Verificar acceso público al
repositorio, instrucciones completas y video. No presentar como resultados
medidos los objetivos de 3s p95 o menos de 1,5s, ni la muestra sintética como
prueba del pipeline. El README raíz contiene afirmaciones de ejecución local
completa y escalado que todavía no están respaldadas por este checkout.
