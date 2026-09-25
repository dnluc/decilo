# Entrega Devpost — seguimiento documental

> **Lectura al 25/09/2026, PR #22 (`e4b9f90`):** Seguimiento histórico del formulario. El borrador Markdown se actualiza localmente; no se reconsultó ni modificó Devpost en esta revisión documental.
> [Estado global, divergencias y evidencia](../../README.md).

Solicitud del usuario, 24/09/2026: revisar el proyecto y completar el formulario
de la hackathon usando Chrome. No introduce ni modifica contratos compartidos;
se registra el avance sin abrir un ciclo de especificación nuevo.

- [x] 1.1 Revisar acuerdos, visión, avances y código disponible — Responsable: Codex | Estado: terminada | Depende de: ninguna. Base revisada: `0bbdfd9`. Frontend implementado; backend y evidencia con audio real pendientes en este checkout. No se inspeccionó ni modificó el worktree de Claude.
- [x] 1.2 Preparar textos para el formulario y contrastar requisitos públicos — Responsable: Codex | Estado: terminada | Depende de: 1.1. Borrador en `docs/devpost.md`; requisitos consultados en `https://nerdearla26.devpost.com/`. Se distingue estado implementado de diseño y experimentos.
- [x] 1.3 Verificar frontend disponible — Responsable: Codex | Estado: terminada | Depende de: 1.1. Ejecutados `npm test` y `npm run build` en `frontend/`, ambos con exit code 0. No se repitieron Playwright ni pruebas de inferencia; los resultados históricos se identifican como tales en el borrador.
- [x] 1.4 Leer campos reales y completar el borrador en Devpost — Responsable: Codex | Estado: terminada | Depende de: conexión al navegador y enlace del formulario. Acceso resuelto abriendo Chrome con perfil separado y depuración local autorizados por el usuario. Guardados nombre, pitch, historia, ocho tecnologías, enlace al repo y campos adicionales de repositorio, stack, Argentina y aceptación de términos. País y aceptación confirmados expresamente por el usuario. Verificación: recarga independiente de cada paso, comparación exacta de textos y lectura de etiquetas, país y checkbox; **DRAFT, 4/5 steps done**. Equipo existente sin cambios. TinyFish no se usó.
- [x] 1.5 Revisar materiales y estado final de la presentación — Responsable: Codex con el usuario | Estado: terminada | Depende de: 1.4. Usuario confirmó que todavía no tiene video; campo vacío y envío final pendiente. Galería y miniatura no se modificaron. La pantalla final recuerda el requisito de video. La implementación del pipeline sigue a cargo de Claude en `mvp-pipeline`; esta tarea no la reasigna.
- [x] 1.6 Actualizar evidencias y verificar entrega final — Responsable: usuario con Codex | Estado: terminada. Ver sección 4: formulario y materiales actualizados; al finalizar se observó SUBMITTED, 5/5. Codex no pulsó «Submit project»; el envío estaba reservado al usuario.

Registro de la revisión inicial: entonces eran cambios locales. Claude publicó
este seguimiento en `61e7b1d`; no implica que se haya enviado el proyecto.

## Revisión de idiomas — 25/09/2026

- [x] 2.1 Aclarar alcance de idiomas en la historia y campo de stack — Responsable: Codex | Estado: terminada | Depende de: pedido del usuario tras revisar las bases. Guardado en Devpost: origen configurado por sesión, destino elegido por espectador entre salidas disponibles, transcripción ES/EN y traducción EN→ES como alcance inicial; ES→EN y otros pares como ampliaciones previstas. El traductor actual en `translate.py` está fijado a EN→ES; no se afirma soporte arbitrario de idiomas.
- [x] 2.2 Actualizar información que quedó desfasada desde la primera carga — Responsable: Codex | Estado: terminada | Depende de: 2.1. Revisados código de pipeline/traducción y avances de Claude hasta `c884ebe`: backend implementado con Gemma 3n e2b y faster-whisper; se conserva como pendiente la validación conjunta bajo dos sesiones y latencia hasta navegador. Agregadas cinco etiquetas del backend. No se tocaron cambios ajenos en `src/` ni se ejecutaron nuevas pruebas de inferencia.
- [x] 2.3 Verificar persistencia de la corrección — Responsable: Codex | Estado: terminada | Depende de: 2.2. Recarga independiente y comparación exacta de historia y campo de stack: correctas. Trece etiquetas, Argentina y aceptación previamente autorizada conservados; video vacío; estado DRAFT 4/5. No se realizó el envío final. Copia actualizada en `docs/devpost.md`.

