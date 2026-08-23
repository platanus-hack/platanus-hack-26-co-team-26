# Pruebas móviles

Pure tests cover PPG frequency detection, short/noisy rejection, location calculations, freshness, stay points, frequent places, and adaptive tracking. On a real device validate permission denial, missing gyroscope, missing accelerometer, camera permission denial, torch failure, capture shorter than eight seconds, battery saver, and no network.

Para PPG, prueba una señal sintética normal, una señal de baja frecuencia que
solicita segunda verificación, dos ventanas anómalas coherentes
(`REPEATED_ANOMALY`) y dos ventanas que discrepan (`INCONCLUSIVE_RECHECK`).
Nunca interpretes el patrón repetido como diagnóstico clínico.

## Prueba física de tres dispositivos

Instala el mismo APK DEBUG en A (teléfono víctima), B (relay) y C (apoyo).
Concede permisos de dispositivos cercanos en los tres y abre **Red cercana**.

1. En A pulsa `NECESITO AYUDA` y luego `Encolar paquete de prueba` desde el
   laboratorio DEBUG.
2. Confirma en B `Paquetes recibidos` y la misma identidad de paquete.
3. Apaga o aleja A; deja B anunciando y buscando.
4. Acerca C y confirma que B reenvía y C recibe la misma identidad.
5. Revisa `Deduplicación` al repetir la ruta; no esperes ACK porque todavía no
   existe confirmación de aplicación.

Esta prueba no se considera aprobada hasta ejecutarse físicamente. También
deben probarse reconexión, Internet desactivado, permisos denegados y una
actualización de movimiento/PPG mientras la señal permanece activa.
