# Demo de Decilo — Nerdearla Vibeathon 2026

Producción iniciada el 25/09/2026 sobre `370d9ba` (PR #24).
Pedido: video de **como máximo dos minutos**, logo, carátulas, arquitectura,
capturas reales y demostración de varias sesiones. Idioma confirmado por el
usuario: **voz argentina y subtítulos en inglés**.

**Video publicado:** [ver demo en YouTube](https://youtu.be/mrHqqAIPJkQ), canal @dnluc,
visibilidad no listado. Versión con música y narración v2.

**Nueva grabación v3:** solicitada tras el PR #25. Ver la revisión al final
de este documento; conserva la publicación v2 y sus resultados históricos.

## Montaje final: 1 minuto 55 segundos

| Tiempo | Imagen / acción | Qué demuestra |
| --- | --- | --- |
| 00:00–00:06 | Logo y carátula «Que ninguna idea quede afuera» | Nombre y propósito |
| 00:06–00:16 | Presentación breve | Accesibilidad, transcripción EN/ES y traducción EN→ES |
| 00:16–00:31 | Aplicación con charla en español, modo local | Whisper local; Gemma/Ollama para el caso EN→ES |
| 00:31–00:46 | Aplicación con charla en inglés, modo nube | Gemini Live y traducción incremental |
| 00:46–01:10 | Dos sesiones en nube, sincronizadas en una toma continua | Dos fuentes diferentes procesadas simultáneamente |
| 01:10–01:23 | Charla en español en local y en nube | Transcripción original ES en ambos proveedores |
| 01:23–01:45 | Diagrama sencillo de arquitectura | Audio → backend → motor local/nube → audiencias |
| 01:45–01:55 | Carátula final, licencia y repositorio | Cómo probar y encontrar el proyecto |

Reservar intervalos sin narración para escuchar la charla original. En la
demostración simultánea, el montaje puede dejar audible una sola fuente para
que se entienda; ambas capturas deben seguir recibiendo su audio. Mantener la
velocidad real durante las tomas que demuestran procesamiento/latencia.

## Fuentes elegidas por el usuario

Metadatos públicos consultados en YouTube. La posición de preparación está
75 segundos antes de la mitad: al grabar después de acumular historial, el
video ya está cerca de su punto medio.

| Video | Idioma declarado por YouTube | Duración | Inicio de preparación | Uso |
| --- | --- | --- | --- | --- |
| [Human-Centric Engineering — Ben Popplestone](https://www.youtube.com/watch?v=7rteJoZSSzo) | Inglés (`en-US`) | 23:39 | 10:34 | Ejemplo adicional local; el enlace fue indicado inicialmente como español |
| [Data Modeling — Scott Sosna](https://www.youtube.com/watch?v=GVadbxHks_A) | Inglés (`en-US`) | 26:04 | 11:47 | Prueba local EN→ES y simultaneidad en nube |
| [¿Qué sabe un LLM del negocio? — Jesica Romero y Marilina Trevisan](https://www.youtube.com/watch?v=Emv8SiDtPkI) | Español (`es-US`) | 18:28 | 07:59 | Transcripción ES en local y nube |
| [Developers Documentation — Frédéric Harper](https://www.youtube.com/watch?v=d1TZv_CjSTY) | Inglés (`en-US`) | 38:51 | 18:10 | Nube EN→ES y simultaneidad |

Dos vistas de una misma sesión prueban distribución a espectadores. Para
demostrar dos procesamientos deben existir **dos sesiones de captura con IDs
distintos y fuentes distintas**, activas en un intervalo común. No es necesario
tener cuatro inferencias simultáneas: el MVP exige dos y el backend limita dos
trabajos nominales.

## Guion de narración

**Portada:** ¡Decilo! Subtítulos en vivo. ¡Que ninguna idea quede afuera!

**Propósito:** ¡El idioma no debería dejarte afuera de una conferencia! Decilo transcribe inglés y español, y traduce del inglés al español.

**Local:** ¡Así de fácil! Pegás el enlace, elegís el idioma y compartís el audio de la pestaña. Whisper transcribe en tu máquina; si el audio está en inglés, Gemma lo traduce al español.

**Nube:** ¿Preferís usar la nube? Seleccionás Gemini. El audio se transcribe en vivo y la traducción aparece de forma incremental, mientras el historial conserva lo que vas escuchando.

**Simultaneidad:** ¡Y mirá esto! Dos charlas distintas traduciéndose al mismo tiempo en la nube. Cada sesión mantiene su propio audio y sus subtítulos. Más espectadores pueden seguir una misma sesión sin duplicar la inferencia.

**Español:** ¡También funciona con charlas en español! Probamos local y nube. En este caso, mostramos la transcripción original.

**Arquitectura:** El navegador envía audio al backend en Python. Ahí se elige el motor local o Gemini, se coordinan las sesiones y se distribuyen los subtítulos por WebSocket. La arquitectura separa procesamiento y audiencia.

**Cierre:** ¡Decilo es open source! Con licencia Apache dos punto cero. Encontrá el código en GitHub. ¡Probalo y sumate!

El montaje usa las tomas completadas y conserva las limitaciones en la evidencia.
La voz es sintética `es-AR-ElenaNeural`; la traducción inglesa del guion es
editorial. No atribuir esos subtítulos en inglés a Decilo: ES→EN sigue fuera
del alcance implementado.

## Requisitos del evento y evidencia necesaria

Revisados en el [overview oficial de Devpost](https://nerdearla26.devpost.com/)
el 25/09/2026. El enlace separado de reglas devolvió una verificación de
navegador; esta revisión cubre los requisitos públicos visibles del overview.

- Video entre uno y dos minutos, mostrando el proyecto con audio real y su
  interacción; entregar enlace a YouTube. Una edición de 115 s deja margen.
- Audio entrante, transcripción original y traducción EN→ES visibles.
- Al menos dos sesiones simultáneas; documentar cómo escalar en README.
- Repositorio público, licencia abierta e instrucciones de instalación/modelos.
- Proyecto construido durante el 24–25/09/2026. El historial de desarrollo
  respalda fechas; no reemplaza la evaluación de los organizadores.
- Enviar por Devpost antes del 25/09/2026, 15:00 UTC / 12:00 Argentina.

Los subtítulos en inglés para el jurado son una recomendación de las bases.
No hace falta fingir capacidades de diarización, video contextual, cinco
escenarios o traducción ES→EN para cubrir el MVP. Los criterios incluyen calidad,
latencia, escalabilidad, facilidad de operación e innovación.

## Material y verificación

Material de trabajo local: `~/Videos/decilo-demo/`. Las grabaciones de las
charlas, pistas de audio y archivos de edición no se suben enteros a Git.
Las carátulas y el logo extienden la marca existente `decilo✳` y su azul.

La captura automática usa Chrome, la interfaz real y `getDisplayMedia` para
compartir únicamente la pestaña de cada ejemplo. Conserva eventos reales del
backend y la pista capturada, para contrastar pantalla, fuente y sesión. No
inyecta subtítulos ni utiliza fixtures para fabricar historial.

Antes de exportar: verificar duración con ffprobe, escuchar audio de charla y
narración, comprobar legibilidad de ambos idiomas y sincronía. Conservar una
toma continua común a las dos fuentes. El video editado es una demo breve;
no acredita el benchmark de latencia/calidad sostenida pendiente en OpenSpec.

La publicación en YouTube y el envío final a Devpost son pasos separados del
montaje local.

## Hallazgos de preparación

- El primer intento automatizado capturaba silencio: Playwright incluía
  `--mute-audio`. Se quitó ese argumento y se verificó señal real.
- Otra toma se interrumpió al apagarse los servidores compartidos. No se usa
  como evidencia de funcionamiento ni se rellena artificialmente su historial.
- El backend local en NixOS necesitaba `libstdc++.so.6` y `libz.so.1` en
  `LD_LIBRARY_PATH`; se corrigió solo el entorno de ejecución de la demo.
- La toma mixta EN local + EN nube produjo transcripciones/traducciones, pero
  registró 18 gaps por sobrecarga local y ninguno en nube. No demuestra que
  ambas rutas cumplan una meta de latencia. Por eso la simultaneidad principal
  se graba con dos fuentes EN en nube, y el modo local se muestra aparte.
- Se usa frontend compilado (`npm run build`, correcto) para evitar recargas
  del servidor de desarrollo durante la captura.

## Resultado y archivos publicados

Video local final: `~/Videos/decilo-demo/Decilo-demo-1m55-con-musica.mp4`. Duración medida
con ffprobe: **115,000 s**, 1920×1080, 30 fps, H.264 + AAC, tamaño verificado en el manifiesto local.
La galería y el paquete de entrega están en esa misma carpeta. El MP4 no se
versiona en Git. La versión v2 ya está publicada en YouTube como no listado;
la presentación de Devpost fue completada y al cerrar la verificación se
observó SUBMITTED, 5/5. Codex no pulsó Submit.

| Prueba real | Originales finales | Traducciones finales | Gaps | Errores publicados |
| --- | ---: | ---: | ---: | ---: |
| EN local, Data Modeling, junto a nube | 11 | 11 | 18 por sobrecarga | 0 |
| EN nube, documentación, junto a local | 15 | 14 | 0 | 0 |
| ES local | 20 | No aplica | 0 | 0 |
| ES nube | 13 | No aplica | 0 | 0 |
| EN nube A, Data Modeling | 23 | 23 | 0 | 0 |
| EN nube B, documentación, simultánea a A | 15 | 13 | 0 | 0 |
| EN local, Human-Centric Engineering | 12 | 12 | 6 por sobrecarga | 0 |

Las dos sesiones de la toma principal procesaron fuentes distintas en nube
durante unos 100 s. La película conserva 24 s continuos de ese intervalo
compartido, a velocidad real. No se exige que el número de finales traducidas
coincida con originales: los cierres residuales de Live mantienen limitaciones
ya documentadas. Estos resultados prueban una demo breve, no un SLA.

Material reutilizable:

- [Logo SVG](demo/logo.svg) y [PNG transparente](demo/logo.png).
- [Carátula inicial](demo/01-portada.png) y [carátula final](demo/08-cierre.png).
- [Arquitectura para presentación](demo/07-arquitectura.png), también en [SVG](demo/07-arquitectura.svg).
- Pantallas reales: [local ES](demo/03-local-es.png), [nube EN](demo/04-nube-en.png),
  [segunda charla EN](demo/05-nube-documentacion.png), [nube ES](demo/06-nube-es.png)
  y [dos sesiones simultáneas](demo/09-sesiones-simultaneas.png).
- [Resultados y fuentes de las pruebas](demo/evidencia.json).
- [Subtítulos en inglés de la narración](demo/subtitulos-en.srt).

La locución se produjo con [edge-tts](https://github.com/rany2/edge-tts), voz
`es-AR-ElenaNeural`. La pista de cada charla proviene de su captura de pestaña.
Se atenúa durante la narración y se deja audible en sus pausas; en pantalla
dividida se escucha una fuente y ambas continúan procesándose. Se verificaron
duración, codecs, presencia de audio, ausencia de clipping digital y siete
fotogramas distribuidos por el montaje.

## Revisión de audio v2 — 25/09/2026

A pedido del usuario, se conserva el montaje de 115 s y se rehace la locución
con más énfasis, frases breves y pausas expresivas. La voz sigue siendo
`es-AR-ElenaNeural`; ritmo `+12%` y tono `+4Hz`. Solo el texto enviado a la voz
sustituye Python por «páiton»: el guion visible y los subtítulos mantienen Python.
Los SRT se regeneraron con los tiempos de palabras informados por la síntesis.

Se agregó **Decilo — Pulso**, una pieza instrumental original sintetizada para
esta presentación: 112 BPM, acordes, bajo, arpegios suaves y percusión, sin
samples externos. El volumen baja durante las demostraciones y se atenúa
además con la narración. Las pistas reales de las charlas se conservan.
Partitura programada, WAV y créditos quedan dentro del paquete local, en
`musica/`. La primera versión se conserva en `revisiones/v1/`.

No se volvieron a ejecutar modelos de Decilo ni se modificaron las tomas de
simultaneidad. Esta revisión cambia el audio editorial y sus subtítulos.

## Publicación en YouTube — 25/09/2026

Usuario autorizó subir la versión con música a su cuenta. Publicación completada
mediante YouTube Studio en el canal **Diego Lucchelli (@dnluc)**, como **oculto /
no listado**: https://youtu.be/mrHqqAIPJkQ. Se cargaron la carátula inicial como
miniatura, descripción ES/EN, capítulos, créditos de las charlas, idioma español
latinoamericano y categoría Ciencia y tecnología. Se declaró uso de IA para la
narración sintética; no es contenido creado para niños ni promoción pagada.

Verificación: Studio confirmó «Se ha publicado el vídeo» y la recarga de sus
detalles mostró «Oculto». Una consulta independiente sin cookies ni sesión
recuperó título, canal, disponibilidad `unlisted` y duración de 115 s. Las
comprobaciones de YouTube no encontraron problemas al publicar. El formulario
de Devpost no se modificó durante esta subida.

## Presentación preparada en Devpost — 25/09/2026

A pedido del usuario, se cargaron el video de YouTube, logo como miniatura,
siete imágenes con captions, historia actualizada, etiquetas y stack. Se adjuntó
`Decilo-Devpost.zip` (11,4 MB) con los materiales para los jueces. La vista previa
está en https://devpost.com/software/decilo. Se verificó la persistencia mediante
recargas del formulario y la carga del video y las imágenes en la vista previa.

La preparación dejó el envío a cargo del usuario. Durante la verificación final
se observó **SUBMITTED, 5/5 steps done** y «Project submitted!». Codex no pulsó
Submit ni ejecutó el envío. La copia del texto guardado está en [devpost.md](devpost.md).

## Nuevas pruebas y montaje v3 — 25/09/2026

Base sincronizada `b6736f2`, con la mejora visual del PR #25. El frontend fue
compilado nuevamente; el backend no cambió respecto de la grabación original.
Se volvieron a capturar los cuatro videos con audio real en cinco sesiones
nuevas. La carátula, arquitectura, voz argentina, música y subtítulos editoriales
se reutilizan; todas las tomas de la aplicación del nuevo montaje son nuevas.

| Prueba v3 | Originales finales | Traducciones finales | Gaps publicados |
| --- | ---: | ---: | ---: |
| ES local | 22 | No aplica | 0 |
| ES nube | 9 | No aplica | 0 |
| EN nube A, Data Modeling | 14 | 13 | 0 |
| EN nube B, documentación | 22 | 18 | 0 |
| EN local, Human-Centric Engineering | 9 | 9 | 7 por sobrecarga |

Las dos sesiones EN nube procesaron fuentes distintas durante **101,628 s**
compartidos. El montaje conserva 24 s continuos, a velocidad real. La geometría
del video y de la barra permaneció constante en las 1.030 observaciones por
sesión nube y 710 locales, tomadas cada 100 ms; ES también mantuvo la geometría
en las diez observaciones de cada sesión. Esto comprueba estabilidad visual
durante las tomas, no estabilidad de la inferencia ni fidelidad de traducción.

Hubo intervalos sin nuevos eventos de subtítulos: aproximadamente **34 s en
ES nube y 47 s en EN nube A**. El backend no los publicó como gaps. El video
y envío de paquetes seguían progresando en EN A; la causa no se diagnosticó
con esta grabación. La ausencia de errores publicados no certifica continuidad.
El inglés local tuvo siete gaps por sobrecarga de CPU. Se conserva esa prueba
adicional, con sus avisos visibles, fuera del montaje principal. Las salidas
residuales de nube siguen pudiendo quedar sin una traducción final.

Carpeta local de la revisión: `~/Videos/decilo-demo/revisiones/v3/`, con scripts,
audios originales, grabaciones completas, reportes y evidencia. La toma española
doble utiliza el intervalo 65–78 s, con cambios de texto reales en ambos modos.
Las demás tomas conservan los tiempos del guion. Los resultados completos
quedan en [evidencia v3](demo/v3/evidencia.json).

Entrega v3: `~/Videos/decilo-demo/Decilo-demo-v3-1m55.mp4` y
`~/Videos/decilo-demo/Decilo-presentacion-v3.zip`. Video verificado de **115,000 s**,
1920×1080/30, H.264/AAC, 8.618.826 bytes; decodificación completa correcta,
pico −4,2 dBFS, 30 cues EN y 30 ES. Se revisaron ocho fotogramas y la integridad
del ZIP. Capturas nuevas: [español local](demo/v3/03-local-es.png) y
[dos sesiones](demo/v3/10-sesiones-simultaneas.png). La página local está en
`revisiones/v3/presentacion.html`. YouTube y Devpost conservan la v2 publicada;
no se modificaron con esta revisión.
