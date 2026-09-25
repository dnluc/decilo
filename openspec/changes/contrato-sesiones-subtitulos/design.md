# Design

## Context

Ver `proposal.md`, `../../../VISION.md` y el cambio `arquitectura-base`.
Backend Python confirmado; motores pendientes de prueba. No hay aplicación
ni clientes existentes. Este es un contrato propuesto por Codex para revisión
de Claude, no una descripción de endpoints ya desplegados.

## Goals / Non-Goals

**Goals:** desacoplar audiencia e inferencia con ejemplos concretos, impedir
mezcla de sesiones y revisiones obsoletas, recuperar el estado reciente y
preservar incrementalidad sin exigirla a todo proveedor.

**Non-Goals:** transporte de audio/video, API administrativa, autenticación,
exportación completa, persistencia durable, framework de UI y selección del
ASR. Video sigue en el plan: aquí reservamos metadatos; su captura, análisis
y sincronización requieren su propio cambio e implementación.

## Decisions

### 1. Catálogo HTTP y suscripción por sesión

| Ruta | Resultado |
| --- | --- |
| `GET /api/v1/sessions` | 200, objeto con `sessions` (lista, posiblemente vacía) |
| `GET /api/v1/sessions/{session_id}` | 200, objeto de sesión; 404 si no existe |
| `WS /api/v1/sessions/{session_id}/events` | Snapshot inicial y eventos de esa sesión |

Sesión desconocida: rechazar antes de aceptar el WebSocket; el cliente puede
consultar HTTP para distinguir 404 de caída de red. Los endpoints de catálogo
son de lectura, sin credenciales del motor ni URL interna de la fuente.
No cachear respuestas de estado. Ejemplo de catálogo:

```json
{
  "sessions": [{
    "id": "konex-sala-1-charla-1",
    "title": "Building reliable systems",
    "source_language": "en",
    "translation_languages": ["es"],
    "target_locale": "es-AR",
    "status": "live"
  }]
}
```

IDs opacos no vacíos, distintos por charla; no reutilizar el ID de una sala
para todas sus charlas. `source_language`: `en` o `es` en MVP;
`translation_languages` enumera salidas habilitadas, sin repetir el original.
`target_locale` es el perfil del evento para español o `null`. La audiencia
elige idioma entre original y traducciones habilitadas. V1 produce un perfil
regional por sesión: no implica una inferencia por espectador.

Estados: `starting` (cargando/conectando), `live`, `degraded` (continúa con
limitaciones), `error` (no puede producir) y `ended` (terminal). Se permite
`starting → live|degraded|error|ended`, `live|degraded → live|degraded|error|ended`,
`error → starting|ended`. Silencio no cambia por sí solo el estado.
Un cliente desconectado muestra su propia pérdida de conexión; no cambia
el estado compartido de la sesión.

### 2. Envelope común y orden

Cada frame de datos es un objeto JSON UTF-8 con estos campos obligatorios:

| Campo | Semántica |
| --- | --- |
| `protocol_version` | Entero `1`; rechazar otra versión |
| `type` | Uno de los tipos definidos abajo |
| `session_id` | Sesión a la que pertenece |
| `stream_id` | Identificador opaco de generación del estado de esa sesión |
| `seq` | Entero seguro no negativo; orden total por sesión y generación |
| `emitted_at` | Fecha UTC del servidor, útil para diagnóstico |
| `data` | Payload específico |

El servidor serializa publicaciones por sesión. Eventos posteriores al
snapshot aumentan `seq` exactamente en uno, comenzando en `snapshot.seq + 1`.
El snapshot usa el último `seq` publicado (0 si todavía no hay eventos) y
no consume un número. Otros espectadores ven la misma secuencia; no se
filtra por idioma en el servidor para evitar huecos artificiales.

Campos desconocidos se ignoran; tipo desconocido o campos obligatorios
inválidos producen error de protocolo visible y reconexión con espera.
Un evento de otra sesión/conexión anterior se ignora. `seq <= aplicado`
se ignora; un salto hacia delante exige reconectar y reemplazar por snapshot.
Un `stream_id` nuevo solo se acepta mediante snapshot de una conexión nueva.

`emitted_at` no mide por sí solo latencia end-to-end. `start_ms` y `end_ms`
de subtítulos son offsets enteros en el audio, desde el inicio de la charla.
El adaptador de captura debe conservar la relación entre audio y reloj de
captura para el benchmark definido en `arquitectura-base`.

### 3. Snapshot autoritativo y recuperación

Primer frame obligatorio: `session.snapshot`. `data` contiene `session`
(objeto del catálogo), `captions` (última revisión vigente por entrada),
`gaps` (discontinuidades recientes) y `history_truncated` (boolean).

