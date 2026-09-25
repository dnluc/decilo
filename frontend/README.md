# Vista de audiencia de Decilo

Cliente del contrato v1 de `contrato-sesiones-subtitulos`. Requiere Node.js
22.12 o superior. No necesita Ollama ni Whisper para probar la UI.

```sh
cd frontend
npm ci
npm run dev
```

Abrir **http://127.0.0.1:5173/**. Seleccionar sesión e idioma; los subtítulos
se actualizan sin duplicar revisiones. La conexión del espectador y el estado
de la charla se muestran por separado. Se conservan hasta 100 segmentos y
100 discontinuidades recientes; no es una exportación completa.

Para ver ejemplos sin backend, abrir **http://127.0.0.1:5173/?demo=1**.
El modo de muestra está rotulado: textos sintéticos y tiempos simulados,
no transcripción ni traducción real. No se activa ante errores de conexión.

## Conectar el backend de Claude

El proxy local envía HTTP y WebSocket de `/api/` a `http://127.0.0.1:8000`.
Cambiar el destino si Claude usa otro puerto:

```sh
DECILO_BACKEND_URL=http://127.0.0.1:8001 npm run dev
```

Rutas consumidas:

- `GET /api/v1/sessions`, respuesta `{ "sessions": [...] }`.
- `WS /api/v1/sessions/{session_id}/events`, empezando con snapshot.

No requiere CORS abierto: el navegador consume el mismo origen del frontend.
La UI no cambia de sesión automáticamente, no publica audio y no llama a los
modelos. El backend determina los idiomas disponibles.

## Pruebas y build

```sh
npm test
npm run build
npx playwright install chromium
npm run test:browser
```

En NixOS se puede usar el Chrome del sistema en lugar del navegador descargado:

```sh
CHROMIUM_PATH=/run/current-system/sw/bin/google-chrome npm run test:browser
```

Los tests de Node cubren el estado del protocolo y la recuperación de conexión.
Playwright prueba selección, actualizaciones, aislamiento, tratamiento seguro
de texto, errores HTTP y reconexión en navegador con API simulada. No acreditan
calidad de inferencia ni el objetivo de latencia; falta la integración con audio real.

`npm run build` produce `dist/`. Para desplegar, servir esos archivos y enrutar
`/api/` al backend **bajo el mismo origen**, con soporte de WebSocket. Usar HTTPS
para obtener WSS automáticamente. Vite es el servidor de desarrollo; este cambio
no incluye despliegue de producción.

## Opciones de lectura

El selector **Tamaño del texto** ofrece Normal, Grande y Muy grande. Se recuerda
la preferencia en este navegador cuando el almacenamiento local está disponible;
si está bloqueado, sigue funcionando durante la visita.

Después de elegir una sesión, **Solo subtítulos** oculta el catálogo y la
presentación. Mantiene idioma, conexión, avisos y la identificación de muestra.
Volver con **Volver a las charlas** o **Escape**. El modo no abre una conexión
nueva ni se restaura automáticamente al recargar, para poder elegir otra charla.

## Integración con el gateway real, sin inferencia

Con Python 3.12 y las dependencias del backend instaladas (`pip install -e .`
desde la raíz, o `uv sync`), ejecutar desde `frontend/`:

```sh
npm run test:integration
# Si el entorno Python se gestiona con uv:
uv run --project .. npm run test:integration
```

Requiere Chromium instalado como las otras pruebas de navegador. Levanta
servidores exclusivos de prueba en `127.0.0.1:18764` y `127.0.0.1:5174` y
los detiene al terminar; falla si esos puertos están ocupados. No usa los puertos
habituales de desarrollo de Claude/Codex.

La app FastAPI, el registro, el stream, el gateway, el proxy y la UI son reales.
Solo se sustituyen las fuentes de eventos por publicaciones sintéticas desde
un módulo de prueba; no se ejecutan Whisper/Ollama. Los endpoints `/api/_test/`
se agregan únicamente en ese módulo y no existen al iniciar `decilo.app:app`.
Verifica el transporte WebSocket real, revisiones, HTTP/estado, cambio de sesión,
reconexión por snapshot y limpieza de suscripciones. No mide calidad ni latencia
con audio real.
