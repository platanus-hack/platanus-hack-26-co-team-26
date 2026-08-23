# Evidencia de movimiento

**Estado: IMPLEMENTADO en dominio; PARCIAL en UI.** El dominio de `core/signal/motion` usa ventanas de acelerómetro y giroscopio, extracción determinista de características y clasificación. El adaptador Android avanzado `SensorManagerMotionAdapter` es el candidato canónico; el shell conserva una fuente simple de compatibilidad.

La UI debe usar “Movimiento reciente detectado” y nunca “persona viva”.

