# Prueba mínima: backend activo con Gemini

Solicitada por el usuario con cuenta prepaga: limitar solicitudes. Se usó main
f5bdbc2 (PRs 15/17/16 integrados), backend real en 8000 y frontend en 5173.
Configuración LOCAL: STT y traducción Gemini 3.8 Flash; sin prewarm ni autostart;
cola de traducción activa, segmentación pause, streaming de traducción apagado.
La clave y la selección local están en .env ignorado; no se versionan credenciales.

Entrada: primeros 3s del WAV sintético EN del repo, por WebSocket de captura en
paquetes de 100ms a ritmo real, luego stop. Un único segmento, dos solicitudes
a Gemini (transcripción y traducción), sin reintentos. No hubo más pruebas de
inferencia; visitar el resultado por snapshot no ejecuta modelos.

- Original: Welcome to this talk about distributed systems
- Traducción: Bienvenidos a esta charla sobre sistemas distribuidos.
- Publicación original: 3.2063s desde fin del audio (6.2063s desde inicio).
- Publicación traducción: 4.9353s desde fin del audio (7.9353s desde inicio).

Ver tiempos exactos y eventos en smoke.json. Un reloj monotónico del cliente
que envía audio y recibe eventos; incluye ida/vuelta del transporte local y cola,
no tiempo de render del navegador. No es una comparación local/nube ni prueba
sostenida de calidad, capacidad o costo. No se obtuvo desglose de tokens/costo.

El backend queda habilitado para nube, sin audio ejecutándose automáticamente.
Cualquier nueva captura que inicie el usuario hará nuevas solicitudes pagas.

Verificación adicional: Playwright abrió la sesión real vía el frontend de 5173
y encontró la traducción del snapshot. No se generó audio ni nueva inferencia.
