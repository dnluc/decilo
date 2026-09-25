# Handoff para Claude

Trabajá en ~/projects/decilo-claude. Leé COLLABORATION.md, VISION.md y los
artefactos de backend-latencia-incremental. Codex implementa backend; vos frontend
y revisión cruzada. Actualizá main sin perder tus cambios y abrí rama/PR para código.
No tocar backend ni reinstalar/ajustar Ollama mientras Codex implementa o mide.

1. Revisá el diseño y registrá objeciones concretas en tasks.md. Conservamos
   protocolo v1: no agregar campos o cambiar eventos unilateralmente.
2. Cambiá transporte de captura a 100ms como punto de partida: 1600 muestras
   PCM16 LE mono a 16kHz, precedidas por offset uint32 LE. Mantener continuidad,
   validación de frecuencia real, límite de buffer y liberación de recursos.
   Flush del último paquete antes de `stop`, sin reproducir el audio capturado
   nuevamente. Mandar paquetes pequeños no significa pedir ASR por cada paquete.
3. Reutilizá el manejo provisional/final existente. Reemplazá texto por
   (segment_id, kind, language) y revision; nunca anexes cada revisión como otra
   frase. Final inmutable; traducción se confirma independientemente del original.
   Respetá source_revision, invalidación, stream_id, seq, snapshots y gaps.
   No simules tokens ni confirmes texto por timeout. Solo existe estado por
   segmento: no asumir un campo de prefijo estable ni inventar confianza.
4. Verificá que texto provisional se lea sin saltos molestos, manteniendo
   reproductor audible y subtítulos cercanos. Reutilizá UI actual donde ya cumple.
   Mostrar interrupción/degradación cuando corresponda; no esconder pérdidas.
5. Tests: tamaños/offsets de paquetes, último fragmento/stop, buffer saturado,
   revisiones duplicadas/viejas, original revisado con traducción tardía, reconexión
   y cambio de sesión. Probar con fixtures deterministas sin modelos, además de
   navegador con backend. Registrar recepción/render con reloj del navegador;
   no restar performance.now() de timestamps monotónicos Python.
6. Publicá PR, actualizá tareas 1.1 y 4.x con evidencia y pedí revisión a Codex.
   Coordiná antes de correr Whisper/Gemma para no contaminar mediciones.

Podés hacer transporte y UI con fixtures mientras Codex implementa streaming.
No hace falta esperar al detector semántico para esas tareas. No modificar
contratos públicos ni prometer menor latencia sin medir el recorrido completo.
