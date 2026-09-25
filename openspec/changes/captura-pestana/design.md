# Diseño vigente de captura de pestaña

Base `e4b9f90`, PRs #21/#22, 25/09/2026. [Arquitectura completa](../../../docs/ARQUITECTURA.md).
Este documento describe implementación; aceptación de calidad y requisitos
pendientes en [estado OpenSpec](../../README.md).

## Navegador y transporte

YouTube se reproduce en iframe o en otra pestaña. `getDisplayMedia` requiere
permiso real para audio; no se solicita micrófono ni se envían frames de video.
AudioContext a 16 kHz; worklet mezcla mono y convierte a PCM16 LE. Envía cada
100 ms (1.600 muestras), no cada cinco segundos. Ganancia cero evita duplicar sonido.

`WS /api/v1/capture?language=auto|en|es&provider=local|gemini` exige
`DECILO_DEMO_SESSIONS=1`. `auto` es default de UI; la API sin language usa en.
Cada frame binario lleva uint32 LE de offset + PCM16; acepta 1–80.000 muestras,
offsets crecientes sin solapamiento y hasta una hora. Saltos se informan como gaps.
`stop` es texto de control; `detecting`/`ready` no son envelopes v1 de audiencia.

Worklet: 16 pendientes más uno esperando ACK, descarta antiguo con aviso.
Socket del navegador: detiene si bufferedAmount supera 320008 bytes.
Flush de último parcial al detener, liberación de pistas/contexto y watchdog de 95 s.
No existe fallback a texto simulado ante errores.

## Sesión, idioma y proveedor

Con auto se acumulan ~2,5 s sobre umbral de energía o hasta 12 s totales,
se detecta con Whisper small y se reingresan los paquetes conservados. Al
alcanzar el tope se intenta detectar incluso sin voz suficiente; no es un
rechazo garantizado de silencio. Idioma fijo evita esa etapa local.

`provider` explícito fija ambas etapas mediante ContextVar; tareas y threads
lo heredan y se restaura al terminar. Omitido conserva configuración por etapa.
`GET /api/v1/providers` expone default y presencia de clave; no saldo/disponibilidad.
Sin preferencia previa la UI adopta default si hay nube, y conserva preferencia
propia en localStorage. Cambiar el selector no cambia la captura en curso.

Rechazos previos a aceptar: 4403 por modo/idioma/proveedor/clave, 1013 por
preparación local y 4429 por cupos; pueden observarse como HTTP 403 de handshake.
Nube con idioma fijo no depende de readiness local. La detección sin resultado
puede cerrar con 4408 después de aceptar.

## Camino por segmentos

Proveedor local o Live desactivado/fallido al conectar. Pausas: mínimo 1 s,
400 ms de silencio, máximo 6 s. Cola de audio: presupuesto 2 × máximo (12 s),
hasta ceil(2 × máximo / mínimo) + 1 entradas; descarta antiguos con overload.
Sin segmentador: dos paquetes pendientes, no ventanas de 5 s garantizadas.

Parciales locales: base/beam 1, instantánea desde 0,8 s y crecimiento de 0,5 s;
una activa y una pendiente reemplazable. Final: small/beam 5 (ES configurable).
El corte textual local usa un límite interno de Whisper desde 2 s y conserva el
PCM posterior; se etiqueta pause. Debe reconciliarse con end_ms ya publicado.
Parciales/corte textual se apagan con DECILO_PARTIALS=0; Gemini REST no aporta
timestamps por segmentos para ese corte. La traducción espera original final.

## Camino Gemini Live

Habilitado por default cuando STT es gemini: conexión WSS con modelo
`gemini-3.5-transcribe-live`, PCM base64 directo, interims/finales a contrato v1.
No usa segmentador acústico, WAV ni cola local de segmentos. Modo SMART y corte
por regex interna de oración: no se promete verbatim ni alineación exacta de palabras.
Traducción separada REST `gemini-3.5-flash-lite`, thinking MINIMAL configurable.

Si falla el setup se publica error y se usa Gemini REST por segmentos. No cambia
a Whisper. Durante Live hay reconexión tras nueve minutos/al fallar envío,
con numeración/base conservadas pero sin replay durable. DECILO_GEMINI_LIVE=0
permite desactivar este camino; DECILO_PARTIALS no controla los interims Live.

Al finalizar/reconectar o ante una reescritura no alineable, el código puede
confirmar la última provisional localmente, sin final oficial. Ese método no
traduce el fragmento. Es una divergencia respecto del objetivo de conservar
incertidumbre, pendiente de revisión; no se presenta como garantía del proveedor.

## Salida, límites y finalización

Ready contiene Session y el navegador abre el WS de audiencia existente:
snapshot y eventos v1. Una inferencia se comparte entre espectadores.
Hasta dos trabajos activos y 20 sesiones para admitir nuevas capturas; las
detecciones auto aún no reservan cupo antes de crear sesión. No son límites
atómicos frente a conexiones concurrentes en detección.

15 s sin mensajes termina el ingreso. Al cerrar, hay hasta 90 s compartidos
para drenar audio/traducción. Live envía audioStreamEnd, espera aproximadamente
3 s si hay texto abierto y aplica su finalización residual. Historial reciente
en RAM, no persistencia ni exportación. Autenticación/producción siguen fuera
de la demo local.
