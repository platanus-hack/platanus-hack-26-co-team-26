# Ubicación

**Estado: PARCIAL.** `:android:sensing` aporta `AndroidLocationSource` con permisos aproximados/precisos, proveedor GNSS/red, perfiles pasivo/normal/activo/emergencia y estados sin proveedor. `core` contiene modelos de ubicación, análisis de frescura y estimación histórica local.

La persistencia de historial y lugares frecuentes aún requiere un repositorio de almacenamiento conectado al shell. El acceso puede continuar sin permiso y no debe crear un callejón sin salida.

