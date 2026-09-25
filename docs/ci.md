# CI mínima para la Vibeathon

GitHub Actions ejecuta `.github/workflows/ci.yml` en cada push y pull request.
Usa Python 3.12, verifica dependencias, compila bytecode, revisa errores básicos
con Ruff y ejecuta pytest. No genera un ejecutable ni despliega servicios.

Hasta que Claude incorpore `src/`, el resumen indica explícitamente que el
backend está pendiente y esos controles se omiten. Un resultado verde en esta
etapa no valida la aplicación. Con `src/` presente, faltar dependencias o tests
es un error: no se oculta el código de salida de pytest cuando no encuentra tests.

Contrato para el backend:

- Dependencias en un `pyproject.toml` instalable o `requirements.txt`.
  Si existe `requirements-dev.txt`, también se instala.
- Tests en `tests/`, con transcriptor y traductor simulados. Incluir las
  dependencias de los tests en el manifiesto o en `requirements-dev.txt`.
- Marcar con `@pytest.mark.model` las pruebas que descargan modelos o necesitan
  Ollama/Whisper reales. Se ejecutan localmente; la CI las excluye. Debe haber
  tests sin modelos: excluir todos los tests hace fallar el job.

Las regresiones prioritarias ya están previstas en `mvp-pipeline`: traducciones
obsoletas, reconexión/snapshot, clientes lentos y aislamiento de dos sesiones.
Se ejecutan con pytest; no hace falta otra herramienta o una suite duplicada.
La calidad de traducción y la latencia con audio real requieren su validación
local por separado.

Las actions se fijan por SHA y el workflow tiene permisos de lectura, no usa
secretos ni runners locales. GitHub ya tiene secret scanning y push protection
activados (verificado el 2026-09-24). Sonar, CodeRabbit, análisis adicional de
seguridad y despliegue automático quedan postergados para priorizar la demo.

Para reproducir localmente, instalar las mismas dependencias del workflow y correr:

```sh
python -m pip check
python -m compileall -q src tests
python -m ruff check --select E9,F63,F7,F82 src tests
python -m pytest tests -q -m "not model" -o "markers=model: requiere modelos o servicios reales"
```

El flujo acordado ahora usa PRs para código/configuración y permite documentación
directa a `main`. Revisar la CI y la aceptación del otro asistente antes de
integrar. Esto es un acuerdo de trabajo: aún no hay protección de rama que
bloquee merges o pushes automáticamente.