```json
{
  "protocol_version": 1,
  "type": "session.snapshot",
  "session_id": "konex-sala-1-charla-1",
  "stream_id": "run-1",
  "seq": 0,
  "emitted_at": "2026-09-25T01:00:00.000Z",
  "data": {
    "session": {
      "id": "konex-sala-1-charla-1",
      "title": "Building reliable systems",
      "source_language": "en",
      "translation_languages": ["es"],
      "target_locale": "es-AR",
      "status": "live"
    },
    "captions": [],
    "gaps": [],
    "history_truncated": false
  }
}
```

Registrar el cliente, capturar estado/seq y encolar el snapshot como una
operación atómica respecto de la publicación. Luego enviar los eventos
posteriores: no leer estado y suscribirse en dos operaciones con un hueco.
No mantener un lock durante I/O hacia el cliente.

Cada reconexión recibe snapshot; el cliente reemplaza, no concatena, su
estado. No implementamos replay por cursor ni prometemos historial completo.
Al perder estado del proceso, generar nuevo `stream_id`; la UI informa el
reinicio y la posible pérdida de historial. Reconectar con espera exponencial
y jitter, propuesta inicial de 0,5s hasta 10s; nunca un bucle inmediato.
Un snapshot `ended` se puede consultar sin reabrir indefinidamente la conexión.

La retención propuesta es los últimos 100 segmentos, hasta 100 gaps y un
snapshot serializado máximo de 1 MiB. Evictar primero segmentos completos
más antiguos (original y traducciones juntos), luego gaps antiguos si hace
falta; conservar `history_truncated=true` desde la primera evicción o pérdida
de historial. No volver a insertar resultados tardíos de segmentos evictados.
El cliente conserva como máximo los 100 segmentos de mayor `segment_seq` y
100 gaps recientes; el snapshot puede reducir esa ventana por el límite de bytes.

### 4. Subtítulos, revisiones y relación con el original

`caption.upsert` lleva en `data` un subtítulo completo, nunca un delta de tokens:

```json
{
  "protocol_version": 1,
  "type": "caption.upsert",
  "session_id": "konex-sala-1-charla-1",
  "stream_id": "run-1",
  "seq": 1,
  "emitted_at": "2026-09-25T01:00:01.100Z",
  "data": {
    "segment_id": "seg-1",
    "segment_seq": 1,
    "kind": "transcript",
    "language": "en",
    "revision": 1,
    "source_revision": null,
    "text": "We need another code review.",
    "status": "final",
    "start_ms": 0,
    "end_ms": 950,
    "speaker_id": null,
    "boundary_reason": "pause"
  }
}
```

```json
{
  "protocol_version": 1,
  "type": "caption.upsert",
  "session_id": "konex-sala-1-charla-1",
  "stream_id": "run-1",
  "seq": 2,
  "emitted_at": "2026-09-25T01:00:01.900Z",
  "data": {
    "segment_id": "seg-1",
    "segment_seq": 1,
    "kind": "translation",
    "language": "es",
    "revision": 1,
    "source_revision": 1,
    "text": "Necesitamos otro code review.",
    "status": "final",
    "start_ms": 0,
    "end_ms": 950,
    "speaker_id": null,
    "boundary_reason": "pause"
  }
}
```

Clave de entrada: `(session_id, stream_id, segment_id, kind, language)`.
`segment_seq` ordena segmentos según audio, es único/creciente y nunca cambia
para un `segment_id`; no usar el orden de llegada de traducciones para ordenar UI.
`revision` comienza en 1 y aumenta por entrada. Se aceptan saltos de revisión:
un proveedor puede omitir hipótesis intermedias. `seq` y `revision` son distintos.

`status` es `provisional` o `final`; `text` no vacío y máximo 8192 bytes UTF-8.
`0 <= start_ms <= end_ms`; la revisión de un provisional puede ampliar
`end_ms`, manteniendo `start_ms`. La traducción copia los tiempos de su
revisión original. El backend valida IDs, tipos, idiomas y límites antes
de publicar. Un dato inválido genera error, no truncamiento silencioso.
El frontend presenta texto como texto, nunca como HTML.

`source_revision` es `null` para original y un entero positivo para traducción.
El original se publica antes de cualquier traducción basada en él. Si el
original avanza, backend y cliente invalidan todas sus traducciones anteriores;
la UI muestra traducción pendiente en vez de mantenerla como vigente.
Cancelar trabajo antiguo cuando sea posible; descartar su resultado al volver.
La revisión del traductor continúa creciendo incluso tras la invalidación.

Un `final` es inmutable en v1: igual revisión es idempotente; una revisión
distinta posterior se rechaza. Solo confirmar traducción si su original
vigente ya es final. Puede haber varios segmentos provisionales mientras
se traducen, pero el motor debe acotar trabajo y tiempo pendientes.
Un segmento emitido no se divide ni fusiona retroactivamente en v1; elegir
sus límites antes de confirmarlo. Accurate path puede revisar provisionales;
correcciones posconfirmación necesitan una extensión explícita futura.