## Actualización documental al PR #22 — 25/09/2026

Codex actualiza `docs/devpost.md` como borrador LOCAL para reflejar captura,
Gemini Live/REST, modelos base/small, cortes y límites. No se abrió ni modificó
el formulario externo, no se verificó su estado actual y no se pulsó Submit.
Los registros 1.4/2.3 conservan su fecha y contenido histórico. Tarea 1.6 sigue
pendiente de material y entrega; no se acredita benchmark nuevo ni revisión de
las bases con esta edición de Markdown.

## Producción de video e imágenes — Codex, 25/09/2026

Usuario autorizó grabar los cuatro enlaces y confirmó narración argentina con
subtítulos en inglés. Luego confirmó que apagó los otros procesos para permitir
pruebas. Base de la grabación: `370d9ba` (PR #24), frontend compilado y backend
del worktree Codex; no se modifica código ni credenciales. En NixOS se agregaron
bibliotecas C++/zlib al entorno del proceso de grabación.

- [x] 3.1 Revisar requisitos públicos y preparar guion cronometrado — Codex.
  Overview Devpost revisado; fuentes y límite 1–2 min en `docs/DEMO.md`.
- [x] 3.2 Crear logo, carátulas, diagrama de presentación, voz ES-AR y SRT EN — Codex.
  Se conserva la identidad de la UI. Inglés editorial, no capacidad ES→EN de Decilo.
- [x] 3.3 Grabar capturas reales con historial y fuentes cerca de su mitad — Codex.
  Siete casos completados, incluida simultaneidad de dos fuentes EN en nube
  sin gaps/errores registrados. También se conservan sobrecargas locales
  (18 gaps en prueba mixta, 6 en Human-Centric), sin declararlas resueltas.
- [x] 3.4 Exportar y verificar el video — Codex. 115 s exactos, Full HD 30 fps,
  H.264/AAC; voz y audio original, siete fotogramas revisados. Logo/capturas
  y evidencia en `docs/demo/`; archivo MP4 y paquete en `~/Videos/decilo-demo/`.
- [x] 3.5 Subir video a YouTube — Responsable: Codex | Estado: terminada.
  Versión v2 publicada como no listado: https://youtu.be/mrHqqAIPJkQ.
  Canal @dnluc; confirmación en Studio, recarga de detalles y consulta sin sesión
  verifican disponibilidad `unlisted` y 115 s. Miniatura y créditos cargados.
- [x] 3.7 Actualizar formulario y dejarlo listo — Responsable: Codex | Estado: terminada.
  Ver sección 4. El envío queda exclusivamente a cargo del usuario (1.6).

No se simularon subtítulos ni se aceleró la toma de simultaneidad. La demora
local y el cierre residual sin traducción de algunos segmentos Live siguen
como límites; estas corridas no completan el benchmark sostenido de OpenSpec.

### Revisión de audio solicitada por el usuario — 25/09/2026

- [x] 3.6 Incorporar música y rehacer la narración — Responsable: Codex |
  Estado: terminada. Música instrumental original sintetizada, énfasis y pausas
  más expresivas; Python se envía como «páiton» únicamente al sintetizador.
  Subtítulos EN/ES regenerados con tiempos de palabras; mismas tomas reales,
  sin nuevas inferencias ni cambios de código de la aplicación. Se conserva v1.

  Validación de v2: MP4 de 115,000 s, H.264/AAC 1080p/30; mezcla con pico
  de −4,1 dBFS, 30 cues EN y 30 ES dentro del montaje, revisión visual de
  arquitectura/cierre e integridad del ZIP. Material actualizado en la misma
  carpeta de entrega; esta revisión no publica el video en YouTube.

## Preparación final del formulario — Codex, 25/09/2026

Pedido explícito: completar Devpost con video, imágenes y logo, y dejar que el
usuario pulse Submit. La preparación no autoriza el envío final.

- [x] 4.1 Actualizar nombre/pitch e imagen principal — Responsable: Codex |
  Estado: terminada. Logo visible y verificado tras guardarlo.
- [x] 4.2 Guardar historia y material real — Responsable: Codex | Estado: terminada.
  Video `mrHqqAIPJkQ`, siete capturas/diagramas con captions y orden persistido;
  historia de la implementación y pruebas, 15 etiquetas con Gemini/Gemini Live.
- [x] 4.3 Completar información para jueces — Responsable: Codex | Estado: terminada.
  Stack actualizado, repo público, archivo `Decilo-Devpost.zip` (11,4 MB).
  Argentina y aceptación previa conservadas; equipo existente sin cambios.
- [x] 4.4 Verificar por recargas independientes y vista previa — Responsable: Codex |
  Estado: terminada. Coincidencia exacta de pitch, historia, video, captions,
  orden y stack; «Current File: Decilo-Devpost.zip» presente; video incrustado
  y siete imágenes cargadas. Repo verificado público sin autenticación.
- [x] 4.5 Verificar estado tras el envío reservado al usuario — Estado: terminada.
  Mientras Codex verificaba la pantalla final, pasó a SUBMITTED, 5/5 steps done
  y «Project submitted!». Codex no pulsó Submit ni envió el formulario.

Copia de textos guardados: `docs/devpost.md`. Evidencia local de verificación:
`~/Videos/decilo-demo/devpost-verificacion.json`. La preparación estaba en DRAFT
4/5; el último estado observado fue SUBMITTED 5/5. Los miembros que aparecen
en la pantalla final son Diego Lucchelli y Sole Lucchelli; Codex no editó el equipo.

## Nueva grabación con lectura estable — Codex, 25/09/2026

Pedido del usuario: rehacer el video y las pruebas tras las mejoras. Base
sincronizada `b6736f2`, con PR #25; respecto de la toma anterior (`370d9ba`)
cambia la presentación del frontend, no el backend. Material separado en
`~/Videos/decilo-demo/revisiones/v3/`; se conserva la versión publicada.

- [x] 5.1 Sincronizar main y compilar el frontend actualizado — Responsable: Codex |
  Estado: terminada. No hay PRs abiertos; `npm run build` correcto.
- [x] 5.2 Repetir capturas humanas local/nube y dos fuentes simultáneas —
  Responsable: Codex | Estado: terminada. Cinco casos nuevos sobre los cuatro
  videos: ES local, ES nube, dos EN nube simultáneos y EN local adicional.
  Intervalo compartido de nube: 101,628 s, IDs y fuentes distintos. Se conservan
  audios, eventos, reportes y capturas. En las sesiones EN, 1.030/1.030/710
  muestras cada 100 ms conservaron tamaño de video y barra. ES conserva diez
  observaciones iguales por sesión. Hay pausas de salida en nube (unos 34 s
  en ES y 47 s en EN A, sin eventos gap) y siete gaps de sobrecarga en EN
  local; no se presentan como resueltos ni como aprobación de latencia.
- [x] 5.3 Montar y verificar versión de hasta dos minutos — Responsable: Codex |
  Estado: terminada. `Decilo-demo-v3-1m55.mp4`: 115,000 s, Full HD/30,
  H.264/AAC, 8.618.826 bytes. Ocho fotogramas revisados; decodificación completa
  sin errores; pico de audio −4,2 dBFS, 30 cues EN y 30 ES dentro del montaje.
  Conserva voz argentina, pronunciación «páiton» y música original. Nueva
  galería, página local y ZIP comprobado. La publicación de YouTube/Devpost
  permanece en v2; esta tarea no modifica los servicios externos.
