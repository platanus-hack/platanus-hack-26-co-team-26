# Navegación

Flujo inicial:

```text
LOGIN → REGISTRO (opcional) → explicación de ubicación → INICIO
                                             ↘ continuar sin permiso
```

En modo normal, la navegación inferior expone Inicio, Mapa, Personas y Perfil.
Desde Inicio se accede a Movimiento, Evaluación fisiológica, Dispositivos
cercanos, permisos y diagnóstico.

Una alerta sísmica, un SOS manual o la simulación atraviesan la misma máquina:

```text
ALERTA → ESPERA DE RESPUESTA → APOYO DE EMERGENCIA
                         ↘ ASISTENCIA REQUERIDA
```

En asistencia requerida se oculta la navegación normal y se prioriza la señal
SOS y la evaluación fisiológica. Las pantallas de Reportes, Alertas recibidas y
Mapa de emergencia son bases honestas: no inventan datos cuando el backend aún
no está conectado.

La experiencia normal usa **Inicio, Mapa, Red y Perfil**. Inicio presenta
un hero espacial y el mapa de baja saturación; en tablet, desde ~720 dp, Mapa se
abre en dos columnas con su contexto de permisos, frescura y relaciones. El
shell muestra una orientación local con GPS real, precisión y frescura. Personas,
reportes y alertas remotas quedan fuera de la navegación normal mientras no haya
un backend de cuentas/incidentes conectado; las simulaciones solo existen en
DEBUG.

