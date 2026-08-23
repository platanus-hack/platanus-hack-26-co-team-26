# Alertas sísmicas

**Estado: PARCIAL.** `services/alerts` tiene fuentes EMSC, USGS y SGC con deduplicación y websocket. La app Android todavía no recibe esos eventos en segundo plano; el estado que se muestra en el shell es local.

La integración pendiente debe conectar `RealEarthquakeAlertSource` y `DemoEarthquakeAlertSource` al mismo `EmergencyController`. No se debe navegar directamente desde un botón de demo.

