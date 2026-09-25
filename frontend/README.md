# Frontend de Decilo

Estado: PRs #21/#22 (`e4b9f90`), 25/09/2026. JavaScript con módulos ES, HTML,
CSS y Vite; Node.js 22.12+. Contrato de subtítulos v1.
[Arranque completo](../README.md) · [Arquitectura](../docs/ARQUITECTURA.md).

## Ejecutar

```sh
cd frontend
npm ci
npm run dev
```

Abrir http://localhost:5173/. El frontend necesita backend en 8000 para captura
real; el proxy reenvía HTTP y WebSocket de `/api` bajo el mismo origen:

```sh
DECILO_BACKEND_URL=http://127.0.0.1:8001 npm run dev
```

El backend debe tener `DECILO_DEMO_SESSIONS=1`. Su `.env` contiene proveedores
y claves; el frontend no necesita ni recibe `GEMINI_API_KEY`.

## Recorrido actual

1. Pegar URL de YouTube y pulsar **Cargar**.
2. Elegir idioma EN/ES o detección automática, y proveedor local/nube.
3. **Compartir audio de pestaña**, autorizar audio en Chrome y dar Play.
4. Elegir idioma de lectura entre las salidas de esa sesión; **Detener** termina captura.

La captura se vuelve la sesión seleccionada. `?session=<id>` permite adjuntarse
a una sesión existente sin repetir inferencia. El catálogo permanece en la API,
pero no hay selector general de charlas en la pantalla actual. `?demo=1` y el
reproductor de WAV de la primera UI fueron retirados; las fixtures se usan en tests.

Sin preferencia guardada y con nube disponible, el selector adopta el default
del backend. `localStorage` conserva proveedor y tamaño de texto. Cambiar el
selector no modifica una captura en curso. `cloud_available` solo indica que
hay clave configurada, no comprueba acceso al modelo ni saldo.

## Captura y eventos

- `getDisplayMedia` nace del clic y requiere permiso real; no se pide micrófono.
- AudioContext a 16 kHz, mezcla mono y PCM16 LE en paquetes de 100 ms, con offset uint32.
- El worklet no reproduce audio adicional. Hasta 16 paquetes pendientes y un ACK en vuelo;
  los descartes conservan salto de offset y se informan.
- WS `/api/v1/capture?language=auto|en|es&provider=local|gemini`: control `detecting`/`ready`
  y PCM. El modo automático necesita Whisper local incluso si se elige nube.
- Al recibir `ready`, la UI abre `/api/v1/sessions/{id}/events`: snapshot y eventos JSON v1.
- `/api/v1/providers` informa opciones; `/api/v1/sessions/{id}` resuelve el adjunto por URL.

Gemini Live y Whisper tienen mecanismos internos distintos; la UI consume el
mismo contrato. Una revisión reemplaza el texto del mismo segmento. Original
final no equivale a traducción disponible: mientras falta español se muestra
el original con estilo provisional, sin cartel «Traduciendo».

## Presentación y recuperación

Dock inferior de subtítulos, historial con lo último arriba y paleta sobria.
El color distingue provisional/final. La barra sostiene cada entrada entre
1,6 y 7 s; revisiones del mismo segmento se actualizan en el lugar. Al drenar
una tanda de más de tres pendientes salta a la última, conservando el historial
reciente de hasta 100 segmentos/100 gaps. No es una exportación completa.

**Tamaño del texto** ofrece Normal, Grande y Muy grande. **Solo subtítulos**
activa lectura; se sale con el botón de vuelta o Escape, sin abrir otro socket.
Un live region anuncia finales. El texto del modelo se inserta con `textContent`.

`state.js` valida y aplica eventos. `connection.js` recupera snapshot ante
reconexión/hueco de secuencia, sin duplicar revisiones. Recargar la página
capturadora termina su audio; un snapshot solo recupera contenido ya publicado.
Los códigos de rechazo anteriores a aceptar el WS pueden verse como HTTP 403
sin detalle de cierre en JavaScript; revisar también la configuración del backend.

## Verificar sin inferencia

```sh
npm test
npm run build
npx playwright install chromium
npm run test:browser
uv run --project .. npm run test:integration
```

La integración requiere dependencias Python instaladas (`uv sync --group dev`
desde la raíz) y puertos libres 18764/5174. Levanta y cierra servidores exclusivos;
usa app, gateway, proxy, AudioWorklet y WS reales con inferencia simulada.
No emplea credenciales pagas ni demuestra calidad/latencia real.
Los endpoints `/api/_test/` solo existen en el módulo de pruebas.

En NixOS, `CHROMIUM_PATH=/run/current-system/sw/bin/google-chrome` permite usar
Chrome instalado para `test:browser` y `test:integration`.

`npm run build` produce `dist/`. Para producción, servir esos archivos con
`/api` bajo el mismo origen, soporte WebSocket y HTTPS. Vite es desarrollo;
no hay despliegue automático ni configuración de producción incluida.