Ejemplo incremental alternativo (otra sesión/generación):

| `seq` | Entrada | Revisión | Original usado | Estado |
| --- | --- | --- | --- | --- |
| 10 | Original, "We need" | 1 | — | provisional |
| 11 | Traducción, "Necesitamos" | 1 | 1 | provisional |
| 12 | Original, "We need another code review." | 2 | — | final |
| — | Resultado tardío de traducción basado en original 1 | — | 1 | descartado antes de publicar |
| 13 | Traducción, "Necesitamos otro code review." | 2 | 2 | final |

Al aplicar 12 se invalida la traducción de 11. Reconectar después de 13
devuelve ambas revisiones 2 en el snapshot, con `seq=13`. Aplicar originales
antes de traducciones al reconstruir el estado desde la lista del snapshot.

`speaker_id` es opcional/nulo o etiqueta opaca local a la sesión; no presume
identidad personal. `boundary_reason` es opcional/nulo o `pause`, `semantic`,
`deadline`, `end_of_stream`. No implica detector semántico implementado.
El deadline fuerza una frontera aunque la idea siga; el contexto puede
continuar en el segmento siguiente. El presupuesto concreto lo decide el
pipeline tras medir; este contrato permite expresar el motivo sin bloquearlo.

### 5. Estado, fallos y discontinuidades

| Tipo | `data` |
| --- | --- |
| `session.status` | `session`: objeto actualizado completo del catálogo |
| `session.error` | `code`, `message` legible sin secretos, `retryable` boolean |
| `session.gap` | `gap_id`, `start_ms`, `end_ms`, `reason`, `discard_captions` |

Gaps: offsets como en subtítulos, `reason` es `overload`, `source_disconnect`
o `processing_error`; ambos tiempos pueden ser `null` si no se conoce el
intervalo, sin fabricar timestamps. `discard_captions` enumera claves
`{segment_id, kind, language}` de entradas provisionales que se retiran;
nunca borra finales. Al retirar un original, retirar también sus traducciones.
Esto permite retirar una traducción fallida sin eliminar su original final.
Al descartar audio, publicar gap y estado `degraded`/`error` según si continúa.
Invalidar los trabajos asociados para rechazar sus resultados en vuelo;
liberar sus referencias al finalizar/cancelar, sin tombstones ilimitados.
La UI muestra la interrupción separada del texto y elimina los provisionales
indicados. El snapshot conserva gaps recientes y excluye entradas retiradas.

Errores sugeridos: `inference_unavailable`, `invalid_caption`, `source_unavailable`.
Un evento de error no cambia por sí solo estado ni elimina texto: emitir
`session.status`/`session.gap` cuando corresponda. Al finalizar, drenar trabajo
hasta un timeout acotado; lo provisional que no pueda concluir se retira con
gap antes de emitir `ended`. No confirmar texto solo porque termine el stream.

### 6. Concurrencia y límites

Una inferencia produce eventos compartidos por todos los espectadores de la
sesión. Mantener registro de sesiones y publicación independiente de modelos.
No llamar al modelo desde un handler por espectador. Cada cliente tiene cola
acotada: propuesta inicial 64 mensajes y 2 MiB, lo que ocurra primero. Un
mensaje individual nunca supera 1 MiB; el snapshot cuenta en ese presupuesto.
Si se excede la cola, cerrar esa conexión con código de aplicación `4008`
(cliente lento). No esperar indefinidamente ni bloquear otras conexiones.

Los límites son defaults de la propuesta, ajustables en configuración y
documentados antes de probar. No introducir Redis/Kafka para el primer
servidor: memoria local alcanza para este contrato. Escalar inferencia externa
sin duplicar el registro de sesiones; múltiples gateways necesitarían un
estado/pub-sub compartido o routing por sesión, fuera de esta primera entrega.

## Risks / Trade-offs

- Snapshot en vez de replay → implementación menor; no recupera una charla
  completa. Comunicar truncamiento y dejar exportación para otro cambio.
- Solo confirmación por segmento → protege lectura; la estabilidad de un
  prefijo dentro del provisional es una extensión futura, no una promesa v1.
- Ventana acotada → resultados muy atrasados se descartan. Medir pérdidas
  en el pipeline, sin presentar descarte como mejora de latencia.
- Video y diarización → metadatos admitidos, pero identidad incierta se
  representa como desconocida y no bloquea transcripción.

## Migration Plan

Sin API anterior. Revisar con Claude y registrar aceptación antes de repartir
implementación. Crear modelos/fixtures y probar productor y consumidor contra
los mismos casos. Integrar en una rama común; archivar tras implementar y
verificar, nunca por la mera existencia de esta propuesta.
