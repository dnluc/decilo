# Acuerdo de colaboración: Claude y Codex

El historial de cómo se llegó a este acuerdo (propuestas, ajustes,
respuestas de cada asistente) queda en el historial de commits de este
archivo — no se duplica acá. Esta versión es el estado vigente.

## Objetivo compartido

Entregar Decilo para la Nerdearla Vibeathon antes del **25 de septiembre de
2026 a las 12:00 de Argentina (15:00 UTC)**. Priorizar un recorrido
funcional y demostrable:

- Entrada de audio en vivo, transcripción original y traducción inglés → español.
- Vista de audiencia con selección de sesión e idioma.
- Al menos dos sesiones simultáneas y documentación de cómo escalar.
- Repo público con licencia open source, instrucciones reproducibles y requisitos.
- Video demo de 1–2 minutos con audio real y entrega en Devpost.

## Carpetas de trabajo

Worktrees hermanos del mismo repo, ninguno anidado dentro del otro:

- Claude: `~/projects/decilo-claude`, rama `main`.
- Codex: `~/projects/decilo-codex`, rama `codex/work` (trackea `origin/main`).

Cada asistente trabaja solo en su propia carpeta. No hay visibilidad en
tiempo real de lo que el otro tiene sin commitear — la única coordinación
real es pushear seguido y hacer `git pull --rebase origin main` antes de
editar algo compartido. Los conflictos se resuelven cuando git los marca
(rebase/merge), no se previenen por adelantado. Nunca `git push --force`
a `main`.

## Flujo de publicación

- **Documentación y planning** (OpenSpec, `COLLABORATION.md`, `AGENTS.md`,
  `VISION.md`, `README.md`): push directo a `main`.
- **Código y configuración** (backend, tests, CI, cualquier archivo bajo
  `src/`, `.github/`, etc.): Pull Request en GitHub, con revisión cruzada
  del otro asistente antes de mergear. Publicar la rama del PR con
  `git push origin HEAD:<rama-del-pr>` (`push.default=upstream` está
  configurado para el caso de documentación directa a `main`, no alcanza
  branches de PR).
- Ninguno de los dos puede aprobar su propia PR en GitHub (ambos commitean
  como la misma cuenta `dnluc`) — dejar un comentario de revisión y
  mergear directo alcanza, no hay branch protection configurada.

## Reparto confirmado

Separar todas las tareas por componente; quien no implementa una tarea la
valida antes de que se integre a `main`. No se trabaja en paralelo sobre
el mismo código — la validación es una revisión del trabajo terminado, no
una segunda implementación.

| Área | Responsable | Valida |
| --- | --- | --- |
| Captura de audio, transcripción, traducción y ejecución de sesiones (`mvp-pipeline`) | Claude | Codex |
| Vista de audiencia, selección de sesión/idioma y presentación de subtítulos | Codex | Claude |
| Integración de ramas y coordinación de archivos compartidos | Claude | Codex |
| Prueba del recorrido completo con dos sesiones | quien no haya integrado esa vez | el otro |

## Especificaciones y formato de tareas

Usar `openspec/changes/<cambio>/` para propuesta, specs, diseño y tareas;
`openspec/specs/` tendrá las specs consolidadas una vez que se archiven
cambios. Ciclo completo de OpenSpec (`propose → apply → verify → archive`)
solo para cambios que definen un contrato compartido entre ambos
asistentes; el resto se implementa directo, dejando avance y verificación
en `tasks.md` sin pasar por un ciclo separado por tarea. Archivar en pocos
checkpoints grandes, no tarea por tarea.

Formato de cada tarea:

```markdown
- [ ] 1.1 Describir tarea — Responsable: Claude | Estado: pendiente | Depende de: ninguna
```

Estados: pendiente, en curso, bloqueada, terminada. Marcar `[x]` solo al
terminar y registrar cómo se verificó. Si una tarea se traslada a otro
cambio de OpenSpec, marcarla como movida ahí (tachado + referencia) en vez
de dejarla duplicada y "sin asignar" en dos archivos.

## Estado de los cambios de OpenSpec

- `arquitectura-base`: drivers y diagrama aceptados por ambos. Falta
  cerrar cuando `mvp-pipeline` resuelva su spike (grupo 2) y la medición
  end-to-end (grupo 6).
- `contrato-sesiones-subtitulos`: contrato aceptado por Claude. Falta que
  Codex cree su propio cambio de OpenSpec para la vista de audiencia y
  que se integren ambos lados (grupo 4).
- `mvp-pipeline`: en curso, Claude. Ver `openspec/changes/mvp-pipeline/tasks.md`.
- CI mínima: PR #1 revisada y mergeada a `main` (Ruff + pytest + detección
  de `src/`, ver `docs/ci.md`).

## Entrega e integración

Al entregar una tarea, registrar en el `tasks.md` del cambio: rama/commit,
qué se completó, cómo se verificó y qué limitaciones quedan abiertas. Las
pruebas deben ser proporcionales al cambio — no declarar resultados sin
ejecutarlos. Quien integra resuelve conflictos preservando el trabajo de
ambos; el otro revisa antes de mergear código (no aplica a documentación,
que va directo). Actualizar y archivar specs solo al completar el cambio,
evitando que ambos lo archiven por separado.
