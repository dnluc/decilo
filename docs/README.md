# Documentación de Decilo

Revisión integral al commit de código `e4b9f90` (PRs #21 y #22), 25/09/2026.

| Necesidad | Documento |
| --- | --- |
| Video, logo, carátulas y evidencia de demo | [Presentación de 1:55](DEMO.md) |
| Instalar y probar, español/inglés | [README raíz](../README.md) |
| Componentes, Mermaid, contratos, recursos y configuración | [Arquitectura](ARQUITECTURA.md) |
| Captura, UI, pruebas y build | [Frontend](../frontend/README.md) |
| Workflows y alcance de pruebas | [CI](ci.md) |
| Objetivos futuros y diferenciales | [Visión](../VISION.md) |
| Implementado, pendiente e historia por cambio | [OpenSpec](../openspec/README.md) |
| Resultados de corridas anteriores | [Evidencia histórica](validation/README.md) |
| Audio sintético y referencias | [Muestras](../samples/README.md) |
| Eventos de ejemplo del protocolo | [Fixtures](../fixtures/README.md) |
| Textos locales para preparar la entrega | [Borrador Devpost](devpost.md) |
| Acuerdo de trabajo | [Colaboración](../COLLABORATION.md) |

## Cómo interpretar la documentación

Las guías operativas describen el código al commit indicado. OpenSpec conserva
requisitos/decisiones y registra diferencias con lo implementado: una casilla de
implementación no acredita el benchmark ni todos los escenarios de aceptación.
Los informes de `validation/` son evidencia histórica inmutable en sus datos;
no actualizarles modelos, tiempos o conteos para hacerlos parecer actuales.

Los defaults son ahora Live STT `gemini-3.5-transcribe-live`, REST
`gemini-3.5-flash-lite`, Whisper provisional `base` y final `small` EN/ES.
Un `.env` previo puede seguir sobreescribiéndolos; esta actualización no cambia
credenciales, procesos activos, configuración local ni el formulario de Devpost.
