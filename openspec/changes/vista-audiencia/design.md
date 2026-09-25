# Design

## Context

Cliente de `contrato-sesiones-subtitulos`, separado del pipeline de Claude.
Leer su `design.md` para rutas, tipos, límites y reglas de revisión.

## Decisions

- JavaScript nativo: reductor puro, transporte inyectable y vista DOM separados.
- Vite entrega assets y proxy local HTTP/WebSocket. Build estático sin dependencias
  de UI en runtime; no modifica la elección de Python para el backend.
- Estado por sesión y generación; cada conexión invalida callbacks anteriores.
  Un salto de secuencia fuerza reconexión y snapshot autoritativo. Una versión
  incompatible detiene la aplicación de eventos hasta cambiar sesión o recargar.
- Retención de 100 segmentos/100 gaps, orden por `segment_seq`, invalidación de
  traducciones al avanzar el original y texto por `textContent`.
- UI adaptable a móvil, controles nativos, foco visible y anuncios de definitivos.
  Seguimiento del último subtítulo desactivable para leer el historial.
- Modo `?demo=1` rotulado y cargado explícitamente; jamás fallback de API.

## Risks / Trade-offs

No hay backend real en la validación inicial. Los fixtures de UI son ejemplos
sintéticos del contrato; se deben cotejar con los compartidos de `mvp-pipeline`
al integrar. El build no configura un servidor de producción. Los metadatos de
hablante son opcionales, sin atribuir diarización ni video implementados.
