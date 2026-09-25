Revisión de Codex sobre `96dc8fc`. **Solicito ajustes antes de integrar.** El alcance de estructura/modelos/fixtures es correcto; no se exige completar el pipeline en este PR.

1. **[P2] Límite de texto en bytes UTF-8** — `src/decilo/models.py:48`. `max_length=8192` acepta 8192 caracteres, pero el contrato permite 8192 bytes. Reproduje que `CaptionData(..., text="á" * 5000)` acepta 10000 bytes. El cliente rechaza ese subtítulo y reconecta, incluso si luego aparece en cada snapshot. Validar bytes UTF-8 sin truncar y cubrir límites con caracteres multibyte.

2. **[P2] Validar el intervalo de los gaps** — `src/decilo/models.py:70-75`. `GapData` acepta `start_ms=200, end_ms=100` y `start_ms=null, end_ms=100`. El contrato requiere un intervalo ordenado o ambos tiempos nulos. Ambos casos pasan el modelo y fallan en el cliente; un gap persistido en el snapshot puede impedir recuperar la sesión. Agregar validación cruzada y pruebas.

3. **[P2] Rechazar enteros fuera del contrato y coerciones silenciosas** — `src/decilo/models.py:95-100` y campos numéricos de `CaptionData`. El envelope acepta `seq=9007199254740993`, que pierde precisión al parsearse en JavaScript y no es un entero seguro. Además `revision=True` se acepta y se convierte a 1 pese a anunciar validación estricta. Rechazar tipos inválidos y acotar `seq` al rango seguro; agregar pruebas de borde para los contadores y tiempos usados por el cliente.

4. **[P2] Rechazar idiomas de traducción repetidos** — `src/decilo/models.py:28-34`. `translation_languages=["es", "es"]` pasa. El contrato no admite repeticiones y el frontend rechaza ese catálogo completo; una configuración inválida de una sesión oculta todas las charlas. Validar unicidad y añadir el caso negativo.

Validación ejecutada:
- 7 tests del PR correctos; Ruff de `src`, `tests`, `scripts` correcto; `/health` devuelve 200 con TestClient.
- Fixtures de Claude consumidas por el reductor real de la UI: catálogo de 2 sesiones, snapshot, provisional, final, traducción, cambio de estado, error y gap, hasta `seq=6`, correctos.
- Los seis casos inválidos descritos arriba se reprodujeron con Pydantic 2.13.5 y fueron aceptados por los modelos.
- Actions ejecutó los tests reales (7 passed), no el salto inicial por ausencia de `src/`.
- Validación local con dependencias de modelos/FastAPI/tests; no instalé ni ejecuté motores de inferencia. No verifiqué de nuevo los benchmarks de audio ni latencia; quedan fuera de esta aprobación parcial.

Los fixtures válidos desbloquean la integración del cliente. Agregar las validaciones y tests negativos anteriores antes del merge; no modificar el contrato para aceptar datos inválidos.
