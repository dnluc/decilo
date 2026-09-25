# Why
Probar audio humano desde el video de YouTube IW0unWVDnrI proporcionado por
el usuario, embebido junto a los subtítulos.

# What Changes
Captura de audio de pestaña con permiso explícito del navegador; envío PCM
mono 16kHz a un WebSocket local, inferencia real y eventos existentes.

# Capabilities
## New Capabilities
- `tab-audio`: captura de audio de pestaña, acotada y detenible.

# Impact
Frontend y backend implementados por Codex tras el handoff de Claude.
Depende de PR #6; no descarga YouTube ni usa sus subtítulos.
