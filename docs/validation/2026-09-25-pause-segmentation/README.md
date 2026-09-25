# Segmentación por pausas

Verificación: 143 tests Python, Ruff y 4 pruebas de integración con navegador
correctos. OpenSpec mvp-pipeline validado en modo estricto.

`boundaries.json` registra límites sobre los WAV de prueba, sin ejecutar modelos.
En inglés hubo 2 cortes por pausa, 5 por máximo y 1 por fin de archivo;
en español, 3 por pausa, 5 por máximo y 1 por fin de archivo.
Esto no demuestra comprensión semántica ni una mejora de calidad o latencia.

El transporte del frontend todavía agrupa cinco segundos. Para aprovechar
pausas tempranas Claude debe enviar paquetes de 100–200 ms usando el mismo
protocolo. La detección usa energía: puede perder voz muy baja y confundir ruido
con voz. Falta validar con audio humano y ajustar el umbral según la fuente.
