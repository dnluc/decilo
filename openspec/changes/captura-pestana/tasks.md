# Tasks
- [x] 1. Compartir inferencia entre archivos y captura — Responsable: Codex
- [x] 2. Implementar ingreso PCM, límites, gaps y cierre — Responsable: Codex
- [x] 3. Embeber video y capturar pestaña con permiso — Responsable: Codex
- [ ] 4. Verificar protocolo, navegador e inferencia real — Responsable: Codex
- [ ] 5. Revisión cruzada — Responsable: Claude (pendiente de disponibilidad)


Validación: 123 tests Python, 14 Node, 5 de navegador, 4 de integración,
Ruff, build y OpenSpec correctos. La integración simula el permiso con un
MediaStream de oscilador, pero usa AudioWorklet, PCM, WS y gateway reales.
Verifica recepción, falta de pista de audio y liberación al detener. Tests
Python cubren tamaño/orden/duración, cola con descarte y fin de sesión.

Prueba adicional con Whisper/Gemma reales: un WAV conocido se inyectó como
MediaStream (permiso simulado), pasó por el worklet y produjo traducción ES
visible. La sesión llegó a ended al detener. No se prueba así el selector de
Chrome, el audio humano de YouTube ni la calidad/latencia. Tarea 4 parcialmente
verificada: falta la autorización y prueba manual del usuario sobre YouTube.
Metadata del enlace verificada mediante oEmbed de YouTube: API Gateway: On
Contracts, Doors and Dangers of the Outside — Vlad Tomashpolskyi, Nerdearla.
