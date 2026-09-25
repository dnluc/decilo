# Integración continua y validación

Estado documental al PR #22 (`e4b9f90`), 25/09/2026. Dos workflows corren en
push, pull request y ejecución manual. No despliegan ni invocan modelos reales.

| Workflow | Controles |
| --- | --- |
| [CI Python](../.github/workflows/ci.yml) | Python 3.12, instalar dependencias y `pip check`, compileall, Ruff básico, pytest excluyendo `model` |
| [Audience](../.github/workflows/audience.yml) | Node 22, npm ci, tests Node, build Vite, Playwright de navegador e integración HTTP/WS real con inferencia simulada |

Python usa `ruff --select E9,F63,F7,F82` en CI: no equivale a lint exhaustivo,
SAST ni análisis de dependencias vulnerables. El detector de `src/` queda como
soporte del arranque del proyecto; hoy el backend ya existe y se ejecutan sus checks.

Las actions están fijadas por SHA y los jobs usan permisos de lectura. Sonar,
CodeRabbit, análisis adicional de seguridad y despliegue automático no están
implementados en estos workflows. La nota histórica de secret scanning/push
protection fue verificada el 24/09; esta actualización no revalida ajustes externos.

## Aislamiento

- `tests/conftest.py` excluye el `.env` del desarrollador y bloquea transportes
  HTTP reales en pruebas sin marca `model`. No es un bloqueo universal de sockets:
  las pruebas de Gemini Live deben simular también sus conexiones WebSocket.
- `frontend/tests/integration/browser_backend.py` usa configuración de prueba,
  sin clave y con inferencia falsa; no ejecuta Whisper/Ollama/Gemini.
- Marcar `model` solo para pruebas que realmente requieren modelos/servicios;
  la CI ejecuta `-m "not model"` y exige tests restantes.

Se cubren revisiones, finales inmutables, traducciones obsoletas, snapshots,
reconexión, clientes lentos, PCM, colas, segmentación, selección local/nube,
parciales, detección inicial y mensajes simulados de Gemini Live. Las pruebas
no sustituyen una sesión humana larga con calidad anotada ni validan cuotas.

## Reproducir

Desde la raíz, luego de `uv sync --group dev` y `npm --prefix frontend ci`:

```sh
uv run python -m compileall -q src tests
uv run python -m ruff check --select E9,F63,F7,F82 src tests
uv run python -m pytest tests -q -m 'not model'
npm --prefix frontend test
npm --prefix frontend run build
```

Para navegador/integración, desde `frontend/`:

```sh
npx playwright install chromium
npm run test:browser
uv run --project .. npm run test:integration
```

La integración utiliza 18764 y 5174, separados de la demo 8000/5173. Sus
servidores se detienen al terminar. Ver [frontend](../frontend/README.md)
para Chrome del sistema/NixOS. No se publican conteos como si se hubieran
repetido pruebas durante una actualización exclusivamente documental.

## Publicación y evidencia

Código/configuración por PR con revisión según [COLLABORATION.md](../COLLABORATION.md);
documentación puede ir a main. El estado externo de protecciones de rama no
se deduce de los archivos de workflow. Cada corrida de inferencia conserva su
configuración y límites en [validation](validation/README.md).
