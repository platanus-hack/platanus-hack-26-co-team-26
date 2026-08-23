# Alertas sísmicas

**Estado: PARCIAL.** `services/alerts` tiene fuentes EMSC, USGS y SGC con deduplicación y websocket. La app Android todavía no recibe esos eventos en segundo plano; el estado que se muestra en el shell es local/demo.

La integración pendiente debe conectar `RealEarthquakeAlertSource` y `DemoEarthquakeAlertSource` al mismo `EmergencyController`. No se debe navegar directamente desde un botón de demo.

Proveedor real disponible en backend: EMSC/USGS y SGC condicionado por configuración.
No se debe reportar una alerta como recibida en el teléfono hasta probar el
adaptador Android y su ejecución en segundo plano.

