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
- [ ] 1.6 Actualizar evidencias y realizar entrega final — Responsable: usuario con Codex | Estado: pendiente | Depende de: video real y cierre del MVP. Actualizar historia/stack al integrar el pipeline, adjuntar video y verificar requisitos antes de enviar. No se pulsó «Submit project».

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
