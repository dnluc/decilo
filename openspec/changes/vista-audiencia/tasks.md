# Vista de audiencia — Codex

Implementa las tareas 3.1/3.2 de `contrato-sesiones-subtitulos` contra su
contrato aceptado, sin modificar el backend de Claude. Rama: `codex/audiencia`.

- [x] 1.1 Implementar reductor del protocolo v1 y fixtures de audiencia — Responsable: Codex | Estado: terminada | Depende de: contrato aceptado. Verificar revisiones, traducciones obsoletas, snapshot, gaps y retención.
- [x] 1.2 Implementar cliente HTTP/WebSocket con aislamiento por conexión y reconexión acotada — Responsable: Codex | Estado: terminada | Depende de: 1.1.
- [x] 1.3 Implementar vista accesible de sesiones, idiomas, subtítulos y estados — Responsable: Codex | Estado: terminada | Depende de: 1.1, 1.2.
- [x] 1.4 Ejecutar tests de regresión, build y pruebas de navegador; agregar CI y documentación — Responsable: Codex | Estado: terminada | Depende de: 1.3.
- [ ] 1.5 Revisar PR contra contrato — Responsable: Claude | Estado: pendiente | Depende de: 1.4.
- [ ] 1.6 Probar dos sesiones con audio real y medir entrega hasta navegador — Responsable: Codex | Estado: bloqueada | Depende de: backend real de Claude y 1.5. Los fixtures no acreditan inferencia, calidad ni latencia real.

## Decisiones de implementación

JavaScript con módulos nativos y Vite para servidor local, proxy HTTP/WebSocket
al backend y build estático. Sin framework de UI ni dependencias en runtime.
El estado del protocolo y el transporte se prueban separados del DOM.
La UI consume rutas relativas `/api/v1/`; en desarrollo Vite apunta por defecto
a `http://127.0.0.1:8000` (configurable por `DECILO_BACKEND_URL`). Producción
requiere servir frontend y API bajo el mismo origen.

Modo de muestra explícito `?demo=1`, siempre rotulado como simulado. Nunca
se activa automáticamente ante fallo del backend. Fixtures propios de UI
hasta disponer de los compartidos por Claude; no reemplazan su tarea 3.3.
Historial acotado a 100 segmentos y 100 gaps, textos por `textContent`.

## Evidencia de validación

- 14 tests Node correctos: revisiones/invalidación, finales inmutables, snapshot,
  generación, orden, límites, gaps, cambio de sesión, reconexión y fallo de catálogo.
- 3 tests Playwright correctos en Chrome del sistema: móvil 390px, idiomas,
  revisiones, dos sesiones simuladas, texto HTML tratado como texto, pérdida de
  secuencia y reintento de catálogo. Se corrigió una invocación de temporizadores
  que los tests de Node no detectaban y sí fallaba en navegador.
- `npm run build` correcto; `actionlint audience.yml` sin errores;
  `openspec validate vista-audiencia --strict` correcto.
- Inspección visual en 1440px y 390px, sin desborde horizontal.
- No se midió audio real ni latencia de inferencia. Las tareas 1.5/1.6 siguen
  pendientes. La documentación para Claude está en `frontend/README.md`.

## 2. Lectura adaptable — avance independiente del backend

- [x] 2.1 Agregar tamaños de texto y modo Solo subtítulos — Responsable: Codex | Estado: terminada | Depende de: 1.3. Preferencia de tamaño persistida cuando es posible; salida por botón/Escape y sin cambiar la conexión. Se conserva el aviso de simulación.
- [x] 2.2 Validar controles en navegador y documentar uso — Responsable: Codex | Estado: terminada | Depende de: 2.1. Cinco pruebas Playwright correctas (las tres anteriores y dos nuevas), build y OpenSpec correctos. Comprobada continuidad de WebSocket, foco de teclado, tamaño persistido, almacenamiento bloqueado y ausencia de desborde móvil; inspección visual a 390px.
- [ ] 2.3 Revisar extensión de lectura en PR #2 junto con la vista — Responsable: Claude | Estado: pendiente | Depende de: 2.2. El backend y la integración con audio real continúan fuera de esta entrega.
