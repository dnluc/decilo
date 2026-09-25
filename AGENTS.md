# Instrucciones de colaboración para Decilo

Antes de trabajar, leer [COLLABORATION.md](./COLLABORATION.md),
[VISION.md](./VISION.md) y los artefactos
del cambio activo en `openspec/changes/`.

Claude y Codex trabajan en paralelo. Respetar responsables y worktrees,
preservar cambios ajenos y registrar decisiones y avances en OpenSpec.
El procedimiento está acordado; el reparto propuesto sigue pendiente de la
decisión del usuario. Leer las respuestas de ambos en el acuerdo y aplicar
OpenSpec por cambios grandes, registrando avances y validaciones por tarea.

Preservar los diferenciales de la visión mediante interfaces extensibles y
construcción por etapas. Distinguir ideas experimentales de capacidades probadas.

## Carpetas de trabajo (2026-09-24)

Cada asistente trabaja en su propio worktree, hermano de este repo:

- Claude: `~/projects/decilo-claude` (rama `main`).
- Codex: `~/projects/decilo-codex` (rama `codex/work`, configurada para
  trackear `origin/main`).

`push.default=upstream` está configurado a nivel de repo (compartido por
ambos worktrees), así que un `git push` simple desde `decilo-codex` empuja
directo a `main` en origin — no hace falta la sintaxis
`codex/work:main`. Antes de pushear, siempre `git pull --rebase origin main`
para evitar un push no-fast-forward; si git lo rechaza igual, no forzar
(`--force`) — resolver el conflicto y reintentar. Nunca hacer force-push a
`main`.
