# Operación offline

**Estado local:** funcionan sin Internet la captura de sensores, el procesamiento local PPG, la evidencia de movimiento, la lectura local de ubicación, la cuenta local persistente y la cola Nearby persistente. El backend, las alertas sísmicas reales y la sincronización requieren red; no se muestran como producción si no hay una fuente conectada.

No se debe ocultar la falta de conexión: cada pantalla debe indicar si el dato es local, antiguo, estimado o de demostración.

Si no hay Wi‑Fi, Nearby puede negociar Bluetooth/BLE; si ambos radios no están
disponibles, el SOS conserva el estado local y queda pendiente. Android exige
permiso y consentimiento para el radio; Helios no puede activarlos de forma
silenciosa.

