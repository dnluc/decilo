# Design
Reproductor YouTube embebido; enlace alternativo si no admite embedding.
El usuario selecciona pestaña y activa audio en getDisplayMedia. No se envía
video ni se usa micrófono. AudioWorklet recibe mono a 16kHz y emite bloques de
hasta 5s. No se reproducen esos bloques localmente (evita eco).

WS /api/v1/capture?language=en|es, solo DECILO_DEMO_SESSIONS=1. Ready JSON
contiene session (catálogo v1), y la audiencia se conecta al stream existente.
Frames binarios: uint32 LE offset de muestras seguido de PCM16 LE mono 16kHz,
entre 1 y 80000 muestras; offsets crecientes sin solapamiento, máximo 1 hora.
Fin mediante texto literal `stop`; el backend drena su cola y termina. Timeout
sin audio 15s termina la captura con gap. Máximo dos workers incluyendo archivos,
20 sesiones de captura retenidas por proceso. Cola de dos bloques; se descarta
el más antiguo si se llena, publicando gap overload. Captions relativos al inicio
de la captura, no al timestamp absoluto de YouTube. Inferencia compartida con WAV.

El navegador cierra si su buffer de transporte supera 320008 bytes; no acumula
una cola infinita. Stop libera pistas/contexto y envía el último bloque parcial.
Si la fuente no trae pista de audio, se explica el problema y no se crea sesión.
No hay fallback a texto simulado. El permiso real lo concede el usuario.
